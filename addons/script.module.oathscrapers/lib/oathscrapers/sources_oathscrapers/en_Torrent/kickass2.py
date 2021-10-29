# -*- coding: UTF-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @tantrumdev wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################

# - Converted to py3/2 for TheOath


import re

import six

from oathscrapers import parse_qs, urlencode, unquote, quote_plus, unquote_plus
from oathscrapers.modules import cache, cleantitle, client, debrid, log_utils, source_utils

from oathscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['kick4ss.com', 'kickasstorrents.id', 'kickasstorrents.bz', 'kkickass.com', 'kkat.net', 'kickasst.net', 'thekat.cc', 'kickasshydra.net', 'kickass.onl', 'thekat.info', 'kickass.cm']
        self.base_link = custom_base
        self.search_link = '/usearch/%s'
        self.aliases = []

    def movie(self, imdb, title, localtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        if debrid.status() is False:
            return

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

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.get_query(title)
            hdlr = 's%02de%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = ' '.join((title, hdlr))
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|<|>|\|)', ' ', query)
            query = self.search_link % quote_plus(query)
            r, self.base_link = client.list_request(self.base_link or self.domains, query)
            if not r:
                return sources
            r = r.replace('&nbsp;', ' ')
            rows = client.parseDOM(r, 'tr', attrs={'id': 'torrent_latest_torrents'})
            if not rows:
                return sources

            for entry in rows:
                try:
                    link_name = client.parseDOM(entry, 'a', attrs={'title': 'Torrent magnet link'}, ret='href')[0]
                    link_name = link_name.split('url=')[1]
                    link_name = unquote_plus(link_name)

                    link = link_name.split('&tr=')[0]
                    name = unquote(link.split('&dn=')[1])

                    if not source_utils.is_match(name, title, hdlr, self.aliases):
                        continue

                    quality, info = source_utils.get_release_quality(name, link)

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', entry)[-1]
                        dsize, isize = source_utils._size(size)
                    except:
                        dsize, isize = 0.0, ''

                    info.insert(0, isize)

                    info = ' | '.join(info)

                    sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en',
                                    'url': link, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                except:
                    pass

            return sources
        except:
            log_utils.log('kickass_exc', 1)
            return sources

    def resolve(self, url):
        return url
