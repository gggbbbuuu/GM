# -*- coding: utf-8 -*-

'''
    ANT1 Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json

from . import api, player
from .constants import (
    REGION_GR, REGION_CY, REGIONS, LIVE_CHANNELS, SHOW_CATEGORIES, NEWS_SECTIONS,
    LIFESTYLE_SECTIONS, SPORTS_SECTIONS, CY_SECTIONS, CY_LIVE_PAGE,
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
    # Bookmarks must replay through the resolver, so store the page url.
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

def _selector_mode():
    try:
        mode = kodi.setting('selector_mode')
    except Exception:
        mode = ''

    # '0' (dedicated line) is the default; only an explicit '1' hides it.
    return '1' if mode == '1' else '0'


@urldispatcher.register('root')
def root():

    if _region() == REGION_CY:
        menu = [
            {'title': i18n(30001), 'action': 'cy_live', 'isPlayable': 'True',
             'image': kodi.addonmedia('live.jpg')},
        ]

        for section, label in CY_SECTIONS:
            menu.append({
                'title': i18n(label),
                'action': 'listing',
                'url': _ref(kind='cy_section', section=section),
                'isFolder': 'True',
                'image': kodi.addonmedia('news.png'
                                         if section == 'enimerosi' else
                                         'entertainment.png'
                                         if section == 'psyhagogia' else
                                         'podcasts.png'
                                         if section == 'podcasts' else
                                         'series.png'
                                         if section == 'series' else
                                         'movies.png'),
            })
    else:
        menu = [
            {'title': i18n(30001), 'action': 'live', 'isFolder': 'True',
             'image': kodi.addonmedia('live.jpg')},
            {'title': i18n(30002), 'action': 'listing', 'url': _ref(kind='shows'),
             'isFolder': 'True', 'image': kodi.addonmedia('shows.png')},
            {'title': i18n(30011), 'action': 'news', 'isFolder': 'True',
             'image': kodi.addonmedia('news.png')},
            {'title': i18n(30070), 'action': 'lifestyle', 'isFolder': 'True',
             'image': kodi.addonmedia('lifestyle.png')},
            {'title': i18n(30012), 'action': 'listing', 'url': _ref(kind='webtv'),
             'isFolder': 'True', 'image': kodi.addonmedia('webtv.png')},
            {'title': i18n(30071), 'action': 'sports', 'isFolder': 'True',
             'image': kodi.addonmedia('sports.png')},
            {'title': i18n(30072), 'action': 'listing', 'url': _ref(kind='radio'),
             'isFolder': 'True', 'image': kodi.addonmedia('radio.jpg')},
        ]

    menu.append({'title': i18n(30009), 'action': 'bookmarks', 'isFolder': 'True',
                 'image': kodi.addonmedia('bookmarks.jpg')})

    if _selector_mode() == '0':
        # Dedicated selector line, AliveGR-style: an action, not a folder.
        menu.append({
            'title': i18n(30003).format(i18n(dict(REGIONS)[_region()])),
            'action': 'selector',
            'isFolder': 'False',
            'isPlayable': 'False',
            'image': kodi.addonmedia('selector.png'),
        })
    else:
        for item in menu:
            item['cm'] = item.get('cm', _context_menu()) + [{
                'title': 30005,
                'query': {'action': 'selector'},
            }]

    for item in menu:
        item.setdefault('cm', _context_menu())

    directory.builder(menu, content='videos')


def _region():
    try:
        region = kodi.setting('region')
    except Exception:
        region = ''

    return region if region in (REGION_GR, REGION_CY) else REGION_GR


@urldispatcher.register('selector')
def selector():

    chosen = kodi.selectDialog([i18n(label) for _, label in REGIONS])

    if chosen == -1:
        return

    if REGIONS[chosen][0] == _region():
        return

    kodi.setSetting('region', REGIONS[chosen][0])

    # Container.Refresh alone reuses the cached listing, so jump back to a
    # rebuilt root instead; it also covers the settings-dialog entry point.
    kodi.execute('Container.Update({0}?action=root,replace)'.format(sysaddon))


@urldispatcher.register('switch')
def switch():
    """Legacy alias, so bookmarks made by older versions keep working."""

    selector()


@urldispatcher.register('news')
def news():

    menu = []

    for cid, slug, label in NEWS_SECTIONS:
        menu.append({
            'title': i18n(label),
            'action': 'listing',
            'url': _ref(kind='news', cid=cid, slug=slug),
            'isFolder': 'True',
            'image': kodi.addonmedia('news.png'),
        })

    _related_menu(menu, 'news', NEWS_SECTIONS)

    for item in menu:
        item['cm'] = _context_menu()

    directory.builder(menu, content='videos')


@urldispatcher.register('lifestyle')
def lifestyle():

    menu = []

    for cid, slug, label in LIFESTYLE_SECTIONS:
        menu.append({
            'title': i18n(label),
            'action': 'listing',
            'url': _ref(kind='lifestyle', cid=cid, slug=slug),
            'isFolder': 'True',
            'image': kodi.addonmedia('lifestyle.png'),
        })

    for item in menu:
        item['cm'] = _context_menu()

    directory.builder(menu, content='videos')


@urldispatcher.register('sports')
def sports():

    menu = []

    for slug, label in SPORTS_SECTIONS:
        menu.append({
            'title': i18n(label),
            'action': 'listing',
            'url': _ref(kind='sports', slug=slug),
            'isFolder': 'True',
            'image': kodi.addonmedia('sports.png'),
        })

    menu.append({
        'title': '{0} - {1}'.format(i18n(30067), i18n(30073)),
        'action': 'listing',
        'url': _ref(kind='related', section='https://www.antenna.gr/football'),
        'isFolder': 'True',
        'image': kodi.addonmedia('sports.png'),
    })

    for item in menu:
        item['cm'] = _context_menu()

    directory.builder(menu, content='videos')


def _related_menu(menu, kind, sections):
    """Adds the 'related videos' rail entry to section folders."""

    from .constants import NEWS_SECTION_PAGE, LIFESTYLE_SECTION_PAGE

    base = NEWS_SECTION_PAGE if kind == 'news' else LIFESTYLE_SECTION_PAGE

    for cid, slug, label in sections:
        menu.append({
            'title': '{0} - {1}'.format(i18n(label), i18n(30073)),
            'action': 'listing',
            'url': _ref(kind='related', section=base.format(slug=slug)),
            'isFolder': 'True',
            'image': kodi.addonmedia('news.png' if kind == 'news' else 'lifestyle.png'),
        })


# ---------------------------------------------------------------------------
# Live
# ---------------------------------------------------------------------------

@cache_function(4, 60)
def _live_info():

    info = {}

    for channel, _label in LIVE_CHANNELS:
        try:
            info[channel] = api.live(channel)
        except Exception:
            info[channel] = {}

    return info


@urldispatcher.register('live')
def live_listing():

    try:
        info = _live_info()
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30033), error))
        directory.builder(_empty(i18n(30033)), content='videos')
        return

    listing = []

    for channel, label in LIVE_CHANNELS:
        entry = info.get(channel) or {}

        title = entry.get('title', '').strip() or i18n(label)

        item = {
            'title': '{0}[CR]{1}'.format(i18n(label), title),
            'action': 'play_live',
            'url': channel,
            'isFolder': 'False',
            'isPlayable': 'True',
        }
        item['cm'] = _context_menu()
        listing.append(item)

    directory.builder(listing or _empty(i18n(30014)), content='videos')


@urldispatcher.register('cy_live')
def cy_live():
    """
    Cyprus live is a single playable channel. Its signed cloudskep playlist
    is read fresh on every playback, like the Alpha CY equivalent.
    """

    try:
        stream = api.cy_live_url()
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30034), error))
        return

    if not stream:
        kodi.infoDialog(i18n(30034))
        return

    _play(stream)


@urldispatcher.register('play_live', ['url'])
def play_live(url):

    try:
        entry = api.live(url)
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30034), error))
        return

    stream = (entry or {}).get('url')

    if not stream:
        kodi.infoDialog(i18n(30034))
        return

    _play(stream)


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------

@cache_function(12, 60)
def _shows(url=None):
    return api.shows(url)


@cache_function(12, 60)
def _stations():
    return api.stations()


@urldispatcher.register('listing', ['url'], ['query'])
def listing(url, query=None):

    try:
        ref = json.loads(url)
    except Exception:
        directory.builder(_empty(i18n(30033)), content='videos')
        return

    kind = ref.get('kind', '')

    try:
        if kind == 'shows':
            directory.builder(_show_folders(None), content='videos')
            return

        if kind == 'show_category':
            directory.builder(_show_folders(ref['url']), content='videos')
            return

        if kind == 'episodes':
            directory.builder(_episodes(ref), content='videos', cacheToDisc=False)
            return

        if kind in ('news', 'lifestyle'):
            page = int(query) if query not in (None, '') else 1
            directory.builder(_category(ref, page), content='videos', cacheToDisc=False)
            return

        if kind == 'related':
            directory.builder(_related(ref), content='videos', cacheToDisc=False)
            return

        if kind == 'sports':
            directory.builder(_sports(ref['slug']), content='videos', cacheToDisc=False)
            return

        if kind == 'webtv':
            directory.builder(_clips(api.webtv()), content='videos')
            return

        if kind == 'cy_section':
            directory.builder(_cy_section(ref['section']), content='videos', cacheToDisc=False)
            return

        if kind == 'cy_subindex':
            directory.builder(_cy_subindex(ref['section'], ref['slug']), content='videos', cacheToDisc=False)
            return

        if kind == 'radio':
            directory.builder(_radio(), content='songs')
            return

        directory.builder(_empty(i18n(30014)), content='videos')

    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30033), error))
        directory.builder(_empty(i18n(30033)), content='videos')


def _show_folders(url):
    """Shows index, or one server-side category of it, as folders."""

    from .constants import SHOW_CATEGORY

    built = []

    if url is None:
        cat_icons = {
            'ellinikes-seires': 'series.png',
            'enimerosi': 'news.png',
            'psyxagogia': 'entertainment.png',
            'eidiseis': 'news.png',
            'athlitikes-ekpompes': 'sports.png',
        }
        for cid, slug, label in SHOW_CATEGORIES:
            built.append({
                'title': i18n(label),
                'action': 'listing',
                'url': _ref(kind='show_category',
                            url=SHOW_CATEGORY.format(category_id=cid, category_slug=slug)),
                'isFolder': 'True',
                'image': kodi.addonmedia(cat_icons.get(slug, 'shows.png')),
            })

    for entry in _shows(url):
        item = {
            'title': entry['title'],
            'action': 'listing',
            'url': _ref(kind='episodes', base=entry['url'], title=entry['title']),
            'isFolder': 'True',
        }

        if entry.get('image'):
            item['image'] = entry['image']
            item['fanart'] = entry['image']

        if entry.get('category'):
            item['studio'] = entry['category']

        item['cm'] = _browseable(item)
        built.append(item)

    return built or _empty(i18n(30014))


def _episodes(ref):
    """A show's full archive (first page + the one-shot 'load more' dump)."""

    from urllib.parse import urlparse

    slug = urlparse(ref['base']).path.strip('/')

    return _clips(api.show_videos(slug), title=ref.get('title'))


def _category(ref, page):
    """One page of a news/lifestyle category archive."""

    from .constants import NEWS_PAGE, LIFESTYLE_PAGE

    link = (NEWS_PAGE if ref['kind'] == 'news' else LIFESTYLE_PAGE).format(
        cid=ref['cid'], page=page)

    items, total_pages = api.category(link, page)

    return _paged(ref, page, total_pages, items)


def _related(ref):
    """The 'related videos' rail of a section page (no paging)."""

    return _clips(api.related_videos(ref['section']))


def _sports(slug):
    """Sports highlight clips of a hub page; resolves titles via the player."""

    return _clips(api.sports(slug))


def _cy_section(section):
    """One CY section index: sub-index folders plus direct episodes."""

    built = []

    for entry in api.cy_section(section):
        depth = entry['url'].rstrip('/').count('/')

        if depth > 4:
            # Episode/news/movie page: play through ResolveURL.
            item = {
                'title': entry['title'],
                'action': 'play',
                'url': entry['url'],
                'isFolder': 'False',
                'isPlayable': 'True',
            }
            item['cm'] = _browseable(item)
        else:
            # Show/movie/podcast sub-index (or a further section level).
            parts = entry['url'].rstrip('/').split('/webtv/', 1)[-1].split('/')
            if len(parts) > 2:
                sub_section, sub_slug = parts[0], '/'.join(parts[1:])
            else:
                sub_section, sub_slug = section, parts[-1]
            item = {
                'title': entry['title'],
                'action': 'listing',
                'url': _ref(kind='cy_subindex', section=sub_section, slug=sub_slug, title=entry['title']),
                'isFolder': 'True',
            }
            item['cm'] = _browseable(item)

        if entry.get('image'):
            item['image'] = entry['image']
            item['fanart'] = entry['image']

        built.append(item)

    return built or _empty(i18n(30014))


def _cy_subindex(section, slug):
    """A CY sub-index page, or a direct episode when the page is a player."""

    try:
        result = api.cy_subindex(section, slug)
    except Exception as error:
        # Gated series detail pages (ANT1+ bounce) have no player; surface
        # the folder error rather than a blank listing.
        kodi.infoDialog('{0}: {1}'.format(i18n(30033), error))
        return _empty(i18n(30014))

    if result.get('playable'):
        return [_direct_playable(result)]

    built = []

    for entry in result.get('items', []):
        # Gated series detail pages (ANT1+ bounce) have no player; the
        # resolver raises a clear error for those at playback time.
        item = {
            'title': entry['title'],
            'action': 'play',
            'url': entry['url'],
            'isFolder': 'False',
            'isPlayable': 'True',
        }

        if entry.get('image'):
            item['image'] = entry['image']
            item['fanart'] = entry['image']

        item['cm'] = _browseable(item)
        built.append(item)

    return built or _empty(i18n(30014))


def _direct_playable(result):
    """A CY player page reached directly: episode title + stream url."""

    meta = result.get('meta') or {}

    item = {
        'title': result.get('title', ''),
        'action': 'play',
        'url': result['url'],
        'isFolder': 'False',
        'isPlayable': 'True',
    }

    if result.get('image'):
        item['image'] = result['image']

    # og:image is the generic site logo; prefer the real poster as thumb.
    if meta.get('poster'):
        item['image'] = meta['poster']

    # The site cover is the wide fanart; the card poster stays the thumb.
    item['fanart'] = meta.get('fanart') or result.get('image', '')

    if meta.get('type'):
        item['studio'] = meta['type']

    if meta.get('aired'):
        item['date'] = meta['aired']

    if meta.get('plot'):
        item['plot'] = meta['plot']
        item['plotoutline'] = meta['plot']

    if meta.get('director'):
        item['director'] = meta['director']

    if meta.get('cast'):
        item['cast'] = meta['cast']

    if meta.get('year'):
        item['year'] = meta['year']

    if meta.get('genre'):
        item['genre'] = meta['genre']

    item['cm'] = _browseable(item)

    return item


def _radio():
    """Stations from the public soundis config; streams read fresh."""

    built = []

    for station in _stations():
        item = {
            'title': station['title'],
            'action': 'play_radio',
            'url': station['url'],
            'isFolder': 'False',
            'isPlayable': 'True',
        }

        if station.get('subtitle'):
            item['plot'] = station['subtitle']

        if station.get('image'):
            item['image'] = station['image']
            item['fanart'] = station['image']

        built.append(item)

    return built or _empty(i18n(30014))


def _paged(ref, page, total_pages, items):
    """Wraps entries with Previous/Next page navigation."""

    built = []

    if page > 1:
        built.append({
            'title': i18n(30030),
            'action': 'listing',
            'url': _ref(**ref),
            'query': str(page - 1),
            'isFolder': 'True',
            'image': kodi.addonmedia('previous.png'),
        })

    built.extend(_entries(items))

    if page < total_pages:
        built.append({
            'title': i18n(30031),
            'action': 'listing',
            'url': _ref(**ref),
            'query': str(page + 1),
            'isFolder': 'True',
            'image': kodi.addonmedia('next.jpg'),
        })

    return built or _empty(i18n(30014))


def _clips(items, title=None):
    """Playable clips; an empty archive is an empty folder, not an error."""

    return _entries(items, title=title) or _empty(i18n(30014))


def _entries(items, title=None):

    built = []

    for entry in items:
        if entry.get('playable', True):
            item = {
                'title': entry['title'],
                'action': 'play',
                'url': entry['url'],
                'isFolder': 'False',
                'isPlayable': 'True',
            }
        else:
            # Text articles carry no video; listed for information only.
            item = {
                'title': entry['title'],
                'action': None,
                'isFolder': 'False',
                'isPlayable': 'False',
            }

        if entry.get('image'):
            item['image'] = entry['image']
            item['fanart'] = entry['image']

        if entry.get('date'):
            item['plot'] = entry['date']

        if title:
            item['studio'] = title

        if entry.get('playable', True):
            item['cm'] = _browseable(item)

        built.append(item)

    return built


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------

@urldispatcher.register('play', ['url'])
def play(url):

    from urllib.parse import urlparse

    # Cyprus pages resolve straight through ResolveURL (the resolver reads
    # the player markup itself); only the Greek site needs the pre-flight.
    if 'ant1live.com' not in url:
        parts = urlparse(url).path.rsplit('/', 2)

        if len(parts) < 3 or not parts[-2]:
            kodi.infoDialog(i18n(30034))
            return

        cid = parts[-2]

        try:
            info = api.player_info(cid)
        except Exception as error:
            kodi.infoDialog('{0}: {1}'.format(i18n(30034), error))
            return

        if api.is_redirected(info):
            # Gated ANT1+ originals: the page only bounces, there is no stream.
            kodi.infoDialog(i18n(30069), heading=i18n(30010))
            return

    _resolve(url)


@urldispatcher.register('play_radio', ['url'])
def play_radio(url):

    _play(url, live=True)


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


def _play(stream, live=False):

    path = stream.split('|')[0]
    hls = '.m3u8' in path

    directory.resolve(
        stream,
        dash=hls,
        manifest_type='hls' if hls else None,
        mimetype='application/vnd.apple.mpegurl' if hls else None,
        live=live,
    )


# ---------------------------------------------------------------------------
# Bookmarks / misc
# ---------------------------------------------------------------------------

@urldispatcher.register('bookmarks')
def bookmarks_list():

    from .constants import bookmarks_file

    items = bookmarks.get(path=bookmarks_file()) or []

    if not items:
        directory.builder(_empty(i18n(30009)), content='videos')
        return

    for item in items:
        # Bookmarks were stored from a listing, so restore the playability
        # flags Kodi reads when the container is rebuilt.
        item.update({'action': 'play', 'isFolder': 'False', 'isPlayable': 'True'})
        item['cm'] = [{
            'title': 30502,
            'query': {'action': 'deleteBookmark', 'url': _json(dict(
                (k, v) for k, v in iteritems(item) if k not in ('next', 'cm')))},
        }]

    kodi.setsortmethod('title')

    directory.builder(items, content='videos')


@urldispatcher.register('go_to_root')
def go_to_root():
    directory.run_builtin(action='root', path_history='replace')
