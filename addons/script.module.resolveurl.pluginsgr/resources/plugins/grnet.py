# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class GrnetResolver(ResolveUrl):

    name = 'Grnet'
    domains = ['diavlos-cache.cnt.grnet.gr']
    pattern = r'(?://|\.)(diavlos-cache\.cnt\.grnet\.gr)/app/index\.html#/el/embed/room/(\d+)'
    api_url = 'https://diavlos-cache.cnt.grnet.gr/config/channels.json'

    def get_media_url(self, host, media_id):

        headers = {
            'User-Agent': common.RAND_UA
        }

        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(self.api_url, headers=headers)
        data = json.loads(res.content)

        try:
            headers.update({'Referer': web_url})
            streams = [(s['title'], s['mainStreamUrl']) for s in data if str(s.get('id')) == media_id]
            uri = helpers.pick_source(helpers.sort_sources_list(streams))
            return uri + helpers.append_headers(headers)
        except IndexError:
            raise ResolverError('No stream found')


    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://{host}/app/index.html#/el/embed/room/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True