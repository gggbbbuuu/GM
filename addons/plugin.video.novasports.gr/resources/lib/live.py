# -*- coding: utf-8 -*-

'''
    Novasports.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

# The site itself no longer offers live streams, but NovaSports keeps its
# channel on YouTube and embeds those broadcasts in the web tv listings.
# This module builds the "Live" section from that channel and, at play time,
# checks whether a stream has actually started: a scheduled premiere cannot
# be played, so the user gets told when it starts instead of an error.
import json
import re

from tulip import kodi

from .api import _fetch
from .constants import YT_CHANNEL, YT_WATCH

try:
    import scrapetube

    _scrapetube = True
except ImportError:
    _scrapetube = False


def available():

    return _scrapetube


def _i18n(number):
    try:
        return kodi.i18n(number)
    except Exception:
        return str(number)


def streams(limit=30):
    """Channel streams, newest first."""

    if not _scrapetube:
        raise RuntimeError('script.module.scrapetube is not installed')

    items = []

    for entry in scrapetube.get_channel(
        channel_url=YT_CHANNEL, limit=limit, content_type='streams', sleep=0
    ):
        video_id = entry.get('videoId')
        if not video_id:
            continue

        is_live = bool(entry.get('is_live'))

        items.append({
            'id': video_id,
            'title': entry.get('title_text') or '',
            'image': _thumbnail(entry),
            'is_live': is_live,
            'status': _status_label(entry, is_live),
        })

    return items


def _thumbnail(entry):

    thumbs = (entry.get('thumbnail') or {}).get('thumbnails') or []

    return thumbs[-1]['url'] if thumbs else ''


def _status_label(entry, is_live):

    """YouTube's own wording for scheduled / archived broadcasts."""

    scheduled = _text(entry.get('viewCountText'))
    streamed = _text(entry.get('publishedTimeText'))

    if is_live:
        return _i18n(30036)

    if scheduled and scheduled.lower().startswith(('scheduled', 'προγραμματισμ')):
        return scheduled

    if streamed:
        return streamed

    return ''


def _text(value):

    if isinstance(value, dict):
        simple = value.get('simpleText')
        if isinstance(simple, str):
            return simple
        runs = value.get('runs') or []
        if runs:
            return ''.join(run.get('text', '') for run in runs)

    return value if isinstance(value, str) else ''


# ---------------------------------------------------------------------------
# Play time state
# ---------------------------------------------------------------------------

def state(video_id):

    """
    YouTube's own verdict for a video id.

    Returns {'live': bool, 'finished': bool, 'label': str}. ``label`` is the
    scheduled/remaining wording for a stream that has not started yet.
    """

    body, _ = _fetch(YT_WATCH + video_id,
                     headers={'Accept-Language': 'el-GR,el;q=0.9,en;q=0.8'})

    html = body.decode('utf-8', errors='ignore')

    payload = _player_response(html)

    if not payload:
        # Nothing usable (private, removed or a layout change). Assume the
        # stream is playable and let the resolver produce the real error.
        return {'live': False, 'finished': False, 'label': ''}

    status = (payload.get('playabilityStatus') or {}).get('status', '')
    reason = (payload.get('playabilityStatus') or {}).get('reason', '') or ''
    details = payload.get('videoDetails') or {}

    finished = bool(details.get('lengthSeconds')) and details['lengthSeconds'] != '0'

    if status == 'LIVE_STREAM_OFFLINE' and not finished:
        return {'live': False, 'finished': False, 'label': reason}

    if status == 'OK' and not finished:
        return {'live': True, 'finished': False, 'label': ''}

    return {'live': False, 'finished': finished, 'label': ''}


def _player_response(html):

    match = re.search(
        r'var ytInitialPlayerResponse\s*=\s*(\{.*?\});(?:var|</script>)', html, re.DOTALL
    )

    if match:
        try:
            return json.loads(match.group(1))
        except ValueError:
            pass

    match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.*?\})\s*;\s*var\s', html, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(1))
        except ValueError:
            pass

    return None