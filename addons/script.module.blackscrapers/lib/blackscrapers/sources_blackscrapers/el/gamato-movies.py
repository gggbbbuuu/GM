# -*- coding: utf-8 -*-

'''
    OathScrapers module
'''

import re

from six import ensure_str

from blackscrapers import parse_qs, urljoin, urlencode, quote_plus

from blackscrapers.modules import cleantitle
from blackscrapers.modules import client
from blackscrapers.modules import source_utils
from blackscrapers.modules import dom_parser
from blackscrapers.modules import log_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['el']
        self.domains = ['gamatomovies.gr']
        self.base_link = custom_base or 'https://gamatomovies1.gr'
        self.search_link = '?s=%s'

    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'localtitle': localtitle, 'title': title,'year': year}
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
            query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            query = quote_plus(query)

            url = urljoin(self.base_link, self.search_link % query)

            r = client.request(url)
            posts = client.parseDOM(r, 'section', attrs={'class': 'gp-post-item.+?'})

            for post in posts:
                try:
                    link_title = dom_parser.parse_dom(post, 'a', req='href')[0]
                    link_title = (link_title.attrs['href'], link_title.attrs['title'])

                    y = re.findall(r'\((\d{4})\)', link_title[1], re.I)[0]

                    t = re.sub(r'(\.|\(|\[|\s)(\d{4}|S\d+E\d+|S\d+|3D)(\.|\)|\]|\s|)(.+|)', '', link_title[1], re.I)

                    if (cleantitle.get(t) == cleantitle.get(title) and year == y):
                        r2 = client.request(link_title[0])

                        items = client.parseDOM(r2, 'div', attrs={'class': 'wpb_text_column wpb_content_element '})
                        items = [i for i in items if any(x in i for x in ['ΕΛΛΗΝΙΚΟΙ', 'ΜΕΤΑΓΛΩΤ'])]
                        items = client.parseDOM(items, 'tr')[1:]
                        for item in items:
                            try:
                                url_host = dom_parser.parse_dom(item, 'a', req='href')[0]
                                url = url_host.attrs['href']
                                host = client.replaceHTMLCodes(url_host.content).lower()
                                host = ensure_str(host)
                                try:
                                    qual = client.parseDOM(item, 'td')[1]
                                    _info = client.parseDOM(item, 'td')[2]
                                    quality = source_utils.check_url(qual)
                                    if 'ΕΛΛΗΝΙΚΟΙ' in _info: info = 'SUBS'
                                    elif 'ΜΕΤΑΓΛΩΤ' in _info: info = 'DUB'
                                    else: info = ''
                                except:
                                    quality = 'sd'
                                    info = ''

                                #if host in hostDict:
                                valid, host = source_utils.is_host_valid(host, hostDict)
                                if valid:
                                    sources.append({'source': host, 'quality': quality, 'url': url, 'info': info, 'language': 'el', 'direct': False, 'debridonly': False})
                            except:
                                pass

                except:
                    #log_utils.log('gamato_exc1', 1)
                    pass

            return sources
        except:
            log_utils.log('gamato_exc', 1)
            return sources

    def resolve(self, url):
        if any(x in url for x in ['gosafe', 'gosfd']):
            try:
                if url.startswith('http:'):
                    url = url.replace('http:', 'https:')
                import requests
                session = requests.Session()
                resp = session.head(url, allow_redirects=True)
                url = resp.url
                #log_utils.log('gamato_resurl: ' + repr(url))
            except:
                pass
        return url

