# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Pluto TV video resolver.
    Resolves on-demand movies, series episodes, and live channels from
    Pluto TV's cluster services into adaptive HLS master playlists.
'''

import json
import os
import re
import sys
import urllib.parse
import uuid

from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled


class PlutoTVResolver(ResolveUrl):

    name = 'PlutoTV'
    domains = ['pluto.tv', 'www.pluto.tv']
    pattern = (
        r'(?://|\.)(pluto\.tv)/'
        r'((?:[a-z]{2}/)?(?:on-demand/(?:movies|series)/[\w\-]+(?:/(?:seasons?/\d+|episode/[\w\-]+))*|live-tv/[\w\-]+))'
    )

    vod_api_base = 'https://service-vod.clusters.pluto.tv/v3/vod/slugs'
    us_header_ip = '104.28.19.1'

    def _client_params(self):
        return {
            'appName': 'web',
            'appVersion': 'na',
            'clientID': str(uuid.uuid4()),
            'clientModelNumber': 'na',
            'serverSideAds': 'false',
            'deviceMake': 'unknown',
            'deviceModel': 'web',
            'deviceType': 'web',
            'deviceVersion': 'unknown',
            'sid': str(uuid.uuid4()),
        }

    def get_media_url(self, host, media_id, subs=False):
        headers = {
            'User-Agent': common.RAND_UA,
            'X-Forwarded-For': self.us_header_ip,
            'Referer': 'https://pluto.tv/'
        }

        stream_url = None

        # 1. On-Demand Movies
        if 'movies/' in media_id:
            slug = media_id.split('movies/')[1].split('/')[0]
            query = urllib.parse.urlencode(self._client_params())
            api_url = '{0}/{1}?{2}'.format(self.vod_api_base, slug, query)

            try:
                res = self.net.http_GET(api_url, headers=headers).content
                data = json.loads(res)
            except Exception as e:
                raise ResolverError('Failed to fetch Pluto movie metadata: {0}'.format(e))

            urls = data.get('stitched', {}).get('urls', [])
            for u in urls:
                if u.get('type') == 'hls' and u.get('url'):
                    stream_url = u.get('url')
                    break

            if not stream_url:
                raise ResolverError('No playable HLS stream for movie: {0}'.format(slug))

        # 2. On-Demand Series Episodes
        elif 'series/' in media_id:
            parts = media_id.split('series/')[1].split('/')
            series_slug = parts[0]
            ep_slug = parts[parts.index('episode') + 1] if 'episode' in parts else None

            query = urllib.parse.urlencode(self._client_params())
            api_url = '{0}/{1}?{2}'.format(self.vod_api_base, series_slug, query)

            try:
                res = self.net.http_GET(api_url, headers=headers).content
                data = json.loads(res)
            except Exception as e:
                raise ResolverError('Failed to fetch Pluto series metadata: {0}'.format(e))

            target_ep = None
            for season in data.get('seasons', []):
                for ep in season.get('episodes', []):
                    if ep_slug is None or ep.get('slug') == ep_slug:
                        target_ep = ep
                        break
                if target_ep:
                    break

            if not target_ep:
                raise ResolverError('Episode not found in Pluto series: {0}'.format(media_id))

            urls = target_ep.get('stitched', {}).get('urls', [])
            for u in urls:
                if u.get('type') == 'hls' and u.get('url'):
                    stream_url = u.get('url')
                    break

            if not stream_url:
                raise ResolverError('No playable HLS stream for episode: {0}'.format(ep_slug or series_slug))

        # 3. Live TV Channels
        elif 'live-tv/' in media_id:
            ch_slug = media_id.split('live-tv/')[1].split('/')[0]
            try:
                res = self.net.http_GET('https://api.pluto.tv/v2/channels', headers=headers).content
                channels = json.loads(res)
            except Exception as e:
                raise ResolverError('Failed to fetch Pluto channel lineup: {0}'.format(e))

            channel = next((c for c in channels if c.get('slug') == ch_slug or c.get('_id') == ch_slug), None)
            if not channel:
                raise ResolverError('Pluto live channel not found: {0}'.format(ch_slug))

            urls = channel.get('stitched', {}).get('urls', [])
            for u in urls:
                if u.get('type') == 'hls' and u.get('url'):
                    stream_url = u.get('url')
                    break

            if not stream_url:
                raise ResolverError('No playable live stream for channel: {0}'.format(ch_slug))

        else:
            raise ResolverError('Unsupported Pluto TV route: {0}'.format(media_id))

        stream_headers = {
            'User-Agent': common.RAND_UA,
            'X-Forwarded-For': self.us_header_ip
        }
        final_url = stream_url + helpers.append_headers(stream_headers)
        if subs:
            return final_url, {}
        return final_url

    def get_url(self, host, media_id):
        return 'https://{0}/{1}'.format(host, media_id)

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('PlutoTVResolver')

    @classmethod
    def _get_priority(cls):
        return 80
