# Shadow Box 0.7.0 installer build

Use `tools/build_launcher.py`, then `tools/build_installer.py --downloads ../downloads --output ../deliverables-v0.7.0`. See `docs/INSTALLER.md` for offline setup, NSIS, platform checks and preserved data. Run `python -m pytest -q` before packaging.

## Historical 0.6 portable build

# Shadow Box build

```sh
python -m pip install -r requirements-dev.txt
python tools/download_dependencies.py --destination ../downloads
python tools/create_sounds.py
QT_QPA_PLATFORM=offscreen python tools/build_launcher.py
python tools/package_windows.py --downloads ../downloads --output ../deliverables-v0.6.0
python tools/package_update.py --downloads ../downloads --output ../deliverables-v0.6.0/ShadowBox-0.6.0-update.zip
```

Before running `python -m pytest -q`, extract only the verified platform executable from `../downloads/Xray-linux-64.zip` to `core/xray` (make it executable on Linux), or from `Xray-windows-64.zip` to `core/xray.exe` on Windows. The source ZIP does not include a core binary; the download helper checks the pinned archive digest before use. The tests require that real core.

The icon is an original code-native SVG; `build_launcher.py` renders it through Qt to PNG/ICO and invokes pinned Zig 0.13.0 RC/CC to compile the Windows icon/version resources into the x64 GUI launcher. It requires the development dependencies; users receive the compiled binary. `create_sounds.py` synthesizes the four original quiet PCM WAV assets locally, with no downloaded audio or licensing dependency.

Pinned Windows CPython/Qt/Xray/QR artifacts and their digests are unchanged. `tools/download_dependencies.py` fetches the pinned base runtime; the two pinned QR wheels are listed in `dependencies.lock.json` and required by packaging. Packaging verifies all expected hashes. Never skip a mismatched hash.

The update contains the modified application/assets plus the branded primary/compatibility launchers and existing pinned QR runtime overlay. It does not copy data, replace Python/Qt or install a core/driver. The full package contains the compatible `NekoRayNext` folder, both launcher names and complete pinned runtime.

Screenshots: `QT_QPA_PLATFORM=offscreen python tools/screenshot_shadow.py`. `tools/verify_shadow_layout.py --baseline /path/to/extracted/0.4.0/source` compares the dashboard widget geometry. The older `verify_settings_scope.py` documents the 0.4.0 visual audit and is not the 0.6.0 geometry audit.

For current screenshots run `tools/screenshot_v060.py`. Public service endpoint probes are disabled by default inside pytest and explicitly exercised against local TLS/Xray fixtures.
