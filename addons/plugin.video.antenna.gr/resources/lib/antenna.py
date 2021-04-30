# -*- coding: utf-8 -*-

'''
    Ant1 Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json, re
from base64 import b64decode
from youtube_resolver import resolve as yt_resolver
from tulip import bookmarks, directory, client, cache, control, youtube, utils
from tulip.compat import range, iteritems, concurrent_futures

method_cache = cache.FunctionCache().cache_method


class Indexer:

    def __init__(self):

        self.list = [] ; self.data = []
        self.base_link = 'https://www.antenna.gr'
        self.shows_link = ''.join([self.base_link, '/shows/ALL'])
        self.archive_link = ''.join([self.base_link, '/directory/ALL'])
        self.news_link = ''.join([self.base_link, '/ant1news/videos'])
        self.weather_link = ''.join([self.base_link, '/webtv/3091/kairos?showall'])
        self.sports_link = ''.join([self.base_link, '/webtv/3062/athlitika?showall'])
        self.latest_link = ''.join([self.base_link, '/webtv/'])
        self.more_videos = ''.join([self.base_link, '/templates/data/morevideos?aid='])
        self.more_web_videos = ''.join([self.base_link, '/templates/data/WEBTVvideosPerVideoCategory?cid='])
        self.player_link = ''.join([self.base_link, '/templates/data/player?cid={0}'])
        self.live_link = 'https://antennalivesp-lh.akamaihd.net/i/live_1@715138/master.m3u8'
        self.yt_id = 'UC0smvAbfczoN75dP0Hw4Pzw'
        self.yt_key = b64decode('VpGUslWWNVzZtgmd4kDWx8UWmFFSvV1T6p0cWNESkhGR5NVY6lUQ'[::-1])

    def root(self):

        self.list = [
            {
                'title': control.lang(30001),
                'action': 'play',
                'isFolder': 'False',
                'icon': 'live.png',
                'url': self.live_link
            }
            ,
            {
                'title': control.lang(30002),
                'action': 'listing',
                'icon': 'shows.png',
                'url': self.shows_link
            }
            ,
            {
                'title': control.lang(30003),
                'action': 'listing',
                'icon': 'archive.png',
                'url': self.archive_link
            }
            ,
            {
                'title': control.lang(30006),
                'action': 'videos',
                'icon': 'news.png',
                'url': self.news_link
            }
            ,
            {
                'title': control.lang(30007),
                'action': 'videos',
                'icon': 'weather.png',
                'url': self.weather_link
            }
            ,
            {
                'title': control.lang(30010),
                'action': 'videos',
                'icon': 'sports.png',
                'url': self.sports_link
            }
            ,
            {
                'title': control.lang(30004),
                'action': 'videos',
                'icon': 'popular.png',
                'url': self.latest_link
            }
            ,
            {
                'title': control.lang(30016),
                'action': 'webtv',
                'icon': 'webtv.png'
            }
            ,
            {
                'title': control.lang(30005),
                'action': 'youtube_channel',
                'icon': 'youtube.png'
            }
            ,
            {
                'title': control.lang(30008),
                'action': 'bookmarks',
                'icon': 'bookmarks.png'
            }
        ]

        for item in self.list:

            cache_clear = {'title': 30011, 'query': {'action': 'cache_clear'}}
            item.update({'cm': [cache_clear]})

        directory.add(self.list, content='videos')

    def bookmarks(self):

        self.list = bookmarks.get()

        if self.list is None:
            return

        for i in self.list:

            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['delbookmark'] = i['url']
            i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

        self.list = sorted(self.list, key=lambda k: k['title'].lower())

        directory.add(self.list, content='videos')

    def youtube_channel(self):

        self.list = [
            {
                'title': 30013,
                'action': 'videos',
                'icon': 'youtube.png',
                'url': self.yt_id

            }
            ,
            {
                'title': 30012,
                'action': 'playlists',
                'icon': 'youtube.png'
            }
        ]

        directory.add(self.list)

    def playlists(self):

        self.list = self.yt_playlists()

        if self.list is None:
            return

        for i in self.list:

            i.update({'action': 'videos'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        directory.add(self.list, content='videos')

    @method_cache(1440)
    def items_list(self, url):

        html = client.request(url)

        items = client.parseDOM(html, 'article', attrs={'class': 'item overlay grid__col-xs-6 grid__col-lg-4'})

        for item in items:

            title = client.parseDOM(item, 'h2')[0]
            image = client.parseDOM(item, 'img', ret='src')[0]
            url = client.parseDOM(item, 'a', attrs={'rel': 'bookmark'}, ret='href')[0]
            url = ''.join([self.base_link, url, '/videos'])
            plot = client.parseDOM(item, 'p', attrs={'class': 'excerpt visible__md'})[0]

            self.list.append({'title': title, 'image': image, 'url': url, 'plot': plot})

        return self.list

    def listing(self, url):

        self.list = self.items_list(url)

        if self.list is None:
            return

        for i in self.list:

            i.update({'action': 'videos'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        directory.add(self.list, content='videos')

    @method_cache(1440)
    def video_list(self, url):

        html = client.request(url)

        if 'webtv' in url:
            attribute = 'library-add-container.+?'
        else:
            attribute = 'item overlay grid__.+?'

        tag = 'article'

        items = client.parseDOM(html, tag, attrs={'class': attribute})

        if "contentContainer_totalpages" in html or ('totalpages' in html and 'webtv' in url and not 'showall' in url):

            totalPages = int(re.search(r'totalpages = (\d+);', html).group(1))

            if 'webtv' in url:
                pattern = r'var cid = (\d+);'
            else:
                pattern = r'/templates/data/morevideos\?aid=(\d+)'

            seriesId = re.search(pattern, html).group(1)
            threads = []

            with concurrent_futures.ThreadPoolExecutor(10) as executor:

                for i in list(range(2, totalPages + 2)):
                    if 'webtv' in url:
                        thread_url = ''.join([self.more_web_videos, seriesId, "&p=", str(i), '&h=15'])
                    else:
                        thread_url = ''.join([self.more_videos, seriesId, "&p=", str(i)])
                    threads.append(executor.submit(self.thread, thread_url))
                for future in concurrent_futures.as_completed(threads):
                    item = future.result()
                    if not item:
                        continue
                    self.data.append(item)

            for i in self.data:
                items.extend(client.parseDOM(i, tag, attrs={'class': attribute}))

        for item in items:

            title = client.parseDOM(item, 'h2')[0]
            image = client.parseDOM(item, 'img', ret='src')[0]

            try:
                url = client.parseDOM(item, 'a', attrs={'rel': 'bookmark'}, ret='href')[0]
            except IndexError:
                url = client.parseDOM(item, 'a', attrs={'class': 'has-video'}, ret='href')[0]

            url = ''.join([self.base_link, url])

            try:
                plot = client.parseDOM(item, 'p', attrs={'class': 'excerpt visible__md.+?'})[0]
            except IndexError:
                plot = title

            self.list.append({'title': title, 'image': image, 'url': url, 'plot': plot})

        return self.list

    def videos(self, url):

        if url == self.yt_id:
            self.list = self.yt_videos(url)
        elif url.startswith('http'):
            self.list = self.video_list(url)
        else:
            self.list = self.yt_playlist()

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False'})

        control.sortmethods()
        control.sortmethods('title')

        if 'webtv' in url and not 'showall' in url and url != self.latest_link:

            more = {
                'title': control.lang(30015),
                'url': url + '?showall',
                'action': 'videos',
                'icon': 'next.png'
            }

            self.list.insert(-1, more)

        elif len(self.list) > int(control.setting('pagination_integer')) and control.setting('paginate') == 'true':

            try:

                pages = utils.list_divider(self.list, int(control.setting('pagination_integer')))
                self.list = pages[int(control.setting('page'))]
                reset = False

            except Exception:

                pages = utils.list_divider(self.list, int(control.setting('pagination_integer')))
                self.list = pages[0]
                reset = True

            self.list.insert(0, self.page_menu(len(pages), reset=reset))

        directory.add(self.list, content='videos')

    def webtv(self):

        self.list = [
            {
                'title': control.lang(30021), # top
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/4676/top-thema?showall'])
            }
            ,
            {
                'title': control.lang(30017), # politics
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/3049/politiki?showall'])
            }
            ,
            {
                'title': control.lang(30020), # society
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/3060/koinonia?showall'])
            }
            ,
            {
                'title': control.lang(30024), # world
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/3060/koinonia?showall'])
            }
            ,
            {
                'title': control.lang(30028), # newspapers
                'action': 'videos',
                'url': ''.join([self.base_link, 'webtv/4674/efimerides?showall'])
            }
            ,
            {
                'title': control.lang(30023), # strange
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/5274/paraxena?showall'])
            }
            ,
            {
                'title': control.lang(30025), # trailers
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/5104/ant1-trailers?showall'])
            }
            ,
            {
                'title': control.lang(30014), # life
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/5271/life?showall'])
            }
            ,
            {
                'title': control.lang(30026), # interviews
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/4348/synenteyxeis-kalesmenon?showall'])
            }
            ,
            {
                'title': control.lang(30030),  # guests
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/4963/kalesmenoi?showall'])
            }
            ,
            {
                'title': control.lang(30019), # fashion
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/4491/moda?showall'])
            }
            ,
            {
                'title': control.lang(30029), # beauty
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/5089/beauty?showall'])
            }
            ,
            {
                'title': control.lang(30022), # gossip
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/4492/gossip?showall'])
            }
            ,
            {
                'title': control.lang(30018), # recipes
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/4349/syntages?showall'])
            }
            ,
            {
                'title': control.lang(30027), # astrology
                'action': 'videos',
                'url': ''.join([self.base_link, '/webtv/4350/zodia?showall'])
            }
        ]

        directory.add(self.list)

    def play(self, url):

        meta = None

        stream = self.resolve(url)

        if stream == self.live_link:

            meta = {'title': 'Ant1 TV'}

        try:
            addon_enabled = control.addon_details('inputstream.adaptive').get('enabled')
        except KeyError:
            addon_enabled = False

        if int(
                control.infoLabel('System.AddonVersion("xbmc.python")').replace('.', '')
        ) >= 2260 and 'm3u8' in stream and addon_enabled:

            m3u8_dash = True

        else:

            m3u8_dash = False

        directory.resolve(
            stream, meta=meta, dash=stream.endswith('.mpd') or m3u8_dash,
            manifest_type='hls' if m3u8_dash else None, mimetype='application/vnd.apple.mpegurl' if m3u8_dash else None
        )

    def resolve(self, url):

        if url == self.live_link:

            return url

        elif 'youtube' in url or len(url) == 11:

            return self.yt_session(url)

        else:

            id = re.search(r'watch/(\d+)/', url).group(1)
            json_ = json.loads(client.request(self.player_link.format(id)))
            media_url = json_['url']

            return media_url

    @staticmethod
    def yt_session(yt_id):

        streams = yt_resolver(yt_id)

        try:
            addon_enabled = control.addon_details('inputstream.adaptive').get('enabled')
        except KeyError:
            addon_enabled = False

        if not addon_enabled:
            streams = [s for s in streams if 'mpd' not in s['title'].lower()]

        stream = streams[0]['url']

        return stream

    @staticmethod
    def page_menu(pages, reset=False):

        if not reset:
            index = str(int(control.setting('page')) + 1)
        else:
            index = '1'

        menu = {
            'title': control.lang(30033).format(index),
            'action': 'switch',
            'query': str(pages),
            'icon': 'selector.png',
            'isFolder': 'False',
            'isPlayable': 'False'
        }

        return menu

    @staticmethod
    def switch(query):

        pages = [control.lang(30034).format(i) for i in list(range(1, int(query) + 1))]

        choice = control.selectDialog(pages, heading=control.lang(30035))

        if choice != -1:
            control.setSetting('page', str(choice))
            control.sleep(200)
            control.refresh()

    def thread(self, url):

        result = client.request(url, timeout=10)
        return result

    @method_cache(60)
    def yt_playlist(self, url):

        return youtube.youtube(key=self.yt_key, replace_url=False).playlist(url)

    @method_cache(60)
    def yt_videos(self, url):

        return youtube.youtube(key=self.yt_key, replace_url=False).videos(url)

    @method_cache(360)
    def yt_playlists(self):

        return youtube.youtube(key=self.yt_key).playlists(self.yt_id)
