# -*- coding: utf-8 -*-

'''
    Skai Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json
import os
import threading
from urllib.parse import quote_plus

import xbmc
import xbmcgui

from . import api, player
from .constants import (
    TV_SECTIONS, LIVE_PAGE, RADIO_LIVE_URL, PAGE_SIZE, bookmarks_file
)
from tulip import kodi, directory, bookmarks
from tulip.init import sysaddon
from tulip.utils import iteritems
from urldispatcher import urldispatcher

try:
    from pickled import FunctionCache

    cache = FunctionCache(kodi.cacheDirectory)
    cache_function = cache.cache_function
except Exception:
    def cache_function(limit, limit_mode=60):
        def wrap(func):
            return func
        return wrap


def i18n(number):
    try:
        return kodi.i18n(number)
    except Exception:
        return str(number)


def _json(value):
    return json.dumps(value, separators=(',', ':'))


def _ref(**kwargs):
    """A listing is fully described by this dict, passed around as its url."""

    return _json(kwargs)


def _browseable(item, **overrides):
    bookmark = dict((k, v) for k, v in iteritems(item) if k not in ('next', 'cm'))
    bookmark.update(overrides)
    bookmark['bookmark'] = bookmark.get('url')
    return [{'title': 30501, 'query': {'action': 'addBookmark', 'url': _json(bookmark)}}]


def _empty(label):
    return [{'title': label, 'action': None, 'isFolder': 'False', 'isPlayable': 'False'}]


def _context_menu():

    return [
        {'title': 30022, 'query': {'action': 'clear_cache'}},
        {'title': 30026, 'query': {'action': 'settings'}},
    ]


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@urldispatcher.register('root')
def root():

    menu = [
        {'title': i18n(30001), 'action': 'live', 'isPlayable': 'True',
         'image': kodi.addonmedia('live.png')},
        {'title': i18n(30008), 'action': 'play', 'url': RADIO_LIVE_URL,
         'isFolder': 'False', 'isPlayable': 'True',
         'image': kodi.addonmedia('live.png')},
        {'title': i18n(30002), 'action': 'listing', 'url': _ref(kind='sections'),
         'isFolder': 'True', 'image': kodi.addonmedia('tvshows.png')},
        {'title': i18n(30009), 'action': 'listing',
         'url': _ref(kind='cinema', title=i18n(30009)),
         'isFolder': 'True', 'image': kodi.addonmedia('entertainment.png')},
        {'title': i18n(30004), 'action': 'listing',
         'url': _ref(kind='trending', title=i18n(30004)),
         'isFolder': 'True', 'image': kodi.addonmedia('latest.png')},
        {'title': i18n(30007), 'action': 'programma',
         'isFolder': 'True', 'image': kodi.addonmedia('selector.png')},
        {'title': i18n(30003), 'action': 'listing',
         'url': _ref(kind='podcasts'),
         'isFolder': 'True', 'image': kodi.addonmedia('podcasts.png')},
        {'title': i18n(30006), 'action': 'bookmarks', 'isFolder': 'True',
         'image': kodi.addonmedia('bookmarks.png')},
    ]

    for item in menu:
        item['cm'] = _context_menu()

    directory.builder(menu, content='videos')


# ---------------------------------------------------------------------------
# Listings
#
# One route serves every folder. ``url`` is the ref dict and ``query`` the
# page number; every listing here counts pages from 1.
# ---------------------------------------------------------------------------

# Durations below are (amount, unit-in-seconds): the show line-up and the
# cinema catalogue barely move, trending turns over through the day, the
# radio archive and episode pages are immutable once published, schedule
# data goes stale within the day.
@cache_function(12, 3600)
def _shows_of(section):
    return api.tv_shows(section)


@cache_function(6, 3600)
def _episodes_of(base):
    return api.show_episodes(base)


@cache_function(1, 3600)
def _trending():
    return api.trending()


@cache_function(12, 3600)
def _cinema():
    return api.cinema_detailed()


@cache_function(6, 3600)
def _prog_dates():
    return api.programma_dates()


@cache_function(30, 60)
def _prog_rows(date):
    return api.programma_rows(date)


@cache_function(6, 3600)
def _pod_shows(page):
    return api.pod_shows(page)


@cache_function(6, 3600)
def _pod_episodes(url):
    return api.pod_episodes(url)


@cache_function(6, 3600)
def _mystyle(tab):
    return api.mystyle_rocks(tab=tab)


@cache_function(12, 3600)
def _mystyle_playlists():
    return api.mystyle_playlists()


@cache_function(6, 3600)
def _mystyle_playlist(playlist):
    return api.mystyle_playlist_videos(playlist)


@urldispatcher.register('listing', ['url'], ['query'])
def listing(url, query=None):

    try:
        ref = json.loads(url)
    except Exception:
        directory.builder(_empty(i18n(30033)), content='videos')
        return

    kind = ref.get('kind', '')

    try:
        if kind == 'sections':
            _sections_listing()
            return

        if kind == 'podcasts':
            page = int(query) if query not in (None, '') else 0
            _podcasts_listing(ref, page)
            return

        if kind == 'pod_episodes':
            _pod_episodes_listing(ref)
            return

        if kind == 'trending':
            _simple_listing(_trending(), ref, 1, 1)
            return

        if kind == 'mystyle':
            _mystyle_hub(ref)
            return

        if kind == 'mystyle_playlists':
            _mystyle_playlists_listing(ref)
            return

        if kind == 'cinema':
            _cinema_listing(ref)
            return

        page = int(query) if query not in (None, '') else 1

        if kind == 'section':
            _section_listing(ref, page)
        elif kind == 'mystyle_tab':
            _mystyle_tab_listing(ref, page)
        elif kind == 'mystyle_playlist':
            _mystyle_playlist_listing(ref, page)
        elif kind == 'seasons':
            _seasons_listing(ref)
        elif kind == 'episodes':
            _episodes_listing(ref, page)
        else:
            directory.builder(_empty(i18n(30020)), content='videos')

    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30033), error))
        directory.builder(_empty(i18n(30033)), content='videos')


def _sections_listing():

    built = []

    for section, label in TV_SECTIONS:
        built.append({
            'title': i18n(label),
            'action': 'listing',
            'url': _ref(kind='section', section=section, title=i18n(label)),
            'isFolder': 'True',
            'image': kodi.addonmedia('tvshows.png'),
            'cm': _context_menu(),
        })

    directory.builder(built, content='videos')


def _section_listing(ref, page):
    """Shows of one /tv/shows/ section, with client-side paging."""

    entries = _shows_of(ref['section'])
    items, total_pages = _slice(entries, page)

    built = _page(ref, 'section', page, total_pages,
                  [_show_item(e) for e in items])
    _render(built, page, total_pages)


def _seasons_listing(ref):
    """One folder per season for shows spanning several season pages."""

    built = []
    for season in ref.get('seasons', []):
        built.append({
            'title': i18n(30016).format(season['label']),
            'action': 'listing',
            'url': _ref(kind='episodes', base=season['url'], title=ref.get('title', '')),
            'isFolder': 'True',
            'cm': _context_menu(),
        })

    directory.builder(built or _empty(i18n(30020)), content='videos')


def _episodes_listing(ref, page):
    """Playable episodes of one show, in page order."""

    entries = _episodes_of(ref['base'])
    chunk, total_pages = _slice(entries, page)

    built = _page(ref, 'episodes', page, total_pages,
                  [_video_item(v, ref, page=page, total_pages=total_pages) for v in chunk])
    _render(built, page, total_pages)


def _mystyle_hub(ref):
    """Unfolds the channel: videos, shorts and season playlists."""

    built = [
        {
            'title': i18n(30010),
            'action': 'listing',
            'url': _ref(kind='mystyle_tab', tab='videos', title=ref.get('title', '')),
            'isFolder': 'True',
            'image': kodi.addonmedia('latest.png'),
            'cm': _context_menu(),
        },
        {
            'title': i18n(30017),
            'action': 'listing',
            'url': _ref(kind='mystyle_tab', tab='shorts', title=ref.get('title', '')),
            'isFolder': 'True',
            'image': kodi.addonmedia('latest.png'),
            'cm': _context_menu(),
        },
        {
            'title': i18n(30019),
            'action': 'listing',
            'url': _ref(kind='mystyle_playlists', title=ref.get('title', '')),
            'isFolder': 'True',
            'image': kodi.addonmedia('tvshows.png'),
            'cm': _context_menu(),
        },
    ]

    directory.builder(built, content='videos')


def _mystyle_tab_listing(ref, page):
    """Newest-first channel videos or shorts, with client-side paging."""

    entries = _mystyle(ref.get('tab', 'videos'))
    chunk, total_pages = _slice(entries, page)

    if ref.get('tab') == 'shorts':
        chunk = api.yt_titles(chunk)

    videos = []
    for entry in chunk:
        title = entry['title'] or entry['url']
        if entry.get('duration'):
            minutes, seconds = divmod(entry['duration'], 60)
            title = '{0} [{1}:{2:02d}]'.format(title, minutes, seconds)
        video = dict(entry, title=title)
        videos.append(_video_item(video, ref, page=page, total_pages=total_pages))

    built = _page(ref, 'mystyle_tab', page, total_pages, videos)
    _render(built, page, total_pages)


def _mystyle_playlists_listing(ref):
    """One folder per season playlist of the channel."""

    built = []
    for entry in _mystyle_playlists():
        item = {
            'title': entry['title'],
            'action': 'listing',
            'url': _ref(kind='mystyle_playlist', playlist=entry['url'],
                         title=entry['title']),
            'isFolder': 'True',
        }
        if entry.get('image'):
            item['image'] = entry['image']
            item['fanart'] = entry['image']
        item['cm'] = _browseable(item)
        built.append(item)

    directory.builder(built or _empty(i18n(30020)), content='videos')


def _mystyle_playlist_listing(ref, page):
    """Playable videos of one season playlist, in playlist order."""

    entries = _mystyle_playlist(ref['playlist'])
    chunk, total_pages = _slice(entries, page)

    built = _page(ref, 'mystyle_playlist', page, total_pages,
                  [_video_item(v, ref, page=page, total_pages=total_pages) for v in chunk])
    _render(built, page, total_pages)


def _cinema_listing(ref):
    """
    Cinema entries open a YouTube trailer search (alpha-style) instead
    of playing the site's brief clip directly.
    """

    built = []
    for video in _cinema():
        item = {
            'title': video['title'],
            'action': 'play_trailer',
            'url': _json({'title': video['title'], 'fallback': video['url']}),
            'isFolder': 'False',
            'isPlayable': 'True',
        }
        if video.get('plot'):
            item['plot'] = video['plot']
            item['plotoutline'] = video['plot']
        if video.get('image'):
            item['image'] = video['image']
            item['fanart'] = video['image']
        item['cm'] = _browseable(item)
        built.append(item)

    _render(built or _empty(i18n(30020)), 1, 1)


def _simple_listing(entries, ref, page, total_pages):
    """A full listing that needs no paging (trending)."""

    built = [_video_item(v, ref, page=page, total_pages=total_pages) for v in entries]
    _render(built or _empty(i18n(30020)), page, total_pages)


def _podcasts_listing(ref, page):
    """Radio show archive index, Drupal-paginated from 0."""

    items, has_next = _pod_shows(page)

    built = []
    for entry in items:
        item = {
            'title': entry['title'],
            'action': 'listing',
            'url': _ref(kind='pod_episodes', base=entry['url'], title=entry['title']),
            'isFolder': 'True',
        }
        if entry.get('image'):
            item['image'] = entry['image']
            item['fanart'] = entry['image']
        item['cm'] = _browseable(item)
        built.append(item)

    if page > 0:
        built.insert(0, {
            'title': i18n(30030),
            'action': 'listing',
            'url': _ref(kind='podcasts'),
            'query': str(page - 1),
            'isFolder': 'True',
            'image': kodi.addonmedia('previous.png'),
        })

    if has_next:
        built.append({
            'title': i18n(30031),
            'action': 'listing',
            'url': _ref(kind='podcasts'),
            'query': str(page + 1),
            'isFolder': 'True',
            'image': kodi.addonmedia('next.png'),
        })

    directory.builder(built or _empty(i18n(30020)), content='videos')


def _pod_episodes_listing(ref):
    """Episodes of one radio show, newest first, directly playable."""

    entries = _pod_episodes(ref['base'])

    built = []
    for entry in entries:
        item = {
            'title': entry['title'],
            'action': 'play',
            'url': entry['url'],
            'isFolder': 'False',
            'isPlayable': 'True',
        }
        item['cm'] = _browseable(item)
        built.append(item)

    directory.builder(built or _empty(i18n(30020)), content='songs')


def _slice(entries, page):
    """Client-side paging over a cached full list."""

    total_pages = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(1, page), total_pages)

    return entries[(page - 1) * PAGE_SIZE:page * PAGE_SIZE], total_pages


def _show_item(show):

    if show.get('yt_channel'):
        action_url = _ref(kind='mystyle', title=show['title'])
    elif len(show.get('seasons') or []) > 1:
        action_url = _ref(kind='seasons', base=show['url'], title=show['title'],
                          seasons=show['seasons'])
    else:
        action_url = _ref(kind='episodes', base=show['url'], title=show['title'])

    item = {
        'title': show['title'],
        'action': 'listing',
        'url': action_url,
        'isFolder': 'True',
    }

    if show.get('image'):
        item['image'] = show['image']
        item['fanart'] = show['image']

    item['cm'] = _browseable(item)

    return item


def _page_items(kind, ref, page, total_pages):
    """The "Previous page" / "Next page" entries, shared by every listing."""

    ref_url = _ref(**dict(ref, kind=kind))
    previous, following = None, None

    if page > 1:
        previous = {
            'title': i18n(30030),
            'action': 'listing',
            'url': ref_url,
            'query': str(page - 1),
            'isFolder': 'True',
            'image': kodi.addonmedia('previous.png'),
        }

    if page < total_pages:
        following = {
            'title': i18n(30031),
            'action': 'listing',
            'url': ref_url,
            'query': str(page + 1),
            'isFolder': 'True',
            'image': kodi.addonmedia('next.png'),
        }

    return previous, following


def _page(ref, kind, page, total_pages, entries):
    """
    Wraps ``entries`` in a page: an optional "Previous page" entry, the
    entries themselves, and an optional "Next page" entry.
    """

    previous, following = _page_items(kind, ref, page, total_pages)

    if not entries:
        return _empty(i18n(30020))

    built = [previous] if previous else []

    built.extend(entries)

    if following:
        built.append(following)

    return built


def _video_item(video, ref=None, page=1, total_pages=1):
    ref = ref or {}
    raw_title = video['title']
    show_title = ref.get('title')

    if show_title and not raw_title.startswith(show_title):
        display_title = '{0} - {1}'.format(show_title, raw_title)
    else:
        display_title = raw_title

    item = {
        'title': display_title,
        'action': 'play',
        'url': video['url'],
        'isFolder': 'False',
        'isPlayable': 'True',
    }

    if video.get('plot'):
        item['plot'] = video['plot']
        item['plotoutline'] = video['plot']

    if show_title:
        item['tvshowtitle'] = show_title
        item['mediatype'] = 'episode'

    if video.get('image'):
        item['image'] = video['image']
        item['fanart'] = video['image']

    cm = _browseable(item)

    if total_pages > 1:
        cm.append({
            'title': 30056,
            'query': {
                'action': 'change_page',
                'url': _json(ref),
                'current': str(page),
                'total': str(total_pages)
            },
        })

    item['cm'] = cm

    return item


def _render(built, page=1, total_pages=1):

    if total_pages > 1:
        _show_page_overlay(i18n(30055).format(page, total_pages))

    directory.builder(built, content='videos', cacheToDisc=False)


def _display_overlay_worker(text, duration=10.0):
    """
    Displays the page indicator overlay non-modally by adding controls
    directly to the active media window (or window 10000).
    This guarantees 0% blocking of list navigation.
    """
    try:
        addon_path = kodi.addonInfo('path')
        texture_path = os.path.join(addon_path, 'resources', 'skins', 'Default', 'media', 'bg_card.png')

        try:
            pos_setting = int(kodi.setting('overlay_position'))
        except Exception:
            pos_setting = 0

        try:
            pad_x = int(float(kodi.setting('overlay_padding_x')))
        except Exception:
            pad_x = 40

        try:
            pad_y = int(float(kodi.setting('overlay_padding_y')))
        except Exception:
            pad_y = 30

        win_id = xbmcgui.getCurrentWindowId()
        if not win_id or win_id == -1:
            win_id = 10025  # MyVideoNav
        win = xbmcgui.Window(win_id)

        try:
            win_w = win.getWidth()
            win_h = win.getHeight()
        except Exception:
            win_w = 0
            win_h = 0

        if not win_w or win_w <= 0:
            win_w = 1920
        if not win_h or win_h <= 0:
            win_h = 1080

        # Scale badge dimensions proportionally with reference 1080p (width ~300, height ~56)
        scale_x = win_w / 1920.0
        scale_y = win_h / 1080.0
        badge_w = int(max(200, 300 * scale_x))
        badge_h = int(max(40, 56 * scale_y))

        if pos_setting == 1:  # top-left
            x = pad_x
            y = pad_y
        elif pos_setting == 2:  # bottom-right
            x = win_w - badge_w - pad_x
            y = win_h - badge_h - pad_y
        elif pos_setting == 3:  # bottom-left
            x = pad_x
            y = win_h - badge_h - pad_y
        else:  # 0: top-right (default)
            x = win_w - badge_w - pad_x
            y = pad_y

        # Non-focusable controls attached directly to the window
        # Alignment 6 = ALIGN_CENTER_X (2) | ALIGN_CENTER_Y (4)
        img_control = xbmcgui.ControlImage(int(x), int(y), badge_w, badge_h, texture_path)
        lbl_control = xbmcgui.ControlLabel(
            int(x + 10), int(y), badge_w - 20, badge_h,
            text, font='font13', textColor='0xFFFFFFFF', alignment=6
        )

        win.addControl(img_control)
        win.addControl(lbl_control)

        # Sleep for the duration, checking abortRequested periodically
        sleep_steps = int(duration * 10)
        for _ in range(sleep_steps):
            if xbmc.Monitor().abortRequested():
                break
            xbmc.sleep(100)

        try:
            win.removeControl(lbl_control)
        except Exception:
            pass
        try:
            win.removeControl(img_control)
        except Exception:
            pass
        del lbl_control
        del img_control
    except Exception:
        pass


def _show_page_overlay(text):
    t = threading.Thread(target=_display_overlay_worker, args=(text,))
    t.daemon = True
    t.start()


@urldispatcher.register('change_page', ['url', 'current', 'total'])
def change_page(url, current, total):
    """Allows jumping directly to a page."""
    try:
        total_p = int(total)
        current_p = int(current)
    except Exception:
        total_p = 1
        current_p = 1

    prompt = i18n(30056)
    if total_p > 1:
        prompt = '{0} (1-{1})'.format(prompt, total_p)

    val = kodi.inputDialog(heading=prompt, default=str(current_p), type=xbmcgui.INPUT_NUMERIC)
    if not val:
        return

    try:
        target_page = int(val)
    except ValueError:
        return

    if target_page < 1:
        target_page = 1
    elif target_page > total_p:
        target_page = total_p

    target_url = '{0}?action=listing&url={1}&query={2}'.format(
        sysaddon, quote_plus(url), target_page)
    kodi.execute('Container.Update("{0}")'.format(target_url))


# ---------------------------------------------------------------------------
# Programme
# ---------------------------------------------------------------------------

@urldispatcher.register('programma')
def programma():

    from .windowxml import ProgrammaDialog

    try:
        dates = _prog_dates()
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30033), error))
        return

    if not dates:
        directory.builder(_empty(i18n(30020)), content='videos')
        return

    dialog = ProgrammaDialog('script-skai-programma.xml', kodi.addonInfo('path'),
                             dates=dates)
    dialog.doModal()
    del dialog


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------

@urldispatcher.register('play_trailer', ['url'])
def play_trailer(url):
    """
    Searches YouTube for the film's trailer using scrapetube, displays
    up to 3 results in a select dialog, and plays the chosen trailer.
    Falls back to the site's own clip when nothing is found.
    """
    try:
        data = json.loads(url)
        title = data.get('title', '')
        fallback = data.get('fallback', '')
    except Exception:
        title = url
        fallback = ''

    def _fallback():
        if fallback:
            _resolve(fallback)
        else:
            kodi.infoDialog(i18n(30068))

    if not title:
        _fallback()
        return

    try:
        from scrapetube import wrapper
        results = wrapper.list_search(
            '{0} trailer'.format(title), limit=3, sleep=0,
            add_url=wrapper.YT_PREFIX
        )
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30034), error))
        return

    if not results:
        _fallback()
        return

    labels = []
    for result in results:
        label = result.get('title') or title
        duration = result.get('duration') or 0
        if duration > 0:
            minutes, seconds = divmod(duration, 60)
            label = '{0} [{1}:{2:02d}]'.format(label, minutes, seconds)
        labels.append(label)

    chosen = kodi.selectDialog(labels, heading='{0} - {1}'.format(title, i18n(30067)))

    if chosen == -1:
        return

    _resolve(results[chosen]['url'])


@urldispatcher.register('play', ['url'])
def play(url):

    if url == RADIO_LIVE_URL:
        _play(url)
        return

    if 'skairadio.gr' in url:
        try:
            stream = api.pod_file(url)
        except Exception as error:
            kodi.infoDialog('{0}: {1}'.format(i18n(30034), error))
            return

        if not stream:
            kodi.infoDialog(i18n(30034))
            return

        _play(stream)
        return

    _resolve(url)


@urldispatcher.register('live')
def live():
    """Live is a single playable entry delegated to PluginsGR/ResolveURL."""

    _resolve(LIVE_PAGE)


def _resolve(url):

    try:
        stream, subtitles = player.resolve(url)
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30034), error))
        return

    if subtitles:
        # Kodi reads external subtitles appended to the stream url, and its
        # <path>|<url>|<lang>|<name> syntax expects exactly three parts.
        stream = '{}|{}|{}'.format(
            stream, subtitles[0]['url'], subtitles[0].get('lang') or 'Greek'
        )

    _play(stream)


def _play(stream):

    path = stream.split('|')[0]
    hls = '.m3u8' in path
    dash = '.mpd' in path

    directory.resolve(
        stream,
        dash=hls or dash,
        manifest_type='hls' if hls else ('mpd' if dash else None),
        mimetype='application/vnd.apple.mpegurl' if hls else ('application/xml+dash' if dash else None),
    )


# ---------------------------------------------------------------------------
# Bookmarks / misc
# ---------------------------------------------------------------------------

@urldispatcher.register('bookmarks')
def bookmarks_list():

    items = bookmarks.get(path=bookmarks_file()) or []

    if not items:
        directory.builder(_empty(i18n(30018)), content='videos')
        return

    for item in items:
        # Bookmarks were stored from a listing, so restore the playability
        # flags Kodi reads when the container is rebuilt.
        action = item.get('action') or 'play'
        item.update({'action': action, 'isFolder': 'False', 'isPlayable': 'True'})
        del_item = dict((k, v) for k, v in iteritems(item) if k not in ('next', 'cm'))
        del_item['delbookmark'] = del_item.get('url')
        item['cm'] = [{
            'title': 30502,
            'query': {'action': 'deleteBookmark', 'url': _json(del_item)},
        }]

    kodi.setsortmethod('title')

    directory.builder(items, content='videos')


@urldispatcher.register('go_to_root')
def go_to_root():
    directory.run_builtin(action='root', path_history='replace')
