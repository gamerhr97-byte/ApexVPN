import base64,json,pytest
from nextapp.profiles import *
UUID='11111111-1111-4111-8111-111111111111'
LINK=f'vless://{UUID}@example.com:443?type=tcp&security=reality&sni=example.com&pbk=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&sid=1234&fp=chrome&flow=xtls-rprx-vision'

def test_lossless_mlkem_and_plus():
    enc='mlkem768x25519plus.native.1rtt.ABC+DEF'
    p=parse_link(LINK+'&encryption='+enc)
    assert p.params['encryption']==enc
    assert p.original==LINK+'&encryption='+enc
    cfg=make_config(p)
    assert cfg['outbounds'][0]['settings']['vnext'][0]['users'][0]['encryption']==enc
    assert Profile(**json.loads(json.dumps(p.to_dict()))).original==p.original

def test_unknown_fields_not_silently_removed():
    p=parse_link(LINK+'&newCryptoField=secret-token')
    with pytest.raises(Unsupported) as err:make_config(p)
    assert 'secret-token' not in str(err.value)
    assert p.params['newCryptoField']=='secret-token'

@pytest.mark.parametrize('suffix',['&security=tls','&encryption=none&encryption=bad'])
def test_duplicates(suffix):
    with pytest.raises(ProfileError):parse_link(LINK+suffix)

def test_malformed_does_not_echo_credentials():
    with pytest.raises(ProfileError) as err:parse_link('vless://secret@server:notaport')
    assert 'secret' not in str(err.value)

def test_reality_required_and_sid():
    with pytest.raises(ProfileError):outbound(parse_link(f'vless://{UUID}@example.com?security=reality'))
    with pytest.raises(ProfileError):outbound(parse_link(LINK.replace('sid=1234','sid=zz')))

def test_unsupported_encryption_retained():
    p=parse_link(LINK+'&encryption=future-encryption')
    with pytest.raises(Unsupported):outbound(p)
    assert p.params['encryption']=='future-encryption'

def test_ss_sip002_and_legacy():
    auth=base64.urlsafe_b64encode(b'aes-128-gcm:secret').decode().rstrip('=')
    p=parse_link('ss://'+auth+'@example.com:8388#Test')
    assert p.secret=='secret' and outbound(p)['protocol']=='shadowsocks'
    raw=base64.urlsafe_b64encode(b'aes-128-gcm:secret@example.com:8388').decode()
    assert parse_link('ss://'+raw).host=='example.com'

def test_vmess_and_subscription():
    d={'v':'2','add':'example.com','port':'443','id':UUID,'aid':'0','net':'ws','tls':'tls','path':'/','host':'example.com'}
    link='vmess://'+base64.b64encode(json.dumps(d).encode()).decode()
    p=parse_import(base64.b64encode(link.encode()).decode())[0]
    assert outbound(p)['streamSettings']['wsSettings']['path']=='/'

def test_hysteria_stored_not_connected():
    p=parse_link('hy2://password@example.com:443#Test')
    assert p.protocol=='hysteria2'
    with pytest.raises(Unsupported):make_config(p)

def test_raw_config_never_silently_rewritten():
    data={'outbounds':[{'protocol':'freedom'}],'routing':{'domainStrategy':'AsIs'}}
    p=parse_import(json.dumps(data))[0]
    assert p.raw==data
    with pytest.raises(Unsupported):make_config(p)

def test_ports_and_tls_security():
    p=parse_link(LINK)
    with pytest.raises(ProfileError):make_config(p,2080,2080)
    with pytest.raises(Unsupported):make_config(parse_link(LINK+'&allowInsecure=1'))
    with pytest.raises(Unsupported):make_config(parse_link(f'vless://{UUID}@example.com?encryption=none'))

def test_unicode_ipv6():
    p=parse_link('trojan://abc@[::1]:443?security=tls#%D8%B3%D8%B1%D9%88%D8%B1')
    assert p.name=='سرور' and p.host=='::1'


def test_tcp_header_none_is_serialized_not_discarded():
    p=parse_link(LINK+'&headerType=none')
    cfg=make_config(p);stream=cfg['outbounds'][0]['streamSettings']
    assert stream['tcpSettings']=={'header':{'type':'none'}}
    assert p.params['headerType']=='none'
    p.params['headerType']='http'
    with pytest.raises(Unsupported,match='headerType'):make_config(p)


def test_reality_aliases_preserve_values_and_detect_conflicts():
    alias_link=LINK.replace('pbk=','publicKey=').replace('sid=','shortId=').replace('fp=','fingerprint=').replace('sni=','serverName=')
    p=parse_link(alias_link)
    result=make_config(p)['outbounds'][0]['streamSettings']['realitySettings']
    assert result['shortId']=='1234' and result['fingerprint']=='chrome'
    assert 'publicKey' in p.params and 'pbk' not in p.params
    with pytest.raises(Unsupported,match='Conflicting fields: pbk / publicKey'):
        make_config(parse_link(LINK+'&publicKey=different'))


def test_shared_parameter_report_omits_values_and_unlisted_keys():
    p=parse_link(LINK+'&headerType=none&ech=sensitive-value&private-token-key=private-token-value')
    with pytest.raises(Unsupported) as error:make_config(p)
    assert 'ech' in str(error.value)
    assert 'sensitive-value' not in str(error.value)
    assert 'private-token-key' not in str(error.value)
    shared=parameter_names(p)
    assert 'headerType' in shared and 'Unlisted field names withheld: 1' in shared
    assert 'private-token-key' not in shared and p.secret not in shared
    local=parameter_names(p,local=True)
    assert 'private-token-key' in local and 'private-token-value' not in local
