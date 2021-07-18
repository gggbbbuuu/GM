# -*- coding: utf-8 -*-

import re

import simplejson as json
from oathscrapers import parse_qs, urlencode, quote_plus

from oathscrapers.modules import client
from oathscrapers.modules import cleantitle
from oathscrapers.modules import directstream
from oathscrapers.modules import source_utils
from oathscrapers.modules import log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['tunemovie.com', 'xmovies.is', '123movies.sc']
        self.base_link = 'https://tunemovie.com'
        self.search_link = '/search/%s.html'


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            query = self.base_link + self.search_link % quote_plus(title)
            check = cleantitle.get(title)
            r = client.request(query)
            r = client.parseDOM(r, 'div', attrs={'class': 'item_movie'}) # for the 123movies domain use client.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = [(client.parseDOM(i, 'a', ret='href'), client.parseDOM(i, 'a', ret='title'), re.findall('(\d{4})', i)) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            url = [i[0] for i in r if check == cleantitle.get(i[1]) and year == i[2]][0]
            url += '|%s' % imdb
            return url
        except Exception:
            log_utils.log('tunemovie Exception', 1)
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            log_utils.log('tunemovie Exception', 1)
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            query = self.base_link + self.search_link % quote_plus(data['tvshowtitle'])
            check = cleantitle.get(data['tvshowtitle'])
            r = client.request(query)
            r = client.parseDOM(r, 'div', attrs={'class': 'item_movie'}) # for the 123movies domain use client.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = [(client.parseDOM(i, 'a', ret='href'), client.parseDOM(i, 'a', ret='title'), re.findall('(\d{4})', i)) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            url = [i[0] for i in r if check in cleantitle.get(i[1]) and ('Season %s' % season) in i[1]][0]
            url += '?episode=%01d|%s' % (int(episode), data['imdb'])
            return url
        except Exception:
            log_utils.log('tunemovie Exception', 1)
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url == None:
                return sources
            imdb = url.split('|')[1]
            url = url.split('|')[0]
            try:
                url, episode = re.findall('(.+?)\?episode=(\d*)$', url)[0]
            except:
                episode = None
            #ref = url
            url += '?play=1'
            ref = url
            #log_utils.log('tunemovie sources starting url: \n' + repr(url))
            result = client.request(url)
            if not imdb in result:
                return sources
            if not episode == None:
                result = client.parseDOM(result, 'div', attrs={'id': 'ip_episode'})[0]
                ep_url = client.parseDOM(result, 'a', attrs={'data-name': str(episode)}, ret='href')[0]
                result = client.request(ep_url)
            r = client.parseDOM(result, 'div', attrs={'class': '[^"]*server_[^"]*'})
            for u in r:
                try:
                    url = self.base_link + '/ip.file/swf/plugins/ipplugins.php'
                    p1 = client.parseDOM(u, 'a', ret='data-film')[0]
                    p2 = client.parseDOM(u, 'a', ret='data-server')[0]
                    p3 = client.parseDOM(u, 'a', ret='data-name')[0]
                    post = {'ipplugins': 1, 'ip_film': p1, 'ip_server': p2, 'ip_name': p3, 'fix': "0"}
                    post = urlencode(post)
                    for i in range(3):
                        result = client.request(url, post=post, XHR=True, referer=ref, timeout='10')
                        if not result == None:
                            break
                    result = json.loads(result)
                    u = result['s']
                    try:
                        s = result['v']
                    except:
                        s = result['c']
                    url = self.base_link + '/ip.file/swf/ipplayer/ipplayer.php'
                    for n in range(3):
                        try:
                            post = {'u': u, 'w': '100%', 'h': '420', 's': s, 'n': n}
                            post = urlencode(post)
                            result = client.request(url, post=post, XHR=True, referer=ref)
                            src = json.loads(result)['data']
                            #log_utils.log('tunemovie sources src 1 list: \n' + repr(src))
                            if not src:
                                continue
                            if type(src) is list:
                                src = [i['files'] for i in src]
                                #log_utils.log('tunemovie sources src 1 list: \n' + repr(src))
                                for i in src:
                                    sources.append({'source': 'gvideo', 'quality': directstream.googletag(i)[0]['quality'], 'language': 'en', 'url': i, 'direct': True, 'debridonly': False})
                            else:
                                link = "https:" + src if not src.startswith('http') else src
                                #log_utils.log('tunemovie sources src link: \n' + repr(link))
                                if 'tunestream.net' in link:
                                    for source in self.tunestream(link, hostDict):
                                        sources.append(source)
                                else:
                                    valid, host = source_utils.is_host_valid(link, hostDict)
                                    if valid:
                                        sources.append({'source': host, 'quality': 'HD', 'language': 'en', 'url': link, 'direct': False, 'debridonly': False})
                        except:
                            log_utils.log('tunemovie Exception', 1)
                            pass
                except:
                    log_utils.log('tunemovie Exception', 1)
                    pass
            return sources
        except Exception:
            log_utils.log('tunemovie Exception', 1)
            return sources


# UnUsed Result, Needs Coded.
# 'https://waaw.tv/watch_video.php?v=e78cLgr5c392'


    def resolve(self, url):
        if 'google' in url:
            url = directstream.googlepass(url)
        return url


    def tunestream(self, url, hostDict):
        sources = [] # 'https://tunestream.net/embed-f1m4uqrfm987.html'
        try:
            header = {'User-Agent': client.agent(), 'Referer': 'https://tunestream.net'}
            page = client.request(url, headers=header)
            results = re.compile('sources\s*:\s*\[(.+?)\]').findall(page)[0]
            items = re.findall(r'''{(.+?)}''', results)
            for item in items:
                link = re.findall(r'''file:"(.+?)"''', item)[0]
                #log_utils.log('tunemovie tunestream: \n' + repr(link))
                try:
                    label = re.findall(r'''label:"(.+?)"''', item)[0]
                except:
                    label = 'SD'
                quality, info = source_utils.get_release_quality(label, link)
                link += '|%s' % urlencode(header)
                sources.append({'source': 'tunestream', 'quality': quality, 'language': 'en', 'info': info, 'url': link, 'direct': True, 'debridonly': False})
            return sources
        except Exception:
            log_utils.log('tunemovie Exception', 1)
            return sources


