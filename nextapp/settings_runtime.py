"""Connection orchestration configured exclusively from Settings."""

import time, datetime
from PySide6.QtCore import QObject, QTimer
from .profiles import make_config
from .settings_services import on_battery


class SettingsRuntime(QObject):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.manual = True
        self.attempt = 0
        self.queue = []
        self.was_connected = False
        self.stable_since = 0
        self.connected_at = 0
        self.subscription_retry = 0
        self.sub_failures = 0
        self.health_elapsed = 0
        self.closed = False
        self.generation = 0
        self.retry = QTimer(self)
        self.retry.setSingleShot(True)
        self.retry.timeout.connect(self._retry)
        owner.engine.state.connect(self.state)

    def stop(self):
        self.manual = True
        self.generation += 1
        self.retry.stop()
        self.queue = []

    def shutdown(self):
        self.closed = True
        self.stop()

    def record(self, success):
        o = self.owner
        if not o.active_id:
            return
        stats = o.settings.setdefault("reliability", {})
        entry = stats.setdefault(
            o.active_id, {"success": 0, "failures": 0, "latency": None}
        )
        key = "success" if success else "failures"
        entry[key] = min(10000, entry.get(key, 0) + 1)
        if success:
            entry["latency"] = o.latency_ms
            entry["verified_at"] = time.time()
        try:
            o.store.save_settings(o.settings)
        except OSError:
            if hasattr(o, "add_diagnostic"):
                o.add_diagnostic(
                    "[PREFERENCES] Reliability history could not be saved."
                )

    def candidates(self):
        o = self.owner
        p = o.selected_profile()
        if not o.settings["smart_connect"]:
            return [p] if p else []
        if p and p.favorite:
            pool = [p]  # An explicitly selected favorite is pinned.
        else:
            pool = list(o.profiles)
        compatible = []
        for item in pool:
            try:
                from .engine import connection_config
                connection_config(item,o.settings)
                compatible.append(item)
            except Exception:
                continue
        history = o.settings.get("reliability", {})
        policy = o.settings["smart_policy"]

        def score(item):
            h = history.get(item.id, {})
            good = h.get("success", 0)
            bad = h.get("failures", 0)
            reliability = (good + 1) / (good + bad + 2)
            # TCP latency from the server list is deliberately excluded.
            latency = (
                h.get("latency")
                if h.get("verified_at", 0) > time.time() - 7 * 86400
                else None
            )
            latency = (
                latency
                if isinstance(latency, (int, float)) and latency >= 0
                else 1_000_000
            )
            if policy == "Lowest latency":
                return (latency, bad)
            if policy == "Highest stability":
                return (-reliability, latency)
            if policy == "Manual preferred":
                return (item.id != o.selected, -reliability, latency)
            return (bad > good + 2, latency / (reliability or 0.01), -reliability)

        return sorted(compatible, key=score)

    def connect(self):
        o = self.owner
        if o.settings["mode"] == "Disabled":
            o.notice(
                "Connections are disabled in Settings → Proxy & Windows Integration."
            )
            return
        self.stop()
        self.manual = False
        self.attempt = 0
        self.was_connected = False
        self.queue = self.candidates()
        if not self.queue:
            o.notice(
                "No compatible profile is available. Original profiles were preserved."
            )
            return
        self._start(self.queue.pop(0))

    def connect_to(self, profile):
        self.stop()
        self.manual = False
        self.attempt = 0
        self.was_connected = False
        self.queue = []
        self._start(profile)

    def _start(self, p):
        if self.manual or self.closed:
            return
        o = self.owner
        if hasattr(o, "add_diagnostic"):
            o.add_diagnostic("[CORE] Starting a verified connection attempt.", "Debug")
        from .settings_policy import effective_settings

        o.active_id = p.id
        o.selected = p.id
        o.refresh_profile()
        o.prev_traffic = None
        o.activity.history.clear()
        o.engine.connect_profile(p, effective_settings(o.settings))

    def state(self, status, note):
        if self.closed:
            return
        if status == "Connected":
            self.retry.stop()
            self.queue = []
            self.was_connected = True
            self.connected_at = time.monotonic()
            self.record(True)
            self.health_elapsed = 0
            if hasattr(self.owner, "add_diagnostic"):
                self.owner.add_diagnostic("[STATE] HTTPS connection verified.", "Info")
        elif status == "Error" and not self.manual:
            self.record(False)
            o = self.owner
            allow = bool(self.queue) or (
                self.was_connected
                and (
                    o.settings["auto_reconnect"]
                    or o.settings["auto_recover_core"]
                    and "crash" in note.lower()
                )
            )
            from .settings_policy import effective_settings

            effective = effective_settings(o.settings)
            if allow and self.attempt < effective["retry_attempts"]:
                delay = min(
                    300,
                    effective["retry_delay"]
                    * (2 ** self.attempt if effective["retry_backoff"] else 1),
                )
                self.attempt += 1
                self.retry.start(delay * 1000)

    def _retry(self):
        o = self.owner
        if self.manual or self.closed:
            return
        if o.engine.busy:
            self.retry.start(100)
            return
        if o.engine.running or o.sub_busy:
            return
        if self.queue:
            p = self.queue.pop(0)
        else:
            candidates = self.candidates()
            p = candidates[0] if candidates else None
        if p:
            self._start(p)

    def tick(self, elapsed):
        from .settings_policy import effective_settings

        o = self.owner
        s = effective_settings(o.settings)
        if o.engine.running:
            # A short-lived success cannot reset the retry budget and produce a restart loop.
            if time.monotonic() - self.connected_at >= 60:
                self.attempt = 0
            if s["monitor"]:
                self.health_elapsed += elapsed
                interval = (
                    s["failure_interval"] if self.attempt else s["stable_interval"]
                )
                if s["lightweight"] or s["battery_reduce"] and on_battery():
                    interval = max(interval, 120)
                if self.health_elapsed >= interval:
                    self.health_elapsed = 0
                    o.engine.check_health()
        interval = {"Manual": 0, "6 hours": 21600, "12 hours": 43200, "Daily": 86400}[
            s["subscription_interval"]
        ]
        if (
            not interval
            or o.sub_busy
            or o.engine.busy
            or self.retry.isActive()
            or time.monotonic() < self.subscription_retry
        ):
            return
        due = []
        # The live proxy can refresh its own subscription. Do not skip it.
        now = datetime.datetime.now()
        for sub in o.subscriptions:
            try:
                age = (
                    (
                        now - datetime.datetime.fromisoformat(sub.updated_at)
                    ).total_seconds()
                    if sub.updated_at
                    else interval
                )
            except ValueError:
                age = interval
            if age >= interval:
                due.append(sub)
        if due:
            self.subscription_retry = time.monotonic() + interval
            o.start_subscriptions(due)

    def subscriptions_finished(self, message):
        # Existing updater returns a fixed failure summary without provider secrets.
        if "fail" in message.lower():
            self.sub_failures = min(8, self.sub_failures + 1)
            self.subscription_retry = time.monotonic() + min(
                86400, 300 * 2**self.sub_failures
            )
        else:
            self.sub_failures = 0
