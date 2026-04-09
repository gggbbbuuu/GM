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


class ArtliveResolver(ResolveUrl):

    name = 'artlive'
    domains = ['arttv.info']
    pattern = r'(?://|\.)(arttv\.info)/(p/art.html)'

    def get_media_url(self, host, media_id):

        headers = {
            'User-Agent': common.RAND_UA
        }

        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        rumble = re.search(r'src="(https://rumble.com/.+?)"', res)

        if rumble:

            result = rumble.group(1)
            res = self.net.http_GET(result, headers=headers).content
            stream = re.search(r'"(https:.+?m3u8)"', res, re.MULTILINE)
            if stream:
                headers.update({'Referer': result})
                stream = stream.group(1).replace('\\', '')
                return stream + helpers.append_headers(headers)
            else:
                raise ResolverError('No stream found')

        else:

            raise ResolverError('No stream found')


    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True