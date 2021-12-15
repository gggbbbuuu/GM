# -*- coding: utf-8 -*-

'''
    Skai Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json, re
from base64 import b64decode
from tulip import bookmarks, directory, client, cache, control, youtube
from tulip.parsers import itertags
from tulip.compat import zip, iteritems
from youtube_resolver import resolve as yt_resolver

cache_method = cache.FunctionCache().cache_method


class Indexer:

    def __init__(self):

        self.list = []; self.data = []
        self.base_link = 'https://www.skaitv.gr'
        self.old_base = 'https://www.skai.gr'
        self.radio_base = 'http://www.skairadio.gr'
        self.yt_channel = 'UCmHgxU394HiIAsN1fMegqzw'
        self.yt_key = b64decode('VhXbK1mdndFejF1dJJWMnNmc4IlbEl3a2d1QxgHZOdjQ5NVY6lUQ'[::-1])
        self.tvshows_link = ''.join([self.base_link, '/shows/seires'])
        self.entertainment_link = ''.join([self.base_link, '/shows/psuchagogia'])
        self.news_link = ''.join([self.base_link, '/shows/enimerosi'])
        self.live_link = ''.join([self.base_link, '/live'])
        self.podcasts_link = ''.join([self.radio_base, '/shows?page=0'])
        self.play_link = 'https://videostream.skai.gr/skaivod/_definst_/mp4:skai/'
        self.radio_link = 'https://skai.live24.gr/skai1003'

    def root(self, audio_only=False):

        self.list = [
            {
                'label': control.lang(30001),
                'title': 'Skai Live TV',
                'action': 'play',
                'isFolder': 'False',
                'icon': 'live.png',
                'url': self.live_link
            }
            ,
            {
                'label': control.lang(30014),
                'title': 'Skai Radio 100.3FM',
                'action': 'play',
                'url': self.radio_link,
                'isFolder': 'False',
                'icon': 'live.png'
            }
            ,
            {
                'title': control.lang(30006),
                'action': 'news',
                'icon': 'news.png'
            }
            ,
            {
                'title': control.lang(30002),
                'action': 'shows',
                'icon': 'tvshows.png',
                'url': self.tvshows_link
            }
            ,
            {
                'title': control.lang(30015),
                'action': 'shows',
                'icon': 'entertainment.png',
                'url': self.entertainment_link
            }
            ,
            {
                'title': control.lang(30003),
                'action': 'podcasts',
                'icon': 'podcasts.png'
            }
            ,
            {
                'title': control.lang(30004),
                'action': 'archive',
                'icon': 'archive.png'
            }
            ,
            {
                'title': control.lang(30005),
                'action': 'latest',
                'icon': 'latest.png'
            }
            ,
            {
                'title': control.lang(30008),
                'action': 'bookmarks',
                'icon': 'bookmarks.png'
            }
        ]

        if audio_only:

            self.list = [self.list[1]] + [self.list[3]]

        for item in self.list:

            cache_clear = {'title': 30009, 'query': {'action': 'cache_clear'}}
            item.update({'cm': [cache_clear]})

        directory.add(self.list, content='videos')

    def bookmarks(self):

        self.list = bookmarks.get()

        if not self.list:
            na = [{'title': control.lang(30018), 'action': None}]
            directory.add(na)
            return

        for i in self.list:
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['delbookmark'] = i['url']
            i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

        self.list = sorted(self.list, key=lambda k: k['title'].lower())

        directory.add(self.list, content='videos')

    @cache_method(172800)
    def yt_playlists(self):

        return youtube.youtube(key=self.yt_key).playlists(self.yt_channel)

    @cache_method(3600)
    def yt_videos(self):

        return youtube.youtube(key=self.yt_key).videos(self.yt_channel, limit=2)

    @cache_method(3600)
    def yt_playlist(self, url):

        return youtube.youtube(key=self.yt_key).playlist(url)

    def archive(self):

        self.list = self.yt_playlists()

        if self.list is None:
            return

        for i in self.list:
            i['title'] = client.replaceHTMLCodes(i['title'])
            i.update({'action': 'episodes'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        control.sortmethods('title')

        directory.add(self.list, content='videos')

    def shows(self, url):

        self.list = self.generic_listing(url)

        if self.list is None:
            return

        for i in self.list:

            i.update({'action': 'episodes'})

            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']

            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        directory.add(self.list, content='videos')

    @cache_method(3600)
    def pod_listing(self, url):

        html = client.request(url)

        listing = client.parseDOM(html, 'div', attrs={'class': 'row border-bottom pt-4 m-0 show-item'})

        nexturl = re.sub(r'\d(?!\d)', lambda x: str(int(x.group(0)) + 1), url)

        for item in listing:

            title = client.parseDOM(item, 'h3')[0].replace('&#039;', '\'')
            if title.startswith('<span'):
                title = client.parseDOM(item, 'a', {'class': 'font-weight-bold text-initial'})[0]
            image = ''.join([self.radio_base, client.parseDOM(item, 'img', ret='src')[0]])
            url = ''.join([self.radio_base, client.parseDOM(item, 'a', ret='href')[0]])

            self.list.append(
                {
                    'title': title, 'image': image, 'url': url, 'nextaction': 'podcasts', 'next': nexturl,
                    'nextlabel': 30500
                }
            )

        return self.list

    def podcasts(self, url=None):

        if url is None:
            url = self.podcasts_link

        self.list = self.pod_listing(url)

        if self.list is None:
            return

        for i in self.list:

            i.update({'action': 'episodes'})

            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']

            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        directory.add(self.list, content='music')

    @cache_method(3600)
    def pod_episodes(self, url):

        html = client.request(url)

        select = client.parseDOM(html, 'div', attrs={'class': 'col-8 col-sm-4 p-0'})[0]
        image = re.search(r'background-image: url\("(.+?)"\)', html).group(1)

        pods = re.findall(r'(<option.+?option>)', select, re.S)

        for pod in pods:

            date = re.search(r'(\d{2}/\d{2}/\d{4})', pod).group(1)
            title = ' - '.join([client.parseDOM(html, 'h2', attrs={'class': 'mb-3.+?'})[0], date])
            url = ''.join([self.radio_base, re.search(r'data-url = "([\w\-/]+)"', pod).group(1)])

            self.list.append({'title': title, 'image': image, 'url': url})

        return self.list

    def episodes(self, url):

        if self.base_link in url:
            self.list = self.episodes_listing(url)
        elif self.radio_base in url:
            self.list = self.pod_episodes(url)
        else:
            self.list = self.yt_playlist(url)

        if self.list is None:

            return

        for i in self.list:

            i.update({'action': 'play', 'isFolder': 'False'})

        directory.add(self.list, content='videos')

    @cache_method(3600)
    def video_listing(self, url):

        html = client.request(url)

        try:
            nexturl = ''.join(
                [
                    self.old_base, '/videos',
                    client.parseDOM(html, 'a', attrs={'rel': 'next'}, ret='href')[0].replace('&amp;', '&')
                ]
            )
        except IndexError:
            nexturl = None

        video_list = client.parseDOM(html, 'div', attrs={'class': 'videoItem cell'}, ret='data-video-url')
        thumbnails = client.parseDOM(html, 'div', attrs={'class': 'videoItem cell'}, ret='data-video-poster')
        titles = client.parseDOM(html, 'div', attrs={'class': 'videoItem cell'}, ret='data-video-name')
        dates = client.parseDOM(html, 'div', attrs={'class': 'videoItem cell'}, ret='data-video-date')

        listing = list(zip(titles, dates, thumbnails, video_list))

        for title, date, image, video in listing:

            title = client.replaceHTMLCodes(title)

            label = ''.join([title, ' ', '(', date, ')'])

            self.list.append(
                {
                    'title': label, 'image': image, 'url': video, 'next': nexturl, 'nextlabel': 30500,
                    'nextaction': 'videos'
                }
            )

        return self.list

    def videos(self, url):

        self.list = self.video_listing(url)

        if self.list is None:
            return

        for i in self.list:

            i.update({'action': 'play', 'isFolder': 'False'})

        directory.add(self.list)

    def latest(self):

        self.list = self.yt_videos()

        if self.list is None:
            return

        self.list = [i for i in self.list if int(i['duration']) > 60]

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False'})

        directory.add(self.list)

    def news(self):

        self.list = [
            {
                'title': 30011,
                'action': 'episodes',
                'icon': 'news.png',
                'url': ''.join([self.base_link, '/show/enimerosi/oi-eidiseis-tou-ska-stis-2/sezon-2021-2022'])
            }
            ,
            {
                'title': 30012,
                'action': 'episodes',
                'icon': 'news.png',
                'url': ''.join([self.base_link, '/show/enimerosi/ta-nea-tou-ska-stis-2000/sezon-2021-2022'])
            }
            ,
            {
                'title': 30005,
                'action': 'videos',
                'icon': 'latest.png',
                'url': ''.join([self.old_base, '/videos?type=recent'])
            }
            ,
            {
                'title': 30016,
                'action': 'videos',
                'icon': 'popular.png',
                'url': ''.join([self.old_base, '/videos?type=popular'])
            }
            ,
            {
                'title': 30017,
                'action': 'videos',
                'icon': 'recommended.png',
                'url': ''.join([self.old_base, '/videos?type=featured'])
            }
        ]

        directory.add(self.list, content='videos')

    def play(self, url):

        resolved = self.resolve(url)

        if 'youtu' in resolved:
            resolved = self.yt_session(resolved)

        if isinstance(resolved, tuple):

            stream, plot = resolved
            meta = {'plot': plot}

        else:

            stream = resolved
            meta = None

        icon = None

        if url == self.live_link:

            icon = {'poster': control.icon(), 'icon': control.icon(), 'thumb': control.icon()}

        dash = ('dash' in stream or '.mpd' in stream or 'm3u8' in stream) and control.kodi_version() >= 18.0

        directory.resolve(
            url=stream, meta=meta, dash=dash, icon=icon,
            mimetype='application/vnd.apple.mpegurl' if 'm3u8' in stream else None,
            manifest_type='hls' if '.m3u8' in stream else None
        )

    @cache_method(1440)
    def generic_listing(self, url):

        html = client.request(url)

        if url == self.news_link:
            new = 'row m-0 listrow new-videos'
            new_items = 'col-12 pl-0 pr-0 list1 list-item color_enimerosi'
            archive = 'row m-0 listrow s234 '
            archived_items = 'col-12 pl-0 pr-0 list1 list-item color_enimerosi'
        elif url == self.entertainment_link:
            new = 'row  listrow list2 '
            new_items = 'd-none d-md-block col-md-4 listimg color_psuchagogia'
            archive = 'row  listrow list2 s234  '
            archived_items = 'd-none d-md-block col-md-3 listimg color_psuchagogia'
        else:
            new = 'row  listrow list2 '
            new_items = 'd-none d-md-block col-md-4 listimg color_seires'
            archive = 'row  listrow list2 s234  '
            archived_items = 'd-none d-md-block col-md-3 listimg color_seires'

        div = client.parseDOM(html, 'div', attrs={'class': new})[0]

        listing = client.parseDOM(div, 'div', attrs={'class': new_items})

        for item in listing:

            title = client.parseDOM(item, 'h3')[0]
            image = client.parseDOM(item, 'img', ret='src')[0]

            url = ''.join([self.base_link, client.parseDOM(item, 'a', ret='href')[0]])

            self.list.append({'title': title, 'url': url, 'image': image})

        if 's234' in html:

            div = client.parseDOM(html, 'div', attrs={'class': archive})[0]
            items = client.parseDOM(div, 'div', attrs={'class': archived_items})

            for item in items:

                title = ' - '.join([client.parseDOM(item, 'h3')[0], control.lang(30013)])
                image = client.parseDOM(item, 'img', ret='src')[0]

                url = ''.join([self.base_link, client.parseDOM(item, 'a', ret='href')[0]])

                self.list.append({'title': title, 'url': url, 'image': image})

        return self.list

    @cache_method(180)
    def episodes_listing(self, url):

        html = client.request(url)

        div = client.parseDOM(html, 'div', attrs={'class': 'row  listrow list2 ?'})[0]

        listing = [i.text for i in itertags(div, 'div')]

        for item in listing:

            try:
                title = client.parseDOM(item, 'h3')[0].replace('<br/>', ' ').replace('<br>', ' ')
            except Exception:
                continue
            image = client.parseDOM(item, 'img', ret='src')[0]

            url = ''.join([self.base_link, client.parseDOM(item, 'a', ret='href')[0]])

            self.list.append({'title': title, 'url': url, 'image': image})

        return self.list

    @cache_method(720)
    def episode_resolver(self, url):

        html = client.request(url)

        if url.startswith(self.radio_base):

            url = re.search(r'["\'](.+?\.mp3)["\']', html).group(1)

            return url

        else:

            json_ = re.search(r'var data = ({.+})', html).group(1)

            json_ = json.loads(json_)

            url = ''.join([self.play_link, json_['episode'][0]['media_item_file'], '/chunklist.m3u8'])

            plot = client.stripTags(json_['episode'][0]['descr'])

            return url, plot

    def resolve(self, url):

        if url == self.live_link:

            html = client.request(self.live_link)

            json_ = re.search(r'var data = ({.+?});', html).group(1)

            json_ = json.loads(json_)

            return json_['now']['livestream']

        elif len(url) == 11:

            link = self.yt_session(url)

            return link

        elif 'episode' in url:

            return self.episode_resolver(url)

        else:

            return url

    @staticmethod
    def yt_session(link):

        streams = yt_resolver(link)

        try:
            addon_enabled = control.addon_details('inputstream.adaptive').get('enabled')
        except KeyError:
            addon_enabled = False

        if not addon_enabled:

            streams = [s for s in streams if 'mpd' not in s['title']]

        stream = streams[0]['url']

        return stream
