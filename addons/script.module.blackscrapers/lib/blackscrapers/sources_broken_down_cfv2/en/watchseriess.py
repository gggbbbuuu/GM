# -*- coding: utf-8 -*-

# OathScrapers module


from blackscrapers.modules import client
from blackscrapers.modules import cleantitle
#from blackscrapers.modules import debrid
from blackscrapers.modules import source_utils
from blackscrapers.modules import log_utils
from blackscrapers import urljoin
#from blackscrapers import cfScraper

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)



class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['watchseriess.io']
        self.base_link = custom_base or 'https://watchmovie.ac'
        self.tvshow_link = '/series/%s-season-%s-episode-%s'
        self.headers = {'User-Agent': client.randomagent(), 'Referer': self.base_link}


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            url = urljoin(self.base_link, '/series/%s-episode-0' % cleantitle.geturl(title))
            return url
        except:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = cleantitle.geturl(tvshowtitle)
            return url
        except:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return
            url = urljoin(self.base_link, self.tvshow_link % (url, season, episode))
            return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            # if debrid.status() is True:
                # return sources
            if url == None:
                return sources
            hostDict = hostprDict + hostDict
            #r = cfScraper.get(url, headers=self.headers, timeout=10).text
            r = client.request(url, headers=self.headers)
            #log_utils.log(r)
            links = client.parseDOM(r, 'div', attrs={'class': 'anime_muti_link'})[0]
            links = client.parseDOM(links, 'li')[1:]
            for link in links:
                try:
                    url = client.parseDOM(link, 'a', ret='data-video')[0]
                    url = 'https:%s' % url if url.startswith('//') else url
                    quality, _ = source_utils.get_release_quality(url)
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})
                except:
                    pass
            return sources
        except:
            log_utils.log('watchseriess_exc:', 1)
            return sources


    def resolve(self, url):
        return url


