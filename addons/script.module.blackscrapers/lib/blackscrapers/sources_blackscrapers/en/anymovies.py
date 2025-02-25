# -*- coding: utf-8 -*-
# Created by Tempest
# Rewritten for TheOath


import re
from blackscrapers import parse_qs, urljoin, urlencode, quote_plus
from blackscrapers.modules import source_utils
from blackscrapers.modules import client
from blackscrapers.modules import log_utils


from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domain = ['downloads-anymovies.com']
        self.base_link = custom_base or 'https://www.downloads-anymovies.co'
        self.search_link = '/search.php?zoom_query=%s'
        self.headers = {'User-Agent': client.agent()}
        self.aliases = []

    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['title']
            year = data['year']

            query = ' '.join((title, year))
            query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url).replace('++', '+')

            post = client.request(url, headers=self.headers)
            try:
                r = client.parseDOM(post, 'div', attrs={'class': 'result_title'})
                r = zip(client.parseDOM(r, 'a', ret='href'), client.parseDOM(r, 'a'))
                r = [(i[0], re.findall(r'(?:Watch|)(.+?)\((\d+)', i[1])) for i in r]
                r = [(i[0], i[1][0]) for i in r if len(i[1]) > 0]
                page_url = [i[0] for i in r if source_utils.is_match(' '.join((i[1][0], i[1][1])), title, year, self.aliases)][0]
            except:
                page_url = self.base_link + '/added_movies/%s-%s-watch-full-movie-online-free.html' % (title.replace(' ', '-').lower(), year)

            page_html = client.request(page_url, headers=self.headers)
            links = client.parseDOM(page_html, 'a', attrs={'target': '_blank'}, ret='href')
            for link in links:
                if any(x in link for x in ['report-error.html', 'statcounter.com']):
                    continue
                valid, host = source_utils.is_host_valid(link, hostDict)
                if valid:
                    sources.append({'source': host, 'quality': 'HD', 'language': 'en', 'url': link, 'direct': False, 'debridonly': False})

            return sources
        except Exception:
            log_utils.log('ANYMOVIES - Exception', 1)
            return sources

    def resolve(self, url):
        return url
