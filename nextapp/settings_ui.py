"""One Settings surface, fourteen internal categories. No dashboard controls added."""

from __future__ import annotations
import concurrent.futures, json, os, pathlib, threading, time
from PySide6.QtCore import Qt, QObject, Signal, QTimer, QUrl, QLocale, QSize
from PySide6.QtGui import QDesktopServices, QColor
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QStackedWidget,
    QScrollArea,
    QFrame,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QPlainTextEdit,
    QFileDialog,
    QMessageBox,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QSizePolicy,
    QApplication,
    QProgressBar,
)
from .settings_schema import (
    SPECS,
    SCHEMA,
    CATEGORIES,
    defaults,
    validate,
    export_preferences,
    import_preferences,
)
from .settings_services import (
    CoreManager,
    TelegramStore,
    parse_telegram,
    diagnostic_report,
    privacy_report,
    support_bundle,
    set_startup,
    Cancelled,
    check_cancel,
    VERSION,
)
from .storage import atomic_write
from .engine import safe_error
from .errors import MESSAGES
from .responsive import ResponsiveStack, SettingRow, ToolGroup, ToggleSwitch
from .quota_widgets import quota_row
from .settings_policy import is_advanced, auto_candidate, SAFE_AUTO_KEYS, RESTYLE_KEYS
from .iconography import CATEGORY_GLYPHS, glyph_icon

FA = {
    "Search settings…": "جست‌وجوی تنظیمات…",
    "Test sound": "آزمایش صدا",
    "Clear logs": "پاک‌کردن لاگ",
    "Copy logs": "کپی لاگ",
    "Export logs": "خروجی لاگ",
    "All": "همه",
    "Apply changes": "اعمال تغییرات",
    "Reset section": "بازنشانی این بخش",
    "Safe defaults": "مقادیر امن اولیه",
    "Export": "خروجی",
    "Import": "ورود فایل",
    "No pending changes": "تغییری در انتظار ذخیره نیست",
    "Pending changes · Save settings": "تغییرات ذخیره‌نشده · برای ذخیره اعمال کنید",
    "Settings": "تنظیمات",
    "Advanced options": "گزینه‌های پیشرفته",
    "Browse executable": "انتخاب فایل اجرایی",
    "Validate core": "اعتبارسنجی هسته",
    "Install pinned release": "نصب نسخه تأییدشده",
    "Roll back managed core": "بازگشت هسته مدیریت‌شده",
    "Restart active core": "راه‌اندازی مجدد هسته فعال",
    "Run privacy check": "بررسی حریم خصوصی",
    "Run diagnostics": "اجرای عیب‌یابی",
    "Test selected server TCP": "بررسی TCP سرور انتخابی",
    "Check DNS": "بررسی DNS",
    "Check local ports": "بررسی پورت‌های محلی",
    "Verify HTTPS via proxy": "بررسی HTTPS از پروکسی",
    "Verify HTTP via proxy": "بررسی HTTP از پروکسی",
    "Restore previous proxy": "بازیابی پروکسی قبلی",
    "Export support ZIP": "خروجی ZIP پشتیبانی",
    "Manage subscriptions": "مدیریت اشتراک‌ها",
    "Refresh subscriptions": "به‌روزرسانی اشتراک‌ها",
    "Import configurations": "افزودن پیکربندی",
    "Import file": "ورود فایل پیکربندی",
    "Import QR image": "ورود تصویر QR",
    "Migration wizard": "انتقال از نسخه قبلی",
    "Import Telegram proxy": "افزودن پروکسی تلگرام",
    "Manual proxy metadata": "ورود دستی پروکسی",
    "Inspect Windows routes": "مشاهده مسیرهای ویندوز",
    "Test TCP": "آزمون TCP",
    "Open in Telegram": "بازکردن در تلگرام",
    "Remove selected": "حذف انتخاب‌شده",
    "Cancel operation": "لغو عملیات",
    "Clear local history": "پاک‌کردن تاریخچه محلی",
    "Show error guide": "راهنمای خطاها",
    "Ready · no checks have been run.": "آماده · هنوز بررسی انجام نشده است.",
    "Save": "ذخیره",
    "Cancel": "لغو",
    "Not available": "در دسترس نیست",
    "Saved. Network settings apply on the next connection.": "ذخیره شد. تنظیمات شبکه در اتصال بعدی اعمال می‌شوند.",
    "Operation canceled; late results discarded.": "عملیات لغو شد؛ نتایج دیرهنگام نمایش داده نمی‌شوند.",
    "Working…": "در حال اجرا…",
    "Pinned Xray release; latest-version discovery is not enabled.": "نسخه مشخص و تأییدشده Xray؛ جست‌وجوی جدیدترین نسخه فعال نیست.",
    "No saved Telegram proxies.": "پروکسی تلگرامی ذخیره نشده است.",
    "No subscriptions.": "اشتراکی ذخیره نشده است.",
    "Unavailable · hover for technical reason": "غیرفعال · دلیل فنی در راهنمای گزینه",
    "Manual": "دستی",
    "Dark": "تیره",
    "Light": "روشن",
    "System": "هماهنگ با سیستم",
    "Manual Proxy": "پروکسی دستی",
    "System Proxy": "پروکسی سیستم",
    "Disabled": "غیرفعال",
    "Lowest latency": "کمترین تأخیر",
    "Highest stability": "بیشترین پایداری",
    "Balanced": "متعادل",
    "Manual preferred": "اولویت با انتخاب دستی",
    "6 hours": "هر ۶ ساعت",
    "12 hours": "هر ۱۲ ساعت",
    "Daily": "روزانه",
    "Off": "خاموش",
    "Error": "خطا",
    "Warning": "هشدار",
    "Info": "اطلاعات",
    "Debug": "اشکال‌زدایی",
}
REASONS = {
    "auto_core": "فقط آداپتور Xray پیاده‌سازی و اعتبارسنجی شده؛ sing-box به مبدل مستقل و مدیریت چرخه اجرا نیاز دارد.",
    "seamless": "مدیر فعلی یک پردازش هسته دارد و امکان آزمودن هم‌زمان مسیر جایگزین و انتقال امن نشست‌های TCP را ندارد.",
    "verify_https": "برای اعلام موفقیت، بررسی واقعی HTTPS اجباری است؛ پاسخ پورت TCP به‌تنهایی کافی نیست.",
    "proxy_recovery": "بازیابی امن همیشه اجباری است؛ مالکیت تنظیمات، نسخه قبلی و ناظر خرابی باید حفظ شوند.",
    "tun": "آداپتور TUN، نصب‌کننده درایور تأییدشده و بازیابی امن مسیرها آماده نیست؛ درایور یا مسیر شبکه تغییر نمی‌کند.",
    "app_split": "برای استثناهای پردازش‌های محلی به بخش ۱۴ بروید؛ دریافت کل ترافیک سیستم با TUN در این نسخه آماده نیست.",
    "domain_rules": "استثناهای دامنه در بخش ۱۴ قابل تنظیم هستند؛ قواعد دلخواه DNS و اسکریپت اجرا نمی‌شوند.",
    "privacy_guard": "پروکسی HTTP تمام DNS و IPv6 سیستم را پوشش نمی‌دهد؛ بررسی دستی IP خروجی در همین بخش قابل اجراست.",
    "kill_switch": "تراکنش امن WFP یا فایروال همراه با بازیابی پس از خرابی آماده نیست؛ این قابلیت خاموش می‌ماند.",
    "load_reduce": "ابزار قابل‌اعتماد اندازه‌گیری بار CPU ویندوز نصب نشده؛ بررسی ضروری اتصال حذف نمی‌شود.",
    "launch_startup": "ثبت اجرای خودکار فقط روی ویندوز در دسترس است.",
    "battery_reduce": "وضعیت باتری ویندوز در این سیستم‌عامل در دسترس نیست.",
}

DESCRIPTIONS_FA = {
    "direct_enabled": "استثناها از اینترنت و IP واقعی شما استفاده می‌کنند. تغییرات را ذخیره کنید و برای اعمال مسیرها دوباره وصل شوید.",
    "direct_ir": "دامنه‌های .ir و زیردامنه‌هایشان مستقیم می‌شوند؛ دامنه‌های دیگر یا همه IPهای ایران شامل این گزینه نیستند.",
    "direct_domains": "هر خط یک دامنه یا نشانی سایت مانند https://example.com؛ نام دامنه خودکار استخراج می‌شود و زیردامنه‌ها نیز شامل می‌شوند. دامنه‌های بررسی اتصال همیشه پروکسی هستند.",
    "direct_apps": "فایل EXE اصلیِ متصل به شبکه را انتخاب کنید، نه فقط لانچر. هر خط یک نام یا مسیر کامل؛ برای حذف همان خط را پاک کنید. حروف کوچک و بزرگ در هسته اهمیت دارند. اگر تشخیص پردازش ناموفق باشد، ترافیک پروکسی می‌شود.",
    "auto_save": "ظاهر و گزینه‌های ساده خودکار ذخیره می‌شوند؛ شبکه، هسته و اجرای ویندوز همچنان به اعمال نیاز دارند.",
    "automatic_tuning": "تعداد تلاش، مهلت و بررسی همزمان خودکار انتخاب می‌شود. برای ویرایش دستی خاموشش کنید.",
    "service_checks": "سایت‌ها بدون VPN از اینترنت عادی و با VPN از پروکسی فعال بررسی می‌شوند. وضعیت ورود، محدودیت کشور و پاک‌بودن IP قطعی نیست.",
    "auto_connect_on_launch": "در شروع برنامه با تست تازهٔ HTTPS به‌طور خودکار سرور انتخاب می‌شود؛ پینگ قدیمی مانع اتصال نیست.",
    "remember_window": "اندازه ذخیره‌شده در شروع بعدی بازیابی می‌شود؛ بازکردن تنظیمات اندازه پنجره را تغییر نمی‌دهد.",
    "visual_effects": "عمق و سایه شیشه‌ای بدون جابه‌جایی اجزا؛ در حالت سبک یا کنتراست بالا غیرفعال می‌شود.",
    "sound_enabled": "صدای کوتاه کلیک، اتصال و قطع با پخش محلی ویندوز؛ بدون تغییر صدای سایر برنامه‌ها.",
    "reduced_motion": "انیمیشن شناورشدن را خاموش می‌کند؛ عمق ثابت قابل استفاده می‌ماند.",
    "theme": "انتخاب روز یا شبِ نسخه قبلی؛ صفحه اصلی فقط با انتخاب صریح شما تغییر می‌کند.",
    "settings_theme": "این پوسته فقط در تنظیمات اعمال می‌شود؛ ظاهر صفحه اصلی حفظ می‌شود.",
    "smart_connect": "سرورهای سازگار به‌ترتیب آزمایش می‌شوند. موفقیت به تأیید واقعی HTTPS وابسته است؛ سرور منتخبِ علاقه‌مندی ثابت می‌ماند.",
    "auto_reconnect": "قطع دستی باعث تلاش مجدد نمی‌شود. تعداد تلاش‌ها تا برقراری یک نشست پایدار محدود است.",
    "mode": "حالت غیرفعال جلوی اتصال جدید را می‌گیرد. پروکسی سیستم پس از موفقیت HTTPS، تنظیمات WinINET کاربر را تغییر می‌دهد.",
    "bypass": "قواعد واقعی آدرس‌های خصوصی در Xray اعمال می‌شوند؛ مقصدهای بررسی اتصال همیشه از پروکسی عبور می‌کنند.",
    "auto_recover_core": "از همان سقف تلاش اتصال مجدد استفاده می‌کند؛ پس از قطع دستی یا خطاهای تکراری متوقف می‌شود.",
    "subscription_interval": "فقط اشتراک‌های ذخیره‌شده بررسی می‌شوند، از جمله اشتراک سرور فعال با پروکسی خود آن؛ شکست‌ها فاصله بررسی را افزایش می‌دهند.",
    "lightweight": "پایش رابط هر ۴ ثانیه، یک تست گروهی در لحظه و بررسی پس‌زمینه کمتر؛ تأیید ضروری HTTPS حفظ می‌شود.",
    "minimize_close": "فقط زمانی عمل می‌کند که سینی سیستم قابل مشاهده باشد؛ گزینه خروج در سینی همیشه برنامه را می‌بندد.",
    "logging": "فقط پیام‌های ثابت و پاک‌سازی‌شده در حافظه می‌مانند؛ خروجی خام هسته، رمزها و لینک‌های پیکربندی ثبت نمی‌شوند.",
}


class Results(QObject):
    done = Signal(object)


class SettingsPage(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setObjectName("settingsRoot")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.controls = {}
        self.rows = []
        self.groups = []
        self.loading = True
        self.dirty = False
        self.active = False
        self.token = 0
        self.cancel = threading.Event()
        self.subscription_cancel = threading.Event()
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="settings"
        )
        self.signals = Results(self)
        self.signals.done.connect(self.operation_done)
        self.operation_busy = False
        self.future = None
        self.closed = False
        self.staging_batch = False
        self.details = []
        self.cancel_buttons = {}
        self.auto_timer = QTimer(self)
        self.auto_timer.setSingleShot(True)
        self.auto_timer.setInterval(450)
        self.auto_timer.timeout.connect(self.autosave)
        self.fa = (
            owner.settings["language"] == "fa"
            or owner.settings["language"] == "auto"
            and QLocale.system().language() == QLocale.Persian
        )
        self.setLayoutDirection(Qt.RightToLeft if self.fa else Qt.LeftToRight)
        self.core_manager = CoreManager(owner.root)
        self.telegram_store = TelegramStore(owner.root)
        self.telegram_error = False
        try:
            self.telegram = self.telegram_store.load()
        except Exception:
            self.telegram = []
            self.telegram_error = True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(9, 9, 9, 8)
        outer.setSpacing(12)
        header = QHBoxLayout()
        self.menu_button = self.btn("☰", self.show_categories)
        self.menu_button.setFixedWidth(36)
        self.menu_button.setAccessibleName(
            "فهرست بخش‌ها" if self.fa else "Settings categories"
        )
        header.addWidget(self.menu_button)
        title = QLabel(self.tr("Settings"))
        title.setObjectName("settingsTitle")
        header.addWidget(title)
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Search settings…"))
        self.search.setAccessibleName(self.tr("Search settings…"))
        self.search.setMaximumWidth(300)
        self.search.setMinimumWidth(0)
        header.addWidget(self.search)
        outer.addLayout(header)
        self.deck = ResponsiveStack()
        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setMinimumWidth(0)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setIconSize(QSize(24, 24))
        self.nav.setSpacing(2)
        self.nav.setAccessibleName(self.tr("Settings"))
        self.stack = ResponsiveStack()
        self.deck.addWidget(self.nav)
        self.deck.addWidget(self.stack)
        outer.addWidget(self.deck, 1)
        for i, (en, fa) in enumerate(CATEGORIES):
            short = [
                "General",
                "Smart Connect",
                "Network Cores",
                "Proxy & Windows",
                "Split Tunneling",
                "Security & Privacy",
                "Diagnostics & Recovery",
                "Subscriptions",
                "Telegram Proxies",
                "Performance",
                "Interface & Tray",
                "Advanced & Developer",
                "Logs",
                "Direct Exceptions",
                "Internet Usage",
            ][i]
            self.nav.addItem(f"{i+1:02}  " + (fa if self.fa else short))
            self.nav.item(i).setToolTip(fa if self.fa else en)
            self.nav.item(i).setIcon(glyph_icon(CATEGORY_GLYPHS[i]))
            scroll = QScrollArea()
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
            scroll.setMinimumWidth(0)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            body = QWidget()
            v = QVBoxLayout(body)
            v.setContentsMargins(0, 0, 6, 8)
            v.setSpacing(9)
            title = QLabel(fa if self.fa else en)
            title.setObjectName("categoryTitle")
            title.setWordWrap(True)
            v.addWidget(title)
            desc = QLabel(
                (
                    "گزینه‌های اصلی اینجا هستند؛ جزئیات فنی در بخش پیشرفته است."
                    if self.fa
                    else "Essentials first. Technical options are under Advanced."
                )
            )
            if i == 14:
                desc.setText("آمار ثبت‌شدهٔ سیستم و تونل" if self.fa else "Recorded adapter and tunnel traffic")
            if i == 13:
                desc.setText("ذخیره خودکار؛ اعمال مسیرها پس از قطع و وصل" if self.fa else "Saved automatically · reconnect to apply routing")
            desc.setObjectName("settingsMuted")
            desc.setWordWrap(True)
            v.addWidget(desc)
            standard = QFrame()
            standard.setObjectName("settingsCard")
            normal = QVBoxLayout(standard)
            normal.setContentsMargins(14, 5, 14, 5)
            normal.setSpacing(0)
            advanced_box = QWidget()
            advanced = QVBoxLayout(advanced_box)
            advanced.setContentsMargins(0, 0, 0, 0)
            advanced.setSpacing(0)
            for spec in (s for s in SPECS if s.section == i):
                self.add_setting(spec, advanced if is_advanced(spec) else normal)
            if normal.count():
                v.addWidget(standard)
            else:
                standard.hide()
            if advanced.count():
                expand = QPushButton(self.tr("Advanced options") + "  ▾")
                expand.setCheckable(True)
                expand.toggled.connect(advanced_box.setVisible)
                v.addWidget(expand)
                v.addWidget(advanced_box)
                advanced_box.hide()
                self.groups.append((i, expand, advanced_box))
            self.add_tools(i, v)
            v.addStretch()
            scroll.setWidget(body)
            self.stack.addWidget(scroll)
        self.status = QLabel(self.tr("No pending changes"))
        self.status.setObjectName("settingsMuted")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.footer = QWidget()
        footer = QGridLayout(self.footer)
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(6)
        self.apply_button = self.btn("ذخیره تنظیمات" if self.fa else "Save settings", lambda: self.apply())
        self.apply_button.setObjectName("settingsApply")
        footer.addWidget(self.apply_button, 0, 0, 1, 2)
        footer.addWidget(self.btn("Reset section", self.reset_section), 1, 0, 1, 2)
        outer.addWidget(self.footer)
        self.nav.itemClicked.connect(
            lambda item: self.open_category(self.nav.row(item))
        )
        self.nav.itemActivated.connect(
            lambda item: self.open_category(self.nav.row(item))
        )
        self.nav.setCurrentRow(0)
        self.search.textChanged.connect(self.filter)
        self.loading = False
        self.apply_button.setEnabled(False)
        self.style()
        self.aliases()
        self.refresh_dynamic()
        self.refresh_automatic()
        self.show_categories()
        self.owner.logs.changed.connect(self.refresh_logs)
        self.refresh_logs()

    def show_categories(self):
        if hasattr(self, "deck"):
            if self.deck.currentIndex() == 1:
                self.cancel_operation()
            self.deck.setCurrentIndex(0)
            if hasattr(self, "footer"):
                self.footer.hide()
            self.menu_button.setVisible(False)
            self.nav.setFocus()
            if getattr(self.owner, "settings_page", None) is self:
                self.owner.record_navigation()

    def open_category(self, index):
        if not 0 <= index < self.stack.count():
            return
        if self.deck.currentIndex() == 1 and self.stack.currentIndex() != index:
            self.cancel_operation()
        self.nav.setCurrentRow(index)
        self.stack.setCurrentIndex(index)
        self.deck.setCurrentIndex(1)
        self.footer.setVisible(index != 14)
        self.menu_button.show()
        self.refresh_dynamic()
        if getattr(self.owner, "settings_page", None) is self:
            self.owner.record_navigation()

    def refresh_logs(self):
        if not hasattr(self, "log_view"):
            return
        text = self.owner.logs.text(
            self.log_search.text(), self.log_filter.currentData()
        )
        self.log_view.setPlainText(
            text or ("هنوز رویدادی ثبت نشده است." if self.fa else "No events recorded.")
        )
        self.log_count.setText(
            (
                f"{len(self.owner.logs.entries)} رویداد · فقط پیام‌های پاک‌سازی‌شده"
                if self.fa
                else f"{len(self.owner.logs.entries)} events · fixed sanitized messages only"
            )
        )

    def copy_logs(self):
        QApplication.clipboard().setText(
            self.owner.logs.text(self.log_search.text(), self.log_filter.currentData())
        )

    def export_logs(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export"), "ShadowBox-log.txt", "Text (*.txt)"
        )
        if path:
            try:
                atomic_write(
                    path,
                    self.owner.logs.text(
                        self.log_search.text(), self.log_filter.currentData()
                    ).encode("utf-8"),
                )
            except OSError:
                self.message("Could not export logs.")

    def hideEvent(self, event):
        if hasattr(self, "status"):
            self.deactivate()
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "status") and not self.closed:
            self.activate()

    def tr(self, text):
        return FA.get(text, text) if self.fa else text

    def btn(self, text, fn):
        b = QPushButton(self.tr(text))
        b.clicked.connect(fn)
        b.setCursor(Qt.PointingHandCursor)
        b.setAccessibleName(b.text())
        return b

    def note(self, text, v):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setObjectName("settingsMuted")
        label.setTextFormat(Qt.PlainText)
        if len(text) > 110:
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(4)
            toggle = self.btn(
                "راهنمای این بخش" if self.fa else "About this section", lambda: None
            )
            toggle.setCheckable(True)
            toggle.toggled.connect(label.setVisible)
            layout.addWidget(toggle)
            layout.addWidget(label)
            label.hide()
            v.addWidget(container)
        else:
            v.addWidget(label)
        return label

    def add_setting(self, spec, parent_layout):
        row = QWidget()
        row.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        row.setObjectName("settingRow")
        layout = QHBoxLayout(row) if spec.kind == "bool" else QVBoxLayout(row)
        layout.setContentsMargins(0, 9, 0, 9)
        layout.setSpacing(8)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(spec.fa if self.fa else spec.title)
        title.setWordWrap(True)
        header_layout.addWidget(title, 1)
        reason = (
            REASONS.get(spec.key, spec.unavailable) if self.fa else spec.unavailable
        )
        description = reason or (
            DESCRIPTIONS_FA.get(spec.key, spec.description)
            if self.fa
            else spec.description
        )
        if description:
            info = QPushButton("?")
            info.setFixedSize(22, 22)
            info.setStyleSheet(
                "padding:0;border:0;background:transparent;color:#8DAEFF;font-weight:600;"
            )
            info.setToolTip(description)
            info.setAccessibleName(
                ("توضیح: " if self.fa else "Explain: ") + title.text()
            )
            info.clicked.connect(
                lambda checked=False, text=description: self.message(text)
            )
            header_layout.addWidget(info)
        layout.addWidget(header, 1 if spec.kind == "bool" else 0)
        value = self.owner.settings.get(spec.key, spec.default)
        if spec.kind == "bool":
            control = ToggleSwitch()
            control.setChecked(value)
            control.toggled.connect(self.changed)
        elif spec.kind == "choice":
            control = QComboBox()
            for choice in spec.choices:
                text = {
                    "en": "English",
                    "fa": "فارسی",
                    "auto": "Automatic / خودکار",
                }.get(choice, self.tr(choice))
                control.addItem(text, choice)
            control.setCurrentIndex(control.findData(value))
            control.currentIndexChanged.connect(self.changed)
        elif spec.kind in ("domains", "applications"):
            control = QPlainTextEdit(str(value))
            control.setFixedHeight(72)
            control.setLayoutDirection(Qt.LeftToRight)
            control.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            control.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            control.setPlaceholderText("https://example.com\nexample.ir" if spec.kind == "domains" else "C:/Games/Example/game.exe")
            control.textChanged.connect(self.changed)
        elif spec.kind == "int":
            control = QSpinBox()
            control.setRange(spec.minimum, spec.maximum)
            control.setValue(value)
            control.valueChanged.connect(self.changed)
        else:
            control = QLineEdit(str(value))
            control.setLayoutDirection(Qt.LeftToRight)
            control.textChanged.connect(self.changed)
        control.setObjectName("setting_" + spec.key)
        control.setAccessibleName(title.text())
        control.setToolTip(description)
        if spec.kind != "bool":
            control.setMaximumWidth(450)
            control.setMinimumWidth(0)
        control.setEnabled(not bool(spec.unavailable))
        layout.addWidget(control)
        if spec.kind == "applications":
            layout.addWidget(self.btn("افزودن برنامه یا بازی…" if self.fa else "Add application or game…", self.browse_direct_app))
        parent_layout.addWidget(row)
        self.controls[spec.key] = control
        self.rows.append(
            (
                spec.section,
                row,
                (
                    spec.key + " " + spec.title + " " + spec.fa + " " + description
                ).casefold(),
            )
        )

    def add_tools(self, i, v):
        if i==14:
            from .traffic_page import TrafficPage
            self.traffic_page=TrafficPage(self.owner,self.fa)
            v.addWidget(self.traffic_page)
            return
        tools = []
        if i == 0:
            self.note(
                "Apex VPN "
                + VERSION
                + " · "
                + (
                    "ظاهر این بخش مستقل از صفحه اصلی است."
                    if self.fa
                    else "Settings appearance is scoped to this page."
                ),
                v,
            )
            tools = [
                ("تغییرات نسخه" if self.fa else "What changed", lambda: self.owner.show_release_notes_force()),
                ("Safe defaults", self.safe_defaults),
                ("Export", self.export_settings),
                ("Import", self.import_settings),
            ]
        elif i == 1:
            self.note(
                (
                    "سیاست‌ها از تأخیر HTTPS تأییدشده و سابقه موفقیت استفاده می‌کنند؛ تأخیر TCP فهرست سرورها معیار موفقیت نیست."
                    if self.fa
                    else "Policies use verified HTTPS latency and local reliability history. Server-list TCP latency is not treated as connection success."
                ),
                v,
            )
        elif i == 2:
            self.core_status = self.note(
                self.tr(
                    "Pinned Xray release; latest-version discovery is not enabled."
                ),
                v,
            )
            self.note(
                "Xray · VLESS / VMess / Shadowsocks / Trojan: supported subset, validated by the selected binary. ML-KEM values stay lossless.\nsing-box · unavailable: missing serializer and process adapter.\nV2Ray / Mihomo · optional, unavailable: missing reviewed adapters.\nHysteria2 / TUIC / WireGuard / HTTP / SOCKS outbound: unavailable in the current adapter.",
                v,
            )
            tools = [
                ("Browse executable", self.browse_core),
                ("Validate core", lambda: self.run("core")),
                ("Install pinned release", self.install_core),
                ("Roll back managed core", self.rollback_core),
                ("Restart active core", self.restart_core),
            ]
        elif i == 3:
            tools = [
                ("Check local ports", lambda: self.run("ports")),
                ("Verify HTTPS via proxy", lambda: self.run("https")),
                ("Restore previous proxy", self.restore_proxy),
            ]
            self.note(
                (
                    "فقط WinINET پشتیبانی می‌شود؛ مدیریت WinHTTP، درایور و مسیرهای TUN آماده نیست. بازیابی، تغییرات برنامه‌های دیگر را بازنویسی نمی‌کند."
                    if self.fa
                    else "WinINET only · WinHTTP, TUN routes, driver installation and adapter management are unavailable. Recovery never overwrites a proxy changed by another application."
                ),
                v,
            )
        elif i == 4:
            self.note(
                (
                    "برای استثناهای سایت‌ها و برنامه‌ها به بخش ۱۴ بروید. عبور مستقیم LAN در همین بخش تنظیم می‌شود."
                    if self.fa
                    else "Use section 14 for direct domain and application exceptions. Private LAN bypass stays in this section."
                ),
                v,
            )
        elif i == 13:
            self.note(
                "قوانین معتبر خودکار ذخیره می‌شوند؛ پورت و گزینه‌های حساس دکمهٔ ذخیره دارند. برای اعمال مسیرهای جدید دوباره وصل شوید. هر خط یک دامنه یا EXE؛ برای حذف، همان خط را پاک کنید. اتصال مستقیم از IP واقعی شما استفاده می‌کند. این بخش دامنه‌های .ir را تشخیص می‌دهد، نه همه IPهای ایران.\n\nقانون برنامه فقط برای ترافیک واردشده به پروکسی Apex VPN است؛ این نسخه TUN ندارد. بیشتر بازی‌ها از پروکسی ویندوز استفاده نمی‌کنند و از قبل مستقیم هستند. فایل EXE اصلی بازی را انتخاب کنید؛ تشخیص پردازش ممکن است برای برنامه‌های محافظت‌شده یا با سطح دسترسی بالاتر موفق نشود. در این حالت ترافیک ورودی همچنان پروکسی می‌شود. تست‌های اتصال و IP برنامه همیشه پروکسی هستند."
                if self.fa else
                "Validated routing edits save automatically; ports and sensitive settings have an explicit Save action. Reconnect to apply routes. One domain or EXE per line; delete a line to remove it. Direct traffic uses your real IP. .ir matching does not include every Iranian IP.\n\nApplication rules cover traffic entering this local proxy; there is no TUN capture. Games that ignore Windows proxy already connect directly. Choose the actual networking EXE. Process lookup can fail for protected or elevated apps; unmatched incoming traffic stays proxied. Connectivity and exit-IP checks always stay on the proxy.",
                v,
            )

        elif i == 5:
            tools = [
                ("Run privacy check", self.privacy),
                ("Inspect Windows routes", lambda: self.run("routes")),
                ("Check DNS", lambda: self.run("dns")),
            ]
            self.note(
                (
                    "بررسی دستی با IPify و country.is از مسیر پروکسی انجام می‌شود؛ این سرویس‌ها IP خروجی را می‌بینند. هیچ کانفیگی ارسال نمی‌شود."
                    if self.fa
                    else "Manual check contacts ipify and country.is through the proxy. They receive the exit IP; no profiles are transmitted. DNS/IPv6 leak protection is not claimed."
                ),
                v,
            )
        elif i == 6:
            tools = [
                ("Run diagnostics", lambda: self.run("full")),
                ("Validate core", lambda: self.run("core")),
                ("Test selected server TCP", lambda: self.run("tcp")),
                ("Check DNS", lambda: self.run("dns")),
                ("Verify HTTPS via proxy", lambda: self.run("https")),
                ("Restore previous proxy", self.restore_proxy),
                ("Show error guide", self.error_guide),
                ("Export support ZIP", self.export_bundle),
            ]
        elif i == 7:
            self.quota_container = QWidget()
            self.quota_layout = QVBoxLayout(self.quota_container)
            self.quota_layout.setContentsMargins(0, 0, 0, 0)
            v.addWidget(self.quota_container)
            self.sub_status = self.note("", v)
            tools = [
                ("Manage subscriptions", self.owner.manage_subscriptions),
                ("Refresh subscriptions", self.owner.update_subscriptions),
                ("Import configurations", self.owner.import_dialog),
                ("Import file", self.owner.import_file),
                ("Import QR image", self.owner.import_qr),
                ("Migration wizard", self.owner.migrate),
            ]
            self.note(
                "VLESS, VMess, Trojan, SS: parsed; Hysteria2 and custom Xray JSON: retained for review, execution may be unsupported. HTTP/SOCKS outbound and YAML imports are unavailable. The migration wizard supports the documented NekoRay subset only. Expiration/traffic remain unknown unless the provider supplies metadata.",
                v,
            )
        elif i == 8:
            self.telegram_list = QListWidget()
            self.telegram_list.setMinimumHeight(125)
            v.addWidget(self.telegram_list)
            tools = [
                ("Import Telegram proxy", self.import_telegram),
                ("Manual proxy metadata", self.manual_telegram),
                ("Test TCP", self.test_telegram),
                ("Open in Telegram", self.open_telegram),
                ("Use SOCKS5 in Apex", self.use_telegram_transport),
                ("Remove selected", self.remove_telegram),
            ]
            self.note(
                (
                    "MTProto فقط برای تلگرام است؛ آزمون TCP احراز هویت یا اعتماد به پروکسی را اثبات نمی‌کند. اطلاعات اتصال روی ویندوز با DPAPI محافظت می‌شود."
                    if self.fa
                    else "MTProto is Telegram-specific, not a system VPN. TCP reachability does not verify authentication or trust. Credentials are protected with Windows DPAPI."
                ),
                v,
            )
        elif i == 9:
            self.stats = self.note("", v)
        elif i == 10:
            tools = [("Test sound", self.test_sound)]
            self.note(
                (
                    "اگر سینی سیستم موجود نباشد، بستن پنجره برنامه را خارج می‌کند. خروج از منوی سینی همیشه پروکسی را بازیابی می‌کند."
                    if self.fa
                    else "If the system tray is unavailable, closing exits normally. Quit in the tray always restores the proxy and exits."
                ),
                v,
            )
        elif i == 11:
            tools = [
                ("Validate core", lambda: self.run("core")),
                ("Test selected server TCP", lambda: self.run("tcp")),
                ("Check DNS", lambda: self.run("dns")),
                ("Check local ports", lambda: self.run("ports")),
                ("Verify HTTP via proxy", lambda: self.run("http")),
                ("Verify HTTPS via proxy", lambda: self.run("https")),
                ("Export support ZIP", self.export_bundle),
                ("Clear local history", self.clear_history),
            ]
            self.note(
                "Command diagnostics use fixed argument vectors: version / run -test -c stdin:. No user shell commands are executed. Configuration stays in a private input pipe. No raw core output is exported.",
                v,
            )
        elif i == 12:
            self.log_count = self.note("", v)
            self.log_search = QLineEdit()
            self.log_search.setPlaceholderText(
                "جست‌وجوی لاگ…" if self.fa else "Search logs…"
            )
            v.addWidget(self.log_search)
            self.log_filter = QComboBox()
            for item in ("All", "Error", "Warning", "Info", "Debug"):
                self.log_filter.addItem(self.tr(item), item)
            v.addWidget(self.log_filter)
            self.log_view = QPlainTextEdit()
            self.log_view.setReadOnly(True)
            self.log_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.log_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.log_view.setMinimumHeight(220)
            self.log_view.setLayoutDirection(Qt.LeftToRight)
            v.addWidget(self.log_view)
            self.log_search.textChanged.connect(self.refresh_logs)
            self.log_filter.currentIndexChanged.connect(self.refresh_logs)
            tools = [
                ("Clear logs", self.clear_history),
                ("Copy logs", self.copy_logs),
                ("Export logs", self.export_logs),
                ("Export support ZIP", self.export_bundle),
            ]
        if tools:
            v.addWidget(ToolGroup([self.btn(name, fn) for name, fn in tools[:2]]))
            if len(tools) > 2:
                extra = ToolGroup([self.btn(name, fn) for name, fn in tools[2:]])
                toggle = self.btn(
                    "ابزارهای بیشتر" if self.fa else "More tools", lambda: None
                )
                toggle.setCheckable(True)
                toggle.toggled.connect(extra.setVisible)
                v.addWidget(toggle)
                v.addWidget(extra)
                extra.hide()
        if i in (2, 3, 5, 6, 8, 11):
            output = QPlainTextEdit()
            output.setReadOnly(True)
            output.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            output.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            output.setPlainText(self.tr("Ready · no checks have been run."))
            output.setLayoutDirection(Qt.LeftToRight)
            output.setMinimumHeight(140)
            output.setMaximumHeight(240)
            output.setObjectName("settingsOutput")
            v.addWidget(output)
            output.hide()
            setattr(self, "output_" + str(i), output)
            cancel_button = self.btn("Cancel operation", self.cancel_operation)
            v.addWidget(cancel_button)
            cancel_button.hide()
            self.cancel_buttons[i] = cancel_button

    def aliases(self):
        o = self.owner
        for attr, key in [
            ("mode", "mode"),
            ("core_path", "core"),
            ("bypass", "bypass"),
            ("http_url", "http_url"),
            ("https_url", "https_url"),
            ("concurrency", "concurrency"),
            ("monitor", "monitor"),
            ("lang", "language"),
            ("accent", "accent"),
            ("minimized", "start_minimized"),
        ]:
            setattr(o, attr, self.controls[key])
        o.ports = [self.controls[k] for k in ("http_port", "socks_port", "stats_port")]
        # Existing theme action remains backward compatible; not a new control outside Settings.
        o.theme = self.controls["theme"]

    def changed(self, *args):
        if self.loading:
            return
        self.dirty = True
        self.apply_button.setEnabled(True)
        self.status.setText(self.tr("Pending changes · Save settings"))
        self.refresh_automatic()
        if hasattr(self, "auto_timer") and not self.staging_batch:
            self.auto_timer.start()

    def refresh_automatic(self):
        if not hasattr(self, "controls") or "automatic_tuning" not in self.controls:
            return
        automatic = self.controls["automatic_tuning"].isChecked()
        from .settings_policy import effective_settings

        effective = effective_settings(
            dict(self.owner.settings, automatic_tuning=automatic)
        )
        for key in (
            "retry_attempts",
            "retry_delay",
            "retry_backoff",
            "stable_interval",
            "failure_interval",
            "health_timeout",
            "concurrency",
        ):
            if key in self.controls:
                self.controls[key].setEnabled(not automatic)
                if automatic:
                    self.controls[key].setToolTip(
                        (
                            f"خودکار: {effective[key]}؛ مقدار فیلد فقط در حالت دستی استفاده می‌شود."
                            if self.fa
                            else f"Automatic: {effective[key]}. Stored field value is used only in manual mode."
                        )
                    )

    def autosave(self):
        if self.closed or self.loading or self.staging_batch:
            return
        from .settings_policy import FORM_AUTO_KEYS
        if self.controls['auto_save'].isChecked():
            candidate = dict(self.owner.settings)
            for key in FORM_AUTO_KEYS:
                candidate[key] = self.read(key)
            try:
                validate(candidate)
            except ValueError:
                pass  # Partial text/port drafts cannot invalidate other preferences.
            else:
                changed = {key for key in FORM_AUTO_KEYS if candidate[key] != self.owner.settings.get(key)}
                if changed - SAFE_AUTO_KEYS:
                    self.apply(automatic=True, values_override=candidate)
                    return
        draft = {key: self.read(key) for key in SAFE_AUTO_KEYS if key in self.controls}
        enabled = self.controls["auto_save"].isChecked()
        if not enabled:
            draft = {"auto_save": False}
        try:
            candidate, changed = auto_candidate(self.owner.settings, draft)
        except ValueError:
            return
        if not changed:
            return
        try:
            self.owner.store.save_settings(candidate)
        except OSError:
            self.status.setText(
                "ذخیره نشد؛ تغییرات حفظ شده‌اند."
                if self.fa
                else "Could not save. Your edits are still staged."
            )
            return
        old_checks = self.owner.settings.get("service_checks", True)
        self.owner.settings = candidate
        if changed & RESTYLE_KEYS:
            self.owner.apply_theme()
            self.style()
        if any(key.startswith('tray_') or key in {'minimize_close','notifications','language'} for key in changed):
            self.owner.configure_tray()
        if old_checks != candidate.get("service_checks", True) and hasattr(
            self.owner, "service_checks"
        ):
            if candidate["service_checks"]:
                self.owner.service_checks.start()
            else:
                self.owner.service_checks.cancel()
        self.dirty = any(self.read(key) != candidate.get(key) for key in self.controls)
        self.apply_button.setEnabled(self.dirty)
        self.status.setText(
            (
                "ظاهر ذخیره شد؛ تغییرات مهم منتظر اعمال هستند."
                if self.dirty
                else "خودکار ذخیره شد."
            )
            if self.fa
            else (
                "Simple preferences saved; important changes still need Apply."
                if self.dirty
                else "Saved automatically."
            )
        )
        self.owner.refresh_profile()
        self.refresh_automatic()
        self.owner.notice("خودکار ذخیره شد." if self.fa else "Saved automatically.")

    def browse_direct_app(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "انتخاب برنامه یا بازی" if self.fa else "Choose application or game",
            "", "Windows applications (*.exe)",
        )
        if paths:
            control = self.controls["direct_apps"]
            current = control.toPlainText().strip()
            candidate = "\n".join(filter(None, [current] + paths))
            from .direct_routing import applications
            try:
                applications(candidate)
            except ValueError as error:
                return self.message(str(error))
            control.setPlainText(candidate)

    def values(self):
        result = {}
        for key, w in self.controls.items():
            kind = SCHEMA[key].kind
            result[key] = (
                w.isChecked()
                if kind == "bool"
                else (
                    w.currentData()
                    if kind == "choice"
                    else w.value() if kind == "int" else w.toPlainText().strip() if kind in ("domains", "applications") else w.text().strip()
                )
            )
        return validate(result)

    def load_values(self, values):
        self.loading = True
        for key, w in self.controls.items():
            value = values[key]
            kind = SCHEMA[key].kind
            if kind == "bool":
                w.setChecked(value)
            elif kind == "choice":
                w.setCurrentIndex(w.findData(value))
            elif kind == "int":
                w.setValue(value)
            elif kind in ("domains", "applications"):
                w.setPlainText(str(value))
            else:
                w.setText(str(value))
        self.loading = False
        self.staging_batch = True
        self.changed()

    def apply(self, automatic=False, values_override=None):
        o = self.owner
        if self.operation_busy:
            return self.message(
                "Wait for the Settings operation to finish or cancel it."
            )
        try:
            new = self.values() if values_override is None else validate(values_override)
        except ValueError as e:
            return self.message(str(e))
        changed = {k for k, v in new.items() if o.settings.get(k) != v}
        reconnect_required = (o.engine.busy or o.engine.running) and any(
            SCHEMA[k].application == "next connection" for k in changed)
        if any(SCHEMA[k].permission != "user" for k in changed):
            if (
                QMessageBox.question(
                    self,
                    self.tr("Apply changes"),
                    "Apply these Windows integration preferences? Proxy changes happen only after a verified connection. Startup registration is per-user.",
                )
                != QMessageBox.Yes
            ):
                return
        old = dict(o.settings)
        candidate = dict(old)
        candidate.update(new)
        candidate["theme"] = o.theme.currentData()
        candidate["schema_version"] = 1
        startup_changed = "launch_startup" in changed
        try:
            if startup_changed:
                set_startup(new["launch_startup"])
            o.store.save_settings(candidate)
        except Exception:
            if startup_changed:
                try:
                    set_startup(old.get("launch_startup", False))
                except Exception:
                    pass
            return self.message(
                "Settings could not be saved. Previous application preferences remain active. Check startup registration if Windows denied rollback."
            )
        o.settings = candidate
        o.notice("تنظیمات ذخیره شد." if self.fa else "Settings saved.")
        self.dirty = any(self.read(key) != candidate.get(key) for key in self.controls)
        self.apply_button.setEnabled(self.dirty)
        self.status.setText(
            ("ذخیره شد؛ برای اعمال شبکه یک بار قطع و وصل کنید." if self.fa else "Saved · reconnect to apply network changes.")
            if reconnect_required else self.tr("Saved. Network settings apply on the next connection.")
        )
        if self.dirty:
            self.status.setText("ذخیره شد؛ گزینه‌های پیشرفتهٔ ویرایش‌شده هنوز منتظر ذخیره‌اند." if self.fa else "Saved; advanced drafts still need Save settings.")
        if changed & RESTYLE_KEYS:
            o.apply_theme()
        if any(key.startswith('tray_') or key in {'minimize_close','notifications','language'} for key in changed):
            o.configure_tray()
        if 'lightweight' in changed:
            o.tick.setInterval(4000 if new["lightweight"] else 2000)
        if "service_checks" in changed and hasattr(o, "service_checks"):
            if new["service_checks"]:
                o.service_checks.start()
            else:
                o.service_checks.cancel()
        if "language" in changed:
            # Rebuild is necessary for existing translated labels; dashboard structure remains identical.
            o.rebuild()
            return
        if not automatic:
            self.staging_batch = False
        self.auto_timer.stop()
        if changed & RESTYLE_KEYS:
            self.style()
        self.refresh_automatic()
        o.refresh_profile()

    def style(self):
        s = self.owner.settings
        theme = s.get("settings_theme", "Apex")
        apex = theme == "Apex"
        dark = (
            theme in ("Dark", "Apex")
            or theme == "System"
            and QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        )
        self.setProperty("settingsDark",dark)
        bg = "#090A0E" if apex else "#0B1020" if dark else "#F2F5FC"
        panel = "#1B1018" if apex else "#192335" if dark else "#FFFFFF"
        fg = "#F8FAFC" if dark else "#152238"
        muted = "#B1BED3" if s["high_contrast"] else "#A8B1C4" if apex else "#94A3B8" if dark else "#586780"
        border = "#687D9F" if s["high_contrast"] else "#3F3150" if apex else "#2C3950" if dark else "#DAE2EF"
        accent = s["accent"]
        size = round(13 * s["text_scale"] / 100)
        self.setStyleSheet(
            f"""#settingsRoot {{background:{bg};border:0;border-radius:0;}} #settingsRoot QWidget {{color:{fg};font-size:{size}px;background:transparent;}}
        #settingsRoot QLabel#settingsTitle {{font-size:{size+10}px;font-weight:700;}} #settingsRoot QLabel#categoryTitle {{font-size:{size+5}px;font-weight:600;margin-bottom:3px;}}
        #settingsRoot QLabel#settingsMuted {{color:{muted};font-size:{max(11,size-1)}px;}} #settingsRoot QFrame#settingsCard {{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {panel},stop:1 {bg});border:1px solid {border};border-radius:15px;}}
        #settingsRoot QListWidget {{background:{panel};border:1px solid {border};border-radius:10px;outline:0;}} #settingsRoot QListWidget::item {{padding:6px 7px;border-radius:6px;}} #settingsRoot QListWidget::item:selected {{background:{accent};color:white;}}
        #settingsRoot QLineEdit,#settingsRoot QComboBox,#settingsRoot QSpinBox,#settingsRoot QPlainTextEdit {{background:{panel};color:{fg};border:1px solid {border};border-radius:7px;padding:6px;selection-background-color:{accent};}}
        #settingsRoot QPushButton {{background:{panel};border:1px solid {border};border-radius:7px;padding:8px 10px;}} #settingsRoot QPushButton:hover {{border-color:{accent};}} #settingsRoot QPushButton:pressed {{background:{accent};color:white;}} #settingsRoot QPushButton:focus {{border:0;background:{panel};}} #settingsRoot QLineEdit:focus,#settingsRoot QPlainTextEdit:focus {{border-color:{accent};}} #settingsRoot QPushButton#settingsApply {{background:{accent};color:white;}}
        #settingsRoot QPushButton:disabled,#settingsRoot QCheckBox:disabled {{color:{muted};}} #settingsRoot QPushButton#settingsApply:disabled {{background:{panel};color:{muted};}} #settingsRoot QCheckBox::indicator {{width:18px;height:18px;border:1px solid {muted};border-radius:5px;background:{panel};}} #settingsRoot QCheckBox::indicator:checked {{background:{accent};}} #settingsRoot QScrollArea {{border:0;}} #settingsRoot QScrollBar::add-line:vertical,#settingsRoot QScrollBar::sub-line:vertical {{height:0;}} #settingsRoot QAbstractScrollArea::corner {{background:{bg};}}
        #settingsRoot QComboBox QAbstractItemView {{background:{panel};color:{fg};selection-background-color:{accent};}}"""
        )

    def filter(self, text):
        query = text.strip().casefold()
        matches = set()
        for i, row, terms in self.rows:
            visible = (
                not query
                or query in terms
                or query in (" ".join(CATEGORIES[i])).casefold()
            )
            row.setVisible(visible)
            if visible:
                matches.add(i)
        for i, expand, body in self.groups:
            if query:
                body.show()
            else:
                body.setVisible(expand.isChecked())
        for i, (en, fa) in enumerate(CATEGORIES):
            self.nav.item(i).setHidden(
                bool(query)
                and i not in matches
                and query not in (en + " " + fa).casefold()
            )
        if query and self.nav.item(self.nav.currentRow()).isHidden() and matches:
            self.nav.setCurrentRow(min(matches))
        self.status.setText(
            (
                f"{len(matches)} دسته"
                if self.fa
                else f"{len(matches)} matching categories"
            )
            if query
            else self.tr(
                "Pending changes · Save settings"
                if self.dirty
                else "No pending changes"
            )
        )

    def reset_section(self):
        values = {k: self.read(k) for k in self.controls}
        i = self.nav.currentRow()
        for s in SPECS:
            if s.section == i:
                values[s.key] = s.reset
        self.load_values(values)

    def read(self, key):
        w = self.controls[key]
        kind = SCHEMA[key].kind
        return (
            w.isChecked()
            if kind == "bool"
            else (
                w.currentData()
                if kind == "choice"
                else w.value() if kind == "int" else w.toPlainText() if kind in ("domains", "applications") else w.text()
            )
        )

    def safe_defaults(self):
        if (
            QMessageBox.question(
                self,
                self.tr("Safe defaults"),
                "Stage safe preferences? Profiles, credentials and the dashboard appearance will be preserved. Click Apply to save.",
            )
            == QMessageBox.Yes
        ):
            values = defaults()
            values["theme"] = self.owner.settings["theme"]
            self.load_values(values)

    def export_settings(self):
        try:
            data = export_preferences(self.values())
        except ValueError as e:
            return self.message(str(e))
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export"), "NekoRayNext-settings.json", "JSON (*.json)"
        )
        if path:
            try:
                atomic_write(
                    path, json.dumps(data, ensure_ascii=False, indent=2).encode()
                )
                self.message(
                    "Non-sensitive preferences exported. Core paths, private endpoints, profile identities and credentials are excluded."
                )
            except OSError:
                self.message("Could not export settings.")

    def import_settings(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Import"), "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            p = pathlib.Path(path)
            if p.stat().st_size > 65536:
                raise ValueError("Settings file is too large.")
            data = import_preferences(json.loads(p.read_text(encoding="utf-8-sig")), self.owner.settings)
            self.load_values(data)
        except (ValueError, OSError):
            self.message(
                "Settings import rejected. Check file format, supported keys and values. Nothing was saved."
            )

    def message(self, text):
        self.status.setText(self.tr(text))
        self.owner.notice(self.tr(text))

    def output(self, text, category=None):
        box = getattr(
            self,
            "output_" + str(self.nav.currentRow() if category is None else category),
            None,
        )
        if box:
            box.setPlainText(text)
            box.show()
        else:
            self.status.setText(text)

    def execute(self, work, kind="report"):
        if self.closed:
            return
        if self.future is not None and not self.future.done():
            return self.message(
                "A previous Settings operation is still finishing its bounded request. Please wait."
            )
        self.cancel = threading.Event()
        self.token += 1
        token = self.token
        cancel = self.cancel
        category = self.nav.currentRow()
        self.operation_busy = True
        self.output(self.tr("Working…"), category)
        if category in self.cancel_buttons:
            self.cancel_buttons[category].show()

        def run():
            try:
                result = work(cancel)
                check_cancel(cancel)
                payload = {"ok": True, "value": result}
            except Cancelled:
                payload = {"ok": False, "value": "Operation canceled."}
            except Exception as e:
                payload = {
                    "ok": False,
                    "value": str(e) if type(e) is ValueError else safe_error(e),
                }
            payload.update(token=token, category=category, kind=kind)
            if not self.closed:
                self.signals.done.emit(payload)

        self.future = self.executor.submit(run)

    def operation_done(self, payload):
        if payload["token"] != self.token or self.closed:
            return
        self.operation_busy = False
        if payload["category"] in self.cancel_buttons:
            self.cancel_buttons[payload["category"]].hide()
        if not self.active:
            return
        if payload["ok"] and payload["kind"] == "install":
            path, version = payload["value"]
            self.controls["core"].setText(path)
            self.output(
                version + " staged at a managed path. Click Apply to select it.",
                payload["category"],
            )
        else:
            self.output(str(payload["value"]), payload["category"])
            if payload["ok"] and payload["kind"] == "core":
                self.core_status.setText(
                    self.tr(
                        "Pinned Xray release; latest-version discovery is not enabled."
                    )
                    + "\nLast inspection: "
                    + time.strftime("%Y-%m-%d %H:%M:%S")
                )

    def cancel_operation(self):
        pending = (
            self.operation_busy or self.future is not None and not self.future.done()
        )
        self.cancel.set()
        self.token += 1
        self.operation_busy = False
        if pending:
            self.output(self.tr("Operation canceled; late results discarded."))
        elif hasattr(self, "status"):
            self.status.setText(
                self.tr(
                    "Pending changes · Save settings"
                    if self.dirty
                    else "No pending changes"
                )
            )

    def deactivate(self):
        if self.auto_timer.isActive():
            self.autosave()
            self.auto_timer.stop()
        self.active = False
        self.subscription_cancel.set()
        self.cancel_operation()

    def activate(self):
        self.active = True
        from .settings_policy import pending_network_changes
        if not self.dirty and pending_network_changes(self.owner):
            self.status.setText("ذخیره شده؛ برای اعمال شبکه دوباره وصل شوید." if self.fa else "Saved · reconnect to apply network changes.")
        if self.subscription_cancel.is_set():
            self.subscription_cancel = threading.Event()
        self.refresh_dynamic()

    def shutdown(self):
        if self.closed:
            return
        if self.auto_timer.isActive():
            self.autosave()
        self.closed = True
        self.auto_timer.stop()
        self.cancel.set()
        self.subscription_cancel.set()
        self.token += 1
        self.executor.shutdown(wait=False, cancel_futures=True)

    def run(self, kind):
        from .settings_policy import session_preferences
        s = session_preferences(self.owner)
        if kind == "core":
            s["core"] = self.controls["core"].text().strip()
        self.execute(
            lambda cancel: diagnostic_report(self.owner, s, cancel, kind), kind
        )

    def privacy(self):
        from .settings_policy import session_preferences
        s = session_preferences(self.owner)
        running = self.owner.engine.running
        self.execute(lambda cancel: privacy_report(s, running, cancel))

    def browse_core(self):
        p, _ = QFileDialog.getOpenFileName(
            self, self.tr("Browse executable"), "", "Executable (*.exe);;All files (*)"
        )
        if p:
            self.controls["core"].setText(p)

    def install_core(self):
        if self.owner.engine.running or self.owner.engine.busy:
            return self.message("Disconnect before installing a core.")
        if (
            QMessageBox.question(
                self,
                self.tr("Install pinned release"),
                "Download the pinned Xray 26.10.21 x64 release from the official XTLS GitHub release? TLS and shipped SHA-256 verification are mandatory. This does not discover the latest version. The previous managed binary is retained for rollback.",
            )
            != QMessageBox.Yes
        ):
            return
        self.execute(self.core_manager.install, "install")

    def rollback_core(self):
        if self.owner.engine.running or self.owner.engine.busy:
            return self.message("Disconnect before rolling back a core.")
        if (
            QMessageBox.question(
                self,
                self.tr("Roll back managed core"),
                "Restore the previous validated managed executable?",
            )
            != QMessageBox.Yes
        ):
            return
        self.execute(
            lambda cancel: (check_cancel(cancel), self.core_manager.rollback())[1],
            "install",
        )

    def restart_core(self):
        o = self.owner
        if not o.engine.running:
            return self.message("No active core to restart.")
        if self.dirty:
            return self.message(
                "Apply or discard pending preferences before restarting."
            )
        if (
            QMessageBox.question(
                self,
                self.tr("Restart active core"),
                "Disconnect and verify a new connection? Active network sessions may be interrupted.",
            )
            != QMessageBox.Yes
        ):
            return
        o.runtime.stop()
        o.engine.disconnect()
        generation = o.runtime.generation
        timer = QTimer(self)
        timer.setInterval(100)

        def ready():
            if not self.active or o.runtime.generation != generation:
                timer.stop()
                timer.deleteLater()
                return
            if not o.engine.busy and not o.engine.running:
                timer.stop()
                timer.deleteLater()
                if not o.engine.lease.path.exists():
                    o.runtime.connect()
                else:
                    self.message(
                        "Proxy recovery remains pending; restart was canceled."
                    )

        timer.timeout.connect(ready)
        timer.start()

    def restore_proxy(self):
        o = self.owner
        if o.engine.running or o.engine.busy:
            return self.message(
                "Disconnect before restoring previous Windows proxy settings."
            )
        if not o.engine.lease.path.exists():
            return self.output("No pending proxy recovery record.")
        if (
            QMessageBox.question(
                self,
                self.tr("Restore previous proxy"),
                "Restore the saved WinINET settings only if this application still owns the proxy? Changes from other applications will be preserved.",
            )
            != QMessageBox.Yes
        ):
            return

        def restore(cancel):
            check_cancel(cancel)
            o.engine.lease.restore()
            return "Recovery finished. External proxy changes were respected. No routes or firewall rules changed."

        self.execute(restore)

    def export_bundle(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export support ZIP"),
            "NekoRayNext-support.zip",
            "ZIP (*.zip)",
        )
        if path:
            self.execute(
                lambda cancel: (check_cancel(cancel), support_bundle(path, self.owner))[
                    1
                ]
            )

    def error_guide(self):
        self.output(
            "\n\n".join(code + "\n" + message for code, message in MESSAGES.items())
        )

    def clear_history(self):
        self.owner.history_errors.clear()
        self.owner.logs.clear()
        self.output("Sanitized in-memory history cleared. No profile data was removed.")

    def test_sound(self):
        if not hasattr(self.owner, "sounds") or not self.owner.sounds.available:
            return self.message(
                "Sound playback requires Windows native audio. No audio backend is available here."
            )
        if not self.owner.sounds.play("connected"):
            self.message("Enable sound in Interface & Tray and Apply, then test again.")

    def refresh_dynamic(self):
        if hasattr(self, "quota_layout"):
            while self.quota_layout.count():
                item = self.quota_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for sub in self.owner.subscriptions:
                self.quota_layout.addWidget(quota_row(sub, self.fa))
        if hasattr(self, "sub_status"):
            lines = []
            for sub in self.owner.subscriptions:
                count = sum(p.subscription_id == sub.id for p in self.owner.profiles)
                from .usage import subscription_usage

                metadata = getattr(sub, "metadata", {})
                usage = subscription_usage(metadata)
                remaining = usage.remaining if usage.known else None
                quota = (
                    f"{remaining} bytes remaining (provider supplied)"
                    if remaining is not None
                    else "quota not supplied"
                )
                expiry = (
                    str(metadata.get("expire")) + " (Unix timestamp, provider supplied)"
                    if "expire" in metadata
                    else "expiration not supplied"
                )
                lines.append(
                    f'{sub.name} · {count} profiles · {sub.updated_at or "not updated"}\n  Status: {getattr(sub,"status","unknown")} · {quota} · {expiry}\n  Last error: {getattr(sub,"last_error","") or "none"}'
                )
            self.sub_status.setText(
                (
                    str(len(self.owner.subscriptions))
                    + (" اشتراک ذخیره‌شده" if self.fa else " saved subscriptions")
                )
                if lines
                else self.tr("No subscriptions.")
            )
            self.sub_status.setToolTip("\n".join(lines))
        if hasattr(self, "telegram_list"):
            selected = self.telegram_list.currentRow()
            self.telegram_list.clear()
            for p in self.telegram:
                self.telegram_list.addItem(
                    p.kind + " · " + p.server + ":" + str(p.port)
                )
            if self.telegram:
                self.telegram_list.setCurrentRow(
                    max(0, min(selected, len(self.telegram) - 1))
                )
        self.refresh_statistics()

    def refresh_statistics(self):
        if hasattr(self,"traffic_page"):self.traffic_page.refresh()
        if not hasattr(self, "stats"):
            return
        o = self.owner
        lines = [
            f"Core: Xray · {o.status}",
            (
                f"HTTPS latency: {o.latency_ms:.0f} ms"
                if o.latency_ms is not None
                else "HTTPS latency: not measured"
            ),
            f'Last verified health: {o.engine.last_check or "not measured"}',
            f"Download: {o.stat_values[0].text()} · {o.stat_notes[0].text()}",
            f"Upload: {o.stat_values[1].text()} · {o.stat_notes[1].text()}",
            f'Retry budget used: {o.runtime.attempt if hasattr(o,"runtime") else 0}',
            f'Failure count: {sum(x.get("failures",0) for x in o.settings.get("reliability",{}).values())}',
        ]
        self.stats.setText("\n".join(lines))

    def import_telegram(self):
        if self.telegram_error:
            return self.message(
                "The protected Telegram store could not be opened. It was preserved. Recover it using the original Windows account before adding entries."
            )
        d = QDialog(self)
        d.setWindowTitle(self.tr("Import Telegram proxy"))
        d.resize(520, 240)
        v = QVBoxLayout(d)
        self.note(
            "Paste a Telegram proxy link. Credentials remain hidden. MTProto is not a system VPN.",
            v,
        )
        edit = QLineEdit()
        edit.setEchoMode(QLineEdit.Password)
        edit.setPlaceholderText("tg://proxy?… / https://t.me/socks?…")
        edit.setLayoutDirection(Qt.LeftToRight)
        v.addWidget(edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        v.addWidget(buttons)
        buttons.rejected.connect(d.reject)

        def save():
            try:
                proxy = parse_telegram(edit.text())
                items = self.telegram + [proxy]
                self.telegram_store.save(items)
                self.telegram = items
                self.refresh_dynamic()
                d.accept()
            except ValueError as e:
                self.message(str(e))
            except Exception:
                self.message(
                    "Could not protect or save Telegram proxy. Existing entries were preserved."
                )

        buttons.accepted.connect(save)
        d.exec()

    def manual_telegram(self):
        if self.telegram_error:
            return self.message(
                "Protected Telegram store could not be opened; existing data was preserved."
            )
        from urllib.parse import urlencode

        d = QDialog(self)
        d.setWindowTitle(self.tr("Manual proxy metadata"))
        v = QVBoxLayout(d)
        f = QFormLayout()
        kind = QComboBox()
        kind.addItems(["MTProto", "SOCKS5"])
        f.addRow("Type", kind)
        fields = {}
        for key, title in [
            ("server", "Server"),
            ("port", "Port"),
            ("secret", "MTProto secret (hex)"),
            ("user", "SOCKS username"),
            ("pass", "SOCKS password"),
        ]:
            edit = QLineEdit()
            edit.setLayoutDirection(Qt.LeftToRight)
            if key in ("secret", "pass"):
                edit.setEchoMode(QLineEdit.Password)
            fields[key] = edit
            f.addRow(title, edit)

        def visibility():
            f.setRowVisible(fields["secret"], kind.currentIndex() == 0)
            for key in ("user", "pass"):
                f.setRowVisible(fields[key], kind.currentIndex() == 1)

        kind.currentIndexChanged.connect(visibility)
        visibility()
        v.addLayout(f)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        v.addWidget(buttons)
        buttons.rejected.connect(d.reject)

        def save():
            query = {
                key: edit.text().strip()
                for key, edit in fields.items()
                if f.isRowVisible(edit)
            }
            try:
                proxy = parse_telegram(
                    "tg://"
                    + ("proxy" if kind.currentIndex() == 0 else "socks")
                    + "?"
                    + urlencode(query)
                )
                items = self.telegram + [proxy]
                self.telegram_store.save(items)
                self.telegram = items
                self.refresh_dynamic()
                d.accept()
            except ValueError as e:
                self.message(str(e))
            except Exception:
                self.message(
                    "Could not protect or save Telegram proxy. Previous entries were preserved."
                )

        buttons.accepted.connect(save)
        d.exec()

    def selected_telegram(self):
        row = self.telegram_list.currentRow()
        return self.telegram[row] if 0 <= row < len(self.telegram) else None

    def test_telegram(self):
        proxy = self.selected_telegram()
        if not proxy:
            return self.message("Select a saved Telegram proxy.")
        from .network import tcp_latency

        self.execute(
            lambda cancel: f"TCP: {tcp_latency(proxy.server,proxy.port,4):.0f} ms. Authentication and MTProto handshake were not tested."
        )

    def use_telegram_transport(self):
        proxy=self.selected_telegram()
        if not proxy:return self.message("Select a saved Telegram proxy.")
        from .telegram_transport import as_profile
        from .profiles import ProfileError
        try:self.owner.import_done([as_profile(proxy.link())],"Profiles imported.")
        except ProfileError as error:self.message(self.tr(str(error)))

    def open_telegram(self):
        proxy = self.selected_telegram()
        if not proxy:
            return self.message("Select a saved Telegram proxy.")
        if (
            QMessageBox.warning(
                self,
                self.tr("Open in Telegram"),
                "Unknown proxies can observe connection metadata. Open this proxy in the locally installed Telegram client? Credentials will be passed to Telegram using its supported link handler.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        if not QDesktopServices.openUrl(QUrl(proxy.link())):
            self.message(
                "Telegram URL handler is not installed or could not be opened."
            )

    def remove_telegram(self):
        proxy = self.selected_telegram()
        if not proxy:
            return
        if (
            QMessageBox.question(
                self, self.tr("Remove selected"), "Remove this saved Telegram proxy?"
            )
            != QMessageBox.Yes
        ):
            return
        try:
            items = [p for p in self.telegram if p.id != proxy.id]
            self.telegram_store.save(items)
            self.telegram = items
            self.refresh_dynamic()
        except Exception:
            self.message("Could not save the removal. Existing entries were preserved.")
