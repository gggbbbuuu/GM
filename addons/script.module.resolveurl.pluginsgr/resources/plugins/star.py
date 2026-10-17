# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import os
import sys
import re
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled

class StarResolver(ResolveUrl):

    name = 'star'
    domains = ['star.gr']
    pattern = r'(?://|\.)(star\.gr)/((?:video|lifestyle|eidiseis|show|tv)/(?:live-stream/?|[\w\-=/]+))'
    player_url = 'https://cdnapisec.kaltura.com/p/713821/sp/0/playManifest/entryId/{0}/format/applehttp/protocol/https/flavorParamId/0/manifest.m3u8'

    def get_media_url(self, host, media_id, subs=False):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        if media_id.rstrip('/') == 'tv/live-stream':
            stream = re.search(r'data-video="(http.+)"', res)
            if stream:
                stream = stream.group(1)
            else:
                raise ResolverError('Live stream not found')
        else:
            stream = re.search(r'file:\s*"(https://deliver2\.siliconweb\.com/kwik/star\.m3u8\?key=[^"]+)"', res)
            if stream:
                stream = self.net.http_GET(stream.group(1), headers=headers, redirect=False).get_redirect_url()
                return self._with_headers(stream, headers, subs)
            stream = re.search(r'contentUrl": "(.+?\.m3u8.+?)"', res)
            if stream:
                stream = self.net.http_GET(stream.group(1), headers=headers, redirect=False).get_redirect_url()
                return self._with_headers(stream, headers, subs)
            # Older pages carry YouTube clips (iframe embeds or the legacy
            # data-video attribute). Like novasports, hand those to the
            # YouTubeGR resolver rather than the youtube addon.
            video_id = _youtube_id(res)
            if video_id:
                return self._resolve_youtube(video_id, subs)
            raise ResolverError('VOD stream not found')

        return stream + helpers.append_headers(headers)

    @staticmethod
    def _with_headers(stream, headers, subs):
        # HostedMediaFile.resolve() unpacks `stream_url, subtitles = ...`
        # whenever subs is in this signature, so this must ALWAYS return a
        # pair when subs are requested.
        if subs:
            return stream + helpers.append_headers(headers), {}

        return stream + helpers.append_headers(headers)

    @staticmethod
    def _resolve_youtube(video_id, subs=False):

        try:
            from youtube import YouTubeGRResolver
        except ImportError as e:
            raise ResolverError('The YouTubeGR plugin is unavailable: {}'.format(e))

        if not YouTubeGRResolver._is_enabled():
            raise ResolverError('The YouTubeGR plugin is disabled.')

        return YouTubeGRResolver().get_media_url('youtube.com', video_id, subs=subs)

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('StarResolver')

def _youtube_id(html):

    for pattern in (r'youtube(?:-nocookie)?\.com/embed/([\w-]{6,})',
                    r'youtube\.com/watch\?[^\\s"\\\']*v=([\w-]{6,})',
                    r'youtu\.be/([\w-]{6,})',
                    r'"contentUrl"\s*:\s*"https://www\.youtube\.com/embed/([\w-]{6,})',
                    r'''data-video="([\w-]{11})"'''):
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    return ''
