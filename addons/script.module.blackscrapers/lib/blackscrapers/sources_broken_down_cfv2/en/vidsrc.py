# -*- coding: utf-8 -*-

'''
    OathScrapers module
'''


import re

from blackscrapers import parse_qs, urljoin, urlencode
from blackscrapers.modules import client
from blackscrapers.modules import dom_parser
from blackscrapers.modules import source_utils
from blackscrapers.modules import log_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['vidsrc.me', 'v2.vidsrc.me']
        self.base_link = custom_base or 'https://vidsrc.xyz'
        self.movie_link = '/embed/movie?imdb=%s'
        self.tv_link = '/embed/tv?imdb=%s&season=%s&episode=%s'
        self.headers = {'User-Agent': client.agent(), 'Referer': self.base_link}

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

            if 'tvshowtitle' in data:
                query = self.tv_link % (data['tmdb'], data['season'], data['episode'])
            else:
                if not data['imdb'] or data['imdb'] == '0':
                    return sources
                query = self.movie_link % data['imdb']

            url = urljoin(self.base_link, query)
            #log_utils.log('VIDSRC url: ' + repr(url))

            r = client.r_request(url)
            #log_utils.log('VIDSRC r: ' + r)

            url = re.findall('"player_iframe" src="(.+?)"', r)[0]
            url = 'https:%s' % url if not url.startswith('http') else url
            sources.append({'source': 'direct', 'quality': '720p', 'language': 'en', 'url': url, 'direct': True, 'debridonly': False})

            # items = dom_parser.parse_dom(r, 'div', req='data-hash')
            # #log_utils.log('vidsrc_items: ' + repr(items))
            # for item in items:
                # url = 'https://rcp.vidsrc.me/rcp/%s' % item.attrs['data-hash']
                # #log_utils.log('VIDSRC url: ' + repr(url))
                # host = item.content
                # #log_utils.log('VIDSRC host: ' + repr(host))
                # host = host.lower().replace('vidsrc', '').strip()
                # if host == 'pro': # other sources are javascripted
                    # host = 'direct'
                    # sources.append({'source': host, 'quality': '720p', 'language': 'en', 'url': url, 'direct': True, 'debridonly': False})
            return sources
        except:
            log_utils.log('VIDSRC Exception', 1)
            return sources

    def resolve(self, url):
        #log_utils.log('VIDSRCurl0: ' + repr(url))
        data = client.request(url)
        #log_utils.log('VIDSRC data: ' + data)
        links = re.findall('"src" , "(.+?)"', data) + re.findall("'player' src='(.+?)'", data) + re.findall('"file": "(.+?)"', data) + re.findall('data-h="(.+?)"', data)
        #log_utils.log('VIDSRC links: ' + repr(links))
        link = links[0]# + '|User-Agent=%s&Referer=https://v2.vidsrc.me/' % client.agent()
        url = link if link.startswith('http') else 'https://rcp.vidsrc.me/rcp/{0}'.format(link)
        #log_utils.log('VIDSRCurl: ' + repr(url))
        return url
