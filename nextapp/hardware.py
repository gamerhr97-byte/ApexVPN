"""Read-only hardware detection, with unknown results rather than guesses."""
import ctypes,os,platform,pathlib

def inspect(root):
    info={'OS':platform.platform(),'Logical CPUs':str(os.cpu_count() or 'Unknown'),'CPU':platform.processor() or 'Unknown','RAM':'Unknown','GPU':'Unknown','Storage':'Unknown'}
    if os.name!='nt':
        try:info['RAM']=f'{os.sysconf("SC_PAGE_SIZE")*os.sysconf("SC_PHYS_PAGES")/1024**3:.1f} GiB'
        except (ValueError,OSError):pass
        return info
    from ctypes import wintypes as w
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:info['CPU']=winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
    except OSError:pass
    class Memory(ctypes.Structure):
        _fields_=[('length',w.DWORD),('load',w.DWORD)]+[(n,ctypes.c_ulonglong) for n in ('physical','available','pagefile','available_pagefile','virtual','available_virtual','extended')]
    mem=Memory();mem.length=ctypes.sizeof(mem)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):info['RAM']=f'{mem.physical/1024**3:.1f} GiB'
    class Display(ctypes.Structure):
        _fields_=[('size',w.DWORD),('name',w.WCHAR*32),('description',w.WCHAR*128),('flags',w.DWORD),('id',w.WCHAR*128),('key',w.WCHAR*128)]
    devices=[]
    for i in range(32):
        dev=Display();dev.size=ctypes.sizeof(dev)
        if not ctypes.windll.user32.EnumDisplayDevicesW(None,i,ctypes.byref(dev),0):break
        if dev.flags&1:devices.append(dev.description)
    if devices:info['GPU']='; '.join(devices)
    drive=pathlib.Path(root).resolve().drive
    if not drive or len(drive)!=2:return info
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE];kernel.CreateFileW.restype=w.HANDLE
    kernel.DeviceIoControl.argtypes=[w.HANDLE,w.DWORD,ctypes.c_void_p,w.DWORD,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD),ctypes.c_void_p];kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.CreateFileW('\\\\.\\'+drive,0,3,None,3,0,None)
    if handle==ctypes.c_void_p(-1).value:return info
    class Query(ctypes.Structure):_fields_=[('property',w.DWORD),('type',w.DWORD),('extra',ctypes.c_ubyte*4)]
    class Seek(ctypes.Structure):_fields_=[('version',w.DWORD),('size',w.DWORD),('penalty',ctypes.c_ubyte)]
    try:
        query=Query();query.property=7;result=Seek();returned=w.DWORD()
        if kernel.DeviceIoControl(handle,0x2D1400,ctypes.byref(query),ctypes.sizeof(query),ctypes.byref(result),ctypes.sizeof(result),ctypes.byref(returned),None):
            info['Storage']='Seeking media (typically HDD)' if result.penalty else 'Non-seeking media (typically SSD; device-reported)'
    finally:kernel.CloseHandle(handle)
    return info
