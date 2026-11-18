"""Stdlib-only crash watcher; waits on a Windows process handle, no polling."""
import ctypes,os,pathlib
from .proxy import ProxyLease

def run(pid,root):
    if os.name!='nt':return
    from ctypes import wintypes as w
    k=ctypes.WinDLL('kernel32');k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.CloseHandle.argtypes=[w.HANDLE]
    handle=k.OpenProcess(0x00100000,False,pid)
    ready=pathlib.Path(root)/'guardian.ready';ready.write_text(str(os.getpid()))
    if handle:k.WaitForSingleObject(handle,0xFFFFFFFF);k.CloseHandle(handle)
    try:ProxyLease(root).restore()
    except Exception:pass # Keep durable backup for the visible recovery action.
    ready.unlink(missing_ok=True)
