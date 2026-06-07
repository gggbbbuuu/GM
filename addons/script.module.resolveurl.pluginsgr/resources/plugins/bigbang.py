# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import json
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

        host, media_id = re.search(r'iframe src="//geo\.(dailymotion\.com)/player/\w+\.html\?video=(\w+)"', html).groups()
        if not host or not media_id:
            raise ResolverError('Could not find a Dailymotion video on the page.')

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
