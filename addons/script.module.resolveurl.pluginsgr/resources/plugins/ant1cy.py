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

class Ant1CYResolver(ResolveUrl):

    name = 'ant1cy'
    domains = ['ant1live.com']
    pattern = r'(?://|\.)(ant1live\.com)/webtv/(.+?)/?$'

    def get_media_url(self, host, media_id, subs=False):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)

        try:
            page = self.net.http_GET(web_url, headers=headers).content
        except Exception as e:
            raise ResolverError('Could not load the video page: {}'.format(e))

        if isinstance(page, bytes):
            page = page.decode('utf-8', 'replace')

        stream = self._extract(page)

        if not stream:
            raise ResolverError('Video not found')

        if isinstance(stream, tuple):
            # YouTube embeds are resolved by the YouTubeGR resolver rather
            # than returned as a bare watch url, which Kodi cannot play.
            return self._resolve_youtube(stream[1], subs)

        # Kodi needs the space-containing vod URLs percent-encoded.
        stream = self._encode(stream)

        if stream.startswith('/'):
            stream = 'https://www.ant1live.com' + stream

        stream = stream + helpers.append_headers(headers)

        # HostedMediaFile.resolve() unpacks `stream_url, subtitles = ...`
        # whenever subs is in the signature, so this must ALWAYS return a
        # pair - returning a bare url makes the unpack explode on any clip
        # that happens to have no subtitle track.
        if subs:
            return stream, {}

        return stream

    @staticmethod
    def _extract(page):
        """The site embeds four player flavours; first hit wins."""

        # 1. videojs HLS (live + news VOD): <source src="...master.m3u8">
        match = re.search(r'''<source\s+src=["']([^"']+?\.m3u8)["']''', page)

        if match:
            return match.group(1)

        # 2. direct mp4 (movies): <source src="/sites/default/files/....mp4">
        match = re.search(r'''<source\s+src=["']([^"']+?\.mp4)["']''', page)

        if match:
            return match.group(1)

        # 3. syndicated clips live behind lazy-loaded YouTube iframes.
        match = re.search(
            r'''(?:data-src|src)=["']https?://www\.youtube(?:-nocookie)?\.com/embed/([\w-]{6,})''', page)

        if match:
            return ('youtube', match.group(1))

        # 4. legacy inline m3u8 (whatever the previous generation left).
        match = re.search(r'''src=["'](http.+?\.m3u8)['"]''', page)

        if match:
            return match.group(1)

        return ''

    @staticmethod
    def _resolve_youtube(video_id, subs):
        """Hand YouTube embeds to the YouTubeGR resolver (cf. skai, star)."""

        try:
            from youtube import YouTubeGRResolver
        except ImportError as e:
            raise ResolverError('The YouTubeGR plugin is unavailable: {}'.format(e))

        if not YouTubeGRResolver._is_enabled():
            raise ResolverError('The YouTubeGR plugin is disabled.')

        if subs:
            return YouTubeGRResolver().get_media_url('youtube.com', video_id, subs=True)

        return YouTubeGRResolver().get_media_url('youtube.com', video_id)

    @staticmethod
    def _encode(stream):
        """Percent-encodes bare spaces, leaving the path otherwise intact."""

        if ' ' not in stream:
            return stream

        from six.moves.urllib_parse import urlsplit, urlunsplit, quote

        parts = urlsplit(stream)

        return urlunsplit((
            parts.scheme, parts.netloc,
            quote(parts.path, safe='/:'),
            parts.query, parts.fragment,
        ))

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/webtv/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('Ant1CYResolver')
