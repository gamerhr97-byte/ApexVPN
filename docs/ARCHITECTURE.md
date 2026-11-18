# Architecture

`app.py` selects GUI versus stdlib-only guardian mode, resolves the data directory,
and acquires a Qt lock to prevent a second app using that directory.

| File | Responsibility |
| --- | --- |
| `nextapp/ui.py` | Native Qt Widgets pages, tray, dialogs, bounded chart, user actions |
| `nextapp/presentation.py` | Code-painted glass surface and vector controls |
| `nextapp/importers.py` | Manual URI construction and bounded local QR decoding |
| `nextapp/i18n.py` | Persian common UI strings and RTL choice |
| `nextapp/profiles.py` | Lossless URI/JSON ingestion, strict adapter validation, Xray JSON |
| `nextapp/storage.py` | Atomic profile/subscription catalog, Windows DPAPI, backup snapshots |
| `nextapp/subscriptions.py` | Source-group reconciliation with stable IDs and isolated replacement |
| `nextapp/errors.py` | Fixed error codes; raw core message classification without retention |
| `nextapp/engine.py` | Core version/preflight, stdin config, process lifecycle, real health gates |
| `nextapp/network.py` | Explicit HTTP proxy health checks, HTTPS subscriptions, TCP latency, metrics |
| `nextapp/proxy.py` | WinINET per-connection settings and compare-before-restore lease |
| `nextapp/guardian.py` | Waits on GUI process handle, attempts owned proxy restoration |
| `nextapp/migration.py` | Backup-first legacy import with review-only retention |
| `nextapp/hardware.py` | Read-only device detection with unknown fallbacks |
| `tools/launcher.c` | Windows GUI-subsystem launcher for bundled pythonw.exe |

## Connection lifecycle

1. UI requests a connection, then a worker validates the adapter and local ports.
2. Xray version is checked; `xray run -test -c stdin:` checks the exact config.
3. A single owned core is started. Configuration crosses its private stdin pipe;
   stdout/stderr are read in bounded fragments, classified to fixed categories, and
   immediately discarded because upstream messages may include credentials.
4. On Windows a kill-on-close Job Object owns the child process.
5. A local listener check establishes readiness only. Certificate-validated
   HTTPS through the explicit proxy must succeed; a separate HTTP check is optional.
6. If System Proxy is selected, the stdlib guardian starts and signals readiness,
   then the old settings are protected and durably saved before WinINET changes.
7. Only then is Connected emitted. Active core metrics are read every 2 seconds.
8. Normal disconnect restores the previous proxy if ownership matches, stops
   the core, terminates its watcher, and releases resources. On mismatch, it
   retains the recovery backup and reports the concurrent change.

A startup/connection error enters Error. A crashed core or failed requested
health verification restores the owned proxy, stops the core, and enters Error.
The app intentionally requires an explicit reconnect rather than automatically
switching profiles or inventing a Reconnecting state.

## Concurrency and retention

The GUI stays on the main thread. Qt signals carry results from workers. Core
operations use at most four executor threads; configuration/connect transitions
are guarded. Cleanup is serialized. Late health results check process identity
before acting on a newer session. TCP tests use bounded batches of the selected
size (default four, maximum sixteen), and cancellation stops later batches.

Traffic history is a deque with at most 120 samples; sanitized error history is
at most 50 items. Bulk latency writes are coalesced. Idle mode performs no network
checks. Optional HTTPS health checks run every sixty seconds. There is no
browsing history and no telemetry. The metrics endpoint binds to loopback only.

## Sensitive material

Profiles and recovery backup files use current-user DPAPI on Windows. All
application writes use atomic rename. The app never saves a plaintext runtime
core config. Normal diagnostic reports omit hostnames, profile names, original
links, executable paths, UUIDs, passwords, subscription URLs, encryption
strings, and raw core output. Hardware details and times may appear in reports.
The user can inspect original links in their own protected stored data; a
profile editor or plaintext export is not enabled.

## Windows safety boundaries

System proxy management uses WinINET `INTERNET_OPTION_PER_CONNECTION_OPTION`
for the default LAN connection plus settings-change/refresh notifications.
It snapshots flags, manual server, bypass and PAC URL. It does not touch WinHTTP,
Ras/VPN per-connection entries, routes, DNS settings, firewall, antivirus, or drivers.
Recovery compares the complete applied snapshot before restoring the complete
previous snapshot. There is no force-off shortcut. Watcher startup must precede
proxy activation. There is no boot service, automatic installer or updater.

A kill of both GUI and watcher, reboot, power loss, access-policy failure, or a
partial OS failure may leave the durable recovery file for next-launch review.
Ownership comparison is deliberately conservative, not a distributed transaction
against other programs. Actual Windows API behavior still requires validation.

## Subscription transactions

`profiles.dat` accepts the old list format and now writes an encrypted object
containing both profiles and subscriptions in a single atomic rename. UI-thread
commits reconcile a downloaded, fully parsed source before replacing anything.
Background workers never mutate stored data. URL edits take effect only when
the replacement download is valid and storage succeeds. Unchanged items retain
IDs and favorites; only that source's stale entries are removed. Failure retains
the previous catalog. The selected-profile preference is a separate best-effort
write; startup falls back to a valid stored profile if it refers to a removed ID.

## 0.3.0 presentation and IP lookup

The home screen uses a compact native window, painted gradients and translucent
Qt panels; no desktop blur/driver or browser is introduced. Server/settings
screens widen as needed. Day/night preferences are saved. A one-time design
migration chooses Light without modifying networking preferences or profiles.

Public IP is requested only from an explicit click. HTTPSConnection tunnels
through the current core HTTP port with certificate validation and bounded JSON
response parsing. It does not use environment/system proxy discovery and has
no direct fallback. Qt results carry the owned process identity; late results
from a different session are ignored and the cache is cleared at disconnect.

Manual and QR imports feed the same lossless parser/store as existing imports.
QR decoding is local, image bytes/pixels are bounded, only one QR is accepted,
and invalid schemes are refused. QR payloads are not logged.

## 0.3.1 interaction additions

The home-only Paste shortcut captures clipboard MIME data when invoked. Bitmap
QRs become bounded PNG bytes in memory and are passed to the existing local
decoder worker; local image-file URLs are opened only for that explicitly copied
image. No persistent clipboard monitoring occurs. The shortcut is disabled away
from home, so editable settings keep native paste behavior.

The + control toggles a child bottom sheet with four icon actions; Escape and ×
close it. The connection ring draws a closed ellipse and uses user-defined
latency boundaries: <150 green, [150,200) blue, >=200 red. No animations/polling
were added. Country data is requested only after an explicit IP reveal, over
HTTPS through the owned core. Responses must match the requested IP. SVG flags
are local licensed assets; unknown/unavailable countries yield no flag.
