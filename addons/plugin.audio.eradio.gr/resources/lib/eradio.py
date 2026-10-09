# -*- coding: utf-8 -*-

'''
    E-Radio Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json

from fuzzywuzzy import process
from netclient import Net
from tulip import bookmarks as bm, cleantitle, directory, kodi
from tulip.log import log
from tulip.utils import iteritems
from urldispatcher import urldispatcher

from .constants import (
    ALL_LINK, CATEGORIES_LINK, CATEGORY_LINK, DEV_PICKS_LINK, IMAGE_LINK,
    INTERNET_LINK, NEW_LINK, POPULAR_LINK, REGIONS_LINK, REGION_LINK,
    RESOLVE_LINK, TRENDING_LINK, cache_duration, cache_function, reset_cache
)


def _http_json(url):

    # eradio.mobi serves application/json with no charset, and Net's default
    # decoding falls back to ascii (dropping every Greek character), so fetch
    # raw bytes and decode as utf-8 explicitly.
    try:
        response = Net().http_GET(url)
        try:
            response.nodecode(True)
        except Exception:
            pass
        content = response.content
        if isinstance(content, bytes):
            content = content.decode('utf-8', 'replace')
        return json.loads(content)
    except Exception as e:
        log('E-Radio: failed to fetch {0}: {1}'.format(url, e))
        return None


def _icon(name):

    try:
        return kodi.addonmedia(name)
    except Exception:
        return ''


def _image(logo):

    if not logo:
        return ''

    cleaned = logo.strip().lstrip('/')
    image = IMAGE_LINK.format(cleaned)
    image = image.replace('/promo/', '/500/')

    if image.endswith('/nologo.png'):
        return ''

    return cleantitle.replaceHTMLCodes(image)


def _bookmark_cm(item):

    bookmark = dict((k, v) for k, v in iteritems(item) if k != 'next')
    bookmark['bookmark'] = item['url']
    return {'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}


def _make_playable(item):

    item.update({'action': 'play', 'isFolder': 'False', 'isPlayable': 'True'})
    item.update({'cm': [_bookmark_cm(item)]})
    return item


def _text(value, fallback=''):

    # directory.builder needs real strings: int ids must be resolved first,
    # otherwise labels/info tags end up broken.
    if isinstance(value, int):
        try:
            return kodi.i18n(value)
        except Exception:
            return fallback
    return value or fallback


def _item(entry):

    entry = dict(entry)
    if 'title' in entry:
        entry['title'] = _text(entry['title'], 'Unknown')
    if isinstance(entry.get('cm'), list):
        fixed = []
        for cm in entry['cm']:
            cm = dict(cm)
            cm['title'] = _text(cm.get('title'), '')
            fixed.append(cm)
        entry['cm'] = fixed
    if 'query' in entry and not isinstance(entry['query'], str):
        entry.pop('query')
    return entry


def _build(items, **kwargs):

    directory.builder([_item(i) for i in items], **kwargs)


@urldispatcher.register('root')
def root():

    main_items = [
        {'title': 30001, 'action': 'radios', 'url': ALL_LINK, 'icon': _icon('all.png'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30002, 'action': 'bookmarks', 'icon': _icon('bookmarks.png'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30006, 'action': 'search', 'icon': _icon('search.png'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30003, 'action': 'radios', 'url': TRENDING_LINK, 'icon': _icon('trending.png'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30004, 'action': 'radios', 'url': POPULAR_LINK, 'icon': _icon('popular.png'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30005, 'action': 'radios', 'url': NEW_LINK, 'icon': _icon('new.png'),
         'isFolder': 'True', 'isPlayable': 'False'},
    ]

    categories = directory_list(CATEGORIES_LINK)

    if categories is None:
        return

    for i in categories:
        i.update(
            {
                'icon': _icon('categories.png'), 'action': 'radios', 'isFolder': 'True',
                'isPlayable': 'False'
            }
        )

    regions = directory_list(REGIONS_LINK)

    if regions is None:
        return

    for i in regions:
        i.update({'icon': _icon('regions.png'), 'action': 'radios',
                  'isFolder': 'True', 'isPlayable': 'False'})

    # No separate developer picks entry: the external picks are merged into
    # the "Internet Radios" region listing and into search results instead.
    # dev_picks_list = [{'title': 30503, 'action': 'dev_picks', 'icon': _icon('recommended.png')}]

    self_list = main_items + categories + regions

    for item in self_list:
        item.update({'cm': [{'title': 30009, 'query': {'action': 'clear_cache'}}]})

    _build(self_list)


@urldispatcher.register('search')
def search():

    input_str = kodi.inputDialog(heading=kodi.i18n(30006))

    if not input_str:
        return

    items = (radios_list(ALL_LINK) or []) + (_devpicks() or [])

    if not items:
        return

    # Dict choices make extract() return (match, score, index), so duplicate
    # station names resolve to the correct station instead of the first one.
    choices = dict((idx, cleantitle.strip_accents(i['title'])) for idx, i in enumerate(items))
    query = cleantitle.strip_accents(input_str)

    try:
        raw_matches = process.extract(query, choices, limit=10)
    except Exception as e:
        log('E-Radio: search failed: {0}'.format(e))
        return

    data = []

    for match in raw_matches or []:
        try:
            if len(match) == 3:
                _title, score, idx = match
            else:
                _title, score = match
                idx = None
        except Exception:
            continue

        if score < 70:
            continue

        if idx is None:
            continue

        try:
            data.append(items[int(idx)])
        except (IndexError, TypeError, ValueError):
            continue

    if not data:
        kodi.infoDialog(kodi.i18n(30010))
        return

    for i in data:
        _make_playable(i)

    kodi.setsortmethod('title')

    _build(data, content='songs', infotype='music')


@urldispatcher.register('bookmarks')
def bookmarks():

    self_list = bm.get()

    if not self_list:
        _build([{'title': kodi.i18n(30007), 'isFolder': 'False', 'isPlayable': 'False'}])
        return

    for i in self_list:
        bookmark = dict((k, v) for k, v in iteritems(i) if k != 'next')
        bookmark['delbookmark'] = i['url']
        i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

    try:
        self_list.sort(key=lambda k: k['title'].lower())
    except Exception:
        pass

    _build(self_list, content='songs', infotype='music')


@urldispatcher.register('radios', kwargs=['url'])
def radios(url):

    self_list = radios_list(url) or []

    if url == INTERNET_LINK:
        self_list = self_list + (_devpicks() or [])

    if not self_list:
        return

    for i in self_list:
        _make_playable(i)

    kodi.setsortmethod('title')

    _build(self_list, content='songs', infotype='music')


# Developer's picks live in a gist (they are outside e-radio's database).
# Disabled ("enable" != "1") stations are skipped. They are merged into the
# "Internet Radios" region listing and into search results.
@cache_function(cache_duration(360))
def _devpicks():

    result = _http_json(DEV_PICKS_LINK)

    if not isinstance(result, dict):
        return []

    data = []

    for station in result.get('stations', []):
        try:
            if str(station.get('enable')) != '1':
                continue

            name = cleantitle.replaceHTMLCodes((station.get('name') or '').strip()).strip()
            stream = cleantitle.replaceHTMLCodes((station.get('url') or '').strip())

            if not name or not stream:
                continue

            logo = (station.get('logo') or '').strip()
            image = cleantitle.replaceHTMLCodes(logo) if logo else ''

            data.append(
                {
                    'title': name, 'image': image, 'url': stream,
                    'action': 'play', 'isFolder': 'False', 'isPlayable': 'True'
                }
            )
        except Exception:
            continue

    return data


@urldispatcher.register('play', kwargs=['url'])
def play(url):

    if url.isdigit():

        resolved = resolve(url)

        if resolved is None:
            kodi.infoDialog(kodi.i18n(30010))
            return

        title, url, image = resolved

        directory.resolve(url, {'title': title}, image)

    else:

        directory.resolve(url)


@cache_function(cache_duration(360))
def directory_list(url):

    result = _http_json(url)

    if not isinstance(result, dict):
        return None

    if 'categories' in result:
        items = result['categories']
    elif 'countries' in result:
        items = result['countries']
    else:
        log('E-Radio: unexpected directory payload from {0}'.format(url))
        return None

    self_list = []

    for item in items:
        try:
            if 'categoryName' in item:
                title = item['categoryName']
            elif 'regionName' in item:
                title = item['regionName']
            else:
                continue
            title = cleantitle.replaceHTMLCodes(title).strip()

            if not title:
                continue

            if 'categoryID' in item:
                link = CATEGORY_LINK.format(str(item['categoryID']))
            elif 'regionID' in item:
                link = REGION_LINK.format(str(item['regionID']))
            else:
                continue
            link = cleantitle.replaceHTMLCodes(link)

            self_list.append({'title': title, 'url': link})
        except Exception:
            continue

    return self_list


@cache_function(cache_duration(360))
def radios_list(url):

    result = _http_json(url)

    if not isinstance(result, dict):
        return None

    items = result.get('media')

    if not items:
        return None

    self_list = []

    for item in items:
        try:
            title = cleantitle.replaceHTMLCodes(item['name'].strip()).strip()

            if not title:
                log('E-Radio: skipping station with blank title (ID {0})'.format(item.get('stationID')))
                continue

            link = cleantitle.replaceHTMLCodes(str(item['stationID']))
            image = _image(item.get('logo'))
            self_list.append({'title': title, 'url': link, 'image': image})
        except Exception:
            continue

    return self_list


@cache_function(cache_duration(360))
def resolve(url):

    link = RESOLVE_LINK.format(url)

    result = _http_json(link)

    try:
        item = result['media'][0]
        media_url = item['mediaUrl'][0]
        stream = (media_url.get('liveURL') or '').strip()
        protocol = (media_url.get('liveProtocol') or '').strip().lower()
    except Exception as e:
        log('E-Radio: failed to resolve {0}: {1}'.format(url, e))
        return None

    if not stream:
        return None

    if stream.startswith('https://') or stream.startswith('http://'):
        pass
    elif stream.startswith('//'):
        stream = 'https:{0}'.format(stream)
    else:
        scheme = 'https://' if protocol == 'https' else 'http://'
        stream = '{0}{1}'.format(scheme, stream.lstrip('/'))

    stream = cleantitle.replaceHTMLCodes(stream)

    title = cleantitle.replaceHTMLCodes(item.get('name', '').strip()).strip() or url
    image = _image(item.get('logo'))

    return title, stream, image


# Utils:

@urldispatcher.register('clear_cache')
def cache_clear():

    try:
        ok = bool(reset_cache())
    except Exception as e:
        log('E-Radio: cache clear failed: {0}'.format(e))
        ok = False

    kodi.infoDialog(kodi.i18n(30008 if ok else 30010))
    kodi.refresh()


@urldispatcher.register('addBookmark', kwargs=['url'])
def addBookmark(url):

    bm.add(url)


@urldispatcher.register('deleteBookmark', kwargs=['url'])
def deleteBookmark(url):

    bm.delete(url)
