# 0.3.1 — dashboard refinements

1. Closed continuous connection ring; removed the intentional arc gap.
2. Smaller server, download and upload cards.
3. Exit-IP display includes a bundled SVG flag after a matching country lookup.
   The country service receives only the IP, through the proxy; no guessing on
   failures. IP geolocation is approximate.
4. Connected control is green below 150 ms, blue from 150 to below 200 ms, and
   red at 200 ms and above, based on actual measured HTTPS response latency.
5. The top-left + now toggles a compact bottom sheet with four vector-icon
   actions. Close it with +, × or Escape.
6. Home Ctrl+V accepts profile text, subscription URLs, QR bitmap images, or a
   single copied local image file. Settings/dialog text pasting is preserved.

Close the app, back up data and merge the entire update folder including its
runtime and assets directories over the existing installation. The update
contains no data, core executable or launcher. A complete portable release and
source are also supplied. The footer shows 0.3.1.

54 automated tests passed on Linux, including a live Xray/TLS IP-country flow
with a controlled service response, QR and clipboard interactions, ordinary
settings Paste, ring pixel regression and latency boundary checks. New Windows
UI and clipboard behaviors still need target-machine validation.
