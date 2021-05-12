# -*- coding: utf-8 -*-

'''
    OathScrapers module

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
        self.domains = ['gamato-movies.gr']
        self.base_link = 'https://gamato-movies.gr/'
        self.search_link = '?s=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'localtitle': localtitle, 'title': title, 'aliases': aliases,'year': year}
            url = urlencode(url)
            return url
        except:
            return

    # def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        # try:
            # url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
            # url = urlencode(url)
            # return url
        # except:
            # return

    # def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        # try:
            # if url == None: return

            # url = parse_qs(url)
            # url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            # url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            # url = urlencode(url)
            # return url
        # except:
            # return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:

            if url == None: return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = data['year']
            hdlr = 's%02de%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else ' (%s)' % year
            query = '%s %s' % (title, year)
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            query = quote_plus(query)

            url = urljoin(self.base_link, self.search_link % query)

            r = client.request(url)
            #log_utils.log('gamato_r: ' + r)
            posts = client.parseDOM(r, 'section', attrs={'class': 'gp-post-item.+?'})
            #log_utils.log('gamato_posts: ' + repr(posts))

            for post in posts:
                try:
                    link_title = dom_parser.parse_dom(post, 'a', req='href')[0]
                    #log_utils.log('gamato_link_title0: ' + repr(link_title))
                    link_title = (link_title.attrs['href'], link_title.attrs['title'])
                    #log_utils.log('gamato_link_title: ' + repr(link_title))

                    y = re.findall('\((\d{4})\)', link_title[1], re.I)[0]

                    t = re.sub('(\.|\(|\[|\s)(\d{4}|S\d+E\d+|S\d+|3D)(\.|\)|\]|\s|)(.+|)', '', link_title[1], re.I)
                    #log_utils.log('gamato_link_t: ' + repr(t))

                    if (cleantitle.get(t) == cleantitle.get(title) and year == y):
                        r2 = client.request(link_title[0])
                        #log_utils.log('gamato_r2: ' + r2)

                        items = client.parseDOM(r2, 'div', attrs={'class': 'wpb_text_column wpb_content_element '})
                        items = [i for i in items if any(x in i for x in ['ΕΛΛΗΝΙΚΟΙ', 'ΜΕΤΑΓΛΩΤΙΣΜΕΝΟ'])]
                        #log_utils.log('gamato_items: ' + repr(items))
                        items = client.parseDOM(items, 'tr')[1:]
                        log_utils.log('gamato_items: ' + repr(items))
                        for item in items:
                            try:
                                log_utils.log('gamato_item: ' + repr(item))
                                url_host = dom_parser.parse_dom(item, 'a', req='href')[0]
                                url = url_host.attrs['href']
                                log_utils.log('gamato_url: ' + repr(url))
                                host = ensure_str(url_host.content).lower()
                                log_utils.log('gamato_host: ' + repr(host))
                                qual = client.parseDOM(item, 'td')[1]
                                log_utils.log('gamato_qual: ' + repr(qual))
                                _info = client.parseDOM(item, 'td')[2]
                                log_utils.log('gamato__info: ' + repr(_info))
                                #valid, host = source_utils.is_host_valid(host, hostDict)
                                #log_utils.log('gamato_host2: ' + repr(host))
                                quality = source_utils.check_url(qual)
                                log_utils.log('gamato_quality: ' + repr(quality))
                                if 'ΕΛΛΗΝΙΚΟΙ' in _info: info = 'subs'
                                elif 'ΜΕΤΑΓΛΩΤ' in _info: info = 'dub'
                                else: info = ''
                                log_utils.log('gamato_info: ' + repr(info))
                                if host in hostDict:

                                    sources.append({'source': host, 'quality': quality, 'url': url, 'info': info, 'language': 'gr', 'direct': False, 'debridonly': False})
                            except:
                                pass

                except:
                    log_utils.log('gamato_exc1', 1)
                    pass

            return sources
        except:
            log_utils.log('gamato_exc', 1)
            return sources

    def resolve(self, url):
        if 'gosfd' in url:
            if url.startswith('http:'):
                url = url.replace('http:', 'https:')
            import requests
            session = requests.Session()
            resp = session.head(url, allow_redirects=True)
            url = ensure_str(resp.url)
            log_utils.log('gamato_resurl: ' + repr(url))
        return url

