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

from six import ensure_str

from oathscrapers import parse_qs, urljoin, urlencode, quote_plus

from oathscrapers.modules import cleantitle
from oathscrapers.modules import client
from oathscrapers.modules import source_utils
from oathscrapers.modules import dom_parser
from oathscrapers.modules import log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['gr']
        self.domains = ['xrysoi.se']
        self.base_link = 'https://xrysoi.pro/'
        self.search_link = 'search/%s/feed/rss2/'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'localtitle': localtitle, 'title': title, 'aliases': aliases,'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url == None: return

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

            if url == None: return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = data['year']
            hdlr = 's%02de%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year
            query = '%s %s' % (title, year)
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            query = quote_plus(query)

            url = urljoin(self.base_link, self.search_link % query)

            r = client.request(url)
            posts = client.parseDOM(r, 'item')

            for post in posts:
                try:
                    name = client.parseDOM(post, 'title')[0]
                    name = client.replaceHTMLCodes(name)
                    name = ensure_str(name, errors='ignore')

                    y = re.findall('(\d{4}|S\d+E\d+|S\d+)', name, re.I)[0]

                    t = re.sub('(\.|\(|\[|\s)(\d{4}|S\d+E\d+|S\d+|3D)(\.|\)|\]|\s|)(.+|)', '', name, re.I)

                    if not (re.findall('\w+', cleantitle.get(t))[0] == cleantitle.get(title) and year == y): raise Exception()

                    if not 'tvshowtitle' in data:
                        links = client.parseDOM(post, 'a', ret='href')
                    else:
                        ep = '%02d' % int(data['episode'])
                        pattern = '>Season[\s|\:]%d<(.+?)(?:<b>Season|</content)' % int(data['season'])
                        data = re.findall(pattern, post, re.S|re.I)
                        data = dom_parser.parse_dom(data, 'a', req='href')
                        links = [(i.attrs['href'], i.content.lower()) for i in data]
                        links = [i[0] for i in links if (hdlr in i[0] or hdlr in i[1] or ep == i[1])]

                    for url in links:
                        try:
                            if any(x in url for x in ['.online', 'xrysoi.', 'filmer', '.bp', '.blogger']): continue

                            url = client.replaceHTMLCodes(url)
                            valid, host = source_utils.is_host_valid(url,hostDict)
                            #if 'hdvid' in host: valid = True
                            if not valid: continue
                            # try: dub = re.findall('ΜΕΤΑΓΛΩΤΙΣΜΕΝΟ', post, re.S|re.I)[0]
                            # except: dub = None
                            # info = ' / '.join((name, 'DUB')) if dub else name

                            sources.append({'source': host, 'quality': 'sd', 'language': 'gr', 'url': url, 'direct': False, 'debridonly': False})
                        except:
                            pass

                except:
                    log_utils.log('xrysoi_exc', 1)
                    pass

            return sources
        except:
            return sources

    def resolve(self, url):
        return url