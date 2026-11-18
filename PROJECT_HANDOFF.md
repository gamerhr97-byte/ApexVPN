> Current: Apex VPN 1.11.0 source and quick update. Read NEXT_AI_HANDOFF_FA.md and README-1.11.0-FA.md first. Earlier sections describe historical 0.10.x states; verify their claims against current source.

> Current: Apex VPN 0.10.5. Read README-0.10.5-FA.md and docs/VALIDATION-0.10.5-FA.md. Older sections are historical.

> Current release: Apex VPN 0.10.4. Read README-0.10.4-FA.md and docs/VALIDATION-0.10.4-FA.md first. Older sections below are historical.

> Latest: 0.10.3. Read README-0.10.3-FA.md, PROTOCOL-SUPPORT-FA.md and docs/VALIDATION-0.10.3-FA.md first. Older notes below are historical.

> 0.10.2 source review: see README-0.10.2-FA.md and docs/VALIDATION-0.10.2-FA.md. Hysteria2 remains unsupported for connection.

> **Update, 2026-10-28 (0.10.1 source):** See README-0.10.1-FA.md and CHANGELOG-0.10.1-FA.md. The rest is historical 0.10.0 baseline and its previous test evidence; it is not validation of this patched version.

# Shadow Box — project handoff

Prepared: 2026-10-28. Application baseline: **0.10.0**, last delivered 2026-10-21.
This document summarizes the visible development history and the inspected source archive. It is not a transcript of all prior chat messages, and gives no access to previous private sessions.

## 1. What this project is

Shadow Box is a native desktop proxy client built with Python and PySide6/Qt. Xray supplies HTTP/SOCKS proxying and supported proxy outbound protocols. The modern distribution targets Windows 10 build 17763+ and Windows 11, Intel/AMD x64. Runtime Python is 3.13.9; historical development/test runs used Linux Python 3.12.

The project started as NekoRay Next. The visible brand is Shadow Box, but package names, protected storage identifiers, installed data folder NekoRayNext and a compatibility NekoRayNext.exe entry point intentionally remain. Do not rename those in a cosmetic cleanup without a data migration plan.

A separate Windows 7 Legacy branch was previously produced, using a different Python/Qt/backend bundle. That branch is not in this modern source archive. A historical Legacy 0.7.1 version number does not supersede modern 0.10.0.

## 2. Owner's recurring preferences

Persian communication; clean code; native responsive UI; white glass plus night/day themes; a centered connect circle; compact server/upload/download cards; little visual clutter. Improve UI/UX within the current composition rather than moving everything. No scrolling home; Settings can scroll without a visible scrollbar. Effects should be gentle and light, not an always-running animation. The owner expects saved settings, genuine latency/status, easy per-subscription management and working domestic-site bypass.

Do not copy another product's logo or claim affiliation: this project uses its own purple network-S identity.

## 3. Implemented current behavior

### Connection and server choice

Main Connect in automatic mode runs fresh HTTPS checks for the selected subscription group, ignoring a text search filter. It connects the first verified result, then chooses the lowest measured verified HTTPS latency after the group completes. An implicitly remembered/first profile is not an explicit manual choice. A deliberate server Connect action pins a manual selection; choosing a subscription restores automatic choice. Switching stops/restores the old session before reconnecting; established TCP sessions are not migrated seamlessly.

Bulk tests distinguish queued, testing, verified, timeout, refused, failed and unsupported. TCP is reachability only. A successful group measurement is not a guarantee of future connectivity or a production site's account/region/media access.

### Imports and subscriptions

Clipboard text/images, local QR image and file/manual imports feed the normal parser. Root HTTPS subscription links are stored protected for refresh. Nested HTTPS subscription bundles, such as lists of other subscription URLs, are bounded by depth, number of links, byte budget and profile count. Root grouping, canonical URL identity, metadata, deduplication, cancellation and failure preservation are implemented.

The source picker supports deliberate selection, quota preview/remaining volume, same-source refresh and copy/rename/edit/remove. Source selection persists. Provider usage/expiry are only displayed when supplied; unknown values must not be invented. Context server editing/copy/delete and Del selection are supported.

### Protocol compatibility

The Xray serializer supports the documented VLESS/VMess/Trojan/Shadowsocks subset, including TCP/RAW, WebSocket, gRPC + TLS/REALITY, XHTTP + TLS/REALITY and HTTPUpgrade where permitted. Compatible headerType=none is accepted without a false gRPC rejection. Original URI fields are retained; unknown/conflicting/insecure/unsupported features still stop serialization.

Hysteria2 may be imported and preserved but is not enabled for connection by this adapter. Full arbitrary JSON is stored for review rather than blindly executed. “Support all configs automatically” has not been achieved and must not be claimed.

### Settings and live session synchronization

There are 14 Settings categories. UTF-8-sig reads match atomic UTF-8 writes, including Persian paths. Complete valid ordinary/routing form edits can autosave. Core path, ports, language, Windows integration and imported batches still require an explicit Save action. Invalid partial drafts must not overwrite stored values or be committed by unrelated appearance autosaves.

Networking edits can be saved while connected. They do not mutate the running Engine's settings/listeners/lease; the next connection uses them. Diagnostics/privacy tests use session_preferences() to follow live ports until reconnect. Networking-only saves avoid full-window restyling; appearance edits still update the relevant UI.

### Direct exceptions

Section 14 contains the master exception toggle, .ir option, custom website/domain list and EXE list/picker. Full HTTP/HTTPS website URLs are normalized to hostnames; suffix rules include subdomains with domain boundaries.

0.10.0 enables master/.ir once when migrating older settings, records direct_defaults_version=1 and preserves subsequent opt-out. Xray receives domain/process direct rules. WinINET receives *.ir and validated custom apex/suffix entries, so compliant browsers can go direct without entering the core at all. Exact prior bypass/PAC/proxy values are restored through the lease.

This is not TUN. Native games that ignore Windows proxy may already go direct; another VPN or browser proxy extension is outside this routing scope. Non-.ir embedded resources are not automatically domestic. Protected/elevated process lookup can fail; unmatched incoming traffic stays proxied and emits a sanitized warning. Health, IP/country and service checks intentionally keep the selected proxy route.

### UI and runtime identity

Native glass dashboard, original icon/splash, compact speed/IP/country display, ping-colored connect ring, 10 HTTPS service tiles, one-second nonmodal green notices, actual page/category history, Alt+Left/Right and mouse side buttons. Service tiles are website header checks, not full native-app compatibility tests. The adult-site tile is obscured.

Settings cards have subtle static depth. Background spheres are painted on ordinary repaints, with no permanent animation timer. Lightweight/high-contrast modes disable extra effects. Event filters/timers are cleaned up when closing.

ShadowBox.exe supervises a branded runtime/ShadowBoxHost.exe. That native C host loads the existing python313.dll and calls Py_Main in-process rather than spawning pythonw.exe for the UI. The guardian uses the same interpreter host. Native binaries were cross-compiled and inspected, not executed interactively on Windows in the previous environment.

### Signing

No trusted signing account/certificate/private key is included. The last distribution is unsigned. tools/sign_release.py is an optional Windows certificate-store/SignTool workflow for a real existing identity. It does not generate/install a self-signed trust root. Do not promise that adding resource metadata or an untrusted signature fixes SmartScreen.

## 4. Relevant release sequence

| Release | Relevant change |
| --- | --- |
| 0.7.0 | Offline base installer, refined grouped server UX, verified group tests, compact home |
| 0.8.0 | Section 14 domain/local-process direct exceptions; explicit network saving |
| 0.9.0 | Main automatic group connection, richer source sheet, additional transports, nested feeds, URL exceptions, real navigation, native host, release acknowledgement |
| 0.10.0 | UTF-8 persistence, saving while connected, validated form autosave, live-session diagnostic snapshots, default .ir WinINET/core bypass, source controls, remembered groups and light depth |

The owner reported unsaved Settings, direct-site failure and source UI/control problems before 0.10.0. Those paths were changed and tested locally. There is **no subsequent owner confirmation that 0.10.0 resolved them on their Windows machine**. Start a new bug task by reproducing rather than relying on earlier confident prose.

## 5. Evidence and limitations

Historical whole-suite result for 0.10.0: **184 passed, 1 skipped, 0 failures, 420.56 seconds**. Later focused result: **11 passed, 95.72 seconds**, including additional diagnostic snapshot and restyling regressions. The focused run overlaps the whole suite; do not add counts as if all were distinct tests.

Sources: docs/test-results-v0100.xml, docs/test-v0100-focused.xml and the first section of docs/TEST_RESULTS.md. Real local Xray/TLS/REALITY tests used generated fixture credentials, not the owner's private server.

The skipped process-lookup case was blocked by this host's Linux netlink restrictions. Actual Windows WinINET and DPAPI, native-host startup/Task Manager presentation and process-based exclusions were not interactively verified. No new runtime suite was executed merely to create this documentation-only handoff. Handoff verification covers ZIP integrity, original file identity, source syntax and file manifest.

## 6. Known gaps / next priorities

### P0: full-installer packaging is stale (found during handoff inspection)

The current launcher requires runtime/ShadowBoxHost.exe and the host's ._pth file. tools/package_update.py and tools/package_windows.py include these. **tools/build_installer.py does not currently stage that host/.pth**, still selects RELEASE-0.7.0.md and names the output ShadowBox-0.7.0-Setup-x64.exe. tools/installer.nsi also needs a version/payload audit. A successful NSIS compile alone would not prove that its installed app can start.

This handoff intentionally preserves all original source bytes. Before shipping a new complete installer, fix the staging/version/docs, rebuild the uninstall file list from the actual payload, extract the resulting installer to verify the host/runtime and test installation/launch/update/uninstall on Windows. The last delivered 0.10.0 artifact was an overlay for an installed modern base, not a newly validated 0.10.0 complete installer.

### P1: artifact/version names and historical documentation

The portable builder includes the current host but still names its ZIP 0.6.0. Some audit/screenshot scripts refer to historical directories or an unavailable baseline checkout. Do not report those scripts as fresh successful checks without their required baseline. Read app/resource version values and actual payload, not old filenames alone.

### P1: Windows confirmation

Use a clean Windows 11 environment to verify preference reopening, user-locale/Persian paths, per-user installed/portable storage, normal disconnect and forced termination recovery, WinINET bypass on a controlled .ir domain, the branded host/guardian and current Task Manager grouping. Check source handling when providers do not publish quota/expiry. Use sanitized diagnostics rather than asking the owner to paste secrets unnecessarily.

### P2: broader protocol/backend and signing work

Add support only with a validated serializer/lifecycle adapter and real tests. Do not enable TUN/WFP/kill-switch controls that have no implementation. Trusted signing requires an identity that is not in the project. A separate Windows 7 branch requires its own source/runtime compatibility work.

## 7. What is in this ZIP

All 487 original entries from the verified 0.10.0 source archive are retained unchanged, including Python/C source, assets, tests, pinned dependency manifest, build scripts, notices/licenses and historical reports. New handoff files provide orientation and a per-file SHA-256 inventory.

Excluded as before: downloaded Python/Qt/Xray runtime binaries, built EXEs, the user's installed profiles/settings/backups, signing credentials and the separate Legacy branch. These are not missing first-party application code. Reproduce third-party binary inputs using the pinned download script and lockfile. No personal instance data was added to the handoff.

Original baseline archive SHA-256: df22974468474cac549403503263c107704121621361b0e5b0dc63a0c4d7c3f0.
