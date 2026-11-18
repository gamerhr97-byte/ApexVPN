"""NekoRay Next desktop entrypoint; no administrator privileges required."""

import os, pathlib, sys, time

BASE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))


def main():
    began=time.monotonic()
    # Guardian uses only stdlib plus proxy/storage and does not load Qt.
    if len(sys.argv) == 4 and sys.argv[1] == "--guard":
        from nextapp.guardian import run

        run(int(sys.argv[2]), sys.argv[3])
        return 0
    if os.name == "nt":
        import ctypes

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "ApexVPN.Desktop"
            )
        except OSError:
            pass
    ready_name = os.environ.pop("SHADOW_BOX_READY_EVENT", "")

    def ready():
        if os.name == "nt" and ready_name:
            import ctypes
            from ctypes import wintypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenEventW.argtypes = [
                wintypes.DWORD,
                wintypes.BOOL,
                wintypes.LPCWSTR,
            ]
            kernel.OpenEventW.restype = wintypes.HANDLE
            kernel.SetEvent.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenEventW(2, False, ready_name)
            if handle:
                kernel.SetEvent(handle)
                kernel.CloseHandle(handle)

    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)
    from nextapp.focus_style import CleanFocusStyle
    app.setStyle(CleanFocusStyle(app.style()))
    app.setApplicationName("Apex VPN")
    app.setOrganizationName("NekoRayNext")
    app.setQuitOnLastWindowClosed(False)
    from nextapp.branding import app_icon

    app.setWindowIcon(app_icon())
    from nextapp.branding import refresh_shell_icons
    refresh_shell_icons()
    root = pathlib.Path(
        os.environ.get(
            "NEKORAY_NEXT_DATA",
            (
                str(BASE / "data")
                if (BASE / "portable.flag").exists()
                else str(
                    pathlib.Path(
                        os.environ.get(
                            "LOCALAPPDATA", str(pathlib.Path.home() / ".local/share")
                        )
                    )
                    / "NekoRayNext"
                )
            ),
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(root / "instance.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        ready()
        QMessageBox.information(
            None, "Apex VPN", "Another instance is already using this data directory."
        )
        return 1
    try:
        from nextapp.startup import ProgressChannel,run_checks,source_splash
        channel=ProgressChannel();splash=None
        if not ready_name:
            splash=source_splash();splash.show();app.processEvents()
        def progress(percent,label):
            channel.report(percent,label)
            if splash:splash.report(percent,label)
        checks=run_checks(root,progress)
        from nextapp.ui import Window
        window = Window(root)
        window.startup_checks=checks
        progress(95,'Ready')
        def show_ready():
            if window.settings["start_tray"]:window.to_tray()
            elif window.settings["start_minimized"]:window.showMinimized()
            else:window.show()
            progress(100,'Ready')
            if splash:splash.close()
            channel.close();ready()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(max(0,round((1.-(time.monotonic()-began))*1000)),show_ready)
        code=app.exec()
        from PySide6.QtCore import QEvent
        app.sendPostedEvents(None,QEvent.DeferredDelete)
        return code
    except Exception:
        ready()
        QMessageBox.critical(
            None,
            "Apex VPN",
            "Startup failed. Reinstall with the latest Setup EXE and check that the user data folder is writable. Your profiles were not overwritten. See README for dependencies and recovery.",
        )
        return 1
    finally:
        lock.unlock()


if __name__ == "__main__":
    sys.exit(main())
