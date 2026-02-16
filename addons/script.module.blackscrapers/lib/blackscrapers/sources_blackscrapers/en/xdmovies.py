# -*- coding: utf-8 -*-

import re
import requests
from blackscrapers import parse_qs, urlencode, quote_plus
from blackscrapers.modules import source_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en', 'el']
        self.domains = ['xdmovies-stremio.hdmovielover.workers.dev']
        self.base_link = custom_base or 'https://xdmovies-stremio.hdmovielover.workers.dev'
        self.movieSearch_link = '/movie?imdbid=%s'
        self.tvSearch_link = '/series?imdbid=%s&s=%s&e=%s'
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
                files = requests.get(url, timeout=30).json()['streams']
            except:
                return sources

            if files:
                for file in files:
                    try:
                        parts = file['title']
                        name_part, info_part = parts.split('\n', 1)
                        name = name_part.strip()
                        url = file['url']
                        if 'video-downloads.googleusercontent' in url:
                            continue
                        url = url.replace('pixeldrain.dev/u/', 'pixeldrain.dev/api/file/')
                        try:
                            dsize = file['behaviorHints']['videoSize']
                            isize = source_utils.convert_size(dsize)
                        except:
                            try:
                                size_info = file.get('size','')
                                if size_info:
                                    rsize = re.search(r'([\d.]+)\s*(KB|MB|GB|TB)', size_info, re.IGNORECASE)
                                else:
                                    rsize = re.search(r'([\d.]+)\s*(KB|MB|GB|TB)', info_part, re.IGNORECASE)
                                value = float(rsize.group(1))
                                unit = rsize.group(2).upper()
                                multipliers = {
                                    'KB': 1024,
                                    'MB': 1024 ** 2,
                                    'GB': 1024 ** 3,
                                    'TB': 1024 ** 4,
                                }

                                size_bytes = int(value * multipliers[unit])
                                dsize = size_bytes
                                isize = source_utils.convert_size(dsize)
                            except:
                                dsize = 0
                                isize = ''
                        quality, info = source_utils.get_release_quality(name)
                        info.insert(0, isize)
                        info = ' | '.join(info)
                        # if quality == 'cam' and not 'tvshowtitle' in data: continue
                        sources.append({'source': 'direct', 'quality': quality, 'language': 'en', 'url': url, 'info': info, 
                                'direct': True, 'debridonly': False, 'name': name, 'size': dsize})
                    except:
                        pass

            return sources
        except:
            return sources

    def resolve(self, url):
        if 'download?url=' in url:
            session = requests.Session()
            hdrs = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}
            session.headers.update(hdrs)
            url = url.split('download?url=')[1]
            response = session.get(url, timeout=20)
            if response.status_code == 200:
                match = re.search(r'href\s*=\s*"(https://gamerxyt.com[^"]+)"', response.text, re.IGNORECASE | re.DOTALL)
                if match:
                    url = match.group(1)
                    response = session.get(url, timeout=20)
                    if response.status_code == 200:
                        match = re.compile(r'<a\s+href="([^"]+)"[^/]+/i> Download \[(.+?)\]', re.IGNORECASE | re.DOTALL).findall(response.text)
                        streams = []
                        for url, name in match:
                            if '10Gbps' in name:
                                continue
                            url = url.replace('pixeldrain.dev/u/', 'pixeldrain.dev/api/file/')
                            streams.append((url,name))
                        if len(streams)==1:
                            url = streams[0][0]
                        else:
                            from blackscrapers.modules import control
                            ret = control.selectDialog([x[1] for x in streams], heading='Select source')
                            if ret >= 0:
                                url = streams[ret][0]
                            else:
                                url = streams[0][0]
                        # url = streams[0][0]
        return url


