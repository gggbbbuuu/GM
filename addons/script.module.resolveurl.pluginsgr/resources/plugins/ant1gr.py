# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import os
import sys
import json
from six.moves import urllib_parse
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled

class Ant1GRResolver(ResolveUrl):

    name = 'ant1gr'
    domains = ['antenna.gr']
    pattern = r'(?://|\.)(antenna\.gr)/watch/(\w+/[\w-]+)'

    def get_media_url(self, host, media_id, subs=False):

        ref = urllib_parse.urljoin(self.get_url(host, media_id), '/')

        headers = {
            'User-Agent': common.RAND_UA,
            'Origin': ref[:-1],
            'Referer': ref
        }

        api_url = 'https://www.antenna.gr/templates/data/PlayerDataGraphQL_v2?cid={}'

        cid = media_id.split('/')[0]

        res_json = self.net.http_GET(api_url.format(cid), headers=headers).content

        try:
            _json = json.loads(res_json)
        except (ValueError, TypeError):
            raise ResolverError('Video not found')

        # Clips gated behind ANT1+ carry no stream, only a bounce target.
        if _json.get('should_redirect') and _json.get('video_url'):
            raise ResolverError('This video is only available on ANT1+')

        stream = _json.get('url')

        if not stream or not isinstance(stream, str):
            raise ResolverError('Video not found')

        stream = stream + helpers.append_headers(headers)

        # HostedMediaFile.resolve() unpacks `stream_url, subtitles = ...`
        # whenever subs is in the signature, so this must ALWAYS return a
        # pair - returning a bare url makes the unpack explode on any clip
        # that happens to have no subtitle track.
        if subs:
            subtitles = {}
            if _json.get('subtitle'):
                subtitles[_json.get('slang') or 'Greek'] = _json['subtitle']
            return stream, subtitles

        return stream


    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, 'http://www.{host}/embed/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('Ant1GRResolver')
