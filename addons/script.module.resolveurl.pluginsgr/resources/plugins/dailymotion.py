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
import base64
import xbmc
import xbmcaddon
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class DailymotionResolver(ResolveUrl):
    name = 'DailymotionGR'
    domains = ['dailymotion.com', 'dai.ly']
    pattern = (
        r'(?://|\.)(dailymotion\.com|dai\.ly)(?:/(?:video|embed|sequence|swf|player)'
        r'(?:/video|/full)?)?/(?:[a-z0-9]+\.html\?video=)?(?!playlist)([0-9a-zA-Z]+)'
    )

    def get_media_url(self, host, media_id, subs=False):

        # if not xbmc.getCondVisibility('System.HasAddon(plugin.video.alivegr)'):
        #     raise ResolverError('AliveGR addon is required to play streams from Dailymotion.')

        main_page_url = 'https://www.dailymotion.com/video/{}'.format(media_id)

        web_url = self.get_url(host, media_id)
        headers = {
            'User-Agent': common.RAND_UA,
            'Origin': 'https://www.dailymotion.com',
            'Referer': main_page_url
        }

        js_result = json.loads(self.net.http_GET(web_url, headers=headers).content)

        if js_result.get('error'):
            raise ResolverError(js_result.get('error').get('title'))

        quals = js_result.get('qualities')
        subtitles = {}

        if subs:

            matches = js_result.get('subtitles', {}).get('data')

            if matches:

                for key in list(matches.keys()):
                    subtitles[matches[key].get('label')] = matches[key].get('urls', [])[0]

        if quals:

            vid_src = quals.get('auto')[0].get('url')
            # port = xbmcaddon.Addon('plugin.video.alivegr').getSetting('proxy_port') or '50199'
            # vid_b64 = base64.urlsafe_b64encode(vid_src.encode('utf-8')).decode('utf-8')
            # vid_src = f'http://127.0.0.1:{port}/dailymotion_{media_id}.m3u8?stream={vid_b64}'

            if subs:
                return vid_src, subtitles

            return vid_src

        raise ResolverError('No playable video found.')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://www.dailymotion.com/player/metadata/video/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True

    @classmethod
    def _get_priority(cls):

        return 80
