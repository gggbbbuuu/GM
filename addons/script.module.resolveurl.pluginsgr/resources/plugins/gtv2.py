# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    gtv2.site posts come in two shapes: tt<ID> pages are self-hosted
    KGVID / Video.js markup with plain <video><source src="...mp4"> tags,
    while numeric 1-<id> pages embed a third-party host (voe.sx, vidmoly,
    ...) in an <iframe>. There is no token and no encryption on the direct
    sources. When a page offers several <source> qualities the choice goes
    through ResolveURL's standard multi-quality picker (auto-pick obeys the
    user's global setting); the embeds are handed to the owning upstream
    plugin, direct <source> URLs first when both are present on one page.
'''

import html
import os
import re
import sys
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled


class Gtv2Resolver(ResolveUrl):
    name = 'gtv2'
    domains = ['gtv2.site']
    pattern = r'(?://|\.)(gtv2\.site)/((?:tt\d+|\d+-\d+)/?)'

    _RES_RANK = {'uhd': 2160, '2160p': 2160, '2160': 2160, '4k': 2160,
                 'full': 1080, 'fhd': 1080, '1080p': 1080, '1080': 1080,
                 'hd': 720, '720p': 720, '720': 720,
                 'sd': 480, '480p': 480, '480': 480}

    _AD_DOMAINS = (
        'googletagmanager.com', 'google-analytics.com', 'googletagservices.com',
        'googleapis.com', 'gstatic.com', 'imasdk.googleapis.com',
        'facebook.com', 'facebook.net', 'twitter.com',
    )

    def get_media_url(self, host, media_id):
        headers = {
            'User-Agent': common.RAND_UA,
            'Accept-Language': 'el,en;q=0.8',
            'Referer': 'https://{0}/'.format(host),
        }
        web_url = self.get_url(host, media_id)
        try:
            page = self.net.http_GET(web_url, headers=headers).content
        except Exception as e:
            raise ResolverError('Page fetch failed: {0}'.format(e))

        best = self._collect_sources(page)
        if best:
            return helpers.pick_source(helpers.sort_sources_list(list(best)))

        # Numeric 1-<id> pages carry a third-party embed alongside ad iframes
        # from ever-changing popunder domains. Those have no resolver, so
        # dispatch each outbound iframe in order and keep the first that
        # actually resolves, greekmovies-style -- never match ad clutter
        # by domain, which rots.
        import resolveurl
        for embed in self._iter_embeds(page, host):
            resolved = resolveurl.resolve(embed)
            if resolved:
                return resolved

        raise ResolverError('No playable video found.')

    @staticmethod
    def _iter_embeds(page, host):
        """Yield outbound <iframe> srcs in document order, ad-tech skipped.

        Entities are unescaped so &amp;-joined query strings survive, and the
        host's own domain is excluded so a player chrome iframe can never
        recurse back into this resolver.
        """
        page = html.unescape(page)
        seen = set()
        for m in re.finditer(
                r'''<iframe\b[^>]*\bsrc\s*=\s*["']([^"']+)["']''', page, re.I):
            src = m.group(1).strip()
            if not src or src.startswith(('data:', 'blob:', 'about:')):
                continue
            if src.startswith('//'):
                src = 'https:' + src
            elif not re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*://', src):
                continue
            if host in src or src in seen:
                continue
            seen.add(src)
            if any(ad in src for ad in Gtv2Resolver._AD_DOMAINS):
                continue
            yield src

    def _collect_sources(self, page):
        """Collect (label, url) pairs from <source> tags for the picker.

        Entities are unescaped first so &quot;-encoded vars blobs and
        &#038;-escaped query strings still match. Bare-relative and
        data:/blob: sources are skipped: without a netloc they are not
        directly playable and almost always carry player chrome. Labels are
        pixel heights zero-padded to four digits, so sort_sources_list ranks
        them numerically ('Full'->1080 beats 'SD'->480) while the dialog shows
        human-readable numbers, exactly like grnet.py hands it mpd titles.
        """
        page = html.unescape(page)
        sources = []
        for m in re.finditer(
                r'''<source\b[^>]*\bsrc\s*=\s*["']([^"']+)["'][^>]*>''', page, re.I):
            tag = m.group(0)
            url = m.group(1).strip()
            if not url or url.startswith(('data:', 'blob:')):
                continue
            if url.startswith('//'):
                url = 'https:' + url
            elif not re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*://', url):
                continue
            if any(u == url for _, u in sources):
                continue
            label = re.search(r'''\bdata-res\s*=\s*["']([^"']*)["']''', tag, re.I)
            rank = self._rank_label(label.group(1) if label else '')
            sources.append(('{0:04d}'.format(rank), url))
        return sources

    @classmethod
    def _rank_label(cls, label):
        """Numeric rank of a data-res label (Full->1080, SD->480, ...).

        Digit-bearing labels map to their pixel height; bare words ('Full',
        'HD') map through _RES_RANK. Unknown or empty labels rank 0, so
        sort_sources_list (and hence the auto-pick default) always prefers a
        known quality over an unlabeled URL. Labels are zero-padded to four
        digits: sort_sources_list strips non-digits anyway, but the dialog
        shows the raw label, so '1080' must read '1080' not '030'.
        """
        label = (label or '').strip().lower()
        m = re.search(r'(\d{3,4})', label)
        if m:
            return int(m.group(1))
        return cls._RES_RANK.get(label, 0)

    def get_url(self, host, media_id):
        return 'https://{0}/{1}/'.format(host, media_id.rstrip('/'))

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('Gtv2Resolver')
