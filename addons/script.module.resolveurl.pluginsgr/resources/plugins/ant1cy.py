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


class Ant1CYResolver(ResolveUrl):

    name = 'ant1cy'
    domains = ['ant1live.com)']
    pattern = r'(?://|\.)(ant1live\.com)/webtv/((?:live|series|video-demand|kypriakes-seires-0|podcasts)(?:/.+)?)'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        m3u8 = re.search(r'''src=["'](http.+?\.m3u8)['"]''', res)
        if m3u8:
            m3u8 = m3u8.group(1)
        else:
            raise ResolverError('Video not found')

        return m3u8 + helpers.append_headers(headers)

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/webtv/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
