"""Settings-only services. Explicit actions, bounded I/O and whitelist-only exports."""
from __future__ import annotations
import datetime, hashlib, ipaddress, json, os, pathlib, platform, re, shutil, socket, subprocess, tempfile, threading, time, urllib.request, urllib.parse, uuid, zipfile
from dataclasses import dataclass, asdict
from .storage import atomic_write,protect
from .engine import HIDDEN,safe_error
from .network import tcp_latency,proxy_probe,proxy_public_ip,proxy_country

from .branding import VERSION

class Cancelled(Exception):pass

def check_cancel(cancel):
    if cancel.is_set():raise Cancelled()

def startup_command():
    import sys
    return subprocess.list2cmdline([str(pathlib.Path(sys.executable).resolve()),str(pathlib.Path(__file__).resolve().parents[1]/'app.py')])

def set_startup(enabled):
    if os.name!='nt':
        if enabled:raise OSError('Startup registration requires Windows.')
        return
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled:winreg.SetValueEx(key,'NekoRayNext',0,winreg.REG_SZ,startup_command())
        else:
            try:
                value,_=winreg.QueryValueEx(key,'NekoRayNext')
                if value!=startup_command():raise OSError('Startup entry is owned by another installation; left unchanged.')
                winreg.DeleteValue(key,'NekoRayNext')
            except FileNotFoundError:pass

def on_battery():
    if os.name!='nt':return False
    import ctypes
    class Power(ctypes.Structure):
        _fields_=[('ac',ctypes.c_ubyte),('flag',ctypes.c_ubyte),('percent',ctypes.c_ubyte),('reserved',ctypes.c_ubyte),('life',ctypes.c_ulong),('full',ctypes.c_ulong)]
    info=Power()
    return bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(info))) and info.ac==0

@dataclass
class TelegramProxy:
    kind:str
    server:str
    port:int
    secret:str=''
    user:str=''
    password:str=''
    id:str=''
    def link(self):
        q={'server':self.server,'port':str(self.port)}
        if self.kind=='MTProto':q['secret']=self.secret
        elif self.user or self.password:q.update(user=self.user,pass_=self.password)
        q={('pass' if k=='pass_' else k):v for k,v in q.items()}
        return 'tg://'+('proxy' if self.kind=='MTProto' else 'socks')+'?'+urllib.parse.urlencode(q)

def parse_telegram(text):
    if len(text)>8192:raise ValueError('Telegram proxy link is too long.')
    u=urllib.parse.urlsplit(text.strip())
    if u.fragment or u.username or u.password:raise ValueError('Unsupported Telegram link.')
    if u.scheme=='tg' and u.netloc in ('proxy','socks') and not u.path:action=u.netloc
    elif u.scheme=='https' and u.netloc.lower() in ('t.me','telegram.me') and u.path in ('/proxy','/socks'):action=u.path[1:]
    else:raise ValueError('Use tg://proxy, tg://socks or the equivalent official Telegram HTTPS link.')
    raw=urllib.parse.parse_qs(u.query,keep_blank_values=True,strict_parsing=True)
    allowed={'server','port','secret'} if action=='proxy' else {'server','port','user','pass'}
    if set(raw)-allowed or any(len(v)!=1 for v in raw.values()):raise ValueError('Unknown or duplicate Telegram proxy parameter.')
    q={k:v[0] for k,v in raw.items()};host=q.get('server','')
    if not host or len(host)>253 or any(c in host for c in '/\\@?#\r\n\x00 '):raise ValueError('Invalid proxy server.')
    # Accept IP addresses or conventional DNS labels; do not allow shell/URL syntax.
    try:ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?',host) or any(not part or len(part)>63 for part in host.split('.')):raise ValueError('Invalid proxy hostname.')
    port=int(q.get('port','0'))
    if not 1<=port<=65535:raise ValueError('Invalid proxy port.')
    secret=q.get('secret','')
    if action=='proxy':
        if not re.fullmatch('[0-9a-fA-F]+',secret) or len(secret)%2 or not (len(secret)==32 or len(secret)==34 and secret[:2].lower()=='dd' or len(secret)>=36 and secret[:2].lower()=='ee'):raise ValueError('Unsupported MTProto secret encoding.')
    if any(len(q.get(k,''))>255 for k in ('user','pass')):raise ValueError('SOCKS credentials are too long.')
    return TelegramProxy('MTProto' if action=='proxy' else 'SOCKS5',host,port,secret,q.get('user',''),q.get('pass',''),uuid.uuid4().hex)

class TelegramStore:
    def __init__(self,root):self.path=pathlib.Path(root)/'telegram.dat'
    def load(self):
        if not self.path.exists():return []
        magic,data=self.path.read_bytes().split(b'\n',1)
        if magic==b'DPAPI1':
            if os.name!='nt':raise OSError('Telegram proxies require the original Windows account.')
            data=protect(data,True)
        elif magic!=b'JSON1':raise ValueError('Unknown Telegram store.')
        return [TelegramProxy(**x) for x in json.loads(data)]
    def save(self,items):
        data=json.dumps([asdict(x) for x in items]).encode()
        atomic_write(self.path,(b'DPAPI1\n'+protect(data)) if os.name=='nt' else b'JSON1\n'+data)

class CoreManager:
    """Only a pinned, shipped Xray release can be installed. No latest-version guess."""
    def __init__(self,root):self.root=pathlib.Path(root)/'managed-cores';self.root.mkdir(parents=True,exist_ok=True)
    def version(self,path):
        p=pathlib.Path(path)
        if not p.is_file():return 'Not installed'
        result=subprocess.run([str(p),'version'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5,**HIDDEN)
        match=re.match(rb'Xray ([0-9A-Za-z.+-]{1,50})\b',result.stdout[:200])
        if result.returncode or not match:raise ValueError('Executable is not a recognized Xray core.')
        return 'Xray '+match[1].decode('ascii')
    def release(self):
        lock=json.loads((pathlib.Path(__file__).resolve().parents[1]/'dependencies.lock.json').read_text())
        machine=platform.machine().lower()
        if machine not in ('amd64','x86_64'):raise ValueError('Pinned core is available for x64 only.')
        archive='Xray-windows-64.zip' if os.name=='nt' else 'Xray-linux-64.zip'
        return 'https://github.com/XTLS/Xray-core/releases/download/v'+lock['Xray']+'/'+archive,lock['sha256'][archive]
    def install(self,cancel,archive_path=None):
        url,expected=self.release();check_cancel(cancel)
        # Download and stage on the same filesystem as final install, for atomic rename.
        with tempfile.TemporaryDirectory(dir=self.root,prefix='.stage-') as temporary:
            stage=pathlib.Path(temporary);archive=stage/'release.zip'
            if archive_path:shutil.copyfile(archive_path,archive)
            else:
                request=urllib.request.Request(url,headers={'User-Agent':'NekoRayNext/'+VERSION})
                class ReleasesOnly(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self,req,fp,code,msg,headers,newurl):
                        target=urllib.parse.urlsplit(newurl)
                        if target.scheme!='https' or target.hostname not in ('github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'):raise ValueError('Untrusted release redirect.')
                        return super().redirect_request(req,fp,code,msg,headers,newurl)
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),ReleasesOnly())
                with opener.open(request,timeout=15) as response,archive.open('wb') as out:
                    total=0
                    while True:
                        check_cancel(cancel);data=response.read(65536)
                        if not data:break
                        total+=len(data)
                        if total>100*1024*1024:raise ValueError('Core archive exceeds size limit.')
                        out.write(data)
            if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError('Official pinned release checksum did not match. Nothing installed.')
            check_cancel(cancel);name='xray.exe' if os.name=='nt' else 'xray';target=stage/name
            with zipfile.ZipFile(archive) as bundle:
                for info in bundle.infolist():
                    path=pathlib.PurePosixPath(info.filename)
                    if path.is_absolute() or '..' in path.parts or '\\' in info.filename or ':' in info.filename:raise ValueError('Unsafe core archive path.')
                    if info.file_size>150*1024*1024 or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe core archive member.')
                matches=[i for i in bundle.infolist() if i.filename==name]
                if len(matches)!=1:raise ValueError('Release does not contain exactly one expected executable.')
                atomic_write(target,bundle.read(matches[0]));target.chmod(0o700)
            version=self.version(target);check_cancel(cancel)
            final=self.root/name;backup=self.root/(name+'.previous')
            if final.exists():atomic_write(backup,final.read_bytes());backup.chmod(0o700)
            os.replace(target,final)
            return str(final),version
    def rollback(self):
        name='xray.exe' if os.name=='nt' else 'xray';final=self.root/name;backup=self.root/(name+'.previous')
        if not backup.exists():raise ValueError('No previous managed core is available.')
        version=self.version(backup);prior=final.read_bytes() if final.exists() else None
        atomic_write(final,backup.read_bytes());final.chmod(0o700)
        if prior:atomic_write(backup,prior);backup.chmod(0o700)
        return str(final),version


def port_report(settings):
    lines=[]
    for key in ('http_port','socks_port','stats_port'):
        with socket.socket() as s:
            s.settimeout(.4);listening=s.connect_ex(('127.0.0.1',settings[key]))==0
        lines.append(f'{key}: '+('listener responds (ownership not proven)' if listening else 'no TCP listener found'))
    return '\n'.join(lines)

def privacy_report(settings,running,cancel):
    lines=['Privacy check — measurements only; HTTP proxy does not enforce whole-device privacy.']
    if not running:return '\n'.join(lines+['Proxy is stopped. Exit IP cannot be verified. DNS/IPv4/IPv6 leak status: not measured.'])
    check_cancel(cancel);ip=proxy_public_ip(settings['http_port']);check_cancel(cancel)
    try:country=proxy_country(settings['http_port'],ip)
    except Exception:country=''
    check_cancel(cancel)
    lines.extend(['Proxy exit IP: '+ip,'Address family: IPv'+str(ipaddress.ip_address(ip).version),'Approximate country: '+(country or 'not supplied'),'HTTPS verified through explicit local proxy.','DNS leak / direct bypass / IPv4 and IPv6 route enforcement: NOT measured.','System Proxy affects WinINET-aware applications only.'])
    return '\n'.join(lines)

def diagnostic_report(owner,settings,cancel,kind='full'):
    lines=['Apex VPN '+VERSION+' · sanitized Settings diagnostics',time.strftime('%Y-%m-%d %H:%M:%S'),'OS: '+platform.system()+' '+platform.release(),'Core state: '+('running' if owner.engine.running else 'stopped'),'Connection stage: '+owner.engine.stage,'Pending proxy recovery: '+str(owner.engine.lease.path.exists())]
    check_cancel(cancel)
    if kind in ('full','core'):
        try:lines.append(CoreManager(owner.root).version(settings['core']))
        except ValueError as e:lines.append('Core validation: '+str(e))
        except Exception as e:lines.append('Core validation: '+safe_error(e))
        p=owner.selected_profile()
        if p:
            try:lines.append(owner.engine.core_preflight(p,settings))
            except Exception as e:lines.append('Configuration: '+safe_error(e))
        else:lines.append('No profile selected.')
    if kind in ('full','ports'):lines.append(port_report(settings))
    check_cancel(cancel)
    if kind=='tcp':
        p=owner.selected_profile()
        if not p:raise ValueError('Choose a profile first.')
        lines.append(f'Selected server TCP: {tcp_latency(p.host,p.port,settings["health_timeout"]):.0f} ms; authentication not verified.')
    if kind=='routes':
        if os.name!='nt':return 'Windows route inspection is unavailable on this operating system. No routes were changed.'
        # Only the trusted Windows system utility, never PATH or a user shell command.
        utility=pathlib.Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/'route.exe'
        lines.append('Local private route tables below are NOT included in support bundles. This is inspection, not proof of leak protection.')
        for family in ('-4','-6'):
            check_cancel(cancel)
            result=subprocess.run([str(utility),'PRINT',family],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=8,**HIDDEN)
            if result.returncode:lines.append(family+': inspection failed.')
            else:lines.append(result.stdout[:65536].decode('utf-8',errors='replace'))
    if kind=='dns':
        # User-initiated resolver test; result count only, never export a private hostname.
        host=urllib.parse.urlsplit(settings['https_url']).hostname
        addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        lines.append('System DNS lookup of the configured verification endpoint: '+str(len({r[4][0] for r in addresses}))+' addresses. Not a DNS-leak test.')
    if kind in ('http','https'):
        if not owner.engine.running:raise ValueError('Connect first to verify HTTP/HTTPS through the local proxy.')
        ms=proxy_probe(settings['http_port'],settings[kind+'_url'],timeout=settings['health_timeout'])
        lines.append(f'{kind.upper()} through local proxy: {ms:.0f} ms, response verified.')
    check_cancel(cancel);lines.append('No Windows proxy, firewall or routes were changed by these checks.')
    return '\n'.join(lines)

def support_bundle(path,owner):
    """Constructed from a whitelist. Never includes arbitrary reports or user-controlled labels."""
    from .errors import MESSAGES
    # Error exports contain only recognized fixed codes, never error strings from callers.
    errors=[]
    for entry in owner.history_errors:
        codes=[code for code in MESSAGES if code in entry]
        if codes:errors.extend(codes)
    info={'application':VERSION,'os':platform.system(),'os_release':platform.release(),'architecture':platform.machine(),'core_state':'running' if owner.engine.running else 'stopped','connection_stage':owner.engine.stage,'proxy_recovery_pending':owner.engine.lease.path.exists(),'profile_count':len(owner.profiles),'subscription_count':len(owner.subscriptions),'error_codes':errors[-50:]}
    try:info['core_version']=CoreManager(owner.root).version(owner.settings['core'])
    except Exception:info['core_version']='unavailable'
    # ZIP is assembled privately then atomically written; no data/config/settings files copied.
    import io
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('summary.json',json.dumps(info,indent=2))
        z.writestr('privacy.txt','No profile links, addresses, names, credentials, subscription URLs, raw logs, clipboard contents or private reports are included. Error history is limited to fixed recognized codes.\n')
    atomic_write(path,buffer.getvalue());return 'Sanitized support ZIP exported.'
