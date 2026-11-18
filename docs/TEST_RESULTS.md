# Shadow Box 0.10.0 executed validation

Whole suite: **184 passed, 1 skipped, 0 failures** in 420.56 seconds (test-results-v0100.xml). Final focused regression run: **11 passed** in 95.72 seconds (test-v0100-focused.xml), including the additional active-session diagnostic-snapshot and no-unnecessary-restyling checks. Linux, Python 3.12, Qt 6.8.3 offscreen, actual pinned Xray 26.3.27. The existing REALITY local fixture timeout was made 20 seconds to allow local H2/camouflage negotiation under load; production application timeouts were not increased.

New executed checks:
- Explicit UTF-8-sig reads round-trip Persian paths regardless of Windows locale defaults.
- Saved active-session ports/routes survive reopening while the running Engine snapshot remains unchanged. Diagnostics and privacy checks follow live ports, not stored next-session drafts.
- Valid complete routing forms autosave while unrelated advanced port drafts remain uncommitted. Manual Save commits those drafts. Networking-only saves do not restyle the entire window; appearance changes still do.
- Default-on .ir upgrade occurs once and later explicit opt-out survives migration.
- WinINET bypass serialization includes *.ir and validated custom apex/suffix entries; the ownership lease restores the exact prior bypass/PAC/proxy values with a fake Windows adapter.
- Actual local HTTP through real Xray reaches a .ir fixture directly with the proxy upstream unavailable; a suffix-lookalike domain is not bypassed.
- Source picker preview does not silently choose a group; its copy action and selected-group persistence work across reopening.
- Existing real TLS/REALITY transport, grouped selection, proxy cleanup, native UI, import, quota, navigation and source refresh tests remain green.

The single skipped check is real OS process matching: this sandbox blocks the Xray netlink interface query. Windows WinINET/DPAPI, native launcher startup and Task Manager behavior have not been interactively executed here. Both Windows launchers were rebuilt as x64 GUI PE files with 0.10.0 version resources. Their Authenticode certificate tables are empty: no trusted signing identity was available and distribution remains unsigned. No trust root or self-signed certificate was installed. Optional signing tooling is prepared for a real existing Windows certificate-store identity, but was not used to claim signing.

Static gradients/spheres have no animation timer and honor lightweight/high-contrast settings. An isolated offscreen smoke check opened the Settings category about 0.08 seconds after the window was shown with effects enabled; this is not a Windows performance benchmark.

## Historical reports

# Shadow Box 0.9.0 executed validation

Final clean run: **177 passed, 1 skipped, 0 failed** in 97.26 seconds. Authoritative report: test-results-v090.xml. Python 3.12, Qt 6.8.3 offscreen, real pinned Xray 26.3.27 on Linux. Focused 0.9.0 regressions: 16 passed in 25.01 seconds (test-v090-focused.xml).

Executed scenarios include main-button group selection (fresh first-working then fastest HTTPS result, current group only, ignores search, respects explicit manual selection); actual TLS traffic through gRPC, XHTTP and HTTPUpgrade; actual REALITY + gRPC and REALITY + XHTTP traffic using ephemeral keys and a local TLS camouflage server; direct exception URL normalization and real domain-boundary routing; nested bundle metadata/deduplication/cycles/limits/cancellation; source usage/expiry/theme; keyboard-preserving focus delegate; in-app one-second notices; page/settings history and native Qt mouse side buttons; persisted once-per-release acknowledgement; existing proxy ownership, storage, grouped catalog, refresh progress, crash recovery and connection-switch coverage.

All network integration traffic uses controlled local fixtures. The user's supplied private server was not contacted; test credentials and REALITY keys were generated just for tests. Successful local protocol traffic does not guarantee a production server's reachability or credentials.

The only skipped scenario remains OS process matching: this host denies Xray's netlink interface query. A process-rule configuration is accepted by the core, and sanitized lookup-failure notification is tested. Actual Windows process lookup is not certified.

Native Windows launchers were cross-compiled and inspected: both are x64 GUI PE files with 0.9.0 resources. ShadowBoxHost uses the existing python313.dll in-process; Py_Main is present in the exact pinned bundled DLL. Imports are standard Windows/UCRT libraries, USER32 and SHELL32; no extra Python distribution or third-party native DLL is added. Native Windows startup, Task Manager presentation and the WinINET/DPAPI implementations were not interactively executed here. No signing claim is made.

Final checks caught and fixed a quota-label regression, a refresh-button state/timing issue, and application event-filter/timer cleanup after closing. The final entire suite is green. The prior exploratory failures are not presented as successful validation.

## Historical reports

# Shadow Box 0.8.0 executed validation

160 passed, 2 skipped, 0 failures/errors in 71.38 seconds. Python 3.12, Qt 6.8.3 offscreen and real pinned Xray 26.3.27 on Linux. Authoritative report: test-results-v080.xml.

New checks cover exact .ir/custom suffix boundaries (including negative suffix lookalikes) using real local HTTP servers through Xray with an unavailable proxy upstream, proxy-only verification precedence, disabled exceptions, preserved LAN routes, invalid inputs and bounded lists, explicit Apply/autosave isolation, preference recovery/export, all 14 native Settings categories at compact widths, new EXE picker/editor and unchanged window dimensions. Older cores cannot silently ignore process rules. A fixed warning is emitted once when lookup fails, without exposing raw core errors or private paths.

The full run skipped the managed-core installation check because the local archive had not yet been staged; the archive was then staged and that exact installation/rollback/checksum/cancellation test passed separately (1 passed in 0.76 seconds; test-core-install-v080.xml). The remaining skipped scenario is real process-match traffic because this sandbox denies Xray's netlink interface query (operation not permitted). Process-rule JSON is accepted by the real pinned core; a successful OS process match has NOT been demonstrated here. Windows process lookup, actual Windows 11 execution and system proxy APIs require validation on Windows. No live Windows execution is claimed.

The Windows x64 launcher was cross-compiled, its PE machine type and 0.8.0 version resource verified. This release is a code/assets overlay for modern 0.7.0; Python, Qt, Xray, QR libraries and app data are preserved.

## Historical reports

# Shadow Box 0.7.0 executed validation

131 tests passed in 56.90 seconds; exit code 0. Qt offscreen tests and real local Xray/TLS tests ran on Linux. This includes fresh-result subscription auto-connect, wrong-credential rejection, cancellation, source grouping, progress, copy/edit/delete, hidden-scroll wheel movement, compact home, proxy cleanup and live core replacement. No production site results or actual interactive Windows install run is claimed.

Full reports: `test-results-v070.xml` and `pytest-output-v070.txt`. Installer PE/resource and extraction/payload validation are recorded separately.

## Historical reports

# Shadow Box 0.6.0 validation

**Final executed run: 123 tests passed, exit code 0 (53.09 seconds).**

Authoritative output: `pytest-output-v060.txt` and `test-results-v060.xml`. Tests use Linux x86_64, Python 3.12, native Qt 6.8.3 and real Xray 26.3.27. Windows PE launchers are cross-compiled and inspected, not interactively run here.

The existing suite remains, including real local HTTP/TLS/Xray, ML-KEM preservation, process/crash/final-cancel cleanup, proxy-ownership logic, parsers, protected catalogs, QR/clipboard, quota/log privacy, typed settings and telemetry-free support exports.

New executed scenarios:
- Independent subscription groups, current-group quota and counts, compact two-column UI, group restoration after restart, and unchanged page dimensions.
- Attempted failed tests are persisted and reconciled; TCP refusal and timeout cannot display Not Tested. TCP and HTTPS methods are explicitly distinguished.
- Thirteen nonempty category icons; hidden scrollbar policies with an actual Qt wheel event changing the scroll position.
- Safe autosave while a port draft is pending, disabled autosave, explicit batch staging, and flushing a pending safe change at close.
- Effective automatic tuning differs from stored manual fields; manual mode uses them again.
- Ten service tiles and generation/process rejection of stale results.
- Real local Xray -> HTTPS endpoint HEAD responses: success, 403, 401, 429, redirects, same-endpoint GET-header fallback for 405, real timeout and closed-proxy failure without a direct fallback.
- Real isolated HTTPS profile probe: correct Shadowsocks credentials verify; wrong credentials cannot pass merely because TCP is reachable.
- Real running connection replacement between two local Xray Shadowsocks servers: old child exits, replacement verifies, local listener ports remain valid and manual disconnect cancels pending switching.

The default pytest fixture prevents traffic to the ten public sites; controlled tests explicitly use local HTTPS fixtures. Production-site access, account/media/geographic restrictions and Windows audio are not claimed as tested. Native screenshots include all categories, a sample-labeled grouped catalog and separate 200% Qt renders. Sample results are presentation fixtures, not production connection measurements. Windows recovery/startup/DPAPI tests retain their existing fake adapters and are not live Windows certification.
