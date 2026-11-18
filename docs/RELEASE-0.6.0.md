# Shadow Box 0.6.0

## Compact servers, identifiable sources

The server page now preserves the current window size. It contains a named subscription selector, provider-quota progress bar, search, a two-column server/result list and a compact test/connect row. Last-tested dates and protocol/favorite columns are removed from the visible table; protocol remains in the tooltip and favorites remain available from the overflow menu. Duplicate import/clipboard/file/migration buttons are no longer repeated below the list. Existing import options remain in the header + menu and Settings. Subscription management, refresh, favorite/delete and parameter-name review are available through the server overflow menu.

Every subscription is a separate group with its own profile count and quota snapshot. A successful import/refresh focuses its source group. Reopening the app restores the selected profile's source; All servers is an explicit optional view, not the default mix. A quota is calculated only from valid provider upload/download/positive total metadata. Missing/unlimited quotas are labeled unavailable, never inferred from local traffic.

## Measured tests and one-action switching

- **TCP** measures a real socket connection to the remote server port. It proves reachability only, not protocol authentication or a working VPN.
- **HTTPS** starts one isolated supervised Xray probe at a time, with private temporary listener ports, manual proxy mode and LAN bypass disabled. The candidate must pass the actual configured certificate-validated HTTPS request. No Windows proxy/driver/firewall setting is changed by a probe. The probe core is shut down after every test.
- Results retain method, measured latency and fixed status. Timeout, Refused, Failed and Unsupported are distinct from Not Tested. Older attempted failures without stored details become Failed, not invented timeouts. Reconciliation preserves test state for unchanged source profiles.
- Test group applies only to the visible source/search results and reports completed/total. Cancel skips queued work; active requests finish their finite network/core timeouts.
- Connect / Switch server performs old-core stop and ownership-safe proxy restoration before verifying the exact selected replacement. The caller no longer has to disconnect first. Repeated choices replace the pending target; explicit Cancel/Disconnect cancels it. A pending recovery record blocks a replacement. This is controlled reconnect, **not** zero-downtime migration or preservation of established TCP sessions.

## Ten web checks

After a verified connection, ten original recognizable site tiles make TLS-validated HTTPS requests **through that session's local proxy**: YouTube, Gemini, ChatGPT, Telegram Web, Instagram, WhatsApp Web, Discord, Netflix, Spotify and the requested adult site. The adult tile uses a neutral obscured 18+ symbol; no explicit imagery is fetched or shown.

Green tick means a successful 2xx website response. Red cross means request/HTTP failure; amber means a redirect, sign-in/proxy-auth challenge or rate limit. The measured HTTP/TLS latency is displayed when available. Click a tile for the public endpoint, exact HTTP status/reason and limitations. These requests do not prove account access, native app protocols, streaming/DRM, regional eligibility or complete IP reputation. In particular a homepage may work while video or an account feature does not. Conversely a WAF can deny an anonymous probe while a signed-in browser works.

Checks use HEAD, with a same-endpoint bounded GET-header fallback only for HTTP 405. They never read/display page content, send cookies or account/profile credentials, follow redirects or fall back to direct networking. Three workers are bounded, pending old futures are canceled and stale results are rejected by both generation and core-process identity. Disconnection clears results. Security & Privacy contains an on/off toggle. The fixed endpoints see the exit IP as an ordinary web request; no analytics service receives configuration data.

## Quieter Settings

All thirteen internal categories have original vector icons, including a white selected-state glyph. Essential settings are shown first. Technical/manual/unsupported controls, long explanations and extra tools are collapsed. Small help buttons explain controls without long paragraphs filling every row. Boolean controls use accessible checkable switches.

Scrollbar chrome is hidden inside Settings, including menus/reports/logs, while mouse wheel, touchpad, keyboard and scroll values remain active. Categories and controls stay within the current compact window. There is no forced expansion when entering Settings or Servers.

**Automatic save** defaults ON for a whitelist of harmless appearance/interface preferences. Networking, core paths/ports, Windows startup and other important drafts still need explicit Apply. Autosave validates against the active network settings and cannot accidentally commit an unfinished port/URL draft. Imported/reset batches remain staged until Apply. Disabling autosave leaves subsequent changes staged. Pending safe changes flush on leaving/closing before the debounce expires.

**Automatic performance tuning** has a separate on/off switch and chooses bounded CPU-aware concurrency, timeouts, retry/backoff and monitoring intervals; lightweight/battery policies remain enforced. Stored manual fields are disabled while automatic mode is on, with the effective value in their tooltip. Turning automatic mode off restores use of the stored manual values. Existing connection timeout changes take effect on the next connection; ongoing monitoring intervals use the active tuning policy.

## Identity, effects and code structure

The busy 3D cube icon is replaced with a high-contrast connected globe designed for 16–32 pixel use. SVG/PNG/multisize ICO and embedded Windows icon/version resources are rebuilt. Effects synchronize with the real Connecting/Connected/error state; the optional connecting animation stops outside Connecting and respects reduced motion, high contrast and lightweight mode. Core/network work remains asynchronous.

Business logic is separated into `server_page`, `profile_testing`, `connection_switch`, `service_checks`, `settings_policy` and `iconography` modules. The touched UI/controller modules are consistently formatted; schema validation and the existing guarded core lifecycle remain central. Existing profiles, private subscription catalogs and data/lease identifiers remain compatible.

## Validation and remaining limits

See TEST_RESULTS.md and the 0.6.0 JUnit/output files. Real local Xray/TLS tests cover authentication rejection, status interpretation, no direct fallback and live server replacement. Tests do not contact the ten production sites; those outcomes are measured on the user's actual connection. Interactive Windows 11, actual audio output, real Windows recovery APIs and production providers are not certified by Linux tests. TUN, WFP kill switch, per-EXE routing and other-core adapters remain unavailable.

Quit the previous app, back up the folder, merge the update into its existing `NekoRayNext` folder, keep `data`, and start ShadowBox.exe. The compatible old launcher filename remains available.
