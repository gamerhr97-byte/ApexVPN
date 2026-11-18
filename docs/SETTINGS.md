# Settings implementation guide

`settings_schema.py` is the source of truth for all preferences. `Setting` defines the unique key, section, value kind, default, enum/range, permissions, application timing, export policy, advanced grouping and unavailable reason. `validate` rejects an entire invalid change set. `migrate` validates legacy preferences and private metadata without touching the protected profile catalog. `settings-schema.json` is generated documentation, not a second configuration implementation.

`settings_ui.py` renders twelve internal categories from that schema, stages dirty controls, validates atomically and persists via Store. Apply is explicit. Startup registration is a current-user Windows registry action and is confirmed; persistence failure attempts to restore the previous registration. Network changes are rejected while connected and take effect on the next connection. Runtime UI preferences apply immediately after save. Startup and remembered-window options take effect at the next launch/Settings visit. No connection-critical restart is silently triggered.

`settings_runtime.py` owns bounded Smart Connect/reconnect orchestration and refresh scheduling. Engine state is authoritative. HTTPS history is separate from server-list TCP tests. A selected favorite pins the candidate pool. Retry timers are canceled by manual disconnect; a brief connection cannot reset the retry budget. Health checks and subscription scheduling share the application's existing timer and create no idle polling threads.

`settings_services.py` provides fixed-command core validation/install/rollback, protected Telegram records, read-only tools, Windows startup/power integration and whitelist-only support bundles. Core install defaults to verified TLS, a fixed official release and the shipped authoritative digest. It rejects bad checksums before any executable validation. It never interprets user shell commands, extracts arbitrary archive members or updates to an unverified "latest" binary.

Settings operations run in a bounded two-worker executor, with one accepted operation at a time. Cancellation tokens are checked around bounded I/O and before install commit; late results cannot update a closed page or select an installed binary. Existing Settings-triggered subscriptions use a cancellation token checked before UI catalog commit. Downloads and sockets have finite timeouts, but OS hostname resolution and an already-running subprocess cannot be synchronously interrupted by a cancellation token; an in-flight request may finish its bounded operation before the worker exits. No infinite cancellation queue is created. Timers are stopped and pools canceled during application shutdown. Durable proxy restoration stays in the existing guarded engine.

Unsupported controls are schema-disabled and also rejected by validation/import. There is no hidden live backend behind an unavailable toggle. The user-facing release matrix lists missing dependencies rather than claiming untested routing/kill-switch/multi-core capability.

## Build

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python tools/download_dependencies.py --help
python tools/package_windows.py --downloads ../downloads --output ../deliverables-v0.4.0
python tools/package_update.py --output ../deliverables-v0.4.0/NekoRayNext-0.4.0-update.zip --downloads ../downloads
```

The Windows package uses the existing PE x64 GUI launcher, CPython 3.13.9, Qt 6.8.3 and pinned Xray 26.3.27. It bundles the modified Python modules and required licenses. Native screenshots use `tools/screenshot_settings.py` with offscreen Qt; `verify_settings_scope.py` compares protected pages to an extracted 0.3.1 release when available.

Primary reference sources reviewed for release constraints:
- https://github.com/XTLS/Xray-core/releases/tag/v26.3.27
- https://sing-box.sagernet.org/configuration/inbound/tun/
- https://sing-box.sagernet.org/configuration/route/

The existence of capabilities in upstream cores does not mean this frontend has implemented their adapters.
