"""Lossless cs/fm/legacy fragment mapping, guarded by a matching core version."""
import copy,json,re
from .profiles import ProfileError,Unsupported

CS_NAMES={'TLS_AES_128_GCM_SHA256','TLS_AES_256_GCM_SHA384','TLS_CHACHA20_POLY1305_SHA256','TLS_RSA_WITH_RC4_128_SHA','TLS_RSA_WITH_3DES_EDE_CBC_SHA','TLS_RSA_WITH_AES_128_CBC_SHA','TLS_RSA_WITH_AES_256_CBC_SHA','TLS_RSA_WITH_AES_128_CBC_SHA256','TLS_RSA_WITH_AES_128_GCM_SHA256','TLS_RSA_WITH_AES_256_GCM_SHA384','TLS_ECDHE_ECDSA_WITH_RC4_128_SHA','TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA','TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA','TLS_ECDHE_RSA_WITH_RC4_128_SHA','TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA','TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA','TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA','TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256','TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256','TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256','TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384','TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256','TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384','TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256','TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256'}


def _range(value,maximum=65535):
    if type(value) is int:value=str(value)
    if not isinstance(value,str) or not re.fullmatch(r'\d{1,8}(?:-\d{1,8})?',value):raise ProfileError('Invalid fragment range.')
    parts=[int(x) for x in value.split('-')]
    if max(parts)>maximum or parts[0]>parts[-1]:raise ProfileError('Fragment range is out of bounds.')
    return parts


def apply_extensions(stream,q):
    if q.get('cs'):
        if stream.get('security')!='tls':raise Unsupported('cs requires TLS; original retained.')
        names=q['cs'].split(':')
        if not 1<=len(names)<=64 or any(x not in CS_NAMES for x in names):raise Unsupported('Unknown TLS cipher suite; original retained.')
        stream['tlsSettings']['cipherSuites']=q['cs']
    fm=None
    if q.get('fm'):
        if len(q['fm'])>32768:raise ProfileError('FinalMask is too large.')
        try:fm=json.loads(q['fm'])
        except (ValueError,TypeError):raise ProfileError('Invalid FinalMask JSON.') from None
        if not isinstance(fm,dict) or set(fm)!={'tcp'} or not isinstance(fm['tcp'],list) or not 1<=len(fm['tcp'])<=8:
            raise Unsupported('Only bounded TCP fragment masks are implemented; original retained.')
        for layer in fm['tcp']:
            if not isinstance(layer,dict) or set(layer)!={'type','settings'} or layer['type']!='fragment':raise Unsupported('Unmapped FinalMask layer retained.')
            v=layer['settings']
            if not isinstance(v,dict) or set(v)-{'packets','length','delay','lengths','delays','maxSplit'}:raise Unsupported('Unmapped fragment options retained.')
            packets=v.get('packets','tlshello')
            if packets!='tlshello' and not re.fullmatch(r'[1-9]\d?(?:-[1-9]\d?)?',packets):raise ProfileError('Invalid fragment packet selection.')
            lengths=v.get('lengths',[v.get('length',100)])
            delays=v.get('delays',[v.get('delay',0)])
            if not isinstance(lengths,list) or not isinstance(delays,list) or not 1<=len(lengths)<=32 or not 1<=len(delays)<=32:raise ProfileError('Invalid fragment arrays.')
            if 'length' in v and 'lengths' in v or 'delay' in v and 'delays' in v:raise Unsupported('Conflicting legacy/new fragment fields retained.')
            for value in lengths:_range(value)
            if _range(lengths[-1])[0]==0:raise ProfileError('Final fragment length cannot be zero.')
            for value in delays:_range(value,10000)
            _range(v.get('maxSplit','0'),4096)
    fragment=q.get('fragment','')
    if fragment:
        parts=fragment.split(',')
        if len(parts)!=4:raise ProfileError('Legacy fragment needs length,delay,packets,maxSplit.')
        if fm is not None:
            # PattN exports this unset legacy placeholder together with the actual
            # FinalMask layers. Preserve it in the profile; do not fragment twice.
            if parts!=['null','null','tlshello','0']:raise Unsupported('Conflicting fm and legacy fragment options retained.')
        else:
            length,delay,packets,maximum=parts
            if length=='null' or delay=='null':raise Unsupported('Unset legacy fragment requires an explicit fm mask.')
            _range(length);_range(delay,10000);_range(maximum,4096)
            if packets!='tlshello' and not re.fullmatch(r'[1-9]\d?(?:-[1-9]\d?)?',packets):raise ProfileError('Invalid fragment packets.')
            fm={'tcp':[{'type':'fragment','settings':{'packets':packets,'length':length,'delay':delay,'maxSplit':maximum}}]}
    if fm is not None:
        if stream.get('security')!='tls':raise Unsupported('This fragment adapter requires a verified TLS transport.')
        stream['finalmask']=copy.deepcopy(fm)
    return stream


def check_core_extensions(version,profile):
    if not any(profile.params.get(k) for k in ('cs','fm','fragment')):return
    match=re.search(rb'^Xray (\d+)\.(\d+)\.(\d+)',version)
    if not match or tuple(map(int,match.groups()))<(26,10,21):
        raise Unsupported('cs/fm fragment arrays require Xray 26.10.21 or newer. Select the bundled core; parameters were not removed.')
