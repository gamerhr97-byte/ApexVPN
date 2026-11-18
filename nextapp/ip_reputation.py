"""On-demand independent provider report; never equate reachability with reputation."""
import http.client,ipaddress,json,ssl
from urllib.parse import urlencode
from .profiles import ProfileError


def parse_report(data, requested):
    if not isinstance(data,dict) or data.get('error'):raise ProfileError('Reputation provider rejected the request or rate limit was reached.')
    try:
        if ipaddress.ip_address(data.get('ip'))!=ipaddress.ip_address(requested):raise ValueError()
    except (ValueError,TypeError):raise ProfileError('Reputation response IP did not match the requested IP.') from None
    fields=('is_abuser','is_tor','is_proxy','is_vpn','is_datacenter')
    # Missing detection flags are unknown, not clean.
    flags={key:data[key] if type(data.get(key)) is bool else None for key in fields}
    return {'ip':str(ipaddress.ip_address(requested)),'provider':'ipapi.is',
            'flags':flags,'abuse_status':'flagged' if flags['is_abuser'] is True else 'not_flagged' if flags['is_abuser'] is False else 'unknown'}


def query_reputation(ip,port=None,key=''):
    ip=str(ipaddress.ip_address(ip))
    conn=http.client.HTTPSConnection('127.0.0.1' if port is not None else 'api.ipapi.is',port if port is not None else 443,timeout=8,context=ssl.create_default_context())
    if port is not None:conn.set_tunnel('api.ipapi.is',443)
    try:
        # Credentials travel in a TLS-protected JSON body, never a URL or local log.
        body=json.dumps({'q':ip,**({'key':key} if key else {})})
        conn.request('POST','/',body=body,headers={'Content-Type':'application/json','Connection':'close','User-Agent':'ApexVPN/0.10.4'})
        r=conn.getresponse();raw=r.read(65537)
        if r.status!=200 or len(raw)>65536:raise ProfileError('Reputation lookup unavailable; verify API key and request limit.')
        return parse_report(json.loads(raw),ip)
    finally:conn.close()
