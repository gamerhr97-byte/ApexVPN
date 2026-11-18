import os,pathlib,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

@pytest.fixture(autouse=True)
def release_test_clipboard_mime():
    """Test-created MIME objects must be released before offscreen Qt shutdown."""
    yield
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance()
    if app is not None:
        app.clipboard().clear()
        app.processEvents()
        from PySide6.QtCore import QEvent
        app.sendPostedEvents(None,QEvent.DeferredDelete)

@pytest.fixture(autouse=True)
def no_external_service_probes(monkeypatch):
    """All site traffic in tests must be explicitly routed to controlled fixtures."""
    from nextapp import service_checks
    def isolated(service,port,timeout=4):
        return service_checks.ServiceResult(service.key,'failed',reason='External requests disabled in test fixture')
    monkeypatch.setattr(service_checks,'probe_service',isolated)
    monkeypatch.setattr(service_checks,'connect_service',isolated)


@pytest.fixture(autouse=True)
def no_release_popup_during_tests(monkeypatch):
    from nextapp import release_notes
    monkeypatch.setattr(release_notes, 'show_release_notes', lambda *args, **kwargs: None)


@pytest.fixture(autouse=True)
def no_public_startup_updates(monkeypatch):
    from nextapp import free_sources
    from nextapp.ui import Window
    monkeypatch.setattr(free_sources,'install_presets',lambda subscriptions,settings:False)
    monkeypatch.setattr(Window,'refresh_on_launch',lambda self:None)

_QT_APP=None

@pytest.fixture(scope='session',autouse=True)
def qt_application_lifetime():
    """Keep QApplication alive for the process, as the pytest-qt harness does."""
    global _QT_APP
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QEvent
    _QT_APP=QApplication.instance() or QApplication([])
    _QT_APP.setQuitOnLastWindowClosed(False)
    yield _QT_APP
    _QT_APP.clipboard().clear()
    _QT_APP.sendPostedEvents(None,QEvent.DeferredDelete)
