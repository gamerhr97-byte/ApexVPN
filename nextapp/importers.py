"""Manual configuration and local QR decoding; decoded links use the regular parser."""
import pathlib,warnings
from urllib.parse import quote,urlencode
from .profiles import ProfileError,parse_link

def manual_profile(values):
    protocol=values['protocol'];host=values['host'].strip()
    if protocol not in ('vless','trojan','ss'):raise ProfileError('Unsupported manual protocol.')
    if not host or any(c in host for c in '/?#@\r\n'):raise ProfileError('Enter a hostname or IP address without a URL or path.')
    if host.startswith('[') and host.endswith(']'):host=host[1:-1]
    try:port=int(values['port'])
    except (ValueError,TypeError):raise ProfileError('Enter a valid port.') from None
    if not 1<=port<=65535:raise ProfileError('Enter a port from 1 to 65535.')
    secret=values['secret']
    if not secret:raise ProfileError('Enter authentication credentials.')
    name=values.get('name','').strip() or protocol.upper()+' profile'
    if protocol=='ss':auth=quote(values.get('method','aes-128-gcm')+':'+secret,safe='');params={}
    else:
        auth=quote(secret,safe='');params={'type':values.get('transport','tcp'),'security':values.get('security','tls')}
        for field in ('sni','fp','pbk','sid','spx','flow','path','serviceName'):
            if values.get(field):params[field]=values[field]
        if protocol=='vless':params['encryption']=values.get('encryption') or 'none'
    authority='['+host+']' if ':' in host else host
    link=f'{protocol}://{auth}@{authority}:{port}'+('?' +urlencode(params,quote_via=quote) if params else '')+'#'+quote(name,safe='')
    return parse_link(link)

def decode_qr(path):
    path=pathlib.Path(path)
    if path.stat().st_size>16*1024*1024:raise ProfileError('QR image exceeds 16 MiB.')
    return decode_qr_bytes(path.read_bytes())

def decode_qr_bytes(data):
    import io
    if len(data)>16*1024*1024:raise ProfileError('QR image exceeds 16 MiB.')
    try:
        import zxingcpp
        from PIL import Image
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.width*source.height>16_000_000:raise ProfileError('QR image exceeds 16 megapixels.')
                image=source.convert('RGB')
                results=zxingcpp.read_barcodes(image,formats=zxingcpp.BarcodeFormat.QRCode)
        texts=list(dict.fromkeys(x.text.strip() for x in results if x.valid and x.text.strip()))
        if not texts:raise ProfileError('No readable QR code found. Choose a clear QR image or paste the link.')
        if len(texts)!=1:raise ProfileError('Multiple QR codes found. Choose an image with a single profile or subscription.')
        # Validate every QR before any import; never open an arbitrary encoded URL.
        from .profiles import parse_import
        for text in texts:
            if text.startswith('https://'):
                from urllib.parse import urlsplit
                u=urlsplit(text)
                if not u.hostname:raise ProfileError('Invalid HTTPS URL in QR code.')
                if u.username is not None or u.password is not None:
                    parse_import(text)  # explicitly credentialed HTTPS proxy
            else:parse_import(text)
        return texts
    except ProfileError:raise
    except ImportError:raise ProfileError('QR dependencies are missing. Use the complete 0.3.0 package or runtime update.') from None
    except Exception:raise ProfileError('Could not decode the image. No QR content was logged.') from None
