# NekoRay Next 0.4.0 — Settings

All new feature controls live inside the existing Settings page. There are exactly four existing outer pages, with twelve internal Settings categories. No new home cards, server-list actions or primary navigation entries were added. `settings-scope-audit.json` records identical AST bodies for the protected page builders and pixel-identical native home, servers and old diagnostics renders against 0.3.1. The home footer retains its original design/version text as part of this strict visual preservation.

## Implemented

- Typed, versioned preference schema with defaults, type/range/cross-field validation, application timing, permissions, atomic persistence, section reset, staged safe defaults, and validated non-sensitive JSON export/import. Legacy preferences migrate without rewriting profile credentials or private subscription catalogs. Unsafe/unavailable values are rejected. Related preferences are committed together; active connection parameters cannot be changed until disconnected.
- Internal search, twelve category pages, compact rows, advanced collapses, scoped default-dark Settings, light/system appearance, Persian RTL / English / automatic language, Settings font scale and contrast. Existing dashboard day/night preference remains available in General and changes the dashboard only by explicit selection. Normal text Paste remains native inside Settings.
- Smart Connect considers only serializer-compatible profiles; rankings use prior **verified HTTPS** latency/reliability, never the server table's TCP latency. Actual candidates are attempted sequentially through supervised Xray and must pass HTTPS. A selected favorite stays pinned. Manual preferred, latency, stability and balanced policies are available. Unmeasured candidates are tried; a failed candidate does not become a success based on an open port. This is bounded failover and history-based selection, not a parallel benchmark of every server.
- Unexpected loss/core-crash recovery with a shared retry budget, exponential delay, maximum attempts and a 60-second stability window before resetting the budget. Explicit Disconnect/Cancel/Exit cancels pending retries. No background auto-connect by default.
- Xray manager: explicitly selected executable, actual version/config validation, fixed command arguments, install/reinstall of the pinned 26.3.27 official x64 release, mandatory HTTPS and shipped authoritative SHA-256, redirect allowlist, archive path/symlink/size checks, staged install, atomic final binary replacement, previous managed version retained for rollback, explicit restart with interruption notice. No claim that the pinned release is the latest; no automatic latest-version discovery or unsigned fallback.
- Manual/System Proxy/Disabled modes; current-user startup registration on Windows with ownership checking. Existing protected WinINET lease, exact restoration, listener verification, process supervision and crash guardian remain mandatory. Settings recovery is explicit, asynchronous and respects outside proxy changes.
- Real Xray private-address LAN bypass. Verification endpoint rules take priority and are forced through the selected outbound even with LAN bypass, so a direct private endpoint cannot falsely certify a failed proxy.
- User-triggered explicit-proxy IP/country verification, system DNS lookup, read-only Windows IPv4/IPv6 route inspection, local port checks, TCP checks, actual HTTP/HTTPS proxy checks. DNS lookup is explicitly not a DNS-leak test; route display is not proof of route enforcement. Private route/IP reports are not exported in support bundles.
- Subscription refresh scheduling (manual / 6h / 12h / daily), exponential failure backoff, active-source exclusion, protected URL retention and source-isolated atomic reconciliation. Health status, timestamp, profile count, fixed last-error code, optional provider-supplied numeric quota/expiry metadata. No invented expiration or quota values. Settings-triggered updates discard pending results on leaving Settings; configured background scheduling continues intentionally.
- Telegram MTProto/SOCKS5 official-link recognition, duplicate/unknown-field rejection, manual metadata entry, protected local storage, TCP reachability, removal and explicit warning before opening Telegram's registered link handler. TCP is not claimed to authenticate MTProto/SOCKS. MTProto is not a general VPN.
- Adaptive health intervals, configured timeout, bounded bulk-test concurrency, Windows battery-aware polling, lightweight mode, actual core counters/HTTPS latency/failure history in Settings. Required verification is never disabled. Tray actions, profile choice, state/server/speed tooltip, minimize-on-close with real tray fallback, notifications and explicit Quit.
- Bounded, sanitized in-memory diagnostic levels. Support ZIP is built from whitelisted fixed metadata and recognized error codes, not by redacting arbitrary logs. It excludes profiles, URLs, identities, names, clipboard, credentials, IP/route reports and raw core output.

## Unsupported / disabled with explanation

- sing-box, V2Ray, Mihomo execution and automatic multi-core selection: missing reviewed serializers/lifecycle adapters. Xray is the only active adapter. Candidate names do not imply installed or usable cores.
- TUN, driver installation, adapter conflict repair, route restoration and per-EXE routing: no audited driver/WFP/TUN transaction and recovery backend. No decorative process selection list is shown.
- Kill switch and continuous DNS/IPv6/bypass leak prevention: no crash-tested firewall/WFP implementation. Kill switch remains OFF. System Proxy affects proxy-aware applications; it does not protect the entire device.
- Seamless switching / preserving established TCP sessions: single-process lifecycle cannot safely guarantee migration. Explicit core restart interrupts sessions.
- Per-domain routing editor, custom DNS resolver policy, whole-OS DNS leak tests, heavy Windows CPU-load detection, YAML/HTTP/SOCKS outbound execution and general-purpose MTProto forwarding.
- Latest-version checking, arbitrary release selection, signature-chain verification beyond authoritative shipped SHA-256, removal of bundled/optional engines. Managed rollback is available only after an earlier managed install.
- Arbitrary Hiddify/sing-box profile database migration. Existing optional NekoRay migration supports only the documented compatible subset. Unknown JSON/URI properties are preserved for local review and are never silently stripped to connect.
- No user interface animations are required; reduced-motion is an explained fixed state, not a fake switch.

## Validation and limits

See `TEST_RESULTS.md`, JUnit output, `screenshots/settings-v040/` and `WINDOWS_VALIDATION.md`. Tests run on Linux with real Qt and local Xray/HTTP/TLS servers. Windows package assembly and PE inspection are supported here; interactive Windows 11 execution, real WinINET/Run-key/DPAPI/guardian recovery and Windows driver/firewall enforcement are **not certified** by Linux mocks. Nothing is labeled production-complete or Windows-tested without that validation.

## Update

1. Exit the old app using **Quit**; allow proxy restoration to finish.
2. Back up the portable folder, especially `data`.
3. Extract the update ZIP over the existing application, merging the `NekoRayNext` directory and replacing program files. Never delete `data`.
4. Launch `NekoRayNext.exe`; open Settings. Existing profiles/subscriptions are retained. New automation is OFF/manual by default.

The full portable ZIP includes the same small Windows GUI launcher plus pinned Python/Qt/Xray runtime. Python application modules implement this Settings release; the unchanged launcher starts them. Source ZIP contains implementation, tests, schema, screenshots, licenses and build tools.
