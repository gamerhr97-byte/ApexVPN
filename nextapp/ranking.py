"""Deterministic server ranking after a complete batch, not during in-flight tests."""


def rank(profile):
    """Star benefits first; measured *HTTPS tunnel* latency second.

    A TCP ping is never treated as authenticated tunnel verification. Unknowns
    remain selectable: this rank must never be used to block connecting.
    """
    stars = int(bool(profile.gemini_ok)) + int(profile.service_score is not None and profile.service_score >= 90)
    measured = (isinstance(profile.latency, (int, float))
                and 0 <= profile.latency < float("inf"))
    verified = (measured and profile.test_method == "HTTPS"
                and profile.test_status == "Verified")
    tcp_only = (measured and profile.test_method == "TCP"
                and profile.test_status == "Reachable")
    tier = 0 if verified else 1 if tcp_only else 2
    return (-stars, -int(bool(profile.favorite)), tier, profile.latency if verified or tcp_only else float("inf"),
            profile.name.casefold())
