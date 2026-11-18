"""Import supported proxy entries while retaining the complete source text.

Only outbound entries are selected; supplied listeners, scripts and routing are
not executed. Profiles are explicitly named as extracted entries.
"""
import copy,json
from .profiles import Profile,ProfileError,Unsupported


def clash_profiles(text):
    import yaml
    from yaml.tokens import AliasToken,AnchorToken
    if any(isinstance(t,(AliasToken,AnchorToken)) for t in yaml.scan(text)):
        raise Unsupported('YAML anchors/aliases are disabled; expand the source first.')
    doc=yaml.safe_load(text)
    if not isinstance(doc,dict) or not isinstance(doc.get('proxies'),list):raise ProfileError('Clash YAML requires a proxies list.')
    if not 0<len(doc['proxies'])<=10000:raise ProfileError('Clash profiles must be between 1 and 10,000.')
    profiles=[]
    for item in doc['proxies']:
        if not isinstance(item,dict):raise ProfileError('Invalid Clash proxy entry.')
        c=copy.deepcopy(item);kind=c.get('type')
        common={'name','type','server','port','udp','tls','servername','sni','skip-cert-verify','alpn','client-fingerprint'}
        extra={'vless':{'uuid','flow','network','ws-opts','grpc-opts','reality-opts'},'vmess':{'uuid','alterId','cipher','network','ws-opts','grpc-opts'},'trojan':{'password','network','ws-opts','grpc-opts'},'ss':{'password','cipher'},'hysteria2':{'password','obfs','obfs-password','up','down'},'tuic':{'uuid','password','congestion-controller','udp-relay-mode'},'anytls':{'password'},'socks5':{'username','password'},'socks4':{'username'},'http':{'username','password'}}
        if kind not in extra or set(c)-(common|extra[kind]):raise Unsupported('Clash entry has unsupported type/options; no fields were silently removed.')
        if not c.get('server') or type(c.get('port')) is not int or not 1<=c['port']<=65535:raise ProfileError('Clash entry needs a server and valid port.')
        ob={'type':{'ss':'shadowsocks','socks5':'socks','socks4':'socks'}.get(kind,kind),'server':c['server'],'server_port':c['port']}
        for key in ('uuid','password','username','flow'):
            if key in c:ob[key]=c[key]
        if kind=='ss':ob['method']=c['cipher']
        if kind=='vmess':ob.update(security=c.get('cipher','auto'),alter_id=c.get('alterId',0))
        if kind=='socks4':ob['version']='4'
        if kind in {'hysteria2','tuic','anytls','trojan'} or c.get('tls'):
            ob['tls']={'enabled':True,'server_name':c.get('servername',c.get('sni',c['server']))}
            if c.get('skip-cert-verify'):ob['tls']['insecure']=True
            if c.get('alpn'):ob['tls']['alpn']=c['alpn']
            if c.get('client-fingerprint'):ob['tls']['utls']={'enabled':True,'fingerprint':c['client-fingerprint']}
            if c.get('reality-opts'):
                r=c['reality-opts']
                if set(r)-{'public-key','short-id'}:raise Unsupported('Unsupported Clash reality options.')
                ob['tls']['reality']={'enabled':True,'public_key':r['public-key'],'short_id':r.get('short-id','')}
        elif any(c.get(k) for k in ('skip-cert-verify','servername','sni','alpn','client-fingerprint','reality-opts')):raise Unsupported('TLS options without TLS are not discarded.')
        net=c.get('network','tcp')
        if net=='ws':
            opts=c.get('ws-opts',{})
            if set(opts)-{'path','headers'}:raise Unsupported('Unsupported WebSocket options.')
            ob['transport']={'type':'ws',**opts}
        elif net=='grpc':
            opts=c.get('grpc-opts',{})
            if set(opts)-{'grpc-service-name'}:raise Unsupported('Unsupported gRPC options.')
            ob['transport']={'type':'grpc','service_name':opts.get('grpc-service-name','')}
        elif net!='tcp':raise Unsupported('Unsupported Clash network.')
        if kind=='hysteria2':
            if c.get('obfs'):ob['obfs']={'type':c['obfs'],'password':c.get('obfs-password','')}
            for k in ('up','down'):
                if k in c:
                    if type(c[k]) is not int:raise Unsupported('Clash Hysteria bandwidth must be integer Mbps.')
                    ob[k+'_mbps']=c[k]
        if kind=='tuic':
            for a,b in [('congestion-controller','congestion_control'),('udp-relay-mode','udp_relay_mode')]:
                if a in c:ob[b]=c[a]
        profiles.append(Profile(str(c.get('name') or kind)+' · extracted','singbox-outbound',c['server'],c['port'],original=text,raw=ob))
    return profiles
