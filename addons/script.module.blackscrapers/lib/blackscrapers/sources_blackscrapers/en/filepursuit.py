# -*- coding: utf-8 -*-

'''
    OpenScrapers Project
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
import requests
import simplejson as json

from blackscrapers import parse_qs, urljoin, urlencode, quote_plus
from blackscrapers.modules import control
from blackscrapers.modules import cleantitle
from blackscrapers.modules import client
from blackscrapers.modules import source_utils
from blackscrapers.modules import log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.base_link = 'https://filepursuit.p.rapidapi.com'
        # 'https://rapidapi.com/azharxes/api/filepursuit' to obtain key
        self.search_link = '/?type=video&q=%s'
        self.aliases = []


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def tvshow(self, imdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tmdb': tmdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def episode(self, url, imdb, tmdb, title, premiered, season, episode):
        try:
            if url is None:
                return
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

            api_key = control.setting('filepursuit.api')
            if not api_key:
                return sources

            headers = {"x-rapidapi-host": "filepursuit.p.rapidapi.com",
                "x-rapidapi-key": api_key}

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s %s' % (title, hdlr)
            query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url)

            r = client.request(url, headers=headers)
            r = json.loads(r)

            if 'not_found' in r['status']:
                return sources

            results = r['files_found']
            for item in results:
                try:
                    dsize = float(item['file_size_bytes']) / 1073741824
                    isize = '%.2f GB' % dsize
                except:
                    dsize = 0.0
                    isize = ''

                url = item['file_link']

                try:
                    name = item['file_name']
                except:
                    name = url.split('/')[-1]
                name = cleantitle.get_title(name)

                if any(x in name.lower() for x in ['trailer', 'promo']):
                    continue

                if not source_utils.is_match(name, title, hdlr, self.aliases):
                    continue

                info = []

                quality, _ = source_utils.get_release_quality(name, url)

                info.insert(0, isize)

                info = ' | '.join(info)

                sources.append({'source': 'direct', 'quality': quality, 'language': 'en', 'url': url, 'info': info,
                                'direct': True, 'debridonly': False, 'size': dsize, 'name': name})
            return sources
        except:
            log_utils.log('filepursuit exc', 1)
            return sources


    def resolve(self, url):
        return url