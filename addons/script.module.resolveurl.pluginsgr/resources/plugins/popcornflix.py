# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Popcornflix video resolver.
'''

import json
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


class PopcornflixResolver(ResolveUrl):

    name = 'Popcornflix'
    domains = ['popcornflix.com', 'www.popcornflix.com']
    pattern = r'(?://|\.)(popcornflix\.com)/((?:watch|movies|series)/[\w\-]+)'

    def get_media_url(self, host, media_id, subs=False):
        web_url = self.get_url(host, media_id)
        headers = {'User-Agent': common.RAND_UA, 'Referer': 'https://popcornflix.com/'}

        try:
            res = self.net.http_GET(web_url, headers=headers).content
        except Exception as e:
            raise ResolverError('Failed to fetch Popcornflix webpage: {0}'.format(e))

        m3u8_match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', res)
        if m3u8_match:
            stream_url = m3u8_match.group(1) + helpers.append_headers({'User-Agent': common.RAND_UA})
            return (stream_url, {}) if subs else stream_url

        mp4_match = re.search(r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']', res)
        if mp4_match:
            stream_url = mp4_match.group(1) + helpers.append_headers({'User-Agent': common.RAND_UA})
            return (stream_url, {}) if subs else stream_url

        raise ResolverError('Popcornflix web player stream not found (service may require DRM/app token)')

    def get_url(self, host, media_id):
        return 'https://{0}/{1}'.format(host, media_id)

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('PopcornflixResolver')

    @classmethod
    def _get_priority(cls):
        return 80
