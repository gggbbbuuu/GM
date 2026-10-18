# -*- coding: utf-8 -*-
"""
ResolveURL PluginsGR Test Suite
Validates registration, patterns, and stream resolution across all Greek resolvers.
"""

import glob
import importlib
import inspect
import os
import re
import sys
import unittest

# Add current directory to sys.path so conftest is reliably found
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

# Import harness to set up sys.path and mock Kodi modules
import conftest  # noqa: F401
from resolveurl.resolver import ResolveUrl, ResolverError


class TestPluginsGR(unittest.TestCase):
    """Test suite for PluginsGR resolvers."""

    @classmethod
    def setUpClass(cls):
        cls.plugins_dir = os.path.join(conftest.REPO_ROOT, 'resources', 'plugins')
        cls.plugin_files = sorted(glob.glob(os.path.join(cls.plugins_dir, '*.py')))

    def _get_resolver_class(self, module_name):
        mod = importlib.import_module(module_name)
        fallback = None
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if inspect.isclass(attr) and issubclass(attr, ResolveUrl) and attr is not ResolveUrl:
                if getattr(attr, '__module__', None) == mod.__name__:
                    return attr
                if fallback is None and attr.__name__.endswith('Resolver'):
                    fallback = attr
        return fallback

    def test_all_plugins_import_and_instantiate(self):
        """Ensure all plugin scripts define a valid ResolveUrl subclass that can be instantiated."""
        found_resolvers = []
        for file_path in self.plugin_files:
            mod_name = os.path.basename(file_path)[:-3]
            if mod_name == '__init__':
                continue
            with self.subTest(plugin=mod_name):
                resolver_cls = self._get_resolver_class(mod_name)
                self.assertIsNotNone(resolver_cls, f"No ResolveUrl subclass found in {mod_name}.py")
                instance = resolver_cls()
                self.assertTrue(bool(instance.name), f"{mod_name} must define a 'name'")
                self.assertTrue(bool(instance.domains), f"{mod_name} must define 'domains'")
                self.assertTrue(bool(instance.pattern), f"{mod_name} must define a regex 'pattern'")
                found_resolvers.append(resolver_cls.__name__)

        self.assertGreaterEqual(len(found_resolvers), 20)

    def test_pattern_matching_live_and_vod(self):
        """Test URL pattern regexes against known test vectors."""
        test_vectors = {
            'aeolostv': 'https://aeolos.tv/live',
            'alphacy': 'https://www.alphacyprus.com.cy/live',
            'alphagr': 'https://www.alphatv.gr/live/',
            'anacon': 'https://anacon.org/app/chans/gr/atticatvimage.php',
            'ant1cy': 'https://www.ant1live.com/webtv/live',
            'ant1gr': 'https://www.antenna.gr/watch/12345/some-title',
            'bigbang': 'https://www.bigbang.gr/movie.asp?id=1',
            'dailymotion': 'https://www.dailymotion.com/video/x7tgad0',
            'ert': 'https://www.ertflix.gr/#/details/ERT_M002339',
            'euronews': 'https://gr.euronews.com/api/live/data?locale=el',
            'grnet': 'https://diavlos-cache.cnt.grnet.gr/app/index.html#/el/embed/room/6015',
            'ioniantv': 'https://ioniantv.gr/live',
            'kick': 'https://kick.com/madtvgreece',
            'mega': 'https://www.megatv.com/live/',
            'omegacy': 'https://www.omegatv.com.cy/live/',
            'opentv': 'https://www.tvopen.gr/live',
            'playlistgr': 'https://playlist.gr/ajax.php?action=get_video&id=eJujqsAR2i1kP',
            'rik': 'https://tv.rik.cy/live-tv/rik-sat/',
            'sigma': 'https://www.sigmatv.com/live',
            'skai': 'https://www.skai.gr/tv/live',
            'star': 'https://www.star.gr/tv/live-stream',
            'tv100': 'https://www.tv100.gr/live',
            'vindral': 'https://lb.cdn.vindral.com/api/v4/connect?channelId=alteregomedia_megatv1_ci_6cc490c7-e5c6-486b-acf0-9bb9c20fa670',
        }

        for mod_name, sample_url in test_vectors.items():
            with self.subTest(plugin=mod_name, url=sample_url):
                resolver_cls = self._get_resolver_class(mod_name)
                self.assertIsNotNone(resolver_cls)
                inst = resolver_cls()
                m = re.search(inst.pattern, sample_url)
                self.assertIsNotNone(
                    m,
                    f"Sample URL {sample_url} did not match pattern '{inst.pattern}' for {mod_name}",
                )

    def test_star_live_and_trailing_slash(self):
        """Verify Star resolver pattern supports URLs with and without trailing slashes."""
        resolver_cls = self._get_resolver_class('star')
        inst = resolver_cls()
        for url in ['https://www.star.gr/tv/live-stream', 'https://www.star.gr/tv/live-stream/']:
            m = re.search(inst.pattern, url)
            self.assertIsNotNone(m, f"Star pattern failed for {url}")
            host, media_id = m.groups()[:2]
            self.assertEqual(media_id.rstrip('/'), 'tv/live-stream')

    def test_star_vod_patterns(self):
        """Verify Star resolver matches the rebuilt site's /video/ page URLs."""
        resolver_cls = self._get_resolver_class('star')
        inst = resolver_cls()
        urls = [
            'https://www.star.gr/video/cash-or-trash/730515/cash-or-trash-15102026',
            'https://www.star.gr/video/eidiseis/ellada/730245/kypselh-blabes-se-20-ktiria',
            'https://www.star.gr/video/cash-or-trash',
        ]
        for url in urls:
            m = re.search(inst.pattern, url)
            self.assertIsNotNone(m, f"Star pattern failed for {url}")

    def test_star_vod_kwik_extraction(self):
        """Verify Star VOD resolves the kwik playerConfig m3u8 and follows its redirect."""
        from unittest import mock

        import star

        page = (
            '<script>(function () { const playerConfig = { IsLiveStream: false,'
            ' mediaid: "Npl5pN9gYTAKlTd8UAkp2A", sources: [ {'
            ' file: "https://deliver2.siliconweb.com/kwik/star.m3u8?key=Npl5pN9gYTAKlTd8UAkp2A"'
            ' } ] }; })();</script>'
        )
        inst = star.StarResolver()

        class FakeResp:
            content = page

            def get_redirect_url(self):
                return ('https://starmotionvod.siliconweb.com/starvod/smil:itwfcdn/'
                        'starmotionvod/2858445-572Z2G5FhNhN4KP-v-1.smil/playlist.m3u8')

        with mock.patch.object(inst.net, 'http_GET', return_value=FakeResp()):
            resolved = inst.get_media_url('star.gr', 'video/cash-or-trash/730515/x')

        self.assertIn('playlist.m3u8', resolved)

    def test_star_vod_youtube_delegation(self):
        """Star YouTube clips delegate to YouTubeGR, novasports-style, never the youtube addon."""
        from unittest import mock

        import star

        pages = {
            'iframe': ('<html><iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ">'
                       '</iframe><iframe src="https://x.grxchange.gr/videoad/30277"></iframe></html>'),
            'legacy': '<html><div data-video="dQw4w9WgXcQ"></div></html>',
        }

        for name, page in pages.items():
            with self.subTest(page=name):
                inst = star.StarResolver()

                class FakeResp:
                    content = page

                with mock.patch.object(inst.net, 'http_GET', return_value=FakeResp()), \
                        mock.patch.object(
                            star.StarResolver, '_resolve_youtube',
                            return_value=('https://yt/videoplayback', {})) as delegated:
                    resolved = inst.get_media_url(
                        'star.gr', 'tv/psychagogia/old-show/old-clip', subs=True)

                delegated.assert_called_once_with('dQw4w9WgXcQ', True)
                self.assertEqual(resolved, ('https://yt/videoplayback', {}))

    def test_mega_vod_patterns(self):
        """Mega resolver matches every video URL shape the site serves.

        Beyond tv/etv/gtvshows the site also serves ftv/fltv/ktvshows,
        megasports and goldenclassics videos (several without a numeric
        id), plus show pages carrying a trailer, all with a kwik m3u8.
        Anything unmatched surfaces as 'No resolver handles <url>'.
        """
        resolver_cls = self._get_resolver_class('mega')
        inst = resolver_cls()
        urls = [
            'https://www.megatv.com/live/',
            'https://www.megatv.com/tvshows/2525368/epeisodio-15-106/',
            'https://www.megatv.com/etvshows/2535349/kentriko-deltio-17-10-26/',
            'https://www.megatv.com/gtvshows/2523040/7-10-2026/',
            'https://www.megatv.com/ftvshows/2196316/enas-erotas-ta-xristougenna-syntoma-diathesimo/',
            'https://www.megatv.com/fltvshows/lili-zografou/',
            'https://www.megatv.com/ktvshows/2241886/pikampou-xristougenna-me-tin-pikampou-meros-g/',
            'https://www.megatv.com/megasports/osfp-mpaksi-ferrol/',
            'https://www.megatv.com/goldenclassics/dentro-i-karavaki/',
            'https://www.megatv.com/ekpompes/1708248/al-tsantiri-niouz/',
            'https://www.megatv.com/gtvshows/2523040/7-10-2026',
        ]
        for url in urls:
            with self.subTest(url=url):
                m = re.search(inst.pattern, url)
                self.assertIsNotNone(m, f"Mega pattern failed for {url}")
                host, media_id = m.groups()[:2]
                self.assertEqual(host, 'megatv.com')
                self.assertEqual(
                    inst.get_url(host, media_id),
                    'https://www.{0}/{1}'.format(host, media_id))

    def test_skai_url_patterns(self):
        """Skai resolver matches live, episode, show/trailer and both domains."""
        resolver_cls = self._get_resolver_class('skai')
        inst = resolver_cls()
        urls = [
            'https://www.skai.gr/tv/live',
            'https://www.skai.gr/tv/live/',
            'https://www.skai.gr/tv/episode/enimerosi/simera/2026-10-15-06',
            'https://www.skai.gr/tv/show/psuchagogia/movietime-3/to-tsakali',
            'https://www.skaitv.gr/tv/live',
        ]
        for url in urls:
            with self.subTest(url=url):
                m = re.search(inst.pattern, url)
                self.assertIsNotNone(m, f"Skai pattern failed for {url}")
                host, media_id = m.groups()[:2]
                self.assertIn(host, ('skai.gr', 'skaitv.gr'))
                self.assertTrue(media_id.startswith('tv/'))
                self.assertEqual(
                    inst.get_url(host, media_id),
                    'https://www.{0}/{1}'.format(host, media_id))

    def test_skai_episode_extraction(self):
        """Episode pages resolve episode[0] through the videostream player."""
        from unittest import mock

        import skai

        page = ('<html><script>var data = {"episode": [{"media_item_file": '
                '"1media/enimerosi/ekpompes/simera20261015.mp4"}]};</script></html>')
        inst = skai.SkaiResolver()

        class FakeResp:
            content = page

        with mock.patch.object(inst.net, 'http_GET', return_value=FakeResp()):
            resolved = inst.get_media_url('skai.gr', 'tv/episode/enimerosi/simera/2026-10-15-06')

        self.assertIn('simera20261015.mp4/chunklink.m3u8', resolved)

    def test_skai_trailer_extraction(self):
        """Show pages resolve episodes[0] trailers instead of raising KeyError."""
        from unittest import mock

        import skai

        page = ('<html><script>var data = {"show": {"title": "MOVIETIME"}, '
                '"episodes": [{"media_item_file": "202502/video/TO_TSAKALI_SE.mp4"}]};'
                '</script></html>')
        inst = skai.SkaiResolver()

        class FakeResp:
            content = page

        with mock.patch.object(inst.net, 'http_GET', return_value=FakeResp()):
            resolved = inst.get_media_url(
                'skai.gr', 'tv/show/psuchagogia/movietime-3/to-tsakali')

        self.assertIn('TO_TSAKALI_SE.mp4/chunklink.m3u8', resolved)

    def test_skai_vod_youtube_delegation(self):
        """Skai pages without a player file delegate to YouTubeGR, never the youtube addon."""
        from unittest import mock

        import skai

        page = ('<html><iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ">'
                '</iframe></html>')
        inst = skai.SkaiResolver()

        class FakeResp:
            content = page

        with mock.patch.object(inst.net, 'http_GET', return_value=FakeResp()), \
                mock.patch.object(
                    skai.SkaiResolver, '_resolve_youtube',
                    return_value='https://yt/videoplayback') as delegated:
            resolved = inst.get_media_url(
                'skai.gr', 'tv/show/psuchagogia/movietime-3/to-tsakali')

        delegated.assert_called_once_with('dQw4w9WgXcQ')
        self.assertEqual(resolved, 'https://yt/videoplayback')

    def test_ert_patterns(self):
        """Verify ERT resolver matches hash and path style details/live URLs."""
        resolver_cls = self._get_resolver_class('ert')
        inst = resolver_cls()
        urls = [
            'https://www.ertflix.gr/#/details/ERT_M002339',
            'https://www.ertflix.gr/details/ERT_M002339',
            'https://www.ertflix.gr/#/details/ERT_PS058510_E0/point/ERT_PS058511/ERT_PS058511-0001',
            'https://www.ertflix.gr/#/details/ERT_PS058510',
            'https://www.ertflix.gr/#/details/ERT_PS058510_E0/play/ERT_PS058511-0001',
            'https://www.ertflix.gr/#/liveTV/ERT_ERT1',
            'https://ertflix-worker.twilight0.workers.dev/watch/series/ERT_PS054368/season/2/episode/1',
            'https://ertflix-worker.twilight0.workers.dev/watch/series/ERT_PS058510/episode/2',
            'https://ertflix-worker.twilight0.workers.dev/watch/movie/ERT_M002339',
            'https://ertflix-worker.twilight0.workers.dev/watch/episode/ERT_PS058511-0001',
            'https://ertflix-worker.twilight0.workers.dev/watch/live/ERT_ERT1',
            'https://ertflix-worker.twilight0.workers.dev/watch/catchup/ERT_ERT1/1791280800/1791284400',
        ]
        for url in urls:
            m = re.search(inst.pattern, url)
            self.assertIsNotNone(m, f"ERT pattern failed for {url}")
            host, media_id = m.groups()[:2]
            self.assertIn(host, ('ertflix.gr', 'www.ertflix.gr', 'ertflix-worker.twilight0.workers.dev'))

    def test_rik_live_and_vod_patterns(self):
        """Verify RIK resolver matches both live channels and VOD episodes."""
        resolver_cls = self._get_resolver_class('rik')
        inst = resolver_cls()
        urls = [
            'https://tv.rik.cy/live-tv/rik-sat/',
            'https://tv.rik.cy/show/geustiko-taxidi/episode/14681/',
            'https://tv.rik.cy/show/perikles-tzai-erietta/episode/14542/',
            'https://tv.rik.cy/show/eideseis-ton-8/episode/15542/',
        ]
        for url in urls:
            m = re.search(inst.pattern, url)
            self.assertIsNotNone(m, f"RIK pattern failed for {url}")

    def test_live_stream_resolution(self):
        """Integration test: resolve actual live streams over the network for reliable channels."""
        live_cases = [
            ('aeolostv', 'https://aeolos.tv/live'),
            ('alphacy', 'https://www.alphacyprus.com.cy/live'),
            ('alphagr', 'https://www.alphatv.gr/live/'),
            ('anacon', 'https://anacon.org/app/chans/gr/atticatvimage.php'),
            ('ant1cy', 'https://www.ant1live.com/webtv/live'),
            ('bigbang', 'https://www.bigbang.gr/movie.asp?id=1'),
            ('dailymotion', 'https://www.dailymotion.com/video/x7tgad0'),
            ('greekmovies', 'https://greek-movies.com/view.php?v=iXFXDc_Bz6pM-5Iw747KxQ'),
            ('grnet', 'https://diavlos-cache.cnt.grnet.gr/app/index.html#/el/embed/room/6015'),
            ('ioniantv', 'https://ioniantv.gr/live'),
            ('kick', 'https://kick.com/madtvgreece'),
            ('kick', 'https://kick.com/api/v2/channels/madtvgreece/livestream'),
            ('mega', 'https://www.megatv.com/live/'),
            ('omegacy', 'https://www.omegatv.com.cy/live/'),
            ('opentv', 'https://www.tvopen.gr/live'),
            ('rik', 'https://tv.rik.cy/live-tv/rik-sat/'),
            ('sigma', 'https://www.sigmatv.com/live'),
            ('skai', 'https://www.skai.gr/tv/live'),
            ('star', 'https://www.star.gr/tv/live-stream'),
            ('tv100', 'https://www.tv100.gr/live'),
        ]

        for mod_name, url in live_cases:
            with self.subTest(plugin=mod_name):
                resolver_cls = self._get_resolver_class(mod_name)
                inst = resolver_cls()
                m = re.search(inst.pattern, url)
                self.assertIsNotNone(m, f"URL {url} did not match pattern")
                host, media_id = m.groups()[:2]
                try:
                    resolved = inst.get_media_url(host, media_id)
                    self.assertTrue(
                        bool(resolved),
                        f"Resolver {mod_name} returned empty stream URL",
                    )
                    self.assertTrue(
                        isinstance(resolved, (str, tuple)),
                        f"Unexpected return type: {type(resolved)}",
                    )
                except ResolverError as e:
                    if 'Source website does not allow this content to be played' in str(e):
                        print(f"Skipping {mod_name} (geoblocked from current IP): {e}")
                    else:
                        self.fail(f"ResolverError in {mod_name}: {e}")
                except Exception as e:
                    self.fail(f"Unexpected error in {mod_name}: {type(e).__name__}: {e}")

    def test_plugin_toggles_match_settings_xml(self):
        """Every plugin_enabled() call must have a matching setting, and vice versa.

        Guards against adding a resolver toggle to one side only, which would
        silently leave the plugin permanently on (or permanently off) with no
        UI control to change it.
        """
        import xml.etree.ElementTree as ET
        from unittest import mock

        settings = os.path.join(conftest.REPO_ROOT, 'resources', 'settings.xml')
        declared = {
            s.get('id') for s in ET.parse(settings).getroot().iter('setting')
            if (s.get('id') or '').endswith('_enabled')
        }

        used = set()
        for path in glob.glob(os.path.join(self.plugins_dir, '*.py')):
            with open(path, encoding='utf-8') as fh:
                source = fh.read()
            used.update(re.findall(r"plugin_enabled\('([^']+)'\)", source))

        self.assertTrue(used, 'no plugin_enabled() calls found')
        # plugin_settings.plugin_enabled(name) reads '<name>_enabled'.
        expected = {'%s_enabled' % name for name in used}
        self.assertEqual(
            sorted(expected - declared), [],
            'plugin_enabled() called but no setting declared')
        self.assertEqual(
            sorted(declared - expected), [],
            'setting declared but never consulted by any resolver')

        # And the toggles must actually flip the resolver's own gate.
        import plugin_settings

        class FakeAddon:
            def __init__(self, values):
                self.values = values

            def getSetting(self, key):
                return self.values.get(key, '')

        sample = ['youtube', 'dailymotion', 'instagram']
        for mod_name in sample:
            mod = importlib.import_module(mod_name)
            resolver = [c for c in vars(mod).values()
                        if inspect.isclass(c) and issubclass(c, ResolveUrl)
                        and c is not ResolveUrl and c.__module__ == mod_name][0]
            name = resolver.__name__
            with mock.patch.object(plugin_settings.xbmcaddon, 'Addon',
                                   lambda _id: FakeAddon({})):
                self.assertTrue(resolver._is_enabled(), f'{name} default should be enabled')
            with mock.patch.object(plugin_settings.xbmcaddon, 'Addon',
                                   lambda _id: FakeAddon({f'{name}_enabled': 'false'})):
                self.assertFalse(resolver._is_enabled(), f'{name} toggle did not disable it')

    def test_referenced_settings_are_declared(self):
        """Every setting id this addon reads must exist in settings.xml.

        An undeclared id reads back as '' forever, so the feature looks
        implemented but never takes effect.
        """
        import xml.etree.ElementTree as ET

        settings = os.path.join(conftest.REPO_ROOT, 'resources', 'settings.xml')
        declared = {
            s.get('id') for s in ET.parse(settings).getroot().iter('setting')
        }

        resources = os.path.join(conftest.REPO_ROOT, 'resources')
        referenced = set()
        for path in glob.glob(os.path.join(resources, '**', '*.py'), recursive=True):
            if 'ytresolver' in path:
                # Vendored engine reads settings of *other* addons.
                continue
            with open(path, encoding='utf-8') as fh:
                source = fh.read()
            referenced.update(re.findall(r"get_setting\(\s*['\"]([^'\"]+)['\"]", source))
            referenced.update(re.findall(r"_SETTING_\w+\s*=\s*['\"]([^'\"]+)['\"]", source))

        self.assertTrue(referenced, 'no settings references found')
        self.assertEqual(
            sorted(referenced - declared), [],
            'settings read by code but not declared in settings.xml')

    def test_instagram_carousel_modes(self):
        """Carousel setting: ask shows the dialog, first/largest bypass it."""
        from unittest import mock
        import xbmcgui

        import instagram

        items = [
            {'label': 'small', 'thumb': 'https://x/s320x320/a.jpg', 'url': 'u1'},
            {'label': 'huge', 'thumb': 'https://x/s1080x1350/b.jpg', 'url': 'u2'},
        ]
        resolver = instagram.InstagramResolver()

        for mode, expect_dialog, expect_url in [
            (None, True, 'u2'),      # unset -> ask, dialog index 1
            ('ask', True, 'u2'),
            ('first', False, 'u1'),
            ('largest', False, 'u2'),
        ]:
            calls = []
            values = {} if mode is None else {'instagram_carousel_select': mode}
            with mock.patch.object(instagram, 'get_setting',
                                   side_effect=lambda k, d='': values.get(k, d)), \
                 mock.patch.object(xbmcgui.Dialog, 'select',
                                   side_effect=lambda *a, **k: (calls.append(1), 1)[1]):
                got = resolver._choose_media(items)['url']
            self.assertEqual(bool(calls), expect_dialog,
                             f'carousel mode {mode!r}: dialog shown={bool(calls)}')
            self.assertEqual(got, expect_url, f'carousel mode {mode!r}')

        # A single-item post must never prompt.
        with mock.patch.object(instagram, 'get_setting', return_value='ask'), \
             mock.patch.object(xbmcgui.Dialog, 'select') as sel:
            self.assertEqual(resolver._choose_media([items[0]])['url'], 'u1')
        sel.assert_not_called()


    def test_settings_xml_schema(self):
            """Guard the settings.xml against shapes Kodi silently rejects.

            Kodi logs 'error reading <control> tag' and then drops the whole
            setting when an attribute/element is invalid -- the addon keeps
            working but that option never appears in the UI. Python tests
            cannot see this, so validate the structure explicitly.
            """
            import xml.etree.ElementTree as ET

            settings = os.path.join(conftest.REPO_ROOT, 'resources', 'settings.xml')
            root = ET.parse(settings).getroot()

            valid_control_types = {
                'button', 'edit', 'list', 'slider', 'color', 'radio',
                'spin', 'label', 'group', 'toggle',
            }
            # Kodi parses 'format' on <control> but only honours these values;
            # anything else (e.g. 'path') makes it discard the <control> tag.
            valid_formats = {'string', 'integer', 'number', 'boolean', 'float'}

            ids = []
            for setting in root.iter('setting'):
                sid = setting.get('id')
                self.assertTrue(sid, '<setting> without an id')
                ids.append(sid)

                controls = setting.findall('control')
                self.assertTrue(controls, f'setting {sid} has no <control>')

                for control in controls:
                    ctype = control.get('type')
                    self.assertIn(
                        ctype, valid_control_types,
                        f'setting {sid}: unknown control type {ctype!r}')
                    fmt = control.get('format')
                    if fmt is not None:
                        self.assertIn(
                            fmt, valid_formats,
                            f'setting {sid}: Kodi rejects format={fmt!r} on '
                            f'<control> and drops the whole control tag')

                # A list control must carry options to be usable.
                for control in controls:
                    if control.get('type') == 'list':
                        options = setting.findall('.//option')
                        self.assertTrue(
                            options, f'setting {sid}: list control has no <option>')

            dupes = {i for i in ids if ids.count(i) > 1}
            self.assertEqual(sorted(dupes), [], 'duplicate setting ids')

            # Defaults must match the type they are stored as.
            for setting in root.iter('setting'):
                sid, stype = setting.get('id'), setting.get('type')
                default = setting.find('default')
                if default is None or stype != 'integer':
                    continue
                self.assertIsNotNone(
                    re.match(r'^-?\d+$', (default.text or '').strip()),
                    f'setting {sid}: integer setting has non-integer default')


if __name__ == '__main__':
    unittest.main(verbosity=2)
