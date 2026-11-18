import threading
import time
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLineEdit,
    QPlainTextEdit,
    QMessageBox,
    QScrollArea,
    QDialogButtonBox,
)

from nextapp.ui import Window
from nextapp.profiles import parse_link
from nextapp.subscriptions import Subscription
from nextapp.profile_testing import ProfileTest
from nextapp.settings_schema import defaults, migrate
from nextapp.bootstrap import hardware_defaults


def app():
    return QApplication.instance() or QApplication([])


def wait(condition, seconds=3):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not condition():
        app().processEvents()
        time.sleep(0.01)
    assert condition()


def catalog(w):
    sub = Subscription("First", "https://example.invalid/private-sub")
    other = Subscription("Second", "https://example.invalid/second")
    profiles = [
        parse_link(f"trojan://private@example.invalid:443?security=tls#{name}")
        for name in ("slow", "fast", "timeout", "outside")
    ]
    for p in profiles[:3]:
        p.subscription_id = sub.id
    profiles[-1].subscription_id = other.id
    w.profiles, w.subscriptions = profiles, [sub, other]
    w.servers_page.select_group(sub.id)
    return sub, other, profiles


@pytest.fixture
def window(tmp_path):
    a = app()
    w = Window(tmp_path)
    w.show()
    a.processEvents()
    yield w
    w.force_quit = True
    w.close()
    a.processEvents()


def test_compact_home_has_no_scroll_and_preserves_frame(window):
    w = window
    for width, height in [(420, 660), (468, 740)]:
        w.resize(width, height)
        w.navigate(0)
        app().processEvents()
        assert not isinstance(w.stack.widget(0), QScrollArea)
        assert w.dashboard.minimumSizeHint().height() <= w.dashboard.height()
        assert sum(tile.isVisible() for tile in w.service_buttons.values()) == 3
        for key in ("chatgpt", "gemini", "telegram"):
            tile = w.service_buttons[key]
            assert tile.isVisible() and tile.mapTo(w.dashboard, tile.rect().bottomRight()).y() < w.dashboard.height()
        before = w.size()
        w.navigate(1)
        w.navigate(3)
        app().processEvents()
        assert w.size() == before


def test_live_progress_first_verified_then_fastest_fresh_only(window, monkeypatch):
    import nextapp.group_testing as module

    w = window
    sub, other, profiles = catalog(w)
    gate = threading.Event()
    calls = []
    switched = []

    def probe(profile, settings, cancel):
        calls.append(profile.id)
        if profile.name == "fast":
            gate.wait(2)
            return ProfileTest("HTTPS", "Verified", 25)
        if profile.name == "timeout":
            return ProfileTest("HTTPS", "Timeout", code="TIMEOUT")
        return ProfileTest("HTTPS", "Verified", 200)

    monkeypatch.setattr(module, "test_https", probe)
    monkeypatch.setattr(w.switcher, "request", lambda p: switched.append(p.id))
    assert not w.servers_page.selected_id()
    w.use_selected()
    wait(lambda: switched == [profiles[0].id])
    assert w.test_busy and w.servers_page.progress.maximum() == 3
    assert profiles[1].id in w.testing_states
    assert profiles[-1].id not in calls
    gate.set()
    wait(lambda: not w.test_busy)
    assert switched == [profiles[0].id, profiles[1].id]
    assert w.test_completed == 3
    assert profiles[2].test_status == "Timeout"
    assert "Not Tested" not in [w.table.item(i, 1).text() for i in range(3)]
    assert not w.servers_page.progress.isVisible()
    assert "Fastest" in w.toast.text()


def test_manual_cancel_stops_auto_selection_and_queued_tests(window, monkeypatch):
    import nextapp.group_testing as module

    w = window
    _, _, profiles = catalog(w)
    gate = threading.Event()
    calls = []
    monkeypatch.setattr(w.switcher, "request", lambda p: calls.append(p.id))

    def probe(profile, settings, cancel):
        gate.wait(2)
        return ProfileTest("HTTPS", "Verified", 10)

    monkeypatch.setattr(module, "test_https", probe)
    w.test_profiles(auto_connect=True)
    wait(lambda: bool(w.testing_states))
    w.toggle_connection()
    assert w.test_cancel.is_set() and not w.auto_group
    gate.set()
    wait(lambda: not w.test_busy)
    assert calls == [] and w.test_completed == 0 and not w.testing_states


def test_source_sheet_and_source_actions_keep_catalog_separate(window, monkeypatch):
    import nextapp.catalog_actions as actions

    w = window
    first, second, profiles = catalog(w)
    w.navigate(1)
    picker = w.servers_page.groups
    picker.showPopup()
    app().processEvents()
    assert picker.sheet.isVisible()
    picker.sheet.hide()
    w.subscription_action("copy")
    assert QApplication.clipboard().text() == first.url
    monkeypatch.setattr(actions, "edit_text", lambda *args, **kw: "Renamed")
    w.subscription_action("rename")
    assert w.subscriptions[0].name == "Renamed"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    w.subscription_action("remove")
    assert [p.id for p in w.profiles] == [profiles[-1].id]
    assert w.subscriptions[0].id == second.id
    assert w.store.load_profiles()[0].id == profiles[-1].id


def test_del_shortcut_multiselect_and_copy_edit_links(window, monkeypatch):
    import nextapp.catalog_actions as actions

    w = window
    _, _, profiles = catalog(w)
    w.navigate(1)
    w.table.selectRow(0)
    w.copy_server()
    assert QApplication.clipboard().text() == profiles[0].original
    monkeypatch.setattr(
        actions,
        "edit_text",
        lambda *args, **kwargs: "trojan://edited@example.invalid:443?security=tls#Edited",
    )
    w.edit_server()
    edited = w.profiles[0]
    assert (
        edited.id == profiles[0].id
        and edited.subscription_id == profiles[0].subscription_id
        and edited.name == "Edited"
    )
    from PySide6.QtCore import QItemSelectionModel

    selection = w.table.selectionModel()
    selection.clearSelection()
    for row in (0, 1):
        selection.select(
            w.table.model().index(row, 0),
            QItemSelectionModel.Select | QItemSelectionModel.Rows,
        )
    w.table.setFocus()
    app().processEvents()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    QTest.keyClick(w.table, Qt.Key_Delete)
    app().processEvents()
    assert [p.id for p in w.profiles] == [profiles[2].id, profiles[3].id]


def test_subscription_refresh_has_busy_indicator_and_final_notice(window, monkeypatch):
    import nextapp.ui as ui

    w = window
    first, _, profiles = catalog(w)
    gate = threading.Event()

    def fetch(*args, **kwargs):
        gate.wait(2)
        return profiles[0].original

    monkeypatch.setattr(ui, "fetch_subscription", fetch)
    w.navigate(1)
    w.servers_page.refresh.click()
    app().processEvents()
    assert (
        w.sub_busy
        and w.servers_page.progress.isVisible()
        and w.servers_page.progress.maximum() == 0
    )
    assert not w.servers_page.refresh.isEnabled()
    gate.set()
    wait(lambda: not w.sub_busy)
    assert not w.servers_page.progress.isVisible() and "finished" in w.toast.text()
    assert len(w.servers_page.visible_profiles()) == 1


def test_nonmodal_feedback_and_hardware_defaults_only_once(window, monkeypatch):
    w = window
    w.notice("Saved")
    assert w.toast.isVisible() and QApplication.activeModalWidget() is None
    monkeypatch.setattr("nextapp.bootstrap.os.cpu_count", lambda: 2)
    settings, changed = hardware_defaults(defaults())
    assert changed and settings["lightweight"] and not settings["visual_effects"]
    settings["lightweight"] = False
    restored = migrate(settings)
    later, changed = hardware_defaults(restored)
    assert not changed and not later["lightweight"]
