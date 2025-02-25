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

from blackscrapers import parse_qs, urlencode, quote_plus
from blackscrapers.modules import cleantitle, client, debrid, source_utils, log_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['eztvx.to', 'eztv.tf', 'eztv.yt', 'eztv1.xyz', 'eztv.wf']
        self.base_link = custom_base
        self.search_link = '/search/%s'
        self.aliases = []

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
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
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'].lower()
            hdlr = 's%02de%02d' % (int(data['season']), int(data['episode']))

            query = ' '.join((title, hdlr))
            query = self.search_link % (quote_plus(query).replace('+', '-'))

            try:
                r, self.base_link = client.list_client_request(self.base_link or self.domains, query=query, post={'layout': 'def_wlinks'})

                results = client.parseDOM(r, 'table', attrs={'class': 'forum_header_border'})
                results = [result for result in results if 'magnet:' in result]
                rows = client.parseDOM(results, 'tr', attrs={'class': 'forum_header_border'})
                if not rows:
                    return sources

                for entry in rows:
                    try:
                        try:
                            columns = re.findall(r'<td\s.+?>(.*?)</td>', entry, re.DOTALL)
                            derka = re.findall('href="magnet:(.+?)" class="magnet" title="(.+?)"', columns[2], re.DOTALL)[0]
                            name = derka[1].split('[eztv]')[0] if '[eztv]' in derka[1] else derka[1]
                            name = cleantitle.get_title(name)
                            if not source_utils.is_match(name, title, hdlr, self.aliases):
                                continue
                            link = 'magnet:%s' % derka[0].split('&tr')[0]
                        except Exception:
                            continue

                        quality, info = source_utils.get_release_quality(name)

                        try:
                            size = re.findall(r'((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', derka[1])[-1]
                            dsize, isize = source_utils._size(size)
                        except Exception:
                            dsize, isize = 0.0, ''
                        info.insert(0, isize)

                        info = ' | '.join(info)
                        sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en',
                                        'url': link, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                    except Exception:
                        continue
            except:
                pass

            for source in self.pack_sources(title, data['season'], data['episode']):
                sources.append(source)

            return sources
        except:
            log_utils.log('eztv_exc', 1)
            return sources

    def pack_sources(self, title, season, episode):
        _sources = []
        try:
            query = '%s s%02d' % (title.lower(), int(season))
            query = self.search_link % (quote_plus(query).replace('+', '-'))
            r, self.base_link = client.list_client_request(self.base_link or self.domains, query=query, post={'layout': 'def_wlinks'})

            results = client.parseDOM(r, 'table', attrs={'class': 'forum_header_border'})
            results = [result for result in results if 'magnet:' in result]
            rows = client.parseDOM(results, 'tr', attrs={'class': 'forum_header_border'})
            if not rows:
                return _sources

            for entry in rows:
                try:
                    try:
                        columns = re.findall(r'<td\s.+?>(.*?)</td>', entry, re.DOTALL)
                        derka = re.findall('href="magnet:(.+?)" class="magnet" title="(.+?)"', columns[2], re.DOTALL)[0]
                        name = derka[1].split('[eztv]')[0] if '[eztv]' in derka[1] else derka[1]
                        name = cleantitle.get_title(name)
                        if not source_utils.is_season_match(name, title, season, self.aliases):
                            continue
                        link = 'magnet:%s' % derka[0].split('&tr')[0]
                    except Exception:
                        continue

                    pack = '%s_%s' % (season, episode)
                    quality, info = source_utils.get_release_quality(name)

                    try:
                        size = re.findall(r'((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', derka[1])[-1]
                        dsize, isize = source_utils._size(size)
                    except Exception:
                        dsize, isize = 0.0, ''
                    info.insert(0, isize)

                    info = ' | '.join(info)
                    _sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': link, 'info': info,
                                     'direct': False, 'debridonly': True, 'size': dsize, 'name': name, 'pack': pack})
                except:
                    continue
            return _sources
        except:
            log_utils.log('eztv_pack_exc', 1)
            return _sources

    def resolve(self, url):
        return url
