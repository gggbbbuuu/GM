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
        self.domains = ['mediafusionfortheweebs.midnightignite.me']
        self.base_link = custom_base or 'https://mediafusionfortheweebs.midnightignite.me'
        self.movieSearch_link = '/%s/stream/movie/%s.json'
        self.tvSearch_link = '/%s/stream/series/%s:%s:%s.json'
        self.aliases = []

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
                    url = '%s%s' % (self.base_link, self.tvSearch_link % (self._token(), imdb, season, episode))
                else:
                    url = '%s%s' % (self.base_link, self.movieSearch_link % (self._token(), imdb))
                    hdlr = year
                
                results = client.request(url, timeout='7')
                if not results or any(value in results for value in SERVER_ERROR): return sources
                files = json.loads(results)['streams']
            except:
                log_utils.log('mediafusion_exc', 1)
                return sources

            if files:
                _INFO = re.compile(r'💾.*')
                for file in files:
                    try:
                        hash = file['infoHash']
                        file_title = file['description'].split('\n')
                        file_info = [x for x in file_title if _INFO.search(x)][0]

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
                        log_utils.log('mediafusion_exc', 1)
                        pass

                if 'tvshowtitle' in data:
                    for source in self.pack_sources(files, title, season, episode):
                        sources.append(source)

            return sources
        except:
            log_utils.log('mediafusion_exc', 1)
            return sources

    def pack_sources(self, files, title, season, episode):
        sources = []
        _INFO = re.compile(r'💾.*')
        for file in files:
            try:
                hash = file['infoHash']
                file_title = file['description'].split('\n')
                file_info = [x for x in file_title if _INFO.search(x)][0]

                name = cleantitle.get_title(file_title[0])
                if not source_utils.is_season_match(name, title, season, self.aliases):
                    continue

                url = 'magnet:?xt=urn:btih:%s' % hash

                quality, info = source_utils.get_release_quality(name)
                if quality == 'cam':
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
                log_utils.log('mediafusion_pack_exc', 1)
                pass
        return sources

    def resolve(self, url):
        return url

    def _token(self):
        return (
            'D-h5mpsX35oygOGFiHutl66dLAPiXzjQTODPXKQuKBaQOLjwNBbVkSPi7TJPr0gdykpCFREq8JOh'
            'DHZcvoS_UNZsWpsbjscCAwzgqc9VvP0S3Wt9lz5blcPT8lU6fcHdAHYctp_yde6nWKtSQ1O9Tjeh'
            'GNwajH9TjGZwn6rOybPFmoMpccXfTkB3Xwe9xRhT9O-bKzoYnGnlG8fCDxlNGdzrnlythePc3C7O'
            'phF8b5GyhuSnvBhxD7dTfkI77Dbay8_k_wqS-me9euZQ-oyOJBNTOIsO8HiWQhLGCC8m9rYsqJT6'
            'QF1Xhn-2bNzlukfbSYh_X1kOFdi6Y-YkBeEYokDlQHzzU45qmrj2b1Nz-GALcJHjNDJEMF3h9Eyx'
            '7UcmGWT1qvTpv_tcXjAX37ceqrWH-e_EqwVkvQDjNnmpjOhBWhuUW2R-0KbvxKUn1s5d2jZjLBxC'
            'bMotHIC-G2SrVCLgC_KV0OUainevUHKOKTe0CQmWz1HKV1ju52CFZFZYAWkOAX5cw55qzNnWl_nQ'
            'RnLyngrW_P6aYqghbYyyrAvQ6hCrIbSnVj4GsMFIelcMETvGW4jIXdwZGZA1L8gCzmyCbI9vAqPv'
            'dZxRWb7roc2EnB7gaSYdFtTP9gGoFKKkQ-9aircUEiPXjkP4QWO7lVI4GZri7KKCKjBM7-hWf4nm'
            'ttY7lJS_4Te_H80BeR_qpqeYQ6V0gpVwihARA6cIsZFbWmQXtoYNO16jt1ZqeVztwR6L1IQQnAsH'
            'ANyR5kF7ovGCOnhWlDDxO3nk8fhm3s0k7XewrMisZHy1zNsivTjvJW6KoVwghLn8-QCTf9PEPoPj'
            's6tW5KjciaRvbMg5-mbhpAhYOmPisB4ZyW63vWY6TeU1OBJV0T_fkHtgbvgiTEX5RFoRVDLnhaof'
            '-xHVw2oCc2AdXmBDVROmFjY8x9KEyZ91QfNjHnrTFmGetelcHE'
        )