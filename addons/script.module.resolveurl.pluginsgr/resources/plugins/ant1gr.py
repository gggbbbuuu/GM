# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
from six.moves import urllib_parse
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class Ant1GRResolver(ResolveUrl):

    name = 'ant1gr'
    domains = ['antenna.gr']
    pattern = r'(?://|\.)(antenna\.gr)/watch/(\w+/[\w-]+)'

    def get_media_url(self, host, media_id):

        ref = urllib_parse.urljoin(self.get_url(host, media_id), '/')

        headers = {
            'User-Agent': common.RAND_UA,
            'Origin': ref[:-1],
            'Referer': ref
        }

        api_url = 'https://www.antenna.gr/templates/data/PlayerDataGraphQL_v2?cid={}'

        res_json = self.net.http_GET(api_url.format(media_id.split('/')[0]), headers=headers).content

        try:

            _json = json.loads(res_json)
            stream = _json.get('url')

            return stream + helpers.append_headers(headers)

        except:

            raise ResolverError('Video not found')


    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, 'http://www.{host}/embed/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
