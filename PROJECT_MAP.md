> Current: Apex VPN 1.11.0. Read NEXT_AI_HANDOFF_FA.md for the latest source map and build state; older release sections below are historical.

> Current: Apex VPN 0.10.5. Read README-0.10.5-FA.md and docs/VALIDATION-0.10.5-FA.md. Older sections are historical.

> Current release: Apex VPN 0.10.4. Read README-0.10.4-FA.md and docs/VALIDATION-0.10.4-FA.md first. Older sections below are historical.

> Latest: 0.10.3. Read README-0.10.3-FA.md, PROTOCOL-SUPPORT-FA.md and docs/VALIDATION-0.10.3-FA.md first. Older notes below are historical.

> **0.10.1 supplemental map:** nextapp/focus_style.py (no dotted native focus), nextapp/ranking.py (star/verified latency order), tools/check_v0101.py (Qt-free regression checks), README-0.10.1-FA.md, CHANGELOG-0.10.1-FA.md and PROTOCOL-SUPPORT-FA.md. Historical map below is the 0.10.0 baseline.

# Source map — Shadow Box 0.10.0

All paths below are relative to this source root. Start from the affected subsystem rather than reading every historical screenshot/report.

## Entry points and UI

| Files | Role |
| --- | --- |
| `app.py` | Qt entry point, data-root choice, instance lock, ready event and guardian mode |
| `nextapp/ui.py` | Main Window composition, cross-page actions, import/subscription callbacks and UI state coordination |
| `nextapp/dashboard.py`, `presentation.py` | Compact home and painted glass/connect ring/icons |
| `nextapp/server_page.py` | Grouped server table, source picker, quota preview, selection and management controls |
| `nextapp/settings_ui.py` | 14-category Settings UI, form staging/autosave/save, diagnostics and tools |
| `nextapp/settings_schema.py` | Typed fields/defaults/validation, migration, import/export and private metadata |
| `nextapp/settings_policy.py` | Safe/form autosave policy, effective tuning, live session snapshot and restyling keys |
| `nextapp/responsive.py`, `effects.py` | Layout helpers and static depth effects |
| `nextapp/feedback.py`, `navigation.py` | One-second in-window toast and bounded page/category back/forward history |
| `nextapp/iconography.py`, `branding.py`, `sound.py`, `i18n.py` | Original glyphs/branding, sound cues and translations |
| `nextapp/release_notes.py` | Once-per-release acknowledgement and manual release-note display |
| `assets/` | Original logo/icon, flags, chevron and local sound assets |

## Connection, routing and tests

| Files | Role |
| --- | --- |
| `nextapp/profiles.py` | Profile dataclass, lossless URI import, alias normalization and supported Xray serialization |
| `nextapp/engine.py` | Central connection_config, core preflight/start/supervision, session settings and cleanup |
| `nextapp/connection_switch.py` | Stop/restore the previous session before starting the selected replacement |
| `nextapp/settings_runtime.py` | Retry/smart policies, local reliability and scheduled monitoring/refresh orchestration |
| `nextapp/direct_routing.py` | Validated host/EXE parsing, .ir/custom direct rules, protected checks and Windows bypass string |
| `nextapp/proxy.py`, `guardian.py` | WinINET adapter, ownership lease/exact restore and independent crash recovery |
| `nextapp/network.py` | Explicit HTTP-proxy probes, provider fetch/metadata, metrics and public-IP/country lookups |
| `nextapp/profile_testing.py`, `group_testing.py` | Isolated real-core HTTPS/TCP checks, statuses, bounded group work and cancellation |
| `nextapp/service_checks.py` | Ten bounded website HTTPS header checks through the active proxy |
| `nextapp/errors.py`, `logbook.py` | Fixed/sanitized error categories and bounded logs |

## Catalog, data and utility services

| Files | Role |
| --- | --- |
| `nextapp/storage.py` | Atomic file writes, explicit UTF-8 preferences, DPAPI catalog and backups |
| `nextapp/subscriptions.py` | Subscription dataclass and reconciliation preserving IDs/favorites/test state |
| `nextapp/subscription_loader.py` | Bounded nested HTTPS feeds, root metadata, canonical URLs and deduplication |
| `nextapp/catalog_actions.py` | Copy/edit/delete server and source actions, persistence and backup |
| `nextapp/importers.py` | Manual configuration and local QR decoding |
| `nextapp/usage.py`, `quota_widgets.py` | Provider-supplied volume accounting and compact quota presentation |
| `nextapp/settings_services.py` | Diagnostics/privacy, pinned core management, Telegram store and support export |
| `nextapp/bootstrap.py`, `hardware.py` | Local hardware defaults and diagnostic descriptions |
| `nextapp/migration.py` | Documented legacy NekoRay import subset and preservation |

## Build and native runtime

| Files | Role / caution |
| --- | --- |
| `dependencies.lock.json` | Exact third-party versions and SHA-256 values for distribution inputs |
| `requirements.txt`, `requirements-dev.txt` | Python dependency pins for development/build tooling |
| `tools/download_dependencies.py` | Download exact upstream artifacts and reject checksum mismatches |
| `tools/launcher.c` | Branded GUI launcher, OS/CPU checks, startup splash and host supervision |
| `tools/python_host.c` | Own branded process loading python313.dll and Py_Main |
| `tools/shadow.rc`, `host.rc` | Native icon/version resources; host.rc is generated by the builder |
| `tools/build_launcher.py` | Build the launcher and host with Zig and generate icon formats |
| `tools/package_update.py` | Current 0.10.0 overlay, including the host and its ._pth; requires an existing modern base |
| `tools/package_windows.py` | Full portable payload builder, including the host; output ZIP name is historically stale (0.6.0) |
| `tools/build_installer.py`, `installer.nsi` | Historical full NSIS builder: must fix host staging and 0.7.0 labels before a new release |
| `tools/uninstall-files.nsh` | Generated from an installer payload; regenerate rather than assuming the old list is current |
| `tools/sign_release.py` | Optional actual Windows certificate-store signing/verification; no certificate is supplied |
| `tools/recover_backup.py` | Recovery utility; inspect its assumptions before handling personal data |
| `tools/benchmark.py`, `screenshot*.py`, `verify*.py` | Development aids; several target old releases/baseline directories |

## Tests and evidence

| Paths | What to use them for |
| --- | --- |
| `tests/test_v0100.py` | Current settings persistence, migration, .ir bypass, live snapshot, source controls and restyling regressions |
| `tests/test_direct_routing.py` | Input boundaries, precedence, routing persistence and actual core direct paths |
| `tests/test_v090.py`, `test_v070.py`, `test_v060.py` | Recent UI/grouping/transports/navigation/autosave regressions |
| `tests/test_e2e.py` | Local HTTP/TLS/Xray fixtures and real lifecycle/traffic checks |
| `tests/test_settings.py`, `test_proxy_storage.py` | Schema/UI services and proxy ownership/storage safety |
| Other `tests/test_*.py` | Parsers, imports, subscriptions, compact UI and presentation boundaries |
| `tests/conftest.py` | Offscreen Qt, clipboard cleanup and suppression of unintended external service traffic |
| `docs/TEST_RESULTS.md` | Latest evidence at the top; older report sections remain below |
| `docs/test-results-v0100.xml`, `test-v0100-focused.xml` | Historical authoritative 0.10.0 whole/focused run results |
| `docs/native-host-v0100.json` | Historical native PE/import/signature inspection |
| `docs/RELEASE-0.10.0.md`, `UPDATE-0.10.0.md` | Current behavior and user update guide |
| `docs/ARCHITECTURE.md`, `LIMITATIONS.md`, older releases/screenshots | Historical context; resolve conflicts against current code and this handoff |

## Quick symptom → starting point

| Symptom | Inspect first |
| --- | --- |
| Settings disappear after restart | storage.py UTF-8, settings_schema.py migrate, settings_ui.py save/autosave and selected data root |
| Saved ports break diagnostics | settings_policy.py session_preferences, settings_ui.py run/privacy, Engine snapshot |
| .ir goes through proxy | persisted routing defaults/opt-out, direct_routing.py, WinINET lease/bypass, reconnect and browser-specific proxy |
| First source server is always chosen | ui.py toggle_connection/test_profiles, explicit manual_selection, ConnectionSwitch and group scope |
| Wrong source/quota after switching | server_page.py group identity/preview, selected_group migration, subscriptions.py reconciliation |
| Config says Unsupported | profiles.py normalized_params/outbound; retain the original and classify the exact unsupported feature |
| New full installer does not start | known missing host/.pth and stale version fields in full NSIS builder |
| SmartScreen unknown publisher | absence of a real trusted Authenticode identity; not a UI/resource-name problem |

## 0.10.5 modules
nextapp/telegram_transport.py distinguishes reusable Telegram SOCKS5 links from MTProto. nextapp/traffic_page.py paints six observed-usage rows with explicit bidi handling. nextapp/interactions.py no longer uses child graphics effects. tools/check_v0105_visual.py and tests/test_v0105.py cover regressions.
