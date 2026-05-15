# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''
import json
import re
import base64
import xbmcaddon
import xbmc
from six.moves import urllib_parse
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

logger = common.log_utils.Logger.get_logger(__name__)
logger.disable()


class MegaTVResolver(ResolveUrl):

    name = 'megatv'
    domains = ['megatv.com']
    pattern = r'(?://|\.)(megatv\.com)/((?:t|e|g|)?(?:tvshows|\d+)/\d+/(?:\d{2}/)?[\w-]+/|live/?)'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}

        if media_id != 'live/':

            try:
                stream = helpers.get_media_url(
                    self.get_url(host, media_id), patterns=[r'''data-kwik_source="(?P<url>.+\.m3u8)"'''], generic_patterns=False
                )

                return stream + helpers.append_headers(headers)

            except:
                raise ResolverError('No playable video found.')

        else:

            if not xbmc.getCondVisibility('System.HasAddon(plugin.video.alivegr)'):
                raise ResolverError('AliveGR addon is required to play live streams from MegaTV.')

            html = self.net.http_GET(self.get_url(host, media_id), headers=headers).content
            js = re.findall(r'<script type="text/javascript" src="(.+?)"', html)
            js = [i for i in js if 'live-' in i][0]
            js = self.net.http_GET(js, headers=headers).content
            channel_id = re.search(r'channelId=([\w-]+)', js).group(1)
            lb_url = f"https://lb.cdn.vindral.com/api/v4/connect?channelId={channel_id}"
            json_data = self.net.http_GET(lb_url, headers=headers).content
            lb_json = json.loads(json_data)
            edge = lb_json.get('edges')[0]
            url = ''.join(
                [
                    edge, '/subscribe?channelId=', channel_id,
                 '&audio.codec=aac&audio.bitRate=128000&video.codec=h264&video.width=1280&video.height=720&video.bitRate=3000000&burstMs=2000'
                ]
            )

            logger.log_notice(r'MEGA_PROXY_URL: {0}'.format(url))

            ws_b64 = base64.urlsafe_b64encode(url.encode('utf-8')).decode('utf-8')
            port = xbmcaddon.Addon('plugin.video.alivegr').getSetting('proxy_port') or '50199'
            origin = urllib_parse.quote('https://www.megatv.com')

            return 'http://127.0.0.1:{port}/mega.flv?ws={ws_b64}&origin={origin}'.format(
                port=port, ws_b64=ws_b64, origin=origin
            )

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
