# -*- coding: utf-8 -*-
"""
    Re-written for Blacklodge
"""

import re
import requests
from blackscrapers import parse_qs, urljoin, urlencode
from blackscrapers.modules import client
from blackscrapers.modules import log_utils
from blackscrapers.modules import source_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['2embed.org']
        self.base_link = custom_base or 'https://www.2embed.org'
        self.search_link = '/embed/%s'

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
            if url is None:
                return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            query = '%s/%s/%s' % (data['imdb'], data['season'], data['episode']) if 'tvshowtitle' in data else data['imdb']

            url = self.search_link % query
            url = urljoin(self.base_link, url)

            r = requests.get(url, headers={'User-Agent': client.agent(), 'Referer': url}).text
            items = re.compile('data-id="(.+?)">.+?</a>').findall(r)

            for item in items:
                try:
                    item = 'https://www.2embed.org/ajax/embed/play?id=%s&_token=' % item
                    #log_utils.log('2embed item: ' + item)
                    r2 = requests.get(item, headers={'User-Agent': client.agent(), 'Referer': item}).text
                    #log_utils.log('2embed r2: ' + r2)
                    urls = re.findall('"link":"(.+?)","sources"', r2)
                    for url in urls:
                        #log_utils.log('2embed_url: ' + repr(url))
                        valid, host = source_utils.is_host_valid(url, hostDict)
                        if valid:
                            sources.append({'source': host, 'quality': '720p', 'language': 'en', 'info': '', 'url': url,
                                            'direct': False, 'debridonly': False})
                except:
                    log_utils.log('2EMBED - Exception', 1)
                    pass

            return sources
        except:
            log_utils.log('2EMBED - Exception', 1)
            return sources

    def resolve(self, url):
        return url
