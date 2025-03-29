# -*- coding: utf-8 -*-
# Blackscrapers module - based on a Scrubs scraper


import re
import requests

from blackscrapers import parse_qs, urlencode

from blackscrapers.modules import client
from blackscrapers.modules import cleantitle
from blackscrapers.modules import debrid
from blackscrapers.modules import source_utils
from blackscrapers.modules import log_utils


from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['swatchfree.in', 'swatchfree.me']
        self.base_link = custom_base or 'https://swatchfree.in'
        self.search_link = '/?s=%s'
        self.ajax_link = '/wp-admin/admin-ajax.php'
        self.session = requests.Session()
        self.aliases = []


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def tvshow(self, imdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def episode(self, url, imdb, tmdb, title, premiered, season, episode):
        try:
            if not url:
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
            if debrid.status() is True:
                return sources
            if url == None:
                return sources
            #hostDict = hostprDict + hostDict
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            search_url = self.base_link + self.search_link % cleantitle.get_title(title, sep='+').lower()
            html = client.request(search_url, verify=False)
            results = client.parseDOM(html, 'div', attrs={'class': 'result-item'})
            results = [(client.parseDOM(i, 'a', ret='href'), client.parseDOM(i, 'img', ret='alt'), client.parseDOM(i, 'span', attrs={'class': 'year'})) for i in results]
            results = [(i[0][0], i[1][0], i[2][0]) for i in results if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            result_url = [i[0] for i in results if source_utils.is_match('.'.join((i[1], i[2])), title, data['year'], self.aliases)][0]
            if 'tvshowtitle' in data:
                check = '-%sx%s' % (season, episode)
                html = client.request(result_url, verify=False)
                results = client.parseDOM(html, 'div', attrs={'class': 'episodiotitle'})
                results = [(client.parseDOM(i, 'a', ret='href')) for i in results]
                result_url = [i[0] for i in results if check in i[0]][0]
            html = client.request(result_url, verify=False)
            try:
                qual = client.parseDOM(html, 'strong', attrs={'class': 'quality'})[0]
            except:
                qual = 'SD'
            customheaders = {
                'Host': self.domains[0],
                'Accept': '*/*',
                'Origin': self.base_link,
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': client.agent(),
                'Referer': result_url,
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            post_link = self.base_link + self.ajax_link
            try:
                results = re.compile(r"data-type='(.+?)' data-post='(.+?)' data-nume='(\d+)'>", re.DOTALL).findall(html)
                for data_type, data_post, data_nume in results:
                    try:
                        payload = {'action': 'doo_player_ajax', 'post': data_post, 'nume': data_nume, 'type': data_type}
                        r = self.session.post(post_link, headers=customheaders, data=payload)
                        i = r.json()
                        if not i['type'] == 'iframe':
                            continue
                        p = i['embed_url'].replace('\\', '')
                        if 'imdb.com' in p:
                            continue
                        valid, host = source_utils.is_host_valid(p, hostDict)
                        if valid:
                            sources.append({'source': host, 'quality': 'sd', 'language': 'en', 'url': p, 'direct': False, 'debridonly': False})
                    except:
                        #log_utils.log('swatchfree', 1)
                        pass
            except:
                #log_utils.log('swatchfree', 1)
                pass
            try:
                tbody = client.parseDOM(html, 'tbody')[0]
                tr = client.parseDOM(html, 'tr')
                downloads = [(client.parseDOM(i, 'a', attrs={'target': '_blank'}, ret='href'), client.parseDOM(i, 'strong', attrs={'class': 'quality'})) for i in tr]
                downloads = [(i[0][0], i[1][0]) for i in downloads if len(i[0]) > 0 and len(i[1]) > 0]
                for download in downloads:
                    try:
                        download_link = self.base_link + download[0] if not download[0].startswith('http') else download[0]
                        download_link = client.request(download_link, timeout='6', output='geturl', verify=False)
                        if any(i in download_link for i in self.domains):
                            download_html = client.request(download_link, verify=False)
                            download_link = client.parseDOM(download_html, 'a', attrs={'id': 'link'}, ret='href')[0]
                        valid, host = source_utils.is_host_valid(download_link, hostDict)
                        if valid:
                            sources.append({'source': host, 'quality': 'sd', 'language': 'en', 'url': download_link, 'direct': False, 'debridonly': False})
                    except:
                        #log_utils.log('swatchfree', 1)
                        pass
            except:
                #log_utils.log('swatchfree', 1)
                pass
            return sources
        except:
            log_utils.log('swatchfree', 1)
            return sources


    def resolve(self, url):
        return url


