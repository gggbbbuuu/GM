# -*- coding: utf-8 -*-

import re

from blackscrapers.modules import client
from blackscrapers.modules import log_utils
from blackscrapers.modules import source_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['databasegdriveplayer.co', 'database.gdriveplayer.us', 'series.databasegdriveplayer.co']
        self.base_link = custom_base or 'https://databasegdriveplayer.xyz'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            if imdb == '0':
                return
            url = self.base_link + '/player.php?imdb=%s' % imdb
            return url
        except Exception:
            log_utils.log('movie', 1)
            return


    def tvshow(self, imdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = self.base_link + '/player.php?type=series&imdb=%s' % imdb
            return url
        except Exception:
            log_utils.log('tvshow', 1)
            return


    def episode(self, url, imdb, tmdb, title, premiered, season, episode):
        try:
            if not url:
                return
            url += '&season=%s&episode=%s' % (season, episode)
            return url
        except Exception:
            log_utils.log('episode', 1)
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url == None:
                return sources
            hostDict = hostDict + hostprDict
            html = client.request(url)
            if '&season=' in url:
                s_e = re.findall(r"&season=(\d+)&episode=(\d+)", url)[0]
                season, episode = int(s_e[0]), int(s_e[1])
                page_title = client.parseDOM(html, 'title')[0]
                s_e = re.findall(r"season\s*(\d+)\s*episode\s*(\d+)", page_title, flags=re.I|re.S)[0]
                stream_season, stream_episode = int(s_e[0]), int(s_e[1])
                if not (season == stream_season and episode == stream_episode):
                    raise Exception('scraper loaded wrong episode: s%se%s' % (stream_season, stream_episode))
            servers = client.parseDOM(html, 'ul', attrs={'class': 'list-server-items'})[0]
            links = client.parseDOM(servers, 'a', ret='href')
            for link in links:
                if link.startswith('/player.php'):
                    continue
                link = 'https:' + link if not link.startswith('http') else link
                link = link.replace('vidcloud.icu', 'vidembed.io').replace(
                                    'vidcloud9.com', 'vidembed.io').replace(
                                    'vidembed.cc', 'vidembed.io').replace(
                                    'vidnext.net', 'vidembed.me')
                if 'vidembed' in link or 'membed' in link:
                    for source in self.get_vidembed(link, hostDict):
                        sources.append(source)
                valid, host = source_utils.is_host_valid(link, hostDict)
                if valid:
                    link = link.split('&title=')[0]
                    sources.append({'source': host, 'quality': '720p', 'language': 'en', 'url': link, 'direct': False, 'debridonly': False})
            return sources
        except Exception:
            log_utils.log('sources', 1)
            return sources


    def resolve(self, url):
        return url


    def get_vidembed(self, link, hostDict):
        sources = []
        try:
            html = client.request(link)
            urls = client.parseDOM(html, 'li', ret='data-video')
            if urls:
                for url in urls:
                    url = url.replace('vidcloud.icu', 'vidembed.io').replace(
                                      'vidcloud9.com', 'vidembed.io').replace(
                                      'vidembed.cc', 'vidembed.io').replace(
                                      'vidnext.net', 'vidembed.me')
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        url = url.split('&title=')[0]
                        sources.append({'source': host, 'quality': '720p', 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})
            return sources
        except Exception:
            #log_utils.log('vidembed', 1)
            return sources

