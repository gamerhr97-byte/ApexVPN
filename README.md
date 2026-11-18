> Current: Apex VPN 1.11.0 full source project. Start with NEXT_AI_HANDOFF_FA.md, README-1.11.0-FA.md, and AGENTS.md. Older release notes are historical.

> Current: Apex VPN 0.10.5. Read README-0.10.5-FA.md and docs/VALIDATION-0.10.5-FA.md. Older sections are historical.

> Current release: Apex VPN 0.10.4. Read README-0.10.4-FA.md and docs/VALIDATION-0.10.4-FA.md first. Older sections below are historical.

# Shadow Box 0.10.3

Windows x64 portable: extract the complete archive and run ShadowBox.exe. Read README-0.10.3-FA.md for current behavior, setup and limitations. Actual Windows execution is not verified in this build environment.

---

# Shadow Box 0.10.0

Native Qt proxy client for Windows 10 1809+ / Windows 11, Intel/AMD x64. Connections use supervised Xray with real HTTPS verification and guarded proxy recovery.

For an existing modern 0.7.0 / 0.8.0 installation, apply `ShadowBox-0.10.0-update.zip` as described in [the update guide](docs/UPDATE-0.10.0.md). For a new computer, install the 0.7.0 base first using `ShadowBox-0.7.0-Setup-x64.exe`, then apply this update. The offline installer includes Python, Qt, Xray, QR/Pillow and app-local MSVC libraries. No administrator access or dependency download is required. Close the app and tray icon before upgrading. Profiles use the existing `%LOCALAPPDATA%\NekoRayNext` location and survive uninstall. Portable users: see the migration instructions in [offline installation](docs/INSTALLER.md).

The compact server view has a searchable source sheet, per-source refresh/menu and provider quota bar. Right-click a server to connect, copy/edit its share link or favorite/delete it. Ctrl/Shift and Del support batch deletion. With no server selected, Connect group tests the visible group, connects the first HTTPS-verified server, then switches to the fastest fresh verified result. Manual selection or cancellation stops that automatic choice. Switching closes the old core and reconnects; existing TCP sessions may close.

Group tests default to HTTPS through isolated cores; TCP remains an optional reachability-only test. Queued/testing/final status, live count, elapsed time and progress make the current work visible. Failed results distinguish Timeout, Refused, Failed and Unsupported. Updates show loading while waiting for the provider, then a summary.

Home has no scrolling viewport and adapts the ring and service icons to available height. Fourteen Settings categories retain wheel/keyboard scrolling without visible scrollbars. Safe preferences autosave; core/network/Windows changes still require Apply. Short nonmodal notifications report action outcomes. The original purple network-S icon appears in native loading, connecting, tray and shortcuts; this is not a Hiddify product.

Ten service tiles check HTTPS headers through the connected proxy, without cookies or direct fallback. An HTTP success does not guarantee login, video, DRM, geographic eligibility or native-app functions. The requested adult tile stays obscured. Disable service checks in Security & Privacy if desired.

See [release notes](docs/RELEASE-0.7.0.md) and [offline installer guide](docs/INSTALLER.md). Source delivery also contains test reports, screenshots and all build scripts. The executable is unsigned: SmartScreen may still warn about an unknown publisher. No security protection is disabled or bypassed. Windows 7/8, x86 and ARM need a separate backend/runtime build and are not supported by this Qt 6 release. Driver TUN, WFP kill switch and non-Xray adapters remain unavailable. Section 14 provides validated domain and local-process direct exceptions for traffic entering the HTTP/SOCKS proxy; this is not full-system capture. See [0.10.0 update instructions](docs/UPDATE-0.10.0.md).

## Direct exceptions (Settings 14)

Disconnect first. Enable direct exceptions, leave .ir enabled if desired, and enter other domains one per line (example.com includes subdomains). Add EXE paths using the file picker, or enter exact EXE names such as game.exe. Apply, reconnect, and restart the affected application to close its existing connections. Direct traffic exposes the actual connection IP. Domain rules need a hostname (HTTP CONNECT, SOCKS remote DNS or recognized SNI); IP-only and encrypted/hidden names cannot be classified as .ir. External resources on other domains need their own entries.

Xray process lookup is on demand, not a polling process monitor. Paths/names are case-sensitive; pick the actual network process rather than its launcher. A failed lookup leaves unmatched traffic proxied and triggers a sanitized warning once per session. Rules do not capture games that ignore system proxy, do not override another VPN, and do not add UDP capture. Health tests, exit-IP lookup and the ten service checks remain forced through the selected proxy.

Release 0.10.0 adds a fresh group scan to the main Connect action, a theme-aware source sheet with quota/expiry, bounded nested subscription feeds, gRPC+REALITY/XHTTP/HTTPUpgrade, full website URL exceptions, one-second green feedback, actual page/category navigation history, mouse side-button navigation, an embedded native ShadowBoxHost process and acknowledge-once release notes. See docs/RELEASE-0.10.0.md.

0.10.0 fixes UTF-8 preference reads and active-session saving, enables .ir direct routing by default in Xray and the WinINET bypass list, adds source-sheet controls and remembered groups, and adds idle static depth. Existing users receive the default .ir policy once; later opt-out survives. Validated forms autosave while ports/core/Windows integration/imported batches use Save settings. This release is unsigned because no trusted code-signing identity is available.
