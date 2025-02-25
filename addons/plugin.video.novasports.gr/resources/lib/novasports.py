# -*- coding: utf-8 -*-

'''
    Novasports.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import unicode_literals, absolute_import

from time import sleep
import re, json
from tulip.compat import bytes, str, iteritems
from tulip import directory, client, cache, control, user_agents, bookmarks
from datetime import date, datetime


CACHE_SIZE = int(control.setting('cache_size')) * 60
cache_method = cache.FunctionCache().cache_method


class Indexer:

    def __init__(self):

        self.list = []
        self.data = []
        self.base_link = 'https://www.novasports.gr'
        self.api_link = ''.join([self.base_link, '/api/v1'])
        self.latest_link = ''.join([self.api_link, '/videos/feed'])
        self.live_link = ''.join([self.api_link, '/videos/livetv'])
        self.live_by_date_link = ''.join([self.api_link, '/videos/livebydate/{date}'])
        self.matches_link = ''.join([self.api_link, '/matchcenter/events/date/{date}'])
        self.event_link = ''.join([self.api_link, '/videos/event/{event}/teama/{team_a}/teamb/team_b'])
        self.sports_link = ''.join([self.api_link, '/webtv/{type}/{sport_id}/range/{range_id}/number/24'])
        self.sports_latest_link = ''.join([self.api_link, '/webtv/latest/range/{range_id}/number/24'])
        self.index_link = ''.join([self.api_link, '/{type}/{event_id}/videos/page/{page}/range/9'])
        self.webtv_link = ''.join([self.base_link, '/web-tv'])

    def root(self):

        self.list = [
            {
                'title': control.lang(30002),
                'action': 'videos',
                'url': self.live_link
            }
            ,
            {
                'title': control.lang(30001),
                'action': 'videos',
                'url': self.latest_link
            }
            ,
            {
                'title': control.lang(30003),
                'action': 'matches'
            }
            ,
            {
                'title': control.lang(30009),
                'action': 'webtv'
            }
            ,
            {
                'title': control.lang(30017),
                'action': 'categories'
            }
            ,
            {
                'title': control.lang(30022),
                'action': 'bookmarks'
            }
        ]

        for item in self.list:

            cache_clear = {'title': 30010, 'query': {'action': 'cache_clear'}}
            item.update({'cm': [cache_clear]})

        directory.add(self.list, content='videos')

    def bookmarks(self):

        self.list = bookmarks.get()

        if not self.list:
            na = [{'title': control.lang(30024), 'action': None}]
            directory.add(na)
            return

        for i in self.list:
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['delbookmark'] = i['url']
            i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

        control.sortmethods('title')

        directory.add(self.list, content='videos')

    def videos(self, url, query=None):

        self.list = self.items_list(url)

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'play', 'isFolder': 'False'})

        if 'live' in url and url != self.live_link:

            formatted_date = datetime.strptime(query, '%Y%m%d').strftime('%d-%m-%Y')

            this_date = {
                'title': control.lang(30023).format(formatted_date),
                'action': None
            }

            self.list.insert(0, this_date)

        if url == self.live_link:

            more_live = {
                'title': control.lang(30013),
                'url': self.live_by_date_link.format(date=bytes(date.today()).replace('-', '')),
                'action': 'videos',
                'query': bytes(date.today()).replace('-', '')
            }

            self.list.append(more_live)

        elif 'livebydate' in url:

            go_to_root = {
                'title': control.lang(30012),
                'action': 'go_to_root',
                'isFolder': 'False',
                'isPlayable': 'False'
            }

            next_live = {
                'title': control.lang(30006),
                'url': self.live_by_date_link.format(date=int(query) + 1),
                'action': 'videos',
                'query': bytes(int(query) + 1)
            }

            previous_live = {
                'title': control.lang(30007),
                'url': self.live_by_date_link.format(date=int(query) - 1),
                'action': 'videos',
                'query': bytes(int(query) - 1)
            }

            self.list.insert(0, next_live)
            self.list.append(previous_live)
            self.list.append(go_to_root)

        directory.add(self.list, content='videos')

    @cache_method(CACHE_SIZE)
    def items_list(self, url):

        if '/api/v1' not in url:

            html = client.request(url)

            if 'web-tv' in url:

                if url.endswith('roi'):

                    urls = [
                        self.sports_latest_link.format(range_id=i) for i in list(
                            range(0, int(control.setting('pages_size')) + 1)
                        )
                    ]

                else:

                    json_id = client.parseDOM(html, 'div', attrs={'class': 'web-tv-container-.+'}, ret='class')[0]
                    json_id = re.search(r'(\d+)', json_id).group(1)
                    type_ = client.parseDOM(html, 'div', attrs={'class': 'vocabulary hidden'})[0]

                    urls = [
                        self.sports_link.format(type=type_, sport_id=json_id, range_id=i) for i in
                        list(range(0, int(control.setting('pages_size')) + 1))
                    ]

            else:

                try:
                    event_id = client.parseDOM(html, 'div', attrs={'id': 'event_id'})[0]
                    type_ = 'event'
                except IndexError:
                    event_id = client.parseDOM(html, 'div', attrs={'id': 'video-list-term-id'})[0]
                    type_ = 'team'

                urls = [
                    self.index_link.format(type=type_, event_id=event_id, page=i) for i in
                    list(range(0, int(control.setting('pages_size')) + 1))
                ]

            for url in urls:

                _json = client.request(url, output='json')
                sleep(0.1)
                items = _json['Items']

                self.data.extend(items)

        else:

            self.data = client.request(url, output='json')

        for r in self.data:

            try:
                title = client.replaceHTMLCodes(r['Title'])
            except KeyError:
                continue

            if 'Is_Live' in r:
                title = '[CR]'.join([title, r['Live_From']])

            try:
                plot = client.replaceHTMLCodes(r['Short_Desc'])
            except TypeError:
                plot = control.lang(30011)
            urls = r['VideoUrl']

            for u in urls:

                data = {'title': title, 'plot': plot}

                image = r.get('Image')

                if image:
                    image = ''.join([self.base_link, image])
                    data.update({'image': image})
                else:
                    data.update({'icon': control.icon()})

                url = u['uri']

                data.update({'url': url})

                self.list.append(data)

        return self.list

    def matches(self, query=None):

        def appender(events):

            _list = []

            for event in events:

                event_name = event['event_name']

                match_centers = event['match_centers']

                for match in match_centers:

                    team_a = match['team_a']
                    team_b = match['team_b']
                    score_a = str(match['score_a'])
                    score_b = str(match['score_b'])
                    desc = match['desc']
                    if not desc:
                        desc = control.lang(30011)
                    _date = str(match['date'])
                    url = ''.join([self.base_link, match['alias_url']])

                    title = ''.join(
                        [
                            event_name, u': ', team_a, u' - ', team_b, u'[CR]', control.lang(30004),
                            score_a, u' - ', score_b, u' (', desc, u' | ', _date, u')'
                        ]
                    )

                    data = {'title': title, 'url': url, 'action': 'event'}

                    _list.append(data)

            return _list

        if not query:
            date_ = bytes(date.today()).replace('-', '')
        else:
            date_ = bytes(query)

        result = client.request(self.matches_link.format(date=date_), output='json')

        if not result['events'] and not result['friendly']:

            self.list = [{'title': control.lang(30008), 'action': 'matches'}]

        else:

            if result['events']:

                self.list.extend(appender(result['events']))

            if result['friendly']:

                self.list.extend(appender(result['friendly']))

        previous_date = {
            'title': control.lang(30007),
            'action': 'matches',
            'query': bytes(int(date_) - 1)
        }

        next_date = {
            'title': control.lang(30006),
            'action': 'matches',
            'query': bytes(int(date_) + 1)
        }

        add_date = {
            'title': control.lang(30005),
            'action': 'add_date',
            'isFolder': 'False',
            'isPlayable': 'False'
        }

        go_to_root = {
            'title': control.lang(30012),
            'action': 'go_to_root',
            'isFolder': 'False',
            'isPlayable': 'False'
        }

        self.list.insert(0, previous_date)
        self.list.append(next_date)
        self.list.append(add_date)
        self.list.append(go_to_root)

        directory.add(self.list)

    def add_date(self):

        input_date = control.inputDialog(type=control.input_date)

        input_date = ''.join(input_date.split('/')[::-1]).replace(' ',  '0')

        directory.run_builtin(action='matches', query=input_date)

    def event(self, url):

        html = client.request(url)

        event_id = client.parseDOM(html, 'div', attrs={'id': 'event_id'})[0]
        teama_id = client.parseDOM(html, 'div', attrs={'id': 'teama_id'})[0]
        teamb_id = client.parseDOM(html, 'div', attrs={'id': 'teamb_id'})[0]

        items = client.request(self.event_link.format(event=event_id, team_a=teama_id, team_b=teamb_id), output='json')

        videos = [i for i in items if ('Has_Videos' in i and i['Has_Videos']) or ('MediaType' in i and i['MediaType'] == 'video')]

        for video in videos:

            title = client.replaceHTMLCodes(video['Title'])

            try:
                image = video['ImageLowQuality']
                if image:
                    image = ''.join([self.base_link, image])
                else:
                    image = control.icon()
                fanart = video['Image']
                if fanart:
                    fanart = ''.join([self.base_link, fanart])
                else:
                    fanart = None
            except KeyError:
                image = video['Image']
                if image:
                    image = ''.join([self.base_link, image])
                else:
                    image = control.icon()
                fanart = None

            url = ''.join([self.base_link, video['Link']])

            data = {'title': title, 'image': image, 'url': url, 'action': 'play', 'isFolder': 'False'}

            if fanart:
                data.update({'fanart': fanart})

            self.list.append(data)

        directory.add(self.list)

    def play(self, url):

        if '.mp4' in url or '.m3u8' in url:

            stream = url

        else:

            html = client.request(url)

            stream = re.search("video/mp4.+?'(.+?)'", html, re.S).group(1)

        try:
            addon_enabled = control.addon_details('inputstream.adaptive').get('enabled')
        except KeyError:
            addon_enabled = False

        dash = '.m3u8' in url and control.kodi_version() >= 18.0 and addon_enabled and control.setting('hls_dash') == 'true'

        if dash:
            directory.resolve(stream, dash=dash, mimetype='application/vnd.apple.mpegurl', manifest_type='hls')
        else:
            directory.resolve(stream)

    @cache_method(CACHE_SIZE)
    def _webtv(self):

        html = client.request(self.webtv_link)

        web_tv_nav = client.parseDOM(html, 'ul', attrs={'class': 'menu menu--web-tv nav'})[0]

        items = client.parseDOM(web_tv_nav, 'li')[1:]

        for item in items:

            title = client.parseDOM(item, 'a')[0]
            url = client.parseDOM(item, 'a', ret='href')[0]
            url = ''.join([self.base_link, url])

            self.list.append({'title': title, 'url': url})

        return self.list

    def webtv(self):

        self.list = self._webtv()

        if self.list is None:
            return

        for i in self.list:
            i.update({'action': 'videos'})

        directory.add(self.list)

    @cache_method(5760)
    def index(self):

        html = client.request(self.webtv_link.replace('www', 'm'), headers={'User-Agent': user_agents.IPHONE})

        items = client.parseDOM(html, 'li', attrs={'class': 'expanded dropdown'})

        football = items[0]
        basket = items[1]
        teams = items[5]

        football_items = client.parseDOM(football, 'div', attrs={'class': 'mega-menu-top-title'})
        basket_items = client.parseDOM(basket, 'div', attrs={'class': 'mega-menu-top-title'})
        teams_items = client.parseDOM(teams, 'div', attrs={'class': 'mega-menu-top-title'})
        football_teams = [i for i in teams_items if 'podosfairo' in i]
        basket_teams = [i for i in teams_items if 'mpasket' in i]

        fb = []
        bt = []
        ftm = []
        btm = []

        for fi in football_items:

            try:
                title = client.replaceHTMLCodes(client.parseDOM(fi, 'a')[0])
            except IndexError:
                continue
            url = ''.join([self.base_link, client.parseDOM(fi, 'a', ret='href')[0], '?type=videos'])

            fb.append({'title': title, 'url': url})

        for bi in basket_items:

            try:
                title = client.replaceHTMLCodes(client.parseDOM(bi, 'a')[0])
            except IndexError:
                continue
            url = ''.join([self.base_link, client.parseDOM(bi, 'a', ret='href')[0], '?type=videos'])

            bt.append({'title': title, 'url': url})

        for ti in football_teams:

            try:
                title = client.replaceHTMLCodes(client.parseDOM(ti, 'a')[0])
            except IndexError:
                continue
            url = ''.join([self.base_link, client.parseDOM(ti, 'a', ret='href')[0], '?type=videos'])
            image = ''.join([self.base_link, client.parseDOM(ti, 'img', ret='src')[0]])

            ftm.append({'title': title, 'url': url, 'image': image})

        for ti in basket_teams:

            try:
                title = client.replaceHTMLCodes(client.parseDOM(ti, 'a')[0])
            except IndexError:
                continue
            url = ''.join([self.base_link, client.parseDOM(ti, 'a', ret='href')[0], '?type=videos'])
            image = ''.join([self.base_link, client.parseDOM(ti, 'img', ret='src')[0]])

            btm.append({'title': title, 'url': url, 'image': image})

        return {'football': fb, 'basket': bt, 'teams_football': ftm, 'teams_basket': btm}

    def categories(self):

        index_items = self.index()

        if index_items is None:
            return

        if control.setting('sport') == '0':
            integer = 30020
            self.list = index_items['football']
        else:
            self.list = index_items['basket']
            integer = 30021

        for i in self.list:
            i.update({'action': 'videos'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        teams = {
            'title': control.lang(30018),
            'action': 'teams_index'
        }

        selector = {
                'title': control.lang(30019).format(control.lang(integer)),
                'action': 'switch',
                'isFolder': 'False',
                'isPlayable': 'False'
        }

        self.list.insert(0, selector)
        self.list.append(teams)

        directory.add(self.list)

    def teams_index(self):

        index_items = self.index()

        if index_items is None:
            return

        if control.setting('sport') == '0':
            integer = 30020
            self.list = index_items['teams_football']
        else:
            self.list = index_items['teams_basket']
            integer = 30021

        for i in self.list:
            i.update({'action': 'videos'})
            bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
            bookmark['bookmark'] = i['url']
            i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

        selector = {
            'title': control.lang(30019).format(control.lang(integer)),
            'action': 'switch',
            'isFolder': 'False',
            'isPlayable': 'False'
        }

        self.list.insert(0, selector)

        directory.add(self.list)

    def switch(self):

        choices = [control.lang(30020), control.lang(30021)]

        choice = control.selectDialog(choices)

        if choice == 0:
            control.setSetting('sport', '0')
        elif choice == 1:
            control.setSetting('sport', '1')

        if choice != -1:
            control.sleep(100)
            control.refresh()
