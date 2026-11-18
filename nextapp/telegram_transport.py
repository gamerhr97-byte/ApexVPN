"""Telegram SOCKS links are reusable; MTProto is not a general TCP/UDP tunnel."""
from urllib.parse import urlsplit

MTPROTO_MESSAGE='MTProto is Telegram-only. Use a SOCKS5 or VPN server for Apex VPN; renaming this link cannot convert its protocol.'

def is_telegram_proxy_link(text):
    if '\n' in text.strip():return False
    try:
        u=urlsplit(text.strip())
        return (u.scheme=='tg' and u.netloc in {'proxy','socks'}) or (u.scheme=='https' and u.netloc.lower() in {'t.me','telegram.me'} and u.path in {'/proxy','/socks'})
    except ValueError:return False

def as_profile(text):
    from .settings_services import parse_telegram
    from .profiles import Profile,Unsupported,ProfileError
    try:proxy=parse_telegram(text)
    except ValueError as error:raise ProfileError(str(error)) from None
    if proxy.kind!='SOCKS5':raise Unsupported(MTPROTO_MESSAGE)
    return Profile('Telegram SOCKS5','socks5',proxy.server,proxy.port,proxy.password,
                   {'username':proxy.user} if proxy.user else {},original=text.strip())
