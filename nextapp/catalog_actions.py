"""Explicit catalog edits, atomic backups and credential-safe feedback."""

import copy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
)
from .profiles import parse_import, ProfileError


def edit_text(owner, title, value, multiline=False):
    dialog = QDialog(owner)
    dialog.setWindowTitle(owner.t(title))
    dialog.resize(390, 220 if multiline else 130)
    layout = QVBoxLayout(dialog)
    note = QLabel(owner.t("Keep this link private; it can contain credentials."))
    note.setWordWrap(True)
    layout.addWidget(note)
    field = QPlainTextEdit(value) if multiline else QLineEdit(value)
    field.setLayoutDirection(Qt.LeftToRight)
    layout.addWidget(field)
    buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if dialog.exec() == QDialog.Accepted:
        return (field.toPlainText() if multiline else field.text()).strip()
    return None


def copy_server(owner):
    profile = owner.table_profile()
    if profile:
        QApplication.clipboard().setText(profile.original)
        owner.notice(owner.t("Server link copied."))


def edit_server(owner):
    profile = owner.table_profile()
    if not profile:
        return
    if (
        owner.sub_busy
        or owner.test_busy
        or owner.switcher.pending
        or (owner.engine.running or owner.engine.busy)
        and profile.id == owner.active_id
    ):
        return owner.notice(
            owner.t(
                "Wait for testing/update, or disconnect the active server before editing it."
            )
        )
    text = edit_text(owner, "Edit server link", profile.original, True)
    if text is None:
        return
    try:
        incoming = parse_import(text)
        if len(incoming) != 1:
            raise ProfileError("Enter exactly one server link.")
        replacement = incoming[0]
        replacement.id = profile.id
        replacement.favorite = profile.favorite
        replacement.favorite_source_id = profile.favorite_source_id
        replacement.subscription_id = profile.subscription_id
        profiles = [replacement if p.id == profile.id else p for p in owner.profiles]
        owner.store.backup()
        owner.store.save_catalog(profiles, owner.subscriptions)
    except Exception:
        return owner.notice(
            owner.t("Could not save this server link. Previous profile kept.")
        )
    owner.profiles = profiles
    owner.populate()
    owner.refresh_profile()
    owner.notice(owner.t("Server saved. Subscription refresh may replace this edit."))


def subscription_action(owner, action, subscription_id=None):
    ident = subscription_id or owner.servers_page.group
    sub = next((s for s in owner.subscriptions if s.id == ident), None)
    if not sub:
        return
    if action == "copy":
        QApplication.clipboard().setText(sub.url)
        return owner.notice(owner.t("Subscription link copied."))
    if owner.sub_busy or owner.test_busy or owner.switcher.pending:
        return owner.notice(owner.t("Wait for the current operation to finish."))
    profiles = copy.deepcopy(owner.profiles)
    subs = copy.deepcopy(owner.subscriptions)
    item = next(s for s in subs if s.id == sub.id)
    old_settings=copy.deepcopy(owner.settings)
    if item.is_free and action == "remove":
        action = "clear"
    if action in ("remove", "clear"):
        removing_link = action == "remove"
        if action == "clear" and not item.is_free:
            return
        active = next((p for p in profiles if p.id == owner.active_id), None)
        if (
            (owner.engine.running or owner.engine.busy)
            and active
            and active.subscription_id == sub.id
        ):
            return owner.notice(
                owner.t("Disconnect this subscription before removing it.")
            )
        if (
            QMessageBox.question(
                owner,
                owner.t("Remove subscription" if removing_link else "Clear Free servers"),
                owner.t(
                    "Remove this Free provider link and its servers? The Free group and other sources will remain."
                    if item.is_free and removing_link else
                    "Clear this Free source's downloaded servers? The source link will remain available to refresh."
                    if item.is_free else
                    "Remove this subscription and all its servers? A backup will be retained."
                ),
            )
            != QMessageBox.Yes
        ):
            return
        profiles = [p for p in profiles if p.subscription_id != sub.id]
        if removing_link:
            subs.remove(item)
        elif item.is_free:
            item.status='unknown';item.updated_at='';item.last_error='';item.metadata={}
    else:
        if item.is_free and action not in ('rename',):
            return owner.notice(owner.t('Free source URLs are fixed. Add a separate personal subscription instead.'))
        value = edit_text(
            owner,
            "Rename subscription" if action == "rename" else "Edit subscription link",
            sub.name if action == "rename" else sub.url,
        )
        if not value:
            return
        if action == "rename":
            item.name = value[:200]
        else:
            from urllib.parse import urlsplit

            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                return owner.notice(
                    owner.t("Enter a name and an HTTPS subscription URL.")
                )
            item.url = value
    try:
        owner.store.backup()
        owner.store.save_settings(owner.settings)
        owner.store.save_catalog(profiles, subs)
    except Exception:
        owner.settings=old_settings
        try:owner.store.save_settings(old_settings)
        except Exception:pass
        return owner.notice(owner.t("Could not save. Existing data kept."))
    owner.profiles, owner.subscriptions = profiles, subs
    if not any(p.id == owner.selected for p in profiles):
        owner.selected = profiles[0].id if profiles else ""
    owner.populate()
    if action in ("remove", "clear"):
        if action=='clear':
            owner.servers_page.select_group(sub.id)
        else:
            owner.servers_page.select_group("free" if sub.is_free else "local")
    owner.refresh_profile()
    owner.configure_tray()
    owner.notice(owner.t("Subscription removed." if action=='remove' else "Subscription saved."))
