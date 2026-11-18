# NekoRay Next 0.2.0

- Smaller 960×700 default window, shorter sidebar, no slogans, unboxed statistics,
  and optional traffic chart instead of an always-visible chart.
- Protected subscription source storage, named subscription management, single-source
  refresh and update-all. Last successful update times and summary counts are shown.
- Refresh validates the entire response before atomic commit; only the selected
  source's entries are replaced. Stable entries keep IDs, favorites and measurements.
  Failed downloads, invalid content and disk-write failures preserve the old catalog.
- Stage-specific connection errors, fixed secret-free error categories, actual Xray
  preflight in diagnostics, Windows Job Object API/error-code reporting, and a short
  selected-server TCP diagnostic after failed HTTPS verification.
- HTTPS remains mandatory; a failed optional HTTP check no longer rejects a verified
  HTTPS session. Raw core output is classified in bounded fragments and not retained.
- Existing 0.1.0 profile lists are readable. The first successful catalog-changing
  operation writes the new combined profile/subscription format, with a backup.
- 35 automated tests passed on Linux, including real Xray traffic, ML-KEM, a blocked
  HTTP endpoint alongside successful HTTPS, and real local HTTPS subscription fetch.

## Applying the small update

1. Close NekoRay Next completely (use tray Quit if hidden). Do not update during a
   connection or subscription refresh.
2. Keep a copy of the current `NekoRayNext/data/` folder.
3. Extract `NekoRayNext-0.2.0-update.zip` into the **parent** of the existing
   `NekoRayNext` folder. Replace the included application files when prompted.
   The update archive contains no `data/`, `runtime/`, `core/` or new EXE; it uses
   the existing 0.1.0 launcher/runtime/core and leaves your stored data in place.
4. Open the existing `NekoRayNext.exe`. The sidebar should show **0.2.0**.
5. In Servers choose Subscriptions. Add your HTTPS sub URL once, then use
   Update subscriptions whenever needed. Old 0.1.0 imports had no saved source URL.

A full portable release is also provided. For a clean install, extract it separately
and copy the existing data folder under the same Windows account; check the saved
core path in Settings if the installation directory changed.

## What the supplied report establishes

The report says direct TCP to the selected remote server was refused. That is not
proof of a local Windows proxy problem; no pending recovery lease was present.
The old generic error hid other causes, so its exact originating exception remains
unknown. This release removes that ambiguity for subsequent attempts. It cannot
make an unavailable or rejecting remote server accept a connection. No target-server
credentials were supplied, so its successful connection remains unverified.

Actual 0.2.0 Windows execution and WinINET/guardian recovery still require target
validation. TUN remains disabled. The supplied 0.1.0 screenshot/report confirms
Windows UI startup and read-only hardware diagnostics, not a working tunnel.
