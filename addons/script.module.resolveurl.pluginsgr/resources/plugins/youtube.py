# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Native YouTube resolver: drives the vendored ytresolver engine
    (kodion port, resources/lib/ytresolver) over ResolveURL net.py only,
    serves the generated DASH manifest through the localhost proxy and
    hands inputstream.adaptive a URL it can adapt across on the fly.
    This replaces the upstream pass-through to plugin.video.youtube.
'''

import os
import sys
import tempfile
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from moq_proxy import serve_yt_mpd, build_yt_stream_url

ADDON_ID = 'script.module.resolveurl.pluginsgr'

try:
    from ytresolver.kodion.context.standalone import StandaloneContext
    from ytresolver.youtube.client.player_client import YouTubePlayerClient
    YT_ENGINE_AVAILABLE = True
except ImportError:
    YT_ENGINE_AVAILABLE = False


def _extract_subtitles(entry):
    subtitles = {}
    try:
        for sub in entry.get('subtitles') or []:
            lang = sub.get('lang') or sub.get('name') or 'en'
            sub_url = sub.get('url')
            if sub_url:
                subtitles[lang] = sub_url
    except Exception:
        pass
    return subtitles


def _get_video_codecs():
    codecs = ['avc1']
    try:
        from kodi_six import xbmcaddon
        raw = xbmcaddon.Addon(ADDON_ID).getSetting('yt_video_codecs')
        if raw:
            parsed = [c.strip() for c in raw.split(',') if c.strip()]
            if parsed:
                codecs = parsed
    except Exception:
        pass
    return codecs


def _engine_context(video_codecs=None):
    if video_codecs is None:
        video_codecs = _get_video_codecs()

    try:
        from kodi_six import xbmcvfs
        _translate = xbmcvfs.translatePath
    except Exception:
        _translate = None

    def _real(path, fallback):
        try:
            out = _translate(path) if _translate else None
        except Exception:
            out = None
        if not out or out.startswith('special://'):
            out = fallback
        os.makedirs(out, exist_ok=True)
        return out

    tmp_base = os.path.join(tempfile.gettempdir(), 'ytresolver')
    data_dir = _real('special://temp/ytresolver/', tmp_base)
    # Engine settings must live in addon userdata (Kodi) or temp (tests),
    # never in the addon code folder / process CWD (the standalone default
    # is `os.getcwd()/config.json`).
    config_dir = _real(
        'special://profile/addon_data/{0}/'.format(ADDON_ID), tmp_base)
    context = StandaloneContext(
        data_dir=data_dir,
        config_file=os.path.join(config_dir, 'ytresolver.json'),
        video_codecs=video_codecs)
    # Full adaptive ladder for inputstream.adaptive (which selects quality
    # on the fly): allow high-frame-rate streams (60fps content like Big
    # Buck Bunny is otherwise capped at 480p) and uncap the quality
    # selection (its default tops out at the 1080p group, dropping
    # 1440p/4K/8K outright instead of binning them).
    try:
        settings = context.get_settings()
        features = set(settings.stream_features())
        if 'hfr' not in features:
            features.add('hfr')
        if 'avc1' in video_codecs:
            features.add('avc1')
        elif video_codecs:
            features.add(video_codecs[0])
        settings.stream_features(sorted(features))
        settings.mpd_video_qualities(7)
    except Exception:
        pass
    return context


def _engine_mpd_path(video_id):
    # Same location the engine wrote to: its import-time BASE_PATH,
    # translated the same way. In Kodi both are the real temp dir.
    try:
        from kodi_six import xbmcvfs
        translate = xbmcvfs.translatePath
    except Exception:
        translate = None

    def _t(path):
        try:
            out = translate(path) if translate else None
        except Exception:
            out = None
        return out or path

    base = _t(YouTubePlayerClient.BASE_PATH)
    if base.startswith('special://'):
        return None
    return os.path.join(base, video_id + '.mpd')


def _read_engine_mpd(video_id):
    path = _engine_mpd_path(video_id)
    if not path:
        return None
    try:
        with open(path, 'rb') as f:
            return f.read()
    except OSError:
        return None


class YouTubeGRResolver(ResolveUrl):
    name = 'YouTubeGR'
    domains = ['youtube.com', 'youtu.be', 'youtube-nocookie.com']
    pattern = (
        r'''(?://|\.)(?:[0-9A-Z-]+\.)?(?:(youtu\.be|youtube(?:-nocookie)?\.com)/?\S*?[^\w\s-])'''
        r'''([\w-]{11})(?=[^\w-]|$)(?![?=&+%\w.-]*(?:['"][^<>]*>|</a>))[?=&+%\w.-]*'''
    )

    def get_media_url(self, host, media_id, subs=False, audio_only=False):
        if not YT_ENGINE_AVAILABLE:
            raise ResolverError('YouTube engine is not available.')

        try:
            client = YouTubePlayerClient(context=_engine_context())
            streams, _yt_item = client.load_stream_info(
                video_id=media_id, use_mpd=True, audio_only=audio_only)
        except Exception as e:
            raise ResolverError('YouTube resolution failed: {}'.format(e))

        stream_list = list(streams) if isinstance(streams, (list, tuple, type({}.values()))) else []

        if audio_only:
            return self._pick_audio(stream_list, media_id, subs, client=client)

        selected = stream_list[0] if stream_list else {}
        if not selected.get('url'):
            raise ResolverError('No playable streams found for YouTube video {}.'.format(media_id))

        xml = _read_engine_mpd(media_id)
        if not xml:
            raise ResolverError('Failed to generate DASH manifest for YouTube video {}.'.format(media_id))

        subtitles = _extract_subtitles(selected) if subs else {}

        proxy_url = serve_yt_mpd(media_id, xml)
        if subs:
            return proxy_url, subtitles
        return proxy_url

    @staticmethod
    def _pick_audio(stream_list, media_id, subs, client=None):
        files = [s for s in stream_list
                 if s.get('url') and (s.get('audio') or {}).get('bitrate', 0) > 0
                 and not s.get('video')]
        if not files:
            # Fall back to HLS variant manifests (playable, adaptive).
            files = [s for s in stream_list if s.get('url')]
        if not files:
            raise ResolverError('No playable audio streams found for YouTube video {}.'.format(media_id))
        best = max(files, key=lambda s: (s.get('audio') or {}).get('bitrate', 0))
        headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://www.youtube.com/watch?v={0}'.format(media_id),
        }
        if client and hasattr(client, '_process_url_params'):
            try:
                proxied_url = client._process_url_params(best['url'], stream_proxy=True, headers=headers)
                if proxied_url:
                    stream_url = build_yt_stream_url(proxied_url)
                else:
                    stream_url = best['url'] + helpers.append_headers(headers)
            except Exception:
                stream_url = best['url'] + helpers.append_headers(headers)
        else:
            stream_url = best['url'] + helpers.append_headers(headers)

        if subs:
            return stream_url, _extract_subtitles(best)
        return stream_url

    def get_url(self, host, media_id):
        return 'https://www.youtube.com/watch?v={0}'.format(media_id)

    @classmethod
    def _is_enabled(cls):
        return True

    @classmethod
    def _get_priority(cls):

        return 80
