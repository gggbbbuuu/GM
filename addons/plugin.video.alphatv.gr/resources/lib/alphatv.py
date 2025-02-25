# -*- coding: utf-8 -*-

'''
    Alpha Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json, re, time
from base64 import b64decode
from datetime import datetime
from kodi_six.utils import py2_decode
from tulip.compat import urljoin, iteritems, parse_qs, parse_qsl, urlparse, range
from tulip import bookmarks, directory, client, cache, user_agents, control, youtube, workers, utils
from youtube_resolver import resolve as yt_resolver


cache_method = cache.FunctionCache().cache_method


class Indexer:

    def __init__(self):

        self.list = []; self.data = []

        self.basegr_link = 'https://www.alphatv.gr'
        self.basecy_link = 'https://www.alphacyprus.com.cy'

        self.xhr_show_list = ''.join([self.basegr_link, '/ajax/Isobar.AlphaTv.Components.Shows.Show.list'])
        self.seriesgr_link = '?'.join([self.xhr_show_list, 'Key=0&Page=1&PageSize=50&ShowType=1'])
        self.showsgr_link = '?'.join([self.xhr_show_list, 'Key=0&Page=1&PageSize=50&ShowType=0'])
        self.seriescy_link = ''.join([self.basecy_link, '/shows/ellinikes-seires?page=0'])
        self.showscy_link_1 = ''.join([self.basecy_link, '/shows/entertainment?page=0'])
        self.showscy_link_2 = ''.join([self.basecy_link, '/shows/informative?page=0'])

        self.views_ajax = ''.join([self.basecy_link, '/views/ajax?_wrapper_format=drupal_ajax'])

        # CY:
        self.ajax_post_index = '&'.join(
            [
                'view_name=alpha_shows_category_view', 'view_display_id=page_3', 'view_args=',
                'view_path=shows', 'view_base_path=shows', 'page={page}', 'pager_element=0'
            ]
        )

        # CY:
        self.ajax_post_episodes = '&'.join(
            [
                'view_name=webtv', 'view_display_id=page_1', 'view_args={view_args}',
                'view_path={view_path}/webtv', 'view_base_path=shows/%/%/webtv', 'page={page}', 'pager_element=0'
            ]
        )

        self.episodeslist_gr = ''.join([self.basegr_link, '/ajax/Isobar.AlphaTv.Components.Shows.Show.episodeslist'])
        self.episodeslist_gr_query = '?'.join([self.episodeslist_gr, 'Key={year}&Page=1&PageSize={pages}&ShowId={show_id}'])

        self.player_link = ''.join([self.basegr_link, '/ajax/Isobar.AlphaTv.Components.PopUpVideo.PopUpVideo.PlayMedia'])
        self.player_query = '/?'.join([self.player_link, 'vid={video_id}&showId={show_id}&year={year}'])

        self.newsgr_link = ''.join([self.basegr_link, '/news'])
        self.newsgr_link_ajax = ''.join([self.newsgr_link, '/?pg={page}&$component=NewsSection[0]&articleCategory={category}'])

        self.newscy_link = ''.join([self.basecy_link, '/shows/news/kentrikodeltio/webtv'])

        self.live_link_gr = ''.join([self.basegr_link, '/live/'])
        self.live_link_cy = ''.join([self.basecy_link, '/live'])

        self.yt_id_gr = 'UCYKe1v03QBPyApJID8CPjPA'
        self.yt_id_cy = 'UCxO8Xtg_dmOxubozdzLw3AA'
        self.yt_key = b64decode('VpGUslWWNVzZtgmd4kDWx8UWmFFSvV1T6p0cWNESkhGR5NVY6lUQ'[::-1])

    def root(self):

        if control.setting('region') == 'CY':
            formatter = control.lang(30005)
        else:
            formatter = control.lang(30004)

        self.list = [
            {
                'title': control.lang(30003).format(formatter),
                'action': 'selector',
                'icon': 'selector.png',
                'isFolder': 'False',
                'isPlayable': 'False'
            }
            ,
            {
                'title': control.lang(30001),
                'action': 'play',
                'icon': 'live.png',
                'url': self.live_link_cy if control.setting('region') == 'CY' else self.live_link_gr,
                'isFolder': 'False'
            }
            ,
            {
                'title': control.lang(30010),
                'action': 'recent',
                'icon': 'recent.png'
            }
            ,
            {
                'title': control.lang(30015 if control.setting('region') == 'CY' else 30008),
                'action': 'index',
                'icon': 'shows.png',
                'url': self.showscy_link_2 if control.setting('region') == 'CY' else self.showsgr_link
            }
            ,
            {
                'title': control.lang(30002),
                'action': 'index',
                'icon': 'series.png',
                'url': self.seriescy_link if control.setting('region') == 'CY' else self.seriesgr_link
            }
            ,
            {
                'title': control.lang(30011),
                'action': 'episodes' if control.setting('region') == 'CY' else 'news',
                'icon': 'news.png',
                'url': self.newscy_link if control.setting('region') == 'CY' else self.newsgr_link
            }
            ,
            {
                'title': control.lang(30009),
                'action': 'bookmarks',
                'icon': 'bookmarks.png'
            }
        ]

        entertainment = {
            'title': control.lang(30016),
            'action': 'index',
            'icon': 'shows.png',
            'url': self.showscy_link_1
        }

        if control.setting('region') == 'CY':

            self.list.insert(-4, entertainment)

        for item in self.list:

            cache_clear = {'title': 30022, 'query': {'action': 'cache_clear'}}
            item.update({'cm': [cache_clear]})

        directory.add(self.list, content='videos')

    @staticmethod
    def selector():

        choices = [control.lang(30004), control.lang(30005)]

        choice = control.selectDialog(choices, control.lang(30007))

        if choice == 0:
            control.setSetting('region', 'GR')
        elif choice == 1:
            control.setSetting('region', 'CY')

        if choice != -1:

            cache.FunctionCache().reset_cache()
            control.sleep(200)
            control.refresh()

    def recent(self):

        if control.setting('region') == 'CY':
            url = self.yt_id_cy
        else:
            url = self.yt_id_gr

        self.list = self.yt_videos(url)

        if self.list is None:
            return

        for i in self.list:

            i.update({'title': client.replaceHTMLCodes(py2_decode(i['title'])), 'action': 'play', 'isFolder': 'False'})

        if len(self.list) > int(control.setting('pagination_integer')) and control.setting('paginate') == 'true':

            try:

                pages = utils.list_divider(self.list, int(control.setting('pagination_integer')))
                self.list = pages[int(control.setting('page'))]
                reset = False

            except Exception:

                pages = utils.list_divider(self.list, int(control.setting('pagination_integer')))
                self.list = pages[0]
                reset = True

            self.list.insert(0, self.page_menu(len(pages), reset=reset))

        directory.add(self.list)

    def bookmarks(self):

        self.list = bookmarks.get()

        if not self.list:

            na = [{'title': 'N/A', 'action': None}]
            directory.add(na)

            return

        for i in self.list:

            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['delbookmark'] = i['url']
            i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

        control.sortmethods('title')

        directory.add(self.list, content='videos')

    @cache_method(1440)
    def index_gr(self, url):

        html = client.request(url)

        items = [i for i in re.findall(r'(<a.+?/a>)', html, re.S) if 'BLOCK_SERIES' not in i]

        for item in items:

            url = client.parseDOM(item, 'a', ret='href')[0]
            # title = client.replaceHTMLCodes(client.parseDOM(item, 'h3')[0]).replace(u'ᵒ', u' μοίρες')
            # image = client.parseDOM(item, 'div', attrs={'class': 'tvShowImg'}, ret='style')[0]
            # image = re.search(r'\([\'"](.+?)[\'"]\)', image).group(1)
            title = client.replaceHTMLCodes(client.parseDOM(item, 'h3')[0]).replace(u'ᵒ', u' μοίρες')
            try:
                image = client.parseDOM(item, 'div', attrs={'class': 'tvShowImg'})[0]
                image = client.parseDOM(image, 'img', ret='data-src')[0]
            except:
                image = control.icon()
            data = {'title': title, 'image': image, 'url': url}

            if 'alpha-news' in url:

                data.update({'action': 'news'})

            self.list.append(data)

        return self.list

    @cache_method(1440)
    def index_cy(self, url):

        html = client.request(url)

        items = [i for i in client.parseDOM(html, 'div', attrs={'class': 'box'}) if urlparse(url).path in i]

        try:
            next_link = client.parseDOM(html, 'a', attrs={'class': 'pager__link pager__link--next'}, ret='href')[0]
            next_link = urljoin(url.partition('?')[0], next_link)
        except Exception:
            next_link = None

        for item in items:

            try:
                title_field = client.parseDOM(item, 'div', {'class': 'box__overlay-title'})[0]
            except IndexError:
                continue

            title = client.replaceHTMLCodes(client.parseDOM(title_field, 'a')[0]).replace(u'ᵒ', u' μοίρες').strip()
            subtitle = client.replaceHTMLCodes(client.parseDOM(item, 'div', {'class': 'box__overlay-subtitle'})[0])
            label = ' | '.join([title, subtitle])
            url = client.parseDOM(title_field, 'a', ret='href')[0]
            url = urljoin(self.basecy_link, url + '/webtv')
            image = client.parseDOM(item, 'img', ret='src')[0]

            data = {'title': label, 'image': image, 'url': url, 'name': title}

            if next_link:
                data.update({'next': next_link})

            self.list.append(data)

        return self.list

    def index(self, url):

        if self.basecy_link in url:
            self.list = self.index_cy(url)
        elif self.basegr_link in url:
            self.list = self.index_gr(url)

        if not self.list:
            return

        for i in self.list:
            if 'action' not in i:
                i.update({'action': 'episodes'})
            if 'next' in i:
                i.update({'nextaction': 'index'})

        for i in self.list:
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        if self.basegr_link in url:

            control.sortmethods('title')
            control.sortmethods()

        directory.add(self.list, content='videos')

    @cache_method(60)
    def episodes_list_gr(self, url, title):

        html = client.request(url)

        link = client.parseDOM(html, 'a', ret='data-url')[1]

        html = client.request(link)

        div_season = client.parseDOM(html, 'div', attrs={'class': 'mbSeasonsList'})[0]

        years = client.parseDOM(div_season, 'a')
        show_id = [i for i in client.parseDOM(html, 'script') if 'window.Environment.showId' in i][0]
        show_id = re.search(r'showId = (\d+);', show_id).group(1)

        for y in years:

            h = client.request(self.episodeslist_gr_query.format(year=y, pages='366', show_id=show_id))

            self.data.append(h)

        html = ''.join(self.data)

        items = client.parseDOM(html, 'div', attrs={'class': 'episodeItem flexClm4'})

        try:
            title = title.decode('utf-8')
        except Exception:
            pass

        for item in items:

            descr = client.parseDOM(item, 'a', attrs={'class': 'openVideoPopUp'})[0]
            descr = client.stripTags(descr).strip()
            if descr.endswith((u'Nέο', u'Νεο', u'New')):
                descr = descr[:-3]
            label = u' - '.join([title, descr])
            image = client.parseDOM(item, 'div', attrs={'class': 'epImg'}, ret='style')[0]
            image = re.search(r'\([\'"](.+?)[\'"]\)', image).group(1)
            try:
                video = re.search(r'WebTvVideoId&quot;:(\d+).+?Year&quot;:(\d{4})}', item)
                url = self.player_query.format(video_id=video.group(1), show_id=show_id, year=video.group(2))
                self.list.append({'title': label, 'image': image, 'url': url})
            except Exception:
                pass

        return self.list

    @cache_method(60)
    def episodes_list_cy(self, url, title, image):

        if title:
            try:
                title = title.decode('utf-8')
                title = title.partition('|')[0]
            except Exception:
                title = title.partition('|')[0]

        if url.startswith(self.views_ajax):

            html = client.request(url.partition('#')[0], post=url.partition('#')[2])
            _json = json.loads(html)
            html = _json[4]['data']
            view_path = dict(parse_qsl(url.partition('#')[2]))['view_path']
            view_args = dict(parse_qsl(url.partition('#')[2]))['view_args']
            page = str(int(dict(parse_qsl(url.partition('#')[2]))['page']) + 1)

        else:

            html = client.request(url)
            view_path = urlparse(url).path
            view_args = '/'.join(view_path.split('/')[2:4])
            page = '1'

        next_link = '#'.join(
            [self.views_ajax, self.ajax_post_episodes.format(view_args=view_args, view_path=view_path, page=page)]
        )

        try:

            items = [i for i in client.parseDOM(html, 'div', {'class': 'box'}) if 'play-big' in i]

            if not items:
                raise Exception

            for item in items:
                itemtitle = client.parseDOM(item, 'a')[-1]
                if title:
                    label = ' - '.join([title, itemtitle])
                else:
                    label = itemtitle
                url = client.parseDOM(item, 'a', ret='href')[0]
                url = urljoin(self.basecy_link, url)
                image = client.parseDOM(item, 'img', ret='src')[0]

                data = {'title': label, 'image': image, 'url': url, 'next': next_link}

                if title:
                    data.update({'name': title})

                self.list.append(data)

        except Exception:

            self.list = [
                {
                    'title': u' - '.join([title, control.lang(30014)]),
                    'action': 'back',
                    'image': image,
                    'isFolder': 'False', 'isPlayable': 'False'
                }
                ,
                {
                    'title': control.lang(30013),
                    'action': 'back',
                    'image': control.icon(),
                    'isFolder': 'False', 'isPlayable': 'False'
                }
            ]

        return self.list

    def episodes(self, url, title=None, name=None, image=None):

        if self.basegr_link in url:
            self.list = self.episodes_list_gr(url, title)
        else:
            self.list = self.episodes_list_cy(url, name, image)

        if self.list is None:
            return

        if self.newscy_link == url:

            item = {
                'title': control.lang(30021),
                'action': 'enter_date',
                'icon': 'selector.png',
                'isFolder': 'False', 'isPlayable': 'False',
                'next': self.list[0]['next']
            }

            self.list.insert(0, item)

        for c, i in list(enumerate(self.list, 1)):

            if 'action' not in i:
                i.update({'action': 'play', 'isFolder': 'False', 'code': str(c)})

            if 'next' in i:
                i.update({'nextaction': 'episodes'})

        if control.setting('reverse') == 'true' and self.basegr_link in url:

            self.list = sorted(self.list, key=lambda k: int(k['code']), reverse=True)

        if len(self.list) > int(control.setting('pagination_integer')) and control.setting('paginate') == 'true':

            try:

                pages = utils.list_divider(self.list, int(control.setting('pagination_integer')))
                self.list = pages[int(control.setting('page'))]
                reset = False

            except Exception:

                pages = utils.list_divider(self.list, int(control.setting('pagination_integer')))
                self.list = pages[0]
                reset = True

            self.list.insert(0, self.page_menu(len(pages), reset=reset))

        if self.basegr_link in url:
            control.sortmethods()
            control.sortmethods('production_code')

        directory.add(self.list, content='videos')

    @cache_method(2880)
    def news_index(self, url):

        html = client.request(url)

        items = client.parseDOM(html, 'li', attrs={'class': 'dropable.*?'})

        for item in items:

            title = client.parseDOM(item, 'a')[0].strip().capitalize()
            if title.endswith(u'σ'):
                title = title[:-1] + u'ς'
            category = client.parseDOM(item, 'a', ret='data-catid')[0]
            # url = self.newsgr_link_ajax.format(page='1', category=category)

            self.list.append({'title': title, 'query': category})

        return self.list

    def news(self, url):

        self.list = self.news_index(url)

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'news_episodes', 'icon': 'news.png'})

        directory.add(self.list, content='videos')

    @cache_method(60)
    def news_episodes_listing(self, query):

        threads = []

        for i in list(range(1, 101)):

            threads.append(workers.Thread(self.thread, i, self.newsgr_link_ajax.format(page=str(i), category=query)))
            self.data.append('')
        [i.start() for i in threads]
        [i.join() for i in threads]

        html = '\n'.join(self.data)

        items = client.parseDOM(html, 'div', attrs={'class': 'newsItem'})

        for item in items:

            label = client.replaceHTMLCodes(client.parseDOM(item, 'a')[1])
            title = u'[CR]'.join([label, client.parseDOM(item, 'time')[0]])
            image = client.parseDOM(item, 'img', ret='src')[0]
            url = client.parseDOM(item, 'a', ret='href')[1]

            self.list.append({'title': title, 'image': image, 'url': url})

        return self.list

    def news_episodes(self, query):

        self.list = self.news_episodes_listing(query)

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False'})

        if len(self.list) > int(control.setting('pagination_integer')) and control.setting('paginate') == 'true':

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

    def play(self, url, query=None, resolved_mode=True):

        if url in [self.live_link_cy, self.live_link_gr]:

            title = 'Alpha'
            icon = control.icon()

        elif query:

            title = query
            icon = control.addonmedia('news.png')

        else:

            title = None
            icon = None

        stream = self.resolve(url)
        meta = {'title': title}
        dash = 'm3u8' in stream and control.kodi_version() >= 18.0

        directory.resolve(
            url=stream, meta=meta, dash=dash, icon=icon,
            mimetype='application/vnd.apple.mpegurl' if '.m3u8' in stream else None,
            manifest_type='hls' if '.m3u8' in stream else None, resolved_mode=resolved_mode
        )

    def resolve(self, url):

        referer = url

        if '.m3u8' in url or '.mp4' in url or url.startswith('plugin'):
            return url

        html = client.request(url)

        if url == self.live_link_gr:

            url = client.parseDOM(html, 'div', attrs={'class': 'livePlayer'}, ret='data-liveurl')[0]

        elif url == self.live_link_cy:

            url = re.search(r'hls: [\'"](.+?)[\'"]', html).group(1)

        elif 'cloudskep' in html:

            url = client.parseDOM(html, 'a', {'class': 'player-play-inline hidden'}, ret='href')[0]
            signature = client.parseDOM(html, 'footer', {'class': 'footer'}, ret='player-signature')
            if signature:
                url = '?wmsAuthSign='.join([url, signature[0]])

        else:

            if 'data-plugin-player' not in html:

                qs = parse_qs(urlparse(url).query)
                video_id = qs['vid'][0]
                year = qs['year'][0]
                show_id = qs['showId'][0]
                html = client.request(self.player_query.format(video_id=video_id, show_id=show_id, year=year))

            try:
                object_ = client.parseDOM(html, 'div', attrs={'id': 'Video-1'}, ret='data-plugin-kplayer')[0]
            except Exception:
                object_ = client.parseDOM(html, 'div', attrs={'id': 'currentvideourl'}, ret='data-plugin-kplayer')[0]

            url = json.loads(client.replaceHTMLCodes(object_))['Url']

            if len(url) == 11:

                return self.yt_session(url)

        return url + user_agents.spoofer(referer=True, ref_str=referer)

    def enter_date(self):

        input_date = control.inputDialog(control.lang(30021), type=control.input_date).replace(' ', '')

        query = ' - '.join(['Alpha News', input_date])

        try:
            date = datetime.strptime(input_date, '%d/%m/%Y').strftime('%d%m%y')
        except TypeError:
            date = datetime(*(time.strptime(input_date, '%d/%m/%Y')[0:6])).strftime('%d%m%y')

        url = ''.join([self.basecy_link, '/shows/news/kentrikodeltio/webtv/kentriko-deltio-{}'.format(date)])

        self.play(url=url, query=query, resolved_mode=False)

    def thread(self, i, url, post=None, sleep_=True):

        try:

            result = client.request(url, post=post)
            self.data[i] = result
            if sleep_:
                time.sleep(0.05)

        except:

            return

    @staticmethod
    def page_menu(pages, reset=False):

        if not reset:
            index = str(int(control.setting('page')) + 1)
        else:
            index = '1'

        menu = {
            'title': control.lang(30025).format(index),
            'action': 'switch',
            'query': str(pages),
            'icon': 'selector.png',
            'isFolder': 'False',
            'isPlayable': 'False'
        }

        return menu

    @staticmethod
    def switch(query):

        pages = [control.lang(30026).format(i) for i in list(range(1, int(query) + 1))]

        choice = control.selectDialog(pages, heading=control.lang(30028))

        if choice != -1:
            control.setSetting('page', str(choice))
            control.sleep(200)
            control.refresh()

    @cache_method(60)
    def yt_videos(self, url):

        return youtube.youtube(key=self.yt_key).videos(url)

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
