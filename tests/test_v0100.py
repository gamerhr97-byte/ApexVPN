"""Persistence, default domestic bypass and source control regression tests."""
import pathlib
import time

from PySide6.QtWidgets import QApplication, QListWidget, QPushButton, QMenu

from nextapp.ui import Window
from nextapp.settings_schema import defaults, migrate
from nextapp.storage import Store
from nextapp.direct_routing import windows_bypass
from nextapp.proxy import ProxyLease
from nextapp.subscriptions import Subscription
from test_proxy_storage import FakeWinInet
from test_e2e import core, port, ready, local_network


def app():
    return QApplication.instance() or QApplication([])


def test_utf8_settings_read_is_explicit_for_windows_locales(tmp_path, monkeypatch):
    store = Store(tmp_path)
    value = dict(defaults(), core='C:/کاربر/هسته/xray.exe', selected_group='اشتراک')
    store.save_settings(value)
    old = pathlib.Path.read_text
    encodings = []
    def read(path, *args, **kwargs):
        if path.name == 'settings.json': encodings.append(kwargs.get('encoding'))
        return old(path, *args, **kwargs)
    monkeypatch.setattr(pathlib.Path, 'read_text', read)
    assert store.load_settings() == value and encodings == ['utf-8-sig']


def test_default_ir_upgrade_once_and_explicit_disable_survives():
    assert defaults()['direct_enabled'] and defaults()['direct_ir']
    upgraded = migrate({'direct_enabled':False, 'direct_ir':False, 'direct_domains':'example.com'})
    assert upgraded['direct_enabled'] and upgraded['direct_ir']
    assert upgraded['direct_domains'] == 'example.com'
    upgraded['direct_enabled'] = False
    assert not migrate(upgraded)['direct_enabled']


def test_windows_bypass_and_exact_restoration(tmp_path):
    settings = dict(defaults(), direct_domains='https://adliran.ir/\nhttps://example.com/path')
    bypass = windows_bypass(settings)
    assert '*.ir' in bypass.split(';')
    assert 'example.com' in bypass.split(';') and '*.example.com' in bypass.split(';')
    assert 'https://' not in bypass and '/path' not in bypass
    adapter = FakeWinInet(); before = adapter.read()
    lease = ProxyLease(tmp_path, adapter)
    lease.enable(2080, bypass)
    assert adapter.read()['bypass'] == bypass
    lease.restore()
    assert adapter.read() == before
    assert windows_bypass(dict(settings, direct_enabled=False)) == '<local>'


def test_saved_active_network_edits_do_not_mutate_running_snapshot(tmp_path):
    qt = app(); w = Window(tmp_path)
    try:
        active = dict(w.settings)
        w.engine.settings = dict(active)
        w.engine.running = True
        page = w.settings_page
        page.controls['direct_domains'].setPlainText('https://adliran.ir/')
        page.controls['http_port'].setValue(3080)
        page.apply()
        assert w.store.load_settings()['http_port'] == 3080
        assert w.engine.settings['http_port'] == active['http_port']
        assert w.engine.settings['direct_domains'] == active['direct_domains']
        assert 'reconnect' in page.status.text().lower()
    finally:
        w.engine.running = False; w.close(); qt.processEvents()
    reopened = Window(tmp_path)
    try:
        assert reopened.settings['http_port'] == 3080
        assert reopened.settings['direct_domains'] == 'https://adliran.ir/'
    finally: reopened.close(); qt.processEvents()


def test_routing_form_autosaves_without_losing_an_advanced_port_draft(tmp_path):
    qt = app(); w = Window(tmp_path)
    try:
        page = w.settings_page
        page.controls['http_port'].setValue(3080)
        page.controls['direct_domains'].setPlainText('https://example.ir')
        page.autosave()
        assert w.store.load_settings()['direct_domains'] == 'https://example.ir'
        assert w.store.load_settings()['http_port'] == defaults()['http_port']
        assert page.controls['http_port'].value() == 3080 and page.dirty
        page.apply()
        assert w.store.load_settings()['http_port'] == 3080
    finally: w.close(); qt.processEvents()


def test_source_sheet_preview_selection_copy_and_restored_group(tmp_path):
    qt = app(); w = Window(tmp_path)
    source = Subscription('Source A', 'https://example.invalid/a', metadata={
        'upload':10, 'download':20, 'total':100})
    w.subscriptions = [source]; w.store.save_catalog([], w.subscriptions); w.populate()
    try:
        picker = w.servers_page.groups
        picker.showPopup(); qt.processEvents()
        listing = picker.sheet.findChild(QListWidget)
        listing.setCurrentRow(picker.findData(source.id))
        assert w.servers_page.group == 'local'
        menu = picker.sheet.findChild(QMenu)
        next(a for a in menu.actions() if a.text()=='Copy subscription link').trigger()
        assert QApplication.clipboard().text()==source.url
        assert w.servers_page.group==source.id
        assert w.settings['selected_group']==source.id
    finally: w.close(); qt.processEvents()
    w = Window(tmp_path)
    try: assert w.servers_page.group==source.id
    finally: w.close(); qt.processEvents()


def test_real_default_ir_route_without_manually_enabling_exceptions(local_network):
    from nextapp.engine import connection_config
    from nextapp.profiles import Profile
    from nextapp.network import proxy_probe
    import pytest
    s = dict(defaults(), http_port=port(), socks_port=port(), stats_port=port(),
             https_url='https://verification.invalid', http_url='http://verification.invalid')
    p = Profile('Unavailable proxy', 'ss', '127.0.0.1', port(), 'ephemeral', {'method':'aes-128-gcm'})
    cfg = connection_config(p, s)
    cfg['dns'] = {'hosts':{'judicial-fixture.ir':'127.0.0.1', 'judicial-fixture.ir.evil.test':'127.0.0.1'}}
    cfg['outbounds'][1]['settings'] = {'domainStrategy':'UseIPv4'}
    target_port = local_network[0].split(':')[-1].strip('/')
    with core(cfg) as process:
        ready(s['http_port'], process)
        assert proxy_probe(s['http_port'], f'http://judicial-fixture.ir:{target_port}/', timeout=2)>0
        with pytest.raises(Exception):
            proxy_probe(s['http_port'], f'http://judicial-fixture.ir.evil.test:{target_port}/', timeout=1)


def test_diagnostics_keep_live_ports_and_current_display_preferences():
    from types import SimpleNamespace
    from nextapp.settings_policy import session_preferences, pending_network_changes
    active = dict(defaults(), http_port=2080, direct_domains='old.example')
    saved = dict(active, http_port=3080, direct_domains='new.example', theme='Dark')
    owner = SimpleNamespace(settings=saved, engine=SimpleNamespace(running=True, settings=active))
    effective = session_preferences(owner)
    assert effective['http_port']==2080 and effective['direct_domains']=='old.example'
    assert effective['theme']=='Dark' and pending_network_changes(owner)
    owner.engine.running = False
    assert session_preferences(owner)['http_port']==3080 and not pending_network_changes(owner)


def test_network_save_does_not_restyle_entire_window(tmp_path, monkeypatch):
    qt = app(); w = Window(tmp_path)
    try:
        repaints = []
        monkeypatch.setattr(w, 'apply_theme', lambda: repaints.append(True))
        page = w.settings_page
        page.controls['direct_domains'].setPlainText('example.ir')
        page.autosave()
        assert w.store.load_settings()['direct_domains'] == 'example.ir'
        assert repaints == []
        page.controls['theme'].setCurrentIndex(page.controls['theme'].findData('Dark'))
        page.autosave()
        assert repaints == [True]
    finally: w.close(); qt.processEvents()
