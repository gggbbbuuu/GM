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

class OmegaCYResolver(ResolveUrl):

    name = 'omegacy'
    domains = ['omegatv.com.cy']
    pattern = r'(?://|\.)(omegatv\.com\.cy)/(.+)'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        if media_id == 'live/':
            stream = re.search(r'''['"]src['"]: ['"](.+m3u8.+)['"]''', res)
        else:
            iframe = re.search(r'''iframe.+"(.+LiveMediaPlayer.+)"''', res).group(1)
            html = self.net.http_GET(iframe, headers=headers).content
            stream = re.search(r"file: '(http://.+?\.mp4.+?)'", html)

        if stream:
            stream = stream.group(1)
        else:
            raise ResolverError('Video not found')

        return stream + helpers.append_headers(headers)

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='http://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('OmegaCYResolver')
