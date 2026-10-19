# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
import os
import re
import sys
import time
from urllib.parse import quote_plus
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled


class Ert(ResolveUrl):

    name = 'Ertflix'
    domains = ['ertflix.gr', 'www.ertflix.gr', 'ertflix-worker.twilight0.workers.dev']
    pattern = (
        r'//((?:www\.)?ertflix\.gr|ertflix-worker\.twilight0\.workers\.dev)'
        r'/(?:#\/)?(details\/[\w\-]+(?:\/(?:point\/[\w\-]+\/|play\/)[\w\-]+)?'
        r'|liveTV\/[\w\-]+'
        r'|watch\/(?:movie|episode|live|series)\/[\w\-]+'
        r'|watch\/series\/[\w\-]+\/(?:season\/\d+\/)?episode\/\d+'
        r'|watch\/catchup\/[\w\-]+\/\d+\/\d+)'
    )

    base_api_link = 'https://api.ertflix.opentv.com/'
    tenant_headers = {'nv-tenant-id': 'nagra', 'tenantId': 'nagra'}
    headers = {'User-Agent': common.RAND_UA, 'Referer': 'https://www.ertflix.gr/'}

    _token = None
    _token_expiry = 0

    def _session_token(self):

        now = time.time()
        if self._token and now < self._token_expiry - 600:
            return self._token

        res = self.net.http_POST(
            self.base_api_link + 'ias/v2/anonymoustoken', {},
            headers=dict(self.headers, **{'Content-Type': 'application/json', 'Accept': '*/*'},
                         **self.tenant_headers),
            jdata=True
        ).json

        self._token = res['access_token']
        self._token_expiry = now + int(res.get('expires_in', 3888000))
        return self._token

    def _api_get(self, path, params=None, token=None):

        query = ''
        if params:
            query = '?' + '&'.join(
                '{0}={1}'.format(k, quote_plus(str(v))) for k, v in params.items()
            )

        headers = dict(self.headers, **self.tenant_headers)
        headers.update({
            'Accept-Language': 'el_GR',
            'Authorization': 'Bearer ' + (token or self._session_token()),
            'Nagra-Device-Type': 'SmartTV',
            'Nagra-Target': 'tv'
        })

        res = self.net.http_GET(self.base_api_link + path + query, headers=headers)
        return json.loads(res.nodecode(True).content.decode('utf-8'))

    @staticmethod
    def _pick_media(media):

        media_list = media if isinstance(media, list) else ([media] if media else [])
        candidates = [
            m for m in media_list
            if m and m.get('uri') and 'example.com' not in m.get('uri')
        ]
        if not candidates:
            return None, None

        stream = next((m for m in candidates if '.mpd' in m.get('uri')), candidates[0])
        return stream.get('uri'), stream.get('drmId')

    widevine_url = 'https://ertp8gz3.anycast.nagra.com/ERTP8GZ3/wvls/contentlicenseservice/v1/licenses'

    def _playout(self, stream_url, drm_id, token):

        if not drm_id:
            return stream_url, None

        data = self._api_get(
            'urlbuilder/v1/playout/content/token',
            {'content_id': drm_id, 'type': 'account', 'content_URL': stream_url},
            token=token
        )

        url = data.get('playbackUrl') or data.get('cdnAccessToken') or stream_url
        content_token = None
        try:
            content_token = data['contentAuthToken']['content_token']
        except (KeyError, TypeError):
            pass

        return url, content_token

    def _build_stream_result(self, stream_url, content_token):

        headers = dict(self.headers)
        if content_token:
            licence_key = '{0}|nv-authorizations={1}&nv-tenant-id=nagra&Content-Type=application/octet-stream|R{{SSM}}|'.format(
                self.widevine_url, content_token
            )
            headers['DRM'] = json.dumps(['com.widevine.alpha', licence_key])

        return stream_url + helpers.append_headers(headers)

    def _live_channel(self, channel_id, token):

        data = self._api_get('metadata/delivery/ERT/btv/services', token=token)

        candidates = []
        for service in data.get('services', []):
            technical = service.get('technical', {}) or {}
            editorial = service.get('editorial', {}) or {}
            device_types = service.get('deviceType') or technical.get('deviceType') or []
            if 'SmartTV' not in device_types:
                continue
            if service.get('e') not in (channel_id,) and editorial.get('id') != channel_id \
                    and editorial.get('stationId') != channel_id:
                continue
            url = technical.get('NetworkLocation')
            if url:
                candidates.append((url, technical.get('drmId'), (technical.get('shortTermCatchUpParameters') or {}).get('sourceId')))

        if not candidates:
            raise ResolverError('Unknown live channel: {0}'.format(channel_id))

        candidates.sort(key=lambda c: 0 if '.mpd' in c[0] else 1)
        return candidates[0]

    @staticmethod
    def _catchup_url(stcu_template, start, end):
        import datetime

        def fmt(ts):
            return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')

        return stcu_template.replace('{startTime}', fmt(start)).replace('{endTime}', fmt(end))

    def _episode_by_numbers(self, series_ref, season_num, ep_num, token):

        if series_ref.endswith('_E0'):
            series_ref = series_ref[:-3]

        seasons = self._api_get(
            'metadata/delivery/ERT/vod/series',
            {
                'filter': json.dumps(
                    {'seriesRef': series_ref, 'locale': 'el_GR'}, separators=(',', ':')
                ),
                'sort': '[["SeasonNumberNumeric", 1]]', 'offset': 0, 'limit': 300
            },
            token=token
        ).get('series', [])

        if not seasons:
            raise ResolverError('No seasons found for series: {0}'.format(series_ref))

        if season_num is None:
            season = seasons[0]
        else:
            season = next(
                (s for s in seasons
                 if str(s.get('SeasonNumberNumeric', s.get('SeasonNumber'))) == str(season_num)),
                None
            )
            if season is None:
                raise ResolverError(
                    'No season {0} for series: {1}'.format(season_num, series_ref)
                )

        episodes = self._api_get(
            'metadata/delivery/v2/ERT/vod/editorials',
            {
                'filter': json.dumps(
                    {'editorial.seasonRef': season.get('id'), 'locale': 'el_GR'},
                    separators=(',', ':')
                ),
                'sort': '[["editorial.episodeNumber", 1]]', 'offset': 0, 'limit': 300
            },
            token=token
        ).get('editorials', [])

        episode = next(
            (e for e in episodes
             if str(e.get('EpisodeNumber', e.get('episodeNumber'))) == str(ep_num)),
            None
        )
        if episode is None:
            raise ResolverError(
                'No episode {0} in season {1}'.format(ep_num, season.get('SeasonNumber'))
            )

        return episode.get('id')

    def _first_episode(self, series_ref, token):

        seasons = self._api_get(
            'metadata/delivery/ERT/vod/series',
            {
                'filter': json.dumps(
                    {'seriesRef': series_ref, 'locale': 'el_GR'}, separators=(',', ':')
                ),
                'sort': '[["SeasonNumberNumeric", 1]]', 'offset': 0, 'limit': 300
            },
            token=token
        ).get('series', [])

        if not seasons:
            raise ResolverError('No seasons found for series: {0}'.format(series_ref))

        episodes = self._api_get(
            'metadata/delivery/v2/ERT/vod/editorials',
            {
                'filter': json.dumps(
                    {'editorial.seasonRef': seasons[0].get('id'), 'locale': 'el_GR'},
                    separators=(',', ':')
                ),
                'sort': '[["editorial.episodeNumber", 1]]', 'offset': 0, 'limit': 1
            },
            token=token
        ).get('editorials', [])

        if not episodes:
            raise ResolverError('No episodes found for series: {0}'.format(series_ref))

        return episodes[0].get('id')

    def get_media_url(self, host, media_id):

        try:
            token = self._session_token()

            parts = media_id.strip('/').split('/')

            if parts[0] == 'watch':
                # worker direct links share the same ids: map onto site routes
                if len(parts) == 3 and parts[1] in ('movie', 'episode'):
                    parts = ['details', parts[2]]
                elif len(parts) == 3 and parts[1] == 'live':
                    parts = ['liveTV', parts[2]]
                elif len(parts) == 3 and parts[1] == 'series':
                    parts = ['details', parts[2]]
                elif len(parts) == 5 and parts[1] == 'series' and parts[3] == 'episode':
                    episode_id = self._episode_by_numbers(parts[2], None, parts[4], token)
                    parts = ['details', 'x', 'play', episode_id]
                elif len(parts) == 7 and parts[1] == 'series' and parts[3] == 'season' and parts[5] == 'episode':
                    episode_id = self._episode_by_numbers(parts[2], parts[4], parts[6], token)
                    parts = ['details', 'x', 'play', episode_id]
                elif len(parts) == 5 and parts[1] == 'catchup':
                    channel = parts[2]
                    stream_url, drm_id, stcu = self._live_channel(channel, token)
                    if stcu:
                        try:
                            stream_url = self._catchup_url(stcu, parts[3], parts[4])
                        except (TypeError, ValueError):
                            pass
                    stream_url, content_token = self._playout(stream_url, drm_id, token)
                    return self._build_stream_result(stream_url, content_token)
                else:
                    raise ResolverError('Unsupported ERT URL: {0}'.format(media_id))

            if parts[0] == 'liveTV' and len(parts) == 2:
                stream_url, drm_id = self._live_channel(parts[1], token)[:2]

            elif parts[0] == 'details' and len(parts) == 2:
                vod_id = parts[1]
                if vod_id.endswith('_E0'):
                    vod_id = self._first_episode(vod_id[:-3], token)
                elif re.fullmatch(r'ERT_[A-Z0-9]+', vod_id) and not vod_id.startswith('ERT_M'):
                    # series master id (e.g. ERT_PS058510): no mediacard, go via seasons
                    vod_id = self._first_episode(vod_id, token)
                card = self._api_get(
                    'metadata/v1/vod/{0}/mediacard'.format(vod_id),
                    {'deviceType': 'SmartTV'}, token=token
                )
                stream_url, drm_id = self._pick_media(card.get('media'))
                if not stream_url:
                    raise ResolverError('No playable stream for: {0}'.format(parts[1]))

            elif parts[0] == 'details' and len(parts) == 5 and parts[2] == 'point':
                episode_id = parts[4]
                card = self._api_get(
                    'metadata/v1/vod/{0}/mediacard'.format(episode_id),
                    {'deviceType': 'SmartTV'}, token=token
                )
                stream_url, drm_id = self._pick_media(card.get('media'))
                if not stream_url:
                    raise ResolverError('No playable stream for episode: {0}'.format(episode_id))

            elif parts[0] == 'details' and len(parts) == 4 and parts[2] == 'play':
                episode_id = parts[3]
                card = self._api_get(
                    'metadata/v1/vod/{0}/mediacard'.format(episode_id),
                    {'deviceType': 'SmartTV'}, token=token
                )
                stream_url, drm_id = self._pick_media(card.get('media'))
                if not stream_url:
                    raise ResolverError('No playable stream for episode: {0}'.format(episode_id))

            else:
                raise ResolverError('Unsupported ERT URL: {0}'.format(media_id))

            stream_url, content_token = self._playout(stream_url, drm_id, token)
            return self._build_stream_result(stream_url, content_token)

        except ResolverError:
            raise
        except Exception as e:
            raise ResolverError('ERT resolve failed: {0}'.format(e))

    def get_url(self, host, media_id):

        if media_id.startswith('watch/'):
            return self._default_get_url(host, media_id, 'https://{host}/{media_id}')

        return self._default_get_url(host, media_id, 'https://{host}/#/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('Ert')
