"""WinINET per-user LAN settings; ownership checked before every restoration.
No WinHTTP changes, driver installs, firewall changes, or forced proxy-off operation.
"""
import ctypes, json, os, pathlib
from .storage import protect, atomic_write

class ProxyError(RuntimeError): pass
class WinInet:
    def __init__(self):
        if os.name!='nt': raise ProxyError('System Proxy is available on Windows only. Use Manual Proxy mode here.')
        from ctypes import wintypes as w
        class Value(ctypes.Union): _fields_=[('number',w.DWORD),('text',ctypes.c_void_p),('time',w.FILETIME)]
        class Option(ctypes.Structure): _fields_=[('option',w.DWORD),('value',Value)]
        class Options(ctypes.Structure): _fields_=[('size',w.DWORD),('connection',w.LPWSTR),('count',w.DWORD),('error',w.DWORD),('options',ctypes.POINTER(Option))]
        self.Option,self.Options=Option,Options
        self.api=ctypes.WinDLL('wininet',use_last_error=True)
        self.api.InternetQueryOptionW.argtypes=[ctypes.c_void_p,w.DWORD,ctypes.c_void_p,ctypes.POINTER(w.DWORD)]
        self.api.InternetSetOptionW.argtypes=[ctypes.c_void_p,w.DWORD,ctypes.c_void_p,w.DWORD]
        self.api.InternetSetOptionW.restype=self.api.InternetQueryOptionW.restype=w.BOOL
        self.free=ctypes.WinDLL('kernel32').GlobalFree; self.free.argtypes=[ctypes.c_void_p]; self.free.restype=ctypes.c_void_p
    def read(self):
        opts=(self.Option*4)()
        for o,key in zip(opts,(1,2,3,4)): o.option=key
        obj=self.Options(ctypes.sizeof(self.Options),None,4,0,opts); size=ctypes.c_ulong(ctypes.sizeof(obj))
        if not self.api.InternetQueryOptionW(None,75,ctypes.byref(obj),ctypes.byref(size)): raise ProxyError('Could not read Windows proxy settings.')
        result={'flags':int(opts[0].value.number)}
        for i,key in enumerate(('server','bypass','auto_url'),1):
            ptr=opts[i].value.text
            result[key]=ctypes.wstring_at(ptr) if ptr else ''
            if ptr: self.free(ptr)
        return result
    def write(self, values):
        opts=(self.Option*4)(); keep=[]
        opts[0].option=1; opts[0].value.number=values['flags']
        for i,key in enumerate(('server','bypass','auto_url'),1):
            buf=ctypes.create_unicode_buffer(values[key]); keep.append(buf)
            opts[i].option=i+1; opts[i].value.text=ctypes.cast(buf,ctypes.c_void_p)
        obj=self.Options(ctypes.sizeof(self.Options),None,4,0,opts)
        if not self.api.InternetSetOptionW(None,75,ctypes.byref(obj),ctypes.sizeof(obj)): raise ProxyError('Windows refused the proxy settings change. Recovery backup retained.')
        # Notify clients after changing the default per-connection settings.
        if not self.api.InternetSetOptionW(None,39,None,0) or not self.api.InternetSetOptionW(None,37,None,0):
            raise ProxyError('Settings changed, but Windows notification failed. Use Restore Previous Windows Proxy Settings.')

class ProxyLease:
    def __init__(self, root, adapter=None):
        self.path=pathlib.Path(root)/'proxy-recovery.dat'; self.adapter=adapter
    def api(self):
        if self.adapter is None: self.adapter=WinInet()
        return self.adapter
    def load(self): return json.loads(protect(self.path.read_bytes(),True))
    def enable(self, port, bypass="<local>"):
        if self.path.exists(): raise ProxyError('A proxy recovery backup already exists. Restore or review it before connecting.')
        if not isinstance(bypass,str) or len(bypass)>16384 or any(c in bypass for c in '\r\n\x00'):raise ProxyError('Invalid Windows bypass list.')
        api=self.api(); before=api.read()
        expected={'flags':3,'server':f'http=127.0.0.1:{port};https=127.0.0.1:{port}','bypass':bypass,'auto_url':''}
        atomic_write(self.path,protect(json.dumps({'before':before,'applied':expected}).encode()))
        api.write(expected)
        if api.read()!=expected: raise ProxyError('Windows proxy verification failed. Recovery backup retained.')
    def restore(self):
        if not self.path.exists(): return 'No pending proxy backup.'
        data=self.load(); api=self.api(); current=api.read()
        if current==data['before']:
            self.path.unlink(); return 'Previous Windows proxy settings are already restored.'
        if current!=data['applied']:
            raise ProxyError('Proxy settings were changed by another application or the user. Nothing was overwritten; the recovery backup is retained for review.')
        api.write(data['before'])
        if api.read()!=data['before']: raise ProxyError('Windows could not verify restoration. Recovery backup retained.')
        self.path.unlink(); return 'Previous Windows proxy settings restored.'
