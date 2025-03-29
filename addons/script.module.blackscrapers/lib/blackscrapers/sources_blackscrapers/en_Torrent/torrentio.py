# -*- coding: utf-8 -*-

import re
import simplejson as json
from blackscrapers import parse_qs, urlencode
from blackscrapers.modules import cleantitle
from blackscrapers.modules import client
from blackscrapers.modules import debrid
from blackscrapers.modules import source_utils
from blackscrapers.modules import log_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)

SERVER_ERROR = ('521 Origin Down', 'No results returned', 'Connection Time-out', 'Database maintenance')

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en', 'el']
        self.domains = ['torrentio.strem.fun']
        self.base_link = custom_base or 'https://torrentio.strem.fun'
        self.movieSearch_link = '/providers=yts,eztv,rarbg,1337x,thepiratebay,kickasstorrents,torrentgalaxy,magnetdl,nyaasi|language=english/stream/movie/%s.json'
        self.tvSearch_link = '/providers=yts,eztv,rarbg,1337x,thepiratebay,kickasstorrents,torrentgalaxy|language=english/stream/series/%s:%s:%s.json'
        self.aliases = []
        # Currently supports YTS(+), EZTV(+), RARBG(+), 1337x(+), ThePirateBay(+), KickassTorrents(+), TorrentGalaxy(+), HorribleSubs(+), NyaaSi(+), NyaaPantsu(+), Rutor(+), Comando(+), ComoEuBaixo(+), Lapumia(+), OndeBaixa(+), Torrent9(+).

    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
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
            if not url: return sources
            if debrid.status() is False:
                return sources

            try:
                data = parse_qs(url)
                data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

                title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
                year = data['year']
                imdb = data['imdb']
                if 'tvshowtitle' in data:
                    season = data['season']
                    episode = data['episode']
                    hdlr = 'S%02dE%02d' % (int(season), int(episode))
                    url = '%s%s' % (self.base_link, self.tvSearch_link % (imdb, season, episode))
                else:
                    url = '%s%s' % (self.base_link, self.movieSearch_link % imdb)
                    hdlr = year
                #log_utils.log('torrentio_url: ' + url)
                results = client.request(url, timeout='7')
                if not results or any(value in results for value in SERVER_ERROR): return sources
                files = json.loads(results)['streams']
            except:
                log_utils.log('torrentio_exc', 1)
                return sources

            if files:
                for file in files:
                    try:
                        #log_utils.log(repr(file))
                        hash = file['infoHash']
                        file_title = file['title'].split('\n')
                        file_info = [x for x in file_title if re.compile(r'👤.*').match(x)][0]

                        name = cleantitle.get_title(file_title[0])
                        if not source_utils.is_match(name, title, hdlr, self.aliases):
                            continue

                        url = 'magnet:?xt=urn:btih:%s' % hash

                        quality, info = source_utils.get_release_quality(name)
                        if quality == 'cam' and not 'tvshowtitle' in data:
                            continue
                        try:
                            size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', file_info).group(0)
                            dsize, isize = source_utils._size(size)
                        except:
                            dsize, isize = 0.0, ''
                        info.insert(0, isize)
                        info = ' | '.join(info)

                        sources.append({'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url,
                                        'info': info, 'direct': False, 'debridonly': True, 'name': name, 'size': dsize})
                    except:
                        log_utils.log('torrentio_exc', 1)
                        pass

                if 'tvshowtitle' in data:
                    for source in self.pack_sources(files, title, season, episode):
                        sources.append(source)

            return sources
        except:
            log_utils.log('torrentio_exc', 1)
            return sources

    def pack_sources(self, files, title, season, episode):
        sources = []
        for file in files:
            try:
                hash = file['infoHash']
                file_title = file['title'].split('\n')
                file_info = [x for x in file_title if re.compile(r'👤.*').match(x)][0]

                name = cleantitle.get_title(file_title[0])
                if not source_utils.is_season_match(name, title, season, self.aliases):
                    continue

                url = 'magnet:?xt=urn:btih:%s' % hash

                quality, info = source_utils.get_release_quality(name)
                if quality == 'cam' and not 'tvshowtitle' in data:
                    continue
                try:
                    size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', file_info).group(0)
                    dsize, isize = source_utils._size(size)
                except:
                    dsize, isize = 0.0, ''
                info.insert(0, isize)
                info = ' | '.join(info)
                pack = '%s_%s' % (season, episode)

                sources.append({'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url,
                                'info': info, 'direct': False, 'debridonly': True, 'name': name, 'size': dsize, 'pack': pack})
            except:
                log_utils.log('torrentio_pack_exc', 1)
                pass
        return sources


    def resolve(self, url):
        return url

