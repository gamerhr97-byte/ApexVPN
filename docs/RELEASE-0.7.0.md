# Shadow Box 0.7.0

- Real offline, per-user NSIS setup for Windows 10 1809+ / Windows 11, Intel/AMD x64. Python 3.13.9, Qt/PySide6 6.8.3, pinned Xray, QR decoder, Pillow and app-local MSVC libraries included. No internet/elevation is needed for installation. Unsupported old Windows and ARM are rejected before copying files.
- Native loading window with the new original network-S icon, readiness event and 30-second splash bound. Connecting also displays the icon. The launcher prevents simultaneous launch/installer overwrite via a session mutex.
- First launch detects CPU count and physical RAM locally. At <=2 logical CPUs or <4 GiB RAM, it starts with lightweight mode, reduced motion and no visual effects. Preferences are subsequently preserved; the performance switches remain available.
- Home is a responsive widget, without a scroll area. Ring and ten service tiles shrink on shorter windows. Settings keep wheel/keyboard scrolling with hidden bars; lists use pixel scrolling, touch kinetic input and styled native scrollbar thumbs.
- Searchable subscription sheet replaces the system dropdown. Source refresh has its own button and busy indicator. The source's overflow menu has copy, rename, edit URL and delete actions. Quota remains the provider's actual snapshot; missing data is never invented.
- Server context menu offers connect, copy original share link, edit one link, favorite and delete. Ctrl/Shift selection and Del support batch deletion; deleting the active server requires disconnecting. Destructive actions retain a backup. Editing a subscription profile preserves its source; a later refresh may replace local edits.
- Group tests default to HTTPS: an isolated Xray instance verifies the actual authenticated TLS tunnel. TCP is an explicitly separate reachability test. At most two HTTPS probes run concurrently (one in lightweight mode); optional plaintext check and redundant failure TCP check are skipped for group probes. Active sockets still finish within their configured timeout on cancellation.
- Every group row shows queued/testing/result. Live count, progress bar and elapsed seconds show progress; a final summary marks completion/cancel. Subscription update shows indeterminate progress while the provider response is pending and a final success/failure count. This does not pretend to know a download percentage the provider hasn't supplied.
- With no server row selected, Connect tests only the currently visible group using HTTPS. The first verified candidate connects immediately; when the fresh batch is complete, the fastest fresh verified result is selected. Switching is a supervised stop/restore/reconnect, so existing TCP sessions may close. Manual selection/disconnect cancels automatic selection. If no candidate passes, the existing connection is kept.
- Notifications use short nonmodal in-window toasts; confirmations remain for destructive operations. Preferences, imports, connection states, tests, updates, edits, copies, favorites and deletes report their outcomes.
- The icon is original, inspired by the requested simple visual direction. No Hiddify artwork/code is bundled or affiliation claimed.

## Scope and limits

The screenshot was Windows Defender SmartScreen's unknown-publisher warning, not a Python exception. This deliverable is unsigned: no publisher certificate or signing service was supplied. The installer does not disable SmartScreen, Defender, certificate checks or security settings. Signing with a trusted publisher certificate and reputation (or Store distribution) is a separate release requirement; even a valid fresh signature does not guarantee no warning.

Qt 6.8 cannot be made Windows-7-compatible by disabling animations. A legacy backend/runtime would be a separate maintained build. This release explicitly supports Windows 10 build 17763+ x64 and Windows 11 x64, not Windows 7/8, x86 or ARM.

Ten site checks measure real HTTPS response headers through the current proxy; they do not certify login, playback, DRM, geolocation or native-app availability. Adult-site tile remains obscured. No production profiles/credentials or real customer site results are packaged. Existing unsupported driver/WFP/TUN functions remain disabled.

131 tests passed in 56.90 seconds on the final source. Validation is Linux Qt offscreen UI and local Xray/TLS integration tests, Windows PE/resource inspection and installer payload extraction/comparison. Actual interactive Windows installation, upgrade, uninstall, SmartScreen policy and audio must still be checked on Windows; no Windows execution is claimed.
