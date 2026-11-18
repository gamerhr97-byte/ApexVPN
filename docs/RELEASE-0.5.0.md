# Shadow Box 0.5.0

The application is now named **Shadow Box**. Original GPL attribution and the compatible data/lock/lease/import identifiers are retained. Existing profiles, subscriptions, Windows proxy recovery records and startup registration are not renamed or reset.

## User-visible changes

- More depth on the existing glass dashboard: static card shadows, layered spherical power-button shading, a complete latency-colored ring and subtle optional hover lift. Widget order, positions and sizes remain unchanged. New `shadow-layout-audit.json` compares power/server/ping/speed/connect geometry against the actual 0.4.0 source. Effects can be disabled; high-contrast and lightweight modes remove depth. Reduced motion suppresses hover animation. There are no continuously running animation timers.
- Original vector identity: an internet globe above a dimensional network cube, available in SVG/PNG/multisize ICO. The Qt window and tray use the same icon. The Windows x64 launcher was recompiled with embedded icon and Shadow Box 0.5.0 version resources. `ShadowBox.exe` is the primary launcher; an identical `NekoRayNext.exe` compatibility alias keeps old shortcuts working.
- Real subscription usage bars: `(provider upload + provider download) / provider total`. A small overlay fits inside the existing selected-server card without increasing its height. Every subscription also has a quota bar in Settings and the existing subscription manager. Upload/download/positive total must all be supplied as valid numeric provider metadata. Missing/invalid/zero/unlimited quota stays unavailable; local session counters never substitute for account usage. Bars clamp at 100% while the text can truthfully show over-quota usage. The displayed figure is a snapshot from the last successful subscription refresh, not a live provider counter.
- Responsive Settings: the first screen is a full-width category menu. Selecting an item opens only its section; the hamburger returns to categories. Controls stack on compact widths and tool grids collapse to one column. Opening Settings, searching and changing any of thirteen categories never resize the window. The large legacy Settings-only saved dimensions are ignored. A new private compact-window preference optionally restores the last actual home/Settings size only at launch.
- A dedicated thirteenth **Logs** category: live sanitized structured events, level control, text search, severity filter, count, clear, copy and text export. Messages are constructed from fixed code/message tables, with timestamps and known lifecycle stages. Raw incoming text, UUIDs, names, hostnames, URLs, tokens, passwords and raw core output are not echoed. The bounded 500-entry history is in memory and clears at restart. The default Error level retains the previous user's preference; choose Info/Debug to include successful connection events.
- Four original quiet PCM cues for click, verified connect, disconnect and error. Native Windows `winsound` playback uses asynchronous flags and local WAV files. Sound can be disabled in Interface & Tray; it does not change the system mixer or other programs. A Test Sound action is available. Linux has no playback backend and reports that limitation; native Windows audibility is not certified by Linux tests.

## Compatibility and limits

The verified connection/core/proxy lifecycle is preserved. Xray remains the only implemented core adapter. TUN, per-EXE split routing, kill switch, seamless switching and other-core execution remain explicitly unavailable. No new routing/firewall/driver claim is made in this visual release.

The portable folder remains `NekoRayNext` internally for safe updates. Launch `ShadowBox.exe`; the old filename remains a compatible alias. Data under `data` is never included in the update ZIP. Existing non-portable environment/data identifiers remain compatible so the rename does not strand credentials or recovery records.

The suite uses real Qt, local TLS/HTTP servers and real Xray on Linux. Windows PE resource verification and native 200% Qt scaling are checked locally, but interactive Windows 11 launch, audio output, Explorer icon-cache behavior and platform integrations need real Windows validation. Screenshots marked as sample quota use explicit temporary test data and never simulate a verified connection.

## Update

Quit the old app through its tray menu and let proxy restoration finish. Back up the existing portable folder. Merge the `NekoRayNext` directory from the update ZIP into the existing one, replacing program files and both launchers. Keep `data`. Start `ShadowBox.exe`. The full portable package is for a separate clean extraction; copy your backed-up data only when intentionally moving installations.
