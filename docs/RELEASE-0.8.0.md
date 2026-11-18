# Shadow Box 0.8.0 — Direct exceptions

- Settings category 14, with icon and compact domain/EXE editors, file picker and contextual Persian/English help.
- Master enable switch (off by default), optional .ir suffix matching, custom domain suffixes and exact local process name/path rules.
- No new runtime dependency, driver, administrator elevation or background polling. The existing pinned Xray 26.3.27 implements the routes.
- Connection checks, public-IP/country lookup and ten service probes remain proxy-only even when an exception covers their domain or calling process.
- Invalid domains, URI/script input, wildcard/folder rules and oversized lists are rejected before saving. Network changes require explicit Apply while disconnected.
- Case-sensitive EXE matching and the limits of system proxy are explained. Failed process lookup produces one sanitized warning per connection, and unmatched incoming traffic remains proxied.
- Preferences and server data are retained. Personal EXE paths are excluded from preference exports.

Read UPDATE-0.8.0.md before copying the overlay. This update targets modern 0.7.0 Windows 10/11 x64, not the Legacy Windows 7 edition.
