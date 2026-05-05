#

# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from resolveurl.lib import helpers
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError


class GreekfunResolver(ResolveUrl):

    name = 'greekfun'
    domains = ['greekfun.net']
    pattern = r'(?://|\.)(greekfun\.net)/media\.php\?type=((?:movie|series)&id=\d+(?:&episode_id=\d+)?)'

    def get_media_url(self, host, media_id):

        headers = {
            'User-Agent': common.RAND_UA,
            'Origin': 'https://{}'.format(host),
            'Referer': self.get_url(host, media_id)
        }

        video_page = self.net.http_GET(self.get_url(host, media_id), headers=headers)

        try:

            vid = helpers.scrape_sources(video_page.content, patterns=[r'''var streamUrl = "(?P<url>.*?\.mp4\?cb=\d+)";'''])
            vid = helpers.pick_source(vid)

            return vid + helpers.append_headers(headers)

        except:

            raise ResolverError('No playable video found.')


    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://{host}/media.php?type={media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
