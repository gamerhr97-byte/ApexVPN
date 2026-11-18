"""Opt into EcoQoS only while Apex is hidden and completely idle."""

import ctypes
import os


class _PowerThrottlingState(ctypes.Structure):
    _fields_ = [('Version', ctypes.c_ulong), ('ControlMask', ctypes.c_ulong),
                ('StateMask', ctypes.c_ulong)]


def set_idle_efficiency(enabled):
    """Request EcoQoS for this UI process; Windows resets it when the process exits."""
    if os.name != 'nt':
        return False
    try:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        call = kernel.SetProcessInformation
        call.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
        call.restype = ctypes.c_int
        state = _PowerThrottlingState(1, 1 if enabled else 0, 1 if enabled else 0)
        current_process = ctypes.c_void_p(-1)
        return bool(call(current_process, 4, ctypes.byref(state), ctypes.sizeof(state)))
    except (AttributeError, OSError, TypeError, ValueError):
        return False
