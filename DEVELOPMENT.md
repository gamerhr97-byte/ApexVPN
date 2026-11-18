> Current: Apex VPN 1.11.0. Start with NEXT_AI_HANDOFF_FA.md. This complete source bundle includes Windows runtime binaries, both core platforms, updated native launchers and the small updater artifact; historical build notes below may be stale.

> Current: Apex VPN 0.10.5. Read README-0.10.5-FA.md and docs/VALIDATION-0.10.5-FA.md. Older sections are historical.

> Current release: Apex VPN 0.10.4. Read README-0.10.4-FA.md and docs/VALIDATION-0.10.4-FA.md first. Older sections below are historical.

# Development and reproducible packaging

These instructions describe the included **0.10.0 source**, not a newly verified Windows installation. Work from this folder, where app.py and requirements-dev.txt reside. Third-party binary inputs are not embedded in the source ZIP.

## 1. Prepare a development environment

Use Python 3.12 for the historically exercised Linux test setup, or a suitable Windows development Python. The shipped Windows runtime is pinned separately to Python 3.13.9. Create a virtual environment and install the exact requirements:

```bash
python -m venv .venv
# Activate .venv using the command appropriate to your shell.
python -m pip install -r requirements-dev.txt
python tools/download_dependencies.py --destination ../downloads
```

Linux Qt may require the normal system GUI libraries and an offscreen-capable plugin. The local TLS integration fixtures require the `openssl` executable. A bare Windows machine does not automatically provide that test dependency. Do not treat a Linux test result as execution of WinINET/DPAPI.

The download script verifies all configured SHA-256 values. Keep failed checks as failures; do not bypass the lockfile to force a build. Initial dependency acquisition needs network access. The assembled user distribution can then run offline without installing Python/Qt separately.

## 2. Stage the pinned development core

The download script downloads archives; it does not place the runtime core at `core/xray` or `core/xray.exe`. From this project root, use the verified archive to stage just the executable:

```python
# Save/run this snippet locally with Python after the pinned download step.
import os
from pathlib import Path
import zipfile

name = 'xray.exe' if os.name == 'nt' else 'xray'
archive = 'Xray-windows-64.zip' if os.name == 'nt' else 'Xray-linux-64.zip'
target = Path('core') / name
target.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(Path('../downloads') / archive) as bundle:
    target.write_bytes(bundle.read(name))
if os.name != 'nt':
    target.chmod(0o755)
```

Some fixtures expect the Linux archive at **../downloads/Xray-linux-64.zip**. Several transport tests require a real core rather than skipping gracefully when it is missing. Prepare the dependency explicitly before interpreting failures.

## 3. Launch without touching the owner's data

app.py supports the **NEKORAY_NEXT_DATA** environment variable, not a documented `--data-dir` flag. Use a new local folder for development:

Linux/macOS-style shell (UI/backend operations are still platform-dependent):

```bash
NEKORAY_NEXT_DATA="$PWD/dev-data" python app.py
```

Windows PowerShell:

```powershell
$env:NEKORAY_NEXT_DATA = Join-Path (Get-Location) 'dev-data'
python app.py
```

Do not copy personal profiles/subscriptions into a source archive. System Proxy can change the current user's Windows proxy after a verified connection; use Manual Proxy for tests that do not require integration. Installed user data normally lives in %LOCALAPPDATA%/NekoRayNext; portable.flag selects a data folder beside the packaged app.

## 4. Tests

After staging the core and installing OpenSSL/system Qt requirements:

```bash
# Set QT_QPA_PLATFORM=offscreen in your shell when using a headless environment.
python -m pytest -q
python -m pytest -q tests/test_v0100.py tests/test_direct_routing.py
```

Tests use local generated TLS/REALITY fixtures. conftest.py prevents unintended public service-tile probes. Keep the same isolation for new tests. A process-lookup test may be skipped when the host denies netlink; report that accurately.

Historical evidence is in docs/test-results-v0100.xml and docs/test-v0100-focused.xml. No runtime tests were rerun solely to add these handoff documents. Verify the actual new environment rather than promising the historical counts repeat everywhere.

## 5. Build current native entry points and an update overlay

From an activated environment with the pinned requirements:

```bash
python tools/build_launcher.py
python tools/package_update.py --code-only --output ../out/ShadowBox-0.10.0-update.zip --downloads ../downloads
```

The launcher builder compiles both tools/ShadowBox.exe and tools/ShadowBoxHost.exe, and creates icon resources. The update ZIP includes root launchers plus runtime/ShadowBoxHost.exe and runtime/ShadowBoxHost._pth. Existing Python/Qt/Xray/data are preserved. `--code-only` is suitable for an existing modern base with the QR runtime already present; it is **not a standalone installer**.

For a non-code-only overlay, provide all pinned QR wheels at --downloads. Inspect the archive rather than assuming a changed output filename updated all hardcoded version references.

## 6. Full portable payload

```bash
python tools/package_windows.py --downloads ../downloads --output ../out
```

The included builder stages the runtime/core/assets and native host. Its output archive is still named **ShadowBox-0.6.0-windows-x64-portable.zip** in source. This is a known stale filename, not the actual current application version. Fix the naming for a new release and verify the payload, native startup and app-local dependencies on Windows before distributing it.

## 7. Full NSIS installer — audit first

The existing CLI is:

```bash
python tools/build_installer.py --downloads ../downloads --output ../out --makensis /path/to/makensis
```

**Do not use that command as proof of a valid current installer.** The script/NSIS metadata still target 0.7.0 and the staging code omits runtime/ShadowBoxHost.exe and its ._pth even though the current launcher requires them. Before shipping:

1. Stage the host and isolated search-path file alongside the pinned Python DLL.
2. Update application/setup/resource/output/documentation versions consistently.
3. Regenerate uninstall-files.nsh from the actual final payload.
4. Extract/inspect the installer; verify all expected files and dependency hashes.
5. Test a real Windows 11 clean install, upgrade with existing data, normal/forced-exit recovery and uninstall.

NSIS (`makensis`) must be installed on the build machine. Linux builds using an extracted NSIS tree may need NSISDIR set. Those build tools are not end-user prerequisites.

## 8. Signing and licensing

The project is unsigned. No certificate, private key, hardware token or service account is included. tools/sign_release.py requires Windows, an existing certificate-store identity and Windows SDK SignTool; it verifies its signed output. Running it with --help does not perform signing. Do not generate/install a fake trusted root as a workaround.

Keep LICENSE, THIRD_PARTY_NOTICES.md, licenses/ and pinned dependency licensing when distributing. The project license file is GPL-3.0; third-party components keep their own notices. This handoff does not change licenses.
