# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.

    novasports.gr on-demand videos.

    The site is a WordPress install whose theme embeds one of four players
    depending on where a clip is actually hosted. Each one is unwrapped here:

      ondemand-kwik  <div id="mainPlayer" data-video-url=... data-video-vtt=...>
      glomex         <glomex-integration integration-id=... playlist-id=...>
                     -> Glomex's public playlist service
      firstview      cnx({playerId, mediaId}) -> Connatix player, spoken protobuf
      youtube        schema.org VideoObject contentUrl -> delegate to YouTubeGR

    The protobuf messages are hand rolled, so the plugin stays a single
    self-contained file with no compiled schema.
'''

import json
import os
import re
import sys
import urllib.request
import uuid
from urllib.parse import urlencode

from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled

BASE_LINK = 'https://www.novasports.gr'

GLOMEX_PLAYLIST_API = 'https://integration-cloudfront-eu-west-1.mes.glomex.cloud/'

CONNATIX_PLS_LINK = 'https://capi.connatix.com/core/pls'
CONNATIX_VID_LINK = 'https://vid.connatix.com'
CONNATIX_BUNDLE_VERSION = 791109792
CONNATIX_TIER = 2


# ---------------------------------------------------------------------------
# Page parsing (pure helpers, no IO)
# ---------------------------------------------------------------------------

def video_source(html):

    match = re.search(r'\bvideo_source-([a-z0-9-]+)\b', html)
    if match:
        return match.group(1)

    if 'glomex-integration' in html:
        return 'glomex'

    if re.search(r'cnx\(\{', html):
        return 'firstview'

    if 'id="mainPlayer"' in html:
        return 'ondemand-kwik'

    return ''


def resolve_kwik(html):

    stream = re.search(r'id="mainPlayer".*?data-video-url="([^"]+)"', html, re.S)
    if not stream:
        raise ResolverError('Kwik player data not found')

    result = {'stream': unescape(stream.group(1))}

    subtitles = re.search(r'id="mainPlayer".*?data-video-vtt="([^"]+)"', html, re.S)
    if subtitles:
        result['subtitle'] = unescape(subtitles.group(1))

    return result


def youtube_id(html):

    for pattern in (r'youtube(?:-nocookie)?\.com/embed/([\w-]{6,})',
                    r'youtube\.com/watch\?[^\s"\']*v=([\w-]{6,})',
                    r'youtu\.be/([\w-]{6,})',
                    r'"contentUrl"\s*:\s*"https://www\.youtube\.com/embed/([\w-]{6,})'):
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    return ''


def unescape(text):

    try:
        from html import unescape

        return unescape(text)
    except Exception:
        return text


# ---------------------------------------------------------------------------
# protobuf primitives
# ---------------------------------------------------------------------------

def pb_varint(value):

    out = bytearray()
    while True:
        chunk = value & 0x7F
        value >>= 7
        if value:
            out.append(chunk | 0x80)
        else:
            out.append(chunk)
            return bytes(out)


def pb_string(number, value):

    if not value:
        return b''

    raw = value.encode('utf-8') if isinstance(value, str) else value
    return pb_varint((number << 3) | 2) + pb_varint(len(raw)) + raw


def pb_int(number, value):

    return b'' if value is None else pb_varint(number << 3) + pb_varint(value)


def pb_bool(number, value):

    return b'' if value is None else pb_varint(number << 3) + pb_varint(1 if value else 0)


def pb_read(buf, index):

    value = shift = 0
    while True:
        byte = buf[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, index
        shift += 7


def pb_parse(buf):
    """Generic protobuf walk -> {field_number: [values]}."""

    out, index, length = {}, 0, len(buf)

    while index < length:
        key, index = pb_read(buf, index)
        number, wire = key >> 3, key & 7

        if wire == 0:
            value, index = pb_read(buf, index)
        elif wire == 2:
            size, index = pb_read(buf, index)
            value, index = buf[index:index + size], index + size
        elif wire == 5:
            value, index = buf[index:index + 4], index + 4
        elif wire == 1:
            value, index = buf[index:index + 8], index + 8
        else:
            raise ValueError('Unsupported wire type {}'.format(wire))

        out.setdefault(number, []).append(value)

    return out


def pb_text(raw):

    try:
        text = raw.decode('utf-8')
    except Exception:
        return ''

    return text if text.isprintable() and text else ''


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class NovasportsResolver(ResolveUrl):

    name = 'novasports'
    domains = ['novasports.gr']
    pattern = r'(?://|\.)(novasports\.gr)/web-tv/((?:.+/)*?video/\d+/.+?)/?$'

    def get_media_url(self, host, media_id, subs=False):

        page_url = self.get_url(host, media_id)

        headers = {'User-Agent': common.RAND_UA, 'Accept': '*/*'}

        try:
            html = self.net.http_GET(page_url, headers=headers, timeout=30).content
        except Exception as e:
            raise ResolverError('Could not load the video page: {}'.format(e))

        source = video_source(html)

        if not source:
            raise ResolverError('No recognised player found for this video.')

        # YouTube clips are hosted elsewhere entirely; hand them to the
        # YouTubeGR resolver rather than duplicating its engine here.
        if source == 'youtube':
            return self._resolve_youtube(html, subs)

        try:
            if source == 'glomex':
                resolved = self._resolve_glomex(page_url, html, headers)
            elif source == 'firstview':
                resolved = self._resolve_firstview(page_url, html, headers)
            else:
                resolved = resolve_kwik(html)
        except Exception as e:
            raise ResolverError(str(e) or 'Resolution failed')

        stream = resolved.get('stream')

        if not stream:
            raise ResolverError('No playable stream found for this video.')

        # The Kwik CDN (siliconweb) refuses anything without a Referer, so the
        # headers travel with the url. The other CDNs are happy either way.
        stream_headers = {'User-Agent': common.RAND_UA, 'Referer': page_url}
        stream = stream + helpers.append_headers(stream_headers)

        # HostedMediaFile.resolve() unpacks `stream_url, subtitles = ...`
        # whenever subs is in this signature, so this must ALWAYS return a
        # pair here - returning a bare url makes the unpack explode on any
        # clip that happens to have no subtitle track.
        if subs:
            subtitle = resolved.get('subtitle')
            return stream, ({'Greek': subtitle} if subtitle else {})

        return stream

    # --- glomex ---------------------------------------------------------

    def _resolve_glomex(self, page_url, html, headers):

        match = re.search(
            r'<glomex-integration[^>]*integration-id="([^"]+)"[^>]*playlist-id="([^"]+)"', html
        )
        if not match:
            raise ResolverError('Glomex integration markup not found')

        query = urlencode({
            'integration_id': match.group(1),
            'playlist_id': match.group(2),
            'current_url': page_url,
        })

        try:
            data = json.loads(
                self.net.http_GET('{}?{}'.format(GLOMEX_PLAYLIST_API, query),
                                  headers=headers, timeout=30).content
            )
        except Exception as e:
            raise ResolverError('Glomex playlist request failed: {}'.format(e))

        clips = data.get('videos') or []
        if not clips:
            raise ResolverError('Glomex playlist is empty')

        sources = clips[0].get('source') or {}
        stream = sources.get('hls') or sources.get('progressive')

        if not stream:
            raise ResolverError('Glomex clip has no playable source')

        resolved = {'stream': stream}

        for track in clips[0].get('text_tracks') or []:
            url = track.get('url') or track.get('file')
            if url:
                resolved['subtitle'] = url
                break

        return resolved

    # --- connatix / firstview -------------------------------------------

    def _resolve_firstview(self, page_url, html, headers):

        # The page hands the player a playerId/mediaId pair and nothing else:
        #     cnx({ playerId: "...", mediaId: "..." }).render("...")
        call = re.search(r'cnx\(\{(?P<args>[^}]*)\}\)', html)

        if not call:
            raise ResolverError('Connatix player call not found')

        token = re.search(r'playerId:\s*"(?P<id>[^"]+)"', call.group('args'))

        if not token:
            raise ResolverError('Connatix player id not found')

        token = token.group('id')

        media_id = re.search(r'mediaId:\s*"(?P<id>[^"]+)"', call.group('args'))
        media_id = media_id.group('id') if media_id else ''

        if not media_id:
            raise ResolverError('Connatix media id missing')

        entries = self._connatix_playlist(page_url, token, media_id, headers)

        entry = next((e for e in entries if e['media_id'] == media_id), None)
        entry = entry or (entries[0] if entries else None)

        if not entry:
            raise ResolverError('Connatix playlist is empty')

        metadata = self._connatix_metadata(entry, headers)

        if not metadata['hls']:
            raise ResolverError('Connatix media has no HLS path')

        base = '{}/{}'.format(CONNATIX_VID_LINK, entry['path'])

        # Renditions live under the multimedia id, the master playlist does not.
        stream = '{}/{}'.format(base, metadata['hls'])
        if metadata['multimedia_id']:
            stream = '{}/mmid-{}/{}'.format(base, metadata['multimedia_id'], metadata['hls'])

        resolved = {'stream': stream}

        # Subtitle tracks sit directly under the media folder.
        if metadata['tracks']:
            resolved['subtitle'] = '{}/{}'.format(base, metadata['tracks'][0])

        return resolved

    def _connatix_playlist(self, page_url, token, media_id, headers):
        """
        contracts.core.pls.v1.ElementsRequest

        token_list(1), page_url(3), force_player_id(7), player_version(10),
        referrer(32), force_media_id_list(36), server_ab0..5(48..53),
        session_id(54), is_domain_parsed(24), implementation_type(25),
        is_tracking_disabled(31), event_timestamp(33)
        """

        body = pb_string(1, token)
        body += pb_string(3, page_url)
        body += pb_string(7, token)
        body += pb_int(10, CONNATIX_BUNDLE_VERSION)
        body += pb_string(32, BASE_LINK + '/')
        body += pb_string(36, media_id)

        for offset, value in enumerate((553, 1500, 500, 0, 0, 0)):
            if value:
                body += pb_int(48 + offset, value)

        body += pb_string(54, str(uuid.uuid4()))
        body += pb_bool(24, False)
        body += pb_int(25, 0)
        body += pb_bool(31, True)
        body += pb_int(33, 1791900000000)

        url = '{}?{}'.format(
            CONNATIX_PLS_LINK, urlencode({'v': CONNATIX_BUNDLE_VERSION, 'tier': CONNATIX_TIER})
        )

        post_headers = dict(headers)
        post_headers.update({'Content-Type': 'multipart/form-data',
                             'Origin': BASE_LINK,
                             'Referer': page_url})

        # Net.http_POST only accepts form data or JSON, so this protobuf body
        # has to go out through urllib. ResolveURL's Net installs a global
        # opener with Kodi's cacert, so urlopen picks that up on its own.
        request = urllib.request.Request(url, data=body, headers=post_headers, method='POST')

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except Exception as e:
            raise ResolverError('Connatix playlist request failed: {}'.format(e))

        response = pb_parse(raw)

        if 1 in response:
            raise ResolverError(pb_text(response[1][0]) or 'Connatix rejected the request')

        entries = []

        for player in response.get(10, []):
            try:
                player_fields = pb_parse(player)
            except ValueError:
                continue

            for item in player_fields.get(60, []):
                try:
                    fields = pb_parse(item)
                except ValueError:
                    continue

                entry_id = pb_text(fields.get(1, [b''])[0])

                if not entry_id:
                    continue

                revision = fields.get(2, [0])[0]
                version = pb_text(fields.get(3, [b''])[0])

                entries.append({
                    'media_id': entry_id,
                    'revision': revision,
                    'version': version,
                    'path': '{}/{}'.format(entry_id, version) if version else entry_id,
                })

        return entries

    def _connatix_metadata(self, entry, headers):
        """
        contracts.vid.elements.v1.ElementsMediaMetadataResponse

        track_list(6), hls_file_path(11), multimedia_id(17)
        """

        url = '{}/{}/{}_media.bin'.format(CONNATIX_VID_LINK, entry['path'], entry['revision'])

        metadata_headers = dict(headers)
        metadata_headers['Referer'] = BASE_LINK + '/'

        try:
            # nodecode: this net decodes as ascii without a charset, which
            # would corrupt the protobuf payload.
            raw = self.net.http_GET(url, headers=metadata_headers,
                                    timeout=30).nodecode(True).content
        except Exception as e:
            raise ResolverError('Connatix metadata request failed: {}'.format(e))

        fields = pb_parse(raw)

        tracks = []
        for track in fields.get(6, []):
            try:
                track_fields = pb_parse(track)
            except ValueError:
                continue
            file = pb_text(track_fields.get(1, [b''])[0])
            if file:
                tracks.append(file)

        return {
            'hls': pb_text(fields.get(11, [b''])[0]),
            'multimedia_id': pb_text(fields.get(17, [b''])[0]),
            'tracks': tracks,
        }

    # --- youtube --------------------------------------------------------

    @staticmethod
    def _resolve_youtube(html, subs=False):

        video_id = youtube_id(html)

        if not video_id:
            raise ResolverError('YouTube video id not found.')

        try:
            from youtube import YouTubeGRResolver
        except ImportError as e:
            raise ResolverError('The YouTubeGR plugin is unavailable: {}'.format(e))

        if not YouTubeGRResolver._is_enabled():
            raise ResolverError('The YouTubeGR plugin is disabled.')

        return YouTubeGRResolver().get_media_url('youtube.com', video_id, subs=subs)

    # --- ResolveUrl plumbing --------------------------------------------

    def get_url(self, host, media_id):

        return 'https://www.{}/web-tv/{}'.format(host, media_id)

    def valid_url(self, url, host):

        return re.search(self.pattern, url, re.I) is not None

    @classmethod
    def _is_enabled(cls):

        return plugin_enabled('NovasportsResolver')

    @classmethod
    def _get_priority(cls):

        return 100