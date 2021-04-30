# -*- coding: utf-8 -*-

'''
    AliveGR Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from resolveurl import common
from resolveurl.plugins.lib import helpers
from resolveurl.resolver import ResolveUrl


class Mega(ResolveUrl):

    name = 'mega'
    domains = ['megatv.com']
    pattern = r'(?://|\.)(megatv\.com)/((?:live|e?tvshows|[a-z]+)/(?:\d+/[\w-]+/|default\.asp.+)?)'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        stream = helpers.scrape_sources(res, scheme='https')
        source = helpers.pick_source(stream)

        return source + helpers.append_headers(headers)

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
