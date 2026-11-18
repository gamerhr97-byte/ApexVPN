"""0.10.4 invariants: Free ownership, retained transport fields, observed usage, idle motion."""
import json, pathlib, subprocess
from urllib.parse import urlencode,quote
import pytest
from nextapp.free_sources import install_presets as seed, prune_failed, load_free_source
from nextapp.subscriptions import Subscription, reconcile
from nextapp.profiles import parse_link, make_config, Unsupported
from nextapp.transport_extensions import check_core_extensions
from nextapp.traffic_history import TrafficHistory

from nextapp.ui import Window
LAUNCH_REFRESH=Window.refresh_on_launch

LINK='trojan://local-fixture@localhost:443?security=tls&type=ws&sni=localhost&path=%2F'
def profile(source='',status='Failed',code='TCP_REFUSED'):
    p=parse_link(LINK);p.subscription_id=source;p.test_status=status;p.test_error=code;return p

def test_free_catalog_restores_removed_builtin_sources():
    subs=[];settings={}
    assert seed(subs,settings) and len(subs)==4 and all(s.is_free for s in subs)
    subs.pop();assert seed(subs,settings) and len(subs)==4
    assert not seed(subs,settings)

def test_free_pruning_is_temporary_owned_and_completed_only():
    sub=Subscription('Free fixture','https://example.invalid/feed',is_free=True)
    bad=profile(sub.id);private=profile('personal');active=profile(sub.id);internal=profile(sub.id,code='CORE_TIMEOUT')
    working=profile(sub.id,'Verified','');untested=profile(sub.id)
    original=[bad,private,active,internal,working,untested]
    kept,removed=prune_failed(original,[sub],{bad.id,private.id,active.id,internal.id,working.id},active.id)
    assert removed==[bad] and private in kept and active in kept and internal in kept and untested in kept
    restored,selected=reconcile(kept,[parse_link(LINK)],sub.id,private.id)
    assert any(p.subscription_id==sub.id for p in restored) and selected==private.id
    assert original[0] is bad

def test_free_tolerates_malformed_entries_without_dropping_parameters():
    sub=Subscription('fixture','https://example.invalid/feed',is_free=True)
    incoming,meta,_=load_free_source(sub,fetch=lambda *a,**kw:LINK+'&future=retained\nnot-a-profile\n'+LINK+'&future=retained')
    assert len(incoming)==1 and incoming[0].params['future']=='retained' and meta['skipped_entries']==1
    with pytest.raises(Unsupported):make_config(incoming[0])

def extension_profile():
    masks={'tcp':[{'type':'fragment','settings':{'packets':'tlshello','lengths':['0','104','1'],'delays':['0'],'maxSplit':'0'}},{'type':'fragment','settings':{'packets':'1-1','lengths':['114','1'],'delays':['1'],'maxSplit':'11'}}]}
    q={'cs':'TLS_AES_128_GCM_SHA256:TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256','fm':json.dumps(masks),'fragment':'null,null,tlshello,0','fp':'unsafe'}
    return parse_link(LINK+'&'+urlencode(q,quote_via=quote)),masks

def test_transport_extensions_lossless_and_core_guard(tmp_path):
    p,masks=extension_profile();cfg=make_config(p)
    stream=cfg['outbounds'][0]['streamSettings']
    assert stream['finalmask']==masks and stream['tlsSettings']['cipherSuites']==p.params['cs']
    assert not stream['tlsSettings'].get('allowInsecure',False)
    assert 'fragment' in p.params and p.params['fp']=='unsafe'
    with pytest.raises(Unsupported):check_core_extensions(b'Xray 26.3.27',p)
    check_core_extensions(b'Xray 26.10.21',p)
    core=pathlib.Path(__file__).resolve().parents[1]/'core/xray'
    if not core.exists():pytest.skip('Pinned Linux core absent')
    file=tmp_path/'local.json';file.write_text(json.dumps(cfg))
    result=subprocess.run([str(core),'run','-test','-c',str(file)],capture_output=True,timeout=5)
    assert result.returncode==0,result.stderr.decode()

def test_observed_traffic_reset_windows_and_persistence(tmp_path):
    now=[2000000000.];h=TrafficHistory(tmp_path,clock=lambda:now[0])
    h.observe('system','nic',10000,20000);h.observe('system','nic',10100,20200)
    assert h.report('system')['session']['total']==300
    h.observe('system','nic',1,2);assert h.report('system')['session']['total']==300
    h.observe('vpn','owned-process',10,20);assert h.report('vpn')['session']['total']==30
    h.unavailable('system');h.observe('system','nic',50000,60000)
    assert h.report('system')['session']['total']==300
    now[0]+=13*3600
    assert h.report('system')['12h']['total']==0 and h.report('system')['24h']['total']==300
    h.close();h=TrafficHistory(tmp_path,clock=lambda:now[0])
    assert h.report('system')['session']['total']==0 and h.report('system')['24h']['total']==300
    h.close()

def test_motion_keeps_geometry_and_stops_at_rest():
    from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QPushButton,QCheckBox
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt,QPoint
    from nextapp.interactions import InteractionEffects
    app=QApplication.instance() or QApplication([])
    w=QMainWindow();w.settings={'visual_effects':True,'reduced_motion':False};central=QWidget();w.setCentralWidget(central)
    layout=QVBoxLayout(central);button=QPushButton('Click');check=QCheckBox('Check');layout.addWidget(button);layout.addWidget(check)
    fx=InteractionEffects(w);w.show();QTest.qWait(30);geometry=(button.geometry(),check.geometry())
    clicks=[];button.clicked.connect(lambda:clicks.append(1));QTest.mouseClick(button,Qt.LeftButton);QTest.mouseClick(check,Qt.LeftButton,pos=QPoint(8,check.height()//2))
    QTest.qWait(450)
    assert clicks==[1] and check.isChecked() and geometry==(button.geometry(),check.geometry())
    assert not fx.overlay.timer.isActive() and all(e is None or e.scale==1. for e in fx.effects.values())
    w.settings['reduced_motion']=True;QTest.mouseClick(button,Qt.LeftButton)
    assert clicks==[1,1] and not fx.overlay.timer.isActive()
    fx.shutdown();w.close();w.deleteLater();app.processEvents()


def test_launch_refreshes_every_source_before_optional_connect():
    from types import SimpleNamespace
    calls=[]
    owner=SimpleNamespace(sub_busy=False,test_busy=False,engine=SimpleNamespace(busy=False),subscriptions=[1,2,3],start_subscriptions=lambda subs:calls.append(subs),connect_on_launch=lambda:calls.append('connect'))
    LAUNCH_REFRESH(owner)
    assert calls==[[1,2,3]] and owner.startup_refresh_pending

def test_production_seed_free_group_and_usage_category(tmp_path,monkeypatch):
    from nextapp import free_sources
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(free_sources,'install_presets',seed)
    w=Window(tmp_path)
    try:
        w.show();app.processEvents()
        assert len(w.subscriptions)==4 and w.settings_page.nav.count()==15
        w.servers_page.select_group('free')
        assert w.servers_page.group=='free'
        w.settings_page.open_category(14);app.processEvents()
        assert w.settings_page.stack.currentIndex()==14
    finally:
        w.close();app.processEvents()
