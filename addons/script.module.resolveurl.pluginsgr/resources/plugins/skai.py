# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import os
import sys
import re, json
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled

class SkaiResolver(ResolveUrl):

    name = 'skai'
    domains = ['skai.gr', 'skaitv.gr']
    pattern = r'(?://|\.)(skai(?:tv)?\.gr)/((?:tv/(?:live|episode|show|videos))[\w\-=/.%]*)'
    player_url = 'https://videostream.skai.gr/skaivod/_definst_/mp4:skai/'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        if media_id.rstrip('/') == 'tv/live':

            stream = re.search(r'livestream\\*":\\*"(https.+?)\\*"', res)

            if stream:
                stream = stream.group(1).replace('\\', '')
            else:
                raise ResolverError('Live stream not found')

        elif 'videos' not in media_id:

            stream = _vod_file(res)

            if stream:
                stream = ''.join([self.player_url, stream, '/chunklink.m3u8'])
            else:
                # Cinema trailers and other editorial pages may carry no
                # player file but embed a YouTube clip instead. Like star,
                # hand those to the YouTubeGR resolver rather than the
                # youtube addon.
                video_id = _youtube_id(res)
                if video_id:
                    return self._resolve_youtube(video_id)
                raise ResolverError('VOD stream not found')

        else:

            stream = re.search(r'"og:video" content=" ?(https://videostream\.skai\.gr/.+\.mp4\.m3u8)"', res)

            if stream:
                stream = stream.group(1)
            else:
                raise ResolverError('Stream not found')

        return stream + helpers.append_headers(headers)

    @staticmethod
    def _resolve_youtube(video_id):

        try:
            from youtube import YouTubeGRResolver
        except ImportError as e:
            raise ResolverError('The YouTubeGR plugin is unavailable: {}'.format(e))

        if not YouTubeGRResolver._is_enabled():
            raise ResolverError('The YouTubeGR plugin is disabled.')

        return YouTubeGRResolver().get_media_url('youtube.com', video_id)

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('SkaiResolver')

def _vod_file(html):
    """
    Returns the player's media file path for episode pages
    (``episode[0]``) and show/trailer pages (``episodes[0]``).
    Scans every ``var data`` blob so an early ad/analytics stub can
    never shadow the real player payload.
    """

    for match in re.finditer(r'var data = ({.+?});', html):
        try:
            payload = json.loads(match.group(1))
        except Exception:
            continue

        for key in ('episode', 'episodes'):
            entries = payload.get(key)
            if isinstance(entries, list) and entries:
                media = entries[0].get('media_item_file')
                if media:
                    return media.replace('\\/', '/').replace('\\', '')

    fallback = re.search(r'media_item_file\\*"\s*:\s*\\*"((?:\\/|[^"\\])*)', html)

    if fallback:
        return fallback.group(1).replace('\\/', '/').replace('\\', '')

    return ''

def _youtube_id(html):

    for pattern in (r'youtube(?:-nocookie)?\.com/embed/([\w-]{6,})',
                    r'youtube\.com/watch\?[^\\s"\\\']*v=([\w-]{6,})',
                    r'youtu\.be/([\w-]{6,})'):
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    return ''
