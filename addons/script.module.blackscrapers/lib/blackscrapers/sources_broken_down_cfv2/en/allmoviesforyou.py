# -*- coding: utf-8 -*-
# Blackscrapers module

import re
from blackscrapers.modules import client, cleantitle, source_utils, log_utils
from blackscrapers import parse_qs, urljoin, urlencode, quote_plus


from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['allmoviesforyou.net', 'allmoviesforyou.co', 'amfy.io']
        self.base_link = custom_base or 'https://anymovie.cc'
        self.movie_link = '/movies/%s/'
        self.tv_link = '/episode/%s-%sx%s/'
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

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            search_title = cleantitle.get_title(title, sep='-').lower()

            if 'tvshowtitle' in data:
                query = self.tv_link % (search_title, data['season'], data['episode'])
            else:
                query = self.movie_link % search_title

            url = urljoin(self.base_link, query)
            headers = {'User-Agent': client.agent(), 'Referer': self.base_link}
            r = client.request(url, headers=headers)

            try: qual = client.parseDOM(r, 'span', attrs={'class': 'Qlty'})[0]
            except: qual = 'SD'
            url = re.findall('<iframe src="(.+?)"', r)[0]
            url = url.replace('#038;', '').strip()
            #log_utils.log(url)
            headers.update({'Referer': url})
            r = client.request(url, headers=headers)
            urls = re.findall('src="(.+?)"', r)
            for url in urls:
                url = url.strip()
                quality, _ = source_utils.get_release_quality(qual, url)
                valid, host = source_utils.is_host_valid(url, hostDict)
                if valid:
                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url,
                                    'direct': False, 'debridonly': False})

            return sources
        except Exception:
            log_utils.log('allmoviesforyou', 1)
            return sources

    def resolve(self, url):
        return url
