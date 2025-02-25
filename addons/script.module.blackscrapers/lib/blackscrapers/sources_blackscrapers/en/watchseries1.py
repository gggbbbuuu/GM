# -*- coding: utf-8 -*-


import re

from blackscrapers.modules import client
from blackscrapers.modules import cleantitle
from blackscrapers.modules import source_utils
from blackscrapers.modules import log_utils
from blackscrapers import parse_qs, urlencode, urlparse, urljoin


from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['watchseries1.fun', 'watchseries.cyou', 'freeprojecttv.cyou', 'projectfreetv.lol']
        self.base_link = custom_base# or 'https://freeprojecttv.cyou'
        self.movie_link = '/movies/%s/'
        self.tvshow_link = '/tv-series/%s-season-%s-episode-%s/'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def tvshow(self, imdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tmdb': tmdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def episode(self, url, imdb, tmdb, title, premiered, season, episode):
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
            if url == None:
                return sources
            hostDict = hostprDict + hostDict
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            search_title = cleantitle.get_title(title, sep='-').lower()
            if 'tvshowtitle' in data:
                query = self.tvshow_link % (search_title, data['season'], data['episode'])
            else:
                query = self.movie_link % '-'.join((search_title, data['year']))
            html, self.base_link = client.list_client_request(self.base_link or self.domains, query)
            ext_links = client.parseDOM(html, 'tr', attrs={'class': 'ext_link.+?'})
            links = [(client.parseDOM(i, 'a', ret='href'), client.parseDOM(i, 'a', ret='title')) for i in ext_links]
            links = [(i[0][0], i[1][0]) for i in links if len(i[0]) > 0 and len(i[1]) > 0]
            for link, host in links:
                link = urljoin(self.base_link, link) if not link.startswith('http') else link
                valid, host = source_utils.is_host_valid(host, hostDict)
                if valid:
                    sources.append({'source': host, 'quality': 'SD', 'language': 'en', 'url': link, 'direct': False, 'debridonly': False})
            return sources
        except:
            log_utils.log('watchseries1', 1)
            return sources


    def resolve(self, url):
        html = client.request(url)
        try:
            link = client.parseDOM(html, 'iframe', ret='src')[0]
            return link
        except:
            base_link = '%s://%s' % (urlparse(url).scheme, urlparse(url).netloc)
            match = re.compile(r'href="(/open/site/.+?)">', re.I|re.S).findall(html) + re.compile(r'href="(/external/site/.+?)">', re.I|re.S).findall(html)
            link = urljoin(base_link, match[0])
            link = client.request(link, output='geturl')
            return link


