# -*- coding: utf-8 -*-

import re

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['cinebox.cc']
        self.base_link = 'https://cinebox.cc'
        self.search_link = '/search/%s'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        url = {'imdb': imdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def episode(self, url, imdb, tmdb, tvdb, title, premiered, season, episode):
        if not url:
            return
        url = parse_qs(url)
        url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
        url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
        url = urlencode(url)
        return url


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            aliases = eval(data['aliases'])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search_url = self.base_link + self.search_link % cleantitle.geturl(title)
            r = client.scrapePage(search_url).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'flw-item'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'a', ret='title'), client_utils.parseDOM(i, 'span', attrs={'class': 'fdi-item'})) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            if 'tvshowtitle' in data:
                result_url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and i[0].startswith('/tv/')][0]
                url = self.base_link + result_url
            else:
                result_url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year) and i[0].startswith('/movie/')][0]
                url = self.base_link + result_url
            r = client.scrapePage(url).text
            try:
                check_year = re.findall(r'Release date:.+?(\d{4})', r)[0]
                check_year = cleantitle.match_year(check_year, year, data['year'])
            except:
                check_year = 'Failed to find year info.' # Used to fake out the year check code.
            if not check_year:
                return self.results
            item_id = client_utils.parseDOM(r, 'div', ret='data-id')[0]
            if 'tvshowtitle' in data:
                check_season = '<span>Season %s</span>' % season
                seasons_url = self.base_link + '/ajax/v2/tv/seasons/%s' % item_id
                r = client.scrapePage(seasons_url).text
                r = zip(client_utils.parseDOM(r, 'a', ret='data-id'), client_utils.parseDOM(r, 'a'))
                item_season_id = [i[0] for i in r if check_season in i[1]][0]
                check_episode = 'Episode %s:' % episode
                episodes_url = self.base_link + '/ajax/v2/season/episodes/%s' % item_season_id
                r = client.scrapePage(episodes_url).text
                r = zip(client_utils.parseDOM(r, 'a', ret='data-id'), client_utils.parseDOM(r, 'a', ret='data-name'))
                item_episode_id = [i[0] for i in r if check_episode in i[1]][0]
                servers_url = self.base_link + '/ajax/v2/episode/servers/%s/#servers-list' % item_episode_id
            else:
                servers_url = self.base_link + '/ajax/movie/episodes/%s' % item_id
            r = client.scrapePage(servers_url).text
            if 'tvshowtitle' in data:
                server_ids = client_utils.parseDOM(r, 'a', ret='data-id')
            else:
                server_ids = client_utils.parseDOM(r, 'a', ret='data-linkid')
            for server_id in server_ids:
                try:
                    get_link = self.base_link + '/ajax/get_link/%s' % server_id
                    r = client.scrapePage(get_link).json()
                    link = r['link']
                    for source in scrape_sources.process(hostDict, link):
                        if scrape_sources.check_host_limit(source['source'], self.results):
                            continue
                        self.results.append(source)
                except:
                    #log_utils.log('sources', 1)
                    pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


