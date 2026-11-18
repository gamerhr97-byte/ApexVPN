# Shadow Box development handoff

Read START_HERE_FA.md, PROJECT_HANDOFF.md, PROJECT_MAP.md and DEVELOPMENT.md before changing the project. This is a documentation-enriched snapshot of modern Shadow Box 0.10.0; it is not a new application release.

## Product and user constraints

- Communicate with the owner in Persian. Keep technical identifiers in English where useful.
- This is a native Qt Windows application, not a web app. Preserve the existing compact glass interface, light/dark themes, connect ring and overall layout unless the owner asks otherwise.
- Keep 15 Settings categories (usage added in 0.10.4), no scrollable home, usable hidden-scrollbar navigation in Settings, and deliberate manual versus automatic server choice.
- Prefer cohesive modules and focused changes. Do not rewrite the entire UI or change cores/frameworks merely to simplify a task.
- User authorization in the current conversation takes precedence over this handoff.

## Data and connection invariants

- Preserve installed data at %LOCALAPPDATA%/NekoRayNext and portable data beside portable.flag. The legacy identifiers are intentional compatibility, not incomplete rebranding.
- Keep DPAPI protection, atomic UTF-8 writes, exact proxy ownership/recovery leases and crash supervision. Never blindly disable another application's proxy or overwrite an externally changed lease.
- Profiles and unknown parameters stay lossless. Do not silently drop fields or weaken TLS certificate checks to make a profile appear supported.
- A TCP listener is not evidence of a working tunnel. Mandatory HTTPS, exit-IP and service verification must retain their intended proxy path.
- Save future connection preferences separately from the running Engine snapshot. Live diagnostics must use live ports. Saved networking edits take effect after reconnect.
- Keep .ir bypass defaults, one-time preference migration and later user opt-out behavior explicit. This is System Proxy/HTTP/SOCKS routing, not full-device TUN capture.
- Prefer local generated test credentials and endpoints. Never commit personal subscription URLs, original private server links, app data or signing private keys into source, logs or screenshots.

## Validation and delivery

- Read actual code and recent reports; old release documentation can be stale.
- Run checks relevant to changes. Real-core integration requires the pinned Xray binary and local TLS fixtures. Clearly distinguish mocks, Linux offscreen tests and actual Windows execution.
- Do not claim verified Windows WinINET, DPAPI, native-host startup, Task Manager identity or process matching without testing those on Windows.
- No trusted publisher certificate is supplied. Do not claim signing, install a self-signed trust root or promise SmartScreen warnings disappear.
- Audit the stale full installer and artifact filenames before producing a fresh installer. See the P0 packaging notes in PROJECT_HANDOFF.md.
- Update version/resource metadata only for an actual app change; maintain release notes, pinned dependencies and a handoff summary after changes.
- Deliver runnable releases separately from source archives. This source-only bundle does not include prebuilt Python/Qt/Xray runtime binaries.

## 0.10.5 compositor invariant
Never install a QGraphicsEffect on child buttons inside a shadowed card. The Windows regression (displaced ping and missing Add-sheet actions) was reproduced under Qt offscreen too. Feedback uses native painting and a mouse-transparent overlay only. Validate both UI languages, both settings themes and DPI 1/1.25/1.5/2 with tools/check_v0105_visual.py. All compatibility EXEs must be rebuilt from the current launcher. Complete source deliveries now include runtime and native binaries.

## 0.10.6 product constraints
Deliver one NSIS Setup EXE to the user (same installer handles upgrades); no portable delivery. Free presets are permanent; personal ownership cannot be inferred from URL/name. Threshold is >=90/100. Caption and connecting mark are Qt-native/vector, never place opaque raster art inside the power ring. Keep Apex/Light/Dark themes and one-time gradient migration. Closed Windows schedule deleteLater; drain deferred deletion while QApplication is alive before Python teardown.

## 0.10.7 product constraints
One-time Free-only cleanup is explicitly requested: create a catalog backup, preserve local servers and favorites, move favorited subscription entries to Local while retaining `favorite_source_id`, delete other non-Free subscriptions and their linked servers, and write a completion marker only after successful persistence. Do not repeat after preference reset. New custom subscriptions added later remain supported. Keep the 100-destination check but bound total service probes based on parallel server checks. EcoQoS only while the UI is hidden/minimized and all network work is idle; restore system-managed QoS on show or work. Installer App Paths alias `vpn.exe` must be removed on uninstall. The uninstaller prompt stays one page with a clear cancel path.
> Current: Apex VPN 0.10.7. Read README-0.10.7-FA.md and docs/VALIDATION-0.10.7-FA.md first.


## 1.11.0 current handoff

Read `NEXT_AI_HANDOFF_FA.md` first; it supersedes older release headers below. Keep the installed 0.10.7 path/storage identity compatible. The displayed version, `shadow.rc`/`host.rc`, and rebuilt native launchers are 1.11.0. The small updater deliberately targets an installed 0.10.7 base. Settings back navigation is detail -> category list -> Home. Service result tiles use green/red/neutral backgrounds without check/cross overlays and have no Search service field. Minimize must call `showMinimized()` directly; a top-level opacity animation was found to block the Windows state change in some environments. Never claim Windows runtime validation from Linux archive checks.
