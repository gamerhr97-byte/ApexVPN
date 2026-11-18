"""One user action: restore/stop old core, then validate/start exactly the selected profile."""

import time
from PySide6.QtCore import QObject, QTimer


class ConnectionSwitch(QObject):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.target = ""
        self.deadline = 0
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self.poll)

    @property
    def pending(self):
        return bool(self.target)

    def cancel(self):
        self.timer.stop()
        self.target = ""

    def request(self, profile):
        owner = self.owner
        if owner.settings["mode"] == "Disabled":
            return owner.notice("Connections are disabled in Settings.")
        if (owner.engine.running and not owner.engine.busy
                and owner.active_id == profile.id and not owner.engine.cancel.is_set()):
            self.cancel()
            return
        owner.runtime.stop()
        self.target = profile.id
        self.deadline = time.monotonic() + 30
        if hasattr(owner, "service_checks"):
            owner.service_checks.cancel()
        if owner.engine.running or owner.engine.busy:
            owner.engine.disconnect()
        self.timer.start()
        self.poll()

    def poll(self):
        owner = self.owner
        if time.monotonic() > self.deadline:
            self.cancel()
            owner.notice(
                "Server switch timed out while waiting for the previous operation. No additional core was started."
            )
            return
        if owner.engine.running or owner.engine.busy or owner.sub_busy:
            return
        profile = next((p for p in owner.profiles if p.id == self.target), None)
        self.cancel()
        if not profile:
            return
        if owner.engine.lease.path.exists():
            owner.connection_state(
                "Error",
                "Previous proxy recovery is still pending. New core was not started.",
            )
            return
        owner.selected = profile.id
        owner.settings["selected"] = profile.id
        try:
            owner.store.save_settings(owner.settings)
        except OSError:
            owner.add_diagnostic(
                "[PREFERENCES] Could not save the selected preference."
            )
        owner.runtime.connect_to(profile)
