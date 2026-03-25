# -*- coding: utf-8 -*-
import re
import requests
from blackscrapers import urlencode, parse_qs, unquote

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['meowtv.vflix.shop']
        self.base_link = custom_base or 'https://meowtv.vflix.shop'
        self.movieSearch_link = '/stream/movie/%s.json'
        self.tvSearch_link = '/stream/series/%s:%s:%s.json'
        self.title_skip_re = r'meowtv\s+\[auto\]'
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def movie(self, *args, **kwargs):
        try:
            if len(args) == 5:
                imdb, title, localtitle, aliases, year = args
            elif len(args) >= 6:
                imdb, tmdb, title, localtitle, aliases, year = args[:6]
            else:
                imdb, title, year = args[0], args[1], args[-1]

            url = {'imdb': imdb, 'title': title, 'year': str(year), 'type': 'Movie'}
            return urlencode(url)
        except:
            return None

    def tvshow(self, *args, **kwargs):
        try:
            if len(args) == 6:
                imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year = args
            elif len(args) >= 7:
                imdb, tvdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year = args[:7]
            else:
                imdb, tvshowtitle, year = args[0], args[2], args[-1]

            url = {'imdb': imdb, 'title': tvshowtitle, 'year': str(year), 'type': 'TV'}
            return urlencode(url)
        except:
            return None

    def episode(self, *args, **kwargs):
        try:
            url = args[0]
            season = args[-2]
            episode = args[-1]

            if not url: 
                return None
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            data['season'] = str(season)
            data['episode'] = str(episode)
            return urlencode(data)
        except:
            return None

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if not url:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            imdb_id = data.get('imdb')
            type_ = data.get('type')
            
            if not imdb_id:
                return sources

            headers = {'User-Agent': self.user_agent}

            if type_ == 'TV':
                season = data.get('season', '0')
                episode = data.get('episode', '0')
                item_url = '%s%s' % (self.base_link, self.tvSearch_link % (imdb_id, season, episode))
            else:
                item_url = '%s%s' % (self.base_link, self.movieSearch_link % imdb_id)

            response = requests.get(item_url, headers=headers, timeout=10)
            if response.status_code != 200:
                return sources
                
            item = response.json()
            streams = item.get('streams', []) if isinstance(item, dict) else item

            if not streams:
                return sources

            for stream in streams:
                video_url = stream.get('url')
                if not video_url:
                    continue

                if 'hls?url=' in video_url:
                    video_url = unquote(video_url.split('hls?url=')[1])

                raw_title = stream.get('title', '') or stream.get('name', '')

                # Έλεγχος για να κάνει skip τα ανεπιθύμητα αποτελέσματα (πχ "meowtv [auto]")
                if self.title_skip_re and re.search(self.title_skip_re, raw_title, re.IGNORECASE):
                    continue

                if 'video-downloads.googleusercontent' in video_url:
                    continue

                video_url = video_url.replace('pixeldrain.dev/u/', 'pixeldrain.dev/api/file/')

                name = stream.get('name', 'MeowTV')
                if name == 'MultiStream':
                    name = video_url.split('/')[2]
                    
                release_name = raw_title.split("\n")[0].strip()

                # Καθορισμός του παρόχου 
                provider = ''
                if 'MEOWTV' in release_name.upper():
                    provider = 'MeowTV'
                else:
                    provider_raw = stream.get('behaviorHints', {}).get('bingeGroup', name)
                    if isinstance(provider_raw, str):
                        provider_parts = provider_raw.lower().split('-')
                        if len(provider_parts) > 2:
                            provider = provider_parts[2].strip().capitalize()
                        else:
                            provider = provider_parts[0].strip().capitalize()
                
                if not provider:
                    provider = 'MeowTV'

                # Καθορισμός της ποιότητας με τον ειδικό κανόνα του MeowTV
                quality = '1080p'
                if provider.lower() == 'meowtv':
                    quality = stream.get('description', '1080p').split(' ')[-1].strip()
                else:
                    quality_raw = stream.get('resolution')
                    if not quality_raw:
                        if '4k' in raw_title.lower() or '2160' in raw_title:
                            quality = '4K'
                        elif '1080' in raw_title:
                            quality = '1080p'
                        elif '720' in raw_title:
                            quality = '720p'
                    else:
                        quality = quality_raw

                sources.append({
                    'source': provider,
                    'quality': quality,
                    'language': 'en',
                    'url': f"{video_url}|User-Agent={self.user_agent}",
                    'direct': True,
                    'debridonly': False
                })

            return sources
        except Exception as e:
            return sources

    def resolve(self, url):
        return url