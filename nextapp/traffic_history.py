"""Observed traffic only: minute buckets, rolling windows, app-session totals.

No historical data is invented for periods when the application was not running.
System counters include LAN traffic on the chosen default-route adapter. VPN
counters are separate, never added to system counters (which would double count).
"""
import os, sqlite3, time
from pathlib import Path

WINDOWS=(('12h',12*3600),('24h',24*3600),('7d',7*86400),('30d',30*86400),('365d',365*86400))

class TrafficHistory:
    def __init__(self,root,clock=time.time):
        self.clock=clock;self.started=clock();self.last={};self.session={'system':[0,0],'vpn':[0,0]}
        self.observed=set();self.pending={};self.closed=False
        path=Path(root)/'traffic-usage.sqlite';path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,timeout=2)
        try:path.chmod(0o600)
        except OSError:pass
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=NORMAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS usage (minute INTEGER,scope TEXT,upload INTEGER,download INTEGER,PRIMARY KEY(minute,scope))')
        self.db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT)')
        self.db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)',('tracking_started',str(self.started)))
        self.db.execute('DELETE FROM usage WHERE minute < ?', (int((self.started-400*86400)//60),));self.db.commit()
        self.last_flush=self.started

    def observe(self,scope,identity,upload,download,now=None):
        if self.closed or scope not in self.session:return
        now=self.clock() if now is None else now
        if any(type(v) is not int or v<0 or v>2**63-1 for v in (upload,download)):return
        previous=self.last.get(scope);self.last[scope]=(identity,upload,download,now);self.observed.add(scope)
        if previous is None or previous[0]!=identity:
            # NIC counters began at OS boot; do not count them retroactively.
            du,dd=(upload,download) if scope=='vpn' else (0,0)
        elif upload<previous[1] or download<previous[2] or now<previous[3]:du,dd=0,0
        else:du,dd=upload-previous[1],download-previous[2]
        self.session[scope][0]+=du;self.session[scope][1]+=dd
        bucket=(int(now//60),scope);entry=self.pending.setdefault(bucket,[0,0]);entry[0]+=du;entry[1]+=dd
        if now-self.last_flush>=60:self.flush(now)

    def unavailable(self,scope):
        # On a gap, start a new baseline rather than attribute unknown traffic.
        self.last.pop(scope,None)

    def flush(self,now=None):
        if self.closed:return
        with self.db:
            for (minute,scope),(up,down) in self.pending.items():
                self.db.execute('INSERT INTO usage VALUES (?,?,?,?) ON CONFLICT(minute,scope) DO UPDATE SET upload=upload+excluded.upload,download=download+excluded.download',(minute,scope,up,down))
        self.pending.clear();self.last_flush=self.clock() if now is None else now

    def report(self,scope,now=None):
        now=self.clock() if now is None else now
        result={}
        for key,seconds in WINDOWS:
            start=int((now-seconds)//60)
            up,down=self.db.execute('SELECT COALESCE(SUM(upload),0),COALESCE(SUM(download),0) FROM usage WHERE scope=? AND minute>=? AND minute<=?',(scope,start,int(now//60))).fetchone()
            for (minute,name),(u,d) in self.pending.items():
                if name==scope and start<=minute<=int(now//60):up+=u;down+=d
            result[key]={'upload':up,'download':down,'total':up+down}
        u,d=self.session[scope];result['session']={'upload':u,'download':d,'total':u+d}
        result['tracking_started']=float(self.db.execute('SELECT value FROM metadata WHERE key=?',('tracking_started',)).fetchone()[0])
        result['observed']=scope in self.observed or bool(self.db.execute('SELECT 1 FROM usage WHERE scope=? LIMIT 1',(scope,)).fetchone())
        return result

    def close(self):
        if not self.closed:self.flush();self.db.close();self.closed=True


def system_counters():
    """Default-route interface, no packets sent, no new third-party dependency."""
    if os.name=='nt':return _windows_counters()
    routes=Path('/proc/net/route').read_text().splitlines()[1:]
    default=next(line.split()[0] for line in routes if line.split()[1]=='00000000' and int(line.split()[3],16)&1)
    root=Path('/sys/class/net')/default/'statistics'
    return default,default,int((root/'tx_bytes').read_text()),int((root/'rx_bytes').read_text())


def _windows_counters():
    import ctypes as C
    u32=C.c_uint32;u64=C.c_uint64
    class GUID(C.Structure):_fields_=[('a',u32),('b',C.c_uint16),('c',C.c_uint16),('d',C.c_ubyte*8)]
    class Row(C.Structure):
        _fields_=[('luid',u64),('index',u32),('guid',GUID),('alias',C.c_wchar*257),('description',C.c_wchar*257),('addressLength',u32),('physical',C.c_ubyte*32),('permanent',C.c_ubyte*32)]+[(n,u32) for n in ('mtu','type','tunnel','media','physicalMedium','access','direction')]+[('flags',C.c_ubyte)]+[(n,u32) for n in ('oper','admin','mediaState')]+[('networkGuid',GUID),('connectionType',u32)]+[(n,u64) for n in ('txSpeed','rxSpeed','inOctets','inUcast','inNUcast','inDiscards','inErrors','inUnknown','inUcastOctets','inMulticastOctets','inBroadcastOctets','outOctets','outUcast','outNUcast','outDiscards','outErrors','outUcastOctets','outMulticastOctets','outBroadcastOctets','outQLen')]
    if C.sizeof(Row)!=1352 or Row.inOctets.offset!=1208 or Row.outOctets.offset!=1280:raise OSError('Unsupported Windows counter layout')
    lib=C.WinDLL('iphlpapi');index=u32()
    lib.GetBestInterface.argtypes=[u32,C.POINTER(u32)];lib.GetBestInterface.restype=u32
    error=lib.GetBestInterface(0x01010101,C.byref(index))
    if error:
        # IPv6-only default route fallback, still no network request.
        import socket
        class Address(C.Structure):_fields_=[('family',C.c_uint16),('port',C.c_uint16),('flow',u32),('address',C.c_ubyte*16),('scope',u32)]
        address=Address();address.family=23;address.address[:]=socket.inet_pton(socket.AF_INET6,'2606:4700:4700::1111')
        lib.GetBestInterfaceEx.argtypes=[C.c_void_p,C.POINTER(u32)];lib.GetBestInterfaceEx.restype=u32
        if lib.GetBestInterfaceEx(C.byref(address),C.byref(index)):raise OSError('No default interface')
    row=Row();row.index=index.value
    lib.GetIfEntry2.argtypes=[C.POINTER(Row)];lib.GetIfEntry2.restype=u32
    if lib.GetIfEntry2(C.byref(row)) or row.oper!=1:raise OSError('Interface counters unavailable')
    return str(row.luid),row.alias,int(row.outOctets),int(row.inOctets)
