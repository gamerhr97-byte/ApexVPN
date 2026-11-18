"""Explicitly owned public Free sources; never infer ownership from a display name."""
import base64, copy, hashlib, html, json
from dataclasses import dataclass
from .profiles import ProfileError, parse_import, parse_link, b64
from .subscriptions import Subscription

FREE_GROUP='free'
PRESETS=(
 ('proxycollector','ProxyCollector','https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/master/sub/proxies.txt'),
 ('alirewa','Alirewa · 100','https://raw.githubusercontent.com/Alirewa/V2ray-Configs/main/sub1.txt'),
 ('patterniha','Patterniha','https://raw.githubusercontent.com/patterniha/Free-Configs/main/configs.txt'),
 ('mahsa','Mahsa','https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/main/app/sub.txt'),
)


def repair_ownership(subscriptions,profiles):
    """Only stable built-in IDs own Free membership; never classify by URL/name."""
    import uuid
    changed=False
    for key,name,url in PRESETS:
        ident='builtin-free-'+key
        entry=next((s for s in subscriptions if s.id==ident),None)
        if entry and entry.url!=url:
            personal=copy.deepcopy(entry);personal.id=uuid.uuid4().hex;personal.is_free=False;personal.source_key=''
            subscriptions.append(personal)
            for profile in profiles:
                if profile.subscription_id==ident:profile.subscription_id=personal.id
            entry.url=url;entry.name=name;entry.metadata={};entry.updated_at='';entry.status='unknown';entry.last_error='';changed=True
    owned={'builtin-free-'+key:key for key,_,_ in PRESETS}
    for sub in subscriptions:
        expected=sub.id in owned
        if sub.is_free!=expected or sub.source_key!=owned.get(sub.id,''):
            sub.is_free=expected;sub.source_key=owned.get(sub.id,'');changed=True
    return changed


def install_presets(subscriptions,settings):
    """Keep the Free feeds available; users clear their nodes, not the feeds."""
    changed=False
    if settings.get('disabled_free_sources'):
        settings['disabled_free_sources']=[]
        changed=True
    for key,name,url in PRESETS:
        ident='builtin-free-'+key
        entry=next((s for s in subscriptions if s.id==ident),None)
        if entry is None:
            subscriptions.append(Subscription(name,url,id=ident,is_free=True,source_key=key));changed=True
        elif not entry.is_free or entry.source_key!=key:
            entry.is_free=True;entry.source_key=key;changed=True
    if settings.get('free_catalog_version')!=2:settings['free_catalog_version']=2;changed=True
    return changed


def free_ids(subscriptions):
    return {s.id for s in subscriptions if s.is_free}


def keep_only_free(subscriptions, profiles):
    """One-time catalog cleanup; preserve local profiles and favorite provider entries."""
    free = free_ids(subscriptions)
    kept_profiles = []
    changed = False
    for profile in profiles:
        if not profile.subscription_id or profile.subscription_id in free:
            kept_profiles.append(profile)
        elif profile.favorite:
            profile.favorite_source_id = profile.subscription_id
            profile.subscription_id = ''
            kept_profiles.append(profile)
            changed = True
        else:
            changed = True
    kept_subscriptions = [item for item in subscriptions if item.id in free]
    changed = changed or len(kept_subscriptions) != len(subscriptions)
    if kept_profiles != profiles:
        profiles[:] = kept_profiles
    if kept_subscriptions != subscriptions:
        subscriptions[:] = kept_subscriptions
    return changed


def removable(profile):
    return profile.test_status in {'Failed','Timeout','Refused','Unsupported'} and profile.test_error not in {
        'UDP_PROTOCOL_USE_HTTPS','INTERNAL_ERROR','CORE_TIMEOUT','PROCESS_SUPERVISION','CORE_EXIT'}


def prune_failed(profiles,subscriptions,tested_ids,active_id=''):
    ids=free_ids(subscriptions)
    removed=[p for p in profiles if p.id in tested_ids and p.subscription_id in ids and p.id!=active_id and removable(p)]
    remove_ids={p.id for p in removed}
    return [p for p in profiles if p.id not in remove_ids],removed


def decode_mahsa(text):
    """Public Mahsa Free feed format; no Android account/authentication requests.

    Format independently implemented from the publicly documented AES-CBC feed.
    Keys here are public format constants, not user credentials. TLS stays strict.
    """
    from .public_feed_crypto import aes_cbc_decrypt
    digest=hashlib.md5(b'mvcfhjju5632gfsseu95642yhfhnhjhty68532gfg',usedforsecurity=False).hexdigest()
    key=(digest[:7]+digest[10:19]).encode()
    raw=base64.b64decode(''.join(text.split()),validate=True)
    document=json.loads(aes_cbc_decrypt(raw,key,b'lvcas56410c97lpb').decode('utf-8'))
    if not isinstance(document,dict):raise ProfileError('Mahsa public feed format changed; previous servers kept.')
    links=[]
    for carrier in ('mtn','mci'):
        entries=document.get(carrier,[])
        if not isinstance(entries,list):continue
        for entry in entries:
            if isinstance(entry,dict) and isinstance(entry.get('config'),str):
                links.append(html.unescape(entry['config'].strip()))
    if not links:raise ProfileError('Mahsa public feed returned no standard profiles.')
    return '\n'.join(dict.fromkeys(links))


def load_free_source(sub,proxy_port=None,cancel=None,fetch=None):
    """Tolerate individual malformed public entries, preserving every valid URI.

    Personal subscriptions retain the strict importer. Unknown URI parameters
    remain intact and are tested by the normal core serializer, never stripped.
    """
    from .network import fetch_subscription
    from .subscription_loader import subscription_url
    fetch=fetch or fetch_subscription
    if cancel is not None and cancel.is_set():raise ProfileError('Canceled')
    document=fetch(subscription_url(sub.url),proxy_port=proxy_port)
    text=document.strip().lstrip('\ufeff')
    if sub.source_key=='mahsa' and '://' not in text and not text.startswith(('{','[')):
        try:text=decode_mahsa(text)
        except Exception:raise ProfileError('Mahsa public feed could not be decoded. Previous profiles kept.') from None
    if text.startswith(('{','[')) or any(l.strip().startswith('proxies:') for l in text.splitlines()[:80]):
        profiles=parse_import(text);rejected=0
    else:
        if '://' not in text:
            try:text=b64(text).decode('utf-8')
            except Exception:raise ProfileError('Free source is not a standard subscription.') from None
        profiles=[];rejected=0;seen=set()
        for line in text.splitlines():
            if cancel is not None and cancel.is_set():raise ProfileError('Canceled')
            line=line.strip()
            if not line or line.startswith('#'):continue
            if line in seen:continue
            seen.add(line)
            if len(seen)>10000:raise ProfileError('Free source exceeds 10,000 entries.')
            try:profiles.append(parse_link(line))
            except ProfileError:rejected+=1
    if not profiles:raise ProfileError('Free source returned no importable profiles; previous servers kept.')
    metadata=dict(getattr(document,'metadata',{}))
    metadata['skipped_entries']=rejected
    return profiles,metadata,''
