# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
import os
import sys
from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from moq_proxy import build_ws_proxy_url

logger = common.log_utils.Logger.get_logger(__name__)
logger.disable()


class VindralResolver(ResolveUrl):

    name = 'vindral'
    domains = ['vindral.com']
    pattern = r'(?://|\.)(vindral\.com)/(?:.*?[?&](?:core\.)?channelId=)?([\w-]+)'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}

        channel_id = media_id
        lb_url = f"https://lb.cdn.vindral.com/api/v4/connect?channelId={channel_id}"
        json_data = self.net.http_GET(lb_url, headers=headers).content
        try:
            lb_json = json.loads(json_data)
        except Exception as e:
            raise ResolverError(f'Failed to parse Vindral load balancer response: {e}')

        edges = lb_json.get('edges')
        if not edges:
            raise ResolverError('No edges found in Vindral response.')

        edge = edges[0]
        url = ''.join(
            [
                edge, '/subscribe?channelId=', channel_id,
                '&audio.codec=aac&audio.bitRate=128000&video.codec=h264&video.width=1280&video.height=720&video.bitRate=3000000&burstMs=2000'
            ]
        )

        logger.log_notice(f'VINDRAL_PROXY_URL: {url}')

        return build_ws_proxy_url(url, origin='https://www.megatv.com')

    def get_url(self, host, media_id):
        return f'https://lb.cdn.{host}/api/v4/connect?channelId={media_id}'

    @classmethod
    def _is_enabled(cls):
        return True
