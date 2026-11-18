# Shadow Box 0.9.0

Modern Windows 10/11 x64 overlay for 0.7.0 / 0.8.0. Preserve the existing runtime/core/data. Include the new runtime/ShadowBoxHost.exe and ShadowBoxHost._pth.

- Main Connect distinguishes implicit first/remembered profiles from an explicit manual connection. Auto mode freshly tests the current group (ignoring search), connects the first HTTPS-verified result, then the lowest measured verified latency. Choosing a source restores Auto mode; explicit server Connect pins the manual choice.
- Theme-aware, centered subscription sheet with provider-supplied usage/expiry. Unknown values stay unknown.
- VLESS gRPC + REALITY, XHTTP and HTTPUpgrade mapping; compatible headerType=none no longer triggers false Unsupported. Nonempty unsupported header obfuscation and unknown fields still stop serialization, preserving original links. No TLS certificate-verification weakening.
- Nested HTTPS subscription bundles with root grouping, metadata, fragments used as local titles, deduplication, cancellation, cycle protection and bounded depth/bytes/profiles. Failed refreshes retain the previous catalog.
- Focus delegate removes dotted cell outline while preserving keyboard selection.
- Full HTTP/HTTPS website URLs accepted in direct exceptions; suffix matching keeps domain boundaries. Checks stay forced through the selected proxy.
- One-second green nonmodal change notices; form errors also remain in Settings status.
- Bounded page/category back/forward history, Alt+Left/Right and mouse Back/Forward.
- Native ShadowBoxHost embeds the existing python313.dll in its own branded process; launcher and guardian use that host. No Python executable renaming, extra interpreter, driver or system changes.
- Acknowledge-once release notes and a Settings/General entry to reopen them.

See UPDATE-0.9.0.md and TEST_RESULTS.md for installation, limits and executed validation. Unsigned binaries remain subject to SmartScreen; no signing claim is made.
