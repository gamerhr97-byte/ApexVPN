"""Low-bandwidth checks, assets, sticky badges, real auxiliary tunnel and fast groups."""
import contextlib,json,os,subprocess,threading,time
from pathlib import Path
from unittest.mock import patch
import pytest
from PySide6.QtWidgets import QApplication
from nextapp.service_checks import SERVICES,ICON_CATALOG,priority_keys,ServiceResult,measure_quality,connect_service
from nextapp.settings_schema import defaults,migrate
from nextapp.profiles import Profile,parse_link
from nextapp.engine import Engine,connection_config
from test_e2e import local_network,port

ROOT=Path(__file__).resolve().parents[1]


def test_100_targets_200_local_icons_and_5_https():
    assert len(SERVICES)==100 and len(ICON_CATALOG)==200
    assert len(priority_keys(defaults()))==5
    for s in ICON_CATALOG:assert (ROOT/'assets/services'/f'{s.key}.png').is_file()
    counts={'https':0,'connect':0}
    def https(s,p,t):
        counts['https']+=1
        return ServiceResult(s.key,'ok',1,200,region='not_observed')
    def connect(s,p,t):
        counts['connect']+=1
        return ServiceResult(s.key,'ok')
    with patch('nextapp.service_checks.probe_service',https),patch('nextapp.service_checks.connect_service',connect):
        score,gemini=measure_quality(12000,threading.Event())
    assert counts=={'https':5,'connect':95} and score==100 and gemini


def test_pin_metadata_and_disabled_removal():
    s=migrate(dict(defaults(),service_priority=['site0','gemini','chatgpt','youtube','telegram']))
    assert priority_keys(s)[0]=='site0'
    assert not s['remove_failed_servers']
    assert not s['allow_insecure_profiles']


def test_auxiliary_core_check_and_tls_opt_in():
    for uri in ('hysteria2://fixture@localhost:443?sni=localhost','tuic://11111111-1111-4111-8111-111111111111:fixture@localhost:443','anytls://fixture@localhost:443','socks4://localhost:1080'):
        cfg=connection_config(parse_link(uri),defaults())
        r=subprocess.run([str(ROOT/'core/sing-box'),'check','-c','stdin'],input=json.dumps(cfg).encode(),capture_output=True)
        assert r.returncode==0
    with pytest.raises(Exception,match='insecure TLS'):
        connection_config(parse_link('hysteria2://fixture@localhost:443?insecure=1'),defaults())
    assert connection_config(parse_link('hysteria2://fixture@localhost:443?insecure=1'),dict(defaults(),allow_insecure_profiles=True))['outbounds'][0]['tls']['insecure']


def test_real_hysteria2_engine_lifecycle(local_network,tmp_path):
    app=QApplication.instance() or QApplication([])
    remote=port();cert=Path(os.environ['SSL_CERT_FILE']);key=cert.with_name('key.pem')
    server={'log':{'level':'error'},'inbounds':[{'type':'hysteria2','listen':'127.0.0.1','listen_port':remote,'users':[{'password':'local-only-test'}],'tls':{'enabled':True,'certificate_path':str(cert),'key_path':str(key)}}],'outbounds':[{'type':'direct','tag':'direct'}]}
    proc=subprocess.Popen([str(ROOT/'core/sing-box'),'run','-c','stdin'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    proc.stdin.write(json.dumps(server).encode());proc.stdin.close()
    engine=Engine(tmp_path/'client')
    settings=dict(defaults(),mode='Manual Proxy',http_port=port(),socks_port=port(),stats_port=port(),http_url=local_network[0],https_url=local_network[1])
    profile=parse_link(f'hysteria2://local-only-test@127.0.0.1:{remote}?sni=localhost')
    try:
        time.sleep(.2)
        if proc.poll() is not None:
            output=proc.stdout.read().decode()
            if 'netlink socket: operation not permitted' in output:pytest.skip('Host denies sing-box netlink initialization; real Hysteria2 traffic not verified')
            pytest.fail('Local sing-box fixture failed to start')
        engine._connect(profile,settings)
        assert engine.running,engine.last_failure
        assert engine.backend=='sing-box'
        child=engine.process
        engine._disconnect()
        assert not engine.running and child.poll() is not None
        assert not list((tmp_path/'client').glob('*.json'))
    finally:
        engine.shutdown();proc.terminate();proc.wait(timeout=5)


def test_parallel_tcp_not_serial():
    from nextapp.group_testing import run_group
    from nextapp.profile_testing import ProfileTest
    profiles=[Profile(str(i),'vless','127.0.0.1',10000+i) for i in range(256)]
    active=0;maximum=0;lock=threading.Lock();received=[]
    def tcp(profile,timeout):
        nonlocal active,maximum
        with lock:active+=1;maximum=max(active,maximum)
        time.sleep(.02)
        with lock:active-=1
        return ProfileTest('TCP','Reachable',1)
    with patch('nextapp.group_testing.test_tcp',tcp):
        run_group(profiles,'TCP',defaults(),threading.Event(),lambda _:None,lambda i,r:received.append(i))
    assert len(received)==256 and maximum>16


def test_sticky_badges_on_quick_retest_and_no_pager(tmp_path):
    from nextapp.ui import Window
    from nextapp.profile_testing import ProfileTest
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path)
    try:
        p=Profile('retained','vless','localhost',443,service_score=90,gemini_ok=True)
        w.profiles=[p];w.test_profile_map={p.id:p}
        w.test_total=1;w.test_completed=0
        w.profile_test_received(p.id,ProfileTest('HTTPS','Verified',1))
        assert p.service_score==90 and p.gemini_ok
        assert not hasattr(w.servers_page,'page_caption')
    finally:w.close()


def test_reputation_requires_matching_ip_and_keeps_unknown():
    from nextapp.ip_reputation import parse_report
    report=parse_report({'ip':'192.0.2.1','is_abuser':False,'is_vpn':True},'192.0.2.1')
    assert report['abuse_status']=='not_flagged' and report['flags']['is_proxy'] is None
    assert parse_report({'ip':'192.0.2.1'},'192.0.2.1')['abuse_status']=='unknown'
    with pytest.raises(Exception):parse_report({'ip':'192.0.2.2','is_abuser':False},'192.0.2.1')


def test_clash_and_json_outbound_imports_are_lossless_and_checked():
    from nextapp.profiles import parse_import
    yaml='proxies:\n  - name: local-test\n    type: hysteria2\n    server: localhost\n    port: 443\n    password: fixture-only\n    sni: localhost\n'
    profiles=parse_import(yaml)
    assert len(profiles)==1 and profiles[0].original==yaml.strip()
    cfg=connection_config(profiles[0],defaults())
    r=subprocess.run([str(ROOT/'core/sing-box'),'check','-c','stdin'],input=json.dumps(cfg).encode(),capture_output=True)
    assert r.returncode==0
    text=json.dumps({'outbounds':[{'type':'socks','tag':'a','server':'localhost','server_port':1080},{'type':'socks','tag':'b','server':'localhost','server_port':1081}]})
    proxies=parse_import(text)
    assert len(proxies)==2 and all(x.original==text for x in proxies)
    from nextapp.subscriptions import reconcile
    merged,_=reconcile([],proxies,'test-sub','')
    assert len(merged)==2
    with pytest.raises(Exception):parse_import('proxies: &p\n  - *p')
    with pytest.raises(Exception):parse_import(yaml.replace('    sni:', '    unknown-option:'))


def test_farsi_does_not_mirror_main_controls(tmp_path):
    from nextapp.ui import Window
    from PySide6.QtCore import Qt
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path)
    try:
        w.settings['language']='fa';w.rebuild();w.show();app.processEvents()
        assert w.add_button.mapTo(w.centralWidget(),w.add_button.rect().center()).x()<w.settings_button.mapTo(w.centralWidget(),w.settings_button.rect().center()).x()
        assert w.servers_page.table.layoutDirection()==Qt.LeftToRight
        assert w.settings_page.layoutDirection()==Qt.RightToLeft
    finally:w.close()


def test_removal_is_opt_in_and_keeps_active_and_unsupported(tmp_path):
    from nextapp.ui import Window
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path)
    try:
        failed=Profile('failed','vless','localhost',443,test_status='Timeout')
        active=Profile('active','vless','localhost',443,test_status='Failed')
        unsupported=Profile('UDP','hysteria2','localhost',443,test_status='Unsupported')
        w.profiles=[failed,active,unsupported];w.active_id=active.id
        w.test_profile_map={p.id:p for p in w.profiles};w.test_total=3
        w.profile_tests_finished();assert len(w.profiles)==3
        w.settings['remove_failed_servers']=True
        w.profile_tests_finished();assert {p.id for p in w.profiles}=={active.id,unsupported.id}
    finally:w.active_id='';w.close()


def test_udp_quick_result_is_not_labeled_as_unsupported():
    from nextapp.profile_testing import result_text
    p=Profile('UDP','hysteria2','localhost',443,test_status='Unsupported',test_error='UDP_PROTOCOL_USE_HTTPS',tested_at='2026-10-28')
    assert result_text(p)=='UDP · HTTPS'


def test_shared_original_documents_are_stored_once_and_restored(tmp_path):
    from nextapp.storage import Store
    original='{"outbounds":['+' ' * 20000+']}';store=Store(tmp_path)
    profiles=[Profile(str(i),'singbox-outbound','localhost',443,original=original,raw={'type':'socks','server':'localhost','server_port':10000+i}) for i in range(1000)]
    store.save_profiles(profiles)
    assert (tmp_path/'profiles.dat').stat().st_size<1500000
    restored=store.load_profiles()
    assert len(restored)==1000 and restored[0].original==original
    assert restored[0].original is restored[-1].original
    assert restored[-1].raw['server_port']==10999
    store.save_profiles(restored)
    assert store.load_profiles()[500].original==original
