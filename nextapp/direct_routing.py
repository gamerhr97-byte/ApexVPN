"""Validated direct exceptions for the pinned Xray core; no drivers or polling."""

import ipaddress
import re
from urllib.parse import urlsplit


def _lines(text):
    if not isinstance(text, str) or len(text) > 4096:
        raise ValueError('Direct exception list is too long (maximum 4096 characters).')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 64:
        raise ValueError('Use at most 64 direct exceptions per list.')
    return lines


def domains(text):
    """Suffix matches include the apex, never a substring of another hostname."""
    result = []
    for line in _lines(text):
        if '://' in line:
            parsed = urlsplit(line)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Enter a domain or an HTTP/HTTPS website URL without credentials.')
            try:
                parsed.port
            except ValueError:
                raise ValueError('Invalid website port.') from None
            host = parsed.hostname
        else:
            host = line
            if any(c in host for c in '/?#@:*\\'):
                raise ValueError('Enter a domain or an HTTP/HTTPS website URL without credentials.')
        host = host.rstrip('.').lower()
        try:
            host = host.encode('idna').decode('ascii')
        except UnicodeError:
            raise ValueError('Invalid direct domain. Enter a domain such as example.ir.') from None
        labels = host.split('.')
        if (len(host) > 253 or len(labels) < 2 or
                any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                    for label in labels)):
            raise ValueError('Enter one domain or HTTP/HTTPS website URL per line; wildcards are not supported.')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError('Enter a domain name, not an IP address.')
        if host not in result:
            result.append(host)
    return result


def applications(text):
    """Only exact Windows EXE paths or EXE names; no folder-wide exceptions."""
    result = []
    for line in _lines(text):
        value = line.replace('\\', '/')
        absolute = bool(re.match(r'^[A-Za-z]:/', value))
        if (value.rsplit('/', 1)[-1].lower() == '.exe' or not value.lower().endswith('.exe') or len(value) > 512 or
                any(ord(c) < 32 or c in '<>"|?*' for c in value) or
                (':' in value and (not absolute or ':' in value[2:])) or
                (not absolute and '/' in value) or
                any(part in ('', '.', '..') for part in value.split('/'))):
            raise ValueError('Use an EXE name (game.exe) or its full Windows path, one per line.')
        # Xray matches names without the .exe suffix; preserve path spelling/case.
        match = value if absolute else value[:-4]
        if match not in result:
            result.append(match)
    return result


def apply_exceptions(config, settings):
    """Health, exit-IP and service checks remain proxy-only ahead of exceptions."""
    custom = domains(settings.get('direct_domains', ''))
    apps = applications(settings.get('direct_apps', ''))
    if not settings.get('direct_enabled', False):
        return config
    suffixes = (['ir'] if settings.get('direct_ir', True) else []) + custom
    rules = []
    if suffixes:
        rules.append({'type': 'field', 'domain': ['domain:' + d for d in suffixes],
                      'outboundTag': 'direct'})
    if apps:
        rules.append({'type': 'field', 'process': apps, 'outboundTag': 'direct'})
    if rules:
        config.setdefault('routing', {}).setdefault('rules', [])[:0] = rules
        for inbound in config['inbounds']:
            inbound['sniffing'] = {'enabled': True, 'destOverride': ['http', 'tls', 'quic'],
                                   'routeOnly': True}
    return config


def protect_checks(config, settings):
    if not config.get('routing', {}).get('rules'):
        return config
    from .service_checks import SERVICES

    urls = [settings[k] for k in ('https_url', 'http_url')]
    urls += ['https://api.ipify.org', 'https://api.country.is', 'https://api.ipapi.is']
    urls += [service.url for service in SERVICES]
    forced = []
    for url in urls:
        host = urlsplit(url).hostname
        if not host:
            raise ValueError('Verification endpoint requires a hostname.')
        rule = {'type': 'field', 'outboundTag': 'proxy'}
        try:
            address = ipaddress.ip_address(host)
            rule['ip'] = [str(address) + ('/32' if address.version == 4 else '/128')]
        except ValueError:
            rule['domain'] = ['full:' + host]
        if rule not in forced:
            forced.append(rule)
    config['routing']['rules'][:0] = forced
    return config


def check_process_core(version_output, settings):
    """Older Xray versions may ignore unknown JSON keys instead of rejecting them."""
    if not settings.get('direct_enabled') or not applications(settings.get('direct_apps', '')):
        return
    match = re.search(rb'^Xray (\d+)\.(\d+)\.(\d+)', version_output)
    if not match or tuple(map(int, match.groups())) < (26, 3, 27):
        from .profiles import Unsupported
        raise Unsupported('Application exceptions require Xray 26.3.27 or newer. Select the bundled core in Settings 3, or remove application exceptions.')


def windows_bypass(settings):
    """WinINET clients go directly without entering the local core at all."""
    entries = ['<local>']
    if settings.get('direct_enabled', True):
        if settings.get('direct_ir', True):
            entries.append('*.ir')
        for host in domains(settings.get('direct_domains', '')):
            entries.extend((host, '*.' + host))
    result = ';'.join(dict.fromkeys(entries))
    if len(result) > 16384:
        raise ValueError('Windows direct exception list is too long.')
    return result
