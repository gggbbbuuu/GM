# -*- coding: utf-8 -*-
import re
import requests
from blackscrapers import urlparse, quote_plus, urlencode, parse_qs
from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['flixhq.to']
        self.base_link = custom_base or 'https://flixhq.to'
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.headers = {
            "Referer": self.base_link+'/',
            "User-Agent": self.user_agent,
            "Origin": self.base_link,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }

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

            title = data.get('title')
            year = data.get('year')
            type_ = data.get('type')

            post_data = f"keyword={quote_plus(title)}"
            query_url = f"{self.base_link}/ajax/search"
            
            search_response = requests.post(query_url, headers=self.headers, data=post_data, timeout=10)
            if search_response.status_code != 200:
                return sources
                
            results = re.split(r'</div>\s*</a>', search_response.text)

            video_url = None
            for result in results:
                match = re.search(r'<a\s+href="/([^"]+)"', result, flags=re.DOTALL | re.IGNORECASE)
                if not match: continue
                temp_url = self.base_link+ '/' + match.group(1)

                match_type = re.search(r'<span>(TV|Movie)</span>', result, flags=re.DOTALL | re.IGNORECASE)
                qtype = match_type.group(1) if match_type else ''

                if qtype.lower() != type_.lower():
                    continue

                if type_ == 'Movie':
                    match_year = re.search(r'<div class="film-infor">\s*<span>(\d+)</span>', result, flags=re.DOTALL | re.IGNORECASE)
                    qyear = match_year.group(1) if match_year else ''
                    if year and qyear and year != qyear:
                        continue
                
                video_url = temp_url
                break

            if not video_url:
                return sources

            item_id = video_url.split('-')[-1]

            if type_ == 'TV':
                season_num = data.get('season')
                episode_num = data.get('episode')
                seasonsurl = self.base_link + '/ajax/season/list/' + item_id
                seasonshtml = requests.get(seasonsurl, headers=self.headers, timeout=10).text
                match_season = re.compile(rf'href="#ss-episodes-(\d+)">Season\s*{season_num}', re.DOTALL | re.IGNORECASE).findall(seasonshtml)
                if not match_season:
                    return sources
                seasonid = match_season[0]

                episodeurl = self.base_link + '/ajax/season/episodes/' + seasonid
                episodehtml = requests.get(episodeurl, headers=self.headers, timeout=10).text
                match_ep = re.compile(rf'data-id="(\d+)"[^_]+?alt="Episode\s*0*{episode_num}"', re.DOTALL | re.IGNORECASE).findall(episodehtml) or \
                           re.compile(rf'data-id="(\d+)"[^>]+?title="Eps\s*0*{episode_num}', re.DOTALL | re.IGNORECASE).findall(episodehtml)
                if not match_ep:
                    return sources
                item_id = match_ep[0]

            serverurl = self.base_link + ('/ajax/episode/list/' + item_id if type_ == 'Movie' else '/ajax/episode/servers/' + item_id)
            serverhtml = requests.get(serverurl, headers=self.headers, timeout=10).text
            match_servers = re.compile(r'(?:data-linkid|data-id)="(\d+)".+?<span>([^<]+)<', re.DOTALL | re.IGNORECASE).findall(serverhtml)

            for serverid, servername in match_servers:
                if servername not in ('UpCloud', 'MegaCloud', 'Vidcloud'):
                    continue

                provider_url = self.base_link + '/ajax/episode/sources/' + serverid
                sources.append({
                    'source': servername,
                    'quality': '1080p',
                    'language': 'en',
                    'url': provider_url,
                    'direct': True,
                    'debridonly': False
                })
            
            return sources
        except:
            return sources

    def resolve(self, url):
        base_url = requests.get(url, headers=self.headers, timeout=10).json().get('link')
        if not base_url:
            return

        parsed_url = urlparse(base_url)
        default_domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        
        embed_headers = {
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": default_domain,
            "User-Agent": self.user_agent
        }
        response = requests.get(base_url, headers=embed_headers, timeout=10).text

        match_file = re.search(r'player" data-id="(\w+)"', response)
        if not match_file:
            return
        file_id = match_file.group(1)

        match_nonce = re.search(r'\b[a-zA-Z0-9]{48}\b', response) or re.search(r'\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b', response)
        if not match_nonce:
            return
        
        nonce = ''.join(match_nonce.groups()) if match_nonce and match_nonce.lastindex == 3 else match_nonce.group()
        
        embed_link = f'{default_domain}embed-1/v3/e-1/getSources?id={file_id}&_k={nonce}'
        embed_response = requests.get(embed_link, headers=embed_headers, timeout=10).json()
        if 'sources' in embed_response and embed_response['sources']:
            url = embed_response['sources'][0].get('file')
            if url:
                url = f"{url}|Referer={default_domain}"
                return url
        return