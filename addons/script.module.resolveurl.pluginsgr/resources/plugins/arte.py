# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Arte.tv video resolver.
    Resolves European art-house cinema, series, and documentaries from
    Arte's player v2 API into adaptive HLS / direct HTTPS streams.
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


class ArteTVResolver(ResolveUrl):

    name = 'ArteTV'
    domains = ['arte.tv', 'www.arte.tv']
    pattern = (
        r'(?://|\.)(arte\.tv)/'
        r'((?:player/v\d+/index\.php\?.*?\bjson_url=.*|[a-z]{2}/videos/\d{6}-\d{3}-[A-Z](?:/[\w\-]+)?))'
    )

    api_base = 'https://api.arte.tv/api/player/v2/config'

    def get_media_url(self, host, media_id, subs=False):
        sub_m = re.search(r'([a-z]{2})/(?:videos/)?(\d{6}-\d{3}-[A-Z])', media_id) or \
                re.search(r'config(?:%2F|/)([a-z]{2})(?:%2F|/)(\d{6}-\d{3}-[A-Z])', media_id)

        if not sub_m:
            raise ResolverError('Unsupported Arte.tv URL: {0}'.format(media_id))

        lang = sub_m.group(1)
        video_id = sub_m.group(2)

        api_url = '{0}/{1}/{2}'.format(self.api_base, lang, video_id)
        headers = {
            'User-Agent': common.RAND_UA,
            'x-validated-age': '18',
            'Referer': 'https://www.arte.tv/'
        }

        try:
            res = self.net.http_GET(api_url, headers=headers).content
            data = json.loads(res)
        except Exception as e:
            raise ResolverError('Failed to fetch Arte metadata: {0}'.format(e))

        attr = data.get('data', {}).get('attributes', {})
        streams = attr.get('streams', [])
        if not streams:
            geoblocking = attr.get('restriction', {}).get('geoblocking', {})
            if geoblocking.get('restrictedArea'):
                raise ResolverError('Arte video is geo-restricted: {0}'.format(geoblocking.get('code')))
            raise ResolverError('No playable streams available on Arte for video {0}'.format(video_id))

        stream_url = None
        # Prefer HLS streams (adaptive bitrate, multi-audio, multi-subtitle)
        for s in streams:
            if 'HLS' in s.get('protocol', '') and s.get('url'):
                stream_url = s.get('url')
                break

        # Fall back to HTTPS direct streams if no HLS
        if not stream_url:
            for s in streams:
                if s.get('protocol') == 'HTTPS' and s.get('url'):
                    stream_url = s.get('url')
                    break

        if not stream_url:
            raise ResolverError('No valid HLS or HTTPS stream found for {0}'.format(video_id))

        stream_headers = {'User-Agent': common.RAND_UA}
        final_url = stream_url + helpers.append_headers(stream_headers)
        if subs:
            return final_url, {}
        return final_url

    def get_url(self, host, media_id):
        return 'https://{0}/{1}'.format(host, media_id)

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('ArteTVResolver')

    @classmethod
    def _get_priority(cls):
        return 80
