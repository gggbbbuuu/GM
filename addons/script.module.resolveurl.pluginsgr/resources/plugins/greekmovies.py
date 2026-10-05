# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Greek-Movies is a front-end index: view pages carry no media, they link
    out to the actual host (AlphaTV episode pages, embeds, ...). This
    resolver collects those outbound URLs and hands each to the owning
    plugin - AlphaTV directly (deterministic, in-house), anything else via
    ResolveURL dispatch (automatic plugin selection by priority).
'''

import re
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError

_AD_DOMAINS = (
    'googletagmanager.com', 'googletagservices.com', 'googleapis.com',
    'gstatic.com', 'imasdk.googleapis.com', 'youbora.com',
    'orangeclickmedia.com', 'facebook.com', 'facebook.net',
)


class GreekMoviesResolver(ResolveUrl):
    name = 'GreekMovies'
    domains = ['greek-movies.com']
    pattern = r'(?://|\.)(greek-movies\.com)/(?:view\.php\?v=([\w-]+))'

    def get_media_url(self, host, media_id, subs=False):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url, headers=headers).content

        candidates = []
        for src in re.findall(r'''<iframe[^>]*src=[\"']((?:https?:)?//[^\s\"']+)''', html, re.I):
            candidates.append(src)
        for href in re.findall(r'''<a[^>]*href=[\"']((?:https?:)?//[^\s\"']+)''', html, re.I):
            candidates.append(href)

        # Lazy import: runs at resolve time, after all plugins are loaded.
        import resolveurl
        for src in candidates:
            if 'greek-movies.com' in src:
                continue
            if any(ad in src for ad in _AD_DOMAINS):
                continue
            if src.startswith('//'):
                src = 'https:' + src
            src = src.replace('&amp;', '&')
            # Automatic plugin selection by priority (AlphaTV included:
            # its URL form matches AlphaGRResolver's pattern).
            resolved = resolveurl.resolve(src)
            if resolved:
                if subs and not isinstance(resolved, tuple):
                    return resolved, {}
                return resolved

        raise ResolverError('No playable video found.')

    def get_url(self, host, media_id):
        return 'https://www.greek-movies.com/view.php?v={0}'.format(media_id)

    @classmethod
    def _is_enabled(cls):
        return True
