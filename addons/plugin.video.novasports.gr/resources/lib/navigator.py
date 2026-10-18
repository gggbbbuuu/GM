# -*- coding: utf-8 -*-

'''
    Novasports.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json
import re
from datetime import date, datetime, timedelta

from . import api, live, player
from .constants import TAX_SPORT, TAX_EVENT, TAX_TEAM, TAX_SHOW, YT_WATCH
from tulip import kodi, directory, bookmarks
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
    # The site uses this to deduplicate; it must follow any url override.
    bookmark['bookmark'] = bookmark.get('url')
    return [{'title': 30501, 'query': {'action': 'addBookmark', 'url': _json(bookmark)}}]


def _empty(label):
    return [{'title': label, 'action': None, 'isFolder': 'False', 'isPlayable': 'False'}]


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@urldispatcher.register('root')
def root():

    menu = [
        {'title': i18n(30002), 'action': 'live', 'isFolder': 'True'},
        {'title': i18n(30001), 'action': 'listing', 'url': _ref(), 'isFolder': 'True'},
        {'title': i18n(30017), 'action': 'categories', 'isFolder': 'True'},
        {'title': i18n(30003), 'action': 'matchcenter', 'isFolder': 'True'},
        {'title': i18n(30025), 'action': 'search', 'isFolder': 'True'},
        {'title': i18n(30022), 'action': 'bookmarks', 'isFolder': 'True'},
    ]

    for item in menu:
        item['cm'] = [
            {'title': 30010, 'query': {'action': 'clear_cache'}},
            {'title': 30026, 'query': {'action': 'settings'}},
        ]

    directory.builder(menu, content='videos')


@urldispatcher.register('categories')
def categories():

    menu = [
        {'title': i18n(30020), 'action': 'terms', 'url': _ref(taxonomy=TAX_SPORT),
         'isFolder': 'True'},
        {'title': i18n(30027), 'action': 'terms', 'url': _ref(taxonomy=TAX_EVENT),
         'isFolder': 'True'},
        {'title': i18n(30021), 'action': 'terms', 'url': _ref(taxonomy=TAX_TEAM),
         'isFolder': 'True'},
        {'title': i18n(30028), 'action': 'terms', 'url': _ref(taxonomy=TAX_SHOW),
         'isFolder': 'True'},
    ]

    for item in menu:
        item['cm'] = [
            {'title': 30010, 'query': {'action': 'clear_cache'}},
            {'title': 30026, 'query': {'action': 'settings'}},
        ]

    directory.builder(menu, content='videos')


@cache_function(12, 60)
def _terms(taxonomy, page):
    return api.terms(taxonomy, page)


@urldispatcher.register('terms', ['url'], ['query'])
def terms(url, query='1'):

    try:
        taxonomy = json.loads(url)['taxonomy']
    except Exception:
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    labels = {
        TAX_SPORT: i18n(30020),
        TAX_EVENT: i18n(30027),
        TAX_TEAM: i18n(30021),
        TAX_SHOW: i18n(30028),
    }

    try:
        items, total_pages = _terms(taxonomy, query)
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30029), error))
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    listing = []

    for entry in items:
        item = {
            'title': '{0} ({1})'.format(entry['title'], entry['count']),
            'action': 'listing',
            'url': _ref(taxonomy=taxonomy, term=entry['id']),
            'isFolder': 'True',
        }
        item['cm'] = _browseable(item)
        listing.append(item)

    page = int(query or 1)

    if page > 1:
        listing.insert(0, {
            'title': i18n(30030).format(page - 1),
            'action': 'terms',
            'url': url,
            'query': str(page - 1),
            'isFolder': 'True',
        })

    if page < total_pages:
        listing.append({
            'title': i18n(30031).format(page + 1),
            'action': 'terms',
            'url': url,
            'query': str(page + 1),
            'isFolder': 'True',
        })

    directory.builder(listing, content='videos')


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------

@cache_function(15, 60)
def _videos(ref, page):
    return api.videos(
        page=page,
        taxonomy=ref.get('taxonomy'),
        term=ref.get('term'),
        search=ref.get('search'),
        date=ref.get('date'),
    )


@urldispatcher.register('listing', ['url'], ['query'])
def listing(url, query='1'):

    try:
        ref = json.loads(url)
    except Exception:
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    page = int(query or 1)

    try:
        items, total_pages = _videos(ref, page)
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30029), error))
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    if not items and page == 1:
        directory.builder(_empty(i18n(30011)), content='videos')
        return

    next_url = _ref(**ref)

    built = []

    if page > 1:
        built.append({
            'title': i18n(30032).format(page - 1),
            'action': 'listing',
            'url': next_url,
            'query': str(page - 1),
            'isFolder': 'True',
        })

    for video in items:
        item = {
            'title': video['title'],
            'action': 'play',
            'url': video['url'],
            'isFolder': 'False',
            'isPlayable': 'True',
        }

        if video['image']:
            item['image'] = video['image']
            item['fanart'] = video['image']

        if video['plot']:
            item['plot'] = video['plot']

        if video['studio']:
            item['studio'] = video['studio']

        if video['date']:
            item['date'] = video['date'][:10].replace('-', '.')
            item['aired'] = video['date'][:10]
            item['year'] = video['date'][:4]

        # The resolver picks the player from the page itself, so the listing
        # only needs to carry the video page url.
        item['cm'] = _browseable(item)

        built.append(item)

    if page < total_pages:
        built.append({
            'title': i18n(30031).format(page + 1),
            'action': 'listing',
            'url': next_url,
            'query': str(page + 1),
            'isFolder': 'True',
        })

    directory.builder(built, content='videos', cacheToDisc=False)


@urldispatcher.register('search')
def search():

    term = kodi.inputDialog(heading=i18n(30025))

    if not term:
        return

    directory.run_builtin(
        action='listing', url=_ref(search=term), query='1', content_type='videos'
    )


@urldispatcher.register('matchcenter')
def matchcenter():

    _matchcenter(date.today().strftime('%d-%m-%Y'))


@urldispatcher.register('matchcenter_date', ['url'])
def matchcenter_date(url):

    _matchcenter(url)


def _matchcenter(date_string):

    try:
        data = api.match_center(date_string)
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30029), error))
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    events = data.get('events') or []

    listing = []

    for event in events:
        matches = event.get('matches') or []

        if not matches:
            continue

        listing.append({
            'title': event.get('single_name') or event.get('slug'),
            'image': event.get('image') or '',
            'isFolder': 'False',
            'isPlayable': 'False',
        })

        for match in matches:
            name_a = _team((match.get('team_a') or {}).get('name'))
            name_b = _team((match.get('team_b') or {}).get('name'))

            score_a = ((match.get('team_a') or {}).get('score') or '').strip()
            score_b = ((match.get('team_b') or {}).get('score') or '').strip()

            when = (match.get('date') or '').split(' ')[-1]
            timer = match.get('timer') or ''
            desc = match.get('score_desc') or ''

            title = '{0} - {1}'.format(name_a, name_b)

            if score_a or score_b:
                title = '{0} [B]{1} - {2}[/B]'.format(title, score_a, score_b)

            info = ' - '.join([i for i in (when, timer, desc) if i])

            listing.append({
                'title': '{0}[CR]{1}'.format(title, info) if info else title,
                'plot': '{0} - {1}'.format(name_a, name_b),
                # A match page carries news, not videos, so hand the user over
                # to the competition's own video listing.
                'action': 'event_videos',
                'url': event.get('term_link') or '',
                'query': _ref(term=event.get('term_id')),
                'isFolder': 'True',
            })

    if not listing:
        listing = _empty(i18n(30008))

    listing.insert(0, {
        'title': i18n(30007),
        'action': 'matchcenter_date',
        'url': _shift_date(date_string, -1),
        'isFolder': 'False',
        'isPlayable': 'False',
    })

    listing.append({
        'title': i18n(30006),
        'action': 'matchcenter_date',
        'url': _shift_date(date_string, 1),
        'isFolder': 'False',
        'isPlayable': 'False',
    })

    listing.append({
        'title': i18n(30005),
        'action': 'add_date',
        'isFolder': 'False',
        'isPlayable': 'False',
    })

    listing.append({
        'title': i18n(30012),
        'action': 'go_to_root',
        'isFolder': 'False',
        'isPlayable': 'False',
    })

    directory.builder(listing, content='videos', cacheToDisc=False)


def _team(value):
    """
    Matchcentre team names carry their discipline: "ΠΑΟΚ - Ποδόσφαιρο".
    The heading already groups by competition, so drop it.
    """

    name = value.get('name') if isinstance(value, dict) else value

    if not name:
        return ''

    return re.sub(r'\s+-\s+[^-]+$', '', str(name)).strip()


def _shift_date(date_string, days):

    try:
        parsed = datetime.strptime(date_string, '%d-%m-%Y')
    except ValueError:
        return date.today().strftime('%d-%m-%Y')

    return (parsed + timedelta(days=days)).strftime('%d-%m-%Y')


@urldispatcher.register('add_date')
def add_date():

    picked = kodi.inputDialog(heading=i18n(30005), type=kodi.input_date)

    if not picked:
        return

    parts = picked.split('/')

    if len(parts) != 3:
        return

    day, month, year = parts

    directory.run_builtin(
        action='matchcenter_date',
        url='{}-{}-{}'.format(day.zfill(2), month.zfill(2), year),
        content_type='videos',
    )


@urldispatcher.register('event_videos', ['url'], ['query'])
def event_videos(url, query=''):

    """Jumps from a match to that competition's videos on the site."""

    if not query:
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    try:
        ref = json.loads(query)
    except Exception:
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    if not ref.get('term'):
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    listing(_ref(taxonomy=TAX_EVENT, term=ref['term']), '1')


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------

@urldispatcher.register('play', ['url'])
def play(url):

    _resolve(url)


def _resolve(url):

    if _not_started(url):
        return

    try:
        stream, subtitles = player.resolve(url)
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30033), error))
        return

    if subtitles:
        # Kodi reads external subtitles appended to the stream url, and its
        # <path>|<url>|<lang>|<name> syntax expects exactly three parts.
        stream = '{}|{}|{}'.format(
            stream, subtitles[0]['url'], subtitles[0].get('lang') or 'Greek'
        )

    dash = '.m3u8' in stream.split('|')[0] and kodi.setting('hls_dash') == 'true'

    directory.resolve(
        stream,
        dash=dash,
        manifest_type='hls' if dash else None,
        mimetype='application/vnd.apple.mpegurl' if dash else None,
    )


# ---------------------------------------------------------------------------
# Live (YouTube channel)
# ---------------------------------------------------------------------------

@cache_function(4, 60)
def _streams():
    return live.streams()


@urldispatcher.register('live')
def live_listing():

    if not live.available():
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    try:
        entries = _streams()
    except Exception as error:
        kodi.infoDialog('{0}: {1}'.format(i18n(30029), error))
        directory.builder(_empty(i18n(30029)), content='videos')
        return

    if not entries:
        directory.builder(_empty(i18n(30011)), content='videos')
        return

    listing = []

    for entry in entries:
        title = entry['title']

        if entry['is_live']:
            title = '{0}[CR]{1}'.format(title, entry['status'])
        elif entry['status']:
            title = '{0}[CR]{1}'.format(title, entry['status'])

        item = {
            'title': title,
            'action': 'play_live',
            'url': entry['id'],
            'isFolder': 'False',
            'isPlayable': 'True',
            'studio': i18n(30002),
        }

        if entry['image']:
            item['image'] = entry['image']
            item['fanart'] = entry['image']

        # Bookmark the plain watch url so it replays through ResolveURL
        # whether or not this listing still exists.
        item['cm'] = _browseable(item, url=YT_WATCH + entry['id'], action='play')

        listing.append(item)

    directory.builder(listing, content='videos')


@urldispatcher.register('play_live', ['url'])
def play_live(url):

    _resolve(YT_WATCH + _video_id(url))


def _video_id(url):
    """Accepts a bare id or a full watch url (bookmarks store the latter)."""

    if not url.startswith('http'):
        return url

    match = re.search(r'(?:v=|/embed/|/shorts/|/live/)([\w-]{6,})', url)

    return match.group(1) if match else url


def _not_started(video_url):
    """
    True when the url is a YouTube broadcast that has not started yet.

    Such a video has no stream at all, so resolve() would only report
    YouTube's own error. Tell the user when it starts instead, and skip the
    resolve entirely.
    """

    if 'youtube.com/' not in video_url and 'youtu.be/' not in video_url:
        return False

    try:
        info = live.state(_video_id(video_url))
    except Exception:
        return False

    if info['live'] or info['finished']:
        return False

    kodi.infoDialog(
        i18n(30035).format(info['label'] or i18n(30037)),
        heading=i18n(30002), time=8000
    )

    return True


# ---------------------------------------------------------------------------
# Bookmarks / misc
# ---------------------------------------------------------------------------

@urldispatcher.register('bookmarks')
def bookmarks_list():

    items = bookmarks.get() or []

    if not items:
        directory.builder(_empty(i18n(30024)), content='videos')
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