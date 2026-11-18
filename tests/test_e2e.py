"""Real local HTTP+TLS -> Xray HTTP inbound -> Xray SS server -> target.
No network credentials or external internet required; no fake core or proxy.
"""
import contextlib,json,os,pathlib,socket,ssl,subprocess,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from nextapp.profiles import Profile,make_config
from nextapp.network import proxy_probe,metrics
from nextapp.service_checks import probe_service as actual_service_probe

CORE=pathlib.Path(__file__).resolve().parents[1]/'core'/('xray.exe' if os.name=='nt' else 'xray')

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def ready(p,proc):
    for _ in range(80):
        assert proc.poll() is None,'Core exited unexpectedly'
        try:
            with socket.create_connection(('127.0.0.1',p),.1):return
        except OSError:time.sleep(.025)
    raise RuntimeError('Core did not listen')

@contextlib.contextmanager
def core(cfg):
    # New Xray denies remote-to-private targets by default. Local fixtures allow
    # only their loopback target; production serialization remains untouched.
    import copy
    cfg=copy.deepcopy(cfg)
    for outbound in cfg.get('outbounds',[]):
        stream=outbound.get('streamSettings',{})
        if stream.get('security')=='tls' and os.environ.get('SSL_CERT_FILE'):
            stream.setdefault('tlsSettings',{})['certificates']=[{'certificateFile':os.environ['SSL_CERT_FILE'],'usage':'verify'}]
        if outbound.get('protocol')=='freedom':
            outbound.setdefault('settings',{})['finalRules']=[{'action':'allow','network':'tcp,udp','ip':['127.0.0.1/32','::1/128']}]
    p=subprocess.Popen([str(CORE),'run','-c','stdin:'],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    p.stdin.write(json.dumps(cfg).encode());p.stdin.close()
    try:yield p
    finally:
        if p.poll() is None:p.terminate()
        p.wait(timeout=5)

class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        status={'/blocked':403,'/signin':401,'/rate':429,'/redirect':302,'/head-fallback':405}.get(self.path,204)
        if self.path=='/slow':time.sleep(.3)
        self.send_response(status)
        if status==302:self.send_header('Location','https://example.invalid/must-not-follow')
        self.end_headers()
    def do_GET(self):
        if self.path=='/subscription':
            import base64
            body=base64.b64encode(b'trojan://test@example.com:443?security=tls#Local')
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        elif self.path=='/ip':
            body=b'{"ip":"203.0.113.9"}';self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        elif self.path=='/country':
            body=b'{"ip":"203.0.113.9","country":"DE"}';self.send_response(200);self.end_headers();self.wfile.write(body)
        elif self.path=='/wrong-country-ip':
            body=b'{"ip":"203.0.113.10","country":"US"}';self.send_response(200);self.end_headers();self.wfile.write(body)
        elif self.path=='/invalid-ip':
            body=b'{"ip":"invalid"}';self.send_response(200);self.end_headers();self.wfile.write(body)
        elif self.path=='/blocked':self.send_response(403);self.end_headers()
        elif self.path=='/downgrade':
            self.send_response(302);self.send_header('Location','http://127.0.0.1/subscription');self.end_headers()
        else:self.send_response(204);self.end_headers()
    def log_message(self,*args):pass

@pytest.fixture
def local_network(tmp_path,monkeypatch):
    cert=tmp_path/'cert.pem';key=tmp_path/'key.pem'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-keyout',str(key),'-out',str(cert),'-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    monkeypatch.setenv('SSL_CERT_FILE',str(cert))
    http=ThreadingHTTPServer(('127.0.0.1',0),Handler);https=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(cert),str(key));https.socket=ctx.wrap_socket(https.socket,server_side=True)
    for server in (http,https):threading.Thread(target=server.serve_forever,daemon=True).start()
    try:yield f'http://127.0.0.1:{http.server_port}/',f'https://127.0.0.1:{https.server_port}/'
    finally:
        for server in (http,https):server.shutdown();server.server_close()

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray core required')
def test_http_https_and_real_metrics(local_network):
    hp,sp,mp,remote=port(),port(),port(),port()
    server={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'local-test-password','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    profile=Profile('Local integration test','ss','127.0.0.1',remote,'local-test-password',{'method':'aes-128-gcm'})
    with core(server) as srv:
        ready(remote,srv)
        with core(make_config(profile,hp,sp,mp)) as client:
            ready(hp,client)
            assert proxy_probe(hp,local_network[0])>0
            assert proxy_probe(hp,local_network[1])>0
            time.sleep(.15)
            up,down=metrics(mp)
            assert up>0 and down>0

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray core required')
def test_listening_port_is_not_connection_success(local_network):
    hp,sp,mp,remote=port(),port(),port(),port()
    p=Profile('Unavailable server','ss','127.0.0.1',remote,'wrong',{'method':'aes-128-gcm'})
    with core(make_config(p,hp,sp,mp)) as proc:
        ready(hp,proc)
        with pytest.raises(Exception):proxy_probe(hp,local_network[1],timeout=2)

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray core required')
@pytest.mark.parametrize('authentication',[0,1],ids=['x25519-authentication','mlkem768-authentication'])
def test_real_vless_mlkem_encrypted_traffic(local_network,authentication):
    import re
    # Test keys are generated for this run by Xray itself, never supplied by a user.
    generated=subprocess.check_output([str(CORE),'vlessenc'],text=True)
    decryption=re.findall(r'"decryption": "([^"]+)"',generated)[authentication]
    encryption=re.findall(r'"encryption": "([^"]+)"',generated)[authentication]
    remote,hp,sp,mp=port(),port(),port(),port();uid='11111111-1111-4111-8111-111111111111'
    server={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'vless','settings':{'decryption':decryption,'clients':[{'id':uid,'flow':'xtls-rprx-vision'}]}}],'outbounds':[{'protocol':'freedom'}]}
    p=Profile('Ephemeral local ML-KEM test','vless','127.0.0.1',remote,uid,{'type':'tcp','security':'none','encryption':encryption,'flow':'xtls-rprx-vision','headerType':'none'})
    cfg=make_config(p,hp,sp,mp)
    assert cfg['outbounds'][0]['settings']['vnext'][0]['users'][0]['encryption']==encryption
    with core(server) as srv:
        ready(remote,srv)
        with core(cfg) as client:
            ready(hp,client)
            assert proxy_probe(hp,local_network[0])>0
            assert proxy_probe(hp,local_network[1])>0


def pump(app,predicate,timeout=12):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError('Timed out waiting for application state')

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray core required')
def test_engine_real_connect_crash_cleanup(local_network,tmp_path):
    from PySide6.QtWidgets import QApplication
    from nextapp.engine import Engine
    from nextapp.ui import defaults
    app=QApplication.instance() or QApplication([])
    remote,hp,sp,mp=port(),port(),port(),port()
    server={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'ephemeral','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    p=Profile('Local lifecycle test','ss','127.0.0.1',remote,'ephemeral',{'method':'aes-128-gcm'})
    engine=Engine(tmp_path);states=[];engine.state.connect(lambda state,note:states.append(state))
    s=defaults();s.update({'core':str(CORE),'mode':'Manual Proxy','http_port':hp,'socks_port':sp,'stats_port':mp,'http_url':local_network[0],'https_url':local_network[1]})
    try:
        with core(server) as srv:
            ready(remote,srv);engine.connect_profile(p,s);pump(app,lambda:'Connected' in states)
            assert engine.running
            assert not (tmp_path/'session.json').exists(),'Runtime secrets must stay in the input pipe'
            child=engine.process;child.kill();child.wait(timeout=3);engine.sample();pump(app,lambda:'Error' in states)
            assert not engine.running and engine.process is None
            states.clear();engine.connect_profile(p,s);pump(app,lambda:'Connected' in states)
            child=engine.process;engine.disconnect();pump(app,lambda:'Disconnected' in states)
            assert child.poll() is not None and not engine.running
    finally:engine.shutdown()

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray core required')
def test_optional_http_failure_does_not_reject_verified_https(local_network,tmp_path):
    from PySide6.QtWidgets import QApplication
    from nextapp.engine import Engine
    from nextapp.ui import defaults
    app=QApplication.instance() or QApplication([]);remote,hp,sp,mp=port(),port(),port(),port()
    server={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'ephemeral','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    p=Profile('HTTP-blocked test','ss','127.0.0.1',remote,'ephemeral',{'method':'aes-128-gcm'})
    engine=Engine(tmp_path);states=[];notes=[];engine.state.connect(lambda state,note:(states.append(state),notes.append(note)))
    s=defaults();s.update({'core':str(CORE),'mode':'Manual Proxy','http_port':hp,'socks_port':sp,'stats_port':mp,'http_url':local_network[0]+'blocked','https_url':local_network[1]})
    try:
        with core(server) as srv:
            ready(remote,srv);engine.connect_profile(p,s);pump(app,lambda:'Connected' in states)
            assert engine.running and 'optional HTTP check failed' in notes[-1]
    finally:engine.shutdown()

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray core required')
def test_engine_refused_server_reports_stage_and_sanitized_cause(local_network,tmp_path):
    from PySide6.QtWidgets import QApplication
    from nextapp.engine import Engine
    from nextapp.ui import defaults
    app=QApplication.instance() or QApplication([]);engine=Engine(tmp_path);states=[]
    engine.state.connect(lambda state,note:states.append(state))
    p=Profile('Private name','ss','127.0.0.1',port(),'private-password',{'method':'aes-128-gcm'})
    s=defaults();s.update({'core':str(CORE),'mode':'Manual Proxy','http_port':port(),'socks_port':port(),'stats_port':port(),'https_url':local_network[1]})
    try:
        engine.connect_profile(p,s);pump(app,lambda:'Error' in states)
        assert 'https-verification' in engine.last_failure
        assert 'private-password' not in engine.last_failure and not engine.running
        assert any(code in engine.last_failure for code in ('TCP_REFUSED','REMOTE_CLOSED','PROXY_TUNNEL'))
    finally:engine.shutdown()


def test_real_https_subscription_download_and_redirect_safety(local_network):
    from nextapp.network import fetch_subscription
    from nextapp.profiles import parse_import,ProfileError
    text=fetch_subscription(local_network[1]+'subscription')
    assert parse_import(text)[0].name=='Local'
    with pytest.raises(ProfileError):fetch_subscription(local_network[1]+'downgrade')
    with pytest.raises(ProfileError):fetch_subscription(local_network[0]+'subscription')

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray core required')
def test_core_accepts_reality_aliases_with_explicit_no_header():
    import re
    from nextapp.profiles import parse_link
    keys=subprocess.check_output([str(CORE),'x25519'],text=True)
    public=re.search(r'Password \(PublicKey\):\s*(\S+)',keys).group(1)
    p=parse_link('vless://11111111-1111-4111-8111-111111111111@example.com:443?type=tcp&security=reality&headerType=none&publicKey='+public+'&serverName=example.com&fingerprint=chrome&shortId=1234&flow=xtls-rprx-vision')
    cfg=make_config(p,port(),port(),port())
    result=subprocess.run([str(CORE),'run','-test','-c','stdin:'],input=json.dumps(cfg).encode(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    assert result.returncode==0,'Core rejected headerType=none / REALITY alias mapping'


@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray core required')
def test_glass_real_connection_ping_and_ip_toggle(local_network,tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication
    from nextapp.ui import Window
    from nextapp.network import proxy_public_ip,proxy_country
    import nextapp.ui as ui
    app=QApplication.instance() or QApplication([]);remote,hp,sp,mp=port(),port(),port(),port()
    server={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'ephemeral','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    p=Profile('Local integration server','ss','127.0.0.1',remote,'ephemeral',{'method':'aes-128-gcm'})
    w=Window(tmp_path);w.notice=lambda text:None;w.profiles=[p];w.selected=p.id;w.refresh_profile();w.populate()
    w.settings.update({'core':str(CORE),'mode':'Manual Proxy','http_port':hp,'socks_port':sp,'stats_port':mp,'http_url':local_network[0],'https_url':local_network[1]})
    monkeypatch.setattr(ui,'proxy_public_ip',lambda proxy_port:proxy_public_ip(proxy_port,local_network[1]+'ip'))
    monkeypatch.setattr(ui,'proxy_country',lambda proxy_port,ip:proxy_country(proxy_port,ip,local_network[1]+'country'))
    try:
        with core(server) as srv:
            ready(remote,srv);w.show();w.toggle_connection();pump(app,lambda:w.status=='Connected')
            assert w.latency_ms is not None and w.latency_ms>0 and not w.public_ip
            w.toggle_ip();pump(app,lambda:w.showing_ip)
            assert w.public_ip=='203.0.113.9' and 'IP' in w.ping_button.text()
            assert w.country_code=='DE' and not w.ping_button.icon().isNull()
            assert proxy_country(hp,w.public_ip,local_network[1]+'wrong-country-ip')==''
            w.toggle_ip();assert not w.showing_ip and 'ms' in w.ping_button.text()
            from nextapp.profiles import ProfileError
            with pytest.raises(ProfileError):proxy_public_ip(hp,local_network[1]+'invalid-ip')
            # Genuine local tunnel, generated by Qt; no fabricated connected state.
            out=pathlib.Path(__file__).resolve().parents[1]/'docs/screenshots/connected-local.png'
            app.processEvents();w.grab().save(str(out))
            w.toggle_connection();pump(app,lambda:w.status=='Disconnected');assert not w.public_ip and w.latency_ms is None
    finally:w.close();app.processEvents()


def test_settings_smart_connect_real_https_failover_and_manual_disconnect(tmp_path,local_network):
    """First real Xray path fails; second real SS path must pass local TLS before success."""
    from PySide6.QtWidgets import QApplication
    from nextapp.ui import Window
    from nextapp.profiles import parse_link
    app=QApplication.instance() or QApplication([]);remote=port()
    config={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'ephemeral-smart','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    with core(config) as server:
        ready(remote,server);w=Window(tmp_path);w.notice=lambda _:None
        import base64
        credentials=base64.urlsafe_b64encode(b'aes-128-gcm:ephemeral-smart').decode().rstrip('=')
        bad=parse_link('ss://'+credentials+'@127.0.0.1:'+str(port())+'#unreachable')
        good=parse_link('ss://'+credentials+'@127.0.0.1:'+str(remote)+'#working')
        w.profiles=[bad,good];w.selected=bad.id;w.settings.update(core=str(CORE),mode='Manual Proxy',http_port=port(),socks_port=port(),stats_port=port(),http_url=local_network[0],https_url=local_network[1],smart_connect=True,smart_policy='Manual preferred',retry_delay=1,health_timeout=2,retry_attempts=2)
        try:
            w.runtime.connect();end=time.monotonic()+18
            while time.monotonic()<end and w.status!='Connected':app.processEvents();time.sleep(.02)
            app.processEvents()
            assert w.engine.running and w.active_id==good.id and w.latency_ms is not None
            history=w.settings['reliability'];assert history[bad.id]['failures']==1 and history[good.id]['success']==1
            assert w.engine.stage=='connected'
            w.toggle_connection();end=time.monotonic()+5
            while (w.engine.busy or w.engine.running) and time.monotonic()<end:app.processEvents();time.sleep(.01)
            assert not w.engine.running and not w.runtime.retry.isActive() and w.runtime.manual
        finally:w.close();app.processEvents()


def test_settings_lan_bypass_enforced_without_bypassing_verification(local_network):
    from nextapp.engine import connection_config
    from nextapp.settings_schema import defaults
    local_network=tuple(url.replace('localhost','127.0.0.1') for url in local_network)
    p=Profile('unreachable','ss','127.0.0.1',port(),'test',{'method':'aes-128-gcm'})
    hp,sp,mp=port(),port(),port();cfg=make_config(p,hp,sp,mp,True)
    with core(cfg) as proc:
        ready(hp,proc);assert proxy_probe(hp,local_network[1],timeout=2)>0
    s=defaults();s.update(http_port=hp,socks_port=sp,stats_port=mp,http_url=local_network[0],https_url=local_network[1],bypass=True)
    with core(connection_config(p,s)) as proc:
        ready(hp,proc)
        with pytest.raises(Exception):proxy_probe(hp,local_network[1],timeout=2)


def test_settings_manual_cancel_at_final_connection_gate(tmp_path,local_network,monkeypatch):
    from PySide6.QtWidgets import QApplication
    from nextapp.engine import Engine
    import nextapp.engine as module
    import types
    app=QApplication.instance() or QApplication([]);remote=port()
    cfg={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'test','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    with core(cfg) as proc:
        ready(remote,proc);engine=Engine(tmp_path);states=[];engine.state.connect(lambda state,note:states.append(state))
        def final_cancel(fmt):
            if engine.running and engine.busy:engine.cancel.set()
            return time.strftime(fmt)
        monkeypatch.setattr(module,'time',types.SimpleNamespace(monotonic=time.monotonic,strftime=final_cancel))
        p=Profile('local','ss','127.0.0.1',remote,'test',{'method':'aes-128-gcm'})
        s={'core':str(CORE),'mode':'Manual Proxy','http_port':port(),'socks_port':port(),'stats_port':port(),'https_url':local_network[1],'http_url':local_network[0]}
        try:
            engine.connect_profile(p,s);end=time.monotonic()+8
            while (engine.busy or 'Disconnected' not in states) and time.monotonic()<end:app.processEvents();time.sleep(.01)
            assert not engine.busy and not engine.running and engine.process is None and 'Disconnected' in states
        finally:engine.shutdown()


def test_real_service_checks_use_proxy_https_and_classify_status(local_network):
    from nextapp.service_checks import Service
    remote=port();cfg={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'service-test','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    p=Profile('local','ss','127.0.0.1',remote,'service-test',{'method':'aes-128-gcm'});hp,sp,mp=port(),port(),port()
    with core(cfg) as server,core(make_config(p,hp,sp,mp)) as client:
        ready(remote,server);ready(hp,client)
        for path,state in [('/','ok'),('/blocked','limited'),('/signin','limited'),('/rate','limited'),('/redirect','limited'),('/head-fallback','ok')]:
            result=actual_service_probe(Service('test','Local',local_network[1].rstrip('/')+path,'#fff','chat'),hp,2)
            assert result.state==state and result.latency>0,(path,result)
        slow=actual_service_probe(Service('slow','Local',local_network[1]+'slow','#fff','chat'),hp,.15);assert slow.state=='unknown' and 'Timed out' in slow.reason
        # The target is reachable directly, but a closed local proxy must still fail.
        failed=actual_service_probe(Service('test','Local',local_network[1],'#fff','chat'),port(),.2);assert failed.state=='unknown'


def test_real_https_profile_test_rejects_auth_failure(local_network):
    from nextapp.profile_testing import test_https
    from nextapp.settings_schema import defaults
    remote=port();cfg={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'valid-test-password','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    settings=defaults();settings.update(core=str(CORE),https_url=local_network[1],http_url=local_network[0],health_timeout=2)
    with core(cfg) as server:
        ready(remote,server);p=Profile('local','ss','127.0.0.1',remote,'valid-test-password',{'method':'aes-128-gcm'})
        result=test_https(p,settings,threading.Event());assert result.status=='Verified' and result.latency>0
        p.secret='wrong-test-password';failed=test_https(p,settings,threading.Event());assert failed.status!='Verified' and failed.latency is None


def test_real_server_switch_stops_previous_core_and_verifies_replacement(tmp_path,local_network):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from nextapp.ui import Window
    app=QApplication.instance() or QApplication([]);r1,r2=port(),port()
    def server_cfg(remote):return {'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'shadowsocks','settings':{'method':'aes-128-gcm','password':'switch-test','network':'tcp'}}],'outbounds':[{'protocol':'freedom'}]}
    with core(server_cfg(r1)) as first,core(server_cfg(r2)) as second:
        ready(r1,first);ready(r2,second);w=Window(tmp_path);w.notice=lambda _:None
        p1=Profile('first','ss','127.0.0.1',r1,'switch-test',{'method':'aes-128-gcm'});p2=Profile('second','ss','127.0.0.1',r2,'switch-test',{'method':'aes-128-gcm'})
        w.profiles=[p1,p2];w.selected=p1.id;w.settings.update(core=str(CORE),mode='Manual Proxy',http_port=port(),socks_port=port(),stats_port=port(),https_url=local_network[1],http_url=local_network[0],service_checks=False);w.populate()
        def wait(predicate):
            deadline=time.monotonic()+10
            while not predicate() and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
            assert predicate()
        try:
            w.manual_selection=True;w.toggle_connection();wait(lambda:w.status=='Connected' and not w.engine.busy);previous=w.engine.process
            w.table.selectRow(1);w.use_selected();wait(lambda:w.status=='Connected' and w.active_id==p2.id and not w.engine.busy)
            assert previous.poll() is not None and w.engine.process is not previous and w.latency_ms>0
            assert proxy_probe(w.settings['http_port'],local_network[1])>0
            w.toggle_connection();wait(lambda:not w.engine.running and not w.engine.busy);assert not w.switcher.pending
        finally:w.close();app.processEvents()


def test_real_subscription_auto_connect_uses_only_fresh_https_results(tmp_path, local_network):
    from PySide6.QtWidgets import QApplication
    from nextapp.ui import Window
    from nextapp.subscriptions import Subscription
    app = QApplication.instance() or QApplication([])
    remote = port()
    cfg = {'log': {'loglevel': 'none'}, 'inbounds': [{'listen': '127.0.0.1', 'port': remote, 'protocol': 'shadowsocks', 'settings': {'method': 'aes-128-gcm', 'password': 'auto-test', 'network': 'tcp'}}], 'outbounds': [{'protocol': 'freedom'}]}
    with core(cfg) as server:
        ready(remote, server)
        w = Window(tmp_path)
        source = Subscription('local test', 'https://example.invalid/source')
        profiles = [Profile(name, 'ss', '127.0.0.1', remote, secret, {'method': 'aes-128-gcm'}) for name, secret in [('invalid auth', 'wrong'), ('working A', 'auto-test'), ('working B', 'auto-test')]]
        for p in profiles:
            p.subscription_id = source.id
            p.latency = .1  # Deliberately misleading stale TCP results must be ignored.
            p.test_method = 'TCP'
        w.profiles, w.subscriptions = profiles, [source]
        w.settings.update(core=str(CORE), mode='Manual Proxy', automatic_tuning=False, health_timeout=2, concurrency=2, http_port=port(), socks_port=port(), stats_port=port(), https_url=local_network[1], http_url=local_network[0], service_checks=False)
        w.servers_page.select_group(source.id)
        try:
            w.use_selected()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                app.processEvents()
                if not w.test_busy and not w.switcher.pending and not w.engine.busy and w.engine.running:
                    break
                time.sleep(.01)
            assert not w.test_busy and w.test_completed == 3
            verified = [p for p in profiles if p.test_status == 'Verified']
            assert len(verified) == 2 and profiles[0].latency is None
            assert w.active_id == min(verified, key=lambda p: p.latency).id
            assert w.engine.running and proxy_probe(w.settings['http_port'], local_network[1]) > 0
        finally:
            w.force_quit = True
            w.close()
            app.processEvents()

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray required')
def test_apex_real_trojan_ws_tls_finalmask(local_network):
    """Real TLS/WS Trojan transport with the new array mask, no public server."""
    from urllib.parse import urlencode,quote
    from nextapp.profiles import parse_link
    cert=os.environ['SSL_CERT_FILE'];key=str(pathlib.Path(cert).with_name('key.pem'))
    remote,hp,sp,mp=port(),port(),port(),port()
    server={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'trojan','settings':{'clients':[{'password':'local-mask-fixture'}]},'streamSettings':{'network':'ws','security':'tls','tlsSettings':{'certificates':[{'certificateFile':cert,'keyFile':key}]},'wsSettings':{'path':'/mask'}}}],'outbounds':[{'protocol':'freedom'}]}
    masks={'tcp':[{'type':'fragment','settings':{'packets':'tlshello','lengths':['100','1'],'delays':['0'],'maxSplit':'3'}}]}
    params={'security':'tls','type':'ws','sni':'localhost','host':'localhost','path':'/mask','fp':'unsafe','cs':'TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256','fm':json.dumps(masks),'fragment':'null,null,tlshello,0'}
    p=parse_link(f'trojan://local-mask-fixture@127.0.0.1:{remote}?'+urlencode(params,quote_via=quote))
    with core(server) as srv:
        ready(remote,srv)
        cfg=make_config(p,hp,sp,mp)
        cfg['outbounds'][0]['streamSettings']['tlsSettings']['certificates']=[{'certificateFile':cert,'usage':'verify'}]
        with core(cfg) as client:
            ready(hp,client)
            assert proxy_probe(hp,local_network[1],timeout=5)>0

@pytest.mark.skipif(not CORE.exists(),reason='Bundled Xray required')
def test_telegram_socks_profile_real_https_and_auth_failure(local_network):
    from nextapp.profiles import parse_link
    remote,hp,sp,mp=port(),port(),port(),port()
    server={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':remote,'protocol':'socks','settings':{'auth':'password','accounts':[{'user':'local-fixture','pass':'local-pass'}],'udp':True}}],'outbounds':[{'protocol':'freedom'}]}
    with core(server) as srv:
        ready(remote,srv)
        for password,success in [('local-pass',True),('wrong-pass',False)]:
            profile=parse_link(f'tg://socks?server=127.0.0.1&port={remote}&user=local-fixture&pass={password}')
            with core(make_config(profile,hp,sp,mp)) as client:
                ready(hp,client)
                if success:assert proxy_probe(hp,local_network[1],timeout=3)>0
                else:
                    with pytest.raises(Exception):proxy_probe(hp,local_network[1],timeout=2)
