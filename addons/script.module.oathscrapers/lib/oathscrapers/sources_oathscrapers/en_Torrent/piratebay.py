# -*- coding: utf-8 -*-

#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @tantrumdev wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################

import re

from oathscrapers import parse_qs, urljoin, urlencode, quote, unquote_plus
from oathscrapers.modules import cache
from oathscrapers.modules import cleantitle
from oathscrapers.modules import client
from oathscrapers.modules import debrid
from oathscrapers.modules import source_utils
from oathscrapers.modules import log_utils

from oathscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['tpb.party', 'pirateproxy.live', 'thepiratebay10.org', 'thehiddenbay.com', 'thepiratebay.zone', 'proxybay.store', 'thepiratebay.party',
                        'piratebay.party', 'piratebay.live', 'piratebayproxy.live']
        self.base_link = custom_base# or 'piratebayproxy.live'
        # self.search_link = '/s/?q=%s&page=1&&video=on&orderby=99' #-page flip does not work
        self.search_link = '/search/%s/1/99/200' #-direct link can flip pages
        self.aliases = []


    def movie(self, imdb, title, localtitle, aliases, year):
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
            if url is None:
                return
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

            if debrid.status() is False:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.get_query(title)

            hdlr = 's%02de%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = ' '.join((title, hdlr))
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)

            query = self.search_link % quote(query)
            r, self.base_link = client.list_request(self.base_link or self.domains, query)
            r = r.replace('&nbsp;', ' ')

            try:
                results = client.parseDOM(r, 'table', attrs={'id': 'searchResult'})
            except:
                return sources

            url2 = urljoin(self.base_link, query.replace('/1/', '/2/'))

            try:
                html2 = client.request(url2)
                html2 = html2.replace('&nbsp;', ' ')
                results += client.parseDOM(html2, 'table', attrs={'id': 'searchResult'})
            except:
                pass

            results = ''.join(results)

            rows = re.findall('<tr(.+?)</tr>', results, re.DOTALL)
            if rows is None:
                return sources

            for entry in rows:
                try:
                    try:
                        url = 'magnet:%s' % (re.findall('a href="magnet:(.+?)"', entry, re.DOTALL)[0])
                        url = str(client.replaceHTMLCodes(url).split('&tr')[0])
                    except:
                        continue

                    name = client.parseDOM(entry, 'td')[1]
                    name = client.parseDOM(name, 'a')[0]

                    if not source_utils.is_match(name, title, hdlr, self.aliases):
                        continue

                    quality, info = source_utils.get_release_quality(name, url)

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', entry)[-1]
                        dsize, isize = source_utils._size(size)
                    except:
                        dsize, isize = 0.0, ''
                    info.insert(0, isize)

                    info = ' | '.join(info)

                    sources.append({'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url,
                                    'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                except:
                    log_utils.log('tpb_exc', 1)
                    continue

            return sources

        except:
            log_utils.log('tpb_exc', 1)
            return sources


    def resolve(self, url):
        return url