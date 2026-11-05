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


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['stremthru.13377001.xyz', 'stremthru.stremio.ru', 'stremthrufortheweebs.midnightignite.me']
        self.base_link = custom_base# or 'https://stremthru.13377001.xyz'
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
            if not url:
                return sources
            if debrid.status() is False:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = data['year']
            imdb = data['imdb']

            if 'tvshowtitle' in data:
                season = data['season']
                episode = data['episode']
                hdlr = 'S%02dE%02d' % (int(season), int(episode))
                query = self.tvSearch_link % (imdb, season, episode)
            else:
                hdlr = year
                query = self.movieSearch_link % imdb

            try:
                r, self.base_link = client.list_request(self.base_link or self.domains, query)
                files = json.loads(r).get('data', {}).get('items', [])
            except:
                files = []

            if files:
                for file in files:
                    try:
                        hash = file['hash']
                        name = cleantitle.get_title(file.get('name'))
                        if not hash or not name:
                            continue

                        if not source_utils.is_match(name, title, hdlr, self.aliases):
                            continue

                        url_magnet = 'magnet:?xt=urn:btih:%s' % hash

                        quality, info = source_utils.get_release_quality(name)

                        try:
                            dsize, isize = source_utils._size(file['size'], is_bytes=True)
                        except:
                            dsize, isize = 0.0, ''

                        info.insert(0, isize)

                        info = ' | '.join(info)

                        sources.append({'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url_magnet,
                                        'info': info, 'direct': False, 'debridonly': True, 'name': name, 'size': dsize})
                    except:
                        pass

                if 'tvshowtitle' in data:
                    for source in self.pack_sources(files, title, season, episode):
                        sources.append(source)

            return sources
        except:
            log_utils.log('torz_exc', 1)
            return sources

    def pack_sources(self, files, title, season, episode):
        sources = []
        for file in files:
            try:
                hash = file['hash']
                name = cleantitle.get_title(file.get('name'))
                if not hash or not name:
                    continue

                if not source_utils.is_season_match(name, title, season, self.aliases):
                    continue
                #log_utils.log(file)

                url_magnet = 'magnet:?xt=urn:btih:%s' % hash

                quality, info = source_utils.get_release_quality(name)

                try:
                    episodes = file['files']
                    episodes = [e for e in episodes if any(e['p'].endswith(x) for x in source_utils.supported_video_extensions())]
                    try: s = [e['s'] for e in episodes if self.matchEpisode(e['n'], season, episode)][0]
                    except: s = file['size'] // len(episodes)
                    dsize, isize = source_utils._size(s, is_bytes=True)
                except:
                    dsize, isize = 0.0, ''

                info.insert(0, isize)

                info = ' | '.join(info)
                pack = '%s_%s' % (season, episode)

                sources.append({'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url_magnet,
                                'info': info, 'direct': False, 'debridonly': True, 'name': name, 'size': dsize, 'pack': pack})
            except:
                pass
        return sources

    def resolve(self, url):
        return url

    def matchEpisode(self, filename, season, episode):
        filename = re.sub('[^A-Za-z0-9 ]+', ' ', filename.split('/')[-1]).lower()
        r = r"(?:[a-z\s*]|^)(?:%s|%s)\s*(?:e|x|episode)\s*(?:%s|%s)\s+" % (season.zfill(2), season, episode.zfill(2), episode)
        m = re.search(r, filename, flags=re.S)

        if m:
            return True
