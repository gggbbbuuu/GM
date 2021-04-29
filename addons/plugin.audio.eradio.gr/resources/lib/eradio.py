# -*- coding: utf-8 -*-

'''
    E-Radio Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import absolute_import

import json
from tulip import bookmarks, directory, client, cache, control
from tulip.compat import unicode, iteritems
from tulip.cleantitle import strip_accents


cache_method = cache.FunctionCache().cache_method


class Indexer:

    def __init__(self):

        self.list = []; self.data = []
        self.base_link = 'http://eradio.mobi'
        self.image_link = 'http://cdn.e-radio.gr/logos/{0}'
        self.all_link = ''.join([self.base_link, '/cache/1/1/medialist.json'])
        self.trending_link = ''.join([self.base_link, '/cache/1/1/medialistTop_trending.json'])
        self.popular_link = ''.join([self.base_link, '/cache/1/1/medialist_top20.json'])
        self.new_link = ''.join([self.base_link, '/cache/1/1/medialist_new.json'])
        self.categories_link = ''.join([self.base_link, '/cache/1/1/categories.json'])
        self.regions_link = ''.join([self.base_link, '/cache/1/1/regions.json'])
        self.category_link = ''.join([self.base_link, '/cache/1/1/medialist_categoryID{0}.json'])
        self.region_link = ''.join([self.base_link, '/cache/1/1/medialist_regionID{0}.json'])
        self.resolve_link = ''.join([self.base_link, '/cache/1/1/media/{0}.json'])

    def root(self):

        radios = [
            {
                'title': control.lang(30001),
                'action': 'radios',
                'url': self.all_link,
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
            {
                'title': control.lang(30003),
                'action': 'radios',
                'url': self.trending_link,
                'icon': 'trending.png'
            }
            ,
            {
                'title': control.lang(30004),
                'action': 'radios',
                'url': self.popular_link,
                'icon': 'popular.png'
            }
            ,
            {
                'title': control.lang(30005),
                'action': 'radios',
                'url': self.new_link,
                'icon': 'new.png'
            }
        ]

        categories = self.directory_list(self.categories_link)

        if categories is None:
            return

        for i in categories:
            i.update({'icon': 'categories.png', 'action': 'radios'})

        regions = self.directory_list(self.regions_link)

        if regions is None:
            return

        for i in regions:
            i.update({'icon': 'regions.png', 'action': 'radios'})

        dev_picks_list = [{'title': control.lang(30503), 'action': 'dev_picks', 'icon': 'recommended.png'}]

        self.list = radios + dev_picks_list + categories + regions

        for item in self.list:

            cache_clear = {'title': 30009, 'query': {'action': 'cache_clear'}}
            item.update({'cm': [cache_clear]})

        directory.add(self.list, content='files')

    def search(self):

        input_str = control.inputDialog()

        if not input_str:
            return

        items_list = [
            i for i in self.radios(
                self.all_link, return_listing=True
            ) if strip_accents(input_str.lower()) in i['title'].lower()
        ]

        if not items_list:
            return

        control.sortmethods('title')

        del self.list

        directory.add(items_list, infotype='Music')

    def bookmarks(self):

        self.list = bookmarks.get()

        if not self.list:
            na = [{'title': control.lang(30007), 'action': None}]
            directory.add(na)
            return

        for i in self.list:

            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['delbookmark'] = i['url']
            i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

        self.list = sorted(self.list, key=lambda k: k['title'].lower())

        directory.add(self.list, infotype='Music')

    def radios(self, url, return_listing=False):

        self.list = self.radios_list(url)

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False'})

        if url == self.all_link:

            self.list.extend(self._devpicks())

        for i in self.list:

            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        control.sortmethods('title')

        if return_listing:
            return self.list
        else:
            directory.add(self.list, infotype='Music')

    @cache_method(360)
    def _devpicks(self):

        xml = client.request('http://alivegr.net/raw/radios.xml')

        items = client.parseDOM(xml, 'station', attrs={'enable': '1'})

        for item in items:

            name = unicode(client.parseDOM(item, 'name')[0])
            logo = client.parseDOM(item, 'logo')[0]
            url = client.parseDOM(item, 'url')[0]

            self.data.append({'title': name, 'image': logo, 'url': url, 'action': 'dev_play', 'isFolder': 'False'})

        return self.data

    def dev_picks(self):

        self.list = self._devpicks()

        if self.list is None:
            return

        for i in self.list:
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        directory.add(self.list, infotype='Music')

    def play(self, url, do_not_resolve=False):

        if not do_not_resolve:

            resolved = self.resolve(url)

            if resolved is None:
                return

            title, url, image = resolved

            directory.resolve(url, {'title': title}, image)

        else:

            directory.resolve(url)

    @cache_method(1440)
    def directory_list(self, url):

        self.list = []

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
                url = self.category_link.format(str(item['categoryID']))
            elif 'regionID' in item:
                url = self.region_link.format(str(item['regionID']))
            url = client.replaceHTMLCodes(url)

            self.list.append({'title': title, 'url': url})

        return self.list

    @cache_method(60)
    def radios_list(self, url):

        result = client.request(url, mobile=True)
        result = json.loads(result)

        items = result['media']

        for item in items:

            try:

                title = item['name'].strip()
                title = client.replaceHTMLCodes(title)

                url = str(item['stationID'])
                url = client.replaceHTMLCodes(url)

                image = item['logo']
                image = self.image_link.format(image)
                image = image.replace('/promo/', '/500/')

                if image.endswith('/nologo.png'):
                    image = '0'

                image = client.replaceHTMLCodes(image)

                self.list.append({'title': title, 'url': url, 'image': image})

            except:

                pass

        return self.list

    def resolve(self, url):

        url = self.resolve_link.format(url)

        result = client.request(url, mobile=True)
        result = json.loads(result)

        item = result['media'][0]

        url = item['mediaUrl'][0]['liveURL']

        if not url.startswith('http://'):
            url = '{0}{1}'.format('http://', url)

        url = client.replaceHTMLCodes(url)

        # url = client.request(url, output='geturl')

        title = item['name'].strip()
        title = client.replaceHTMLCodes(title)

        image = item['logo']
        image = self.image_link.format(image)
        image = image.replace('/promo/', '/500/')

        if image.endswith('/nologo.png'):
            image = '0'

        image = client.replaceHTMLCodes(image)

        return title, url, image
