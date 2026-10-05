# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolverError, ResolveUrl


class BigBangGR(ResolveUrl):

    name = 'BigBangGR'
    domains = ['bigbang.gr']
    pattern = r'(?://|\.)(bigbang\.gr)/movie\.asp\?id=(\d+)'

    def get_media_url(self, host, media_id, subs=False):

        web_url = f'https://www.{host}/movie.asp?id={media_id}'
        html = self.net.http_GET(web_url).content
        headers = {'User-Agent': common.RAND_UA}

        # Embedded third-party players. Dailymotion goes to our resolver
        # directly (deterministic geo-first + proxy relay); anything else
        # via ResolveURL dispatch (automatic plugin selection by priority).
        # Lazy imports: run at resolve time, after all plugins are loaded.
        import resolveurl
        from dailymotion import DailymotionResolver
        for src in re.findall(r'''<iframe[^>]*src=["']([^"']+)''', html, re.I):
            if 'bigbang.gr' in src:
                continue
            if src.startswith('//'):
                src = 'https:' + src
            dm_match = re.search(r'//geo\.(dailymotion\.com)/player/\w+\.html\?video=(\w+)', src)
            if dm_match:
                dm_host, dm_id = dm_match.groups()
                return DailymotionResolver().get_media_url(dm_host, dm_id, subs=subs)
            resolved = resolveurl.resolve(src)
            if resolved:
                # hmf unpacks a 2-tuple whenever the outer call requested
                # subs; the inner resolve ran without subs, so none to pass on.
                if subs:
                    return resolved, {}
                return resolved

        # Self-hosted file in an HTML5 <video> tag (older movies).
        match = re.search(r'''<video[^>]*>.*?<source\s+src=["']([^"']+)''', html, re.S | re.I)
        if match:
            stream_url = match.group(1) + helpers.append_headers(headers)
            # hmf unpacks a 2-tuple whenever subs was requested; direct
            # files carry no subtitles.
            if subs:
                return stream_url, {}
            return stream_url

        raise ResolverError('No playable video found.')

    @classmethod
    def _is_enabled(cls):
        return True
