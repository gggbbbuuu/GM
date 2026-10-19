# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Archive Watch (archivewatch.org) video resolver.
    Resolves curated public domain films from Archive Watch to direct
    Internet Archive streaming media URLs with subtitle support.
'''

import json
import os
import re
import sys

from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled


def _shard_of(item_id: str) -> str:
    h = 0x811c9dc5
    for b in item_id.encode('utf-8'):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h & 0xFF:02x}"


class ArchiveWatchResolver(ResolveUrl):

    name = 'Archive Watch'
    domains = ['archivewatch.org', 'www.archivewatch.org']
    pattern = r'(?://|\.)(archivewatch\.org)/(?:#/)?(?:item|details)/([^/?#\s]+)'

    def get_media_url(self, host, media_id, subs=False):
        shard = _shard_of(media_id)
        shard_url = f"https://archivewatch.org/details/{shard}.json"
        headers = {'User-Agent': common.RAND_UA, 'Referer': 'https://archivewatch.org/'}

        stream_url = None
        subtitles = {}

        try:
            res = self.net.http_GET(shard_url, headers=headers).content
            data = json.loads(res) if res else {}
            rec = data.get(media_id)
            if rec and isinstance(rec, list) and rec[0]:
                stream_url = rec[0]
                if subs and len(rec) > 7 and isinstance(rec[7], list):
                    for sub in rec[7]:
                        if isinstance(sub, (list, tuple)) and len(sub) >= 3:
                            lang = sub[0] or 'en'
                            sub_url = sub[2]
                            if sub_url:
                                subtitles[lang] = sub_url
        except Exception:
            pass

        # Fallback to Internet Archive metadata API if shard didn't yield a stream
        if not stream_url:
            try:
                meta_url = f"https://archive.org/metadata/{media_id}"
                res = self.net.http_GET(meta_url, headers=headers).content
                meta = json.loads(res) if res else {}
                files = meta.get('files', [])
                # Pick best playable derivative (H.264 / MP4)
                mp4_files = [f for f in files if (f.get('name') or '').lower().endswith(('.mp4', '.m4v')) and int(f.get('size', 0)) > 5000000]
                if mp4_files:
                    best = max(mp4_files, key=lambda f: int(f.get('size', 0)))
                    stream_url = f"https://archive.org/download/{media_id}/{best['name']}"
            except Exception as e:
                raise ResolverError(f"Failed to resolve Archive Watch video: {e}")

        if not stream_url:
            raise ResolverError(f"Playable video stream not found for Archive Watch item '{media_id}'")

        stream_url = stream_url + helpers.append_headers({'User-Agent': common.RAND_UA})

        if subs:
            return stream_url, subtitles
        return stream_url

    def get_url(self, host, media_id):
        return f"https://{host}/#/item/{media_id}"

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled(cls.name)
