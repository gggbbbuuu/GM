# -*- coding: utf-8 -*-

'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import json, re

from base64 import b64decode
from youtube_resolver import resolve as yt_resolver
from tulip import bookmarks, directory, client, cache, youtube, control
from tulip.parsers import itertags_wrapper, parseDOM
from tulip.cleantitle import replaceHTMLCodes
from tulip.compat import urlparse, iteritems, OrderedDict

cache_method = cache.FunctionCache().cache_method


class Indexer:

    def __init__(self):

        self.list = []; self.data = []; self.groups = []
        self.stargr_link = 'https://www.star.gr'
        self.starx_link = 'https://www.starx.gr'
        self.startv_link = ''.join([self.stargr_link, '/tv/'])
        self.star_video_link = ''.join([self.stargr_link, '/video'])
        self.starx_latest_link = ''.join([self.starx_link, '/latest'])
        self.starx_viral_link = ''.join([self.starx_link, '/viral'])
        self.starx_popular_link = ''.join([self.starx_link, '/popular'])
        self.starx_shows_link = ''.join([self.starx_link, '/shows'])
        self.ajax_player = ''.join([self.startv_link, 'ajax/Atcom.Sites.StarTV.Components.Show.PopupSliderItems'])
        self.player_query = '&'.join(
            [
                'showid={show_id}', 'type=Episode', 'itemIndex={item_index}', 'seasonid={season_id}', 'single=false'
            ]
        )
        self.m3u8_link = (
            'https://cdnapisec.kaltura.com/p/713821/sp/0/playManifest/entryId/{0}/format/applehttp/protocol/https/'
            'flavorParamId/0/manifest.m3u8'
        )
        self.live_link = ''.join([self.startv_link, 'live-stream/'])
        self.youtube_key = b64decode('zNHTHh1STN3SzVERB9kUmFWVmlkUFJ1UwYHZZJkUh5kQ5NVY6lUQ'[::-1])
        self.youtube_link = 'UCwUNbp_4Y2Ry-asyerw2jew'

    def root(self):

        self.list = [
            {
                'label': control.lang(30009),
                'title': 'Star TV Live',
                'action': 'play',
                'isFolder': 'False',
                'url': self.live_link,
                'icon': 'live.png'
            }
            ,
            {
                'title': control.lang(30003),
                'action': 'startv',
                'icon': 'tvshows.png'
            }
            ,
            {
                'title': control.lang(30007),
                'action': 'videos',
                'icon': 'videos.png'
            }
            ,
            {
                'title': control.lang(30008),
                'action': 'starx',
                'icon': 'starx.png'
            }
            ,
            {
                'title': control.lang(30010),
                'action': 'news',
                'icon': 'news.png'
            }
            ,
            {
                'title': control.lang(30002),
                'action': 'archive',
                'icon': 'archive.png'
            }
            ,
            {
                'title': control.lang(30006),
                'action': 'bookmarks',
                'icon': 'bookmarks.png'
            }
        ]

        for item in self.list:
            cache_clear = {'title': 30403, 'query': {'action': 'cache_clear'}}
            item.update({'cm': [cache_clear]})

        directory.add(self.list)

    def bookmarks(self):

        self.list = bookmarks.get()

        if self.list is None:
            self.list = [{'title': 'N/A', 'action': None}]
            directory.add(self.list)
            return

        for i in self.list:
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['delbookmark'] = i['url']
            i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

        self.list = sorted(self.list, key=lambda k: k['title'].lower())

        directory.add(self.list)

    @cache_method(1440)
    def yt_playlists(self):

        return youtube.youtube(key=self.youtube_key).playlists(self.youtube_link)

    @cache_method(60)
    def yt_playlist(self, url):

        return youtube.youtube(key=self.youtube_key).playlist(url)

    def archive(self):

        self.list = self.yt_playlists()

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'youtube'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        control.sortmethods('title')

        directory.add(self.list)

    def youtube(self, url):
    
        self.list = self.yt_playlist(url)

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False'})

        directory.add(self.list)

    @cache_method(720)
    def index(self):

        html = client.request(self.startv_link)

        divs = parseDOM(html, 'div', {'class': 'wrapper'})[3:6]

        htmls = '\n'.join(divs)

        items = parseDOM(htmls, 'div', attrs={'class': 'tile'})

        for item in items:

            title = parseDOM(item, 'b')[0]
            title = replaceHTMLCodes(title)
            url = parseDOM(item, 'a', attrs={'class': 'tile_title'}, ret='href')[0]
            try:
                image = parseDOM(item, 'div', attrs={'data-tile-img': 'background-image:.+'}, ret='style')[0]
            except IndexError:
                image = parseDOM(item, 'div', attrs={'data-tile-img': 'background-image:.+'}, ret='data-grid-img')[0]
            image = re.search(r'(http.+?\.jpg)', image).group(1)
            group = urlparse(url).path.split('/')[2]

            self.list.append({'title': title, 'image': image, 'url': url, 'group': group})

        return self.list

    def loop(self, i, group):

        try:

            title = parseDOM(i, 'a', ret='data-title')[0]
            title = replaceHTMLCodes(title)

        except Exception:
            return

        try:
            image = parseDOM(i, 'img', ret='src')[0]
        except IndexError:
            image = parseDOM(i, 'img', ret='data-src')[0]

        image = client.quote_paths(image)

        url = itertags_wrapper(i, 'a', ret='href')[0]

        data = {'title': title, 'image': image, 'url': url, 'group': group}

        return data

    @cache_method(60)
    def listing(self, url):

        html = client.request(url)

        content = parseDOM(html, 'div', attrs={'class': 'seasons'})[0]

        groups_content = parseDOM(content, 'div', {'class': 'row'})

        for group_content in groups_content:

            group = replaceHTMLCodes(parseDOM(group_content, 'h3')[0].splitlines()[0])
            items = parseDOM(group_content, 'li', attrs={'class': 'horizontal-cell.+?'})

            self.groups.append(group)

            for i in items:

                item = self.loop(i, group)
                if item is None:
                    continue
                self.list.append(item)

        return self.list, self.groups

    def show(self, url):

        try:
            self.list, self.groups = self.listing(url)
        except TypeError:
            return

        try:
            self.list = [i for i in self.list if i['group'] == self.groups[int(control.setting('group'))]]
        except IndexError:
            control.setSetting('group', '0')

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False'})

        try:
            title = u''.join([control.lang(30005), u': {0}'.format(self.groups[int(control.setting('group'))])])
        except IndexError:
            try:
                title = u''.join([control.lang(30005), u': {0}'.format(self.groups[0])])
            except Exception:
                return

        selector = {
            'title': title,
            'action': 'selector',
            'icon': 'selector.png',
            'isFolder': 'False',
            'isPlayable': 'False',
            'query': json.dumps(self.groups)
        }

        self.list.insert(0, selector)

        directory.add(self.list)

    def startv(self):

        self.list = self.index()

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'show'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        option = control.setting('option')

        selector = {
            'title': u''.join([control.lang(30005), u': {0}'.format(control.lang(self.vod_groups()[option]))]),
            'action': 'selector',
            'icon': 'selector.png',
            'isFolder': 'False',
            'isPlayable': 'False'
        }

        self.list = [i for i in self.list if i['group'] == option]

        self.list.insert(0, selector)

        directory.add(self.list)

    @cache_method(720)
    def _videos(self):

        html = client.request(self.star_video_link)

        items = parseDOM(html, 'div', attrs={'class': 'video__title'})

        for i in items:

            title = parseDOM(i, 'a', attrs={'style': 'color.+?'})[0]
            url = parseDOM(i, 'a', attrs={'style': 'color.+?'}, ret='href')[0]

            self.list.append({'title': title, 'url': url})

        return self.list

    def videos(self):

        self.list = self._videos()

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'category'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        directory.add(self.list)

    @cache_method(60)
    def _category(self, url):

        html = client.request(url)

        content = parseDOM(html, 'div', attrs={'class': 'block block--no-space'})[0]

        items = parseDOM(content, 'div', attrs={'style': 'margin-bottom:20px;'})

        try:
            next_url = parseDOM(html, 'a', {'rel': 'next'}, ret='href')[0]
        except Exception:
            next_url = ''

        for i in items:

            title = parseDOM(i, 'div', attrs={'class': 'title'})[0].strip()
            title = replaceHTMLCodes(title)
            url = parseDOM(i, 'a', ret='href')[0]
            if not url.startswith('http'):
                url = ''.join([self.stargr_link, url])
            image = parseDOM(i, 'img', attrs={'class': 'video-tumbnail'}, ret='src')[0]

            self.list.append({'title': title, 'image': image, 'url': url, 'next': next_url})

        return self.list

    def category(self, url):

        self.list = self._category(url)

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False', 'nextlabel': 30500, 'nextaction': 'category'})

        directory.add(self.list)

    def starx(self):

        self.list = [
            {
                'title': u''.join([control.lang(30008), ': ', control.lang(30004)]),
                'url': self.starx_latest_link,
                'icon': 'starx.png',
                'action': 'starx_videos'
            }
            ,
            {
                'title': u''.join([control.lang(30008), ': ', control.lang(30013)]),
                'url': self.starx_viral_link,
                'icon': 'starx.png',
                'action': 'starx_videos'
            }
            ,
            {
                'title': u''.join([control.lang(30008), ': ', control.lang(30014)]),
                'url': self.starx_popular_link,
                'icon': 'starx.png',
                'action': 'starx_videos'
            }
            ,
            {
                'title': u''.join([control.lang(30008), ': ', control.lang(30012)]),
                'icon': 'starx.png',
                'action': 'starx_shows'
            }
        ]

        directory.add(self.list)

    def news(self):

        self.list = [
            {
                'title': 30018,
                'action': 'show',
                'icon': 'news.png',
                'url': 'https://www.star.gr/tv/enimerosi/mesimeriano-deltio-eidiseon/'
            }
            ,
            {
                'title': 30019,
                'action': 'show',
                'icon': 'news.png',
                'url': 'https://www.star.gr/tv/enimerosi/kedriko-deltio-eidiseon/'
            }
            ,
            {
                'title': 30022,
                'action': 'show',
                'icon': 'news.png',
                'url': 'https://www.star.gr/tv/enimerosi/kentriko-deltio-eidiseon-sabbatokuriakou/'
            }
            ,
            {
                'title': 30020,
                'action': 'show',
                'icon': 'sign.png',
                'url': 'https://www.star.gr/tv/enimerosi/apogeumatino-deltio-eidiseon/'
            }
            ,
            {
                'title': 30021,
                'action': 'show',
                'icon': 'weather.png',
                'url': 'https://www.star.gr/tv/enimerosi/star-kairos/'
            }
        ]

        directory.add(self.list)

    @cache_method(60)
    def _starx_videos(self, url, title):

        try:
            title = title.decode('utf-8')
        except Exception:
            pass

        html = client.request(url)

        if 'javascript:void(0)' in html and 'rel="more"' in html:

            items = json.loads(re.search('var episodes = (.+?);', html).group(1))

            episodes = list(range(1, len(items) + 1))[::-1]

            for i, e in zip(items, episodes):

                try:
                    label = u''.join([title, ' - ', control.lang(30016), str(e), '[CR][I]', i['title'], '[/I]'])
                except Exception:
                    label = u''.join([title, ' - ', control.lang(30016), str(e)])
                image = self.thumb_maker(i['video_id'])
                url = i['video_id']

                data = {'title': label, 'url': url, 'image': image}

                if i['kaltura_id']:
                    data.update({'query': i['kaltura_id']})

                self.list.append(data)

        else:

            items = parseDOM(html, 'div', attrs={'class': 'video-.+?'})

            try:
                next_url = parseDOM(html, 'a', attrs={'rel': 'next'}, ret='href')[0]
            except Exception:
                next_url = ''

            for i in items:

                title = parseDOM(i, 'span', attrs={'class': 'name'})[0]
                title = replaceHTMLCodes(title)
                try:
                    url = html.partition(i.encode('utf-8'))[0]
                except TypeError:
                    url = html.partition(i)[0]
                url = parseDOM(url, 'a', ret='href')[-1]
                image = parseDOM(i, 'img', attrs={'class': 'lozad'}, ret='src')[0]
                if image == 'https://www.starx.gr/images/1x1.png':
                    image = parseDOM(i, 'img', attrs={'class': 'lozad'}, ret='data-src')[0]

                self.list.append({'title': title, 'url': url, 'image': image, 'next': next_url})

        return self.list

    def starx_videos(self, url, title):

        self.list = self._starx_videos(url, title)

        if self.list is None:
            return

        for i in self.list:

            i.update({'action': 'play', 'isFolder': 'False'})

            if 'next' in i:
                i.update({'nextlabel': 30500, 'nextaction': 'starx_videos'})

        directory.add(self.list)

    @cache_method(720)
    def _starx_shows(self):

        html = client.request(self.starx_shows_link)

        items = parseDOM(html, 'div', attrs={'class': 'video-.+?'})

        for i in items:

            title = parseDOM(i, 'span', attrs={'class': 'name'})[0]
            url = html.partition(i.encode('utf-8'))[0]
            url = parseDOM(url, 'a', ret='href')[-1]
            image = parseDOM(i, 'img', ret='data-src')[0]

            self.list.append({'title': title, 'url': url, 'image': image})

        return self.list

    def starx_shows(self):

        self.list = self._starx_shows()

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'starx_videos'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        directory.add(self.list)

    def play(self, url, query=None):

        if url == self.live_link:

            icon = {'poster': control.icon()}
            meta = {'plot': ' '.join([control.lang(30023), self.video_resolver(url)[1]])}

        else:

            meta = None
            icon = None

        if len(url) == 11:

            try:
                stream = self.yt_session(url)
                directory.resolve(stream, dash=stream.endswith('.mpd'))
                return
            except Exception:
                return self.play(query)

        elif len(url) == 10:

            url = self.m3u8_link.format(url)

        elif url.startswith('plugin://'):

            return self.play(url[-11:])

        elif 'Atcom.Sites' in url or '/video/' in url:

            html = client.request(url)

            try:

                url = re.search(r'url: ["\'](.+?)["\']', html).group(1)

            except AttributeError:

                if 'kaltura-player' in html:

                    url = self.m3u8_link.format(re.search(r'kaltura-player(\w+)', html).group(1))

                elif 'iframe' in html and 'youtube' in html:

                    url = parseDOM(html, 'iframe', ret='src')[0]
                    stream = self.yt_session(url)
                    directory.resolve(stream, dash=stream.endswith('.mpd'))
                    return

                else:

                    url = 'https://static.adman.gr/inpage/blank.mp4'

        elif '/episode/' in url:

            html = client.request(url)

            url = self.m3u8_link.format(re.search(r'kalturaPlayer\(["\'](\w+)["\']', html).group(1))

        elif '/tv/' in url:

            html = client.request(url)

            if 'onYouTubeIframeAPIReady' in html:
                stream = re.search(r'''videoId: ["'](\w{11})["']''', html).group(1)
                stream = self.yt_session(stream)
                directory.resolve(stream, dash=stream.endswith('.mpd'))
                return
            else:
                if url == self.live_link:
                    url = self.video_resolver(url)[0]
                else:
                    url = self.video_resolver(url)

        elif '/viral/' in url or '/popular/' in url:

            html = client.request(url)

            yt_id = re.search(r'onYouTubeIframeAPIReady\(["\']([\w-]{11})["\']\);', html).group(1)

            return self.play(yt_id)

        try:

            addon_enabled = control.addon_details('inputstream.adaptive').get('enabled')

        except KeyError:

            addon_enabled = False

        version = int(control.infoLabel('System.AddonVersion({0})'.format('xbmc.python')).replace('.', ''))

        dash = addon_enabled and version >= 2260

        if dash:

            directory.resolve(
                url, meta=meta, icon=icon, dash=True, manifest_type='hls', mimetype='application/vnd.apple.mpegurl'
            )

        else:

            directory.resolve(url, meta=meta, icon=icon)

    @cache_method(15)
    def video_resolver(self, url):

        html = client.request(url)

        stream = re.search(r"(?P<url>http.+?\.m3u8)", html).group('url')

        if url == self.live_link:

            desc = client.parseDOM(html, 'div', {'class': 'desc'})[0]
            plot = client.parseDOM(desc, 'h3')[0]

            return stream, plot

        else:

            return stream

    @staticmethod
    def thumb_maker(video_id):

        return 'http://img.youtube.com/vi/{0}/{1}.jpg'.format(video_id, 'mqdefault')

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
    def vod_groups():

        return OrderedDict(
            [
                ('enimerosi', 30010), ('psychagogia', 30011), ('seires', 30012)
            ]
        )

    def selector(self, query=None):

        if query:

            query = json.loads(query)

            choice = control.selectDialog(query, control.lang(30017))

            if choice != -1:
                control.setSetting('group', str(choice))

        else:

            choices = [control.lang(i) for i in list(self.vod_groups().values())]

            groups = list(self.vod_groups().keys())

            choice = control.selectDialog(choices, control.lang(30003))

            option = groups[choice]

            if choice != -1:
                control.setSetting('option', option)

        if choice != -1:
            control.sleep(200)
            control.refresh()
