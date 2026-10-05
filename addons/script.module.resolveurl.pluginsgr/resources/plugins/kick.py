# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
import re
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class KickResolver(ResolveUrl):

    name = 'kick'
    domains = ['kick.com']
    pattern = r'(?://|\.)(kick\.com)/((?:video/[0-9a-fA-F-]{36})|(?:api/v\d+/channels/[\w-]+(?:/livestream)?)|[\w-]+)'

    def get_media_url(self, host, media_id):

        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://kick.com/'
        }

        # Case 1: Direct VOD / Video by UUID (e.g. video/<uuid>)
        if media_id.startswith('video/'):
            video_uuid = media_id.split('/', 1)[1]
            api_url = f'https://kick.com/api/v1/video/{video_uuid}'
            res = self.net.http_GET(api_url, headers=headers)
            try:
                data = json.loads(res.content)
            except Exception as e:
                raise ResolverError(f'Failed to parse Kick video JSON: {e}')

            stream = data.get('source')
            if not stream:
                raise ResolverError('No video stream source found')
            return stream + helpers.append_headers(headers)

        # Case 2: Direct API livestream endpoint (e.g. api/v2/channels/<slug>/livestream)
        if media_id.startswith('api/') and 'livestream' in media_id:
            api_url = f'https://kick.com/{media_id}'
            res = self.net.http_GET(api_url, headers=headers)
            try:
                payload = json.loads(res.content)
            except Exception as e:
                raise ResolverError(f'Failed to parse Kick livestream JSON: {e}')

            data_obj = payload.get('data') or payload
            playback_url = data_obj.get('playback_url')
            if playback_url:
                return playback_url + helpers.append_headers(headers)
            raise ResolverError('No playback_url in livestream response')

        # Case 3: Channel livestream or VOD fallback
        slug = media_id
        if slug.startswith('api/'):
            m_slug = re.search(r'channels/([\w-]+)', slug)
            if m_slug:
                slug = m_slug.group(1)

        if not slug or slug.lower() in ('video', 'categories', 'browse', 'search'):
            raise ResolverError('Invalid Kick channel')

        api_url = f'https://kick.com/api/v2/channels/{slug}'
        res = self.net.http_GET(api_url, headers=headers)
        try:
            data = json.loads(res.content)
        except Exception as e:
            raise ResolverError(f'Failed to parse Kick channel JSON: {e}')

        # Check if the channel is currently live
        is_live = bool(data.get('livestream'))
        playback_url = data.get('playback_url')

        if is_live and playback_url:
            return playback_url + helpers.append_headers(headers)

        # Fallback: check recent videos / VODs if channel is offline
        vod_url = f'https://kick.com/api/v2/channels/{slug}/videos'
        res_vod = self.net.http_GET(vod_url, headers=headers)
        try:
            vods = json.loads(res_vod.content)
        except Exception:
            vods = []

        if vods and isinstance(vods, list) and len(vods) > 0:
            stream = vods[0].get('source')
            if stream:
                return stream + helpers.append_headers(headers)

        if not is_live:
            raise ResolverError('Channel is currently offline')

        raise ResolverError('No playable stream found for channel')

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://{host}/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True
