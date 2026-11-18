# Apex VPN installer and upgrades

Run ApexVPN-0.10.7-Setup-x64.exe. This is a complete offline NSIS installation for Windows x64, not a portable ZIP or launcher-only EXE. The same installer performs an in-place upgrade of an existing installed copy. Close the app/tray first: Setup and launcher share the Local\ShadowBoxDesktop mutex.

Existing install registration Software\ShadowBox and install directory are preserved for upgrades. Default location: %LOCALAPPDATA%\Programs\ShadowBox. The display/shortcut brand is Apex VPN. Profiles/settings remain at %LOCALAPPDATA%\NekoRayNext; uninstall preserves that directory. The generated uninstall manifest removes only owned packaged files. No recursive wipe of the data root is used. No global Python/Qt, driver, firewall change, or admin rights are needed for the default user installation.

Portable migration: first close both apps, back up portable data, then copy the contents of the old data folder into %LOCALAPPDATA%\NekoRayNext only if that does not overwrite a newer catalog. No attempt is made to search arbitrary user folders.

Build: python tools/build_launcher.py then python tools/build_installer.py --payload <complete reviewed app directory> --output <folder> --makensis <NSIS compiler>. The builder excludes portable.flag and user data; writes installed.flag; installs a native host with its ._pth; verifies required runtimes; generates exact uninstall paths. A new version is delivered by one newer Setup EXE, not an overlay ZIP.

Build platform: Linux, NSIS 3.09 from official Ubuntu packages. The setup loader is PE32; the application, Python, Qt and cores are x64. Setup rejects unsupported OS and non-AMD64 machines. Actual Windows installation/reinstallation, shortcut refresh, native caption move/resize and DPAPI require Windows testing. This build is unsigned.
