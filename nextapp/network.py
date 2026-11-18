"""Bounded networking operations, real HTTP/HTTPS via an explicit HTTP proxy."""
import http.client, socket, ssl, time, urllib.request
from urllib.parse import urlsplit
from .profiles import ProfileError
from .errors import AppError

MAX_BODY=8*1024*1024

def tcp_latency(host,port,timeout=4):
    start=time.monotonic()
    with socket.create_connection((host,port),timeout): return (time.monotonic()-start)*1000

def proxy_probe(port,url,timeout=8):
    u=urlsplit(url)
    if u.scheme not in ('http','https') or not u.hostname or u.username or u.password: raise ProfileError('Health URL must use HTTP or HTTPS without credentials.')
    start=time.monotonic()
    if u.scheme=='https':
        conn=http.client.HTTPSConnection('127.0.0.1',port,timeout=timeout,context=ssl.create_default_context())
        conn.set_tunnel(u.hostname,u.port or 443)
        path=(u.path or '/')+('?' +u.query if u.query else '')
    else: conn=http.client.HTTPConnection('127.0.0.1',port,timeout=timeout); path=url
    try:
        conn.request('GET',path,headers={'User-Agent':'NekoRayNext/0.1','Connection':'close'})
        response=conn.getresponse()
        # Small health endpoints only; do not consume arbitrary large responses.
        response.read(4096)
        if not 200<=response.status<300: raise AppError('HTTP_STATUS',f'Health endpoint returned HTTP {response.status}; check the endpoint in Settings.')
        return (time.monotonic()-start)*1000
    finally: conn.close()

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        target=urlsplit(newurl)
        if target.scheme!='https' or target.username or target.password: raise ProfileError('Subscription redirect to insecure HTTP rejected.')
        # Only the user's supplied service is contacted; never forward custom credentials.
        return super().redirect_request(req,fp,code,msg,headers,newurl)

class SubscriptionText(str):
    def __new__(cls,text,metadata=None):
        value=super().__new__(cls,text);value.metadata=metadata or {};return value

def subscription_metadata(header):
    result={}
    if not header or len(header)>2048:return result
    for item in header.split(';'):
        parts=item.strip().split('=',1)
        if len(parts)==2 and parts[0] in ('upload','download','total','expire'):
            if parts[1].isdigit() and len(parts[1])<=19:
                value=int(parts[1])
                if value<=2**63-1:result[parts[0]]=value
    return result

def fetch_subscription(url,proxy_port=None):
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password: raise ProfileError('Use an HTTPS subscription URL without userinfo.')
    proxies={'https':f'http://127.0.0.1:{proxy_port}'} if proxy_port else {}
    opener=urllib.request.build_opener(urllib.request.ProxyHandler(proxies),SafeRedirect())
    try:
        with opener.open(urllib.request.Request(url,headers={'User-Agent':'NekoRayNext/0.1'}),timeout=15) as r:
            data=r.read(MAX_BODY+1);metadata=subscription_metadata(r.headers.get('Subscription-Userinfo',''))
        if len(data)>MAX_BODY: raise ProfileError('Subscription exceeds 8 MiB.')
        return SubscriptionText(data.decode('utf-8-sig'),metadata)
    except ProfileError: raise
    except Exception: raise ProfileError('Subscription could not be downloaded. Check its URL and network; URL details were not logged.') from None


def metrics(port):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=1.0)
    try:
        conn.request('GET','/debug/vars'); response=conn.getresponse()
        if response.status!=200: raise ConnectionError('Statistics unavailable.')
        import json
        d=json.loads(response.read(1024*1024))
        counters=d.get('stats',{}).get('outbound',{}).get('proxy',{})
        # Core versions expose a nested stats map. Never substitute system-wide counters.
        if 'uplink' not in counters or 'downlink' not in counters: raise ValueError('Core statistics format is unavailable.')
        return int(counters['uplink']),int(counters['downlink'])
    finally: conn.close()


def proxy_public_ip(port,url='https://api.ipify.org?format=json',timeout=8):
    """On-demand IP, explicitly direct when port=None, otherwise strict proxy tunnel."""
    import ipaddress,json
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password:raise ProfileError('IP endpoint must use HTTPS without credentials.')
    conn=http.client.HTTPSConnection(u.hostname if port is None else '127.0.0.1',u.port or 443 if port is None else port,timeout=timeout,context=ssl.create_default_context())
    if port is not None:conn.set_tunnel(u.hostname,u.port or 443)
    try:
        conn.request('GET',(u.path or '/')+('?' +u.query if u.query else ''),headers={'User-Agent':'NekoRayNext/0.3','Connection':'close'})
        response=conn.getresponse();body=response.read(4097)
        if response.status!=200 or len(body)>4096:raise ProfileError('IP endpoint returned an invalid response. Tap again to retry.')
        try:return str(ipaddress.ip_address(json.loads(body)['ip']))
        except Exception:raise ProfileError('IP endpoint returned an invalid IP address.') from None
    finally:conn.close()


def proxy_country(port,ip,url=None,timeout=4):
    """Look up only the explicitly requested exit IP. No direct fallback or logging."""
    import ipaddress,json,re
    from urllib.parse import quote
    requested=str(ipaddress.ip_address(ip))
    u=urlsplit(url or 'https://api.country.is/'+quote(requested,safe=''))
    if u.scheme!='https' or not u.hostname or u.username or u.password:raise ProfileError('Country endpoint must use HTTPS.')
    conn=http.client.HTTPSConnection(u.hostname if port is None else '127.0.0.1',u.port or 443 if port is None else port,timeout=timeout,context=ssl.create_default_context())
    if port is not None:conn.set_tunnel(u.hostname,u.port or 443)
    try:
        conn.request('GET',(u.path or '/')+('?' +u.query if u.query else ''),headers={'User-Agent':'NekoRayNext/0.3.1','Connection':'close'})
        response=conn.getresponse();data=response.read(4097)
        if response.status!=200 or len(data)>4096:return ''
        try:
            result=json.loads(data)
            if str(ipaddress.ip_address(result['ip']))!=requested:return ''
            code=result.get('country')
            if not isinstance(code,str) or not re.fullmatch('[A-Z]{2}',code):return ''
            return code
        except (ValueError,KeyError,TypeError):return ''
    finally:conn.close()
