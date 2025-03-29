# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
import re
from os.path import split
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class Ert(ResolveUrl):

    name = 'ert'
    domains = ['webtv.ert.gr', 'www.ertflix.gr', 'archive.ert.gr']
    pattern = r'//((?:www|archive|webtv)\.ert(?:flix)?\.gr)/(\d+/|(?:epg|vod)/(?:channel|vod)(?:/|\.)(?:\d{6}|[\w-]+))'
    base_api_link = 'https://api.app.ertflix.gr/'
    device_key = '5ac9136c63fb4e682c94e13128540e43'
    get_regions = ''.join(
        [
            base_api_link,
            'v1/IpRegion/GetRegionsForIpAddress?platformCodename=www&$headers=%7B%22X-Api-Date-Format%22:%22iso%22,%22X-Api-Camel-Case%22:true%7D'
        ]
    )
    acquire_content = ''.join(
        [
            base_api_link, 'v1/Player/AcquireContent?platformCodename=www&deviceKey={0}&codename={1}'
        ]
    )
    headers = {'User-Agent': common.RAND_UA, 'Referer': 'https://www.ertflix.gr/'}

    def get_media_url(self, host, media_id):

        if 'archive' in host:

            web_url = self.get_url(host, media_id)
            res = self.net.http_GET(web_url, headers=self.headers).content
            iframe = re.search(r'''iframe src=['"](https.+?)['"]''', res)

            if iframe:

                iframe = iframe.group(1)
                html = self.net.http_GET(iframe.replace(' ', '%20'), headers=self.headers).content
                streams = re.findall(r'''(?:HLSLink|var stream(?:ww)?) +?= ['"](https.+)['"]''', html)
                return streams[0] + helpers.append_headers(self.headers)

            else:

                raise ResolverError('Error in searching urls from within the html')

        else:

            codename = split(media_id)[1]

            if 'epg/channel' in media_id:
                res = self.net.http_GET(self.acquire_content.format(self.device_key, codename), headers=self.headers).content
                _json = json.loads(res)

                return self._filter_m3u8(_json) + helpers.append_headers(self.headers)

            elif len(codename) > 10:

                codename = codename.partition('-')[2]
                res = self.net.http_GET(self.acquire_content.format(self.device_key, codename), headers=self.headers).content
                _json = json.loads(res)

                return self._filter_m3u8(_json) + helpers.append_headers(self.headers)

            else:

                web_url = self.get_url(host, media_id)
                res = self.net.http_GET(web_url, headers=self.headers).content
                match = re.search(r'codenameToId":{"([\w-]+)', res)

                if match:

                    codename = match.group(1)
                    res = self.net.http_GET(self.acquire_content.format(self.device_key, codename), headers=self.headers).content
                    _json = json.loads(res)

                    return self._filter_m3u8(_json)+ helpers.append_headers(self.headers)

                else:

                    raise ResolverError('Failed to find codename to resolve video content')

    @staticmethod
    def _filter_m3u8(_json):

        for media in _json['MediaFiles']:

            if media['RoleName'] == 'main':

                if len(media['Formats']) == 1:

                    return media['Formats'][0]['Url']

                else:

                    for result in media['Formats']:
                        if '.m3u8' in result['Url']:
                            return result['Url']

        raise ResolverError('Failed to resolve video content')

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, 'https://{host}/{media_id}')

    # @common.cache.cache_method(cache_limit=24)
    # def _geo_detect(self):
    #
    #     _json = self.net.http_GET('https://geoip.siliconweb.com/geo.json').content
    #
    #     _json = json.loads(_json)
    #
    #     if 'GR' in _json['country']:
    #         return True
    #
    # @common.cache.cache_method(cache_limit=24)
    # def _get_regions(self):
    #
    #     res = self.net.http_GET(self.get_regions, headers=self.headers).content
    #
    #     return json.loads(res)['regions']

    @classmethod
    def _is_enabled(cls):
        return True
