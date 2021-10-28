# -*- coding: UTF-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @tantrumdev wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################

# fixed and added multi-domain check support  for TheOath - 8/21


import re

from oathscrapers import cfScraper
from oathscrapers import parse_qs, urljoin, urlparse, urlencode, quote_plus
from oathscrapers.modules import cleantitle, client, debrid, log_utils, source_utils

from oathscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['rlsbb.ru', 'rlsbb.to', 'releasebb.net', 'proxybb.com'] # cf: 'rlsbb.unblockit.ch'
        self.base_link = custom_base # or 'https://rlsbb.to'
        #self.search_base_link = 'http://search.rlsbb.ru'
        #self.search_cookie = 'serach_mode=rlsbb'
        #self.search_link = 'lib/search526049.php?phrase=%s&pindex=1&content=true'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('RLSBB - Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('RLSBB - Exception', 1)
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            log_utils.log('RLSBB - Exception', 1)
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:

            if url is None:
                return sources

            if debrid.status() is False:
                return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = re.findall('(\d{4})', data['premiered'])[0] if 'tvshowtitle' in data else data['year']
            title = cleantitle.get_query(title)
            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year
            aliases = data['aliases']
            #premDate = ''

            query = '%s S%02dE%02d' % (title, int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (title, year)
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
            query = query.replace(" ", "-")
            #query = self.search_link % quote_plus(query)

            if int(year) < 2021:
                for i, d in enumerate(self.domains):
                    self.domains[i] = 'old3.' + d
                self.base_link = None

            r, _base_link = client.list_request(self.base_link or self.domains, query)

            if not r and 'tvshowtitle' in data:
                season = re.search('S(.*?)E', hdlr)
                season = season.group(1)
                query = title
                query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
                query = query + "-S" + season
                query = query.replace("&", "and")
                query = query.replace("  ", " ")
                query = query.replace(" ", "-")
                r, _base_link = client.list_request(self.base_link or self.domains, query)

            for loopCount in range(0, 2):
                if loopCount == 1 or (r is None and 'tvshowtitle' in data):

                    #premDate = re.sub('[ \.]', '-', data['premiered'])
                    query = re.sub(r'[\\\\:;*?"<>|/\-\']', '', title)
                    query = query.replace(
                        "&", " and ").replace(
                        "  ", " ").replace(
                        " ", "-")  # throw in extra spaces around & just in case
                    #query = query + "-" + premDate

                    url = urljoin(_base_link, query)

                    r = cfScraper.get(url).text

                entry_title = client.parseDOM(r, "h1", attrs={"class": "entry-title"})[0]
                if not source_utils.is_match(entry_title, title, hdlr, aliases):
                    continue

                posts = client.parseDOM(r, "div", attrs={"class": "content"})
                items = []
                for post in posts:
                    try:
                        u = client.parseDOM(post, 'a', ret='href')
                        for i in u:
                            try:
                                if not i.endswith(('.rar', '.zip', '.iso', '.idx', '.sub', '.srt', '.ass', '.ssa')) \
                                and not any(x in i for x in ['.rar.', '.zip.', '.iso.', '.idx.', '.sub.', '.srt.', '.ass.', '.ssa.']):
                                    items.append(i)
                                #elif len(premDate) > 0 and premDate in i.replace(".", "-"):
                                    #items.append(i)
                            except:
                                pass
                    except:
                        pass

                if len(items) > 0:
                    break

            seen_urls = set()

            for item in items:
                try:
                    url = item.replace("\\", "").strip('"')

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    name = url.split('/')[-1]
                    name = name if cleantitle.get(title) in cleantitle.get(name) else None
                    if not name:
                        continue

                    quality, info = source_utils.get_release_quality(name)
                    info = ' | '.join(info)

                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url,
                                        'info': info, 'direct': False, 'debridonly': True, 'name': name})
                except:
                    log_utils.log('RLSBB - Exception', 1)
                    pass

            return sources
        except:
            log_utils.log('RLSBB - Exception', 1)
            return sources

    def resolve(self, url):
        return url
