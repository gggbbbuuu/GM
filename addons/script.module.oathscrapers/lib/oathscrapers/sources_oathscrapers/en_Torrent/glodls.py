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

import re

from oathscrapers import parse_qs, urljoin, urlencode, quote_plus
from oathscrapers.modules import debrid
from oathscrapers.modules import cleantitle
from oathscrapers.modules import client
from oathscrapers.modules import source_utils
from oathscrapers.modules import log_utils

from oathscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['glodls.to', 'gtdb.to']
        self.base_link = custom_base or 'https://glodls.to'
        self.tvsearch = '/search_results.php?search={0}&cat=41&incldead=0&inclexternal=0&lang=1&sort=seeders&order=desc'
        self.moviesearch = '/search_results.php?search={0}&cat=1&incldead=0&inclexternal=0&lang=1&sort=size&order=desc'
        self.aliases = []

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources

            if debrid.status() is False:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            self.title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            self.title = cleantitle.get_query(self.title)
            self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = ' '.join((self.title, self.hdlr))
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            if 'tvshowtitle' in data:
                url = self.tvsearch.format(quote_plus(query))
                url = urljoin(self.base_link, url)

            else:
                url = self.moviesearch.format(quote_plus(query))
                url = urljoin(self.base_link, url)

            items = self._get_items(url)

            hostDict = hostDict + hostprDict
            for item in items:
                try:
                    name = item[0]
                    url = item[1]
                    url = url.split('&tr')[0]
                    quality, info = source_utils.get_release_quality(name, url)
                    info.insert(0, item[2])
                    info = ' | '.join(info)

                    sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url, 'info': info,
                                    'direct': False, 'debridonly': True, 'size': item[3], 'name': name})
                except:
                    log_utils.log('glodls0_exc', 1)
                    pass

            return sources
        except:
            log_utils.log('glodls1_exc', 1)
            return sources

    def _get_items(self, url):
        items = []
        try:
            headers = {'User-Agent': client.agent()}
            r = client.request(url, headers=headers)
            posts = client.parseDOM(r, 'tr', attrs={'class': 't-row'})
            posts = [i for i in posts if not 'racker:' in i]
            for post in posts:
                try:
                    data = client.parseDOM(post, 'a', ret='href')
                    url = [i for i in data if 'magnet:' in i][0]
                    name = client.parseDOM(post, 'a', ret='title')[0]

                    if not source_utils.is_match(name, self.title, self.hdlr, self.aliases):
                        continue

                    try:
                        size = re.findall('((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB))', post)[0]
                        dsize, isize = source_utils._size(size)
                    except:
                        dsize, isize = 0.0, ''

                    items.append((name, url, isize, dsize))
                except:
                    pass
            return items
        except:
            log_utils.log('glodls2_exc', 1)
            return items


    def resolve(self, url):
        return url
