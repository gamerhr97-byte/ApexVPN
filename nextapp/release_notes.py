"""Acknowledge each installed release once; never replace the user's preferences."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from .branding import VERSION

NOTES_FA = (
    'بازگشت در تنظیمات مرحله‌ای است: از زیرصفحه به فهرست تنظیمات و از آنجا به خانه.',
    'جست‌وجوی پنجرهٔ سرویس‌ها حذف شد؛ موفق/ناموفق با رنگ سبز/قرمز کارت‌ها مشخص می‌شود.',
    'Minimize مستقیماً از گذار بومی Windows استفاده می‌کند تا کوچک‌شدن فوری و قابل‌اعتماد باشد.',
    'نسخهٔ برنامه و لانچرها به 1.11.0 ارتقا یافتند؛ تنظیمات و اشتراک‌های قبلی حفظ می‌شوند.',
)
NOTES_EN = (
    'Settings back navigation is staged: detail to categories, then categories to Home.',
    'Service search is removed; green/red card backgrounds show successful/failed checks.',
    'Minimize uses the native Windows transition so the window state changes immediately.',
    'The app and native launchers are now 1.11.0; existing settings and subscriptions are preserved.',
)


def show_release_notes(owner, force=False):
    if not force and owner.settings.get('release_seen') == VERSION:
        return
    if getattr(owner, 'release_dialog', None) is not None and owner.release_dialog.isVisible():
        return
    dialog = QDialog(owner)
    dialog.setWindowTitle(owner.t('What changed') + ' · ' + VERSION)
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.setStyleSheet(owner.styleSheet())
    layout = QVBoxLayout(dialog)
    fa = owner.t('Settings') == 'تنظیمات'
    title = QLabel(('تغییرات نسخهٔ ' if fa else 'What changed in ') + VERSION)
    layout.addWidget(title)
    for text in (NOTES_FA if fa else NOTES_EN):
        label = QLabel('• ' + text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.PlainText)
        layout.addWidget(label)
    done = QPushButton('متوجه شدم' if fa else 'Got it')
    layout.addWidget(done)

    def acknowledge():
        candidate = dict(owner.settings, release_seen=VERSION)
        try:
            owner.store.save_settings(candidate)
        except OSError:
            owner.notice('Could not save release acknowledgement.')
            return
        owner.settings = candidate
        dialog.accept()

    done.clicked.connect(acknowledge)
    dialog.resize(min(420, owner.width() - 28), 470)
    owner.release_dialog = dialog
    # Drop the reference before the Qt wrapper is destroyed.
    dialog.finished.connect(lambda _: setattr(owner, 'release_dialog', None))
    dialog.show()
