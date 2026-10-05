"""
    Plugin for ResolveURL
    Copyright (C) 2020 gujal

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import os
import sys
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

# noinspection unresolved-references
from moq_proxy import build_m3u8_proxy_url

# Ungated token issuance (CloudFront/envoy, no Cloudflare Turnstile):
# returns {"stream": {"url": "<cdndirector master manifest>"}, ...}.
GEO_URL = 'https://geo.dailymotion.com/videos/{media_id}'


class DailymotionResolver(ResolveUrl):
    name = 'DailymotionGR'
    domains = ['dailymotion.com', 'dai.ly']
    pattern = (
        r'(?://|\.)(dailymotion\.com|dai\.ly)(?:/(?:video|embed|sequence|swf|player)'
        r'(?:/video|/full)?)?/(?:[a-z0-9]+\.html\?video=)?(?!playlist)([0-9a-zA-Z]+)'
    )

    def get_media_url(self, host, media_id, subs=False):

        main_page_url = 'https://www.dailymotion.com/video/{}'.format(media_id)
        headers = {
            'User-Agent': common.RAND_UA,
            'Origin': 'https://www.dailymotion.com',
            'Referer': main_page_url,
            # Real-Chrome HTTP/2 hint; streamlink needs it to avoid 403s on some routes.
            'priority': 'u=1, i',
        }

        subtitles = {}
        manifest_url = None

        # 1. Geo endpoint first: the only call that must survive Turnstile regions.
        try:
            geo = json.loads(self.net.http_GET(
                GEO_URL.format(media_id=media_id),
                headers={'User-Agent': common.RAND_UA, 'Referer': main_page_url}
            ).content)
            manifest_url = (geo.get('stream') or {}).get('url')
        except Exception:
            manifest_url = None

        # 2. Legacy player metadata: fallback manifest source, and the only
        # subtitles source (the geo responses carry no subtitles).
        if manifest_url is None or subs:
            try:
                js_result = json.loads(self.net.http_GET(
                    self.get_url(host, media_id), headers=headers).content)
            except Exception:
                js_result = {}
            if js_result.get('error'):
                raise ResolverError(js_result.get('error').get('title'))
            if subs:
                matches = js_result.get('subtitles', {}).get('data')
                if matches:
                    for key in list(matches.keys()):
                        subtitles[matches[key].get('label')] = matches[key].get('urls', [])[0]
            if manifest_url is None:
                quals = js_result.get('qualities') or {}
                auto = quals.get('auto')
                if auto:
                    manifest_url = auto[0].get('url')

        if not manifest_url:
            raise ResolverError('No playable video found.')

        # Relay the Cloudflare-gated master manifest through the localhost
        # proxy so playback works globally, live included: the relay
        # re-fetches upstream on every player request (nothing is cached),
        # so live playlists stay fresh with newly minted tokens, and the
        # server-side fetch carries the full header set (Kodi's ffmpeg
        # bridge drops `priority`, which the live endpoint requires).
        # Renditions and segments stay direct on dmcdn (verified ungated).
        stream_url = build_m3u8_proxy_url(manifest_url, headers=headers)
        if subs:
            return stream_url, subtitles
        return stream_url

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://www.dailymotion.com/player/metadata/video/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True

    @classmethod
    def _get_priority(cls):

        return 80
