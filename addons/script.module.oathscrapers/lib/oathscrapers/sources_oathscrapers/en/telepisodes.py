# -*- coding: UTF-8 -*-
# -Cleaned and Checked on 10-16-2019 by JewBMX in Scrubs.
# -Fixed and py2/3 compat for TheOath - June 2021

import re

from six import ensure_text

from oathscrapers import cfScraper
from oathscrapers.modules import client
from oathscrapers.modules import cleantitle
from oathscrapers.modules import source_utils
from oathscrapers.modules import log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['telepisodes.org']
        self.base_link = 'https://www1.telepisodes.org/'
        self.tvshow_link = 'tv-series/%s/season-%s/episode-%s/'
        self.headers = {'User-Agent': client.randomagent(), 'Referer': self.base_link}


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
            url = self.base_link + self.tvshow_link % (url, season, episode)
            #log_utils.log('telepisodes_search: ' + repr(url))
            return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url == None:
                return sources
            hostDict = hostprDict + hostDict
            page = cfScraper.get(url, headers=self.headers).text
            match = re.compile(r'rel="nofollow ugc" title="(.+?)" target="_blank" href="(.+?)">', re.I|re.S).findall(page)
            for hoster, link in match:
                url = self.base_link + link
                valid, host = source_utils.is_host_valid(hoster, hostDict)
                if valid:
                    sources.append({'source': host, 'quality': 'SD', 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})
            return sources
        except:
            log_utils.log('telepisodes_exc:', 1)
            return sources


    def resolve(self, url):
        try:
            page2 = cfScraper.get(url, headers=self.headers).text
            match2 = re.compile(r'href="/open/site/(.+?)"', re.I|re.S).findall(page2)[0]
            link2 = self.base_link + "open/site/" + match2
            link3 = ensure_text(cfScraper.get(link2, timeout=10).url, errors='replace')
            return link3
        except:
            log_utils.log('telepisodes_res:', 1)
            return


