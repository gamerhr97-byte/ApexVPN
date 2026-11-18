"""Compact server catalog. Subscription identity is explicit and never inferred from names."""

import weakref
from PySide6.QtCore import Qt, QSize, QPoint, QTimer, Signal
from PySide6.QtGui import QColor, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QProgressBar,
    QMenu,
    QSizePolicy,
    QFrame,
    QListWidget,
    QDialog,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
)
from .usage import subscription_usage, size
from .profile_testing import result_text
from .feedback import improve_scroll


class SourceDelegate(QStyledItemDelegate):
    """Elided, two-line quota cards with a stable inset progress track."""
    def __init__(self, parent, dark=False, apex=False):
        super().__init__(parent)
        self.dark = dark
        self.apex = apex

    def paint(self, painter, option, index):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QFont
        painter.save()
        painter.setRenderHint(__import__("PySide6.QtGui",fromlist=["QPainter"]).QPainter.Antialiasing)
        rect = option.rect.adjusted(2, 3, -2, -3)
        selected = bool(option.state & QStyle.State_Selected)
        dark = self.dark
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#321421' if self.apex else '#354D75' if dark else '#E5EEFF') if selected else QColor(110,140,180,12))
        painter.drawRoundedRect(rect, 10, 10)
        text = str(index.data() or '').split('\n',1)
        font = QFont(option.font); font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#E7EFFB" if dark else "#24334C"))
        title_rect = rect.adjusted(12, 3, -12, -24)
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft | Qt.TextForceLeftToRight,
                         painter.fontMetrics().elidedText(text[0], Qt.ElideRight, title_rect.width()))
        font.setBold(False); font.setPointSize(max(8,font.pointSize()-1)); painter.setFont(font)
        if len(text)>1:
            detail_rect = rect.adjusted(12, 22, -12, -8)
            painter.setPen(QColor('#91A2BF' if dark else '#70819C'))
            painter.drawText(detail_rect, Qt.AlignVCenter | Qt.AlignLeft | Qt.TextForceLeftToRight,
                             painter.fontMetrics().elidedText(text[1], Qt.ElideRight, detail_rect.width()))
        percent = index.data(Qt.UserRole+1)
        if percent is not None:
            track = QRectF(rect.left()+12,rect.bottom()-5,rect.width()-24,3)
            painter.setPen(Qt.NoPen); painter.setBrush(QColor(100,140,210,32)); painter.drawRoundedRect(track,1.5,1.5)
            track.setWidth(track.width()*max(0,min(100,percent))/100)
            painter.setBrush(QColor('#6B96EB')); painter.drawRoundedRect(track,1.5,1.5)
        painter.restore()


class SourcePage(QFrame):
    def __init__(self,owner):super().__init__();self.owner=weakref.proxy(owner)
    def accept(self):self.owner.navigate(1)
    def reject(self):self.owner.navigate(1)

class SubscriptionPicker(QPushButton):
    """A navigation button with a small catalog model, not a drop-down control."""
    currentIndexChanged=Signal(int)
    def __init__(self):
        super().__init__();self.items=[];self.index=-1;self.clicked.connect(self.showPopup)
    def clear(self):self.items=[];self.index=-1;self.setText('')
    def count(self):return len(self.items)
    def addItem(self,text,data=None):
        self.items.append((text,data))
        if self.index<0:self.setCurrentIndex(0)
    def itemData(self,index):return self.items[index][1] if 0<=index<len(self.items) else None
    def itemText(self,index):return self.items[index][0] if 0<=index<len(self.items) else ''
    def currentData(self):return self.itemData(self.index)
    def currentText(self):return self.itemText(self.index)
    def currentIndex(self):return self.index
    def findData(self,value):return next((i for i,item in enumerate(self.items) if item[1]==value),-1)
    def setCurrentIndex(self,index):
        if not 0<=index<len(self.items):return
        changed=self.index!=index;self.index=index;self.setText(self.currentText()+'  ›')
        if changed:self.currentIndexChanged.emit(index)

    def showPopup(self):
        owner=self.window()
        if hasattr(self,'sheet'):
            owner.stack.removeWidget(self.sheet);self.sheet.deleteLater()
        theme = owner.settings["theme"]
        dark = theme in ("Dark", "Apex")
        apex = theme == "Apex"
        self.sheet = SourcePage(owner)
        owner=weakref.proxy(owner)
        self.sheet.setWindowModality(Qt.WindowModal)
        self.sheet.setObjectName("sourceSheet")
        self.sheet.setLayoutDirection(Qt.LeftToRight)
        self.sheet.setWindowTitle(owner.t("Subscriptions"))
        bg, fg, selected, border = (("#120C12", "#EFF5FF", "#321421", "#3F3150")
            if apex else ("#202B40", "#EFF5FF", "#3F5B88", "#53657D")
            if dark else ("#F8FAFF", "#24334C", "#E0EBFF", "#D6E1F2"))
        self.sheet.setStyleSheet(owner.styleSheet() +
            f"#sourceSheet{{background:{bg};border:0;border-radius:14px;}}"
            f"#sourceSheet QListWidget{{background:transparent;border:0;color:{fg};outline:0;}}"
            f"#sourceSheet QListWidget::item{{margin:3px 0;padding:6px 10px;border-radius:9px;}}"
            f"#sourceSheet QListWidget::item:selected{{background:{selected};color:{fg};}}"
            f"#sourceSheet QPushButton:pressed{{background:{selected};}}")
        layout = QVBoxLayout(self.sheet)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(7)
        header = QHBoxLayout()
        header.addWidget(QLabel(owner.t("Subscriptions")), 1)
        close = QPushButton()
        from .service_icons import symbol_icon
        close.setIcon(symbol_icon("close"))
        close.setAccessibleName(owner.t("Close"))
        close.setFixedSize(32, 32)
        close.clicked.connect(self.sheet.reject)
        header.addWidget(close)
        layout.addLayout(header)
        search = QLineEdit()
        search.setPlaceholderText(self.window().t("Search subscriptions…"))
        layout.addWidget(search)
        listing = QListWidget()
        listing.setItemDelegate(SourceDelegate(listing, dark, apex))
        listing.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        listing.setContextMenuPolicy(Qt.CustomContextMenu)
        improve_scroll(listing)
        layout.addWidget(listing)
        from collections import Counter
        counts = Counter(p.subscription_id for p in owner.profiles)
        for index in range(self.count()):
            text = self.itemText(index)
            source = next((sub for sub in owner.subscriptions if sub.id == self.itemData(index)), None)
            if source:
                import datetime
                usage = subscription_usage(source.metadata)
                quota = (f"{size(usage.used)} / {size(usage.total)} · {usage.percent:.1f}%"
                         if usage.known else owner.t("Usage unknown"))
                expiry = source.metadata.get("expire")
                try:
                    expiry = datetime.datetime.fromtimestamp(expiry).strftime("%Y-%m-%d") if expiry else owner.t("Unknown")
                except (ValueError, OSError, TypeError, OverflowError):
                    expiry = owner.t("Unknown")
                saved_count=source.metadata.get('profile_count')
                count=saved_count if type(saved_count) is int and saved_count>=0 else counts[source.id]
                text = ("\u2068" + source.name + "\u2069" + f"  ·  {count} servers" + "\n"
                        + quota + "  ·  " + owner.t("Expires") + ": " + expiry)
            listing.addItem(text)
            listing.item(index).setData(Qt.UserRole, index)
            listing.item(index).setSizeHint(QSize(1, 62))
            if source and usage.known:
                listing.item(index).setData(Qt.UserRole+1, usage.percent)
            listing.item(index).setToolTip(text)
        listing.setCurrentRow(self.currentIndex())
        search.textChanged.connect(
            lambda text: [
                listing.item(i).setHidden(
                    text.casefold() not in listing.item(i).text().casefold()
                )
                for i in range(listing.count())
            ]
        )

        def choose(item):
            self.setCurrentIndex(item.data(Qt.UserRole))
            owner.manual_selection = False
            owner.servers_page.table.clearSelection()
            owner.servers_page.table.setCurrentCell(-1, -1)
            owner.refresh_profile()
            self.sheet.accept()

        preview = QProgressBar()
        preview.setRange(0, 1000)
        preview.setFixedHeight(6)
        preview.setTextVisible(False)
        layout.addWidget(preview)
        summary = QLabel()
        summary.setWordWrap(True)
        summary.setTextFormat(Qt.PlainText)
        layout.addWidget(summary)
        actions = QHBoxLayout()
        select = QPushButton("انتخاب" if owner.t("Settings") == "تنظیمات" else "Select")
        select.setProperty("kind", "primary")
        select.clicked.connect(lambda: choose(listing.currentItem()) if listing.currentItem() else None)
        actions.addWidget(select, 1)
        refresh = QPushButton()
        from .iconography import glyph_icon
        refresh.setIcon(glyph_icon('refresh', '#8BA8DD' if dark else '#5C82CF'))
        refresh.setIconSize(QSize(20, 20))
        refresh.setFixedSize(38, 38)
        refresh.setStyleSheet('padding:0;')
        refresh.setAccessibleName(owner.t("Refresh this subscription"))
        actions.addWidget(refresh)
        more = QPushButton("⋮")
        more.setFixedSize(38, 38)
        more.setStyleSheet('QPushButton{padding:0;font-size:20px;} QPushButton::menu-indicator{image:none;width:0;}')
        actions.addWidget(more)
        layout.addLayout(actions)

        def source():
            item = listing.currentItem()
            ident = self.itemData(item.data(Qt.UserRole)) if item else None
            return next((sub for sub in owner.subscriptions if sub.id == ident), None)

        def update_preview():
            sub = source()
            usage = subscription_usage(sub.metadata) if sub else None
            known = bool(usage and usage.known)
            preview.setEnabled(known)
            preview.setValue(round(min(100, usage.percent)*10) if known else 0)
            summary.setText((f"{size(usage.remaining)} " + ("باقی‌مانده" if owner.t("Settings") == "تنظیمات" else "remaining"))
                            if known else owner.t("Quota not supplied by provider.") if sub else "")
            refresh.setEnabled(bool(sub) and not owner.sub_busy)
            refresh.setToolTip(owner.t("Wait for the current operation to finish.") if owner.test_busy else owner.t("Refresh this subscription"))
            more.setEnabled(bool(sub))

        def manage(action, ident=None):
            item = listing.currentItem()
            sub = source()
            if ident is None:
                ident = sub.id if sub else None
            if item is None or sub is None or sub.id != ident:
                return
            combo_index = next(
                (i for i in range(self.count()) if self.itemData(i) == ident), -1
            )
            if combo_index < 0:
                return
            self.setCurrentIndex(combo_index)
            owner.servers_page.select_group(ident)
            self.sheet.accept()
            if action == 'refresh':
                owner.servers_page.refresh_group()
            else:
                owner.subscription_action(action, ident)

        def source_context(point):
            item=listing.itemAt(point)
            if item is None:return
            listing.setCurrentItem(item)
            sub=source()
            if sub is None:return
            context=QMenu(listing)
            titles=[('Copy subscription link','copy'),('Rename subscription','rename'),
                    ('Edit subscription link','edit')]
            if sub.is_free:titles.append(('Clear Free servers','clear'))
            else:titles.append(('Remove subscription','remove'))
            for title,action in titles:
                context.addAction(owner.t(title),lambda checked=False,key=action,ident=sub.id:manage(key,ident))
            context.exec(listing.mapToGlobal(point))
        listing.customContextMenuRequested.connect(source_context)

        def remove_selected_source():
            if listing.currentItem() is not None:
                sub=source()
                if sub:manage('clear' if sub.is_free else 'remove',sub.id)
        delete_source=QShortcut(QKeySequence.Delete,listing)
        delete_source.setContext(Qt.WidgetWithChildrenShortcut)
        delete_source.activated.connect(remove_selected_source)

        refresh.clicked.connect(lambda: manage('refresh'))
        menu = QMenu(more)
        def fill_more_menu():
            menu.clear();sub=source()
            if sub is None:return
            titles=[('Copy subscription link','copy'),('Rename subscription','rename'),
                    ('Edit subscription link','edit')]
            if sub.is_free:titles.append(('Clear Free servers','clear'))
            else:titles.append(('Remove subscription','remove'))
            for title,action in titles:
                menu.addAction(owner.t(title),lambda checked=False,key=action,ident=sub.id:manage(key,ident))
        menu.aboutToShow.connect(fill_more_menu)
        more.setMenu(menu)
        listing.itemSelectionChanged.connect(update_preview)
        listing.itemDoubleClicked.connect(choose)
        listing.itemActivated.connect(choose)
        update_preview()
        owner.stack.addWidget(self.sheet)
        owner.navigate(owner.stack.indexOf(self.sheet))
        search.setFocus()


class CleanSelectionDelegate(QStyledItemDelegate):
    """Keep keyboard selection and accessibility without a dotted cell rectangle."""
    def paint(self, painter, option, index):
        clean = QStyleOptionViewItem(option)
        clean.state &= ~QStyle.State_HasFocus
        super().paint(painter, clean, index)


class ServersPage(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        selected = owner.selected_profile()
        self.group = (
            selected.subscription_id
            if selected and selected.subscription_id
            else ("free" if any(s.is_free for s in owner.subscriptions)
                  and not any(not p.subscription_id for p in owner.profiles) else "local")
        )
        remembered = owner.settings.get('selected_group')
        if remembered in {'local', 'favorites', 'all','free'} | {sub.id for sub in owner.subscriptions}:
            self.group = remembered
        self.page_index = 0
        self.updating = False
        self.sort_verified = any(p.tested_at for p in owner.profiles)
        self.setObjectName("serversPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        top = QHBoxLayout()
        self.groups = SubscriptionPicker()
        self.groups.setObjectName("subscriptionGroups")
        self.groups.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.groups.setMinimumWidth(0)
        top.addWidget(self.groups, 1)
        self.refresh = QPushButton()
        from .iconography import glyph_icon

        self.refresh.setIcon(glyph_icon("refresh", "#5C82CF"))
        self.refresh.setIconSize(QSize(22, 22))
        self.refresh.setAccessibleName(owner.t("Refresh this subscription"))
        self.refresh.setObjectName("refreshSubscription")
        self.refresh.setFixedSize(40, 40)
        self.refresh.setToolTip(owner.t("Refresh this subscription"))
        self.refresh.clicked.connect(self.refresh_group)
        top.addWidget(self.refresh)
        self.more = QPushButton("⋮")
        self.more.setObjectName("serverMore")
        self.more.setStyleSheet(
            "QPushButton{padding:0;font-size:22px;} QPushButton::menu-indicator{image:none;width:0;}"
        )
        self.more.setFixedWidth(40)
        self.more.setAccessibleName(owner.t("More actions"))
        self.menu = QMenu(self.more)
        self.more.setMenu(self.menu)
        top.addWidget(self.more)
        layout.addLayout(top)
        self.quota = QProgressBar()
        self.quota.setObjectName("serverSubscriptionQuota")
        self.quota.setRange(0, 1000)
        self.quota.setTextVisible(False)
        self.quota.setFixedHeight(6)
        layout.addWidget(self.quota)
        self.quota_note = QLabel()
        self.quota_note.setWordWrap(True)
        self.quota_note.setProperty("kind", "muted")
        layout.addWidget(self.quota_note)
        self.search = QLineEdit()
        self.search.setPlaceholderText(owner.t("Search profiles…"))
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 2)
        self.table.setObjectName("compactServers")
        self.table.setLayoutDirection(Qt.LeftToRight)
        self.table.setItemDelegate(CleanSelectionDelegate(self.table))
        self.table.setHorizontalHeaderLabels([owner.t("Server"), owner.t("Result")])
        from .service_icons import server_icon
        server_header=QTableWidgetItem('')
        server_header.setIcon(server_icon())
        server_header.setToolTip(owner.t("Server"))
        server_header.setData(Qt.AccessibleTextRole,owner.t("Server"))
        self.table.setHorizontalHeaderItem(0,server_header)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 118)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.cellDoubleClicked.connect(lambda *_: owner.use_selected())
        self.table.itemSelectionChanged.connect(self.update_action)
        improve_scroll(self.table)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.profile_menu)
        QShortcut(
            QKeySequence.Delete,
            self.table,
            activated=owner.delete_selected,
            context=Qt.WidgetWithChildrenShortcut,
        )
        layout.addWidget(self.table, 1)
        self.empty = QLabel(owner.t("No servers in this group."))
        self.empty.setProperty("kind", "muted")
        self.empty.setWordWrap(True)
        layout.addWidget(self.empty)
        row = QHBoxLayout()
        self.method = QComboBox()
        self.method.addItem("سریع · TCP" if owner.t("Settings") == "تنظیمات" else "Quick · TCP", "TCP")
        self.method.addItem("HTTPS", "HTTPS")
        self.method.addItem("کیفیت · ۱۰۰ سایت" if owner.t("Settings") == "تنظیمات" else "Quality · 100 sites", "QUALITY")
        self.method.setCurrentIndex(0)
        self.method.setToolTip(
            owner.t("TCP: reachability only. HTTPS: actual verified proxy tunnel.")
        )
        row.addWidget(self.method)
        self.test = QPushButton(owner.t("Test group"))
        self.test.clicked.connect(self.test_group)
        row.addWidget(self.test)
        self.connect = QPushButton(owner.t("Connect"))
        self.connect.setProperty("kind", "primary")
        self.connect.clicked.connect(owner.use_selected)
        row.addWidget(self.connect, 1)
        layout.addLayout(row)
        self.table.verticalScrollBar().valueChanged.connect(self.scroll_page)
        self.progress = QProgressBar()
        self.progress.setObjectName("operationProgress")
        self.progress.setFixedHeight(7)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setProperty("kind", "muted")
        layout.addWidget(self.status)
        # Compatibility aliases live on Window; no duplicate controls are displayed.
        self.filter = QComboBox()
        self.filter.addItem("All protocols")
        self.filter.hide()
        self.menu.aboutToShow.connect(self.subscription_menu)
        self.groups.currentIndexChanged.connect(self.group_changed)
        self.search.textChanged.connect(self.reset_catalog)
        self.populate()
        self.elapsed = QTimer(self)
        self.elapsed.setInterval(1000)
        self.elapsed.timeout.connect(self.operation_progress)
        self.elapsed.start()

    def subscription_menu(self):
        self.menu.clear()
        sub = next((s for s in self.owner.subscriptions if s.id == self.group), None)
        if sub:
            actions=[
                ("Copy subscription link", "copy"),
                ("Rename subscription", "rename"),
                ("Edit subscription link", "edit"),
            ]
            if sub.is_free:actions.append(("Clear Free servers", "clear"))
            else:actions.append(("Remove subscription", "remove"))
            for title, action in actions:
                self.menu.addAction(
                    self.owner.t(title),
                    lambda checked=False, a=action, ident=sub.id: self.owner.subscription_action(a, ident),
                )
            self.menu.addSeparator()
        self.menu.addAction(
            self.owner.t("Subscriptions"), self.owner.manage_subscriptions
        )

    def profile_menu(self, point):
        item = self.table.itemAt(point)
        if item and not item.isSelected():
            self.table.selectRow(item.row())
        if not self.selected_id():
            return
        menu = QMenu(self)
        selected_count = len(self.table.selectionModel().selectedRows())
        remove_title = "Remove server" if selected_count == 1 else "Remove selected servers"
        for title, callback in [
            ("Connect (no ping required)", self.owner.use_selected),
            ("بررسی ۱۰۰ سایت" if self.owner.t("Settings") == "تنظیمات" else "Check 100 sites", lambda: self.owner.test_profiles(only=self.owner.table_profile(),quality=True)),
            ("Copy server link", self.owner.copy_server),
            ("Edit server link", self.owner.edit_server),
            ("Favorite · move to local", self.owner.favorite),
            (remove_title, self.owner.delete_selected),
        ]:
            menu.addAction(self.owner.t(title), callback)
        menu.exec(self.table.viewport().mapToGlobal(point))

    def operation_progress(self):
        owner = self.owner
        busy = owner.test_busy or owner.sub_busy
        self.progress.setVisible(busy)
        # Keep refresh reachable during a test so the owner sees the busy toast.
        # Running a refresh concurrently with a profile test is explicitly rejected.
        self.refresh.setEnabled(not owner.sub_busy and self.group not in ("local", "favorites"))
        self.refresh.setToolTip(owner.t("Wait for the current operation to finish.") if owner.test_busy else owner.t("Refresh this subscription"))
        self.groups.setEnabled(not owner.sub_busy)
        self.method.setEnabled(not busy)
        self.test.setEnabled(not owner.sub_busy)
        if owner.test_busy:
            import time

            seconds = int(
                time.monotonic() - getattr(owner, "test_started", time.monotonic())
            )
            self.progress.setRange(0, max(1, owner.test_total))
            self.progress.setValue(owner.test_completed)
            self.status.setText(
                f"{owner.test_completed} / {owner.test_total} · {seconds}s · "
                + owner.t("Testing…")
            )
        elif owner.sub_busy:
            self.progress.setRange(0, 0)
            self.status.setText(owner.t("Updating subscriptions…"))

    def test_group(self):
        if self.owner.test_busy:
            self.owner.cancel_tests()
        else:
            self.owner.test_profiles()

    def visible_profiles(self, ignore_search=False):
        text = "" if ignore_search else self.search.text().casefold()
        from .free_sources import free_ids
        free=free_ids(self.owner.subscriptions)
        hidden=getattr(self.owner,"free_failed_ids",set()) if self.owner.test_busy else set()
        profiles = [
            p for p in self.owner.profiles
            if (p.id not in hidden or p.id==self.owner.active_id)
            and (self.group=="free" and p.subscription_id in free or self.group == "local" and not p.subscription_id
                or self.group == "favorites" and p.favorite
                or p.subscription_id == self.group)
            and (not text or text in p.name.casefold() or text in p.protocol.casefold())
        ]
        # Stable while probes are in flight; sort only after a completed batch.
        if self.sort_verified and not self.owner.test_busy:
            from .ranking import rank
            profiles.sort(key=rank)
        return profiles

    def refresh_groups(self):
        selected = self.groups.currentData() or self.group
        from collections import Counter
        counts = Counter(p.subscription_id or "local" for p in self.owner.profiles)
        for sub in self.owner.subscriptions:
            saved_count=sub.metadata.get('profile_count')
            if type(saved_count) is int and saved_count>=0:
                counts[sub.id]=saved_count
        counts['favorites']=sum(bool(p.favorite) for p in self.owner.profiles)
        from .free_sources import free_ids
        free=free_ids(self.owner.subscriptions)
        counts["free"]=sum(counts[k] for k in free)
        values = (
            [("local", self.owner.t("Local profiles")), ("favorites", self.owner.t("Favorite servers"))]
            + [("free","Free")]+[(s.id,"  ↳ "+s.name) for s in self.owner.subscriptions if s.is_free]
            + [(s.id, s.name) for s in self.owner.subscriptions if not s.is_free]
        )
        self.groups.blockSignals(True)
        self.groups.clear()
        for key, title in values:
            count = counts[key]
            self.groups.addItem(f"{title}  ·  {count}", key)
        index = self.groups.findData(selected)
        self.groups.setCurrentIndex(max(0, index))
        self.group = self.groups.currentData()
        self.groups.blockSignals(False)

    def select_group(self, ident):
        self.group = ident
        self.refresh_groups()
        index = self.groups.findData(ident)
        if index >= 0:
            self.groups.setCurrentIndex(index)
            self.group = ident
        self.populate()

    def group_changed(self):
        self.page_index=0
        self.group = self.groups.currentData() or "local"
        if not self.updating:
            self.owner.manual_selection = False
            self.owner.settings['selected_group'] = self.group
            try:
                self.owner.store.save_settings(self.owner.settings)
            except OSError:
                self.owner.notice("Could not save source selection.")
            self.table.clearSelection()
            self.table.setCurrentCell(-1, -1)
            self.populate()
            if getattr(self.owner, "servers_page", None) is self:
                self.owner.refresh_profile()

    def populate(self, *_):
        if self.updating:
            return
        self.updating = True
        try:
            ident = self.selected_id()
            self.refresh_groups()
            profiles = self.visible_profiles()
            count = len(profiles)
            pages = max(1, (count + 99) // 100)
            self.page_index = min(self.page_index, pages - 1)
            profiles = profiles[self.page_index * 100:(self.page_index + 2) * 100]
            self.table.setUpdatesEnabled(False)
            self.table.setIconSize(QSize(76, 24))
            self.table.setRowCount(len(profiles))
            for row, profile in enumerate(profiles):
                values = [
                    profile.name,
                    (
                        self.owner.t(self.owner.testing_states[profile.id])
                        if profile.id in self.owner.testing_states
                        else result_text(profile, self.owner.t)
                    ),
                ]
                for column, text in enumerate(values):
                    item = QTableWidgetItem(text)
                    item.setData(Qt.UserRole, profile.id)
                    if column == 0:
                        from .service_icons import row_server_icon
                        from .service_icons import profile_country_code
                        item.setIcon(row_server_icon(profile.protocol,profile.gemini_ok,profile.service_score is not None and profile.service_score >= 90,profile_country_code(profile)))
                    if column == 1:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    item.setToolTip(
                        profile.protocol.upper() + " · " + text
                        + " · Gemini public page · Coverage: at least 90/100 destinations (not reputation)"
                        if column == 0
                        else self.owner.t(
                            "TCP: reachability only. HTTPS: actual verified proxy tunnel."
                        )
                    )
                    if column == 1 and profile.latency is None and profile.tested_at:
                        item.setForeground(QColor("#EF6A78"))
                    self.table.setItem(row, column, item)
                self.table.setRowHeight(row, 44)
                if profile.id == ident:
                    self.table.selectRow(row)
            if not ident:
                self.table.clearSelection()
                self.table.setCurrentCell(-1, -1)
            self.empty.setVisible(not profiles)
            self.refresh_quota()
            self.update_action()
        finally:
            self.table.setUpdatesEnabled(True)
            self.updating = False

    def reset_catalog(self, *_):
        self.page_index=0
        self.populate()

    def scroll_page(self, value):
        bar=self.table.verticalScrollBar()
        count=len(self.visible_profiles())
        if not self.updating and bar.maximum()>0 and value == bar.maximum() and (self.page_index+2)*100<count:
            anchor=max(0,value-100)
            self.page_index+=1
            self.populate()
            QTimer.singleShot(0,lambda a=anchor:self.table.verticalScrollBar().setValue(a))
        elif not self.updating and value == 0 and self.page_index>0:
            anchor=100
            self.page_index-=1
            self.populate()
            QTimer.singleShot(0,lambda a=anchor:self.table.verticalScrollBar().setValue(a))

    def change_page(self, delta):
        self.page_index = max(0, self.page_index + delta)
        self.populate()

    def selected_id(self):
        if not self.table.selectionModel().hasSelection():
            return ""
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.UserRole) if item else ""

    def refresh_quota(self):
        sub = next((s for s in self.owner.subscriptions if s.id == self.group), None)
        usage = subscription_usage(getattr(sub, "metadata", {}))
        self.quota.setVisible(sub is not None)
        self.quota_note.setVisible(sub is not None)
        if usage.known:
            self.quota.setEnabled(True)
            self.quota.setValue(round(min(100, usage.percent) * 10))
            self.quota_note.setText(
                f"{usage.percent:.1f}% · {size(usage.used)} / {size(usage.total)}"
            )
            self.quota.setToolTip(
                self.owner.t("Provider snapshot") + " · " + sub.updated_at
            )
        else:
            self.quota.setEnabled(False)
            self.quota.setValue(0)
            self.quota_note.setText(self.owner.t("Quota not supplied by provider."))

    def refresh_group(self):
        if self.group in ('local','favorites'):
            return
        if self.group=="free":
            self.owner.start_subscriptions([s for s in self.owner.subscriptions if s.is_free])
            return
        sub = next((s for s in self.owner.subscriptions if s.id == self.group), None)
        if sub:
            self.owner.start_subscriptions([sub])
        else:
            self.owner.update_subscriptions()
        self.operation_progress()

    def update_action(self):
        self.operation_progress()
        self.connect.setText(
            self.owner.t(
                ("Switch server" if self.owner.engine.running else "Connect")
                if self.selected_id()
                else "Auto connect group"
            )
        )
        self.connect.setEnabled(
            bool(self.visible_profiles()) and not self.owner.sub_busy
        )
        self.test.setText(
            self.owner.t("Cancel tests" if self.owner.test_busy else "Test group")
        )
