# -*- coding: utf-8 -*-
"""
Tests for the localhost MoQ/WebSocket proxy (resources/lib/moq_proxy.py).
Covers URL builders, FLV tag encoding, and server lifecycle without network.
"""

import base64
import http.server
import os
import sys
import threading
import unittest
import urllib.parse
import urllib.request

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import conftest  # noqa: F401
import moq_proxy


class TestMoQProxy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from unittest import mock as _mock
        # Builders default to the configured port; force ephemeral ports so
        # the suite never collides with a live Kodi holding 50199 (its
        # service owns the port and answers our EADDRINUSE probe, which is
        # correct production behavior but wrong test isolation).
        cls._port_patch = _mock.patch.object(moq_proxy, 'get_proxy_port', return_value=0)
        cls._port_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls._port_patch.stop()
        moq_proxy.stop_server()

    def test_flv_tag_roundtrip(self):
        mgr = moq_proxy.StreamManager.__new__(moq_proxy.StreamManager)
        payload = b'\x01\x02\x03'
        tag = mgr.write_flv_tag(9, 1234, payload)
        # FLV tag: 1 (type) + 3 (len) + 3 (ts low) + 1 (ts ext) + 3 (stream id) + payload + 4 (prev size)
        self.assertEqual(tag[0], 9)
        self.assertEqual(int.from_bytes(tag[1:4], 'big'), len(payload))
        self.assertEqual(tag[11:11 + len(payload)], payload)
        self.assertEqual(int.from_bytes(tag[-4:], 'big'), 11 + len(payload))

    def test_build_ws_proxy_url_format(self):
        moq_proxy.stop_server()
        url = moq_proxy.build_ws_proxy_url(
            'wss://edge.example/subscribe?channelId=abc', origin='https://www.megatv.com', port=0
        )
        self.assertTrue(url.startswith('http://127.0.0.1:'))
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        self.assertIn('ws', qs)
        self.assertIn('origin', qs)
        decoded = base64.urlsafe_b64decode(qs['ws'][0]).decode('utf-8')
        self.assertEqual(decoded, 'wss://edge.example/subscribe?channelId=abc')
        moq_proxy.stop_server()

    def test_build_m3u8_proxy_url_format(self):
        moq_proxy.stop_server()
        url = moq_proxy.build_m3u8_proxy_url(
            'https://example.com/list.m3u8', headers={'User-Agent': 'UA', 'Referer': 'https://x/'}, port=0
        )
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        self.assertIn('stream', qs)
        decoded = base64.urlsafe_b64decode(qs['stream'][0]).decode('utf-8')
        self.assertTrue(decoded.startswith('https://example.com/list.m3u8|'))
        moq_proxy.stop_server()

    def test_server_starts_and_head_ok(self):
        port = moq_proxy.start_server(port=0)
        self.assertIsNotNone(port)
        actual = moq_proxy.g_proxy_server.server_address[1]
        req = urllib.request.Request(f'http://127.0.0.1:{actual}/probe.flv', method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get_content_type(), 'video/x-flv')
        # Idempotent second start returns same bound port
        self.assertEqual(moq_proxy.start_server(), actual)
        moq_proxy.stop_server()

    def test_eaddrinuse_reuses_service_port_without_threads(self):
        # The service binds the port at login; a resolver in another invoker
        # must reuse it without spawning threads of its own.
        moq_proxy.stop_server()

        class ForeignHandler(http.server.BaseHTTPRequestHandler):
            def do_HEAD(self):
                # Not our proxy: anything but 200 video/x-flv.
                self.send_error(404)

            def log_message(self, *args):
                pass

        foreign = http.server.HTTPServer(('', 0), ForeignHandler)
        port = foreign.server_address[1]
        serve_thread = threading.Thread(target=foreign.serve_forever, daemon=True)
        serve_thread.start()
        try:
            bound = moq_proxy.start_server(port=port)
            self.assertIsNone(bound)
            self.assertIsNone(moq_proxy.g_proxy_server)
            # No serve thread must have been created for the occupied port.
            self.assertIsNone(moq_proxy.g_proxy_thread)
        finally:
            foreign.shutdown()
            foreign.server_close()
            moq_proxy.stop_server()

    def test_eaddrinuse_probes_our_own_proxy(self):
        # If the occupying server answers like our FLV proxy, assume the
        # service owns it and hand back the port.
        moq_proxy.stop_server()
        owner = moq_proxy.ThreadedHttpServer(('', 0), moq_proxy.ProxyRequestHandler)
        port = owner.server_address[1]
        owner_thread = threading.Thread(target=owner.serve_forever, daemon=True)
        owner_thread.start()
        try:
            self.assertTrue(moq_proxy._probe_existing(port))
            bound = moq_proxy.start_server(port=port)
            self.assertEqual(bound, port)
            self.assertIsNone(moq_proxy.g_proxy_server)
            self.assertIsNone(moq_proxy.g_proxy_thread)
            self.assertEqual(moq_proxy.g_external_port, port)
        finally:
            owner.shutdown()
            owner.server_close()
            moq_proxy.stop_server()
        self.assertIsNone(moq_proxy.g_external_port)

    def test_stop_server_is_fast_and_resets_state(self):
        import time
        moq_proxy.stop_server()
        port = moq_proxy.start_server(port=0)
        self.assertIsNotNone(port)
        started = time.time()
        moq_proxy.stop_server()
        self.assertLess(time.time() - started, 2.0)
        self.assertIsNone(moq_proxy.g_proxy_server)
        self.assertIsNone(moq_proxy.g_proxy_thread)
        # Restartable after a stop.
        self.assertIsNotNone(moq_proxy.start_server(port=0))
        moq_proxy.stop_server()

    def test_head_content_type_per_path(self):
        port = moq_proxy.start_server(port=0)
        actual = moq_proxy.g_proxy_server.server_address[1]
        for path, expected in (
            ('/live.flv', 'video/x-flv'),
            ('/proxy.m3u8?stream=abcd', 'application/vnd.apple.mpegurl'),
        ):
            req = urllib.request.Request(f'http://127.0.0.1:{actual}{path}', method='HEAD')
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.headers.get_content_type(), expected)
        moq_proxy.stop_server()

    def test_service_entry_and_extension(self):
        service_py = os.path.join(conftest.REPO_ROOT, 'resources', 'service.py')
        self.assertTrue(os.path.exists(service_py))
        with open(service_py, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('run_service', src)
        addon_xml = os.path.join(conftest.REPO_ROOT, 'addon.xml')
        with open(addon_xml, encoding='utf-8') as f:
            xml = f.read()
        self.assertIn('xbmc.service', xml)
        self.assertIn('resources/service.py', xml)
    def test_dailymotion_geo_and_proxy(self):
        with open(os.path.join(conftest.PLUGINS_DIR, 'dailymotion.py'), encoding='utf-8') as f:
            src = f.read()
        self.assertIn('build_m3u8_proxy_url', src)
        self.assertIn('geo.dailymotion.com/videos/', src)
        self.assertIn("'priority'", src)
        self.assertNotIn('plugin.video.alivegr', src)
        self.assertNotIn('System.HasAddon', src)

    def test_dailymotion_live_resolve_via_geo(self):
        import re
        import importlib
        mod = importlib.import_module('dailymotion')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'DailymotionResolver'
        )
        inst = cls()
        m = re.search(inst.pattern, 'https://www.dailymotion.com/video/x7iulfv')
        self.assertIsNotNone(m)
        host, media_id = m.groups()[:2]
        resolved = inst.get_media_url(host, media_id)
        self.assertTrue(resolved.startswith('http://127.0.0.1:'))
        parsed = urllib.parse.urlparse(resolved)
        qs = urllib.parse.parse_qs(parsed.query)
        self.assertIn('stream', qs)
        payload = base64.urlsafe_b64decode(qs['stream'][0]).decode('utf-8')
        self.assertIn('cdndirector.dailymotion.com/cdn/manifest/', payload)
        self.assertIn('Referer=', payload)
        moq_proxy.stop_server()

    def test_dailymotion_live_uses_proxy_relay(self):
        import importlib
        import json as _json
        mod = importlib.import_module('dailymotion')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'DailymotionResolver'
        )
        manifest = 'https://cdndirector.dailymotion.com/cdn/manifest/video/xlive1.m3u8?sec=abc'

        class FakeResp:
            def __init__(self, payload):
                self.content = _json.dumps(payload)

        def make_inst(stream_type):
            inst = cls()

            class FakeNet:
                def http_GET(self, url, headers=None):
                    return FakeResp({'stream': {'stream_type': stream_type, 'url': manifest}})

            inst.net = FakeNet()
            return inst

        # Live and VOD alike go through the relay: Kodi's ffmpeg bridge drops
        # the `priority` header the live endpoint requires, so only the
        # server-side fetch (full header set) survives. The relay re-fetches
        # upstream per player request, keeping live playlists fresh.
        for stream_type in ('live', 'recorded'):
            with self.subTest(stream_type=stream_type):
                resolved = make_inst(stream_type).get_media_url('dailymotion.com', 'xlive1')
                self.assertIn('/proxy.m3u8?stream=', resolved)
                payload = base64.urlsafe_b64decode(
                    urllib.parse.parse_qs(urllib.parse.urlparse(resolved).query)['stream'][0]
                ).decode('utf-8')
                self.assertTrue(payload.startswith(manifest + '|'))
                self.assertIn('Referer=', payload)
        moq_proxy.stop_server()

    def test_bigbang_delegates_to_dailymotion(self):
        with open(os.path.join(conftest.PLUGINS_DIR, 'bigbang.py'), encoding='utf-8') as f:
            src = f.read()
        self.assertIn('DailymotionResolver', src)
        # No duplicated manifest logic anymore: issuance + relay live in dailymotion.py.
        self.assertNotIn('player/metadata', src)
        self.assertNotIn("quals.get('auto')", src)
        self.assertNotIn('plugin.video.alivegr', src)

    def test_eltube_auto_selects_owning_plugin(self):
        import importlib
        from unittest import mock
        from resolveurl.resolver import ResolverError
        mod = importlib.import_module('eltube')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'EltubeResolver'
        )

        class FakeResp:
            def __init__(self, content):
                self.content = content

        html = ('<html><body>'
                '<iframe src="https://voe.sx/e/abcdef1234"></iframe>'
                '</body></html>')

        def make_inst():
            inst = cls()

            class FakeNet:
                def http_GET(self, url, headers=None):
                    return FakeResp(html)

            inst.net = FakeNet()
            return inst

        # Owning plugin resolves the foreign iframe automatically.
        with mock.patch('resolveurl.resolve', return_value='https://cdn.voe.sx/video.mp4') as m:
            resolved = make_inst().get_media_url('eltube.gr', '123')
            self.assertEqual(resolved, 'https://cdn.voe.sx/video.mp4')
            m.assert_called_once_with('https://voe.sx/e/abcdef1234')

        # Nothing can resolve it: informative error naming the host.
        with mock.patch('resolveurl.resolve', return_value=False):
            with self.assertRaises(ResolverError) as ctx:
                make_inst().get_media_url('eltube.gr', '123')
            self.assertIn('voe.sx', str(ctx.exception))

    def test_bigbang_foreign_iframe_dispatch(self):
        import importlib
        from unittest import mock
        from resolveurl.resolver import ResolverError
        mod = importlib.import_module('bigbang')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'BigBangGR'
        )

        class FakeResp:
            def __init__(self, content):
                self.content = content

        def make_inst(html):
            inst = cls()

            class FakeNet:
                def http_GET(self, url, headers=None):
                    return FakeResp(html)

            inst.net = FakeNet()
            return inst

        yt_html = ('<html><body>'
                   '<iframe src="//www.youtube.com/embed/vOX21J-NeOU"></iframe>'
                   '</body></html>')
        # Non-DM iframe normalizes to https and goes through dispatch.
        with mock.patch('resolveurl.resolve', return_value='https://cdn.yt/x.mp4') as m:
            resolved = make_inst(yt_html).get_media_url('bigbang.gr', '841')
            self.assertEqual(resolved, 'https://cdn.yt/x.mp4')
            m.assert_called_once_with('https://www.youtube.com/embed/vOX21J-NeOU')

        # Dispatch result is wrapped as a tuple when subs was requested
        # (inner resolve runs without subs, so none to pass on).
        with mock.patch('resolveurl.resolve', return_value='https://cdn.yt/x.mp4'):
            stream_url, subtitles = make_inst(yt_html).get_media_url('bigbang.gr', '841', subs=True)
            self.assertEqual(stream_url, 'https://cdn.yt/x.mp4')
            self.assertEqual(subtitles, {})

        # Unresolvable iframe falls through to direct <video> source.
        mp4_html = ('<html><body><video width="560" controls>'
                    '<source src="https://www.tavideomas.com/kyriakos/bigbang/movies/mp4/kiklothimia.mp4">'
                    '</video></body></html>')
        with mock.patch('resolveurl.resolve', return_value=False):
            resolved = make_inst(mp4_html).get_media_url('bigbang.gr', '15')
            self.assertTrue(resolved.startswith(
                'https://www.tavideomas.com/kyriakos/bigbang/movies/mp4/kiklothimia.mp4|'))
            self.assertIn('User-Agent=', resolved)

        # hmf unpacks a 2-tuple whenever subs was requested: direct files
        # carry no subtitles, so expect (url, {}).
        with mock.patch('resolveurl.resolve', return_value=False):
            stream_url, subtitles = make_inst(mp4_html).get_media_url('bigbang.gr', '15', subs=True)
            self.assertTrue(stream_url.startswith('https://www.tavideomas.com/'))
            self.assertEqual(subtitles, {})

        # Nothing playable at all.
        with mock.patch('resolveurl.resolve', return_value=False):
            with self.assertRaises(ResolverError):
                make_inst('<html><body>no video here</body></html>').get_media_url('bigbang.gr', '9')

    def test_ytresolver_has_no_requests_dependency(self):
        import importlib
        importlib.import_module('youtube')
        loaded = [m for m in __import__('sys').modules
                  if m == 'requests' or m.startswith('requests.')
                  or m == 'urllib3' or m.startswith('urllib3.')]
        self.assertEqual(loaded, [])

    def test_yt_mpd_serve_and_rewrite(self):
        moq_proxy.stop_server()
        port = moq_proxy.start_server(port=0)
        actual = moq_proxy.g_proxy_server.server_address[1]
        vid = 'aqz-KE-bpKQ'
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<MPD><BaseURL>'
               'http://127.0.0.1:50152/youtube/stream?expire=1&amp;sig=ab+cd'
               '</BaseURL><BaseURL>https://rr1.googlevideo.com/videoplayback?x=1</BaseURL></MPD>')
        url = moq_proxy.serve_yt_mpd(vid, xml.encode('utf-8'))
        self.assertTrue(url.startswith(f'http://127.0.0.1:{actual}/yt/{vid}.mpd'))
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get_content_type(), 'application/dash+xml')
            body = resp.read().decode('utf-8')
        self.assertIn(f'http://127.0.0.1:{actual}/youtube/stream?expire=1&amp;sig=ab+cd', body)
        self.assertNotIn('127.0.0.1:50152', body)
        self.assertIn('https://rr1.googlevideo.com/videoplayback?x=1', body)
        # Unknown video id 404s.
        req = urllib.request.Request(f'http://127.0.0.1:{actual}/yt/abcdefghijk.mpd')
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail('expected HTTP 404')
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            e.close()
        moq_proxy.stop_server()

    def test_yt_stream_relay(self):
        from unittest import mock
        moq_proxy.stop_server()
        port = moq_proxy.start_server(port=0)
        actual = moq_proxy.g_proxy_server.server_address[1]

        def fake_fetch(url, headers, method='GET', timeout=20):
            self.assertTrue(url.startswith('https://h1.example/videoplayback?itag=22&sig=x'))
            self.assertEqual(method, 'POST')
            self.assertEqual(headers.get('Range'), 'bytes=0-99')
            return b'0123456789', {'Content-Type': 'video/mp4',
                                   'Content-Range': 'bytes 0-9/100'}

        with mock.patch.object(moq_proxy, '_fetch_upstream', side_effect=fake_fetch):
            req = urllib.request.Request(
                f'http://127.0.0.1:{actual}/youtube/stream?__host=h1.example&__path=/videoplayback'
                '&__method=POST&itag=22&sig=x&__headers=eyJBLiI6IEEiIH0%3D',
                headers={'Range': 'bytes=0-99'}, method='GET')
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 206)
                self.assertEqual(resp.headers.get('Content-Range'), 'bytes 0-9/100')
                self.assertEqual(resp.read(), b'0123456789')

        # Host failover: first host raises, second serves.
        calls = []

        def flaky_fetch(url, headers, method='GET', timeout=20):
            calls.append(url)
            if 'bad.example' in url:
                raise urllib.error.URLError('down')
            return b'data', {'Content-Type': 'video/mp4'}

        with mock.patch.object(moq_proxy, '_fetch_upstream', side_effect=flaky_fetch):
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{actual}/youtube/stream?__host=bad.example'
                    '&__host=good.example&__path=/videoplayback&itag=22',
                    timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.read(), b'data')
            self.assertEqual(len(calls), 2)

            # Second request: bad.example is memoized as failed, so good.example is tried first.
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{actual}/youtube/stream?__host=bad.example'
                    '&__host=good.example&__path=/videoplayback&itag=22',
                    timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.read(), b'data')
            self.assertEqual(len(calls), 3)
            self.assertTrue(calls[2].startswith('https://good.example/videoplayback'))

        moq_proxy.stop_server()

    def test_youtube_plugin_wiring(self):
        import importlib
        from unittest import mock
        mod = importlib.import_module('youtube')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'YouTubeGRResolver'
        )
        self.assertEqual(cls.name, 'YouTubeGR')
        self.assertEqual(cls._get_priority(), 80)
        self.assertTrue(cls._is_enabled())

        entry = {'url': 'http://127.0.0.1:50152/youtube/manifest/dash?file=aqz-KE-bpKQ.mpd',
                 'subtitles': [{'lang': 'en', 'url': 'https://example.com/en.vtt'}]}
        xml = ('<MPD><BaseURL>http://127.0.0.1:50152/youtube/stream?expire=1</BaseURL></MPD>')

        class FakeClient:
            def __init__(self, context=None):
                pass

            def load_stream_info(self, video_id=None, use_mpd=None, audio_only=None):
                self._seen = (video_id, use_mpd, audio_only)
                return [entry], {}

        with mock.patch.object(mod, 'YouTubePlayerClient', FakeClient), \
                mock.patch.object(mod, '_read_engine_mpd', return_value=xml.encode('utf-8')):
            inst = cls()
            resolved = inst.get_media_url('youtube.com', 'aqz-KE-bpKQ')
            self.assertIn('/yt/aqz-KE-bpKQ.mpd', resolved)
            with urllib.request.urlopen(resolved, timeout=5) as resp:
                body = resp.read().decode('utf-8')
            self.assertIn('/youtube/stream?expire=1', body)
            self.assertNotIn('127.0.0.1:50152', body)
            stream_url, subtitles = inst.get_media_url('youtube.com', 'aqz-KE-bpKQ', subs=True)
            self.assertEqual(subtitles, {'en': 'https://example.com/en.vtt'})
        moq_proxy.stop_server()

    def test_yt_mpd_disk_fallback_cross_interpreter(self):
        # The serving interpreter never sees the resolving interpreter's
        # module state: with an empty store, the handler must read the
        # engine-written file. Simulates service-side serving after a
        # router-side resolve by pointing the path helper at a real file.
        import tempfile
        from unittest import mock
        moq_proxy.stop_server()
        port = moq_proxy.start_server(port=0)
        actual = moq_proxy.g_proxy_server.server_address[1]
        vid = 'aqz-KE-bpKQ'
        xml = ('<MPD><BaseURL>http://127.0.0.1:50152/youtube/stream?expire=1</BaseURL></MPD>')
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, vid + '.mpd')
            with open(path, 'wb') as f:
                f.write(xml.encode('utf-8'))
            with mock.patch.object(moq_proxy, '_yt_mpd_path', return_value=path):
                with urllib.request.urlopen(
                        f'http://127.0.0.1:{actual}/yt/{vid}.mpd', timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    body = resp.read().decode('utf-8')
            self.assertIn(f'http://127.0.0.1:{actual}/youtube/stream?expire=1', body)
            self.assertNotIn('127.0.0.1:50152', body)
        moq_proxy.stop_server()

    def test_youtube_engine_full_ladder_settings(self):
        import importlib
        mod = importlib.import_module('youtube')
        ctx = mod._engine_context()
        settings = ctx.get_settings()
        self.assertIn('hfr', settings.stream_features())
        self.assertGreaterEqual(settings.mpd_video_qualities()[0]['nom_height'], 4320)

    def test_euronews_delegates_to_youtube(self):
        import importlib
        from unittest import mock
        from resolveurl.resolver import ResolverError
        mod = importlib.import_module('euronews')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'EuronewsGRResolver'
        )
        self.assertTrue(cls._is_enabled())

        class FakeResp:
            def __init__(self, content):
                self.content = content

        def make_inst(payload):
            inst = cls()

            class FakeNet:
                def http_GET(self, url, headers=None):
                    return FakeResp(payload)

            inst.net = FakeNet()
            return inst

        api = '{"videoId":"aqz-KE-bpKQ","other":1}'
        with mock.patch('youtube.YouTubeGRResolver') as yt:
            yt.return_value.get_media_url.return_value = 'http://127.0.0.1:1/yt/aqz-KE-bpKQ.mpd'
            resolved = make_inst(api).get_media_url('gr.euronews.com', 'api/live/data?locale=el')
            self.assertEqual(resolved, 'http://127.0.0.1:1/yt/aqz-KE-bpKQ.mpd')
            yt.return_value.get_media_url.assert_called_once_with(
                'youtube.com', 'aqz-KE-bpKQ', subs=False)

        with mock.patch('youtube.YouTubeGRResolver') as yt:
            yt.return_value.get_media_url.return_value = ('http://127.0.0.1:1/yt/x.mpd', {})
            resolved = make_inst(api).get_media_url('gr.euronews.com', 'api/live/data?locale=el', subs=True)
            self.assertEqual(resolved, ('http://127.0.0.1:1/yt/x.mpd', {}))
            yt.return_value.get_media_url.assert_called_once_with(
                'youtube.com', 'aqz-KE-bpKQ', subs=True)

        with self.assertRaises(ResolverError):
            make_inst('{"nope":true}').get_media_url('gr.euronews.com', 'api/live/data?locale=el')

    def test_euronews_player_shapes(self):
        import importlib
        import json as _json
        from unittest import mock
        mod = importlib.import_module('euronews')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'EuronewsGRResolver'
        )

        class FakeResp:
            def __init__(self, content):
                self.content = content

        def make_inst(payload):
            inst = cls()

            class FakeNet:
                def http_GET(self, url, headers=None):
                    return FakeResp(payload)

            inst.net = FakeNet()
            return inst

        # Dailymotion player shape delegates to DailymotionGR.
        dm_api = _json.dumps({'player': 'dailymotion', 'videoId': 'xar7s56'})
        with mock.patch('dailymotion.DailymotionResolver') as dm:
            dm.return_value.get_media_url.return_value = 'http://127.0.0.1:1/proxy.m3u8?stream=x'
            resolved = make_inst(dm_api).get_media_url('gr.euronews.com', 'api/live/data?locale=el')
            self.assertEqual(resolved, 'http://127.0.0.1:1/proxy.m3u8?stream=x')
            dm.return_value.get_media_url.assert_called_once_with(
                'dailymotion.com', 'xar7s56', subs=False)

        # Direct primary URL is returned with headers (subscribers get a tuple).
        direct_api = _json.dumps({'player': 'dailymotion', 'videoId': 'xar7s56',
                                  'videoPrimaryUrl': 'https://cdn-euronews.akamaized.net/live/x.m3u8?hdnea=abc'})
        resolved = make_inst(direct_api).get_media_url('gr.euronews.com', 'api/live/data?locale=el')
        self.assertTrue(resolved.startswith('https://cdn-euronews.akamaized.net/live/x.m3u8'))
        self.assertIn('User-Agent=', resolved)
        stream_url, subtitles = make_inst(direct_api).get_media_url(
            'gr.euronews.com', 'api/live/data?locale=el', subs=True)
        self.assertEqual(subtitles, {})

    def test_euronews_edition_hosts(self):
        import importlib
        import re
        mod = importlib.import_module('euronews')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'EuronewsGRResolver'
        )
        inst = cls()
        for url, host, media_id in (
            ('https://gr.euronews.com/api/live/data?locale=el', 'gr.euronews.com', 'api/live/data?locale=el'),
            ('https://fr.euronews.com/api/live/data?locale=fr', 'fr.euronews.com', 'api/live/data?locale=fr'),
            ('https://www.euronews.com/api/live/data?locale=en', 'euronews.com', 'api/live/data?locale=en'),
            ('https://es.euronews.com/api/live/data?locale=es', 'es.euronews.com', 'api/live/data?locale=es'),
        ):
            with self.subTest(url=url):
                m = re.search(inst.pattern, url)
                self.assertIsNotNone(m)
                self.assertEqual(m.groups()[:2], (host, media_id))

    def test_euronews_live_editions(self):
        import importlib
        import re
        mod = importlib.import_module('euronews')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'EuronewsGRResolver'
        )
        for url in ('https://gr.euronews.com/api/live/data?locale=el',
                    'https://fr.euronews.com/api/live/data?locale=fr'):
            with self.subTest(url=url):
                inst = cls()
                m = re.search(inst.pattern, url)
                self.assertIsNotNone(m)
                try:
                    resolved = inst.get_media_url(*m.groups()[:2])
                    self.assertTrue(resolved.startswith('https://'))
                except Exception as e:
                    if 'HTTP Error' in str(e) or '406' in str(e):
                        print(f"Skipping euronews test for {url} (network/server rejection): {e}")
                    else:
                        raise
        import moq_proxy
        moq_proxy.stop_server()

    def test_greekmovies_front_end_dispatch(self):
        import importlib
        import re
        from unittest import mock
        from resolveurl.resolver import ResolverError
        mod = importlib.import_module('greekmovies')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'GreekMoviesResolver'
        )
        m = re.search(cls.pattern, 'https://greek-movies.com/view.php?v=iXFXDc_Bz6pM-5Iw747KxQ')
        self.assertIsNotNone(m)

        class FakeResp:
            def __init__(self, content):
                self.content = content

        def make_inst(html):
            inst = cls()

            class FakeNet:
                def http_GET(self, url, headers=None):
                    return FakeResp(html)

            inst.net = FakeNet()
            return inst

        alpha_html = ('<html><body><a href="https://www.alphatv.gr/series/x/episode/1-s1-e1/">watch</a>'
                      '</body></html>')
        with mock.patch('resolveurl.resolve', return_value='https://cdn.example/v.mp4') as r:
            resolved = make_inst(alpha_html).get_media_url('greek-movies.com', 'iXFXDc_Bz6pM-5Iw747KxQ')
            self.assertEqual(resolved, 'https://cdn.example/v.mp4')
            r.assert_called_once_with('https://www.alphatv.gr/series/x/episode/1-s1-e1/')

        yt_html = ('<html><body><iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>'
                   '</body></html>')
        with mock.patch('resolveurl.resolve', return_value='https://cdn.yt/v.mp4') as r:
            resolved = make_inst(yt_html).get_media_url('greek-movies.com', 'iXFXDc_Bz6pM-5Iw747KxQ')
            self.assertEqual(resolved, 'https://cdn.yt/v.mp4')
            r.assert_called_once_with('https://www.youtube.com/embed/dQw4w9WgXcQ')

        # Subs callers always get a tuple.
        with mock.patch('resolveurl.resolve', return_value='https://cdn.yt/v.mp4'):
            stream_url, subtitles = make_inst(yt_html).get_media_url(
                'greek-movies.com', 'iXFXDc_Bz6pM-5Iw747KxQ', subs=True)
            self.assertEqual(subtitles, {})

        with self.assertRaises(ResolverError):
            make_inst('<html><body>no video here</body></html>').get_media_url(
                'greek-movies.com', 'iXFXDc_Bz6pM-5Iw747KxQ')

    def test_youtube_audio_only_picks_best(self):
        import importlib
        mod = importlib.import_module('youtube')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'YouTubeGRResolver'
        )
        entries = [
            {'url': 'https://rr1.googlevideo.com/vp?itag=140',
             'audio': {'bitrate': 128, 'codec': 'aac'}},
            {'url': 'https://rr1.googlevideo.com/vp?itag=251',
             'audio': {'bitrate': 160, 'codec': 'opus'},
             'subtitles': [{'lang': 'en', 'url': 'https://example.com/en.vtt'}]},
            {'url': 'https://rr1.googlevideo.com/vp?itag=134',
             'audio': {'bitrate': 0, 'codec': ''},
             'video': {'height': 360, 'codec': 'avc1'}},
        ]

        class FakeClient:
            def __init__(self, context=None):
                pass

            def load_stream_info(self, video_id=None, use_mpd=None, audio_only=None):
                self._seen = (video_id, use_mpd, audio_only)
                return list(entries), {}

        from unittest import mock
        with mock.patch.object(mod, 'YouTubePlayerClient', FakeClient):
            inst = cls()
            resolved = inst.get_media_url('youtube.com', 'aqz-KE-bpKQ', audio_only=True)
            self.assertTrue(resolved.startswith('https://rr1.googlevideo.com/vp?itag=251'))
            self.assertIn('User-Agent=', resolved)
            self.assertNotIn('127.0.0.1', resolved)
            stream_url, subtitles = inst.get_media_url(
                'youtube.com', 'aqz-KE-bpKQ', subs=True, audio_only=True)
            self.assertEqual(subtitles, {'en': 'https://example.com/en.vtt'})

    def test_youtube_audio_only_live(self):
        import importlib
        mod = importlib.import_module('youtube')
        cls = next(
            c for n, c in vars(mod).items()
            if isinstance(c, type) and c.__name__ == 'YouTubeGRResolver'
        )
        resolved = cls().get_media_url('youtube.com', 'aqz-KE-bpKQ', audio_only=True)
        self.assertIn('/youtube/stream', resolved)
        self.assertTrue(resolved.startswith('http://127.0.0.1:'))

    def test_no_legacy_shims(self):
        with open(os.path.join(conftest.REPO_ROOT, 'resources', 'lib', 'moq_proxy.py'), encoding='utf-8') as f:
            src = f.read()
        for leftover in ('LEGACY_ADDON_ID', 'ensure_proxy_started', 'useragents', 'mega.flv', 'plugin.video.alivegr'):
            self.assertNotIn(leftover, src)

    def test_mega_vindral_use_proxy_builder(self):
        for mod_name in ('mega', 'vindral'):
            with self.subTest(plugin=mod_name):
                with open(os.path.join(conftest.PLUGINS_DIR, f'{mod_name}.py'), encoding='utf-8') as f:
                    src = f.read()
                self.assertIn('build_ws_proxy_url', src)
                self.assertNotIn('plugin.video.alivegr', src)
                self.assertNotIn('System.HasAddon', src)

    def test_youtube_standalone_context_codecs(self):
        from ytresolver.kodion.context.standalone import StandaloneContext
        # Default with no video_codecs specified: all codecs present
        ctx_default = StandaloneContext()
        caps_default = ctx_default.inputstream_adaptive_capabilities()
        self.assertIn('avc1', caps_default)
        self.assertIn('vp9', caps_default)
        self.assertIn('vp9.2', caps_default)
        self.assertIn('av01', caps_default)
        self.assertTrue(ctx_default.inputstream_adaptive_capabilities('avc1'))
        self.assertTrue(ctx_default.inputstream_adaptive_capabilities('vp9'))

        # Restrict to avc1 only
        ctx_avc1 = StandaloneContext(video_codecs=['avc1'])
        caps_avc1 = ctx_avc1.inputstream_adaptive_capabilities()
        self.assertIn('avc1', caps_avc1)
        self.assertNotIn('vp9', caps_avc1)
        self.assertNotIn('vp9.2', caps_avc1)
        self.assertNotIn('av01', caps_avc1)
        self.assertTrue(ctx_avc1.inputstream_adaptive_capabilities('avc1'))
        self.assertFalse(ctx_avc1.inputstream_adaptive_capabilities('vp9'))

        # Restrict to vp9: both vp9 and vp9.2 are enabled
        ctx_vp9 = StandaloneContext(video_codecs=['vp9'])
        caps_vp9 = ctx_vp9.inputstream_adaptive_capabilities()
        self.assertIn('vp9', caps_vp9)
        self.assertIn('vp9.2', caps_vp9)
        self.assertNotIn('avc1', caps_vp9)
        self.assertNotIn('av01', caps_vp9)

    def test_youtube_get_video_codecs(self):
        from unittest import mock
        import importlib
        mod = importlib.import_module('youtube')
        # Default when setting returns empty or error
        with mock.patch('kodi_six.xbmcaddon.Addon.getSetting', return_value=''):
            self.assertEqual(mod._get_video_codecs(), ['avc1'])
        # Multi-selection parsed correctly
        with mock.patch('kodi_six.xbmcaddon.Addon.getSetting', return_value='avc1,vp9'):
            self.assertEqual(mod._get_video_codecs(), ['avc1', 'vp9'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
