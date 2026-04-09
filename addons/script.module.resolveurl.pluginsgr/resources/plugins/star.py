# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class StarResolver(ResolveUrl):

    name = 'star'
    domains = ['star.gr']
    pattern = r'(?://|\.)(star?\.gr)/((?:video|lifestyle|eidiseis|show|tv)/(?:live-stream/|[\w\-=/]+))'
    player_url = 'https://cdnapisec.kaltura.com/p/713821/sp/0/playManifest/entryId/{0}/format/applehttp/protocol/https/flavorParamId/0/manifest.m3u8'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        if media_id == 'tv/live-stream':
            stream = re.search(r'data-video="(http.+)"', res)
            if stream:
                stream = stream.group(1)
            else:
                raise ResolverError('Live stream not found')
        else:
            stream = re.search(r'contentUrl": "(.+?\.m3u8.+?)"', res)
            youtu = re.search(r'''data-video="([\w-]{11})"''', res)
            if stream:
                stream = self.net.http_GET(stream.group(1), headers=headers, redirect=False).get_redirect_url()
            elif youtu:
                stream = 'plugin://plugin.video.youtube/play/?video_id=' + youtu.group(1)
                return stream
            else:
                raise ResolverError('VOD stream not found')

        return stream + helpers.append_headers(headers)

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
