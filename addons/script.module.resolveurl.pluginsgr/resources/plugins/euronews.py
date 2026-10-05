# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
import re
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolverError, ResolveUrl


class EuronewsGRResolver(ResolveUrl):

    name = 'EuronewsGR'
    domains = ['euronews.com', 'fr.euronews.com', 'de.euronews.com',
               'es.euronews.com', 'it.euronews.com', 'pt.euronews.com',
               'tr.euronews.com', 'gr.euronews.com']
    pattern = r'(?://|\.)((?:[a-z]{2}\.)?euronews\.com)/(api/live/data\?locale=[\w-]+)'

    def get_media_url(self, host, media_id, subs=False):

        locale_match = re.search(r'locale=([\w-]+)', media_id)
        locale = locale_match.group(1) if locale_match else 'en'
        lang = locale.split('-')[0]
        edition = 'https://{0}/'.format(host)
        headers = {
            'User-Agent': common.RAND_UA,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': '{0},{1};q=0.9,en;q=0.8'.format(locale, lang),
            'Referer': edition,
            'Origin': edition.rstrip('/'),
        }

        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        try:
            data = json.loads(res)
        except Exception:
            data = {}

        player = data.get('player')
        video_id = data.get('videoId')
        primary_url = data.get('videoPrimaryUrl')

        # A direct broadcaster URL wins when present: token-authed HLS,
        # no further hops. Otherwise delegate by player backend.
        if primary_url:
            stream_url = primary_url + helpers.append_headers(headers)
            if subs:
                return stream_url, {}
            return stream_url

        # Lazy imports: run at resolve time, after all plugins are loaded.
        if player == 'youtube' and video_id:
            from youtube import YouTubeGRResolver
            return YouTubeGRResolver().get_media_url('youtube.com', video_id, subs=subs)

        if player == 'dailymotion' and video_id:
            from dailymotion import DailymotionResolver
            return DailymotionResolver().get_media_url('dailymotion.com', video_id, subs=subs)

        # Legacy shape: bare YouTube id somewhere in the payload.
        youtu = re.search(r'videoId":"([\w-]{11})"', res)
        if youtu:
            from youtube import YouTubeGRResolver
            return YouTubeGRResolver().get_media_url('youtube.com', youtu.group(1), subs=subs)

        raise ResolverError('No stream found')

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
