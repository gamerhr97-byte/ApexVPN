# Historical MVP limitations

This document records the early MVP. For the current 0.10.0 scope, use README.md, RELEASE-0.10.0.md and UPDATE-0.10.0.md. Category 14 now implements direct domain/local-process exceptions; full-system TUN capture is still unavailable.

# Original scope

This is an MVP, not the complete twenty-section production specification.

## Implemented and locally exercised

- Native Qt dashboard; dark/light/accent themes; English and common Persian UI.
- Stored URI import: VLESS, VMess, Shadowsocks, Trojan, Hysteria2.
- Connected adapter subset: VLESS TCP/RAW + REALITY/TLS/encryption, supported
  WS/gRPC/TLS combinations, AEAD VMess subset, Trojan TLS, basic Shadowsocks.
- Original URI/unknown fields retained. Unsupported fields stop connection.
- Xray preflight, core process supervision, mandatory HTTPS verification plus optional HTTP check,
  loopback-only HTTP/SOCKS inbounds and real core metrics.
- Clipboard, drag/drop, file import; protected HTTPS subscription storage and on-demand refresh.
- Server name/protocol/search/filter/favorites, TCP tests, test time, cancellation.
- Backup/retention migration, diagnostics, manual recovery action and preferences.

## Implemented but NOT validated on Windows

- C-built x64 GUI launcher and assembled embeddable Python/Qt portable runtime.
- DPAPI storage and backup protection.
- WinINET snapshot/change/notification/exact restoration and concurrent-change
  detection; API flags/PAC/autodetect behavior need real Windows testing.
- Job Object lifecycle and stdlib guardian recovery after forced termination.
- Hardware RAM/GPU/CPU/storage detection, tray and notifications, Win11 snapping,
  and Windows 100/125/150/200 percent scaling.

The Linux unit tests for proxy safety use a test adapter; they are not evidence
that the Windows API implementation has been executed. Qt screenshots were
made on Linux with its offscreen platform plugin.

## Not implemented or deliberately restricted

- **TUN mode, driver installation, route/DNS changes and TUN recovery.** No Wintun
  DLL is shipped in this package. Settings explain that TUN is unavailable.
- Automatic startup registration, installer, code signing, authenticated updates,
  automatic reconnect/backoff, profile failover and multiple selectable cores.
- Hysteria2 connections. Its URI is stored, but this adapter refuses to connect.
- Full custom Xray/sing-box JSON execution. Xray JSON is preserved as review-only;
  custom routes, inbounds or unknown options are not silently rewritten.
- Most legacy JSON conversions. Basic SS converts; all original config and
  subscription data is backed up; other profiles remain review-only.
- Scheduled/automatic subscription refresh. On-demand URL editing and refresh are implemented.
- Country inference/flags/sort: no trustworthy metadata was supplied; none invented.
- Editing existing profiles in place. New manual VLESS/Trojan/SS entry is supported.
- Fully translated diagnostics/dialogs, localization quality review by a native speaker.
- Region rules, DNS/IPv6 settings, ICMP/packet-loss tests, protocol-level bulk tests,
  profile HTTP-latency bulk tests, guaranteed authentication classification for every core message format.
- UI sorting by country or last successful connection; last-success time is stored.
- TCP result error categories are summarized in the test footer; failed rows show
  Not Tested rather than a persisted per-row reason. Numeric latency rows use the
  TCP column's unit; they do not imply ICMP latency.
- Production Windows benchmark targets, memory-leak soak tests, Windows API
  failure injection, full OS disconnection/reconnection and reboot recovery tests.

## Operational caveats

The HTTPS health check must return 2xx. Blocking that endpoint can cause a
connection failure even if some other proxy traffic works. The plaintext HTTP
check is optional and cannot override a successful HTTPS verification. A manual health failure
stops the session conservatively. HTTPS verifies certificates with the runtime
trust configuration. No TLS bypass is offered.

A listener probe can race another program before Xray binds its ports. Core preflight
and subsequent verified proxy traffic catch the resulting failure. A selected
external core is executable code: only choose a trusted Xray binary. Version
output alone is not a signature. No updater downloads replacement binaries.

Local metrics use Xray's debug-vars endpoint with outbound counters; counters
include health probes. Other local processes under the user account can access
loopback HTTP/SOCKS/metrics ports. This is not a multi-user isolation boundary.

Canceling TCP tests stops later batches; OS DNS resolution is synchronous and
may outlast the socket timeout. Exit waits for active work to finish. Backup
retention is manual; encrypted backups can accumulate after repeated imports.
Windows DPAPI binds data to the original account; “portable” does not mean
secrets can automatically move between machines/accounts.

## 0.2.0 status

Windows UI startup and hardware detection were observed in the user-supplied
0.1.0 screenshot/report, with a failed remote connection. The new package still
needs Windows validation. The supplied report shows the selected remote server
refusing direct TCP; it does not establish which internal startup/handshake
exception caused the original generic message. No claim that the user's server
connection is repaired is made without a new verified test.

## 0.2.1 parameter handling

Explicit TCP/RAW headerType=none and REALITY/TLS aliases are now supported.
Other header types and unimplemented fields still block. Publicly registered
unsupported names are reportable without their values; unlisted key names are
local-only until the user explicitly copies and reviews them.

## 0.3.0 presentation scope

The user confirmed 0.2.1 works on their Windows system. The 0.3.0 UI, newly
bundled QR libraries and external ipify lookup require Windows validation.
The dashboard glass effect is painted translucency over a native gradient,
not desktop blur/Mica. QR uses local image files, not a live camera.
IP lookup is on-demand through the verified proxy, does not affect the tunnel
on lookup failure, and exposes the exit IP to the configured ipify endpoint
by the nature of that request. No IP lookup occurs on startup or in idle mode.

## 0.3.1

Country geolocation is approximate and depends on country.is availability. Only
the requested exit IP is shared through the proxy; a failed lookup leaves IP
visible without a guessed flag. New UI and clipboard behaviors still require
validation on the target Windows machine. Clipboard-image QR import is local
and on-demand; camera capture remains outside this release.

## 0.4.0 Settings supersedes earlier preference descriptions

See `RELEASE-0.4.0.md` for the implemented/unsupported matrix. Twelve internal Settings categories, bounded failover/recovery, explicit pinned core installation, subscription scheduling, Telegram proxies and scoped appearance are now implemented. Xray remains the only active adapter. TUN, per-application split routing, kill switch, seamless switching, other-core adapters and whole-device leak prevention remain unavailable. Windows-specific integrations still need real Windows 11 validation.
