# -*- coding: utf-8 -*-

'''
    ERTflix Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import absolute_import

import json, re, xbmc
from os.path import split
from .constants import *
from .utils import geo_detect, collection_post, tiles_post, live_post, search_post
from tulip import bookmarks as bms, directory, client, cache, control
from tulip.compat import iteritems, range, concurrent_futures, quote, parse_qs
from tulip.parsers import parseDOM, itertags
from tulip.url_dispatcher import urldispatcher
from youtube_resolver import resolve as yt_resolver
import requests
cache_function = cache.FunctionCache().cache_function

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'}

if 'Greek' in control.infoLabel('System.Language'):
    headers.update({'Accept-Language': 'show'})
else:
    headers.update({'Accept-Language': 'en'})
sess = requests.Session()
# Βοηθητική συνάρτηση για εύρεση IDs παντού μέσα στο JSON manalab
def find_all_ids(data):
    ids = []
    if isinstance(data, dict):
        # Έλεγχος αν το ίδιο το αντικείμενο είναι πλακίδιο
        if 'id' in data and ('title' in data or 'codename' in data):
            ids.append(data['id'])
        
        # Έλεγχος για λίστες με tiles
        if 'tiles' in data:
            if isinstance(data['tiles'], list):
                for t in data['tiles']:
                    if isinstance(t, dict) and 'id' in t:
                        ids.append(t['id'])
                    elif isinstance(t, (str, int)):
                        ids.append(str(t))
        
        if 'tilesIds' in data and isinstance(data['tilesIds'], list):
            ids.extend([str(x) for x in data['tilesIds']])

        # Αναδρομική αναζήτηση
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                ids.extend(find_all_ids(value))
                
    elif isinstance(data, list):
        for item in data:
            ids.extend(find_all_ids(item))
            
    return ids


@urldispatcher.register('root')
def root():

    menu = [
        {
            'title': control.lang(30001),
            'action': 'live',
            'icon': 'channels.jpg'
        }
        ,
        {
            'title': control.lang(30002),
            'action': 'listing',
            'url': 'vods',
            'icon': 'recent.jpg'
        }
        ,
        {
            'title': control.lang(30015),
            'action': 'enter_yt_channel',
            'icon': 'youtube.jpg',
            'url': ''.join(
                ['plugin://plugin.video.youtube/channel/', CHANNEL_ID, '/?addon_id=', control.addonInfo('id')]
            ),
            'isFolder': 'False', 'isPlayable': 'False'
        }
        ,
        {
            'title': control.lang(30004),
            'action': 'listing',
            'url': NEWS_LINK,
            'icon': 'news.jpg'
        }
        ,
        {
            'title': control.lang(30049),
            'action': 'categories',
            'icon': 'movies.jpg',
            'url': MOVIES_LINK
        }
        ,
        {
            'title': control.lang(30020),
            'action': 'categories',
            'url': SHOWS_LINK,
            'icon': 'shows.jpg'
        }
        ,
        {
            'title': control.lang(30038),
            'action': 'categories',
            'url': SERIES_LINK,
            'icon': 'series.jpg'
        }
        ,
        {
            'title': control.lang(30017),
            'action': 'categories',
            'icon': 'documentaries.jpg',
            'url': DOCUMENTARIES_LINK
        }
        ,
        {
            'title': control.lang(30003),
            'action': 'categories',
            'url': SPORTS_LINK,
            'icon': 'sports.jpg'
        }
        ,
        {
            'title': control.lang(30005),
            'action': 'categories',
            'url': INFO_LINK,
            'icon': 'interviews.jpg'
        }
        ,
        {
            'title': control.lang(30055),
            'action': 'categories',
            'url': ARCHIVE_LINK,
            'icon': 'archive.jpg'
        }
        ,
        {
            'title': control.lang(30060),
            'action': 'categories',
            'url': KIDS_LINK,
            'icon': 'kids.jpg'
        }
        ,
        # {
            # 'title': control.lang(30019),
            # 'action': 'index',
            # 'icon': 'index.jpg'
        # }
        # ,
        {
            'title': control.lang(30012),
            'action': 'bookmarks',
            'icon': 'bookmarks.jpg'
        }
        ,
        {
            'title': control.lang(30026),
            'action': 'radios',
            'icon': 'radio.jpg'
        }
    ]

    settings_menu = {
            'title': control.lang(30044),
            'action': 'settings',
            'icon': 'settings.jpg',
            'isFolder': 'False', 'isPlayable': 'False'
        }

    exit_button = {
        'title': control.lang(30048),
        'action': 'exit_kodi',
        'icon': 'exit.jpg',
        'isFolder': 'False', 'isPlayable': 'False'
    }

    if control.setting('settings_boolean') == 'true':
        menu.append(settings_menu)

    if control.setting('show_exit') == 'true':
        menu.append(exit_button)

    for item in menu:

        clear_cache = {'title': 30036, 'query': {'action': 'clear_cache'}}
        settings = {'title': 30039, 'query': {'action': 'settings'}}
        item.update({'cm': [clear_cache, settings]})

    directory.add(menu, content='videos')


@urldispatcher.register('bookmarks')
def bookmarks():

    self_list = bms.get()

    if not self_list:
        na = [{'title': control.lang(30058), 'action': None}]
        directory.add(na)
        return

    for i in self_list:
        bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
        bookmark['delbookmark'] = i['url']
        i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

    if control.setting('bookmarks_clear_boolean') == 'true':

        clear_menu = {
            'title': control.lang(30059), 'action': 'clear_bookmarks', 'isFolder': 'False', 'isPlayable': 'False'
        }

        self_list.insert(0, clear_menu)

    control.sortmethods()
    control.sortmethods('title')

    directory.add(self_list, content='videos')


@cache_function(3600)
def get_live():

    # FilterNowOnTvTiles = client.request(FILTER_NOW_ON_TV_TILES, headers=headers, output='json')
    FilterNowOnTvTiles = sess.get(FILTER_NOW_ON_TV_TILES, headers=headers).json()
    
    if not FilterNowOnTvTiles: return []

    channels = FilterNowOnTvTiles.get('Channels', [])

    fnotvtiles_channel_list = []

    for channel in channels:

        c = {'id': channel['Id']}
        fnotvtiles_channel_list.append(c)

    # GetTiles = client.request(GET_TILES, headers=headers, post=live_post(fnotvtiles_channel_list), output='json')
    GetTiles = sess.post(GET_TILES, headers=headers, data=live_post(fnotvtiles_channel_list)).json()
    if not GetTiles: return []

    stations = GetTiles.get('tiles', [])

    self_list = []

    for station in stations:

        if station['isRegionRestrictionEnabled'] and not geo_detect:
            continue

        title = station['title']
        image = station['images'][0]['url']
        fanart = station['images'][1]['url']
        try:
            codename = station['tileChannel']['codename']
        except KeyError:
            codename = station['codename']
        # acquire_content = client.request(ACQUIRE_CONTENT.format(DEVICE_KEY, codename), headers=headers, output='json')
        acquire_content = sess.get(ACQUIRE_CONTENT.format(DEVICE_KEY, codename), headers=headers).json()
        try:
            url = acquire_content['MediaFiles'][0]['Formats'][0]['Url']
        except:
            continue
            
        data = {'title': title.replace(' LIVE', ''), 'image': image, 'fanart': fanart, 'url': url}
        self_list.append(data)

    return self_list


@urldispatcher.register('live')
def live():

    self_list = get_live()

    for i in self_list:
        i.update({'action': 'play', 'isFolder': 'false'})

    directory.add(self_list)


@cache_function(2880)
def index_listing():

    # html = client.request(INDEX_LINK, headers=headers)
    html = sess.get(INDEX_LINK, headers=headers).content.decode('utf-8')
    li = parseDOM(html, 'li')

    li.extend(parseDOM(html, 'li', attrs={'class': 'hideli'}))

    items = [i for i in li if 'title' in i]

    self_list = []

    for item in items:

        title = client.replaceHTMLCodes(parseDOM(item, 'a')[0])
        url = parseDOM(item, 'a', ret='href')[0]

        self_list.append({'title': title, 'url': url})

    self_list.sort(key=lambda k: k['title'].lower())

    return self_list


@urldispatcher.register('index')
def index():

    try:
        self_list = index_listing()
    except Exception:
        return

    for i in self_list:
        i.update({'action': 'sub_index'})

    for i in self_list:
        bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
        bookmark['bookmark'] = i['url']
        i.update({'cm': [{'title': 30006, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

    directory.add(self_list, content='videos')


@urldispatcher.register('sub_index', ['url'])
def sub_index(url):

    self_list = sub_index_listing(url)

    for i in self_list:
        try:
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            bookmark['title'] = i['title'].rpartition(' - ')[0]
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})
        except KeyError:
            pass

    directory.add(self_list, content='videos')


@cache_function(3600)
def sub_index_listing(url):

    # html = client.request(url, headers=headers)
    html = sess.get(url, headers=headers).content.decode('utf-8')

    name = client.parseDOM(html, 'h1', attrs={'class': 'tdb-title-text'})[0]
    name = client.replaceHTMLCodes(name)

    links = [l for l in list(itertags(html, 'a')) if 'su-button' in l.attributes.get('class', '')]

    if not links:
        links = [l for l in list(itertags(html, 'a')) if l.text and u'Επεισόδια' in l.text]

    description = client.replaceHTMLCodes(client.stripTags(client.parseDOM(html, 'div', attrs={'class': 'tdb-block-inner td-fix-index'})[-2]))

    if '</div>' in description:
        description = client.stripTags(description.partition('</div>')[2])
    else:
        description = client.stripTags(description)

    image_div = [i for i in list(itertags(html, 'div')) if 'sizes' in i.text]
    image = re.search(r'w, (http.+?\.(?:jpg|png)) 300w', image_div[0].text).group(1)
    fanart = re.search(r'(http.+?\.(?:jpg|png))', image_div[0].text).group(1)

    self_list = []

    for link in links:

        title = ' - '.join([name, client.stripTags(link.text).strip()])
        url = client.replaceHTMLCodes(link.attributes['href'])

        action = 'listing'

        if 'series' in link.attributes['href']:
            url = split(url)[1].split('-')[0]
            url = GET_SERIES_DETAILS.format(url)
        elif 'vod' in link.attributes['href']:
            action = 'play'

        data = {'title': title, 'url': url, 'image': image, 'fanart': fanart, 'plot': description, 'action': action}

        if data['action'] == 'play':
            data.update({'title': name, 'label': title, 'isFolder': 'False'})

        self_list.append(data)

    if not self_list:
        self_list.append(
            {
                'title': ''.join([name, ' - ', control.lang(30022)]), 'action': 'read_plot', 'isFolder': 'False',
                'isPlayable': 'False', 'plot': description, 'image': image, 'fanart': fanart
            }
        )

    plot_item = {
        'title': ''.join(['[B]', name, ' - ', control.lang(30021), '[/B]']), 'action': 'read_plot', 'isFolder': 'False',
        'isPlayable': 'False', 'plot': description, 'image': image, 'fanart': fanart
    }

    self_list.append(plot_item)

    return self_list


@urldispatcher.register('read_plot')
def read_plot():

    heading = control.infoLabel('Listitem.Title')
    plot = control.infoLabel('Listitem.Plot')

    control.dialog.textviewer(heading=heading, text=plot)


@cache_function(1800)
def recursive_list_items(url):
    page = 1
    total_pages = 1
    tiles_post_list = []
    
    next_post = None

    if url.startswith('https'):

        if BASE_API_LINK not in url:
            # Fallback Legacy
            # html = client.request(url, headers=headers)
            html = sess.get(url, headers=headers).content.decode('utf-8')
            try:
                script = [i for i in client.parseDOM(html, 'script') if 'INITIAL_STATE' in i][0]
                script = re.sub(r'var _*?\w+_*? = ', '', script).replace(';</script>', '')
                if script.endswith(';'):
                    script = script[:-1]
                _json = json.loads(script)
            except:
                _json = {}
        else:
            # _json = client.request(url, headers=headers)
            _json = sess.get(url, headers=headers).json()

        if '/list' in url:
            try:
                codename = split(url)[1].partition('=')[2]
                total_pages = _json['pages']['sectionsByCodename'][codename]['totalPages']
                page = _json['pages']['sectionsByCodename'][codename]['fetchedPage']
                tiles = _json['pages']['sectionsByCodename'][codename]['tilesIds']
                tiles_post_list = [{'id': i} for i in tiles]
            except:
                pass

        else:

            tiles = []
            if 'GetSeriesDetails' in url:
                episode_groups = _json.get('episodeGroups', [])
                for group in episode_groups:
                    episodes = group.get('episodes', [])
                    for episode in episodes:
                        if 'id' in episode:
                            tiles.append(episode['id'])
                tiles_post_list = [{'id': i} for i in tiles]
                total_pages = 1

            elif 'GetPageContent' in url or 'GetSectionContent' in url:
                # UNIVERSAL ID EXTRACTION FOR CATEGORIES
                # This scans the whole JSON for 'tiles' or 'tilesIds' lists and grabs IDs
                # This solves the issue where tiles are hidden or incomplete
                
                raw_ids = find_all_ids(_json)
                
                # Remove duplicates and prepare for POST
                seen = set()
                for i in raw_ids:
                    if i and i not in seen:
                        tiles_post_list.append({'id': i})
                        seen.add(i)
                
                try:
                    _json = _json.get('sectionContent', _json)
                    page = _json['pagination']['page']
                    total_pages = _json['pagination']['totalPages']
                except:
                    total_pages = 1

            else:
                try:
                    codenames = list(_json['pages']['sectionsByCodename'].keys())
                    for codename in codenames:
                        tiles_list = _json['pages']['sectionsByCodename'][codename]['tilesIds']
                        tiles.extend(tiles_list)
                    tiles_post_list = [{'id': i} for i in tiles]
                    total_pages = 1
                except:
                    tiles_post_list = []
                    total_pages = 0

    else:
        # VODS / SEARCH path
        if url.startswith('{"platformCodename":"www"'):
            collection_json = json.loads(url)
            url = collection_json['orCollectionCodenames']
            page = collection_json['page']

        # filter_tiles = client.request(FILTER_TILES, headers=headers, post=collection_post(url, page), output='json')
        filter_tiles = sess.post(FILTER_TILES, headers=headers, data=collection_post(url, page)).json()
        if filter_tiles:
            total_pages = filter_tiles['pagination']['totalPages']
            page = filter_tiles['pagination']['page']
            tiles = filter_tiles['tiles']
            tiles_post_list = [{'id': i['id']} for i in tiles]
        else:
            tiles_post_list = []
            total_pages = 0
    if total_pages > 1 and page < total_pages:
        page = page + 1
        if 'GetSectionContent' in url:
            next_post = re.sub(r'page=\d+', 'page={}'.format(page), url)
        else:
            next_post = collection_post(url, page)
    else:
        next_post = None

    if not tiles_post_list:
        xbmc.log("ERTFLIX: No IDs found for URL: " + str(url), xbmc.LOGINFO)
        return []
    # Always fetch full details
    tiles_list = []
    while len(tiles_post_list) > 200:
        # get_tiles = client.request(GET_TILES, headers=headers, post=tiles_post(tiles_post_list[:200]), output='json')
        get_tiles = sess.post(GET_TILES, headers=headers, data=tiles_post(tiles_post_list[:200])).json()
        if not get_tiles and not tiles_list:
            return []
        tiles_list+=get_tiles.get('tiles', [])
        del tiles_post_list[:200]
    if tiles_post_list:
        # get_tiles = client.request(GET_TILES, headers=headers, post=tiles_post(tiles_post_list), output='json')
        get_tiles = sess.post(GET_TILES, headers=headers, data=tiles_post(tiles_post_list)).json()
        if not get_tiles and not tiles_list:
            return []
        tiles_list+=get_tiles.get('tiles', [])

    self_list = []

    for tile in tiles_list:

        if tile.get('isRegionRestrictionEnabled') and not geo_detect:
            continue

        title = tile.get('title')
        endpublish = tile.get('endPublishDate', '')
        if endpublish:
            if not endpublish.startswith('9999'):
                endpublish = '[COLORkhaki][I]{}[/I][/COLOR][CR]'.format(control.lang(30065).format(endpublish.split('T')[0]))
            else:
                endpublish = ''
        if 'subtitle' in tile and tile['subtitle']:
            title = ' - '.join([title, tile['subtitle']])
        try:
            if tile.get('isEpisode'):
                try:
                    season = ' '.join([control.lang(30063), str(tile['season']['seasonNumber'])])
                except KeyError:
                    season = None
                if not season:
                    subtitle = ' '.join([control.lang(30064), str(tile['episodeNumber'])])
                else:
                    try:
                        subtitle = ''.join(
                            [
                                season, ', ', control.lang(30064),
                                ' ', str(tile['episodeNumber'])
                            ]
                        )
                    except KeyError:
                        subtitle = tile['publishDate'].partition('T')[0]
                        subtitle = '/'.join(subtitle.split('-')[::-1])
                title = '[CR]'.join([title, subtitle])
        except Exception:
            pass

        images = tile.get('images', [])
        fanart = control.fanart()
        image = ''

        if len(images) == 1:
            image = images[0]['url']
        elif len(images) > 1:
            image_list = [
                [i['url'] for i in images if i.get('isMain')], 
                [i['url'] for i in images if i.get('role') == 'hbbtv-icon'],
                [i['url'] for i in images if i.get('role') == 'photo'], 
                [i['url'] for i in images if i.get('role') == 'hbbtv-background']
            ]

            for i in image_list:
                if i:
                    image = i[0]
                    break

            fanart_list = [
                [i['url'] for i in images if i.get('role') == 'photo-details'],
                [i['url'] for i in images if i.get('role') == 'hbbtv-background'],
                [i['url'] for i in images if i.get('role') == 'photo' and 'ertflix-background' in i['url']]
            ]

            for f in fanart_list:
                if f and len(f) > 1:
                    fanart = f[1]
                    break
                elif f and len(f) == 1:
                    fanart = f[0]
                    break

        codename = tile.get('codename')
        vid = tile.get('id')

        if not title or not vid:
            continue

        plots = [
            tile.get('description'), tile.get('shortDescription'), tile.get('tinyDescription'), tile.get('subtitle'),
            tile.get('subTitle')
        ]

        plot = control.lang(30014)

        for p in plots:
            if p:
                plot = client.stripTags(p)
                plot = client.replaceHTMLCodes(plot)
                break

        year = tile.get('year')

        if not year:
            try:
                year = int(tile.get('productionYears')[:4])
            except Exception:
                year = 2021

        if tile.get('hasPlayableStream') and not tile.get('type') == 'ser':
            url = VOD_LINK.format('-'.join([vid, codename]))
        else:
            url = GET_SERIES_DETAILS.format(vid)

        data = {
            'title': title, 'image': image, 'fanart': fanart, 'url': url, 'plot': endpublish+plot,
            'year': year
        }

        if tile.get('durationSeconds'):
            data.update({'duration': tile.get('durationSeconds')})

        if next_post:
            data.update(
                {
                    'next': next_post, 'nextaction': 'listing', 'nextlabel': 30500,
                    'nexticon': control.addonmedia('next.jpg')
                }
            )

        if tile.get('hasPlayableStream') and not tile.get('type') == 'ser':
            data.update({'action': 'play', 'isFolder': 'False'})
        else:
            data.update({'action': 'listing'})

        self_list.append(data)

    return self_list


@urldispatcher.register('listing', ['url'])
def listing(url):

    self_list = recursive_list_items(url)

    for i in self_list:
        bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
        bookmark['bookmark'] = i['url']
        i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

    directory.add(self_list, content='videos')


@cache_function(1800)
def category_list(url):
    old_menu_paths = ['show/sport', 'show/news','show/movies','show/documentary','show/series','show/ekpompes','show/archives','show/children']
    if any(url.endswith(x) for x in old_menu_paths):
        codename = url.split('/')[-1]
        url = GET_PAGE_CONTENT.format(1, codename)
    
    if BASE_API_LINK in url:

        # _json = client.request(url, headers=headers, output='json')
        _json = sess.get(url, headers=headers).json()
        if not _json: return []
        
        list_of_lists = []
        
        # Priority check for sections
        if 'sections' in _json:
            list_of_lists = _json['sections']
        elif 'sectionContents' in _json:
            list_of_lists = _json['sectionContents']
        elif 'zones' in _json:
            list_of_lists = _json['zones']

        try:
            codename = parse_qs(split(url)[1])['pageCodename'][0]
        except:
            codename = 'unknown'
            
        try:
            page = _json['pagination']['page']
            total_pages = _json['pagination']['totalPages']
        except:
            page = 1
            total_pages = 1

    else:

        # html = client.request(url, headers=headers)
        html = sess.get(url, headers=headers).content.decode('utf-8')
        script = [i for i in client.parseDOM(html, 'script') if 'INITIAL_STATE' in i][0]
        script = re.sub(r'var _*?\w+_*? = ', '', script).partition(';</script>')[0]
        if script.endswith(';'):
            script = script[:-1]
        _json = json.loads(script)
        pages = _json['pages']
        list_of_lists = [i for i in list(pages['sectionsByCodename'].values()) if 'adman' not in i['sectionContentCodename']]
        codename = list(pages.keys())[-1]
        page = 1
        total_pages = pages[codename]['totalPages']

    next_url = GET_PAGE_CONTENT.format(page + 1, codename)

    self_list = []

    for list_ in list_of_lists:

        title = list_.get('title')
        if not title:
            if 'Greek' in control.infoLabel('System.Language'):
                try:
                    title = list_['algorithmParameters']['categories'][0]['categoryNameTransations']['el']['name']
                except Exception:
                    title = list_.get('portalName', 'Unknown')
            else:
                title = list_.get('portalName', 'Unknown')
        if title == 'Unknown':
            continue

        # Find the codename using multiple possible keys
        section_codename = list_.get('sectionContentCodename') or list_.get('codename') or list_.get('id')
        
        if not section_codename:
             continue
        
        # Construct the URL correctly for GetSectionContent using the proper constant
        url = LIST_OF_LISTS_LINK.format(1, section_codename)

        data = {'title': title, 'url': url}

        if page < total_pages:
            data.update(
                {
                    'nextaction': 'categories', 'nextlabel': 30500, 'nexticon': control.addonmedia('next.jpg'),
                    'next': next_url
                }
            )
        self_list.append(data)

    return self_list


@urldispatcher.register('categories', ['url'])
def categories(url):

    self_list = category_list(url)

    for i in self_list:
        i.update({'action': 'listing'})

    directory.add(self_list)


# @urldispatcher.register('search')
# def search():

    # input_str = control.inputDialog()

    # _json = client.request(SEARCH, headers=headers, post=search_post(input_str), output='json')


@urldispatcher.register('radios')
def radios():

    images = [
        ''.join([RADIO_LINK, i]) for i in [
            '/wp-content/uploads/2016/06/proto.jpg', '/wp-content/uploads/2016/06/deytero.jpg',
            '/wp-content/uploads/2016/06/trito.jpg', '/wp-content/uploads/2016/06/kosmos.jpg',
            '/wp-content/uploads/2016/06/VoiceOgGreece.png', '/wp-content/uploads/2016/06/eraSport.jpg',
            '/wp-content/uploads/2016/06/958fm.jpg', '/wp-content/uploads/2016/06/102fm.jpg'
        ]
    ]

    names = [control.lang(n) for n in list(range(30028, 30036))]

    urls = [
        ''.join([RADIO_STREAM, i]) for i in [
            '/ert-proto', '/ert-deftero', '/ert-trito', '/ert-kosmos', '/ert-voiceofgreece', '/ert-erasport',
            '/ert-958fm', '/ert-102fm'
        ]
    ]

    _radios = map(lambda x, y, z: (x, y, z), names, images, urls)

    self_list = []

    for title, image, link in _radios:

        self_list.append(
            {
                'title': title, 'url': link, 'image': image, 'action': 'play', 'isFolder': 'False',
                'fanart': control.addonmedia('radio_fanart.jpg')
            }
        )

    self_list.insert(
        4,
        {
            'title': 'Zeppelin Radio 106.1', 'action': 'play', 'isFolder': 'False',
            'url': ''.join([RADIO_STREAM, '/ert-zeppelin']), 'image': 'https://i.imgur.com/ep3LptZ.jpg',
            'fanart': control.addonmedia('zeppelin_bg.jpg')
        }
    )

    _district = {
        'title': control.lang(30027), 'action': 'district', 'icon': 'district.jpg',
        'fanart': control.addonmedia('radio_fanart.jpg')
    }

    self_list.append(_district)

    directory.add(self_list)


def _radio_loop(station):

    title = parseDOM(station, 'a')[0]
    href = parseDOM(station, 'a', ret='href')[0]
    html = client.request(href, as_bytes=True)
    html = html.decode('windows-1253')
    link = parseDOM(html, 'iframe', ret='src')[0]
    # embed = client.request(link, headers=headers)
    embed = sess.get(link, headers=headers).content.decode('utf-8')
    url = re.search(r'mp3: [\'"](.+?)[\'"]', embed).group(1).replace('https', 'http')
    image = parseDOM(html, 'img', ret='src')[0]

    data = {'title': title, 'image': image, 'url': url}

    return data


@cache_function(5760)
def district_list():

    result = client.request(DISTRICT_LINK, as_bytes=True)
    result = result.decode('windows-1253')
    _radios = parseDOM(result, 'td')
    stations = [r for r in _radios if r]

    self_list = []

    with concurrent_futures.ThreadPoolExecutor(5) as executor:

        threads = [executor.submit(_radio_loop, station) for station in stations]

        for future in concurrent_futures.as_completed(threads):

            item = future.result()

            if not item:
                continue

            self_list.append(item)

    return self_list


@urldispatcher.register('district')
def district():

    self_list = district_list()

    for i in self_list:
        i.update({'action': 'play', 'isFolder': 'False', 'fanart': control.addonmedia('radio_fanart.jpg')})

    directory.add(self_list)


@cache_function(259200)
def cached_resolve(url):

    codename = split(url)[1].partition('-')[2]

    # _json = client.request(ACQUIRE_CONTENT.format(DEVICE_KEY, codename), headers=headers, output='json')
    _json = sess.get(ACQUIRE_CONTENT.format(DEVICE_KEY, codename), headers=headers).json()

    drm_info = _json.get("DrmInfo")
    # drm_dict = {}
    # if drm_info:
        # for i in drm_info:
            # if i.get("DrmSystem").lower() == "widevine":
                # drm_dict = i
                # break

    for media in _json['MediaFiles']:

        if media['RoleName'] == 'main':

            if len(media['Formats']) == 1:

                return media['Formats'][0]['Url']

            else:
                result_urls = [x['Url'].replace('\\','/') for x in media['Formats']]
                stream_url = ''
                if control.setting('prefer_mpd') == 'true':
                    stream_url = [x for x in result_urls if '.mpd' in x]
                elif drm_info:
                    stream_url = [x for x in result_urls if '.mpd' in x]
                    # if stream_url:
                        # drm_url = json.dumps({"link":stream_url[0], "drm":drm_dict})
                        # return drm_url
                if not stream_url:
                    stream_url = [x for x in result_urls if '.m3u8' in x]
                return stream_url[0]


def resolve(url):

    if url.startswith('plugin://'):

        vid = re.search(r'video_id=([\w-]{11})', url).group(1)

        streams = yt_resolver(vid)

        try:
            addon_enabled = control.addon_details('inputstream.adaptive').get('enabled')
        except KeyError:
            addon_enabled = False

        if not addon_enabled:
            streams = [s for s in streams if 'mpd' not in s['title'].lower()]

        stream = streams[0]['url']

        return stream

    else:

        return cached_resolve(url)

# def resolve_drm(url, drm):
    # import xbmcgui, xbmcplugin, sys
    # handle = int(sys.argv[1])
    # mpd_url = url
    # custom_data = drm.get("DrmChallengeCustomData","")
    # license_key = f'{drm.get("LicenseServerUrl","")}|CustomData={custom_data}|R{{SSM}}|'
    # li = xbmcgui.ListItem(path=mpd_url)
    # li.setProperty("inputstream", "inputstream.adaptive")
    # li.setProperty("inputstream.adaptive.manifest_type", "mpd")
    # li.setProperty("inputstream.adaptive.license_type", "com.widevine.alpha")
    # li.setProperty("inputstream.adaptive.license_key", license_key)
    # li.setProperty("inputstream.adaptive.stream_headers", "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")
    # li.setProperty("inputstream.adaptive.manifest_headers", "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")
    # xbmcplugin.setResolvedUrl(handle, True, li)

@urldispatcher.register('play', ['url'])
def play(url):

    if not any(['.m3u8' in url, '.mpd' in url, 'radiostreaming' in url]):
        url = resolve(url)

    # try:
        # url_drm = json.loads(url)
        # drm_link = url_drm["link"]
        # drm_i = url_drm["drm"]
        # return resolve_drm(drm_link, drm_i)
    # except:
        # pass

    dash = ('.m3u8' in url or '.mpd' in url) and control.kodi_version() >= 18.0

    directory.resolve(
        url, dash=dash,
        mimetype='application/vnd.apple.mpegurl' if 'm3u8' in url else None,
        manifest_type='hls' if 'm3u8' in url else None
    )


@urldispatcher.register('enter_yt_channel', ['url'])
def enter_yt_channel(url):

    control.execute('Container.Update({},return)'.format(url))