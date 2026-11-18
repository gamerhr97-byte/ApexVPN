"""Regression checks for the eleven reported 0.8.0 usability failures."""

import base64
import json
import pathlib
import subprocess
import threading
import time

import pytest
from PySide6.QtCore import Qt, QEvent, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QListWidget

from nextapp.direct_routing import domains
from nextapp.navigation import History
from nextapp.network import SubscriptionText
from nextapp.profiles import parse_link, make_config, ProfileError
from nextapp.subscription_loader import load_bundle, subscription_url
from nextapp.subscriptions import Subscription
from nextapp.ui import Window
from nextapp.release_notes import show_release_notes as actual_release_notes
from test_e2e import CORE, core, port, ready, local_network


def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path):
    qt_app = app()
    w = Window(tmp_path)
    w.show()
    app().processEvents()
    yield w
    w.force_quit = True
    w.close()
    app().processEvents()


def test_urls_are_normalized_in_direct_exceptions(window):
    assert domains('https://torob.com\nhttps://www.whatismyip.com/path?q=x#frag\nTOROB.COM') == [
        'torob.com', 'www.whatismyip.com']
    page = window.settings_page
    page.controls['direct_enabled'].setChecked(True)
    page.controls['direct_domains'].setPlainText('https://torob.com\nhttps://www.whatismyip.com')
    page.apply()
    assert window.settings['direct_enabled']
    from nextapp.engine import connection_config
    p = parse_link('trojan://test@example.invalid:443')
    rules = connection_config(p, window.settings)['routing']['rules']
    assert any(r.get('domain') == ['domain:ir','domain:torob.com','domain:www.whatismyip.com'] for r in rules)


def test_main_connect_runs_current_group_ignores_implicit_first_and_search(window, monkeypatch):
    import nextapp.group_testing as group
    from nextapp.profile_testing import ProfileTest
    sub = Subscription('Group', 'https://feed.invalid/root')
    profiles = [parse_link(f'trojan://test@example.invalid:443#{n}') for n in ('first','fastest','outside')]
    profiles[0].subscription_id = profiles[1].subscription_id = sub.id
    window.profiles, window.subscriptions, window.selected = profiles, [sub], profiles[0].id
    window.servers_page.select_group(sub.id)
    window.servers_page.search.setText('first')
    calls, switched = [], []
    gate = threading.Event()

    def probe(p, settings, cancel):
        calls.append(p.id)
        if p is profiles[1]: gate.wait(3)
        return ProfileTest('HTTPS', 'Verified', 20 if p is profiles[1] else 200)

    monkeypatch.setattr(group, 'test_https', probe)
    monkeypatch.setattr(window.switcher, 'request', lambda p: switched.append(p.id))
    window.toggle_connection()
    end = time.monotonic() + 3
    while not switched and time.monotonic() < end:
        app().processEvents(); time.sleep(.01)
    assert switched == [profiles[0].id]
    gate.set()
    while window.test_busy and time.monotonic() < end:
        app().processEvents(); time.sleep(.01)
    assert not window.test_busy and switched[-1] == profiles[1].id
    assert set(calls) == {p.id for p in profiles[:2]}
    window.manual_selection = True
    manual = []
    monkeypatch.setattr(window.runtime, 'connect_to', lambda p: manual.append(p.id))
    window.toggle_connection()
    assert manual == [profiles[0].id]


def test_subscription_bundle_headers_fragments_cycles_and_dedup():
    root = 'https://feed.invalid/root'
    child = 'https://feed.invalid/child'
    link = 'trojan://test@example.invalid:443#fixture'
    calls = []
    documents = {root: SubscriptionText('#profile-title: Mahsa\n#subscription-userinfo: upload=1; download=2; total=100; expire=2000000000\n'+child+'#child\n'+child),
                 child: SubscriptionText(base64.b64encode((link+'\n'+link+'\n'+root).encode()).decode())}
    def fetch(url, proxy_port=None):
        calls.append(url)
        return documents[url]
    profiles, metadata, title = load_bundle(root+'#مهسا', fetch=fetch)
    assert len(profiles) == 1 and calls == [root, child]
    assert title == 'Mahsa' and metadata['total'] == 100
    assert subscription_url(root+'#label') == root


def test_subscription_bundle_limits_cancellation_and_failure():
    with pytest.raises(ProfileError):
        load_bundle('https://feed.invalid/0', fetch=lambda u, **kw: 'https://feed.invalid/'+str(int(u.rsplit('/',1)[1])+1))
    canceled = threading.Event(); canceled.set()
    with pytest.raises(ProfileError, match='canceled'):
        load_bundle('https://feed.invalid/', cancel=canceled, fetch=lambda *a, **kw: pytest.fail())
    with pytest.raises(ProfileError):
        subscription_url('https://user:pass@feed.invalid/')


def test_picker_shows_actual_provider_usage_expiry_and_light_theme(window):
    sub = Subscription('Sample provider', 'https://feed.invalid/', metadata={
        'upload':0,'download':1024,'total':4096,'expire':2000000000})
    window.subscriptions = [sub]
    window.populate()
    picker = window.servers_page.groups
    picker.showPopup(); app().processEvents()
    try:
        text = '\n'.join(picker.sheet.findChild(QListWidget).item(i).text()
                         for i in range(picker.count()))
        assert '25.0%' in text and '2033-' in text
        assert '#F8FAFF' in picker.sheet.styleSheet() and picker.sheet.width() < window.width()
        assert isinstance(window.table.itemDelegate(), __import__('nextapp.server_page',fromlist=['CleanSelectionDelegate']).CleanSelectionDelegate)
    finally: picker.sheet.reject()


def test_back_forward_settings_categories_mouse_and_history_branch(window):
    w = window
    w.navigate(1); w.navigate(3); w.settings_page.open_category(13)
    w.go_back()
    assert w.current == 3 and w.settings_page.deck.currentIndex() == 0
    w.go_back(); assert w.current == 1
    w.go_forward(); assert w.current == 3 and w.settings_page.deck.currentIndex() == 0
    w.go_forward(); assert w.settings_page.stack.currentIndex() == 13
    event = QMouseEvent(QEvent.MouseButtonRelease, QPointF(2,2), QPointF(2,2),
                        Qt.BackButton, Qt.NoButton, Qt.NoModifier)
    QApplication.sendEvent(w.settings_page, event)
    assert w.settings_page.deck.currentIndex() == 0
    event = QMouseEvent(QEvent.MouseButtonRelease, QPointF(2,2), QPointF(2,2),
                        Qt.ForwardButton, Qt.NoButton, Qt.NoModifier)
    QApplication.sendEvent(w.settings_page, event)
    assert w.settings_page.deck.currentIndex() == 1
    h = History(); h.push((1,None)); h.push((3,13)); h.step(-1); h.push((0,None))
    assert h.step(1) is None


def test_settings_notifications_do_not_open_native_messagebox(window, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox,'information',lambda *a: pytest.fail('Blocking notice'))
    window.settings_page.message('Saved')
    assert window.toast.text() == 'Saved' and window.toast.timer.interval() == 1800
    assert '#DCFCE7' in window.toast.styleSheet()


@pytest.mark.parametrize('transport', ['grpc', 'xhttp', 'httpupgrade'])
def test_real_core_accepts_expanded_transport_mapping(transport):
    # Ephemeral fixture credentials/keys. Never contact the user's server.
    import re
    keys = subprocess.check_output([str(CORE),'x25519'],text=True)
    public = re.search(r'Password \(PublicKey\):\s*(\S+)', keys).group(1)
    security = 'tls' if transport == 'httpupgrade' else 'reality'
    query = f'type={transport}&security={security}&headerType=none&sni=example.com'
    if security == 'reality': query += '&pbk='+public+'&sid=1234'
    query += '&serviceName=fixture&mode=gun' if transport == 'grpc' else '&path=%2Ffixture'
    p = parse_link('vless://11111111-1111-4111-8111-111111111111@example.invalid:443?'+query)
    cfg = make_config(p,port(),port(),port())
    result = subprocess.run([str(CORE),'run','-test','-c','stdin:'], input=json.dumps(cfg).encode(),
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    assert result.returncode == 0, result.stdout.decode()


@pytest.mark.parametrize('transport', ['grpc','xhttp','httpupgrade'])
def test_real_tls_transport_traffic(local_network, tmp_path, transport):
    import ssl
    # local_network creates a trusted test CA; use its cert for an Xray TLS server.
    cert, key = tmp_path/'cert.pem', tmp_path/'key.pem'
    remote, hp, sp, mp = port(),port(),port(),port()
    uid = '11111111-1111-4111-8111-111111111111'
    stream = {'network':transport,'security':'tls','tlsSettings':{
        'certificates':[{'certificateFile':str(cert),'keyFile':str(key)}]}}
    if transport == 'grpc': stream['grpcSettings']={'serviceName':'fixture'}
    elif transport == 'xhttp': stream['xhttpSettings']={'path':'/fixture'}
    else: stream['httpupgradeSettings']={'path':'/fixture'}
    server = {'log':{'loglevel':'error'},'inbounds':[{'listen':'127.0.0.1','port':remote,
        'protocol':'vless','settings':{'decryption':'none','clients':[{'id':uid}]},
        'streamSettings':stream}],'outbounds':[{'protocol':'freedom'}]}
    query = f'type={transport}&security=tls&sni=localhost&headerType=none'
    query += '&serviceName=fixture&mode=gun' if transport == 'grpc' else '&path=%2Ffixture'
    p = parse_link(f'vless://{uid}@127.0.0.1:{remote}?'+query)
    from nextapp.network import proxy_probe
    with core(server) as srv:
        ready(remote,srv)
        with core(make_config(p,hp,sp,mp)) as client:
            ready(hp,client)
            assert proxy_probe(hp,local_network[1],timeout=6)>0

@pytest.mark.parametrize('transport', ['grpc','xhttp'])
def test_real_reality_transport_traffic(local_network, tmp_path, transport):
    import re, ssl
    from http.server import ThreadingHTTPServer
    from test_e2e import Handler
    from nextapp.network import proxy_probe
    keys = subprocess.check_output([str(CORE),'x25519'], text=True)
    private = re.search(r'PrivateKey:\s*(\S+)',keys).group(1)
    public = re.search(r'Password \(PublicKey\):\s*(\S+)',keys).group(1)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.set_alpn_protocols(['h2','http/1.1'])
    context.load_cert_chain(str(tmp_path/'cert.pem'),str(tmp_path/'key.pem'))
    class CamouflageHandler(Handler):
        def setup(self):
            self.request = context.wrap_socket(self.request, server_side=True)
            super().setup()
    camouflage = ThreadingHTTPServer(('127.0.0.1',0),CamouflageHandler)
    threading.Thread(target=camouflage.serve_forever,daemon=True).start()
    remote,hp,sp,mp = port(),port(),port(),port()
    uid='11111111-1111-4111-8111-111111111111'
    stream={'network':transport,'security':'reality','realitySettings':{
        'dest':f'127.0.0.1:{camouflage.server_port}','serverNames':['localhost'],
        'privateKey':private,'shortIds':['1234']}}
    if transport=='grpc':stream['grpcSettings']={'serviceName':'fixture'}
    else:stream['xhttpSettings']={'path':'/fixture'}
    server={'log':{'loglevel':'error'},'inbounds':[{'listen':'127.0.0.1','port':remote,
        'protocol':'vless','settings':{'decryption':'none','clients':[{'id':uid}]},
        'streamSettings':stream}],'outbounds':[{'protocol':'freedom'}]}
    query=f'type={transport}&security=reality&headerType=none&sni=localhost&fp=chrome&pbk={public}&sid=1234'
    query+='&mode=gun&serviceName=fixture' if transport=='grpc' else '&path=%2Ffixture'
    p=parse_link(f'vless://{uid}@127.0.0.1:{remote}?'+query)
    try:
        server['log']={'loglevel':'debug' ,'error':str(tmp_path/'reality-server.log')}
        cfg=make_config(p,hp,sp,mp);cfg['log']={'loglevel':'debug','error':str(tmp_path/'reality-client.log')}
        with core(server) as srv:
            ready(remote,srv)
            with core(cfg) as client:
                ready(hp,client)
                assert proxy_probe(hp,local_network[1],timeout=20)>0
    finally:
        camouflage.shutdown();camouflage.server_close()


def test_release_notes_are_acknowledged_once_and_survive_migration(window):
    from nextapp.branding import VERSION
    from nextapp.settings_schema import migrate
    from PySide6.QtWidgets import QPushButton
    actual_release_notes(window)
    app().processEvents()
    dialog = window.release_dialog
    assert dialog.isVisible()
    next(button for button in dialog.findChildren(QPushButton) if button.text() in ('Got it','متوجه شدم')).click()
    app().processEvents()
    assert window.settings['release_seen'] == VERSION
    assert migrate(window.store.load_settings())['release_seen'] == VERSION
    actual_release_notes(window)
    assert window.release_dialog is None
