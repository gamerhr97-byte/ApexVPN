# 0.3.0 — compact glass dashboard

- Compact centered connection circle following the supplied sketch; no sidebar.
- White glass-style panels and day/night themes. Connected control turns pink
  and shows measured HTTPS latency; clicking it disconnects.
- Server card opens the server manager. Upload/download use actual Xray counters.
- Click Ping to view the exit IP from an explicit proxy-tunneled HTTPS request;
  click again to return. No direct fallback or persistent IP logging.
- Top + menu: clipboard, manual VLESS/Trojan/SS, local QR image, link/subscription.
- QR is decoded locally with ZXing; ambiguous/invalid content is refused.
- Settings includes theme, subscriptions/update, server manager and diagnostics.
- Existing network engine and profile compatibility remain in use.

Close the app and back up data. Merge the entire small-update `NekoRayNext`
folder over the existing installation, including the new `runtime/` files.
The overlay adds only QR/Pillow runtime modules; it does not replace Python,
Qt, Xray, the launcher or data. Or use the full portable release and copy data
under the same Windows account. The footer identifies 0.3.0.

45 automated tests passed on Linux, including a real local connected dashboard,
measured latency, proxy-tunneled IP response, manual-dialog save and QR decoding.
Windows 0.3.0 and real public IP lookup still need target-machine validation.
Screenshots are native Qt renders; connected-local is a genuine controlled tunnel.
