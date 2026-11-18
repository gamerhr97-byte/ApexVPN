"""One supervised core, validated configs, cancelable connection lifecycle."""

from __future__ import annotations
import concurrent.futures, json, os, pathlib, socket, subprocess, sys, threading, time, tempfile
from PySide6.QtCore import QObject, Signal
from .profiles import make_config, ProfileError, Unsupported
from .network import proxy_probe, metrics, tcp_latency
from .proxy import ProxyLease, ProxyError
from .storage import atomic_write
from .errors import AppError, core_category, exception_category

HIDDEN = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def connection_config(profile, settings):
    """One routing builder for connections and isolated server tests."""
    from .singbox_adapter import PROTOCOLS, make_config as singbox_config
    if profile.protocol in PROTOCOLS:
        return singbox_config(profile, settings)
    from .direct_routing import apply_exceptions, protect_checks

    cfg = make_config(profile, settings['http_port'], settings['socks_port'],
                      settings['stats_port'], settings.get('bypass', False))
    apply_exceptions(cfg, settings)
    return protect_checks(cfg, settings)


class Job:
    """Kill the Windows child on GUI death without a background service."""

    def __init__(self, process):
        self.handle = None
        if os.name != "nt":
            return
        import ctypes
        from ctypes import wintypes as w

        class Basic(ctypes.Structure):
            _fields_ = [
                ("process_time", ctypes.c_longlong),
                ("job_time", ctypes.c_longlong),
                ("flags", w.DWORD),
                ("min_ws", ctypes.c_size_t),
                ("max_ws", ctypes.c_size_t),
                ("active", w.DWORD),
                ("affinity", ctypes.c_size_t),
                ("priority", w.DWORD),
                ("scheduling", w.DWORD),
            ]

        class IO(ctypes.Structure):
            _fields_ = [
                (n, ctypes.c_ulonglong)
                for n in (
                    "read_ops",
                    "write_ops",
                    "other_ops",
                    "read_bytes",
                    "write_bytes",
                    "other_bytes",
                )
            ]

        class Extended(ctypes.Structure):
            _fields_ = [
                ("basic", Basic),
                ("io", IO),
                ("process_mem", ctypes.c_size_t),
                ("job_mem", ctypes.c_size_t),
                ("peak_process", ctypes.c_size_t),
                ("peak_job", ctypes.c_size_t),
            ]

        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        k.CreateJobObjectW.restype = w.HANDLE
        k.SetInformationJobObject.argtypes = [
            w.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            w.DWORD,
        ]
        k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        k.CloseHandle.argtypes = [w.HANDLE]
        h = k.CreateJobObjectW(None, None)
        info = Extended()
        info.basic.flags = 0x2000
        operation = "CreateJobObject"
        ok = bool(h)
        if ok:
            operation = "SetInformationJobObject"
            ok = bool(
                k.SetInformationJobObject(h, 9, ctypes.byref(info), ctypes.sizeof(info))
            )
        if ok:
            operation = "AssignProcessToJobObject"
            ok = bool(k.AssignProcessToJobObject(h, w.HANDLE(int(process._handle))))
        if not ok:
            code = ctypes.get_last_error()
            if h:
                k.CloseHandle(h)
            raise AppError(
                "PROCESS_SUPERVISION",
                f"{operation} failed (Windows error {code}). Core stopped before system proxy activation.",
            )
        self.handle = h
        self.k = k

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None


class Engine(QObject):
    state = Signal(str, str)
    traffic = Signal(object)
    health = Signal(float)
    diagnostic = Signal(str)
    routing_warning = Signal()

    def __init__(self, root):
        super().__init__()
        self.root = pathlib.Path(root)
        self.pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="next"
        )
        self.cancel = threading.Event()
        self.process = None
        self.job = None
        self.running = False
        self.busy = False
        self.lock = threading.RLock()
        self.cleanup_lock = threading.RLock()
        self.last_check = ""
        self.lease = ProxyLease(root)
        self.guard = None
        self.started = 0
        self.stage = "idle"
        self.last_failure = ""
        self.core_fault = None
        self.log_reader = None
        self.routing_warned = False

    def canceled(self):
        return self.cancel.is_set() or (
            getattr(self, "external_cancel", None) is not None
            and self.external_cancel.is_set()
        )

    def connect_profile(self, profile, settings):
        with self.lock:
            if self.busy or self.running:
                return
            self.busy = True
            self.cancel.clear()
        self.state.emit("Connecting", "Validating profile and core…")
        self.pool.submit(self._connect, profile, dict(settings))

    def _connect(self, p, s):
        try:
            self.stage = "configuration"
            self.core_fault = None
            self.last_failure = ""
            self.routing_warned = False
            if s["mode"] == "Disabled":
                raise ProfileError("Connections are disabled in Settings.")
            from .singbox_adapter import PROTOCOLS
            auxiliary = p.protocol in PROTOCOLS
            self.backend = "sing-box" if auxiliary else "xray"
            path = pathlib.Path(s["singbox_core"] if auxiliary else s["core"]).resolve()
            if not path.is_file():
                raise FileNotFoundError(
                    "Selected core missing. Select its executable in Network Cores settings."
                )
            cfg = connection_config(p, s)
            # Probe existing listeners, rather than bind-and-close: binding without
            # reuse flags produces false conflicts during TCP TIME_WAIT on reconnect.
            # Xray's own bind remains authoritative for reservation and race failures.
            for port in (s["http_port"], s["socks_port"], s["stats_port"]):
                with socket.socket() as probe:
                    probe.settimeout(0.3)
                    if probe.connect_ex(("127.0.0.1", port)) == 0:
                        raise ProfileError(
                            "Local port conflict. Change the inbound ports in Settings."
                        )
            # Runtime credentials stay in memory and cross only the private input pipe.
            config_bytes = json.dumps(cfg, ensure_ascii=False).encode()
            # Core stderr may contain secrets. Consume it, never persist it or echo it to UI.
            self.stage = "core-validation"
            version = subprocess.run(
                [str(path), "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=5,
                **HIDDEN,
            )
            expected = b"sing-box version " if auxiliary else b"Xray "
            if version.returncode or not version.stdout.startswith(expected):
                raise Unsupported("Selected executable does not match the required core.")
            from .direct_routing import check_process_core
            if not auxiliary:
                check_process_core(version.stdout, s)
                from .transport_extensions import check_core_extensions
                check_core_extensions(version.stdout,p)
            check = subprocess.run(
                [str(path), "check", "-c", "stdin"] if auxiliary else [str(path), "run", "-test", "-c", "stdin:"],
                input=config_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=10,
                **HIDDEN,
            )
            if check.returncode:
                category = core_category(check.stdout.decode("utf-8", errors="replace"))
                if category:
                    raise AppError(category)
                if auxiliary:
                    raise Unsupported("sing-box rejected this configuration; review protocol parameters. Raw output was not logged.")
                raise Unsupported(
                    "Xray rejected this configuration. For VLESS encryption, use a core supporting the exact encryption scheme. Bundled baseline: Xray 26.10.21; value preserved. No compatibility was assumed."
                )
            if self.canceled():
                raise InterruptedError()
            self.stage = "core-start"
            self.process = subprocess.Popen(
                [str(path), "run", "-c", "stdin"] if auxiliary else [str(path), "run", "-c", "stdin:"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                **HIDDEN,
            )
            process = self.process
            self.log_reader = threading.Thread(
                target=self._read_core, args=(process,), daemon=True
            )
            self.log_reader.start()
            self.stage = "process-supervision"
            self.job = Job(process)
            self.stage = "core-start"
            try:
                self.process.stdin.write(config_bytes)
                self.process.stdin.close()
            except (BrokenPipeError, OSError):
                raise AppError("CORE_EXIT") from None
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                if self.canceled():
                    raise InterruptedError()
                if self.process.poll() is not None:
                    raise AppError(self.core_fault or "CORE_EXIT")
                try:
                    with socket.create_connection(("127.0.0.1", s["http_port"]), 0.2):
                        break
                except OSError:
                    self.cancel.wait(0.1)
            else:
                raise TimeoutError("Local proxy listener did not become available.")
            self.stage = "https-verification"
            self.state.emit("Connecting", "Verifying HTTPS through the selected proxy…")
            latency = proxy_probe(
                s["http_port"], s["https_url"], timeout=s.get("health_timeout", 8)
            )
            # A blocked plaintext endpoint alone is not evidence of a broken TLS tunnel.
            self.stage = "http-check"
            http_note = ""
            try:
                if not s.get("probe_only", False):
                    proxy_probe(s["http_port"], s["http_url"], timeout=3)
            except Exception as e:
                http_note = " HTTPS verified; optional HTTP check failed."
                self.diagnostic.emit("Optional HTTP check: " + safe_error(e))
            if self.canceled():
                raise InterruptedError()
            if self.process.poll() is not None:
                raise AppError(self.core_fault or "CORE_EXIT")
            self.stage = "system-proxy"
            if s["mode"] == "System Proxy":
                self._start_guard()
                from .direct_routing import windows_bypass
                self.lease.enable(s["http_port"], windows_bypass(s))
            if self.canceled():
                raise InterruptedError()
            self.running = True
            self.started = time.monotonic()
            self.settings = s
            self.last_check = time.strftime("%H:%M:%S")
            self.health.emit(latency)
            self.stage = "connected"
            self.state.emit(
                "Connected", "HTTPS verified through the proxy." + http_note
            )
        except InterruptedError:
            self._cleanup()
            self.state.emit("Disconnected", "Connection canceled")
        except Exception as e:
            if self.core_fault and self.stage in (
                "https-verification",
                "http-check",
                "core-start",
            ):
                message = safe_error(AppError(self.core_fault))
            else:
                message = safe_error(e)
            if (
                self.stage == "https-verification"
                and p.host
                and not s.get("probe_only", False)
            ):
                try:
                    tcp_latency(p.host, p.port, timeout=2)
                except Exception as tcp_error:
                    code = exception_category(tcp_error)
                    if code:
                        message += " Selected server TCP: " + str(AppError(code))
            self.last_failure = f"[{self.stage}] " + message
            cleanup = self._cleanup()
            self.state.emit(
                "Error", self.last_failure + ((" " + cleanup) if cleanup else "")
            )
        finally:
            # A disconnect arriving after the final gate must still stop the core.
            if self.canceled() and self.running:
                error = self._cleanup()
                self.state.emit(
                    "Error" if error else "Disconnected",
                    error or "Connection canceled; proxy restored and core stopped.",
                )
            with self.lock:
                self.busy = False

    def _read_core(self, process):
        try:
            while True:
                line = process.stdout.readline(4096)
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace")
                if ("unables to find local process name" in decoded.lower()
                        and process is self.process and not self.routing_warned):
                    self.routing_warned = True
                    self.routing_warning.emit()
                category = core_category(decoded)
                if category and process is self.process:
                    self.core_fault = category
        except (OSError, ValueError):
            pass

    def core_preflight(self, profile, settings):
        """Read-only validation without starting a tunnel or changing proxy settings."""
        from .singbox_adapter import PROTOCOLS
        auxiliary=profile.protocol in PROTOCOLS
        path=pathlib.Path(settings["singbox_core"] if auxiliary else settings["core"]).resolve()
        cfg = connection_config(profile, settings)
        if not auxiliary and (settings.get('direct_enabled') and settings.get('direct_apps', '').strip() or any(profile.params.get(k) for k in ('cs','fm','fragment'))):
            from .direct_routing import check_process_core
            version = subprocess.run([str(path), 'version'], stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, timeout=5, **HIDDEN)
            check_process_core(version.stdout, settings)
            from .transport_extensions import check_core_extensions
            check_core_extensions(version.stdout,profile)
        result = subprocess.run(
            [str(path), "check", "-c", "stdin"] if auxiliary else [str(path), "run", "-test", "-c", "stdin:"],
            input=json.dumps(cfg).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            **HIDDEN,
        )
        if result.returncode:
            raise AppError(
                core_category(result.stdout.decode("utf-8", errors="replace"))
                or "ENCRYPTION_UNSUPPORTED"
            )
        return "Core configuration preflight passed. This is not a traffic test."

    def _start_guard(self):
        if os.name != "nt":
            return
        # A separate, non-service process restores the lease if the GUI is forcibly terminated.
        script = pathlib.Path(__file__).resolve().parents[1] / "app.py"
        ready = self.root / "guardian.ready"
        ready.unlink(missing_ok=True)
        self.guard = subprocess.Popen(
            [sys.executable, str(script), "--guard", str(os.getpid()), str(self.root)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **HIDDEN,
        )
        deadline = time.monotonic() + 6
        while not ready.exists():
            if self.guard.poll() is not None or time.monotonic() > deadline:
                raise ProxyError(
                    "Crash recovery watcher could not start. System proxy was not enabled."
                )
            self.cancel.wait(0.05)

    def disconnect(self):
        self.cancel.set()
        if self.busy:
            return
        with self.lock:
            if self.busy:
                return
            self.busy = True
        self.pool.submit(self._disconnect)

    def _disconnect(self):
        try:
            error = self._cleanup()
            self.state.emit(
                "Error" if error else "Disconnected",
                error or "Previous proxy settings restored; core stopped",
            )
        finally:
            self.busy = False

    def _cleanup(self):
        with self.cleanup_lock:
            return self._cleanup_locked()

    def _cleanup_locked(self):
        error = ""
        try:
            if self.lease.path.exists():
                self.lease.restore()
        except Exception as e:
            error = safe_error(e)
        self.running = False
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            if self.log_reader:
                self.log_reader.join(timeout=1)
                self.log_reader = None
            if self.process.stdout:
                self.process.stdout.close()
            self.process = None
        if self.job:
            self.job.close()
            self.job = None
        if self.guard:
            if self.guard.poll() is None:
                self.guard.terminate()
                self.guard.wait(timeout=3)
            self.guard = None
        (self.root / "guardian.ready").unlink(missing_ok=True)
        (self.root / "session.json").unlink(missing_ok=True)
        return error

    def sample(self):
        if not self.running or getattr(self, "sampling", False):
            return
        self.sampling = True
        self.pool.submit(self._sample)

    def _sample(self):
        try:
            if not self.process or self.process.poll() is not None:
                error = self._cleanup()
                self.state.emit(
                    "Error",
                    "Core process crashed. "
                    + (error or "Previous proxy settings restored."),
                )
                return
            try:
                self.traffic.emit(metrics(self.settings["stats_port"]))
            except Exception:
                self.traffic.emit(None)
        finally:
            self.sampling = False

    def check_health(self):
        if not self.running or getattr(self, "checking", False):
            return
        self.checking = True
        process = self.process

        def work():
            try:
                ms = proxy_probe(
                    self.settings["http_port"],
                    self.settings["https_url"],
                    timeout=self.settings.get("health_timeout", 8),
                )
                if process is not self.process or not self.running:
                    return
                self.last_check = time.strftime("%H:%M:%S")
                self.health.emit(ms)
                self.diagnostic.emit(
                    "HTTPS request through proxy succeeded. Certificate validation passed."
                )
            except Exception as e:
                if process is not self.process or not self.running:
                    return
                self.diagnostic.emit(safe_error(e))
                self.cancel.set()
                error = self._cleanup()
                self.state.emit(
                    "Error",
                    "Verified internet access interrupted. "
                    + (error or "Proxy settings restored. Reconnect when ready."),
                )
            finally:
                self.checking = False

        self.pool.submit(work)

    def shutdown(self):
        self.cancel.set()
        self.pool.shutdown(wait=True, cancel_futures=True)
        self._cleanup()


def safe_error(e):
    if isinstance(e, (AppError, ProfileError, ProxyError)):
        return str(e)
    if isinstance(e, subprocess.TimeoutExpired):
        return "[CORE_TIMEOUT] Core validation timed out. Check the executable."
    category = exception_category(e)
    if category:
        return str(AppError(category))
    # Numeric codes are safe to export, but arbitrary exception strings are not.
    if isinstance(e, OSError):
        return f"[OS_ERROR] OS operation failed (code {e.errno or 0})."
    return f"[INTERNAL_ERROR] Operation failed ({type(e).__name__}); run diagnostics to identify its stage."
