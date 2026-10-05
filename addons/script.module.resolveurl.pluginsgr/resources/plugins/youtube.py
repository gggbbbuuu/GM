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
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from moq_proxy import serve_yt_mpd

try:
    from ytresolver.kodion.context.standalone import StandaloneContext
    from ytresolver.youtube.client.player_client import YouTubePlayerClient
    YT_ENGINE_AVAILABLE = True
except ImportError:
    YT_ENGINE_AVAILABLE = False


def _engine_context():
    data_dir = None
    try:
        from kodi_six import xbmcvfs
        data_dir = xbmcvfs.translatePath('special://temp/ytresolver/') or None
    except Exception:
        pass
    if not data_dir:
        data_dir = os.path.join(tempfile.gettempdir(), 'ytresolver')
    context = StandaloneContext(data_dir=data_dir)
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

    def get_media_url(self, host, media_id, subs=False):
        if not YT_ENGINE_AVAILABLE:
            raise ResolverError('YouTube engine is not available.')

        try:
            client = YouTubePlayerClient(context=_engine_context())
            streams, _yt_item = client.load_stream_info(video_id=media_id, use_mpd=True)
        except Exception as e:
            raise ResolverError('YouTube resolution failed: {}'.format(e))

        stream_list = list(streams) if isinstance(streams, (list, tuple, type({}.values()))) else []
        selected = stream_list[0] if stream_list else {}
        if not selected.get('url'):
            raise ResolverError('No playable streams found for YouTube video {}.'.format(media_id))

        xml = _read_engine_mpd(media_id)
        if not xml:
            raise ResolverError('Failed to generate DASH manifest for YouTube video {}.'.format(media_id))

        subtitles = {}
        if subs:
            try:
                for sub in selected.get('subtitles') or []:
                    lang = sub.get('lang') or sub.get('name') or 'en'
                    sub_url = sub.get('url')
                    if sub_url:
                        subtitles[lang] = sub_url
            except Exception:
                pass

        proxy_url = serve_yt_mpd(media_id, xml)
        if subs:
            return proxy_url, subtitles
        return proxy_url

    def get_url(self, host, media_id):
        return 'https://www.youtube.com/watch?v={0}'.format(media_id)

    @classmethod
    def _is_enabled(cls):
        return True

    @classmethod
    def _get_priority(cls):

        return 80
