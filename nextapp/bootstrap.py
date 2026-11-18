"""One-time local hardware defaults, never downloads or modifies OS protection."""

import ctypes
import os


def hardware_defaults(settings):
    result = dict(settings)
    if result.get("hardware_tuned"):
        return result, False
    ram = None
    if os.name == "nt":

        class Memory(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong)
                for name in (
                    "physical",
                    "available",
                    "pagefile",
                    "available_pagefile",
                    "virtual",
                    "available_virtual",
                    "extended",
                )
            ]

        memory = Memory()
        memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            ram = memory.physical
    constrained = (os.cpu_count() or 2) <= 2 or ram is not None and ram < 4 * 1024**3
    if constrained:
        result.update(lightweight=True, visual_effects=False, reduced_motion=True)
    result["hardware_tuned"] = True
    return result, True
