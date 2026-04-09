# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
from resolveurl import common
from resolveurl.lib import kodi
from resolveurl.resolver import ResolverError, ResolveUrl


class EuronewsGRResolver(ResolveUrl):

    name = 'EuronewsGR'
    domains = ['gr.euronews.com']
    pattern = r'(?://|\.)(gr\.euronews\.com)/(api/live/data\?locale=el)'

    def get_media_url(self, host, media_id):

        headers = {
            'User-Agent': common.RAND_UA
        }

        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        youtu = re.search(r'videoId":"([\w-]{11})"', res)

        if youtu:

            return 'plugin://plugin.video.youtube/play/?video_id={0}'.format(youtu.group(1))

        else:

            raise ResolverError('No stream found')

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return kodi.has_addon('plugin.video.youtube')
