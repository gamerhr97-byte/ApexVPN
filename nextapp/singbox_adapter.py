"""Strict auxiliary sing-box adapter, shared by live and isolated tests.

Uses only loopback inbounds and private stdin configuration. Unknown URI fields
are rejected instead of silently dropped. Existing proxy lease/HTTPS gates stay
owned by Engine.
"""
import copy, ipaddress, json, os
from pathlib import Path
from urllib.parse import urlsplit,unquote
from .profiles import Profile,ProfileError,Unsupported,query_items

PROTOCOLS={'hysteria2','hysteria','tuic','anytls','socks4','socks4a','ssh','naive','singbox-outbound'}
RAW_TYPES={'hysteria2','hysteria','tuic','anytls','socks','ssh','naive','http','vless','vmess','trojan','shadowsocks','wireguard'}


def parse_aux_link(link):
    u=urlsplit(link);scheme=u.scheme.lower()
    aliases={'hy2':'hysteria2','hy':'hysteria','naive+https':'naive','naive+quic':'naive'}
    kind=aliases.get(scheme,scheme)
    if kind not in PROTOCOLS-{'singbox-outbound'}:raise Unsupported('No adapter for this URI scheme.')
    if not u.hostname:raise ProfileError('Missing server address.')
    q=query_items(u.query)
    secret=unquote(u.password or '') if kind in {'tuic','ssh','naive','socks4','socks4a'} else unquote(u.username or '')
    if kind in {'tuic','ssh','naive','socks4','socks4a'}:q['username']=unquote(u.username or '')
    if scheme=='naive+quic':q['quic']='1'
    port=u.port or (22 if kind=='ssh' else 1080 if kind.startswith('socks') else 443)
    if not 1<=port<=65535:raise ProfileError('Invalid port.')
    return Profile(unquote(u.fragment) or kind.upper(),kind,u.hostname,port,secret,q,link)


def tls_options(q,host,settings):
    insecure=str(q.get('insecure',q.get('allowInsecure','0'))).lower() in {'1','true'}
    if insecure and not settings.get('allow_insecure_profiles',False):
        raise Unsupported('Profile requests insecure TLS. Verify its certificate/SNI or explicitly enable Allow insecure TLS profiles in Security settings.')
    tls={'enabled':True,'server_name':q.get('sni',q.get('peer',host))}
    if insecure:tls['insecure']=True
    if q.get('alpn'):tls['alpn']=q['alpn'].split(',')
    return tls


def outbound(profile, settings):
    kind=profile.protocol;q=copy.deepcopy(profile.params)
    if kind=='singbox-outbound':
        ob=copy.deepcopy(profile.raw)
        if not isinstance(ob,dict) or ob.get('type') not in RAW_TYPES:raise Unsupported('Unsupported sing-box outbound type.')
        def inspect(value):
            if isinstance(value,dict):
                for key,v in value.items():
                    if key.endswith('_path') or key in {'detour','download_url','domain_resolver'}:raise Unsupported('External files, detours and custom resolvers need explicit review.')
                    if key=='insecure' and v and not settings.get('allow_insecure_profiles',False):raise Unsupported('Insecure TLS is disabled in Security settings.')
                    inspect(v)
            elif isinstance(value,list):
                for v in value:inspect(v)
        inspect(ob)
        if ob['type']=='ssh' and not ob.get('host_key'):raise Unsupported('SSH requires a pinned host_key.')
        ob['tag']='proxy';return ob
    allowed={'sni','peer','alpn','insecure','allowInsecure','security','username'}
    if kind=='hysteria2':allowed|={'obfs','obfs-password','upmbps','downmbps'}
    if kind=='hysteria':allowed|={'auth','obfs','upmbps','downmbps','protocol'}
    if kind=='tuic':allowed|={'congestion_control','udp_relay_mode','disable_sni'}
    if kind=='ssh':allowed|={'host_key'}
    if kind=='naive':allowed|={'quic'}
    if set(q)-allowed:raise Unsupported('Unmapped auxiliary-core parameters retained; edit before connecting.')
    if q.get('security','tls')!='tls':raise Unsupported('This auxiliary URI requires TLS security.')
    ob={'type':'socks' if kind.startswith('socks4') else kind,'tag':'proxy','server':profile.host,'server_port':profile.port}
    if kind.startswith('socks4'):
        ob['version']='4a' if kind=='socks4a' else '4'
        if q.get('username'):ob['username']=q['username']
        if profile.secret:raise Unsupported('SOCKS4 does not support password authentication.')
        return ob
    if kind=='ssh':
        if not q.get('host_key'):raise Unsupported('SSH requires host_key to verify the server identity.')
        ob.update(user=q.get('username') or 'root',password=profile.secret,host_key=[q['host_key']]);return ob
    ob['tls']=tls_options(q,profile.host,settings)
    if kind in {'hysteria2','anytls','tuic','naive'}:ob['password']=profile.secret
    if kind=='tuic':
        ob['uuid']=q.get('username','')
        for k in ('congestion_control','udp_relay_mode'):
            if k in q:ob[k]=q[k]
        if str(q.get('disable_sni','0')).lower() not in {'0','false'}:raise Unsupported('disable_sni was not silently applied.')
    if kind=='naive':ob.update(username=q.get('username',''),quic=q.get('quic')=='1')
    if kind in {'hysteria','hysteria2'}:
        for key in ('up','down'):
            if q.get(key+'mbps'):ob[key+'_mbps']=int(q[key+'mbps'])
        if kind=='hysteria':
            if q.get('protocol','udp')!='udp':raise Unsupported('Hysteria transport must be UDP.')
            if not ob.get('up_mbps') or not ob.get('down_mbps'):raise Unsupported('Hysteria requires upmbps/downmbps.')
            ob['auth_str']=q.get('auth',profile.secret)
            if q.get('obfs'):ob['obfs']=q['obfs']
        elif q.get('obfs'):
            if q['obfs']!='salamander' or not q.get('obfs-password'):raise Unsupported('Hysteria2 obfs requires salamander and obfs-password.')
            ob['obfs']={'type':'salamander','password':q['obfs-password']}
    return ob


def make_config(profile,settings):
    from .direct_routing import domains,applications
    from .service_checks import SERVICES
    rules=[]
    # Diagnostic destinations always follow the selected outbound before bypasses.
    protected=[urlsplit(settings[k]).hostname for k in ('https_url','http_url')]
    protected+=['api.ipify.org','api.country.is','api.ipapi.is']+[urlsplit(s.url).hostname for s in SERVICES]
    rules.append({'domain':list(dict.fromkeys(protected)),'action':'route','outbound':'proxy'})
    if settings.get('bypass'):rules.append({'ip_is_private':True,'action':'route','outbound':'direct'})
    if settings.get('direct_enabled'):
        suffixes=(['ir'] if settings.get('direct_ir') else [])+domains(settings.get('direct_domains',''))
        if suffixes:rules.append({'domain_suffix':suffixes,'action':'route','outbound':'direct'})
        apps=applications(settings.get('direct_apps',''))
        names=[x+'.exe' for x in apps if '/' not in x];paths=[x for x in apps if '/' in x]
        if names:rules.append({'process_name':names,'action':'route','outbound':'direct'})
        if paths:rules.append({'process_path':paths,'action':'route','outbound':'direct'})
    return {'log':{'level':'error'},'inbounds':[
        {'type':'http','tag':'http-in','listen':'127.0.0.1','listen_port':settings['http_port']},
        {'type':'socks','tag':'socks-in','listen':'127.0.0.1','listen_port':settings['socks_port']}],
        'outbounds':[outbound(profile,settings),{'type':'direct','tag':'direct'}],
        'route':{'rules':rules,'final':'proxy'}}
