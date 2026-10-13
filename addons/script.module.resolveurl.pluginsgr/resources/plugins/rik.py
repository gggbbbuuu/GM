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

class RikResolver(ResolveUrl):

    name = 'rik'
    domains = ['tv.rik.cy']
    pattern = r'(?://|\.)(tv\.rik\.cy)/((?:tr/)?(?:live-tv|show)/.+)'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        stream = re.search(r'''['"]file['"]: ['"](https.+?(?:m3u8|mp4))['"]''', res)

        if stream:
            stream = stream.group(1)
        else:
            raise ResolverError('Video not found')

        return stream + helpers.append_headers(headers)

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('RikResolver')
