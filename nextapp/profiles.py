"""Lossless profile import and conservative Xray configuration construction."""
from __future__ import annotations
import base64, copy, json, uuid
from dataclasses import dataclass, field, asdict
from urllib.parse import urlsplit, unquote

class ProfileError(ValueError): pass
class Unsupported(ProfileError): pass

def b64(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

def query_items(q):
    # URI query values use percent encoding. Preserve literal '+' in cryptographic fields.
    out = {}
    for pair in q.split('&'):
        if not pair: continue
        k, _, v = pair.partition('='); k, v = unquote(k), unquote(v)
        if k in out: raise ProfileError('Duplicate query parameter; import rejected without changes.')
        out[k] = v
    return out

@dataclass
class Profile:
    name: str
    protocol: str
    host: str
    port: int
    secret: str = ''
    params: dict = field(default_factory=dict)
    original: str = ''
    raw: dict | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    service_cache: dict = field(default_factory=dict)
    service_score: int | None = None  # successes in the optional 100-site public check
    free_failures: int = 0
    favorite: bool = False
    # A favorited provider entry is copied into Local servers; keep its source
    # identity so the next refresh updates it instead of adding a duplicate.
    favorite_source_id: str = ''
    gemini_ok: bool = False  # Public page passed: not proof of account/region entitlement
    latency: float | None = None
    tested_at: str = ''
    last_success: str = ''
    subscription_id: str = ''
    test_status: str = ''
    test_method: str = ''
    test_error: str = ''
    def to_dict(self): return asdict(self)


def parse_link(link):
    link = link.strip()
    from .telegram_transport import is_telegram_proxy_link,as_profile
    if is_telegram_proxy_link(link):return as_profile(link)
    try:
        u = urlsplit(link); scheme = u.scheme.lower()
        if scheme in ('socks4','socks4a','tuic','anytls','hysteria','hy','ssh','naive+https','naive+quic'):
            from .singbox_adapter import parse_aux_link
            return parse_aux_link(link)
        if scheme == 'vmess':
            d = json.loads(b64(link[8:]).decode('utf-8'))
            return Profile(str(d.get('ps') or 'VMess profile'), 'vmess', str(d['add']), int(d['port']), str(d['id']), d, link)
        if scheme in ('socks5', 'socks', 'http', 'https'):
            # Plain proxy links. Credential-free HTTPS links are subscription URLs,
            # never silently treated as unauthenticated upstream HTTP proxies.
            if not u.hostname or not u.port or not 1 <= u.port <= 65535:
                raise ProfileError('Proxy URL needs a hostname and explicit valid port.')
            if u.query:
                raise Unsupported('Upstream proxy query parameters are not supported; original URL retained.')
            if scheme == 'https' and u.username is None:
                raise Unsupported('Credential-free HTTPS URL is a subscription, not a proxy profile.')
            if u.username is None and u.password is not None:
                raise ProfileError('Proxy password requires a username.')
            params = {'username': unquote(u.username)} if u.username else {}
            return Profile(unquote(u.fragment) or scheme.upper() + ' proxy',
                           'socks5' if scheme in ('socks5','socks') else scheme,
                           u.hostname, u.port, unquote(u.password or ''), params, link)
        if scheme not in ('vless','trojan','ss','hysteria2','hy2'):
            raise Unsupported('Unsupported outbound scheme; original link is not executed. A compatible validated adapter is required.')
        # SIP002 and legacy base64(method:password@host:port)
        if scheme == 'ss' and '@' not in link.split('#')[0]:
            decoded = b64(u.netloc or u.path).decode()
            u = urlsplit('ss://' + decoded + ('#'+u.fragment if u.fragment else ''))
        if scheme!='ss' and u.password is not None:raise ProfileError('Encode colons inside authentication with percent encoding; ambiguous userinfo was not imported.')
        params = query_items(u.query)
        secret = unquote(u.username or '')
        if scheme == 'ss':
            if u.password is not None: secret += ':' + unquote(u.password)
            if ':' not in secret: secret = b64(secret).decode()
            method, sep, password = secret.partition(':')
            if not sep: raise ProfileError('Missing Shadowsocks method or password.')
            params['method'] = method; secret = password
        if not u.hostname or not secret: raise ProfileError('Missing server address or authentication field.')
        port = u.port or (443 if scheme != 'ss' else 8388)
        if not 1 <= port <= 65535: raise ProfileError('Invalid server port.')
        return Profile(unquote(u.fragment) or scheme.upper()+' profile', 'hysteria2' if scheme=='hy2' else scheme, u.hostname, port, secret, params, link)
    except ProfileError: raise
    except Exception: raise ProfileError('Malformed profile link. No credentials were logged.') from None


def parse_import(text):
    text = text.strip().lstrip('\ufeff')
    if not text: raise ProfileError('Nothing to import.')
    if len(text.encode()) > 8*1024*1024: raise ProfileError('Import exceeds 8 MiB.')
    if any(line.strip().startswith('proxies:') for line in text.splitlines()[:80]):
        from .config_formats import clash_profiles
        return clash_profiles(text)
    if text[0] in '[{':
        try: data = json.loads(text)
        except Exception: raise ProfileError('Malformed JSON configuration.') from None
        if isinstance(data, dict) and 'outbounds' in data:
            # Full core configs are preserved, but never executed blindly.
            if not isinstance(data['outbounds'], list) or not data['outbounds']: raise ProfileError('No outbounds in configuration.')
            ob = data['outbounds'][0]
            if 'protocol' not in ob:
                from .singbox_adapter import RAW_TYPES
                proxies=[x for x in data['outbounds'] if isinstance(x,dict) and x.get('type') in RAW_TYPES]
                if not proxies:raise Unsupported('No supported sing-box proxy outbounds.')
                return [Profile(str(x.get('tag') or 'sing-box outbound'),'singbox-outbound',str(x.get('server','')),int(x.get('server_port',0)),original=text,raw=x) for x in proxies]
            return [Profile('Imported Xray configuration', 'xray-json', '', 0, original=text, raw=data)]
        raise Unsupported('JSON must be a complete Xray configuration with outbounds. Use migration for NekoRay data.')
    if '://' not in text:
        try: text = b64(text).decode('utf-8')
        except Exception: raise ProfileError('Not a profile link or base64 subscription.') from None
    links = [x.strip() for x in text.splitlines() if x.strip() and not x.lstrip().startswith('#')]
    if len(links)>10000: raise ProfileError('Import is limited to 10,000 profiles per batch.')
    return [parse_link(x) for x in links]


# Names from known client schemas are safe for shared diagnostics. Unknown key names
# stay in a local, user-opened report; arbitrary keys can themselves contain secrets.
PUBLIC_FIELD_NAMES=set('type security sni peer fp alpn allowInsecure insecure host path serviceName authority mode flow pbk sid spx encryption headerType publicKey shortId spiderX fingerprint serverName packetEncoding packet_encoding ech pqv extra mux concurrency ed seed quicSecurity key net tls v ps add port id aid scy plugin method cs fm fragment'.split())
ALIASES={'serverName':'sni','fingerprint':'fp','publicKey':'pbk','shortId':'sid','spiderX':'spx'}

def parameter_names(p,local=False):
    keys=sorted(p.params)
    if local:
        import re
        # Local-only names; no values, URL, server host or identifier are displayed.
        names=[repr(k[:120]) + (' (truncated)' if len(k)>120 else '') for k in keys]
        return 'Profile parameter NAMES ONLY (local view; review before sharing):\n'+'\n'.join(names)
    public=[k for k in keys if k in PUBLIC_FIELD_NAMES]
    hidden=sum(k not in PUBLIC_FIELD_NAMES for k in keys)
    return 'Known parameter names: '+(', '.join(public) or 'none')+f'. Unlisted field names withheld: {hidden}. Values are never included.'

def normalized_params(p):
    q=copy.deepcopy(p.params)
    if p.protocol in ('vless','trojan'):
        for alias,canonical in ALIASES.items():
            if alias not in q:continue
            if canonical in q and q[canonical]!=q[alias]:
                raise Unsupported(f'Conflicting fields: {canonical} / {alias}. Values were not changed; resolve the aliases in the original profile.')
            q[canonical]=q.pop(alias)
    return q


def outbound(p):
    if p.protocol=='xray-json':
        data=p.raw or {}
        candidates=[x for x in data.get('outbounds',[]) if x.get('protocol') not in ('freedom','blackhole','dns')]
        if len(candidates)!=1 or set(data)-{'outbounds','log'}:
            raise Unsupported('Full Xray JSON with custom routing/listeners is retained for review. To connect, provide an outbounds-only JSON with one proxy outbound.')
        ob=copy.deepcopy(candidates[0])
        if ob.get('protocol') not in {'vless','vmess','trojan','shadowsocks','socks','http','wireguard'}:raise Unsupported('Unsupported Xray JSON outbound protocol.')
        def inspect(v):
            if isinstance(v,dict):
                for k,x in v.items():
                    if k in {'allowInsecure','proxySettings','sockopt','dialerProxy','certificateFile','keyFile','proxyProtocol'} and x:raise Unsupported('Xray JSON external/insecure options need manual review.')
                    inspect(x)
            elif isinstance(v,list):
                for x in v:inspect(x)
        inspect(ob);ob['tag']='proxy';return ob
    if p.protocol in ('socks5', 'http', 'https'):
        q = p.params
        if set(q) - {'username'} or (p.secret and not q.get('username')):
            raise Unsupported('Unsupported proxy settings or password without username; original retained.')
        settings = {'address': p.host, 'port': p.port}
        if q.get('username'):
            settings.update(user=q['username'], **{'pass': p.secret})
        result = {'tag': 'proxy',
                  'protocol': 'socks' if p.protocol == 'socks5' else 'http',
                  'settings': settings}
        if p.protocol == 'https':
            result['streamSettings'] = {'security': 'tls',
                                        'tlsSettings': {'serverName': p.host}}
        return result
    q = normalized_params(p)
    common = {'type','security','sni','peer','fp','alpn','allowInsecure','insecure','host','path','serviceName','authority','mode','flow','pbk','sid','spx','encryption','headerType','extra','cs','fm','fragment'}
    if p.protocol == 'vmess':
        known={'v','ps','add','port','id','aid','scy','net','type','host','path','tls','sni','alpn','fp'}
    elif p.protocol == 'ss': known={'method'}
    else: known=common if p.protocol=='vless' else common-{'encryption','flow'}
    unknown = set(q)-known
    if unknown:
        names=sorted(unknown & PUBLIC_FIELD_NAMES)
        detail=('Known unsupported fields: '+', '.join(names)+'. ') if names else ''
        hidden=len(unknown-set(names))
        if hidden:detail+=f'Unlisted fields: {hidden} (names withheld from shared diagnostics). '
        raise Unsupported('[UNSUPPORTED_FIELDS] '+detail+'Open Servers → Parameter names to inspect the field names locally. Original values are retained; no parameter was silently removed.')
    if p.protocol=='hysteria2': raise Unsupported('Hysteria2 is retained losslessly but is not enabled in this Xray adapter. Use a compatible supported client/core.')
    if p.protocol=='ss':
        return {'tag':'proxy','protocol':'shadowsocks','settings':{'servers':[{'address':p.host,'port':p.port,'method':q['method'],'password':p.secret}]}}
    network = q.get('net' if p.protocol=='vmess' else 'type', 'tcp') or 'tcp'
    if network not in ('tcp','raw','ws','grpc','xhttp','httpupgrade'): raise Unsupported('Transport unsupported by this MVP; original link is retained.')
    security = q.get('tls','') if p.protocol=='vmess' else q.get('security','tls' if p.protocol=='trojan' else 'none')
    security = 'tls' if security=='tls' else security or 'none'
    if security not in ('none','tls','reality'): raise Unsupported('Unsupported transport security.')
    if security=='none' and any(q.get(k) for k in ('sni','peer','fp','alpn')):raise Unsupported('TLS-related fields cannot be applied without TLS or REALITY; original retained.')
    if q.get('peer') and q.get('sni') and q['peer']!=q['sni']:raise Unsupported('Conflicting server-name aliases; original retained.')
    if security=='reality' and q.get('peer'):raise Unsupported('REALITY peer alias is unsupported; use sni explicitly.')
    if q.get('allowInsecure',q.get('insecure','0')).lower() not in ('0','false',''):
        raise Unsupported('Insecure TLS verification is not supported. Fix the server certificate or SNI.')
    if p.protocol=='vless':
        enc=q.get('encryption','none')
        if enc!='none' and not enc.startswith('mlkem768x25519plus.'):
            raise Unsupported('Unsupported VLESS encryption field. A compatible Xray implementation is required; value was preserved.')
        user={'id':p.secret,'encryption':enc}
        if q.get('flow'): user['flow']=q['flow']
        settings={'vnext':[{'address':p.host,'port':p.port,'users':[user]}]}
    elif p.protocol=='vmess':
        if int(q.get('aid',0))!=0: raise Unsupported('Legacy VMess alterId is unsupported.')
        if q.get('type','none') not in ('none',''): raise Unsupported('VMess header type is unsupported.')
        settings={'vnext':[{'address':p.host,'port':p.port,'users':[{'id':p.secret,'alterId':0,'security':q.get('scy','auto')}]}]}
    else: settings={'servers':[{'address':p.host,'port':p.port,'password':p.secret}]}
    stream={'network':network,'security':security}
    if 'headerType' in q:
        if q['headerType'] not in ('','none'):
            raise Unsupported('[UNSUPPORTED_FIELDS] Only headerType=none is supported; nonempty obfuscation headers require a separate adapter. Original value retained.')
        if network in ('tcp','raw'):stream['tcpSettings' if network=='tcp' else 'rawSettings']={'header':{'type':'none'}}
    if q.get('flow','').startswith('xtls-rprx-vision') and network not in ('raw','tcp'):
        raise Unsupported('Vision with this transport needs a separately validated adapter.')
    if security=='reality':
        if not q.get('pbk') or not q.get('sni'): raise ProfileError('REALITY requires public key (pbk) and server name (sni).')
        if network not in ('tcp','raw','grpc','xhttp'): raise Unsupported('REALITY requires TCP/RAW, gRPC or XHTTP.')
        sid=q.get('sid','')
        if len(sid)>16 or len(sid)%2 or any(c not in '0123456789abcdefABCDEF' for c in sid): raise ProfileError('Invalid REALITY short ID.')
        stream['realitySettings']={'serverName':q['sni'],'fingerprint':q.get('fp','chrome'),'publicKey':q['pbk'],'shortId':sid,'spiderX':q.get('spx','/')}
    elif security=='tls':
        stream['tlsSettings']={'serverName':q.get('sni',q.get('peer',p.host)),'fingerprint':q.get('fp','chrome')}
        if q.get('alpn'): stream['tlsSettings']['alpn']=q['alpn'].split(',')
    elif p.protocol in ('vless','trojan','vmess'):
        if p.protocol!='vless' or q.get('encryption','none')=='none':
            raise Unsupported('Unencrypted transport is disabled. Use TLS, REALITY, or supported VLESS encryption.')
    if network=='ws':
        stream['wsSettings']={'path':q.get('path','/')}
        if q.get('host'): stream['wsSettings']['headers']={'Host':q['host']}
    elif network=='grpc':
        if q.get('mode','gun') not in ('gun','multi'): raise Unsupported('Unsupported gRPC mode.')
        stream['grpcSettings']={'serviceName':q.get('serviceName',''),'multiMode':q.get('mode')=='multi'}
        if q.get('authority'): stream['grpcSettings']['authority']=q['authority']
    elif network=='httpupgrade':
        stream['httpupgradeSettings']={'path':q.get('path','/')}
        if q.get('host'):stream['httpupgradeSettings']['host']=q['host']
    elif network=='xhttp':
        mode=q.get('mode','auto')
        if mode not in ('auto','packet-up','stream-up','stream-one'):raise Unsupported('Unsupported XHTTP mode.')
        stream['xhttpSettings']={'path':q.get('path','/'),'mode':mode}
        if q.get('host'):stream['xhttpSettings']['host']=q['host']
        if q.get('extra'):
            try:extra=json.loads(q['extra'])
            except (ValueError,TypeError):raise ProfileError('Invalid XHTTP extra JSON.') from None
            if not isinstance(extra,dict) or len(q['extra'])>16384:raise ProfileError('Invalid XHTTP extra object.')
            stream['xhttpSettings']['extra']=extra
    if q.get('extra') and network!='xhttp':raise Unsupported('extra is supported only for XHTTP.')
    # Transport-specific fields must not disappear silently.
    for key, allowed in {'path':('ws','xhttp','httpupgrade'),'host':('ws','xhttp','httpupgrade'),'serviceName':('grpc',),'authority':('grpc',),'mode':('grpc','xhttp')}.items():
        if q.get(key) and network not in allowed: raise Unsupported('Transport-specific parameter cannot be applied to the selected transport; original retained.')
    if security!='reality' and any(q.get(k) for k in ('pbk','sid','spx')): raise Unsupported('REALITY parameters require REALITY security.')
    if security!='tls' and q.get('alpn'): raise Unsupported('ALPN is not applied by this adapter outside TLS.')
    from .transport_extensions import apply_extensions
    apply_extensions(stream,q)
    return {'tag':'proxy','protocol':p.protocol,'settings':settings,'streamSettings':stream}


def make_config(p, http_port=2080, socks_port=2081, stats_port=2082, bypass=False):
    ports=[http_port,socks_port,stats_port]
    if len(set(ports))!=3 or any(not 1024<=x<=65535 for x in ports): raise ProfileError('Choose three different local ports from 1024 to 65535.')
    ob=outbound(p)
    cfg={'log':{'loglevel':'error'},'inbounds':[
        {'tag':'http','listen':'127.0.0.1','port':http_port,'protocol':'http','settings':{}},
        {'tag':'socks','listen':'127.0.0.1','port':socks_port,'protocol':'socks','settings':{'udp':True}},
    ],'outbounds':[ob,{'tag':'direct','protocol':'freedom'}],
    'stats':{},'policy':{'system':{'statsOutboundUplink':True,'statsOutboundDownlink':True}},
    'metrics':{'tag':'metrics','listen':f'127.0.0.1:{stats_port}'}}
    if bypass:
        cfg['routing']={'rules':[{'type':'field','ip':['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','127.0.0.0/8','::1/128','fc00::/7','fe80::/10'],'outboundTag':'direct'}]}
    return cfg
