import json
"""Bounded HTTPS subscription bundles with atomic, all-or-nothing refresh."""

import base64
from urllib.parse import urlsplit, urlunsplit, unquote

from .network import fetch_subscription, subscription_metadata
from .profiles import parse_import, ProfileError


def subscription_url(value):
    url = urlsplit(value.strip())
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ProfileError('Use a credential-free HTTPS subscription URL.')
    # A fragment is a local display name, never part of an HTTP download.
    return urlunsplit((url.scheme, url.netloc, url.path, url.query, ''))


def load_bundle(url, proxy_port=None, cancel=None, fetch=None):
    fetch = fetch or fetch_subscription
    seen = set()
    profiles = []
    metadata = {}
    title = ''
    budget = 0

    def visit(value, depth=0):
        nonlocal budget, metadata, title
        target = subscription_url(value)
        if target in seen:
            return
        if cancel is not None and cancel.is_set():
            raise ProfileError('Subscription update canceled.')
        if depth > 3 or len(seen) >= 16:
            raise ProfileError('Subscription bundle exceeds its nesting or link limit.')
        seen.add(target)
        document = fetch(target, proxy_port=proxy_port)
        budget += len(document.encode('utf-8'))
        if budget > 16 * 1024 * 1024:
            raise ProfileError('Subscription bundle exceeds 16 MiB.')
        text = document.strip().lstrip('\ufeff')
        yaml_document=any(line.strip().startswith('proxies:') for line in text.splitlines()[:80])
        if '://' not in text and not text.startswith(('{', '[')) and not yaml_document:
            try:
                text = base64.urlsafe_b64decode(text + '=' * (-len(text) % 4)).decode('utf-8')
            except Exception:
                raise ProfileError('Subscription is not a supported document.') from None
        if depth == 0:
            metadata = dict(getattr(document, 'metadata', {}))
            for line in text.splitlines():
                if line.lower().startswith('#subscription-userinfo:'):
                    metadata = {**subscription_metadata(line.split(':', 1)[1]), **metadata}
                elif line.lower().startswith('#profile-title:'):
                    title = line.split(':', 1)[1].strip()[:120]
        links = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('https://'):
                parsed = urlsplit(line)
                if parsed.username is None and parsed.password is None:
                    visit(line, depth + 1)
                else:
                    # Credentialed HTTPS proxy, not a nested subscription URL.
                    links.append(line)
            else:
                links.append(line)
        if links:
            # Complete JSON remains lossless, handled by the regular importer.
            profiles.extend(parse_import(text if yaml_document or text.startswith(('{', '[')) else '\n'.join(links)))
        if len(profiles) > 10000:
            raise ProfileError('Subscription bundle exceeds 10,000 profiles.')

    visit(url)
    unique = {(p.original,json.dumps(p.raw,sort_keys=True) if p.raw else ""): p for p in profiles}
    if not unique:
        raise ProfileError('Subscription returned no profiles. Previous profiles were kept.')
    return list(unique.values()), metadata, title
