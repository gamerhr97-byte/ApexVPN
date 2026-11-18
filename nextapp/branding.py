"""Apex VPN identity; storage/lease identifiers deliberately remain compatible."""

from pathlib import Path

APP_NAME = "Apex VPN"
VERSION = "1.11.0"
ASSETS = Path(__file__).resolve().parents[1] / "assets"


def app_icon():
    from PySide6.QtGui import QIcon

    return QIcon(str(ASSETS / "apex-vpn-0.10.7.png"))


def refresh_shell_icons():
    """Notify Explorer about owned updated files; never delete the user's cache."""
    import os
    if os.name!='nt':return
    import ctypes
    try:
        shell=ctypes.WinDLL('shell32');notify=shell.SHChangeNotify
        notify.argtypes=[ctypes.c_long,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p];notify.restype=None
        for relative in ('ApexVPN-0.10.7.exe','ApexVPN.exe','ShadowBox.exe','NekoRayNext.exe','runtime/ApexVPNHost.exe'):
            path=ASSETS.parent/relative
            if path.is_file():
                text=ctypes.create_unicode_buffer(str(path));notify(0x2000,0x0005,ctypes.cast(text,ctypes.c_void_p),None)
    except (OSError,AttributeError):pass
