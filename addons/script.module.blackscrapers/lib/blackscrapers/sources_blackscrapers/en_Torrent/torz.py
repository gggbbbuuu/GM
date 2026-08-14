# -*- coding: utf-8 -*-

import simplejson as json
from blackscrapers import parse_qs, urlencode
from blackscrapers.modules import cleantitle
from blackscrapers.modules import client
from blackscrapers.modules import debrid
from blackscrapers.modules import source_utils
from blackscrapers.modules import log_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = [
            'stremthru.13377001.xyz',
            'stremthru.stremio.ru',
            'stremthrufortheweebs.midnightignite.me'
        ]
        self.base_link = custom_base or 'https://stremthru.13377001.xyz'
        self.aliases = []
        self.movieSearch_link = '/v0/torrents?sid=%s'
        self.tvSearch_link = '/v0/torrents?sid=%s:%s:%s'

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

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
            year = data['year']
            imdb = data['imdb']
            
            if 'tvshowtitle' in data:
                season = data['season']
                episode = data['episode']
                hdlr = 'S%02dE%02d' % (int(season), int(episode))
                api_url = '%s%s' % (self.base_link, self.tvSearch_link % (imdb, season, episode))
            else:
                season = None
                episode = None
                hdlr = year
                api_url = '%s%s' % (self.base_link, self.movieSearch_link % imdb)

            try:
                results = client.request(api_url, timeout='7')
                files = json.loads(results).get('data', {}).get('items', [])
            except:
                files = []

            for file in files:
                try:
                    hash = file.get('hash')
                    name = file.get('name')
                    if not hash or not name: continue

                    if not source_utils.is_match(name, title, hdlr, self.aliases):
                        continue

                    url_magnet = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)

                    quality, info = source_utils.get_release_quality(name, url_magnet)
                        
                    try:
                        size = float(file.get('size', 0)) / 1024 / 1024 / 1024
                        dsize, isize = source_utils._size('%s GB' % size)
                        info.insert(0, isize)
                    except:
                        dsize = 0.0
                        
                    info = ' | '.join(info)

                    sources.append({'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url_magnet,
                                    'info': info, 'direct': False, 'debridonly': True, 'name': name, 'size': dsize})
                except:
                    pass

            if 'tvshowtitle' in data and files:
                for source in self.pack_sources(files, title, season, episode):
                    sources.append(source)

            return sources
        except Exception as e:
            log_utils.log('torz_exc: %s' % str(e), 1)
            return sources

    def pack_sources(self, files, title, season, episode):
        sources = []
        for file in files:
            try:
                hash = file.get('hash')
                name = file.get('name')
                if not hash or not name: continue

                # Το Blacklodge is_season_match φιλτράρει το string με δική του ρουτίνα
                if not source_utils.is_season_match(name, title, season, self.aliases):
                    continue

                url_magnet = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)

                quality, info = source_utils.get_release_quality(name, url_magnet)

                try:
                    size = float(file.get('size', 0)) / 1024 / 1024 / 1024
                    dsize, isize = source_utils._size('%s GB' % size)
                    info.insert(0, isize)
                except:
                    dsize = 0.0

                info = ' | '.join(info)
                pack = '%s_%s' % (season, episode)

                sources.append({'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url_magnet,
                                'info': info, 'direct': False, 'debridonly': True, 'name': name, 'size': dsize, 'pack': pack})
            except:
                pass
        return sources

    def resolve(self, url):
        return url