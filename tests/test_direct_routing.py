"""Exception boundaries, persistence, native UI and real pinned-core traffic."""

import json
import pathlib
import subprocess
import sys

import pytest

from nextapp.direct_routing import domains, applications
from nextapp.engine import connection_config
from nextapp.settings_schema import defaults, validate, migrate, export_preferences
from nextapp.profiles import Profile
from nextapp.network import proxy_probe
from test_e2e import core, port, ready, CORE, local_network


def settings(**extra):
    result = defaults()
    result.update(direct_enabled=False, http_port=port(), socks_port=port(), stats_port=port(),
                  https_url='https://verification.invalid/', http_url='http://verification.invalid/')
    result.update(extra)
    return result


def profile():
    return Profile('Unavailable upstream', 'ss', '127.0.0.1', port(), 'ephemeral',
                   {'method': 'aes-128-gcm'})


def test_domain_normalization_and_duplicates():
    assert domains('EXAMPLE.ir.\nexample.ir\nمثال.ir') == ['example.ir', 'xn--mgbh0fb.ir']
    assert applications('C:\\Games\\Test Game\\game.exe\ngame.exe\ngame.exe') == [
        'C:/Games/Test Game/game.exe', 'game']


@pytest.mark.parametrize('value', ['https://user:pass@example.ir', '*.ir', 'ir', 'bad..ir',
    'example.ir/path', 'user@site.ir', '127.0.0.1', 'domain:example.ir',
    'example.ir;evil.com', 'a'*64+'.ir', 'a.ir\x00', '\n'.join(f'x{i}.ir' for i in range(65))])
def test_reject_invalid_domains(value):
    with pytest.raises(ValueError): domains(value)


@pytest.mark.parametrize('value', ['self/', 'xray/', 'C:/Games/', '../game.exe',
    'C:/Games/../game.exe', 'C:/Games/*.exe', 'C:/game.exe:stream', 'game.bat',
    '//server/share/game.exe', 'C:/game.exe\x00', '/usr/bin/game.exe'])
def test_reject_invalid_applications(value):
    with pytest.raises(ValueError): applications(value)


def test_explicit_apply_defaults_and_migration():
    from nextapp.settings_policy import SAFE_AUTO_KEYS, auto_candidate
    s = defaults()
    assert s['direct_enabled'] and s['direct_ir']
    s['direct_enabled'] = False
    draft = dict(s, direct_enabled=True, direct_domains='example.ir', direct_apps='game.exe')
    assert validate(draft)['direct_apps'] == 'game.exe'
    assert migrate(draft)['direct_domains'] == 'example.ir'
    assert migrate(draft)['direct_apps'] == 'game.exe'
    assert migrate(dict(draft, direct_domains='*.ir'))['direct_domains'] == ''
    assert 'direct_apps' not in export_preferences(draft)['settings']
    assert not {'direct_enabled', 'direct_ir', 'direct_domains', 'direct_apps'} & SAFE_AUTO_KEYS
    assert auto_candidate(s, draft)[0]['direct_enabled'] is False


def test_disabled_routes_and_priority():
    p = profile()
    assert 'routing' not in connection_config(p, settings(direct_domains='example.ir'))
    cfg = connection_config(p, settings(direct_enabled=True, bypass=True, direct_apps='game.exe'))
    rules = cfg['routing']['rules']
    assert rules[0]['outboundTag'] == 'proxy'
    assert rules[-3]['domain'] == ['domain:ir']
    assert rules[-2]['process'] == ['game']
    assert rules[-1]['outboundTag'] == 'direct' and 'ip' in rules[-1]
    assert all(i['sniffing']['routeOnly'] for i in cfg['inbounds'])
    assert any(r.get('domain') == ['full:api.ipify.org'] and r['outboundTag']=='proxy' for r in rules)


@pytest.mark.skipif(not CORE.exists(), reason='Real Xray required')
def test_real_domain_suffix_boundaries_and_proxy_only_verification(local_network):
    s = settings(direct_enabled=True, direct_domains='custom.test')
    cfg = connection_config(profile(), s)
    names = ['site.ir', 'sub.site.ir', 'custom.test', 'sub.custom.test',
             'site.ir.evil.test', 'notcustom.test', 'verification.invalid']
    cfg['dns'] = {'hosts': {name: '127.0.0.1' for name in names}}
    cfg['outbounds'][1]['settings'] = {'domainStrategy': 'UseIPv4'}
    target_port = local_network[0].split(':')[-1].strip('/')
    with core(cfg) as proc:
        ready(s['http_port'], proc)
        for name in names[:4]:
            assert proxy_probe(s['http_port'], f'http://{name}:{target_port}/', timeout=2) > 0
        for name in names[4:]:
            with pytest.raises(Exception):
                proxy_probe(s['http_port'], f'http://{name}:{target_port}/', timeout=1)


@pytest.mark.skipif(not CORE.exists() or sys.platform != 'linux', reason='Linux local-process integration')
def test_real_process_route_and_no_proxy_fallback(local_network, tmp_path):
    # Windows-style EXE name goes through the exact same parser; core strips suffix.
    exe = pathlib.Path('/proc/self/comm').read_text().strip()
    s = settings(direct_enabled=True, direct_ir=False, direct_apps=exe+'.exe')
    cfg = connection_config(profile(), s)
    accepted = subprocess.run([str(CORE), 'run', '-test', '-c', 'stdin:'],
        input=json.dumps(cfg).encode(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert accepted.returncode == 0
    log = tmp_path / 'process-errors.log'
    cfg['log']['error'] = str(log)
    with core(cfg) as proc:
        ready(s['http_port'], proc)
        try:
            assert proxy_probe(s['http_port'], local_network[0], timeout=3) > 0
        except Exception:
            # This host blocks netlink interface queries. Never claim a process match.
            if log.exists() and 'netlinkrib: operation not permitted' in log.read_text():
                pytest.skip('Host sandbox blocks Xray process lookup via netlink')
            raise
        assert proxy_probe(s['http_port'], local_network[1], timeout=3) > 0
    cfg['routing']['rules'][-1]['process'] = ['nonexistent-shadowbox-test-process']
    with core(cfg) as proc:
        ready(s['http_port'], proc)
        with pytest.raises(Exception): proxy_probe(s['http_port'], local_network[0], timeout=1)


def test_section14_editor_and_dimensions(tmp_path):
    from PySide6.QtWidgets import QApplication
    from nextapp.ui import Window
    app = QApplication.instance() or QApplication([])
    window = Window(tmp_path)
    window.settings['language'] = 'fa'
    window.current = 3
    window.rebuild()
    window.show()
    try:
        page = window.settings_page
        before = window.size()
        page.open_category(13)
        app.processEvents()
        assert page.nav.count() == 15 and not page.nav.item(13).icon().isNull()
        assert window.size() == before
        page.controls['direct_domains'].setPlainText('example.ir')
        page.controls['direct_apps'].setPlainText('game.exe')
        page.controls['direct_enabled'].setChecked(True)
        assert page.values()['direct_apps'] == 'game.exe'
        assert window.settings['direct_domains'] == ''
        page.load_values(defaults())
        assert page.controls['direct_domains'].toPlainText() == ''
        page.controls['direct_enabled'].setChecked(True)
        page.controls['direct_apps'].setPlainText('game.exe')
        page.apply()
        assert window.settings['direct_enabled'] and window.settings['direct_apps']=='game.exe'
        window.grab().save(str(tmp_path / 'section14.png'))
    finally:
        window.close()
        app.processEvents()


def test_lookup_failure_emits_one_safe_warning(tmp_path):
    import io, types
    from PySide6.QtWidgets import QApplication
    from nextapp.engine import Engine
    app = QApplication.instance() or QApplication([])
    engine = Engine(tmp_path)
    warning = []
    engine.routing_warning.connect(lambda: warning.append(True))
    process = types.SimpleNamespace(stdout=io.BytesIO(
        b'Unables to find local process name: private-name\n' * 2))
    engine.process = process
    try:
        engine._read_core(process)
        assert warning == [True] and engine.core_fault is None
    finally:
        engine.process = None
        engine.shutdown()


def test_old_cores_cannot_silently_ignore_process_exceptions():
    from nextapp.direct_routing import check_process_core
    from nextapp.profiles import Unsupported
    s = settings(direct_enabled=True, direct_apps='game.exe')
    with pytest.raises(Unsupported): check_process_core(b'Xray 1.8.24', s)
    with pytest.raises(Unsupported): check_process_core(b'unknown', s)
    check_process_core(b'Xray 26.3.27 (Xray)', s)
    check_process_core(b'Xray 26.4.1 (Xray)', s)
    check_process_core(b'Xray 1.8.24', dict(s, direct_enabled=False))
