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
from resolveurl.resolver import ResolveUrl, ResolverError


class TV100Resolver(ResolveUrl):

    name = 'tv100'
    domains = ['tv100.gr']
    pattern = r'(?://|\.)(tv100\.gr)/(live)'

    def get_media_url(self, host, media_id):

        headers = {
            'User-Agent': common.RAND_UA
        }

        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers)

        match = re.search(r'streamURL = "(.+master\.m3u8)";', res.content)

        if match:
            stream = match.group(1) + helpers.append_headers(headers)
            return stream
        else:
            raise ResolverError('No stream found')

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True