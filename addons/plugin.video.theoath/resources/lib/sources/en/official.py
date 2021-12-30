# -*- coding: utf-8 -*-

'''
    TheOath Add-on (C) 2021
'''

import re
import requests
from six.moves.urllib_parse import parse_qs, urlencode
from resources.lib.modules import api_keys
from resources.lib.modules import control
from resources.lib.modules import source_utils
from resources.lib.modules import log_utils
from resources.lib.modules.justwatch import JustWatch


netflix_enabled = (control.condVisibility('System.HasAddon(plugin.video.netflix)') == True and control.setting('netflix') == 'true')
prime_enabled = (control.condVisibility('System.HasAddon(plugin.video.amazon-test)') == True and control.setting('prime') == 'true')
hbo_enabled = (control.condVisibility('System.HasAddon(slyguy.hbo.max)') == True and control.setting('hbo.max') == 'true')
disney_enabled = (control.condVisibility('System.HasAddon(slyguy.disney.plus)') == True and control.setting('disney.plus') == 'true')
iplayer_enabled = (control.condVisibility('System.HasAddon(plugin.video.iplayerwww)') == True and control.setting('iplayer') == 'true')
curstream_enabled = (control.condVisibility('System.HasAddon(slyguy.curiositystream)') == True and control.setting('curstream') == 'true')
hulu_enabled = (control.condVisibility('System.HasAddon(slyguy.hulu)') == True and control.setting('hulu') == 'true')
paramount_enabled = (control.condVisibility('System.HasAddon(slyguy.paramount.plus)') == True and control.setting('paramount') == 'true')

scraper_init = any(e for e in [netflix_enabled, prime_enabled, hbo_enabled, disney_enabled, iplayer_enabled, curstream_enabled, hulu_enabled, paramount_enabled])


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en', 'el']
        self.domains = []
        self.base_link = ''
        self.country = control.setting('official.country') or 'US'
        self.tm_user = control.setting('tm.user') or api_keys.tmdb_key
        self.tmdb_by_imdb = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', self.tm_user)
        self.aliases = []


    def movie(self, imdb, title, localtitle, aliases, year):
        if not scraper_init:
            return

        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if not scraper_init:
            return

        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return
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
            if url is None: return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = data['year']
            content = 'movie' if not 'tvshowtitle' in data else 'show'

            result = None

            jw = JustWatch(country=self.country)
            # r0 = jw.get_providers()
            # log_utils.log('justwatch {0} providers: {1}'.format(self.country, repr(r0)))

            if content == 'movie':
                tmdb = requests.get(self.tmdb_by_imdb % data['imdb']).json()
                tmdb = tmdb['movie_results'][0]['id']

                r = jw.search_for_item(query=title.lower())
                items = r['items']

                for item in items:
                    tmdb_id = item['scoring']
                    if tmdb_id:
                        tmdb_id = [t['value'] for t in tmdb_id if t['provider_type'] == 'tmdb:id']
                        if tmdb_id:
                            if tmdb_id[0] == tmdb:
                                result = item
                                break

            else:
                jw0 = JustWatch(country='US')
                r = jw0.search_for_item(query=title.lower())

                items = r['items']
                jw_id = [i for i in items if source_utils.is_match(' '.join((i['title'], str(i['original_release_year']))), title, year, self.aliases)]
                jw_id = [i['id'] for i in jw_id if i['object_type'] == 'show']
                if jw_id:
                    r = jw.get_episodes(str(jw_id[0]))
                    item = r['items']
                    item = [i for i in item if i['season_number'] == int(data['season']) and i['episode_number'] == int(data['episode'])]
                    if not item:
                        r = jw.get_episodes(str(jw_id[0]), page='2')
                        item = r['items']
                        item = [i for i in item if i['season_number'] == int(data['season']) and i['episode_number'] == int(data['episode'])]
                    if item:
                        result = item[0]

            #log_utils.log('justwatch result: ' + repr(result))

            if result:

                netflix = ['nfx', 'nfk']
                prime = ['amp', 'prv', 'aim']
                hbo = ['hmf', 'hbm', 'hbo', 'hbn']
                disney = ['dnp']
                iplayer = ['bbc']
                curstream = ['cts']
                hulu = ['hlu']
                paramount = ['pmp']

                offers = result['offers']
                #log_utils.log('justwatch offers: ' + repr(offers))

                streams = []

                if netflix_enabled:
                    try:
                        nfx = [o for o in offers if o['package_short_name'] in netflix]
                        if nfx:
                            netflix_id = nfx[0]['urls']['standard_web']
                            netflix_id = netflix_id.rstrip('/').split('/')[-1]
                            #log_utils.log('official netflix_id: ' + netflix_id)
                            streams.append(('netflix', 'plugin://plugin.video.netflix/play_strm/movie/%s/' % netflix_id))
                    except:
                        pass

                if prime_enabled:
                    try:
                        prv = [o for o in offers if o['package_short_name'] in prime]
                        if prv:
                            prime_id = prv[0]['urls']['standard_web']
                            prime_id = prime_id.rstrip('/').split('gti=')[1]
                            #log_utils.log('official prime_id: ' + prime_id)
                            streams.append(('amazon prime', 'plugin://plugin.video.amazon-test/?asin=%s&mode=PlayVideo&name=None&adult=0&trailer=0&selbitrate=0' % prime_id))
                    except:
                        pass

                if hbo_enabled:
                    try:
                        hbm = [o for o in offers if o['package_short_name'] in hbo]
                        if hbm:
                            hbo_id = hbm[0]['urls']['standard_web']
                            hbo_id = hbo_id.rstrip('/').split('/')[-1]
                            #log_utils.log('official hbo_id: ' + hbo_id)
                            streams.append(('hbo max', 'plugin://slyguy.hbo.max/?_=play&slug=' + hbo_id))
                    except:
                        pass

                if disney_enabled:
                    try:
                        dnp = [o for o in offers if o['package_short_name'] in disney]
                        if dnp:
                            disney_id = dnp[0]['urls']['deeplink_web']
                            disney_id = disney_id.rstrip('/').split('/')[-1]
                            #log_utils.log('official disney_id: ' + disney_id)
                            streams.append(('disney+', 'plugin://slyguy.disney.plus/?_=play&_play=1&content_id=' + disney_id))
                    except:
                        pass

                if iplayer_enabled:
                    try:
                        bbc = [o for o in offers if o['package_short_name'] in iplayer]
                        if bbc:
                            iplayer_id = bbc[0]['urls']['standard_web']
                            #log_utils.log('official iplayer_id: ' + iplayer_id)
                            streams.append(('bbc iplayer', 'plugin://plugin.video.iplayerwww/?url=%s&mode=202&name=null&iconimage=null&description=null&subtitles_url=&logged_in=False' % iplayer_id))
                    except:
                        pass

                if curstream_enabled:
                    try:
                        cts = [o for o in offers if o['package_short_name'] in curstream]
                        if cts:
                            cts_id = cts[0]['urls']['standard_web']
                            cts_id = cts_id.rstrip('/').split('/')[-1]
                            #log_utils.log('official cts_id: ' + cts_id)
                            streams.append(('curiosity stream', 'plugin://slyguy.curiositystream/?_=play&_play=1&id=' + cts_id))
                    except:
                        pass

                if hulu_enabled:
                    try:
                        hlu = [o for o in offers if o['package_short_name'] in hulu]
                        if hlu:
                            hulu_id = hlu[0]['urls']['standard_web']
                            hulu_id = hulu_id.rstrip('/').split('/')[-1]
                            #log_utils.log('official hulu_id: ' + hulu_id)
                            streams.append(('hulu', 'plugin://slyguy.hulu/?_=play&id=' + hulu_id))
                    except:
                        pass

                if paramount_enabled:
                    try:
                        pmp = [o for o in offers if o['package_short_name'] in paramount]
                        if pmp:
                            pmp_url = pmp[0]['urls']['standard_web']
                            pmp_id = pmp_url.split('?')[0].split('/')[-1] if content == 'movie' else re.findall('/video/(.+?)/', pmp_url)[0]
                            #log_utils.log('official pmp_url: {0} | pmp_id: {1}'.format(pmp_url, pmp_id))
                            streams.append(('paramount+', 'plugin://slyguy.paramount.plus/?_=play&id=' + pmp_id))
                    except:
                        pass

                if streams:
                    for s in streams:
                        sources.append({'source': s[0], 'quality': '1080p', 'language': 'en', 'url': s[1], 'direct': True, 'debridonly': False, 'official': True})

            return sources
        except:
            log_utils.log('Official scraper exc', 1)
            return sources


    def resolve(self, url):
        return url
