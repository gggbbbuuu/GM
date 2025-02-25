# -*- coding: utf-8 -*-

'''
    E-Radio Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import absolute_import

import json, os
from io import BytesIO
from PIL import Image
from tulip import bookmarks as bm, directory, client, cache, control
from tulip.fuzzywuzzy import process
from tulip.compat import unicode, iteritems, is_py3
from tulip.cleantitle import strip_accents
from tulip.user_agents import mobile_agent
from tulip.url_dispatcher import urldispatcher
from .constants import *


cache_function = cache.FunctionCache().cache_function
clear_cache = cache.FunctionCache().reset_cache

if is_py3:
    LOGOS_DIR = control.join(control.addonPath, "resources", "media", "logos")
    dLOGOS_DIR = control.join(control.dataPath, "logos")
else:
    LOGOS_DIR = control.join(control.addonPath, "resources", "media", "logos").decode('utf-8')
    dLOGOS_DIR = control.join(control.dataPath, "logos").decode('utf-8')
if not os.path.exists(LOGOS_DIR):
    os.makedirs(LOGOS_DIR)
if not os.path.exists(dLOGOS_DIR):
    os.makedirs(dLOGOS_DIR)

@urldispatcher.register('root')
def root():

    main_items = [
        {
            'title': control.lang(30001),
            'action': 'radios',
            'url': ALL_LINK,
            'icon': 'all.png'
        }
        ,
        {
            'title': control.lang(30002),
            'action': 'bookmarks',
            'icon': 'bookmarks.png'
        }
        ,
        {
            'title': control.lang(30006),
            'action': 'search',
            'icon': 'search.png'
        }
        ,
        # {
            # 'title': control.lang(30003),
            # 'action': 'radios',
            # 'url': TRENDING_LINK,
            # 'icon': 'trending.png'
        # }
        # ,
        {
            'title': control.lang(30004),
            'action': 'radios',
            'url': POPULAR_LINK,
            'icon': 'popular.png'
        }
        ,
        {
            'title': control.lang(30005),
            'action': 'radios',
            'url': NEW_LINK,
            'icon': 'new.png'
        }
    ]

    categories = directory_list(CATEGORIES_LINK)

    if categories is None:
        return

    for i in categories:
        i.update({'icon': 'categories.png', 'action': 'radios'})

    regions = directory_list(REGIONS_LINK)

    if regions is None:
        return

    for i in regions:
        i.update({'icon': 'regions.png', 'action': 'radios'})

    dev_picks_list = [{'title': control.lang(30503), 'action': 'dev_picks', 'icon': 'recommended.png'}]

    self_list = main_items + dev_picks_list + categories + regions

    for item in self_list:

        cc = {'title': 30009, 'query': {'action': 'clear_cache'}}
        item.update({'cm': [cc]})

    directory.add(self_list, content='files')


@urldispatcher.register('search')
def search():

    input_str = control.inputDialog()

    if not input_str:
        return

    items = radios_list(ALL_LINK) + _devpicks()

    if is_py3:

        titles = [strip_accents(i['title']) for i in items]

        matches = [
            titles.index(t) for t, s in process.extract(
                strip_accents(input_str), titles, limit=10
            ) if s >= 70
        ]

    else:

        titles = [strip_accents(i['title']).encode('unicode-escape') for i in items]

        matches = [
            titles.index(t) for t, s in process.extract(
                strip_accents(input_str).encode('unicode-escape'), titles, limit=10
            ) if s >= 70
        ]

    data = []

    for m in matches:
        data.append(items[m])

    if not data:

        control.infoDialog(30010)

        return

    else:

        for i in data:
            i.update({'action': 'play', 'isFolder': 'False'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        control.sortmethods('title')
        directory.add(data, infotype='music')


@urldispatcher.register('bookmarks')
def bookmarks():

    self_list = bm.get()

    if not self_list:
        na = [{'title': control.lang(30007), 'action': None}]
        directory.add(na)
        return

    for i in self_list:

        bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
        bookmark['delbookmark'] = i['url']
        i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

    self_list.sort(key=lambda k: k['title'].lower())

    directory.add(self_list, infotype='music')


@urldispatcher.register('radios', ['url'])
def radios(url):

    self_list = radios_list(url)

    if self_list is None:
        return

    if url == ALL_LINK:

        self_list.extend(_devpicks())

    for i in self_list:

        i.update({'action': 'play', 'isFolder': 'False'})
        bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
        bookmark['bookmark'] = i['url']
        i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

    control.sortmethods('title')

    directory.add(self_list, infotype='music')


@cache_function(21600)
def _devpicks():

    xml = client.request('http://alivegr.net/raw/radios.xml')

    items = client.parseDOM(xml, 'station', attrs={'enable': '1'})

    data = []

    for item in items:

        name = unicode(client.parseDOM(item, 'name')[0])
        logo = client.parseDOM(item, 'logo')[0]
        url = client.parseDOM(item, 'url')[0]

        data.append({'title': name, 'image': logo, 'url': url, 'action': 'play', 'isFolder': 'False'})

    return data


@urldispatcher.register('dev_picks')
def dev_picks():

    self_list = _devpicks()

    if self_list is None:
        return

    for i in self_list:
        bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
        bookmark['bookmark'] = i['url']
        i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

    directory.add(self_list, infotype='music')


@urldispatcher.register('play', ['url'])
def play(url):

    if url.isdigit():

        resolved = resolve(url)

        if resolved is None:
            return

        title, url, image = resolved

        directory.resolve(url, {'title': title}, image)

    else:

        directory.resolve(url)


@cache_function(21600)
def directory_list(url):

    self_list = []

    result = client.request(url, mobile=True, output='json')

    if 'categories' in result:
        items = result['categories']
    else:
        items = result['countries']

    for item in items:

        if 'categoryName' in item:
            title = item['categoryName']
        else:
            title = item['regionName']
        title = client.replaceHTMLCodes(title)

        if 'categoryID' in item:
            url = CATEGORY_LINK.format(str(item['categoryID']))
        elif 'regionID' in item:
            url = REGION_LINK.format(str(item['regionID']))
        url = client.replaceHTMLCodes(url)

        self_list.append({'title': title, 'url': url})

    return self_list


@cache_function(21600)
def radios_list(url):

    result = client.request(url, mobile=True)
    result = json.loads(result)

    items = result['media']

    self_list = []

    for item in items:

        title = item['name'].strip()
        title = client.replaceHTMLCodes(title)

        url = str(item['stationID'])
        url = client.replaceHTMLCodes(url)

        image = item['logo']
        image = IMAGE_LINK.format(image)
        image = image.replace('/promo/', '/big/')

        if image.endswith('/nologo.png'):
            image = '0'
        else:
            image = get_image(image)

        self_list.append({'title': title, 'url': url, 'image': image})

    return self_list

def get_image(image_url):
    # image_url = client.replaceHTMLCodes(image_url)
    hdrs = {'User-Agent': mobile_agent()}
    try:
        img_name = image_url.split('/')[-1]
        img_path = control.join(LOGOS_DIR, img_name)
        img_dpath = control.join(dLOGOS_DIR, img_name)
        if not os.path.exists(img_path):
            if not os.path.exists(img_dpath):
                response = client.request(image_url, headers=hdrs, as_bytes=True)
                image_data = Image.open(BytesIO(response))
                width, height = image_data.size
                # image_data = image_data.resize((int((width / height) * 256), 256), Image.ANTIALIAS)
                image_data.save(img_dpath)
            return img_dpath
        return img_path
    except:
        return '0'
    
@cache_function(21600)
def resolve(url):

    url = RESOLVE_LINK.format(url)

    result = client.request(url, mobile=True)
    result = json.loads(result.replace('	', ''))

    item = result['media'][0]

    url = item['mediaUrl'][0]['liveURL']

    if not url.startswith('http://'):
        url = '{0}{1}'.format('http://', url)

    url = client.replaceHTMLCodes(url)

    # url = client.request(url, output='geturl')

    title = item['name'].strip()
    title = client.replaceHTMLCodes(title)

    image = item['logo']
    image = IMAGE_LINK.format(image)
    image = image.replace('/promo/', '/500/')

    if image.endswith('/nologo.png'):
        image = '0'
    else:
        image = get_image(image)

    image = client.replaceHTMLCodes(image)

    return title, url, image


# Utils:

@urldispatcher.register('clear_cache')
def cache_clear():

    clear_cache(notify=True, label_success=30008)


@urldispatcher.register('addBookmark', ['url'])
def addBookmark(url):

    bookmarks.add(url)


@urldispatcher.register('deleteBookmark', ['url'])
def deleteBookmark(url):

    bookmarks.delete(url)
