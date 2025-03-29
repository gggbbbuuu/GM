# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl


class Mega(ResolveUrl):

    name = 'mega'
    domains = ['megatv.com']
    pattern = r'(?://|\.)(megatv\.com)/((?:live|e?tvshows|[a-z]+)/(?:\d+/[\w-]+/|default\.asp.+)?)'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}
        stream = helpers.get_media_url(
            self.get_url(host, media_id), patterns=[r'''data-kwik_source="(?P<url>.+\.m3u8)"'''], generic_patterns=False
        )

        return stream + helpers.append_headers(headers)

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
