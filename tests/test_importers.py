import pathlib,pytest
from nextapp.importers import manual_profile,decode_qr
from nextapp.profiles import make_config,ProfileError

def test_manual_reality_fields_and_encryption_are_preserved():
    enc='mlkem768x25519plus.native.1rtt.test+value'
    p=manual_profile({'protocol':'vless','host':'2001:db8::1','port':'443','secret':'11111111-1111-4111-8111-111111111111','name':'نام','security':'reality','pbk':'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA','sid':'1234','sni':'example.com','fp':'chrome','flow':'xtls-rprx-vision','encryption':enc})
    assert p.host=='2001:db8::1' and p.name=='نام' and p.params['encryption']==enc
    assert make_config(p)['outbounds'][0]['settings']['vnext'][0]['users'][0]['encryption']==enc


def test_manual_ss_and_invalid_host():
    p=manual_profile({'protocol':'ss','host':'example.com','port':8388,'secret':'p:a+ss','name':'local','method':'aes-128-gcm'})
    assert p.secret=='p:a+ss' and p.params['method']=='aes-128-gcm'
    with pytest.raises(ProfileError):manual_profile({'protocol':'trojan','host':'https://example.com/path','port':443,'secret':'secret'})


def test_real_qr_decoding_and_invalid_qr_safety(tmp_path):
    import zxingcpp
    from PIL import Image
    link='trojan://test-secret@example.com:443?security=tls#Local'
    bitmap=zxingcpp.write_barcode(zxingcpp.BarcodeFormat.QRCode,link,400,400)
    pixels=memoryview(bitmap);image=Image.frombytes('L',(pixels.shape[1],pixels.shape[0]),pixels.tobytes());path=tmp_path/'qr.png';image.save(path)
    assert decode_qr(path)==[link]
    bitmap=zxingcpp.write_barcode(zxingcpp.BarcodeFormat.QRCode,'file:///private-data',400,400)
    pixels=memoryview(bitmap);Image.frombytes('L',(pixels.shape[1],pixels.shape[0]),pixels.tobytes()).save(path)
    with pytest.raises(ProfileError):decode_qr(path)
    Image.new('RGB',(200,200),'white').save(path)
    with pytest.raises(ProfileError,match='No readable QR'):decode_qr(path)
