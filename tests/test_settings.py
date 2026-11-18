import json,pathlib,threading,time,zipfile,types
import pytest
from PySide6.QtCore import QObject,Signal,Qt
from PySide6.QtWidgets import QApplication
from nextapp.settings_schema import SCHEMA,SPECS,defaults,validate,migrate,export_preferences,import_preferences
from nextapp.settings_services import TelegramStore,parse_telegram,CoreManager,Cancelled,support_bundle
from nextapp.settings_runtime import SettingsRuntime
from nextapp.ui import Window
from nextapp.profiles import parse_link

def app():return QApplication.instance() or QApplication([])
def pump(predicate,timeout=3):
    end=time.monotonic()+timeout
    while not predicate() and time.monotonic()<end:app().processEvents();time.sleep(.005)
    assert predicate()

def test_schema_defaults_and_metadata():
    s=validate(defaults());assert len(SCHEMA)==len(SPECS) and s['settings_theme']=='Dark' and not s['kill_switch']
    for field in SPECS:
        assert field.persistence and field.permission and field.application and field.error_handling
        assert field.reset==field.default
    assert all(0<=field.section<14 for field in SPECS) and SCHEMA['logging'].section==12

@pytest.mark.parametrize('key,value',[('http_port',80),('retry_attempts',99),('kill_switch',True),('seamless',True),('https_url','http://a.com'),('https_url','https://user:pass@a.com'),('accent','#bad'),('lightweight',1)])
def test_schema_rejects_invalid_or_unavailable(key,value):
    values=defaults();values[key]=value
    with pytest.raises(ValueError):validate(values)

def test_atomic_related_validation_and_migration():
    values=defaults();values['socks_port']=values['http_port']
    with pytest.raises(ValueError):validate(values)
    result=migrate({'concurrency':-2,'language':'fa','selected':'private-id','theme':'Light','kill_switch':True})
    assert result['concurrency']==4 and result['language']=='fa' and result['theme']=='Apex' and not result['kill_switch'] and result['selected']=='private-id'

def test_non_sensitive_export_and_import():
    current=defaults();current['core']='/private/path';current['https_url']='https://example.invalid/private-token';current['selected']='uuid';current['reliability']={'private-id':{'success':4}}
    data=export_preferences(current);raw=json.dumps(data)
    for token in ('private-token','/private/path','private-id','uuid','selected','reliability'):assert token not in raw
    assert import_preferences(data,current)['core']=='/private/path'
    data['settings']['https_url']='https://example.com'
    with pytest.raises(ValueError):import_preferences(data,current)

@pytest.mark.parametrize('url,kind',[
 ('tg://proxy?server=example.com&port=443&secret='+'ab'*16,'MTProto'),
 ('https://t.me/proxy?server=127.0.0.1&port=443&secret=dd'+'ab'*16,'MTProto'),
 ('tg://socks?server=example.com&port=1080&user=a&pass=b','SOCKS5')])
def test_telegram_parse_roundtrip_and_protected_persistence(tmp_path,url,kind):
    proxy=parse_telegram(url);assert proxy.kind==kind
    assert parse_telegram(proxy.link()).server==proxy.server
    store=TelegramStore(tmp_path);store.save([proxy]);assert store.load()==[proxy]

@pytest.mark.parametrize('url',[
 'https://evil.example/proxy?server=ok&port=443&secret='+'ab'*16,
 'tg://proxy?server=ok&port=443&secret=invalid',
 'tg://socks?server=x&port=0','tg://socks?server=x&port=1080&unknown=1',
 'tg://socks?server=x&server=y&port=1080','tg://socks?server=x%0A&port=1080',
 'tg://socks?server=x&port=1080#ignored'])
def test_telegram_rejects_ambiguous_or_unsafe(url):
    with pytest.raises(ValueError):parse_telegram(url)

def test_core_verified_local_install_and_rollback(tmp_path):
    source=pathlib.Path(__file__).resolve().parents[2]/'downloads/Xray-linux-64.zip'
    if not source.exists():pytest.skip('Pinned Linux release not present')
    manager=CoreManager(tmp_path);cancel=threading.Event();path,version=manager.install(cancel,source)
    assert version=='Xray '+json.loads((pathlib.Path(__file__).resolve().parents[1]/'dependencies.lock.json').read_text())['Xray'] and pathlib.Path(path).is_file()
    previous=pathlib.Path(path).read_bytes();manager.install(cancel,source)
    restored,version=manager.rollback();assert pathlib.Path(restored).read_bytes()==previous
    corrupt=tmp_path/'corrupt.zip';corrupt.write_bytes(source.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='checksum'):manager.install(cancel,corrupt)
    assert pathlib.Path(path).read_bytes()==previous
    cancel.set()
    with pytest.raises(Cancelled):manager.install(cancel,source)

def test_core_safe_extraction_before_execution(tmp_path,monkeypatch):
    import hashlib
    archive=tmp_path/'evil.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('../xray',b'evil');z.writestr('xray',b'evil')
    manager=CoreManager(tmp_path);monkeypatch.setattr(manager,'release',lambda:('https://github.com/XTLS/Xray-core/releases/download/v26.3.27/Xray-linux-64.zip',hashlib.sha256(archive.read_bytes()).hexdigest()))
    with pytest.raises(ValueError,match='Unsafe'):manager.install(threading.Event(),archive)
    assert not (tmp_path/'xray').exists()

class FakeEngine(QObject):
    state=Signal(str,str)
    def __init__(self):super().__init__();self.busy=False;self.running=False;self.calls=[]
    def connect_profile(self,p,s):self.calls.append(p.id)

class FakeOwner(QObject):
    def __init__(self,tmp_path):
        super().__init__();from nextapp.storage import Store
        self.settings=defaults();self.engine=FakeEngine();self.profiles=[];self.selected='';self.active_id='';self.latency_ms=42;self.store=Store(tmp_path);self.sub_busy=False;self.runtime=None;self.activity=types.SimpleNamespace(history=[]);self.notices=[]
    def selected_profile(self):return next((p for p in self.profiles if p.id==self.selected),None)
    def refresh_profile(self):pass
    def notice(self,text):self.notices.append(text)

def test_smart_selection_uses_https_history_not_tcp_and_respects_pin(tmp_path):
    o=FakeOwner(tmp_path);a=parse_link('trojan://x@a.example:443?security=tls');b=parse_link('trojan://y@b.example:443?security=tls');a.latency=1;b.latency=999;o.profiles=[a,b];o.selected=a.id;o.settings['smart_connect']=True
    o.settings['reliability']={a.id:{'success':3,'failures':0,'latency':200,'verified_at':time.time()},b.id:{'success':4,'failures':0,'latency':40,'verified_at':time.time()}}
    r=SettingsRuntime(o);assert r.candidates()[0].id==b.id
    a.favorite=True;assert [p.id for p in r.candidates()]==[a.id]
    r.shutdown()

def test_bounded_reconnect_manual_stop_and_short_success_does_not_reset(tmp_path):
    app();o=FakeOwner(tmp_path);p=parse_link('trojan://x@a.example:443?security=tls');o.profiles=[p];o.selected=p.id;o.settings.update(auto_reconnect=True,retry_attempts=2,automatic_tuning=False)
    r=SettingsRuntime(o);r.connect();assert len(o.engine.calls)==1
    r.state('Connected','verified')
    for attempt in range(2):
        r.state('Error','network lost');assert r.retry.isActive();r.retry.stop();r._retry();r.state('Connected','verified');assert r.attempt==attempt+1
    r.state('Error','network lost');assert not r.retry.isActive() and len(o.engine.calls)==3
    r.stop();r.state('Error','late failure');assert not r.retry.isActive()
    r.shutdown()

def test_settings_persist_search_rtl_and_disabled_states(tmp_path):
    a=app();w=Window(tmp_path);w.notice=lambda _:None
    try:
        w.show();w.navigate(3);a.processEvents();page=w.settings_page;page.message=lambda _:None
        assert w.stack.count()==4 and page.stack.count()==15 and page.nav.count()==15
        assert not page.controls['tun'].isEnabled() and not page.controls['app_split'].isEnabled() and not page.controls['kill_switch'].isChecked()
        page.controls['retry_attempts'].setValue(5);page.apply();assert w.store.load_settings()['retry_attempts']==5
        assert w.settings['theme']=='Apex' and w.settings['settings_theme']=='Dark'
        page.search.setText('kill switch');assert page.nav.currentRow()==5
        page.search.clear();page.nav.setCurrentRow(1);page.reset_section();assert w.settings['retry_attempts']==5 and page.controls['retry_attempts'].value()==3
        page.controls['language'].setCurrentIndex(1);page.apply();a.processEvents();assert w.settings_page.layoutDirection()==Qt.RightToLeft
    finally:w.close();a.processEvents()
    w=Window(tmp_path)
    try:assert w.settings['language']=='fa' and w.settings['retry_attempts']==3 and w.settings_page.fa
    finally:w.close();a.processEvents()

def test_settings_cancel_discards_results_and_bounds_pending_work(tmp_path):
    a=app();w=Window(tmp_path);w.show();w.navigate(3);p=w.settings_page;p.nav.setCurrentRow(6);messages=[];p.message=messages.append;gate=threading.Event()
    try:
        p.execute(lambda cancel:(gate.wait(2),'late result')[1]);p.cancel_operation();p.execute(lambda cancel:'should not queue');assert messages
        w.navigate(0);gate.set();pump(lambda:p.future.done());a.processEvents();assert p.output_6.toPlainText()!='late result'
    finally:gate.set();w.close();a.processEvents()

def test_support_bundle_never_contains_secrets(tmp_path):
    a=app();w=Window(tmp_path);secret='NEVER_INCLUDE_THIS_PRIVATE_TOKEN'
    try:
        w.settings['https_url']='https://example.com/'+secret;w.history_errors.append(secret+' [AUTH_FAILED]');w.profiles=[parse_link('trojan://'+secret+'@example.com:443?security=tls#'+secret)]
        path=tmp_path/'support.zip';support_bundle(path,w)
        with zipfile.ZipFile(path) as z:
            data=b''.join(z.read(n) for n in z.namelist());assert secret.encode() not in data and b'example.com' not in data and b'AUTH_FAILED' in data
            assert set(z.namelist())=={'summary.json','privacy.txt'}
    finally:w.close();a.processEvents()

def test_privacy_stopped_reports_unknown_without_network():
    from nextapp.settings_services import privacy_report
    text=privacy_report(defaults(),False,threading.Event());assert 'not measured' in text and 'stopped' in text

def test_startup_registry_current_user_and_ownership(monkeypatch):
    import sys
    import nextapp.settings_services as services
    values={}
    class Key:
        def __enter__(self):return self
        def __exit__(self,*args):pass
    def query(key,name):
        if name not in values:raise FileNotFoundError
        return values[name],1
    registry=types.SimpleNamespace(HKEY_CURRENT_USER=1,REG_SZ=1,CreateKey=lambda root,path:Key(),SetValueEx=lambda key,name,unused,typ,value:values.update({name:value}),QueryValueEx=query,DeleteValue=lambda key,name:values.pop(name))
    monkeypatch.setattr(services,'os',types.SimpleNamespace(name='nt'));monkeypatch.setitem(sys.modules,'winreg',registry)
    services.set_startup(True);assert values['NekoRayNext']==services.startup_command()
    services.set_startup(False);assert not values
    values['NekoRayNext']='another installation'
    with pytest.raises(OSError,match='another installation'):services.set_startup(False)
    assert values['NekoRayNext']=='another installation'

def test_subscription_metadata_accepts_only_provider_numeric_fields():
    from nextapp.network import subscription_metadata
    assert subscription_metadata('upload=3; download=7; total=100; expire=1900000000; token=PRIVATE')=={'upload':3,'download':7,'total':100,'expire':1900000000}
    assert subscription_metadata('upload=-5; download=invalid; total='+'9'*30)=={}

def test_subscription_scheduler_backoff_and_include_active(tmp_path):
    import datetime
    from nextapp.subscriptions import Subscription
    o=FakeOwner(tmp_path);o.active_id='active';o.engine.running=True;o.engine.check_health=lambda:None;o.settings['subscription_interval']='6 hours'
    active=parse_link('trojan://a@a.example:443?security=tls');active.id='active';active.subscription_id='protected';o.profiles=[active]
    o.subscriptions=[Subscription('active','https://example.invalid/private','protected'),Subscription('other','https://example.invalid/other','due')]
    called=[];o.start_subscriptions=lambda entries:called.extend(x.id for x in entries)
    runtime=SettingsRuntime(o);runtime.tick(2);assert called==['protected','due']
    runtime.tick(2);assert called==['protected','due']
    runtime.subscriptions_finished('failed');assert runtime.sub_failures==1 and runtime.subscription_retry>time.monotonic()+590
    runtime.shutdown()

def test_settings_subscription_cancel_keeps_catalog(tmp_path,monkeypatch):
    import nextapp.ui as ui
    from nextapp.subscriptions import Subscription
    a=app();w=Window(tmp_path);w.notice=lambda _:None;w.show();w.navigate(3);gate=threading.Event()
    monkeypatch.setattr(ui,'fetch_subscription',lambda *args,**kwargs:(gate.wait(2),'trojan://x@a.example:443?security=tls')[1])
    try:
        w.start_subscriptions([Subscription('test','https://example.invalid/private')]);w.navigate(0);gate.set();pump(lambda:not w.sub_busy)
        assert w.profiles==[] and w.subscriptions==[]
    finally:gate.set();w.close();a.processEvents()
