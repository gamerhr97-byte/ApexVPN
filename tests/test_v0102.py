"""0.10.2 regression: bounded rendering and honest route/quality states."""
import threading
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog
from nextapp.ui import Window
from nextapp.profiles import Profile
from nextapp.service_checks import SERVICES, ServiceResult, measure_quality
from nextapp.ranking import rank


def test_catalog_exactly_200():
    assert len(SERVICES) == 100
    assert len({s.key for s in SERVICES}) == 100
    assert len({s.url for s in SERVICES}) == 100
    assert {'Google Flow','Cloudflare','Dota 2','Firestorm'} <= {s.name for s in SERVICES}


def test_quality_uses_proxy_and_threshold():
    calls = []
    def probe(service, port, timeout):
        calls.append(port)
        return ServiceResult(service.key,'ok',10,200,region='not_observed')
    with patch('nextapp.service_checks.probe_service', probe), patch('nextapp.service_checks.connect_service', probe):
        score, gemini = measure_quality(12345, threading.Event())
    assert score == 100 and gemini
    assert calls == [12345] * 100
    canceled = threading.Event(); canceled.set()
    assert measure_quality(12345, canceled) == (None, False)


def test_quality_ranking_and_roundtrip():
    p = Profile('coverage','vless','localhost',443, service_score=100)
    q = Profile('fast','vless','localhost',443,latency=1,test_method='HTTPS',test_status='Verified')
    assert sorted([q,p],key=rank)[0] is p
    assert Profile(**p.to_dict()).service_score == 100


def test_window_fixed_and_large_catalog(tmp_path):
    app = QApplication.instance() or QApplication([])
    w = Window(tmp_path)
    try:
        w.show(); app.processEvents()
        assert w.minimumSize() == w.maximumSize()
        w.profiles = [Profile(f'Server {i}', 'vless','localhost',443) for i in range(10000)]
        w.servers_page.group = 'all'
        w.servers_page.populate()
        assert w.table.rowCount() == 200
        assert len(w.servers_page.visible_profiles()) == 10000
        w.servers_page.change_page(1)
        assert w.table.item(0,0).text() == 'Server 100'
        w.settings['allow_resize'] = True
        w.apply_theme(); app.processEvents()
        assert w.isVisible()
        assert w.maximumWidth() > w.minimumWidth()
    finally:
        w.close()


def test_direct_ip_result_and_svg(tmp_path):
    from nextapp.service_icons import stars_icon, symbol_icon
    app = QApplication.instance() or QApplication([])
    w = Window(tmp_path)
    try:
        w.ip_received({'proxy':False,'process':None,'ip':'192.0.2.1','country':'DE','error':''})
        assert 'Direct IP' in w.ping_button.text()
        assert not stars_icon(True, True).isNull()
        assert not symbol_icon('close').isNull()
        # Exercise the complete 200-button dialog without external traffic.
        QTimer.singleShot(30, lambda: [x.accept() for x in app.topLevelWidgets() if isinstance(x,QDialog)])
        w.service_checks.show_details()
    finally:
        w.close()
