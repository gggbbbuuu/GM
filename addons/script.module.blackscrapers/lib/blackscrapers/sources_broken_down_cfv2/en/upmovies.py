# -*- coding: utf-8 -*-

'''
    BlackScrapers module
'''


import re, base64

import six

from blackscrapers import parse_qs, urljoin, urlparse, urlencode, quote_plus
from blackscrapers.modules import client, cleantitle, source_utils, log_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['upmovies.to', 'upmovies.net']
        self.base_link = custom_base or 'https://upmovies.net'
        self.search_link = '/search-movies/%s.html'
        self.aliases = []

    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year}
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
            if url is None: return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            hdlr = 'Season %d' % int(data['season']) if 'tvshowtitle' in data else data['year']
            query = ' '.join((title, hdlr))
            query = quote_plus(query)
            query = self.search_link % query

            url = urljoin(self.base_link, query)
            #log_utils.log('upmovies_url: ' + url)
            r = client.request(url)
            items = client.parseDOM(r, 'div', attrs={'class': 'category'})[0]
            items = client.parseDOM(items, 'div', attrs={'class': 'itemInfo'})

            if not 'tvshowtitle' in data:
                items = [(client.parseDOM(i, 'a')[0], re.findall('<p>Year: (.*?)</p>', i)[0], client.parseDOM(i, 'a', ret='href')[0]) for i in items]
                item = [i for i in items if source_utils.is_match(' '.join((i[0], i[1])), title, hdlr, self.aliases)][0]
                url2 = item[2]
            else:
                items = [(client.parseDOM(i, 'a')[0], client.parseDOM(i, 'a', ret='href')[0]) for i in items]
                item = [i for i in items if i[0].endswith(hdlr) and source_utils.is_match(i[0].split(hdlr)[0], title, aliases=self.aliases)][0]
                if data['episode'] == '1':
                    url2 = item[1]
                else:
                    r = client.request(item[1])
                    episodes = client.parseDOM(r, 'div', attrs={'id': 'details', 'class': 'section-box'})[0]
                    episodes = zip(client.parseDOM(episodes, 'a'), client.parseDOM(episodes, 'a', ret='href'))
                    episodes = [(i[0], i[1]) for i in episodes]
                    episode = [i for i in episodes if i[0] == data['episode']][0]
                    url2 = episode[1]

            #log_utils.log('upmovies_url2: ' + url2)
            r = client.request(url2)
            items = client.parseDOM(r, 'div', attrs={'id': 'total_version'})[0]
            items = client.parseDOM(items, 'p', attrs={'class': 'server_servername'})
            for item in items:
                try:
                    host = client.parseDOM(item, 'a')[0]
                    host = host.split('Server ')[1].split('Link')[0].strip().lower()
                    if host == 'vip': host = 'eplayvid'
                    elif host == 'voesx': host = 'voe'
                    valid, host = source_utils.is_host_valid(host, hostDict)
                    if valid:
                        url = client.parseDOM(item, 'a', ret='href')[0]
                        sources.append({'source': host, 'quality': 'sd', 'language': 'en', 'url': url,
                                        'direct': False, 'debridonly': False})
                except:
                    pass

            return sources
        except:
            log_utils.log('upmovies Exception', 1)
            return sources

    def resolve(self, url):
        if url.startswith(self.base_link) or any(x in url for x in self.domains):
            try:
                r = client.request(url)
                try:
                    v = re.findall(r'document.write\(Base64.decode\("(.+?)"\)', r)[0]
                    b64 = base64.b64decode(v)
                    b64 = six.ensure_text(b64, errors='ignore')
                    try:
                        url = client.parseDOM(b64, 'iframe', ret='src')[0]
                    except:
                        url = client.parseDOM(b64, 'a', ret='href')[0]
                    url = url.replace('///', '//')
                except:
                    u = client.parseDOM(r, 'div', attrs={'class': 'player'})[0]
                    url = client.parseDOM(u, 'a', ret='href')[0]
            except:
                log_utils.log('upmovies resolve Exception', 1)
            return url
        else:
            return url

