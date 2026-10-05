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
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if inspect.isclass(attr) and issubclass(attr, ResolveUrl) and attr is not ResolveUrl:
                return attr
        return None

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
