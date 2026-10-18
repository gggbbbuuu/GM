# -*- coding: utf-8 -*-

'''
    Star Player Addon
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
    TV_SECTIONS, VIDEO_HUBS, LIVE_PAGE, PAGE_SIZE, bookmarks_file
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
        {'title': i18n(30070), 'action': 'listing', 'url': _ref(kind='sections'),
         'isFolder': 'True', 'image': kodi.addonmedia('tvshows.png')},
        {'title': i18n(30007), 'action': 'listing', 'url': _ref(kind='hubs'),
         'isFolder': 'True', 'image': kodi.addonmedia('videos.png')},
        {'title': '{0}: {1}'.format(i18n(30008), i18n(30004)),
         'action': 'listing',
         'url': _ref(kind='hub', category='starx', title=i18n(30008)),
         'isFolder': 'True', 'image': kodi.addonmedia('starx.png')},
        {'title': i18n(30010), 'action': 'listing',
         'url': _ref(kind='hub', category='eidiseis', title=i18n(30010)),
         'isFolder': 'True', 'image': kodi.addonmedia('news.png')},
        {'title': i18n(30071), 'action': 'programma',
         'isFolder': 'True', 'image': kodi.addonmedia('selector.png')},
        {'title': i18n(30087), 'action': 'search',
         'isFolder': 'True'},
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
# video sitemaps barely move, episode pages are immutable once published,
# schedule data goes stale within the day.
@cache_function(12, 3600)
def _shows_of(section):
    return api.tv_shows(section)


@cache_function(6, 3600)
def _episodes_of(base):
    return api.show_episodes(base)


@cache_function(12, 3600)
def _counts():
    return api.category_counts()


@cache_function(6, 3600)
def _prog_dates():
    return api.programma_dates()


@cache_function(30, 60)
def _prog_rows(date):
    return api.programma_rows(date)


@cache_function(2, 3600)
def _hub_page(category, page):
    return api.category_videos(category, page=page)


@cache_function(24, 3600)
def _detail(url):
    return api.episode_details(url)


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

        if kind == 'hubs':
            _hubs_listing()
            return

        if kind == 'categories':
            _categories_listing()
            return

        page = int(query) if query not in (None, '') else 1

        if kind == 'section':
            _section_listing(ref, page)
        elif kind == 'episodes':
            _episodes_listing(ref, page)
        elif kind == 'hub':
            _hub_listing(ref, page)
        elif kind == 'search':
            _search_listing(ref, page)
        else:
            directory.builder(_empty(i18n(30014)), content='videos')

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


def _hubs_listing():

    built = []

    for hub, label in VIDEO_HUBS:
        built.append({
            'title': i18n(label),
            'action': 'listing',
            'url': _ref(kind='hub', category=hub, title=i18n(label)),
            'isFolder': 'True',
            'image': kodi.addonmedia('videos.png'),
            'cm': _context_menu(),
        })

    built.append({
        'title': i18n(30079),
        'action': 'listing',
        'url': _ref(kind='categories'),
        'isFolder': 'True',
        'image': kodi.addonmedia('videos.png'),
        'cm': _context_menu(),
    })

    directory.builder(built, content='videos')


def _categories_listing():

    built = []
    counts = _counts()

    for category in sorted(counts):
        item = {
            'title': '{0} ({1})'.format(category.replace('-', ' ').title(), counts[category]),
            'action': 'listing',
            'url': _ref(kind='hub', category=category, title=category),
            'isFolder': 'True',
        }
        item['cm'] = _browseable(item)
        built.append(item)

    directory.builder(built or _empty(i18n(30014)), content='videos')


def _section_listing(ref, page):
    """Shows of one /tv/ section, with client-side paging."""

    entries = _shows_of(ref['section'])
    items, total_pages = _slice(entries, page)

    built = _page(ref, 'section', page, total_pages,
                  [_show_item(e) for e in items])
    _render(built, page, total_pages)


EPISODE_FILTERS = (
    ('all', 30084),
    ('full', 30085),
    ('clips', 30086),
)


def _episode_filter():
    try:
        choice = kodi.setting('episode_filter')
    except Exception:
        choice = 'all'

    return choice if choice in ('all', 'full', 'clips') else 'all'


def _episodes_listing(ref, page):
    """Playable episodes/clips of one show, newest page first."""

    all_entries = _episodes_of(ref['base'])
    choice = _episode_filter()

    if choice == 'full':
        entries = [e for e in all_entries if e.get('dated')]
    elif choice == 'clips':
        entries = [e for e in all_entries if not e.get('dated')]
    else:
        entries = all_entries

    chunk, total_pages = _slice(entries, page)

    videos = []
    for entry in chunk:
        detail = _detail(entry['url']) or {}
        if not detail.get('playable'):
            continue
        merged = dict(entry)
        merged.update({k: v for k, v in iteritems(detail) if v})
        videos.append(merged)

    built = _page(ref, 'episodes', page, total_pages,
                  [_video_item(v, ref, page=page, total_pages=total_pages) for v in videos])

    if any(e.get('dated') for e in all_entries) and \
            any(not e.get('dated') for e in all_entries):
        label = dict(EPISODE_FILTERS).get(choice, 30084)
        built.insert(0, {
            'title': '{0}: {1}'.format(i18n(30083), i18n(label)),
            'action': 'episode_filter',
            'icon': 'selector.png',
            'isFolder': 'False',
            'isPlayable': 'False',
        })

    _render(built, page, total_pages)


@urldispatcher.register('episode_filter')
def episode_filter():

    labels = [i18n(label) for _, label in EPISODE_FILTERS]
    choices = [key for key, _ in EPISODE_FILTERS]

    picked = kodi.selectDialog(labels, heading=i18n(30083))

    if picked == -1:
        return

    kodi.setSetting('episode_filter', choices[picked])
    kodi.sleep(200)
    kodi.refresh()


def _hub_listing(ref, page):
    """Newest-first videos of one /video/ hub category."""

    items, total_pages = _hub_page(ref['category'], page)

    built = _page(ref, 'hub', page, total_pages,
                  [_video_item(v, ref, page=page, total_pages=total_pages) for v in items])
    _render(built, page, total_pages)


def _slice(entries, page):
    """Client-side paging over a cached full list."""

    total_pages = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(1, page), total_pages)

    return entries[(page - 1) * PAGE_SIZE:page * PAGE_SIZE], total_pages


def _show_item(show):

    item = {
        'title': show['title'],
        'action': 'listing',
        'url': _ref(kind='episodes', base=show['url'], title=show['title']),
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
        return _empty(i18n(30014))

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
# Search (history kept in the search_history setting, most recent first)
# ---------------------------------------------------------------------------

HISTORY_LIMIT = 15


def _history():

    try:
        saved = json.loads(kodi.setting('search_history') or '[]')
    except Exception:
        return []

    return [entry for entry in saved if isinstance(entry, str) and entry][:HISTORY_LIMIT]


def _history_save(entries):

    kodi.setSetting('search_history', _json(entries[:HISTORY_LIMIT]))


@urldispatcher.register('search')
def search_menu():

    menu = [{
        'title': i18n(30088),
        'action': 'new_search',
        'isFolder': 'True',
        'cm': _context_menu(),
    }]

    for entry in _history():
        menu.append({
            'title': entry,
            'action': 'listing',
            'url': _ref(kind='search', query=entry, title=entry),
            'isFolder': 'True',
            'cm': [
                {'title': 30089, 'query': {'action': 'search_delete', 'url': entry}},
                {'title': 30090, 'query': {'action': 'search_clear'}},
            ],
        })

    directory.builder(menu, content='videos')


@urldispatcher.register('new_search')
def new_search():

    text = kodi.inputDialog(heading=i18n(30088))

    if not text or not text.strip():
        return

    text = text.strip()
    entries = [entry for entry in _history() if entry != text]
    entries.insert(0, text)
    _history_save(entries)

    target = '{0}?action=listing&url={1}'.format(
        sysaddon, quote_plus(_ref(kind='search', query=text, title=text)))
    kodi.execute('Container.Update("{0}")'.format(target))


@urldispatcher.register('search_delete', ['url'])
def search_delete(url):

    _history_save([entry for entry in _history() if entry != url])
    kodi.refresh()


@urldispatcher.register('search_clear')
def search_clear():

    _history_save([])
    kodi.infoDialog(i18n(30402))
    kodi.refresh()


@cache_function(1, 3600)
def _search_of(query):
    return api.search(query)


def _search_listing(ref, page):
    """Show folders first, then paged playable episodes for a search."""

    shows, episodes = _search_of(ref.get('query', ''))

    chunk, total_pages = _slice(episodes, page)

    videos = []
    for entry in chunk:
        detail = _detail(entry['url']) or {}
        if not detail.get('playable'):
            continue
        merged = dict(entry)
        merged.update({k: v for k, v in iteritems(detail) if v})
        videos.append(merged)

    built = [_show_item(show) for show in shows] if page == 1 else []
    built.extend(_video_item(v, ref, page=page, total_pages=total_pages) for v in videos)

    if not built:
        _render(_empty(i18n(30014)))
        return

    if total_pages > 1:
        built = _page(ref, 'search', page, total_pages, built)

    _render(built, page, total_pages)


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
        directory.builder(_empty(i18n(30014)), content='videos')
        return

    dialog = ProgrammaDialog('script-star-programma.xml', kodi.addonInfo('path'),
                             dates=dates)
    dialog.doModal()
    del dialog


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------

@urldispatcher.register('play', ['url'])
def play(url):

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
        directory.builder(_empty(i18n(30006)), content='videos')
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
