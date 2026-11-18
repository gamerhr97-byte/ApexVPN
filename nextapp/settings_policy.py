"""Central UX/application policy: safe autosave never commits networking drafts."""

import os
from .settings_schema import SCHEMA, validate

SAFE_AUTO_KEYS = frozenset(
    {
        "auto_save",
        "automatic_tuning",
        "service_checks",
        "theme",
        "settings_theme",
        "accent",
        "text_scale",
        "reduced_motion",
        "visual_effects",
        "allow_resize",
        "sound_enabled",
        "high_contrast",
        "tray_status",
        "tray_server",
        "tray_speed",
        "notifications",
        "logging",
        "remember_window",
        "remember_profile",
    }
)
# Validated complete edits can be saved without changing the active connection.
# Core/ports/Windows integration and imported batches still require the save button.
FORM_AUTO_KEYS = frozenset(k for k, spec in SCHEMA.items()
    if spec.permission == 'user' and not spec.unavailable
    and k not in {'core','singbox_core','mode','http_port','socks_port','stats_port','language'})

PRIMARY = {
    0: {"auto_save", "language", "theme", "settings_theme"},
    1: {"auto_connect_on_launch", "smart_connect", "auto_reconnect", "smart_policy"},
    2: {"core","singbox_core"},
    3: {"mode"},
    4: {"bypass"},
    5: {"service_checks"},
    6: {"auto_recover_core"},
    7: {"subscription_interval","remove_failed_servers"},
    8: set(),
    9: {"automatic_tuning", "monitor", "lightweight"},
    10: {"allow_resize", "sound_enabled", "visual_effects", "reduced_motion", "tray_enabled"},
    11: set(),
    12: {"logging"},
    13: {"direct_enabled", "direct_ir", "direct_domains", "direct_apps"},
}


def is_advanced(spec):
    return (
        spec.advanced
        or spec.unavailable
        or spec.key not in PRIMARY.get(spec.section, set())
    )


def auto_candidate(current, draft):
    candidate = dict(current)
    changed = set()
    for key in SAFE_AUTO_KEYS:
        if key in draft and draft[key] != current.get(key):
            candidate[key] = draft[key]
            changed.add(key)
    # Validation sees the active networking settings, never the user's partial network draft.
    validate(candidate)
    return candidate, changed


def effective_settings(settings):
    result = dict(settings)
    if settings.get("automatic_tuning", True):
        result.update(
            retry_delay=3,
            retry_attempts=3,
            retry_backoff=True,
            stable_interval=60,
            failure_interval=15,
            health_timeout=8,
            concurrency=max(1, min(4, (os.cpu_count() or 2) // 2)),
        )
    if settings.get("lightweight", False):
        result["concurrency"] = 1
    return result


def session_preferences(owner):
    """Diagnostics follow the live listener, never a saved next-session port."""
    result = dict(owner.settings)
    active = getattr(owner.engine, 'settings', None)
    if owner.engine.running and active:
        for key, spec in SCHEMA.items():
            if spec.application == 'next connection' and key in active:
                result[key] = active[key]
    return result


def pending_network_changes(owner):
    active = session_preferences(owner)
    return any(spec.application == 'next connection' and active.get(key) != owner.settings.get(key)
               for key, spec in SCHEMA.items())


RESTYLE_KEYS = frozenset({'theme','settings_theme','accent','text_scale',
    'visual_effects','reduced_motion','high_contrast','lightweight','allow_resize'})
