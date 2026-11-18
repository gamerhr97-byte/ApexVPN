# Required Windows validation before a production release

These are outstanding tests, not completed results. Use an isolated Windows 11
x64 machine or VM before relying on System Proxy mode on your daily computer.

1. Extract the portable folder; launch without administrator elevation. Validate
   VC runtime/Qt plugin loading, Unicode installation paths, long paths, writable
   and non-writable folders, and optional source execution. Check no console pops up.
2. Test 100%, 125%, 150%, 200% display scaling, mixed DPI monitors, snapping,
   Persian RTL, English, dark/light themes, tray and shortcuts.
3. In Manual Proxy mode use test profiles for VLESS/REALITY/Vision/Chrome and the
   exact ML-KEM encryption scheme supplied privately by the user. Verify HTTP,
   HTTPS, certificate validation, upload/download counters and error states.
4. Validate DPAPI roundtrip, a second account failing to decrypt, local backup
   recovery and no secret values in diagnostic exports or process command lines.
5. Save the actual WinINET LAN snapshot with proxy disabled, enabled, PAC URL,
   autodetect, existing bypass list and existing corporate proxy cases. Validate
   enabling and disconnecting restores every field exactly. Verify WinHTTP unchanged.
6. Change Windows proxy settings concurrently while connected. Disconnect must
   preserve the other program's changes, display a warning and retain its backup.
7. Force-end the GUI process, then the launcher; separately kill the core.
   Check owned core termination and guardian restoration. Kill both watcher and
   GUI and test next-launch visible recovery. Reboot with a saved recovery lease.
8. Deny settings writes/notification calls and inject failure during startup,
   core validation, endpoint testing, proxy apply and restoration. Confirm clear
   errors, no duplicate core, no false Connected state, and retained recoverable data.
9. Test missing dependencies, malformed links, unknown fields, unsupported
   encryption, wrong authentication, DNS errors, TLS errors and occupied ports.
10. Cancel bulk tests; disconnect/reconnect during startup; disconnect the network
    and restore it. Ensure no silent profile switching or proxy-off reset.
11. Apply the performance targets and measurement protocol in PERFORMANCE.md.

TUN is disabled and must have its own implementation, consent flow, route/DNS
recovery design and end-to-end Windows tests before it can be enabled.

## 0.4.0 Settings acceptance (not executed in this Linux environment)

- Apply / reset / import/export preferences, restart, inspect all twelve categories in Persian and English at 100–200% display scaling.
- Real current-user Run-key enable/disable, spaces in executable paths, moved installations and outside-owned startup entry refusal.
- Real DPAPI profile/subscription/Telegram encryption, invalid protected file preservation, same-account recovery.
- Real WinINET backup, HTTPS-before-enable, disconnect, GUI kill, crash guardian and external proxy ownership conflict. No WinHTTP changes.
- Actual Windows core download with TLS, pinned release digest match, rollback, install lock/antivirus denial and offline/canceled download behavior. Never disable antivirus/firewall.
- Smart Connect with real authorized compatible profiles; failed auth/unsupported encryption must not count as success. Verify retries stop after explicit Disconnect and the configured budget, including short repeated sessions.
- Provider-supplied subscription metadata, scheduled refresh/backoff and cancellation when leaving Settings. Confirm active subscription refresh is excluded.
- Installed Telegram handler handoff only after warning, SOCKS/MTProto format failures, masked credentials, removal and failed-save preservation.
- Tray unavailable fallback, explicit Quit versus minimize-to-tray, tooltip/profile-action states, battery-aware checks and pending networking preferences.
- Confirm TUN, process split, kill switch, seamless and non-Xray adapters cannot be activated/imported. There is no driver/firewall backend to certify.

## 0.5.0 Shadow Box platform acceptance (not executed on Linux)

- Launch ShadowBox.exe and its compatibility alias after a full extraction; check the native icon in Explorer, window, tray and taskbar.
- Update over the previous portable folder without changing `data`; verify saved profiles/subscriptions and proxy recovery still work under the renamed application.
- Listen to click/connected/disconnected/error cues, test mute and check that a real verified connection controls the connected cue. Test a machine with no audio output device; playback failure must not affect networking.
- Navigate all thirteen Settings categories at Windows 100–200% scaling; opening/closing Settings must not resize the current window. Check keyboard Enter, hamburger return, Persian RTL and reduced motion.
- Check an authorized provider returning complete Subscription-Userinfo data, missing/unlimited data and usage beyond quota. Compare displayed percentage to the supplied header snapshot.
- Verify log search/filter/copy/export never exposes secrets, raw core output or configuration/subscription URLs.
