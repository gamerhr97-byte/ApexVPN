"""Dependency-free smoke/regression tests for the 0.10.1 logic changes.

Run: python tools/check_v0101.py. Does not execute Qt/Windows or a real Xray core.
"""
from pathlib import Path
import importlib, sys, types, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nextapp.profiles import Profile, ProfileError, Unsupported, parse_link, outbound
from nextapp.subscriptions import reconcile
from nextapp.ranking import rank

# In a source-only environment Qt is missing; just the pure classifier is tested.
try:
    from nextapp.service_checks import Service, classify_status, probe_service
except ImportError:
    qt = types.ModuleType('PySide6')
    core = types.ModuleType('PySide6.QtCore')
    core.QObject = type('QObject', (), {})
    core.Signal = lambda *args, **kwargs: None
    sys.modules['PySide6'] = qt
    sys.modules['PySide6.QtCore'] = core
    from nextapp.service_checks import Service, classify_status, probe_service


class ChangeTests(unittest.TestCase):
    def test_region_specific_marker(self):
        gemini = Service('gemini', 'Gemini', 'https://gemini.google.com/app', '', '')
        result = classify_status(gemini, 200, b'Gemini is not available in your country')
        self.assertEqual(result, ('limited', 'Explicit country restriction on public page', 'blocked'))
        self.assertEqual(classify_status(gemini, 200, b'<h1>Gemini login</h1>')[2], 'not_observed')
        self.assertEqual(classify_status(gemini, 403)[2], 'unknown')

    def test_antibot_is_not_false_red_cross(self):
        service = Service('chatgpt', 'ChatGPT', 'https://chatgpt.com/', '', '')
        for status in (302, 401, 403, 404, 429, 503):
            self.assertEqual(classify_status(service, status)[0], 'limited')
        self.assertEqual(classify_status(service, 200)[0], 'ok')

    def test_explicit_route_selection(self):
        from unittest.mock import patch
        service = Service('chatgpt', 'ChatGPT', 'https://chatgpt.com/', '', '')
        created = []
        class Fake:
            def __init__(self, host, port, **kwargs):
                self.host, self.port, self.tunnel = host, port, None
                created.append(self)
            def set_tunnel(self, host, port): self.tunnel = (host, port)
            def request(self, method, path, headers): pass
            def getresponse(self):
                return types.SimpleNamespace(status=200)
            def close(self): pass
        with patch('nextapp.service_checks.http.client.HTTPSConnection', Fake):
            self.assertEqual(probe_service(service, None).state, 'ok')
            self.assertEqual(probe_service(service, 20080).state, 'ok')
        self.assertEqual((created[0].host, created[0].tunnel), ('chatgpt.com', None))
        self.assertEqual((created[1].host, created[1].port), ('127.0.0.1', 20080))
        self.assertEqual(created[1].tunnel, ('chatgpt.com', 443))

    def test_new_xray_proxy_serializers(self):
        for link, kind, tls in (
            ('socks5://alice:secret@example.com:1080#S5', 'socks', False),
            ('http://alice:secret@example.com:3128#HTTP', 'http', False),
            ('https://alice:secret@example.com:443#HTTPS', 'http', True),
        ):
            p = parse_link(link)
            obj = outbound(p)
            self.assertEqual(obj['protocol'], kind)
            self.assertEqual(obj['settings']['user'], 'alice')
            self.assertEqual(obj['settings']['pass'], 'secret')
            self.assertEqual(obj.get('streamSettings', {}).get('security') == 'tls', tls)
        self.assertEqual(parse_link('socks4://example.com:1080').protocol, 'socks4')

    def test_nested_subscription_distinguishes_https_proxy(self):
        from nextapp.subscription_loader import load_bundle
        from nextapp.network import SubscriptionText
        root = 'https://example.invalid/subscription'
        text = ('https://alice:secret@proxy.example:443#protected\n'
                'socks5://user:pw@socks.example:1080#socks\n')
        result, _, _ = load_bundle(root, fetch=lambda url, proxy_port=None:
                                   SubscriptionText(text))
        self.assertEqual([p.protocol for p in result], ['https', 'socks5'])

    def test_stars_https_rank_and_persistence(self):
        def p(name, latency, method='HTTPS', status='Verified', favorite=False, gemini=False):
            item = Profile(name, 'vless', 'example.com', 443,
                           favorite=favorite, gemini_ok=gemini,
                           latency=latency, test_method=method, test_status=status)
            return item
        a = p('unstarred', 15)
        b = p('starred', 170, favorite=True)
        c = p('two-stars', 300, favorite=True, gemini=True)
        d = p('ping-only', 1, method='TCP', status='Reachable')
        self.assertEqual([x.name for x in sorted([a, b, c, d], key=rank)],
                         ['two-stars', 'starred', 'unstarred', 'ping-only'])
        old = p('source', 200, favorite=True, gemini=True)
        old.subscription_id = 'sub'
        old.original = 'vless://test'
        update = p('source', None)
        update.original = old.original
        result, ident = reconcile([old], [update], 'sub', old.id)
        self.assertTrue(result[0].gemini_ok)
        self.assertTrue(result[0].favorite)
        self.assertEqual(ident, old.id)


if __name__ == '__main__':
    unittest.main(verbosity=2)
