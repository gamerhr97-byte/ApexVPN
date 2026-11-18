"""Honest profile tests: TCP reachability or isolated, HTTPS-verified Xray tunnel."""

from dataclasses import dataclass
import socket, tempfile, time
from PySide6.QtCore import Qt
from .network import tcp_latency
from .errors import exception_category


@dataclass(frozen=True)
class ProfileTest:
    method: str
    status: str
    latency: float | None = None
    code: str = ""
    service_score: int | None = None
    gemini_ok: bool = False


def failure_status(code):
    if code in ("TIMEOUT", "CORE_TIMEOUT"):
        return "Timeout"
    if code == "TCP_REFUSED":
        return "Refused"
    if code in ("ENCRYPTION_UNSUPPORTED", "UNSUPPORTED"):
        return "Unsupported"
    return "Failed"


def test_tcp(profile, timeout=4):
    if profile.protocol in {"hysteria2","hysteria","tuic"}:
        return ProfileTest("TCP","Unsupported",code="UDP_PROTOCOL_USE_HTTPS")
    try:
        return ProfileTest(
            "TCP", "Reachable", tcp_latency(profile.host, profile.port, timeout)
        )
    except Exception as error:
        code = exception_category(error) or "NETWORK_ERROR"
        return ProfileTest("TCP", failure_status(code), code=code)


def temporary_ports():
    sockets = []
    try:
        for _ in range(3):
            sock = socket.socket()
            sock.bind(("127.0.0.1", 0))
            sockets.append(sock)
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def test_https(profile, settings, cancel):
    # Imports stay local: callers run this operation on a worker thread.
    from .engine import Engine

    if cancel.is_set():
        return ProfileTest("HTTPS", "Canceled")
    config = dict(settings)
    ports = temporary_ports()
    config.update(
        mode="Manual Proxy",
        bypass=False,
        http_port=ports[0],
        socks_port=ports[1],
        stats_port=ports[2],
        probe_only=True,
    )
    latency = []
    with tempfile.TemporaryDirectory(prefix="shadow-test-") as root:
        engine = Engine(root)
        engine.external_cancel = cancel
        engine.health.connect(latency.append, Qt.DirectConnection)
        try:
            engine._connect(profile, config)
            if cancel.is_set():
                return ProfileTest("HTTPS", "Canceled")
            if engine.running and latency:
                score, gemini = None, False
                if settings.get("quality_checks", False):
                    from .service_checks import measure_quality
                    score, gemini = measure_quality(config["http_port"], cancel, settings)
                return ProfileTest("HTTPS", "Verified", latency[-1], service_score=score, gemini_ok=gemini)
            code = next(
                (
                    name
                    for name in (
                        "TIMEOUT",
                        "CORE_TIMEOUT",
                        "TCP_REFUSED",
                        "ENCRYPTION_UNSUPPORTED",
                        "TLS_FAILED",
                        "AUTH_FAILED",
                    )
                    if "[" + name + "]" in engine.last_failure
                ),
                "NETWORK_ERROR",
            )
            if engine.stage == "configuration":
                code = "UNSUPPORTED"
            return ProfileTest("HTTPS", failure_status(code), code=code)
        finally:
            engine.shutdown()


def result_text(profile, translate=lambda text: text):
    if profile.test_error == "UDP_PROTOCOL_USE_HTTPS":
        return "UDP · HTTPS"
    status = profile.test_status
    method = profile.test_method or "TCP"
    if profile.latency is not None:
        return f"{profile.latency:.0f} ms · {method}"
    if status in ("Timeout", "Refused", "Failed", "Unsupported", "Canceled"):
        return translate(status)
    return translate("Failed" if profile.tested_at else "Not Tested")
