from __future__ import annotations
import collections, concurrent.futures, datetime, json, os, pathlib, platform, sys, threading, time
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSize, QBuffer, QIODevice, QEvent
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QIcon,
    QPixmap,
    QAction,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QComboBox,
    QFileDialog,
    QDialog,
    QPlainTextEdit,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QCheckBox,
    QMessageBox,
    QScrollArea,
    QSystemTrayIcon,
    QMenu,
    QAbstractItemView,
    QSizePolicy,
    QProgressBar,
)
from .profiles import parse_import, ProfileError, make_config, parameter_names
from .storage import Store, atomic_write
from .engine import Engine, safe_error
from .network import fetch_subscription, tcp_latency
from .i18n import translate
from .subscriptions import Subscription, reconcile
from .presentation import GlassSurface, IconButton, Power, action_icon
from .importers import manual_profile, decode_qr, decode_qr_bytes
from .network import proxy_public_ip, proxy_country

from .branding import APP_NAME, VERSION, app_icon
from .usage import subscription_usage, size as quota_size

BASE = pathlib.Path(__file__).resolve().parents[1]


def defaults():
    from .settings_schema import defaults as schema_defaults

    result = schema_defaults()
    result["theme"] = "Apex"
    return result


def label(text, cls=""):
    w = QLabel(text)
    w.setProperty("kind", cls)
    return w


def button(text, fn, cls=""):
    w = QPushButton(text)
    w.setCursor(Qt.PointingHandCursor)
    w.setProperty("kind", cls)
    w.clicked.connect(fn)
    return w


def card():
    w = QFrame()
    w.setObjectName("card")
    return w


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


class Bridge(QObject):
    imported = Signal(object, str)
    tested = Signal(str, object, str)
    notice = Signal(str)
    diagnostics = Signal(str)
    subscription_ready = Signal(object)
    subscriptions_finished = Signal(str)
    reputation_result = Signal(object)
    ip_result = Signal(object)
    profile_result = Signal(str, object)
    tests_finished = Signal()
    profile_started = Signal(str)


class Activity(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.owner = parent
        self.history = collections.deque(maxlen=120)
        self.setMinimumHeight(135)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(12, 12, -12, -20)
        dark = self.owner.settings["theme"] in ("Dark", "Apex")
        grid = QColor("#273248" if dark else "#e0e6ef")
        p.setPen(QPen(grid, 1, Qt.DashLine))
        for f in (0.15, 0.5, 0.85):
            y = r.top() + r.height() * f
            p.drawLine(r.left(), int(y), r.right(), int(y))
        if len(self.history) < 2:
            p.setPen(QColor("#94A3B8"))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(r, Qt.AlignCenter, self.owner.t("No traffic measurements yet"))
            return
        maximum = max(1024, max(max(x) for x in self.history))
        denom = max(30, len(self.history) - 1)
        for idx, color in ((0, self.owner.settings["accent"]), (1, "#22C55E")):
            p.setPen(QPen(QColor(color), 2))
            for i in range(1, len(self.history)):
                a = self.history[i - 1][idx]
                b = self.history[i][idx]
                p.drawLine(
                    int(r.left() + (i - 1) * r.width() / denom),
                    int(r.bottom() - a / maximum * r.height()),
                    int(r.left() + i * r.width() / denom),
                    int(r.bottom() - b / maximum * r.height()),
                )


class Window(QMainWindow):
    def __init__(self, root):
        super().__init__()
        self.root = pathlib.Path(root)
        self.store = Store(root)
        self.settings = defaults()
        self.settings.update(self.store.load_settings())
        from .settings_schema import migrate

        previous_settings = dict(self.settings)
        self.settings = migrate(self.settings)
        if self.settings != previous_settings:
            self.store.save_settings(self.settings)
        if self.settings.get("dashboard_design") != "glass-v1":
            self.settings["theme"] = "Apex"
            self.settings["dashboard_design"] = "glass-v1"
            self.store.save_settings(self.settings)
        from .bootstrap import hardware_defaults

        self.settings, tuned = hardware_defaults(self.settings)
        if tuned:
            self.store.save_settings(self.settings)
        self.profiles = self.store.load_profiles()
        self.subscriptions = self.store.load_subscriptions()
        from .free_sources import install_presets,repair_ownership,keep_only_free
        ownership_changed=repair_ownership(self.subscriptions,self.profiles)
        cleanup_marker=self.root/'free-only-cleanup-v1.done'
        cleanup_pending=not cleanup_marker.exists()
        cleanup_changed=False
        if cleanup_pending:
            # This release intentionally removes every non-Free subscription once.
            # Keep a backup and preserve favorites by moving them into Local servers.
            self.store.backup()
            cleanup_changed=keep_only_free(self.subscriptions,self.profiles)
            if self.settings.get('selected') and not any(p.id==self.settings['selected'] for p in self.profiles):
                self.settings['selected']=self.profiles[0].id if self.profiles else ''
        presets_changed=install_presets(self.subscriptions,self.settings)
        if presets_changed or ownership_changed or cleanup_changed or cleanup_pending:
            self.store.save_catalog(self.profiles,self.subscriptions)
            self.store.save_settings(self.settings)
            if cleanup_pending:atomic_write(cleanup_marker,b'Completed Apex VPN free-catalog cleanup v1.\n')
        from .traffic_history import TrafficHistory
        try:self.traffic_history=TrafficHistory(root)
        except Exception:self.traffic_history=None
        self.traffic_adapter=""
        self.startup_refresh_pending=False
        self.free_failed_ids=set()
        self.sub_busy = False
        self.selected = (
            self.settings.get("selected", "")
            if self.settings["remember_profile"]
            else ""
        )
        self.status = "Disconnected"
        self.active_id = ""
        self.current = 0
        from .navigation import History
        self.navigation = History()
        self.navigation_replaying = False
        self.manual_selection = False
        self.prev_traffic = None
        self.history_errors = collections.deque(maxlen=50)
        from .logbook import LogBook

        self.logs = LogBook(self)
        if self.profiles and not any(p.id == self.selected for p in self.profiles):
            self.selected = self.profiles[0].id
        self.latency_ms = None
        self.public_ip = ""
        self.country_code = ""
        self.showing_ip = False
        self.ip_busy = False
        self.engine = Engine(root)
        self.engine.setParent(self)
        self.bridge = Bridge(self)
        self.bridge.imported.connect(self.import_done)
        self.bridge.tested.connect(self.test_done)
        self.bridge.notice.connect(self.notice)
        self.bridge.diagnostics.connect(self.diagnostics_done)
        self.bridge.subscription_ready.connect(self.subscription_received)
        self.bridge.subscriptions_finished.connect(self.subscriptions_finished)
        self.bridge.ip_result.connect(self.ip_received)
        self.bridge.reputation_result.connect(self.reputation_received)
        self.bridge.profile_result.connect(self.profile_test_received)
        self.bridge.tests_finished.connect(self.profile_tests_finished)
        self.bridge.profile_started.connect(self.profile_test_started)
        self.engine.state.connect(self.connection_state)
        self.engine.traffic.connect(self.update_traffic)
        self.engine.health.connect(self.update_health)
        self.engine.diagnostic.connect(self.add_diagnostic)
        self.engine.routing_warning.connect(self.direct_routing_warning)
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.catalog_timer = QTimer(self)
        self.catalog_timer.setSingleShot(True)
        self.catalog_timer.setInterval(120)
        self.catalog_timer.timeout.connect(self.populate)
        self.test_cancel = threading.Event()
        self.test_busy = False
        self.test_total = 0
        self.test_completed = 0
        self.testing_states = {}
        self.test_started = 0
        self._efficiency_mode = False
        self.auto_group = False
        self.auto_first = False
        self.auto_results = []
        self.jobs = set()
        self.setWindowFlag(Qt.FramelessWindowHint,True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(410, 650)
        self.setMinimumSize(380, 560)
        self.setAcceptDrops(True)
        if self.settings["remember_window"] and self.settings.get("shadow_window"):
            width, height = self.settings["shadow_window"]
            if self.settings.get("allow_resize",False):
                screen=QApplication.primaryScreen().availableGeometry()
                self.resize(max(380,min(width,screen.width())),max(560,min(height,screen.height())))
            else:
                self.resize(390,580)
        self.make_ui()
        self.apply_theme()
        self.apply_native_corner_preference()
        self.setup_tray()
        from .sound import Sounds

        self.sounds = Sounds(self)
        from .settings_runtime import SettingsRuntime

        self.runtime = SettingsRuntime(self)
        from .connection_switch import ConnectionSwitch

        self.switcher = ConnectionSwitch(self)
        from .service_checks import ServiceChecks

        self.service_checks = ServiceChecks(self)
        from .interactions import InteractionEffects
        self.interactions=InteractionEffects(self)
        # Test through the ordinary network when disconnected, without using system proxy.
        QTimer.singleShot(800, lambda: self.service_checks.start()
                          if not self.engine.running and not self.engine.busy else None)
        QTimer.singleShot(1200,self.refresh_on_launch)
        self.tick = QTimer(self)
        self.tick.timeout.connect(self.on_tick)
        self.tick.start(4000 if self.settings["lightweight"] else 2000)
        self.monitor_tick = 0
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self.toggle_connection)
        QShortcut(QKeySequence("Ctrl+I"), self, activated=self.import_dialog)
        self.paste_shortcut = QShortcut(
            QKeySequence.Paste, self, activated=self.import_clipboard
        )
        self.paste_shortcut.setEnabled(self.current == 0)
        QShortcut(QKeySequence("Escape"), self, activated=self.hide_add_sheet)
        QShortcut(QKeySequence("Alt+Left"), self, activated=self.go_back)
        QShortcut(QKeySequence("Alt+Right"), self, activated=self.go_forward)
        QApplication.instance().installEventFilter(self)
        QTimer.singleShot(2200, self.show_release_notes)
        if self.engine.lease.path.exists():
            QTimer.singleShot(
                200,
                lambda: self.notice(
                    "A previous Windows proxy recovery backup exists. Review Diagnostics and use Restore Previous Windows Proxy Settings."
                ),
            )

    def t(self, s):
        from PySide6.QtCore import QLocale

        lang = self.settings["language"]
        if lang == "auto":
            lang = "fa" if QLocale.system().language() == QLocale.Persian else "en"
        return translate(s, lang)

    def selected_profile(self):
        return next((p for p in self.profiles if p.id == self.selected), None)

    def make_ui(self):
        from PySide6.QtCore import QLocale

        fa = (
            self.settings["language"] == "fa"
            or self.settings["language"] == "auto"
            and QLocale.system().language() == QLocale.Persian
        )
        self.setLayoutDirection(Qt.RightToLeft if fa else Qt.LeftToRight)
        outer = GlassSurface(self)
        outer.setObjectName("glassRoot")
        outer.setLayoutDirection(Qt.LeftToRight)
        self.setCentralWidget(outer)
        layout = QVBoxLayout(outer)
        self.outer_layout = layout
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        from .window_chrome import WindowChrome
        self.chrome=WindowChrome(self)
        layout.addWidget(self.chrome)
        # Symmetric side rails keep the real brand precisely centered.
        header = QGridLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setColumnMinimumWidth(0, 82)
        header.setColumnStretch(1, 1)
        header.setColumnMinimumWidth(2, 82)
        left = QHBoxLayout()
        left.setSpacing(2)
        left.setDirection(QHBoxLayout.LeftToRight)
        self.add_button = IconButton("plus", self, self.show_add_menu, self.t("Add profile"))
        self.back_button = IconButton("back", self, self.go_back, self.t("Back"))
        left.addWidget(self.add_button)
        left.addWidget(self.back_button)
        header.addLayout(left, 0, 0, Qt.AlignLeft)
        self.page_title = label(APP_NAME, "brand")
        self.page_title.setAlignment(Qt.AlignCenter)
        header.addWidget(self.page_title, 0, 1)
        self.settings_button = IconButton("gear", self, lambda: self.navigate(3), self.t("Settings"))
        header.addWidget(self.settings_button, 0, 2, Qt.AlignRight)
        self.status_badge = label("")
        self.status_badge.hide()
        self.nav = []
        layout.addLayout(header)
        from .responsive import ResponsiveStack

        self.stack = ResponsiveStack()
        layout.addWidget(self.stack, 1)
        self.build_dashboard()
        self.build_servers()
        self.build_diagnostics()
        self.build_settings()
        self.build_add_sheet()
        from .feedback import Toast

        self.toast = Toast(self)
        self.navigate(self.current)
        self.populate()
        self.refresh_profile()

    def build_dashboard(self):
        from .dashboard import Dashboard

        page = Dashboard(self)
        self.dashboard = page
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(8)
        v.addSpacing(0)
        self.power = Power(self)
        self.power.setFixedSize(142, 142)
        v.addWidget(self.power, 0, Qt.AlignHCenter)
        self.connection_title = label(self.t(self.status), "status")
        self.connection_title.hide()
        self.connect_button = button(
            self.t("Connect"), self.toggle_connection, "connection"
        )
        self.connect_button.setMinimumHeight(35)
        v.addWidget(self.connect_button, 0, Qt.AlignHCenter)
        self.connection_note = label("", "muted")
        self.connection_note.setAlignment(Qt.AlignCenter)
        self.connection_note.setWordWrap(True)
        self.connection_note.setMaximumHeight(38)
        self.connection_note.hide()
        v.addWidget(self.connection_note)
        v.addSpacing(2)
        c = card()
        c.setObjectName("card")
        self.server_card = c
        c.setCursor(Qt.PointingHandCursor)
        c.setAccessibleName(self.t("Choose a server"))
        c.mousePressEvent = lambda event: self.navigate(1)
        cv = QHBoxLayout(c)
        cv.setContentsMargins(15, 9, 15, 9)
        sv = QVBoxLayout()
        sv.setSpacing(2)
        sv.addWidget(label(self.t("Server"), "eyebrow"))
        self.profile_name = label("", "heading")
        self.profile_name.setWordWrap(True)
        self.profile_name.setMaximumHeight(38)
        sv.addWidget(self.profile_name)
        self.profile_detail = label("", "muted")
        sv.addWidget(self.profile_detail)
        from .quota_widgets import QuotaStrip

        self.active_quota = QuotaStrip(c)
        self.active_quota.setObjectName("activeQuota")
        self.active_quota.setRange(0, 1000)
        self.active_quota.setFixedHeight(4)
        self.active_quota.setTextVisible(False)
        self.active_quota.hide()
        cv.addLayout(sv, 1)
        cv.addWidget(button("›", lambda: self.navigate(1), "chevron"))
        v.addWidget(c)
        self.stat_values = [label("—", "metric") for _ in range(4)]
        self.stat_notes = [label(self.t("Not measured"), "muted") for _ in range(4)]
        self.stat_values[2].hide()
        self.stat_notes[2].hide()
        self.stat_notes[3].hide()
        c = card()
        self.ping_card=c
        row = QHBoxLayout(c)
        row.setContentsMargins(12, 8, 15, 8)
        self.ping_button = button(self.t("Ping") + "  —", self.toggle_ip, "ping")
        self.ping_button.setToolTip(
            self.t("Tap for exit IP and country via proxy (ipify / country.is).")
        )
        self.ping_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ping_button.customContextMenuRequested.connect(self.ip_menu)
        self.ping_button.setMinimumHeight(32)
        self.ping_button.setLayoutDirection(Qt.LeftToRight)
        self.ping_button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        row.addWidget(self.ping_button, 1)
        self.stat_values[3].setProperty("kind", "session")
        self.stat_values[3].setMinimumWidth(76)
        self.stat_values[3].setLayoutDirection(Qt.LeftToRight)
        self.stat_values[3].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.stat_values[3])
        v.addWidget(c)
        c = card()
        row = QHBoxLayout(c)
        row.setContentsMargins(15, 10, 15, 10)
        row.setSpacing(12)
        for idx, title in ((0, "Download"), (1, "Upload")):
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(
                label(("↓  " if idx == 0 else "↑  ") + self.t(title), "eyebrow")
            )
            col.addWidget(self.stat_values[idx])
            col.addWidget(self.stat_notes[idx])
            row.addLayout(col, 1)
        v.addWidget(c)
        self.activity = Activity(self)
        self.activity.hide()
        self.dashboard_sub_note = label("", "muted")
        self.dashboard_sub_note.setWordWrap(True)
        self.dashboard_sub_note.hide()
        v.addWidget(self.dashboard_sub_note)
        from .service_checks import SERVICES
        from .iconography import ServiceTile

        self.service_buttons = {}
        services = QWidget()
        self.services_grid = services
        strip = QHBoxLayout(services)
        strip.setContentsMargins(0, 0, 0, 0)
        strip.setSpacing(4)
        highlights = {"chatgpt", "gemini", "telegram"}
        for service in SERVICES:
            tile = ServiceTile(service, self)
            tile.set_result(None)
            self.service_buttons[service.key] = tile
            if service.key in highlights:
                strip.addWidget(tile, 1)
            else:
                tile.setParent(services)
                tile.hide()
        more = button("⋯", lambda: self.service_checks.show_details(), "serviceMore")
        more.setFixedSize(38, 34)
        more.setToolTip("More services · detailed checks / IP reputation limitations")
        more.setAccessibleName("More service results")
        strip.addWidget(more)
        self.services_more = more
        v.addWidget(services)
        note = label("HTTPS availability · direct / VPN · ? = uncertain", "muted")
        note.setAlignment(Qt.AlignCenter)
        self.services_note = note
        v.addWidget(note)
        v.addStretch()
        footer = label(f"APEX VPN  /  {VERSION}", "footer")
        footer.setAlignment(Qt.AlignCenter)
        v.addWidget(footer)
        self.stack.addWidget(page)

    def build_add_sheet(self):
        self.add_sheet = QFrame(self.centralWidget())
        self.add_sheet.setObjectName("addSheet")
        v = QVBoxLayout(self.add_sheet)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(label(self.t("Add profile"), "heading"))
        top.addStretch()
        close = button("", self.hide_add_sheet, "sheetclose")
        from .service_icons import symbol_icon
        close.setIcon(symbol_icon("close"))
        close.setAccessibleName(self.t("Close"))
        top.addWidget(close)
        v.addLayout(top)
        grid = QGridLayout()
        grid.setSpacing(8)
        self.add_sheet_actions = []
        for idx, (kind, text, fn) in enumerate(
            [
                ("clipboard", "Paste from clipboard", self.import_clipboard),
                ("edit", "Manual configuration", self.manual_dialog),
                ("qr", "QR code from image", self.import_qr),
                ("link", "Link / subscription", self.import_dialog),
            ]
        ):

            def invoke(checked=False, callback=fn):
                self.hide_add_sheet()
                callback()

            btn = button(self.t(text), invoke, "sheetaction")
            btn.setIcon(action_icon(kind, self.settings["theme"] in ("Dark", "Apex")))
            btn.setIconSize(QSize(22, 22))
            grid.addWidget(btn, idx // 2, idx % 2)
            self.add_sheet_actions.append((kind, btn))
        v.addLayout(grid)
        self.add_sheet.hide()

    def position_add_sheet(self):
        if hasattr(self, "add_sheet"):
            self.add_sheet.setGeometry(
                16,
                max(8, self.centralWidget().height() - 202),
                self.centralWidget().width() - 32,
                186,
            )

    def show_add_menu(self):
        self.position_add_sheet()
        self.add_sheet.setVisible(not self.add_sheet.isVisible())
        self.add_sheet.raise_()

    def hide_add_sheet(self):
        if hasattr(self, "add_sheet"):
            self.add_sheet.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self.toast.reposition()
        self.position_add_sheet()

    def manual_dialog(self):
        d = QDialog(self)
        d.setWindowTitle(self.t("Manual configuration"))
        d.resize(530, 650)
        v = QVBoxLayout(d)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QFormLayout(body)
        protocol = QComboBox()
        protocol.setObjectName("manual_protocol")
        protocol.addItems(["vless", "trojan", "ss"])
        form.addRow(self.t("Protocol"), protocol)
        fields = {}
        for key, title, default in [
            ("name", "Name", ""),
            ("host", "Server address", ""),
            ("port", "Port", "443"),
            ("secret", "UUID / password", ""),
            ("sni", "Server name (SNI)", ""),
            ("pbk", "REALITY public key", ""),
            ("sid", "REALITY short ID", ""),
            ("fp", "Fingerprint", "chrome"),
            ("flow", "Flow", ""),
            ("encryption", "VLESS encryption", "none"),
            ("path", "WebSocket path", ""),
            ("serviceName", "gRPC service", ""),
            ("method", "Shadowsocks method", "aes-128-gcm"),
        ]:
            edit = QLineEdit(default)
            edit.setObjectName("manual_" + key)
            edit.setLayoutDirection(Qt.LeftToRight)
            if key in ("secret", "pbk", "encryption"):
                edit.setEchoMode(QLineEdit.Password)
            fields[key] = edit
            form.addRow(self.t(title), edit)
        transport = QComboBox()
        transport.addItems(["tcp", "ws", "grpc"])
        security = QComboBox()
        security.addItems(["tls", "reality", "none"])
        form.addRow(self.t("Transport"), transport)
        form.addRow(self.t("Security"), security)

        def rows():
            proto = protocol.currentText()
            sec = security.currentText()
            net = transport.currentText()
            for key in ("sni", "fp"):
                form.setRowVisible(
                    fields[key], proto != "ss" and sec in ("tls", "reality")
                )
            for key in ("pbk", "sid"):
                form.setRowVisible(fields[key], proto != "ss" and sec == "reality")
            for key in ("flow", "encryption"):
                form.setRowVisible(fields[key], proto == "vless")
            form.setRowVisible(fields["path"], proto != "ss" and net == "ws")
            form.setRowVisible(fields["serviceName"], proto != "ss" and net == "grpc")
            form.setRowVisible(fields["method"], proto == "ss")
            form.setRowVisible(security, proto != "ss")
            form.setRowVisible(transport, proto != "ss")

        protocol.currentTextChanged.connect(rows)
        security.currentTextChanged.connect(rows)
        transport.currentTextChanged.connect(rows)
        rows()
        scroll.setWidget(body)
        v.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        v.addWidget(buttons)
        buttons.rejected.connect(d.reject)

        def save():
            values = {
                key: field.text()
                for key, field in fields.items()
                if form.isRowVisible(field)
            }
            values.update(
                protocol=protocol.currentText(),
                transport=transport.currentText(),
                security=security.currentText(),
            )
            # A default fingerprint is applicable only to TLS/REALITY profiles.
            if values["security"] == "none":
                values["fp"] = ""
            try:
                profile = manual_profile(values)
            except Exception as e:
                return self.notice(safe_error(e))
            self.import_done([profile], "Profile imported.")
            d.accept()

        buttons.accepted.connect(save)
        d.exec()

    def import_qr(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("QR code from image"),
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if path:
            self.import_qr_path(path)

    def import_qr_path(self, path):
        def work():
            try:
                texts = decode_qr(path)
                self.bridge.imported.emit({"qr_texts": texts}, "")
            except Exception as e:
                self.bridge.notice.emit(safe_error(e))

        self.pool.submit(work)

    def ip_menu(self, point):
        from PySide6.QtWidgets import QMenu
        menu=QMenu(self)
        copy=menu.addAction("کپی IP" if self.t("Settings") == "تنظیمات" else "Copy IP")
        copy.setEnabled(bool(self.public_ip))
        copy.triggered.connect(lambda: QApplication.clipboard().setText(self.public_ip))
        check=menu.addAction("بررسی اعتبار IP…" if self.t("Settings") == "تنظیمات" else "Check IP reputation…")
        check.triggered.connect(self.check_reputation)
        menu.exec(self.ping_button.mapToGlobal(point))

    def check_reputation(self):
        from PySide6.QtWidgets import QInputDialog,QLineEdit
        import os
        fa=self.t("Settings") == "تنظیمات"
        key=os.environ.get("SHADOWBOX_IPAPI_KEY","")
        if not key:
            key,ok=QInputDialog.getText(self,"IP reputation · ipapi.is",
                "کلید API از ipapi.is (فقط در این درخواست استفاده می‌شود):" if fa else "ipapi.is API key (used for this request only):",QLineEdit.Password)
            if not ok or not key.strip():return
        proxy=self.engine.running
        process=self.engine.process if proxy else None
        port=self.engine.settings["http_port"] if proxy else None
        self.notice("در حال بررسی اعتبار IP…" if fa else "Checking IP reputation…")
        def work():
            try:
                from .ip_reputation import query_reputation
                ip=proxy_public_ip(port)
                data=query_reputation(ip,port,key.strip())
                self.bridge.reputation_result.emit({"proxy":proxy,"process":process,"data":data})
            except Exception:
                self.bridge.reputation_result.emit({"proxy":proxy,"process":process,"error":True})
        self.pool.submit(work)

    def reputation_received(self,result):
        if result["proxy"] != self.engine.running or (result["proxy"] and result["process"] is not self.engine.process):return
        fa=self.t("Settings") == "تنظیمات"
        if result.get("error"):
            self.notice("بررسی اعتبار IP ناموفق بود." if fa else "IP reputation lookup failed.")
            return
        from PySide6.QtWidgets import QMessageBox
        data=result['data'];flags=data['flags']
        yes,no,unknown=("بله","خیر","نامشخص") if fa else ("Yes","No","Unknown")
        names={'is_abuser':"گزارش سوءاستفاده" if fa else "Abuse flagged",'is_tor':"Tor",'is_proxy':"Proxy",'is_vpn':"VPN",'is_datacenter':"Datacenter"}
        lines=[data['ip'],"ipapi.is"]
        for k,name in names.items():lines.append(name+": "+(yes if flags[k] is True else no if flags[k] is False else unknown))
        lines.append("گزارش این ارائه‌دهنده است؛ تضمین تمیزی IP نیست." if fa else "Provider evidence only; no guarantee of a clean IP.")
        QMessageBox.information(self,"اعتبار IP" if fa else "IP reputation","\n".join(lines))

    def toggle_ip(self):
        if self.ip_busy:
            return
        if self.showing_ip:
            self.showing_ip = False
            self.render_ping()
            return
        if self.public_ip:
            self.showing_ip = True
            self.render_ping()
            return
        self.ip_busy = True
        self.ping_button.setText(self.t("Looking up IP…"))
        using_proxy = self.engine.running
        process = self.engine.process if using_proxy else None
        port = self.engine.settings["http_port"] if using_proxy else None

        def work():
            try:
                ip = proxy_public_ip(port)
                try:
                    country = proxy_country(port, ip)
                except Exception:
                    country = ""
                result = {"process": process, "proxy": using_proxy,
                          "ip": ip, "country": country, "error": ""}
            except Exception as e:
                result = {"process": process, "proxy": using_proxy,
                          "ip": "", "error": safe_error(e)}
            self.bridge.ip_result.emit(result)

        self.pool.submit(work)

    def ip_received(self, result):
        # Ignore late lookups after disconnect/reconnect; never show a previous session's IP.
        if result["proxy"] != self.engine.running or (
            result["proxy"] and result["process"] is not self.engine.process
        ):
            return
        self.ip_busy = False
        if result["error"]:
            self.render_ping()
            self.notice(self.t("IP lookup failed. Your connection was not changed."))
            return
        self.public_ip = result["ip"]
        self.country_code = result.get("country", "")
        self.showing_ip = True
        self.render_ping()

    def render_ping(self):
        self.ping_button.setIcon(QIcon())
        if self.showing_ip and self.public_ip:
            self.ping_button.setText(("VPN IP  " if self.engine.running else "Direct IP  ") + self.public_ip)
            self.ping_button.setLayoutDirection(Qt.LeftToRight)
            flag = BASE / "assets" / "flags" / (self.country_code.lower() + ".svg")
            if (
                len(self.country_code) == 2
                and self.country_code.isalpha()
                and flag.is_file()
            ):
                self.ping_button.setIcon(QIcon(str(flag)))
                self.ping_button.setIconSize(QSize(24, 18))
            self.ping_button.setToolTip(
                ("VPN exit IP" if self.engine.running else "Direct public IP")
                + " · Country approximate; IP reputation is NOT verified."
            )
        else:
            self.ping_button.setText(
                self.t("Ping")
                + "  "
                + (f"{self.latency_ms:.0f} ms" if self.latency_ms is not None else "—")
            )

    def build_servers(self):
        from .server_page import ServersPage

        self.servers_page = ServersPage(self)
        self.search = self.servers_page.search
        self.filter = self.servers_page.filter
        self.table = self.servers_page.table
        self.test_label = self.servers_page.status
        self.empty_note = self.servers_page.empty
        self.subscription_note = self.servers_page.status
        self.stack.addWidget(self.servers_page)

    def build_diagnostics(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        c = card()
        cv = QVBoxLayout(c)
        cv.setContentsMargins(24, 24, 24, 24)
        cv.addWidget(label(self.t("No automatic repairs"), "heading"))
        l = label(
            self.t("Verify your connection without changing Windows settings."), "muted"
        )
        l.setWordWrap(True)
        cv.addWidget(l)
        cv.addWidget(button(self.t("Run Diagnostics"), self.run_diagnostics, "primary"))
        v.addWidget(c)
        self.diag_text = QPlainTextEdit()
        self.diag_text.setReadOnly(True)
        self.diag_text.setPlainText(
            "Ready. No diagnostics have been run.\n\nA listening local port is not proof of a working connection.\n\nHealth checks contact only the endpoints configured in Settings."
        )
        v.addWidget(self.diag_text, 1)
        v.addWidget(
            button(
                self.t("Restore Previous Windows Proxy Settings"), self.restore_proxy
            )
        )
        v.addWidget(button(self.t("Export sanitized report"), self.export_report))
        self.stack.addWidget(page)

    def build_settings(self):
        from .settings_ui import SettingsPage

        self.settings_page = SettingsPage(self)
        self.stack.addWidget(self.settings_page)

    def apply_theme(self):
        self.apply_window_size()
        theme = self.settings["theme"]
        dark = theme in ("Dark", "Apex")
        apex = theme == "Apex"
        text = "#F2F5FF" if dark else "#27334D"
        muted = "#A8B1C4" if apex else "#9BA9C1" if dark else "#7D89A1"
        surface = "rgba(10,12,17,228)" if apex else "rgba(35,45,67,205)" if dark else "rgba(255,255,255,190)"
        panel = "rgba(45,13,22,205)" if apex else "rgba(40,50,74,160)" if dark else "rgba(255,255,255,165)"
        border = "rgba(79,140,255,65)" if apex else "rgba(160,180,220,35)" if dark else "rgba(255,255,255,230)"
        accent = self.settings["accent"]
        self.setStyleSheet(
            f"""
        QMainWindow {{background:transparent;}}
        QWidget {{background:transparent;color:{text};font-family:'Segoe UI','DejaVu Sans';font-size:13px;}}
        #glassRoot {{background:transparent;}}
        #card {{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {surface},stop:1 {panel});border:1px solid {border};border-radius:20px;}}
        #card QLabel {{background:transparent;}}
        #addSheet {{background:{'#100B10' if apex else '#263149' if dark else '#F5F7FE'};border:1px solid {border};border-radius:20px;}}
        QPushButton[kind="sheetaction"] {{font-size:11px;min-height:28px;text-align:left;}}
        QPushButton[kind="sheetclose"] {{padding:1px 8px;font-size:20px;}}
        QLabel[kind="brand"] {{font-size:14px;font-weight:600;color:{muted};}}
        QLabel[kind="heading"] {{font-size:15px;font-weight:600;}}
        QLabel[kind="eyebrow"] {{font-size:11px;font-weight:500;color:{muted};}}
        QLabel[kind="muted"] {{font-size:10px;color:{muted};}}
        QLabel[kind="metric"] {{font-size:20px;font-weight:600;}}
        QLabel[kind="session"] {{font-size:11px;color:{muted};}}
        QLabel[kind="footer"] {{font-size:9px;letter-spacing:2px;color:{muted};}}
        QPushButton {{background:{surface};border:1px solid {border};border-radius:10px;padding:9px 12px;}}
        QPushButton:hover {{border:1px solid {accent};}}
        QPushButton:pressed {{background:{'#18315A' if apex else '#3A4F74' if dark else '#CCDCF9'};border:2px solid {accent};padding-top:10px;padding-bottom:8px;}}
        QPushButton:focus {{border:0;background:rgba(105,145,245,24);}}
        QPushButton:disabled {{color:{muted};}}
        QCheckBox::indicator:pressed {{border:2px solid {accent};}}
        QComboBox:pressed {{border:2px solid {accent};}}
        QLineEdit:focus,QComboBox:focus {{border:1px solid {accent};}}
        QPushButton[kind="icon"] {{border-radius:14px;padding:0;}}
        QPushButton[kind="connection"] {{background:transparent;border:0;font-size:18px;font-weight:600;padding:0 20px;}}
        QPushButton[kind="connection"]:pressed {{color:{accent};background:transparent;}}
        QPushButton[kind="serviceMore"] {{font-size:21px;padding:0;}}
        QPushButton[kind="ping"] {{background:transparent;border:0;padding:8px 4px;text-align:left;font-size:12px;}}
        QPushButton[kind="chevron"] {{background:transparent;border:0;font-size:26px;padding:0 4px;color:{muted};}}
        QPushButton[kind="primary"] {{background:{accent};border-color:{accent};color:white;font-weight:600;}}
        QLineEdit,QComboBox,QSpinBox,QPlainTextEdit {{background:{surface};border:1px solid {border};border-radius:8px;padding:8px;selection-background-color:{accent};}}
        QComboBox::drop-down {{border:0;background:transparent;width:26px;}}
        QComboBox::down-arrow {{image:url({(BASE / 'assets/chevron-down.svg').as_posix()});width:14px;height:14px;}}
        QComboBox#subscriptionGroups {{border-radius:14px;font-weight:600;padding:11px 16px;}}
        QComboBox QAbstractItemView,QMenu {{background:{'#160C12' if apex else '#202B40' if dark else '#F8FAFF'};color:{text};selection-background-color:{accent};}}
        QMenu::item {{padding:10px 20px;}}
        QMenu::item:selected {{background:{accent};color:white;}}
        QDialog,QMessageBox {{background:{'#10090E' if apex else '#1A2338' if dark else '#F3F5FB'};}}
        QTableWidget {{background:{surface};border:1px solid {border};border-radius:12px;selection-background-color:{'#321421' if apex else '#374765' if dark else '#E3EAF9'};}}
        QTableWidget::item {{padding:10px 6px;}} QTableWidget::item:selected {{color:{text};background:{"#321421" if apex else "#374765" if dark else "#DCE6FA"};}}
        QHeaderView::section {{background:{surface};color:{muted};border:0;padding:14px 8px;}}
        QScrollArea {{border:0;}}
        QScrollBar:vertical {{background:transparent;width:9px;margin:2px 0;}}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
        QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {{background:transparent;}}
        QScrollBar::handle:vertical:hover {{background:{accent};}}
        QScrollBar::handle:vertical {{background:{'#435B8D' if apex else '#485675' if dark else '#CCD4E5'};border-radius:3px;min-height:24px;}}
        QCheckBox {{spacing:10px;}}
        QCheckBox::indicator {{width:16px;height:16px;border:1px solid {muted};border-radius:4px;background:{surface};}}
        QCheckBox::indicator:checked {{background:{accent};border-color:{accent};}}
        QToolTip {{background:{'#160C12' if apex else '#202B40' if dark else '#FFFFFF'};color:{text};border:1px solid {border};}}
        """
        )
        from .feedback import improve_scroll

        for area in self.findChildren(QAbstractItemView) + self.findChildren(
            QScrollArea
        ):
            improve_scroll(area)
        self.centralWidget().update()
        self.power.set_status(self.status)
        self.power.update()
        if (
            self.settings.get("reduced_motion", True)
            or not self.settings.get("visual_effects", True)
            or self.settings.get("lightweight", False)
        ):
            self.power.animation.stop()
            self.power.hover = 0.0
        from .effects import apply_depth

        apply_depth(self)
        self.setStyleSheet(
            self.styleSheet()
            + f"QProgressBar {{border:0;background:rgba(115,135,175,35);border-radius:2px;}} QProgressBar::chunk {{background:{accent};border-radius:2px;}}"
        )
        if hasattr(self, "add_sheet_actions"):
            for kind, btn in self.add_sheet_actions:
                btn.setIcon(action_icon(kind, dark))

    def apply_window_size(self):
        if hasattr(self,"chrome"):self.chrome.sync()
        allowed = self.settings.get("allow_resize", False)
        if bool(self.windowFlags() & Qt.WindowMaximizeButtonHint) != allowed:
            visible = self.isVisible()
            self.setWindowFlag(Qt.WindowMaximizeButtonHint, allowed)
            if visible:
                self.show()
        if allowed:
            self.setMaximumSize(16777215, 16777215)
            self.setMinimumSize(380, 560)
        else:
            self.setFixedSize(390, 580)

    def apply_native_corner_preference(self):
        if os.name != "nt":
            return
        try:
            import ctypes
            preference=ctypes.c_int(2)  # DWMWCP_ROUND on Windows 11
            set_attribute=ctypes.WinDLL("dwmapi").DwmSetWindowAttribute
            set_attribute.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint]
            set_attribute.restype=ctypes.c_long
            set_attribute(
                ctypes.c_void_p(int(self.winId())), 33,
                ctypes.byref(preference), ctypes.sizeof(preference)
            )
        except (OSError, AttributeError, TypeError, ValueError):
            pass

    def toggle_theme(self):
        themes=("Apex","Dark","Light")
        self.settings["theme"]=themes[(themes.index(self.settings["theme"])+1)%len(themes)]
        self.store.save_settings(self.settings)
        self.theme.setCurrentIndex(self.theme.findData(self.settings["theme"]))
        self.apply_theme()

    def record_navigation(self):
        if self.navigation_replaying:
            return
        category = None
        if self.current == 3 and hasattr(self, "settings_page"):
            if self.settings_page.deck.currentIndex() == 1:
                category = self.settings_page.stack.currentIndex()
        self.navigation.push((self.current, category))

    def move_history(self, delta):
        state = self.navigation.step(delta)
        if state is None:
            return
        self.navigation_replaying = True
        try:
            page, category = state
            self.navigate(page)
            if page == 3:
                if category is None:
                    self.settings_page.show_categories()
                else:
                    self.settings_page.open_category(category)
        finally:
            self.navigation_replaying = False

    def go_back(self):
        if self.current == 3 and hasattr(self, "settings_page"):
            if self.settings_page.deck.currentIndex() == 1:
                self.settings_page.show_categories()
            else:
                self.navigate(0)
        elif self.current != 0:
            self.navigate(0)

    def go_forward(self):
        self.move_history(1)

    def eventFilter(self, watched, event):
        if (event.type()==QEvent.MouseButtonPress and isinstance(watched,QWidget)
                and (watched is self or self.isAncestorOf(watched)) and self.settings.get('allow_resize',False)
                and not self.isMaximized() and event.button()==Qt.LeftButton):
            point=self.mapFromGlobal(event.globalPosition().toPoint());edges=Qt.Edges()
            if point.x()<6:edges|=Qt.LeftEdge
            if point.x()>self.width()-6:edges|=Qt.RightEdge
            if point.y()<6:edges|=Qt.TopEdge
            if point.y()>self.height()-6:edges|=Qt.BottomEdge
            if edges and self.windowHandle() and self.windowHandle().startSystemResize(edges):return True
        if (event.type() == QEvent.MouseButtonRelease and isinstance(watched, QWidget)
                and (watched is self or self.isAncestorOf(watched))):
            if event.button() == Qt.BackButton:
                self.go_back()
                return True
            if event.button() == Qt.ForwardButton:
                self.go_forward()
                return True
        return super().eventFilter(watched, event)

    def show_release_notes(self):
        from .release_notes import show_release_notes
        show_release_notes(self)

    def show_release_notes_force(self):
        from .release_notes import show_release_notes
        show_release_notes(self, force=True)

    def navigate(self, i):
        self.hide_add_sheet()
        previous = self.current
        if hasattr(self, "paste_shortcut"):
            self.paste_shortcut.setEnabled(i == 0)
        if hasattr(self, "settings_page"):
            if i == 3:
                self.settings_page.activate()
                if previous != 3:
                    self.settings_page.show_categories()
            elif previous == 3:
                self.settings_page.deactivate()
        self.current = i
        # Settings spans the available canvas; other pages remain compact.
        self.outer_layout.setContentsMargins(*( (0, 6, 0, 0) if i == 3 else (14, 12, 14, 12) ))
        self.stack.setCurrentIndex(i)
        self.back_button.setVisible(i != 0)
        self.page_title.setText(
            APP_NAME
            if i == 0
            else self.t(("Overview", "Servers", "Diagnostics", "Settings", "Subscriptions")[i])
        )
        self.record_navigation()
        # No resize or minimum-width jump when Settings opens or categories change.
        if not self.settings.get("allow_resize", False):
            self.apply_window_size()
            return
        if i in (0, 1, 3):
            self.setMinimumWidth(380)
        elif i == 2:
            self.setMinimumWidth(720)
            self.resize(820, 760)
        if i == 0 and previous == 2:
            self.resize(410, 650)

    def refresh_profile(self):
        p = self.selected_profile()
        self.profile_name.setText(p.name if p else self.t("No profile selected"))
        self.profile_detail.setText(
            (p.protocol.upper() + "  ·  " + self.t(self.settings["mode"]))
            if p
            else self.t("Import a profile to get started")
        )
        if self.status == "Disconnected":
            self.connection_note.setText(
                p.name if p else self.t("Import a profile to get started")
            )
        self.refresh_active_quota()
        if (p and not self.manual_selection and self.status in ("Disconnected", "Error")
                and hasattr(self, "servers_page")):
            group = self.servers_page.groups.currentText().split("  ·  ")[0]
            self.profile_name.setText(self.t("Auto connect group") + " · " + group)

    def refresh_active_quota(self):
        if not hasattr(self, "active_quota"):
            return
        profile = self.selected_profile()
        source_id = profile.subscription_id if profile else None
        if (not self.manual_selection and self.status in ("Disconnected", "Error")
                and hasattr(self, 'servers_page') and self.servers_page.group not in ('local','all')):
            source_id = self.servers_page.group
        sub = next(
            (
                item
                for item in self.subscriptions
                if item.id == source_id
            ),
            None,
        )
        usage = subscription_usage(getattr(sub, "metadata", {}))
        self.active_quota.setVisible(usage.known)
        if usage.known:
            percentage = min(100, usage.percent)
            self.active_quota.setValue(round(percentage * 10))
            detail = f"{usage.percent:.1f}% · {quota_size(usage.used)} / {quota_size(usage.total)}"
            color = (
                "#EF4444"
                if usage.percent >= 90
                else "#F59E0B" if usage.percent >= 75 else self.settings["accent"]
            )
            self.active_quota.setStyleSheet(
                f"QProgressBar::chunk{{background:{color};border-radius:2px;}}"
            )
            self.active_quota.setToolTip(
                detail + " · " + (sub.updated_at or "Provider metadata")
            )
            self.active_quota.setAccessibleName(
                self.t("Subscription usage") + " " + detail
            )
            profile = self.selected_profile()
            self.profile_detail.setText((profile.protocol.upper() + " · " if profile else "") + detail)

    def populate(self, *args):
        self.servers_page.populate()

    def table_profile(self):
        if not self.servers_page.selected_id():
            return None
        row = self.table.currentRow()
        if row < 0:
            return None
        ident = self.table.item(row, 0).data(Qt.UserRole)
        return next((p for p in self.profiles if p.id == ident), None)

    def use_selected(self):
        profile = self.table_profile()
        if not profile:
            return self.test_profiles(auto_connect=True)
        self.manual_selection = True
        self.auto_group = False
        if self.test_busy:
            self.cancel_tests()
        self.switcher.request(profile)
        self.notice(self.t("Switching server…"))
        self.navigate(0)

    def copy_server(self):
        from .catalog_actions import copy_server

        copy_server(self)

    def edit_server(self):
        from .catalog_actions import edit_server

        edit_server(self)

    def subscription_action(self, action, subscription_id=None):
        from .catalog_actions import subscription_action

        subscription_action(self, action, subscription_id)

    def favorite(self):
        p = self.table_profile()
        if p:
            p.favorite = not p.favorite
            if p.favorite and p.subscription_id:
                p.favorite_source_id=p.subscription_id
                p.subscription_id=''
                self.store.backup()
                self.store.save_catalog(self.profiles,self.subscriptions)
                self.servers_page.select_group('favorites')
            else:
                self.store.save_catalog(self.profiles,self.subscriptions)
            self.populate()
            self.notice(self.t("Favorite updated."))

    def delete_selected(self):
        ids = {
            self.table.item(index.row(), 0).data(Qt.UserRole)
            for index in self.table.selectionModel().selectedRows()
        }
        if not ids:
            return
        if self.sub_busy or self.test_busy or self.switcher.pending:
            return self.notice(self.t("Wait for the current operation to finish."))
        if (self.engine.running or self.engine.busy) and self.active_id in ids:
            return self.notice(
                self.t("Disconnect the active server before deleting it.")
            )
        if (
            QMessageBox.question(
                self,
                "Apex VPN",
                self.t("Delete selected servers? A backup will be retained."),
            )
            != QMessageBox.Yes
        ):
            return
        from collections import Counter
        before=Counter(p.subscription_id for p in self.profiles)
        for sub in self.subscriptions:
            if sub.is_free and type(sub.metadata.get('profile_count')) is not int:
                sub.metadata['profile_count']=before[sub.id]
        profiles = [p for p in self.profiles if p.id not in ids]
        self.store.backup()
        self.store.save_catalog(profiles, self.subscriptions)
        self.profiles = profiles
        if self.selected in ids:
            self.selected = profiles[0].id if profiles else ""
            self.settings["selected"] = self.selected
            self.store.save_settings(self.settings)
        self.populate()
        self.refresh_profile()
        self.configure_tray()
        self.notice(self.t("Servers deleted."))

    def show_parameter_names(self):
        p = self.table_profile() or self.selected_profile()
        if not p:
            return self.notice(self.t("Choose a server"))
        d = QDialog(self)
        d.setWindowTitle(self.t("Parameter names"))
        d.resize(560, 380)
        v = QVBoxLayout(d)
        note = label(
            self.t(
                "Local view: names only. Review before sharing; do not send your full link."
            ),
            "muted",
        )
        note.setWordWrap(True)
        v.addWidget(note)
        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setLayoutDirection(Qt.LeftToRight)
        edit.setPlainText(parameter_names(p, local=True))
        v.addWidget(edit)
        row = QHBoxLayout()
        row.addWidget(
            button(
                self.t("Copy names only"),
                lambda: QApplication.clipboard().setText(edit.toPlainText()),
            )
        )
        row.addWidget(button(self.t("Close"), d.accept))
        v.addLayout(row)
        d.exec()

    def import_dialog(self):
        d = QDialog(self)
        d.setWindowTitle(self.t("Import profiles"))
        d.resize(590, 390)
        v = QVBoxLayout(d)
        l = label(
            "Paste share links, an HTTPS subscription URL, or Xray JSON.\nOriginal fields are retained. Unknown fields cannot silently connect.",
            "muted",
        )
        l.setWordWrap(True)
        v.addWidget(l)
        edit = QPlainTextEdit()
        edit.setPlaceholderText("vless://…\nss://…\nhttps://…")
        edit.setLayoutDirection(Qt.LeftToRight)
        v.addWidget(edit)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        v.addWidget(bb)
        if d.exec() == QDialog.Accepted:
            self.import_text(edit.toPlainText())

    def import_clipboard(self):
        mime = QApplication.clipboard().mimeData()
        if mime is None:
            return self.notice(
                self.t("Clipboard has no profile, subscription link or QR image.")
            )
        if mime.hasImage():
            image = QApplication.clipboard().image().copy()
            if image.isNull():
                return self.notice(self.t("Clipboard image could not be read."))
            if image.width() * image.height() > 16_000_000:
                return self.notice(self.t("QR image exceeds 16 megapixels."))
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            if not image.save(buffer, "PNG"):
                return self.notice(self.t("Clipboard image could not be read."))
            data = bytes(buffer.data())
            buffer.close()

            def work():
                try:
                    self.bridge.imported.emit({"qr_texts": decode_qr_bytes(data)}, "")
                except Exception as e:
                    self.bridge.notice.emit(safe_error(e))

            self.pool.submit(work)
        elif (
            mime.hasUrls()
            and len(mime.urls()) == 1
            and mime.urls()[0].isLocalFile()
            and pathlib.Path(mime.urls()[0].toLocalFile()).suffix.lower()
            in (".png", ".jpg", ".jpeg", ".webp", ".bmp")
        ):
            self.import_qr_path(mime.urls()[0].toLocalFile())
        elif mime.hasText():
            self.import_text(mime.text())
        else:
            self.notice(
                self.t("Clipboard has no profile, subscription link or QR image.")
            )

    def import_file(self):
        p, _ = QFileDialog.getOpenFileName(
            self,
            self.t("Import file"),
            "",
            "Profiles (*.txt *.json *.conf);;All files (*)",
        )
        if p:
            try:
                if pathlib.Path(p).stat().st_size > 8 * 1024 * 1024:
                    raise ProfileError("Import exceeds 8 MiB.")
                self.import_text(pathlib.Path(p).read_text(encoding="utf-8-sig"))
            except Exception as e:
                self.notice(safe_error(e))

    def import_text(self, text):
        from .telegram_transport import is_telegram_proxy_link,as_profile
        if is_telegram_proxy_link(text):
            try:self.import_done([as_profile(text)],"Profiles imported.")
            except ProfileError as error:self.notice(self.t(str(error)))
            return
        from urllib.parse import urlsplit
        candidate = urlsplit(text.strip()) if text.strip().startswith("https://") else None
        if candidate and candidate.username is None and candidate.password is None:
            from urllib.parse import unquote
            from .subscription_loader import subscription_url
            try:
                source = subscription_url(text)
            except Exception as error:
                return self.notice(safe_error(error))
            title = unquote(urlsplit(text.strip()).fragment).strip()[:120]
            # Store root bundle identity; nested feeds remain grouped under that source.
            self.start_subscriptions(
                [
                    Subscription(
                        title or self.t("Subscription") + " " + str(len(self.subscriptions) + 1),
                        source,
                    )
                ]
            )
        else:
            try:
                self.import_done(parse_import(text), "Profiles imported.")
            except Exception as e:
                self.notice(safe_error(e))

    def manage_subscriptions(self):
        if self.sub_busy:
            return self.notice(self.t("Subscription update is already running."))
        d = QDialog(self)
        d.setWindowTitle(self.t("Subscriptions"))
        d.resize(560, 310)
        v = QVBoxLayout(d)
        f = QFormLayout()
        choice = QComboBox()
        choice.addItem(self.t("New subscription"), "")
        for sub in self.subscriptions:
            choice.addItem(
                sub.name + (" · " + sub.updated_at if sub.updated_at else ""), sub.id
            )
        name = QLineEdit()
        url = QLineEdit()
        url.setEchoMode(QLineEdit.Password)
        url.setLayoutDirection(Qt.LeftToRight)
        url.setPlaceholderText("https://…")
        f.addRow(self.t("Subscriptions"), choice)
        f.addRow(self.t("Name"), name)
        f.addRow(self.t("Subscription URL"), url)
        v.addLayout(f)
        show = QCheckBox(self.t("Show URL"))
        show.toggled.connect(
            lambda state: url.setEchoMode(
                QLineEdit.Normal if state else QLineEdit.Password
            )
        )
        v.addWidget(show)
        note = label(
            self.t(
                "URLs are protected on Windows. Updates contact only your provider."
            ),
            "muted",
        )
        note.setWordWrap(True)
        v.addWidget(note)
        quota = QProgressBar()
        quota.setObjectName("subscriptionQuota")
        quota.setRange(0, 1000)
        quota.setFixedHeight(7)
        quota.setTextVisible(False)
        v.addWidget(quota)
        quota_note = label("", "muted")
        quota_note.setWordWrap(True)
        v.addWidget(quota_note)
        remove_button = None

        def changed():
            sub = next(
                (x for x in self.subscriptions if x.id == choice.currentData()), None
            )
            name.setText(sub.name if sub else "")
            url.setText(sub.url if sub else "")
            usage = subscription_usage(getattr(sub, "metadata", {}))
            quota.setEnabled(usage.known)
            quota.setValue(round(min(100, usage.percent) * 10) if usage.known else 0)
            quota_note.setText(
                f"{usage.percent:.1f}% · {quota_size(usage.used)} / {quota_size(usage.total)}"
                if usage.known
                else self.t("Quota not supplied by provider.")
            )
            if remove_button is not None:
                remove_button.setText(self.t("Clear Free servers" if sub and sub.is_free else "Remove subscription"))
                remove_button.setEnabled(bool(sub))

        choice.currentIndexChanged.connect(changed)
        changed()
        row = QHBoxLayout()

        def save_update():
            if not name.text().strip() or not url.text().strip():
                return self.notice(
                    self.t("Enter a name and an HTTPS subscription URL.")
                )
            sub = Subscription(name.text().strip(), url.text().strip())
            if choice.currentData():
                sub.id = choice.currentData()
            d.accept()
            self.start_subscriptions([sub])

        def remove():
            ident = choice.currentData()
            if not ident:
                return
            item=next((s for s in self.subscriptions if s.id==ident),None)
            if item is None:return
            self.servers_page.select_group(ident)
            d.accept()
            self.subscription_action('clear' if item.is_free else 'remove', ident)

        row.addWidget(button(self.t("Save & update"), save_update, "primary"))
        remove_button=button(self.t("Remove subscription"), remove)
        row.addWidget(remove_button)
        changed()
        row.addWidget(button(self.t("Cancel"), d.reject))
        v.addLayout(row)
        d.exec()

    def update_subscriptions(self):
        if not self.subscriptions:
            return self.manage_subscriptions()
        self.start_subscriptions(list(self.subscriptions))

    def refresh_sub_note(self, text):
        self.subscription_note.setText(text)
        self.dashboard_sub_note.setText(text)

    def start_subscriptions(self, subscriptions, cancel=None):
        if self.sub_busy:
            return self.notice(self.t("Subscription update is already running."))
        if self.engine.busy:
            return self.notice(self.t("Wait for the connection operation to finish."))
        # Resolve repeated URLs before checking the active source group.
        import copy

        from .subscription_loader import subscription_url
        requested = copy.deepcopy(subscriptions)
        for sub in requested:
            try:
                sub.url = subscription_url(sub.url)
                previous = next((x for x in self.subscriptions if x.id==sub.id),None)
                if previous is None:
                    previous=next((x for x in self.subscriptions if x.is_free==sub.is_free and subscription_url(x.url)==sub.url),None)
            except ValueError:
                return self.notice("Invalid subscription URL; previous data kept.")
            if previous:
                if previous.is_free and sub.url!=previous.url:
                    return self.notice(self.t('Free source URLs are fixed. Add a separate personal subscription instead.'))
                sub.id = previous.id
                sub.is_free=previous.is_free
                sub.source_key=previous.source_key
                if sub.name.startswith(("Subscription ", "اشتراک ")):
                    sub.name = previous.name
        # Refresh through the *live* HTTP proxy even when the active subscription
        # supplies that same running server. Engine retains its own connection snapshot.
        if cancel is None and self.current == 3:
            cancel = self.settings_page.subscription_cancel
        if self.test_busy:
            return self.notice(self.t("Wait for the current operation to finish."))
        self.sub_busy = True
        self._update_efficiency_mode()
        self.servers_page.operation_progress()
        self.notice(self.t("Updating subscriptions…"))
        self.preserve_refresh_group=self.servers_page.group if self.startup_refresh_pending or len(requested)>1 or (self.servers_page.group=="free" and all(s.is_free for s in requested)) else None
        self.sub_result_counts = [0, 0]
        self.refresh_sub_note(self.t("Updating subscriptions…"))
        proxy_port = self.engine.settings["http_port"] if self.engine.running else None

        def fetch_one(sub):
            if cancel is not None and cancel.is_set():return None
            try:
                if sub.is_free:
                    from .free_sources import load_free_source
                    incoming,sub.metadata,title=load_free_source(sub,proxy_port,cancel,fetch=fetch_subscription)
                else:
                    from .subscription_loader import load_bundle
                    incoming,sub.metadata,title=load_bundle(sub.url,proxy_port,cancel,fetch=fetch_subscription)
                if title and sub.name.startswith(("Subscription ","اشتراک ")):sub.name=title
                return {"subscription":sub,"profiles":incoming,"error":"","cancel":cancel}
            except Exception as error:
                return {"subscription":sub,"profiles":[],"error":safe_error(error),"cancel":cancel}
        def work():
            with concurrent.futures.ThreadPoolExecutor(max_workers=3,thread_name_prefix='subscription') as batch:
                futures=[batch.submit(fetch_one,sub) for sub in requested]
                for future in concurrent.futures.as_completed(futures):
                    value=future.result()
                    if value is not None:self.bridge.subscription_ready.emit(value)
            self.bridge.subscriptions_finished.emit(self.t("Subscription update finished."))

        self.pool.submit(work)

    def subscription_received(self, result):
        if result.get("cancel") is not None and result["cancel"].is_set():
            return
        if result["error"]:
            self.sub_result_counts[1] += 1
            previous = next(
                (x for x in self.subscriptions if x.id == result["subscription"].id),
                None,
            )
            if previous:
                previous.status = "failed"
                previous.last_error = "SUBSCRIPTION_DOWNLOAD_FAILED"
                self.store.save_catalog(self.profiles, self.subscriptions)
            self.refresh_sub_note(self.t("Update failed; previous profiles kept."))
            self.add_diagnostic("[SUBSCRIPTION] " + result["error"])
            return
        sub = result["subscription"]
        try:
            sub.metadata['profile_count']=len(result['profiles'])
            profiles, selected = reconcile(
                self.profiles, result["profiles"], sub.id, self.selected
            )
            if sub.is_free:
                for item in profiles:
                    if item.subscription_id==sub.id and item.id!=self.active_id:
                        item.latency=None;item.tested_at='';item.test_status='';item.test_method='';item.test_error='';item.free_failures=0
            # Keep a running profile available until the session ends if its
            # provider removed it mid-refresh. Never switch core silently.
            active = next((p for p in self.profiles if p.id == self.active_id), None)
            if (self.engine.running and active and active.subscription_id == sub.id
                    and not any(p.id == active.id for p in profiles)):
                import copy
                retained = copy.deepcopy(active)
                retained.name += " · active session"
                retained.subscription_id = ""
                profiles.append(retained)
                if self.selected == active.id:
                    selected = active.id
            sub.updated_at = datetime.datetime.now().isoformat(timespec="seconds")
            sub.status = "success"
            sub.last_error = ""
            subs = [x for x in self.subscriptions if x.id != sub.id] + [sub]
            self.store.backup()
            self.store.save_catalog(profiles, subs)
        except Exception as e:
            self.sub_result_counts[1] += 1
            self.add_diagnostic("[SUBSCRIPTION] " + safe_error(e))
            self.refresh_sub_note(self.t("Update failed; previous profiles kept."))
            return
        self.sub_result_counts[0] += 1
        self.profiles = profiles
        self.selected = selected
        self.subscriptions = subs
        self.settings["selected"] = selected
        try:
            self.store.save_settings(self.settings)
        except OSError:
            self.add_diagnostic(
                "[PREFERENCES] Could not save the selected-profile preference; subscription data was saved."
            )
        self.populate()
        if not getattr(self,"preserve_refresh_group",None):self.servers_page.select_group(sub.id)
        self.refresh_profile()
        self.configure_tray()
        self.refresh_sub_note(
            self.t("Updated")
            + " · "
            + sub.updated_at
            + " · "
            + str(len(result["profiles"]))
        )

    def subscriptions_finished(self, text):
        self.sub_busy = False
        self._update_efficiency_mode()
        ok, failed = self.sub_result_counts
        self.refresh_sub_note(
            self.t("Updated")
            + ": "
            + str(ok)
            + " · "
            + self.t("Failed")
            + ": "
            + str(failed)
        )
        self.servers_page.operation_progress()
        self.notice(self.t("Subscription update finished.") + f" ✓ {ok} · × {failed}")
        self.runtime.subscriptions_finished("failed" if failed else "success")
        group=getattr(self,"preserve_refresh_group",None)
        if group:
            if group=='local' and not any(not p.subscription_id for p in self.profiles) and any(s.is_free for s in self.subscriptions):group='free'
            self.servers_page.select_group(group)
        if self.startup_refresh_pending:
            self.startup_refresh_pending=False
            QTimer.singleShot(100,self.connect_on_launch)
        if self.current == 3:
            self.settings_page.refresh_dynamic()
        elif self.current==4:
            self.servers_page.groups.showPopup()

    def import_done(self, new, msg):
        if isinstance(new, dict) and "qr_texts" in new:
            # Each QR is validated in the worker before reaching this import route.
            texts = new["qr_texts"]
            profiles = []
            for text in texts:
                if text.startswith("https://"):
                    self.import_text(text)
                else:
                    profiles.extend(parse_import(text))
            if profiles:
                self.import_done(profiles, "QR profiles imported.")
            return
        if new:
            self.store.backup()
        seen = {(p.original,json.dumps(p.raw,sort_keys=True) if p.raw else "") for p in self.profiles}
        added = [p for p in new if (p.original,json.dumps(p.raw,sort_keys=True) if p.raw else "") not in seen]
        self.profiles.extend(added)
        if not self.selected and added:
            self.selected = added[0].id
        self.store.save_profiles(self.profiles)
        self.settings["selected"] = self.selected
        self.store.save_settings(self.settings)
        self.populate()
        self.refresh_profile()
        self.configure_tray()
        self.notice(f"{len(added)} " + msg)

    def refresh_on_launch(self):
        if self.sub_busy or self.test_busy or self.engine.busy:
            QTimer.singleShot(500,self.refresh_on_launch)
            return
        if not self.subscriptions:
            self.connect_on_launch()
            return
        self.startup_refresh_pending=True
        self.start_subscriptions(list(self.subscriptions))

    def connect_on_launch(self):
        """Opt-in startup connection; never depend on a cached ping."""
        if (self.settings.get("auto_connect_on_launch") and self.profiles
                and not self.engine.running and not self.engine.busy
                and not self.sub_busy and not self.test_busy):
            self.manual_selection = False
            self.toggle_connection()

    def toggle_connection(self):
        if self.auto_group:
            self.cancel_tests()
            if not (self.engine.running or self.engine.busy or self.switcher.pending):
                return
        if (
            self.engine.running
            or self.engine.busy
            or self.runtime.retry.isActive()
            or self.switcher.pending
        ):
            self.switcher.cancel()
            self.runtime.stop()
            self.engine.disconnect()
            return
        if self.sub_busy:
            return self.notice(self.t("Subscription update is already running."))
        p = self.selected_profile()
        if not p:
            self.navigate(1)
            self.import_dialog()
            return
        if self.manual_selection:
            self.runtime.connect_to(p)
        else:
            self.test_profiles(auto_connect=True)

    def connection_state(self, status, note):
        if hasattr(self,'_efficiency_mode'):
            self._update_efficiency_mode()
        previous = self.status
        if hasattr(self, "sounds") and previous != status:
            if status == "Connected":
                self.sounds.play("connected")
            elif status == "Error":
                self.sounds.play("error")
            elif status == "Disconnected" and previous == "Connected":
                self.sounds.play("disconnected")
        if status in ("Error", "Disconnected") or (
            status == "Connecting" and previous != "Connecting"
        ):
            self.latency_ms = None
            self.public_ip = ""
            self.country_code = ""
            self.showing_ip = False
            self.ip_busy = False
        if status=="Error":
            from .free_sources import free_ids
            p=next((p for p in self.profiles if p.id==self.active_id),None)
            if p and p.subscription_id in free_ids(self.subscriptions) and not self.engine.running and any(code in note for code in ("https-verification","UNSUPPORTED","AUTH_FAILED","TCP_REFUSED","TLS_FAILED")):
                p.free_failures+=1
                if p.free_failures>=10:
                    self.store.backup()
                    self.profiles=[x for x in self.profiles if x.id!=p.id]
                    self.active_id=""
                    if self.selected==p.id:self.selected=self.profiles[0].id if self.profiles else ""
                    self.settings["selected"]=self.selected
                    self.store.save_settings(self.settings)
                    self.populate()
                    self.refresh_profile()
                self.store.save_profiles(self.profiles)
        elif status=="Connected":
            p=next((p for p in self.profiles if p.id==self.active_id),None)
            if p and p.free_failures:
                p.free_failures=0
                self.store.save_profiles(self.profiles)
        self.status = status
        if previous != status and hasattr(self, "toast"):
            self.notice(self.t(status))
        self.power.set_status(status)
        self.status_badge.setText("●  " + self.t(status))
        self.connection_title.setText(self.t(status))
        self.connection_note.setText(note)
        self.connection_note.setToolTip(note)
        self.connect_button.setText(
            self.t(
                "Disconnect"
                if status == "Connected"
                else "Cancel" if status == "Connecting" else "Connect"
            )
        )
        color = (
            "#22C55E"
            if status == "Connected"
            else "#EF4444" if status == "Error" else self.settings["accent"]
        )
        self.power.update()
        if hasattr(self, "service_checks"):
            if status == "Connected" and previous != "Connected":
                self.service_checks.start()
            elif status == "Connecting":
                self.service_checks.cancel()
            elif status in ("Error", "Disconnected") and previous != status:
                # Recheck public websites directly on the user's ordinary connection.
                self.service_checks.start()
        if status == "Connected":
            p = next((p for p in self.profiles if p.id == self.active_id), None)
            if p:
                p.last_success = datetime.datetime.now().isoformat(timespec="seconds")
                self.store.save_profiles(self.profiles)
            if self.tray.isVisible() and self.settings["notifications"]:
                self.tray.showMessage(
                    "Apex VPN",
                    "Connection verified",
                    QSystemTrayIcon.Information,
                    2500,
                )
        if status in ("Error", "Disconnected"):
            self.stat_values[0].setText("—")
            self.stat_values[1].setText("—")
            self.stat_values[2].setText("—")
            self.prev_traffic = None
        self.connection_note.setVisible(status in ("Error", "Connecting"))
        self.render_ping()
        if status == "Error":
            self.add_diagnostic(note)
        if hasattr(self, "servers_page"):
            self.servers_page.update_action()

    def update_traffic(self, counts):
        if counts is None:
            for i in (0, 1):
                self.stat_values[i].setText("—")
                self.stat_notes[i].setText("Core counter unavailable")
            self.prev_traffic = None
            return
        up, down = counts
        if self.traffic_history is not None:
            identity=str(getattr(self.engine.process,"pid",id(self.engine.process)))+":"+str(self.engine.started)
            self.traffic_history.observe('vpn',identity,up,down)
        now = time.monotonic()
        if self.prev_traffic:
            before, old = self.prev_traffic
            elapsed = now - before
            ur = max(0, up - old[0]) / elapsed
            dr = max(0, down - old[1]) / elapsed
            self.stat_values[0].setText(human(dr) + "/s")
            self.stat_values[1].setText(human(ur) + "/s")
            self.activity.history.append((dr, ur))
            self.activity.update()
        self.prev_traffic = (now, counts)
        self.stat_notes[0].setText(human(down) + " received")
        self.stat_notes[1].setText(human(up) + " sent")

    def update_health(self, ms):
        self.latency_ms = ms
        self.stat_values[2].setText(f"{ms:.0f} ms")
        self.stat_notes[2].setText("HTTPS via proxy · " + time.strftime("%H:%M:%S"))
        self.power.update()
        self.render_ping()

    def _update_efficiency_mode(self):
        # EcoQoS is only appropriate for hidden background idling. Never throttle
        # the foreground UI, active tunnel, or any network operation.
        if not hasattr(self,'engine'):
            return
        idle=(not self.engine.running and not self.engine.busy and not self.test_busy
              and not self.sub_busy and not getattr(getattr(self,'switcher',None),'pending',False))
        hidden=(not self.isVisible() or self.isMinimized())
        enabled=bool(idle and hidden)
        if enabled==self._efficiency_mode:
            return
        from .efficiency import set_idle_efficiency
        set_idle_efficiency(enabled)
        self._efficiency_mode=enabled

    def showEvent(self,event):
        super().showEvent(event)
        if hasattr(self,'_efficiency_mode'):
            QTimer.singleShot(0,self._update_efficiency_mode)

    def changeEvent(self,event):
        super().changeEvent(event)
        if event.type()==QEvent.WindowStateChange and hasattr(self,'_efficiency_mode'):
            QTimer.singleShot(0,self._update_efficiency_mode)

    def on_tick(self):
        if self.traffic_history is not None:
            try:
                from .traffic_history import system_counters
                identity,self.traffic_adapter,up,down=system_counters()
                self.traffic_history.observe('system',identity,up,down)
            except Exception:
                self.traffic_history.unavailable('system')
        if self.engine.running:
            elapsed = int(time.monotonic() - self.engine.started)
            self.stat_values[3].setText(
                f"{elapsed//3600:02}:{elapsed//60%60:02}:{elapsed%60:02}"
            )
            self.stat_notes[3].setText(self.t(self.settings["mode"]))
            self.engine.sample()
            self.monitor_tick += self.tick.interval() / 1000
        self.runtime.tick(self.tick.interval() / 1000)
        self._update_efficiency_mode()
        if self.current == 3:
            self.settings_page.refresh_statistics()
        self.update_tray_status()

    def test_profiles(self, auto_connect=False, only=None, quality=False):
        if self.test_busy or self.sub_busy:
            return self.notice(self.t("Wait for the current operation to finish."))
        if auto_connect and self.settings["mode"] == "Disabled":
            return self.notice(self.t("Connections are disabled in Settings."))
        profiles = [only] if only else [p for p in self.servers_page.visible_profiles(ignore_search=auto_connect) if p.host]
        if not profiles:
            return self.notice(self.t("No servers in this group."))
        self.test_cancel = threading.Event()
        self.test_busy = True
        self._update_efficiency_mode()
        self.free_failed_ids=set()
        self.test_profile_map = {p.id: p for p in profiles}
        self.test_total = len(profiles)
        self.test_completed = 0
        self.test_started = time.monotonic()
        self.auto_group = auto_connect
        self.auto_first = False
        self.auto_results = []
        self.testing_states = {p.id: "Queued" for p in profiles}
        requested = self.servers_page.method.currentData()
        quality = quality or requested == "QUALITY"
        method = "HTTPS" if auto_connect or quality else requested
        self.servers_page.update_action()
        self.servers_page.operation_progress()
        self.populate()
        self.notice(self.t("Testing group…"))
        from .settings_policy import effective_settings
        from .group_testing import run_group

        settings = effective_settings(self.settings)
        if quality:
            settings["quality_checks"]=True
        from .free_sources import free_ids
        sources=free_ids(self.subscriptions)
        settings['free_profile_ids']={p.id for p in profiles if p.subscription_id in sources}
        cancel = self.test_cancel

        def work():
            try:
                run_group(
                    profiles,
                    method,
                    settings,
                    cancel,
                    self.bridge.profile_started.emit,
                    self.bridge.profile_result.emit,
                )
            finally:
                self.bridge.tests_finished.emit()

        self.pool.submit(work)

    def profile_test_started(self, ident):
        if self.test_busy and not self.test_cancel.is_set():
            self.testing_states[ident] = "Testing…"
            if not self.catalog_timer.isActive():
                self.catalog_timer.start()

    def profile_test_received(self, ident, result):
        profile = getattr(self, "test_profile_map", {}).get(ident) or next((p for p in self.profiles if p.id == ident),None)
        if not profile or result.status == "Canceled" or self.test_cancel.is_set():
            return
        self.testing_states.pop(ident, None)
        if result.method == "HTTPS" and result.service_score is not None:
            profile.service_score = result.service_score
            profile.gemini_ok = result.gemini_ok
        profile.latency = result.latency
        profile.test_status = result.status
        profile.test_method = result.method
        profile.test_error = result.code
        from .free_sources import removable,free_ids
        if profile.subscription_id in free_ids(self.subscriptions) and removable(profile):self.free_failed_ids.add(profile.id)
        profile.tested_at = datetime.datetime.now().isoformat(timespec="seconds")
        self.test_completed += 1
        self.servers_page.operation_progress()
        if not self.catalog_timer.isActive():
            self.catalog_timer.start()
        if (
            self.auto_group
            and result.method == "HTTPS"
            and result.status == "Verified"
            and result.latency is not None
        ):
            self.auto_results.append((result.latency, profile.id))
            if not self.auto_first:
                self.auto_first = True
                self.switcher.request(profile)
                self.notice(self.t("First working server found; checking the rest…"))

    def profile_tests_finished(self):
        self.test_busy = False
        self._update_efficiency_mode()
        self.testing_states.clear()
        from collections import Counter
        before=Counter(p.subscription_id for p in self.profiles)
        for sub in self.subscriptions:
            if sub.is_free and type(sub.metadata.get('profile_count')) is not int:
                sub.metadata['profile_count']=before[sub.id]
        if not self.test_cancel.is_set():
            self.servers_page.sort_verified = True
        if not self.test_cancel.is_set():
            from .free_sources import prune_failed
            kept,removed=prune_failed(self.profiles,self.subscriptions,getattr(self,"free_failed_ids",set()),self.active_id)
            if removed:
                self.store.backup()
                self.profiles=kept
                if self.selected in {p.id for p in removed}:
                    self.selected=kept[0].id if kept else ""
                    self.settings["selected"]=self.selected
                    self.store.save_settings(self.settings)
                self.refresh_profile()
        if self.settings.get("remove_failed_servers",False) and not self.test_cancel.is_set():
            failed={p.id for p in getattr(self,"test_profile_map",{}).values()
                    if p.test_status in {"Failed","Timeout","Refused"} and p.id != self.active_id}
            if failed:
                self.store.backup()
                self.profiles=[p for p in self.profiles if p.id not in failed]
                if self.selected in failed:
                    self.selected=self.profiles[0].id if self.profiles else ""
                    self.settings["selected"]=self.selected
                    self.store.save_settings(self.settings)
                    self.refresh_profile()
        self.store.save_profiles(self.profiles)
        self.servers_page.update_action()
        self.servers_page.operation_progress()
        self.populate()
        text = self.t(
            "Canceled"
            if self.test_cancel.is_set()
            else "Tests finished. TCP is reachability; HTTPS verifies the tunnel."
        )
        self.test_label.setText(f"{self.test_completed} / {self.test_total} · " + text)
        self.notice(text)
        if self.auto_group and not self.test_cancel.is_set():
            if self.auto_results:
                # Prefer genuine HTTPS responders, with star benefits first.
                def score(result):
                    latency, ident = result
                    p = self.test_profile_map.get(ident)
                    return (-(int(p.gemini_ok) + int(p.service_score is not None and p.service_score >= 90)) if p else 0, latency)
                _, ident = min(self.auto_results, key=score)
                best = next((p for p in self.profiles if p.id == ident), None)
                if best and ident != (self.switcher.target or self.active_id):
                    self.switcher.request(best)
                self.notice(self.t("Fastest verified server selected."))
            else:
                # A transient timeout in a parallel test must not permanently
                # prevent a real independent engine connection attempt.
                group = self.servers_page.visible_profiles(ignore_search=True)
                fallback = (self.selected_profile() if self.selected_profile() in group
                            else next(iter(group), None))
                if fallback:
                    self.notice("Bulk checks inconclusive; verifying selected server once more…")
                    self.switcher.request(fallback)
                else:
                    self.notice(self.t("No server passed HTTPS verification."))
        self.auto_group = False

    def test_done(self, ident, ms, error):
        from .profile_testing import ProfileTest, failure_status

        code = (
            next(
                (c for c in ("TIMEOUT", "TCP_REFUSED", "TLS_FAILED") if c in error),
                "NETWORK_ERROR",
            )
            if error
            else ""
        )
        self.profile_test_received(
            ident,
            ProfileTest(
                "TCP", failure_status(code) if error else "Reachable", ms, code
            ),
        )

    def cancel_tests(self):
        self.auto_group = False
        self.test_cancel.set()
        self.testing_states.clear()
        self.populate()
        self.notice(self.t("Canceling tests…"))
        self.test_label.setText(
            self.t(
                "Pending tests canceled. Active requests finish within their timeouts."
            )
        )

    def run_diagnostics(self):
        self.navigate(2)
        if getattr(self, "diagnosing", False):
            return
        self.diagnosing = True
        self.diag_text.setPlainText("Running read-only diagnostics…")
        p = self.selected_profile()
        s = dict(self.settings)

        def work():
            lines = [
                "Apex VPN · sanitized diagnostic report",
                time.strftime("%Y-%m-%d %H:%M:%S"),
                "",
            ]
            from .hardware import inspect

            lines.extend(
                key + ": " + value for key, value in inspect(self.root).items()
            )
            lines.append(
                "Core file: "
                + (
                    "present"
                    if pathlib.Path(s["core"]).is_file()
                    else "MISSING — select xray.exe in Settings."
                )
            )
            lines.append("Last connection stage: " + self.engine.stage)
            if self.engine.last_failure:
                lines.append("Last failure: " + self.engine.last_failure)
            if p:
                lines.append(parameter_names(p))
                try:
                    lines.append(self.engine.core_preflight(p, s))
                except Exception as e:
                    lines.append("Profile: " + safe_error(e))
                if p.host:
                    try:
                        lines.append(
                            f"Direct TCP reachability: {tcp_latency(p.host,p.port):.0f} ms (does not verify authentication)."
                        )
                    except Exception as e:
                        lines.append(
                            "Selected server TCP (not local proxy): " + safe_error(e)
                        )
            else:
                lines.append("Profile: none selected — import a share link.")
            lines.append(
                "Core state: " + ("running" if self.engine.running else "stopped")
            )
            lines.append(
                "Pending proxy recovery: "
                + ("yes" if self.engine.lease.path.exists() else "no")
            )
            lines.append("No Windows settings were changed by diagnostics.")
            lines.append("")
            if self.history_errors:
                lines.extend(["Recent sanitized errors:", *list(self.history_errors)])
            self.bridge.diagnostics.emit("\n".join(lines))

        self.pool.submit(work)
        if self.engine.running:
            self.engine.check_health()

    def diagnostics_done(self, text):
        self.diagnosing = False
        self.diag_text.setPlainText(text)

    def direct_routing_warning(self):
        self.add_diagnostic("[DIRECT_PROCESS] Process lookup failed; unmatched traffic remains proxied.", "Warning")
        self.notice("تشخیص برنامه ناموفق بود؛ بعضی استثناهای برنامه اعمال نشدند. راهنمای بخش ۱۴ را ببینید."
                    if self.settings.get("language") == "fa" else
                    "Process lookup failed; some application exceptions could not apply. See Settings 14.")

    def add_diagnostic(self, text, severity=None):
        levels = {"Off": 99, "Error": 40, "Warning": 30, "Info": 20, "Debug": 10}
        if severity is None:
            severity = (
                "Warning"
                if text.startswith("Optional HTTP")
                else (
                    "Info"
                    if "succeeded" in text.lower() or "passed" in text.lower()
                    else "Error"
                )
            )
        if levels.get(severity, 40) < levels.get(
            self.settings.get("logging", "Error"), 40
        ):
            return
        self.history_errors.append(time.strftime("%H:%M:%S") + " " + text)
        self.diag_text.appendPlainText(text)
        self.logs.append(text, severity, self.engine.stage)

    def restore_proxy(self):
        if self.engine.running or self.engine.busy:
            return self.notice(
                "Disconnect first. Disconnect automatically attempts to restore the previous settings."
            )
        if (
            QMessageBox.question(
                self,
                "Windows proxy recovery",
                "Restore the saved previous Windows LAN proxy settings? This changes Windows settings only if they still match those applied by Apex VPN. Concurrent changes will be preserved.",
            )
            != QMessageBox.Yes
        ):
            return
        try:
            self.notice(self.engine.lease.restore())
        except Exception as e:
            self.notice(safe_error(e))

    def export_report(self):
        p, _ = QFileDialog.getSaveFileName(
            self,
            "Export sanitized report",
            "nekoray-next-diagnostics.txt",
            "Text (*.txt)",
        )
        if p:
            atomic_write(p, self.diag_text.toPlainText().encode("utf-8"))

    def browse_core(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Xray core", "", "Executable (*.exe);;All files (*)"
        )
        if p:
            self.core_path.setText(p)

    def save_settings(self):
        self.settings_page.apply()

    def rebuild(self):
        if hasattr(self, "settings_page"):
            self.settings_page.shutdown()
        old = self.takeCentralWidget()
        old.deleteLater()
        self.make_ui()
        self.apply_theme()
        self.connection_state(
            self.status,
            (
                self.engine.last_failure
                if self.status == "Error"
                else self.connection_note.text()
            ),
        )
        if hasattr(self, "service_checks"):
            self.service_checks.restore_widgets()

    def reset_settings(self):
        if self.engine.running or self.engine.busy:
            return self.notice("Disconnect before resetting settings.")
        if (
            QMessageBox.question(
                self,
                "Safe defaults",
                "Reset preferences? Profiles and secrets will be preserved.",
            )
            != QMessageBox.Yes
        ):
            return
        self.store.backup()
        selected = self.selected
        self.settings = defaults()
        self.settings["selected"] = selected
        self.store.save_settings(self.settings)
        self.rebuild()

    def migrate(self):
        if self.engine.running or self.engine.busy:
            return self.notice("Disconnect before migrating data.")
        path = QFileDialog.getExistingDirectory(
            self, "Select the old NekoRay config directory (contains profiles/)"
        )
        if not path:
            return
        from .migration import migrate

        try:
            new, report = migrate(path, self.store)
            self.import_done(new, report)
        except Exception as e:
            self.notice(safe_error(e))

    def setup_tray(self):
        icon = app_icon()
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.activated.connect(
            lambda reason: (
                self.showNormal() if reason == QSystemTrayIcon.DoubleClick else None
            )
        )
        self.configure_tray()

    def configure_tray(self):
        previous = self.tray.contextMenu()
        menu = QMenu(self)
        self.tray_profile_actions = []
        menu.addAction("Show Apex VPN", self.showNormal)
        if self.settings["tray_connect"]:
            menu.addAction("Connect / disconnect", self.toggle_connection)
        if self.settings["tray_profiles"]:
            profiles = menu.addMenu("Choose profile")
            for profile in self.profiles:
                action = profiles.addAction(profile.name)
                self.tray_profile_actions.append(action)
                action.setEnabled(not self.engine.running and not self.engine.busy)
                action.triggered.connect(
                    lambda checked=False, ident=profile.id: self.select_tray_profile(
                        ident
                    )
                )
        menu.addSeparator()
        menu.addAction("Quit", self.quit_app)
        self.tray.setContextMenu(menu)
        if previous:
            previous.deleteLater()
        self.tray.setVisible(
            self.settings["tray_enabled"] and QSystemTrayIcon.isSystemTrayAvailable()
        )
        self.update_tray_status()

    def update_tray_status(self):
        if not hasattr(self, "tray"):
            return
        for action in getattr(self, "tray_profile_actions", []):
            action.setEnabled(not self.engine.running and not self.engine.busy)
        parts = ["Apex VPN"]
        if self.settings["tray_status"]:
            parts.append(self.status)
        if self.settings["tray_server"]:
            profile = self.selected_profile()
            if profile:
                parts.append(profile.name[:80])
        if self.settings["tray_speed"]:
            parts.append(
                "↓ " + self.stat_values[0].text() + " · ↑ " + self.stat_values[1].text()
            )
        self.tray.setToolTip(" · ".join(parts)[:240])

    def select_tray_profile(self, ident):
        if self.engine.running or self.engine.busy:
            return
        if any(p.id == ident for p in self.profiles):
            self.runtime.stop()
            self.manual_selection = True
            self.selected = ident
            self.settings["selected"] = ident
            self.store.save_settings(self.settings)
            self.refresh_profile()

    def quit_app(self):
        self.force_quit = True
        self.close()

    def to_tray(self):
        if self.tray.isVisible():
            self.hide()
        else:
            self.showMinimized()

    def notice(self, msg):
        if hasattr(self, "toast"):
            self.toast.show_message(msg)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() or e.mimeData().hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        try:
            if e.mimeData().hasUrls():
                for u in e.mimeData().urls():
                    if u.isLocalFile():
                        p = pathlib.Path(u.toLocalFile())
                        if p.stat().st_size > 8 * 1024 * 1024:
                            raise ProfileError("Import exceeds 8 MiB.")
                        self.import_text(p.read_text(encoding="utf-8-sig"))
                    else:
                        self.import_text(u.toString())
            else:
                self.import_text(e.mimeData().text())
        except Exception as ex:
            self.notice(safe_error(ex))

    def closeEvent(self, e):
        if (
            self.settings["minimize_close"]
            and self.tray.isVisible()
            and not getattr(self, "force_quit", False)
        ):
            e.ignore()
            self.hide()
            return
        QApplication.instance().removeEventFilter(self)
        self.servers_page.elapsed.stop()
        self.toast.timer.stop()
        self.switcher.cancel()
        self.service_checks.shutdown()
        self.runtime.shutdown()
        self.settings_page.shutdown()
        self.sounds.shutdown()
        if self.current in (0, 3) and self.settings["remember_window"]:
            self.settings["shadow_window"] = [self.width(), self.height()]
        self.settings["selected"] = (
            self.selected if self.settings["remember_profile"] else ""
        )
        try:
            self.store.save_settings(self.settings)
        except OSError:
            pass
        self.tick.stop()
        self.test_cancel.set()
        self.engine.cancel.set()
        self.hide()
        QApplication.processEvents()
        self.engine.shutdown()
        if self.traffic_history is not None:self.traffic_history.close()
        if hasattr(self,"interactions"):self.interactions.shutdown()
        self.pool.shutdown(wait=True, cancel_futures=True)
        try:
            self.store.save_profiles(self.profiles)
        except OSError:
            pass
        self.tray.hide()
        e.accept()
        self.deleteLater()
        QApplication.quit()
