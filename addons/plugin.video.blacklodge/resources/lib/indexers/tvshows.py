# -*- coding: utf-8 -*-

"""
    Exodus Add-on
    ///Updated for BlackLodge///

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


from resources.lib.modules import trakt
from resources.lib.modules import cleantitle
from resources.lib.modules import cleangenre
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules import cache
from resources.lib.modules import metacache
from resources.lib.modules import playcount
from resources.lib.modules import workers
from resources.lib.modules import views
from resources.lib.modules import utils
from resources.lib.modules import api_keys
from resources.lib.modules import log_utils
from resources.lib.indexers import navigator

import os,sys,re,datetime
import simplejson as json

import six
from six.moves import urllib_parse, zip

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

import requests


params = dict(urllib_parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()
action = params.get('action')


class tvshows:
    def __init__(self):
        self.list = []
        self.code = ''

        self.session = requests.Session()

        self.imdb_link = 'https://www.imdb.com'
        self.trakt_link = 'https://api.trakt.tv'
        self.tvmaze_link = 'https://www.tvmaze.com'
        self.tmdb_link = 'https://api.themoviedb.org/3'
        self.logo_link = 'https://i.imgur.com/'
        self.datetime = datetime.datetime.utcnow()# - datetime.timedelta(hours = 5)
        self.year_date = (self.datetime - datetime.timedelta(days = 365)).strftime('%Y-%m-%d')
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.specials = control.setting('tv.specials') or 'true'
        self.showunaired = control.setting('showunaired') or 'true'
        self.hq_artwork = control.setting('hq.artwork') or 'false'
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.tm_user = control.setting('tm.user') or api_keys.tmdb_key
        self.fanart_tv_user = control.setting('fanart.tv.user')
        self.fanart_tv_headers = {'api-key': api_keys.fanarttv_key}
        if not self.fanart_tv_user == '':
            self.fanart_tv_headers.update({'client-key': self.fanart_tv_user})
        self.user = control.setting('fanart.tv.user')
        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.imdb_sort = 'alpha,asc' if control.setting('imdb.sort.order') == '1' else 'date_added,desc'
        self.trailer_source = control.setting('trailer.source') or '2'
        self.country = control.setting('official.country') or 'US'
        self.lang = control.apiLanguage()['tmdb'] or 'en'

        self.tvmaze_info_link = 'https://api.tvmaze.com/shows/%s'
        self.fanart_tv_art_link = 'http://webservice.fanart.tv/v3/tv/%s'
        self.fanart_tv_level_link = 'http://webservice.fanart.tv/v3/level'

        ## TMDb ##
        self.tmdb_api_link = 'https://api.themoviedb.org/3/tv/%s?api_key=%s&language=%s&append_to_response=aggregate_credits,content_ratings,external_ids' % ('%s', self.tm_user, self.lang)
        self.tmdb_by_imdb = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', self.tm_user)
        self.tmdb_networks_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&sort_by=popularity.desc&with_networks=%s&page=1' % (self.tm_user, '%s')
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.tm_search_link = 'https://api.themoviedb.org/3/search/tv?api_key=%s&language=en-US&query=%s&page=1' % (self.tm_user, '%s')
        self.related_link = 'https://api.themoviedb.org/3/tv/%s/similar?api_key=%s&page=1' % ('%s', self.tm_user)

        self.tmdb_pop_link = 'https://api.themoviedb.org/3/discover/tv?with_original_language=en&with_type=2|4&api_key=%s&page=1' % self.tm_user
        self.tmdb_rating_link = 'https://api.themoviedb.org/3/tv/top_rated?api_key=%s&page=1' % self.tm_user
        self.tmdb_voted_link = 'https://api.themoviedb.org/3/discover/tv?sort_by=vote_count.desc&api_key=%s&page=1' % self.tm_user
        self.tmdb_featured_link = 'https://api.themoviedb.org/3/trending/tv/week?api_key=%s&page=1' % self.tm_user
        self.tmdb_airing_link = 'https://api.themoviedb.org/3/tv/airing_today?with_original_language=en&api_key=%s&page=1' % self.tm_user
        self.tmdb_active_link = 'https://api.themoviedb.org/3/discover/tv?with_status=0&with_type=2|4&with_original_language=en&api_key=%s&page=1' % self.tm_user
        self.tmdb_premiere_link = 'https://api.themoviedb.org/3/discover/tv?first_air_date.gte=%s&first_air_date.lte=%s&with_original_language=en&sort_by=primary_release_date.desc&api_key=%s&page=1' % (self.year_date, self.today_date, self.tm_user)

        self.tmdb_genre_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&with_genres=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s')
        self.tmdb_year_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&with_original_language=en&with_type=0|2|4&first_air_date_year=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s')
        self.tmdb_decade_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&with_original_language=en&with_type=0|2|4&first_air_date.gte=%s&first_air_date.lte=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s', '%s')
        self.tmdb_language_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&with_original_language=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s')

        self.tmdb_providers_avail_link = 'https://api.themoviedb.org/3/tv/%s/watch/providers?api_key=%s' % ('%s', self.tm_user)
        self.tmdb_providers_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&sort_by=popularity.desc&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', self.country)
        self.tmdb_providers_rated_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&sort_by=vote_average.desc&vote_count.gte=500&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', self.country)
        self.tmdb_providers_pop_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', self.country)
        self.tmdb_providers_voted_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&sort_by=vote_count.desc&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', self.country)
        self.tmdb_providers_premiere_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&first_air_date.gte=%s&first_air_date.lte=%s&sort_by=primary_release_date.desc&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, self.year_date, self.today_date, '%s', self.country)

        ## IMDb ##
        self.genre_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&genres=%s&release_date=,date[0]&sort=moviemeter,asc&count=%s' % ('%s', self.items_per_page)
        self.year_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=%s,%s&sort=moviemeter,asc&count=%s' % ('%s', '%s', self.items_per_page)
        self.language_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&sort=moviemeter,asc&num_votes=100,&primary_language=%s&count=%s' % ('%s', self.items_per_page)
        self.certification_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&certificates=US:%s&release_date=,date[0]&sort=moviemeter,asc&count=%s'% ('%s', self.items_per_page)

        self.popular_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=,date[0]&sort=moviemeter,asc&num_votes=100,&count=%s'% self.items_per_page
        self.rating_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&genres=!documentary&release_date=,date[0]&sort=user_rating,desc&num_votes=10000,&count=%s' % self.items_per_page
        self.views_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=,date[0]&sort=num_votes,desc&num_votes=100,&count=%s' % self.items_per_page
        self.airing_link = 'https://www.imdb.com/search/title/?title_type=tv_episode&release_date=date[1],date[0]&sort=moviemeter,asc&count=%s' % self.items_per_page
        self.premiere_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=date[60],date[0]&sort=release_date,desc&num_votes=10,&languages=en&count=%s' % self.items_per_page
        self.keyword_link = 'https://www.imdb.com/search/title?title_type=tv_series,tv_miniseries&release_date=,date[0]&keywords=%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)

        self.imdblists_link = 'https://www.imdb.com/user/ur%s/lists?tab=all&sort=modified&order=desc&filter=titles' % self.imdb_user
        self.imdblist_link = 'https://www.imdb.com/list/%s/?sort=%s&title_type=tv_series,tv_miniseries&start=0' % ('%s', self.imdb_sort)
        self.imdbwatchlist_link = 'https://www.imdb.com/user/ur%s/watchlist/?sort=%s&title_type=tv_series,tv_miniseries&start=0' % (self.imdb_user, self.imdb_sort)

        ## Trakt ##
        self.trending_link = 'https://api.trakt.tv/shows/trending?limit=%s&page=1' % self.items_per_page
        self.trakt_certification_link = 'https://api.trakt.tv/shows/popular?certifications=%s&limit=%s&page=1' % ('%s', self.items_per_page)
        self.mosts_link = 'https://api.trakt.tv/shows/%s/%s?limit=%s&page=1' % ('%s', '%s', self.items_per_page)
        self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
        self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000'
        self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items'
        self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/shows'
        self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/shows'
        self.traktfeatured_link = 'https://api.trakt.tv/recommendations/shows?ignore_collected=true&ignore_watchlisted=true&limit=40'
        # self.related_link = 'https://api.trakt.tv/shows/%s/related'
        # self.search_link = 'https://api.trakt.tv/search/show?limit=20&page=1&query='


    def __del__(self):
        self.session.close()


    def get(self, url, idx=True, create_directory=True, code=''):
        try:
            try: url = getattr(self, url + '_link')
            except: pass

            try: u = urllib_parse.urlparse(url).netloc.lower()
            except: pass

            self.code = code

            if u in self.trakt_link and '/users/' in url:
                try:
                    #if not '/users/me/' in url: raise Exception()
                    if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user): raise Exception()
                    self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                except:
                    self.list = self.trakt_list(url, self.trakt_user)

                if '/users/me/' in url and '/collection/' in url:
                    self.list = sorted(self.list, key=lambda k: utils.title_key(k['title']))

                if idx == True: self.worker()

            elif u in self.trakt_link:
                self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                if idx == True: self.worker()

            elif u in self.imdb_link:
                self.list = cache.get(self.imdb_list, 24, url)
                if idx == True: self.worker()

            elif u in self.tvmaze_link:
                self.list = cache.get(self.tvmaze_list, 168, url)
                if idx == True: self.worker()

            elif u in self.tmdb_link:
                self.list = cache.get(self.tmdb_list, 24, url, self.code)
                if self.code and not self.list:
                    return control.infoDialog('Nothing found on your services')
                if idx == True: self.worker()

            if idx == True and create_directory == True: self.tvshowDirectory(self.list)
            return self.list
        except:
            log_utils.log('tv_get', 1)
            pass


    def search(self, code=''):
        code = urllib_parse.quote(code) if code else ''

        navigator.navigator().addDirectoryItem(32603, 'tvSearchnew&code=%s' % code, 'search.png', 'DefaultTVShows.png')

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.executescript("CREATE TABLE IF NOT EXISTS tvshow (ID Integer PRIMARY KEY AUTOINCREMENT, term);")
        except:
            pass

        dbcur.execute("SELECT * FROM tvshow ORDER BY ID DESC")

        lst = []

        delete_option = False
        for (id,term) in dbcur.fetchall():
            if term not in str(lst):
                delete_option = True
                navigator.navigator().addDirectoryItem(term.title(), 'tvSearchterm&name=%s&code=%s' % (term, code), 'search.png', 'DefaultTVShows.png', context=(32644, 'tvDeleteterm&name=%s' % term))
                lst += [(term)]
        dbcur.close()

        if delete_option:
            navigator.navigator().addDirectoryItem(32605, 'clearCacheSearch&select=tvshow', 'tools.png', 'DefaultAddonProgram.png')

        navigator.navigator().endDirectory(False)


    def search_new(self, code=''):
        control.idle()

        t = control.lang(32010)
        k = control.keyboard('', t)
        k.doModal()
        q = k.getText() if k.isConfirmed() else None

        if not q: return
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM tvshow WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO tvshow VALUES (?,?)", (None,q))
        dbcon.commit()
        dbcur.close()
        url = self.tm_search_link % urllib_parse.quote(q)
        self.get(url, code=code)


    def search_term(self, q, code=''):
        control.idle()
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM tvshow WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO tvshow VALUES (?,?)", (None, q))
        dbcon.commit()
        dbcur.close()
        url = self.tm_search_link % urllib_parse.quote(q)
        self.get(url, code=code)


    def delete_term(self, q):
        control.idle()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM tvshow WHERE term = ?", (q,))
        dbcon.commit()
        dbcur.close()
        control.refresh()


    def mosts(self):
        keywords = [
            ('Most Played This Week', 'played', 'weekly'),
            ('Most Played This Month', 'played', 'monthly'),
            ('Most Played This Year', 'played', 'yearly'),
            ('Most Played All Time', 'played', 'all'),
            ('Most Collected This Week', 'collected', 'weekly'),
            ('Most Collected This Month', 'collected', 'monthly'),
            ('Most Collected This Year', 'collected', 'yearly'),
            ('Most Collected All Time', 'collected', 'all'),
            ('Most Watched This Week', 'watched', 'weekly'),
            ('Most Watched This Month', 'watched', 'monthly'),
            ('Most Watched This Year', 'watched', 'yearly'),
            ('Most Watched All Time', 'watched', 'all')
        ]

        for i in keywords: self.list.append(
            {
                'name': i[0],
                'url': self.mosts_link % (i[1], i[2]),
                'image': 'trakt.png',
                'action': 'tvshows'
            })
        self.addDirectory(self.list)
        return self.list


    def genres(self):
        genres = [
            ('Action', 'action', True),
            ('Adventure', 'adventure', True),
            ('Animation', 'animation', True),
            ('Anime', 'anime', False),
            ('Biography', 'biography', True),
            ('Comedy', 'comedy', True),
            ('Crime', 'crime', True),
            ('Documentary', 'documentary', True),
            ('Drama', 'drama', True),
            ('Family', 'family', True),
            ('Fantasy', 'fantasy', True),
            ('Game-Show', 'game_show', True),
            ('History', 'history', True),
            ('Horror', 'horror', True),
            ('Music ', 'music', True),
            ('Musical', 'musical', True),
            ('Mystery', 'mystery', True),
            ('News', 'news', True),
            ('Reality-TV', 'reality_tv', True),
            ('Romance', 'romance', True),
            ('Science Fiction', 'sci_fi', True),
            ('Sport', 'sport', True),
            ('Superhero', 'superhero', False),
            ('Talk-Show', 'talk_show', True),
            ('Thriller', 'thriller', True),
            ('War', 'war', True),
            ('Western', 'western', True)
        ]

        for i in genres: self.list.append(
            {
                'name': cleangenre.lang(i[0], self.lang),
                'url': self.genre_link % (i[1] + ',!documentary' if i[1] != 'documentary' else i[1]) if i[2] else self.keyword_link % i[1],
                'image': 'genres/{}.png'.format(i[1]),
                'action': 'tvshows'
            })
        self.addDirectory(self.list)
        return self.list


    def tmdb_genres(self, code=''):
        genres = [
            ('Action & Adventure', '10759'),
            ('Animation', '16'),
            ('Comedy', '35'),
            ('Crime', '80'),
            ('Documentary', '99'),
            ('Drama', '18'),
            ('Family', '10751'),
            ('Kids', '10762'),
            ('Mystery', '9648'),
            ('News', '10763'),
            ('Reality', '10764'),
            ('Sci-Fi & Fantasy', '10765'),
            ('Soap', '10766'),
            ('Talk-Show', '10767'),
            ('War & Politics', '10768'),
            ('Western', '37')
        ]

        region = self.country if code else ''

        for i in genres: self.list.append(
            {
                'name': cleangenre.lang(i[0], self.lang),
                'url': self.tmdb_genre_link % (i[1], code, region),
                'image': 'genres.png',
                'action': 'tvshows'
            })
        self.addDirectory(self.list)
        return self.list


    def networks(self):
        networks = [
            ('A&E', '129'),
            ('ABC', '2'),
            ('ABC Australia', '18'),
            ('ABC Family', '75'),
            ('Acorn TV', '2697'),
            ('Adult Swim', '80'),
            ('AMC', '174'),
            ('Animal Planet', '91'),
            ('Apple TV+', '2552'),
            ('AT-X', '173'),
            ('Audience', '251'),
            ('BBC One', '4'),
            ('BBC Two', '332'),
            ('BBC Three', '3'),
            ('BBC Four', '100'),
            ('BBC America', '493'),
            ('BET', '24'),
            ('Bravo', '74'),
            ('C More', '458'),
            ('Cartoon Network', '56'),
            ('CBC', '23'),
            ('CBS All Access', '1709'),
            ('CBS', '16'),
            ('Channel 4', '26'),
            ('Channel 5', '99'),
            ('Cinemax', '359'),
            ('Comedy Central', '47'),
            ('Crackle', '928'),
            ('CTV', '110'),
            ('Curiosity Stream', '2349'),
            ('DC Universe', '2243'),
            ('Discovery+', '4353'),
            ('Discovery Channel', '64'),
            ('Disney+', '2739'),
            ('Disney Channel', '54'),
            ('Disney Junior', '281'),
            ('Disney XD', '44'),
            ('E!', '76'),
            ('E4', '136'),
            ('Epix', '922'),
            ('Food Network', '143'),
            ('FOX', '19'),
            ('Freeform', '1267'),
            ('FX', '88'),
            ('FXX', '1035'),
            ('Hallmark Channel', '384'),
            ('HBO Max', '3186'),
            ('HBO', '49'),
            ('HGTV', '210'),
            ('History Channel', '65'),
            ('Hulu', '453'),
            ('Investigation Discovery', '244'),
            ('ITV', '9'),
            ('Lifetime', '34'),
            ('MAX', '6783'),
            ('MTV', '33'),
            ('National Geographic', '43'),
            ('NBC', '6'),
            ('Netflix', '213'),
            ('Nick Junior', '35'),
            ('Nickelodeon', '13'),
            ('NRK1', '379'),
            ('Oxygen', '132'),
            ('Paramount+', '4330'),
            ('Paramount Network', '2076'),
            ('PBS', '14'),
            ('Peacock', '3353'),
            ('Prime Video', '1024'),
            ('Showtime', '67'),
            ('Sky Atlantic', '1063'),
            ('Sky One', '214'),
            ('Spike', '55'),
            ('Starz', '318'),
            ('SundanceTV', '270'),
            ('Syfy', '77'),
            ('TBS', '68'),
            ('The CW', '71'),
            ('The WB', '21'),
            ('TLC', '84'),
            ('TNT', '41'),
            ('Travel Channel', '209'),
            ('truTV', '364'),
            ('TV Land', '397'),
            ('USA Network', '30'),
            ('Viaplay Denmark', '2869'),
            ('Viaplay Norway', '2406'),
            ('Viaplay Sweden', '1585'),
            ('VH1', '158'),
            ('WGN America', '202'),
            ('YouTube Premium', '1436')
        ]

        for i in networks: self.list.append(
            {
                'name': i[0],
                'url': self.tmdb_networks_link % i[1],
                'image': 'networks/{}.png'.format(i[0]),
                'action': 'tvshows'
            })
        self.addDirectory(self.list)
        return self.list


    def languages(self, code='', tmdb=False):
        languages = [
            ('Arabic', 'ar'),
            ('Bosnian', 'bs'),
            ('Bulgarian', 'bg'),
            ('Chinese', 'zh'),
            ('Croatian', 'hr'),
            ('Dutch', 'nl'),
            ('English', 'en'),
            ('Finnish', 'fi'),
            ('French', 'fr'),
            ('German', 'de'),
            ('Greek', 'el'),
            ('Hebrew', 'he'),
            ('Hindi ', 'hi'),
            ('Hungarian', 'hu'),
            ('Icelandic', 'is'),
            ('Italian', 'it'),
            ('Japanese', 'ja'),
            ('Korean', 'ko'),
            ('Norwegian', 'no'),
            ('Persian', 'fa'),
            ('Polish', 'pl'),
            ('Portuguese', 'pt'),
            ('Punjabi', 'pa'),
            ('Romanian', 'ro'),
            ('Russian', 'ru'),
            ('Serbian', 'sr'),
            ('Spanish', 'es'),
            ('Swedish', 'sv'),
            ('Turkish', 'tr'),
            ('Ukrainian', 'uk')
        ]

        region = self.country if code else ''

        for i in languages: self.list.append(
            {
                'name': i[0],
                'url': self.language_link % i[1] if not tmdb else self.tmdb_language_link % (i[1], code, region),
                'image': 'languages.png',
                'action': 'tvshows'
            })
        self.addDirectory(self.list)
        return self.list


    def certifications(self, code=''):
        certificates = ['TV-Y', 'TV-Y7', 'TV-G', 'TV-PG', 'TV-14', 'TV-MA']

        for i in certificates: self.list.append(
            {
                'name': i,
                'url': self.certification_link % i if not code else self.trakt_certification_link % i.lower(),
                'image': 'mpaa/{}.png'.format(i),
                'action': 'tvshows'
            })
        self.addDirectory(self.list)
        return self.list


    def years(self, code='', tmdb=False):
        region = self.country if code else ''

        year = (self.datetime.strftime('%Y'))
        for i in range(int(year)-0, 1935, -1): self.list.append(
            {
                'name': str(i),
                'url': self.year_link % (str(i), str(i)) if not tmdb else self.tmdb_year_link % (str(i), code, region),
                'image': 'years.png',
                'action': 'tvshows'
            })
        self.addDirectory(self.list)
        return self.list


    def decades(self, code='', tmdb=False):
        region = self.country if code else ''

        year = (self.datetime.strftime('%Y'))
        dec = int(year[:3]) * 10
        for i in range(dec, 1920, -10): self.list.append(
            {
                'name': str(i) + 's',
                'url': self.year_link % (str(i), str(i+9)) if not tmdb else self.tmdb_decade_link % (str(i) + '-01-01', str(i+9) + '-12-31', code, region),
                'image': 'years.png',
                'action': 'tvshows'
            })
        self.addDirectory(self.list)
        return self.list


    def services(self, code):
        _code = urllib_parse.quote(code)

        navigator.navigator().addDirectoryItem(32011, 'tvTmdbGenres&code=%s' % _code, 'genres.png', 'DefaultTVShows.png')
        navigator.navigator().addDirectoryItem(32012, 'tvYears&code=%s&tmdb=True' % _code, 'years.png', 'DefaultTVShows.png')
        navigator.navigator().addDirectoryItem(32123, 'tvDecades&code=%s&tmdb=True' % _code, 'years.png', 'DefaultTVShows.png')
        navigator.navigator().addDirectoryItem(32014, 'tvLanguages&code=%s' % _code, 'languages.png', 'DefaultTVShows.png')

        self.list.append(
            {
                'name': control.lang(32018),
                'url': self.tmdb_providers_pop_link % code,
                'image': 'people-watching.png',
                'action': 'tvshows'
            })
        self.list.append(
            {
                'name': control.lang(32023),
                'url': self.tmdb_providers_rated_link % code,
                'image': 'highly-rated.png',
                'action': 'tvshows'
            })
        self.list.append(
            {
                'name': control.lang(32019),
                'url': self.tmdb_providers_voted_link % code,
                'image': 'most-voted.png',
                'action': 'tvshows'
            })
        self.list.append(
            {
                'name': control.lang(32568),
                'url': self.tmdb_providers_premiere_link % code,
                'image': 'new-tvshows.png',
                'action': 'tvshows'
            })

        self.addDirectory(self.list)
        return self.list


    def services_availability(self, tmdb, code):
        url = self.tmdb_providers_avail_link % tmdb
        r = self.session.get(url, timeout=10).json()
        r = r['results'].get(self.country)
        if r:
            offers = [r.get('free'), r.get('ads'), r.get('flatrate')]
            offers = [o for o in offers if o]
            if offers:
                providers = []
                for o in offers:
                    for c in o:
                        providers.append(str(c['provider_id']))
                if providers:
                    if any(p in code.split('|') for p in providers):
                        return True
        return False


    def userlists(self):
        try:
            userlists = []
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            activity = trakt.getActivity()
        except:
            pass

        try:
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlists_link, self.trakt_user): raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link, self.trakt_user)
        except:
            pass
        try:
            self.list = []
            if self.imdb_user == '': raise Exception()
            userlists += cache.get(self.imdb_user_list, 120, self.imdblists_link)
        except:
            pass
        try:
            self.list = []
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link, self.trakt_user): raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlikedlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user)
        except:
            pass

        self.list = userlists
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'tvshows'})
        self.list = sorted(self.list, key=lambda k: (k['image'], k['name'].lower()))
        self.addDirectory(self.list)
        return self.list


    def trakt_list(self, url, user):
        try:
            q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib_parse.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q

            result = trakt.getTraktAsJson(u)

            items = []
            for i in result:
                try: items.append(i['show'])
                except: pass
            if len(items) == 0:
                items = result
        except:
            return self.list

        try:
            q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
            if not int(q['limit']) == len(items): raise Exception()
            page = q['page']
            q.update({'page': str(int(page) + 1)})
            q = (urllib_parse.urlencode(q)).replace('%2C', ',')
            next = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q
            next = six.ensure_str(next)
        except:
            next = page = ''

        def items_list(item):
            try:
                title = item['title']
                title = re.sub(r'\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)

                year = item['year']
                year = re.sub('[^0-9]', '', str(year))

                #if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = item['ids']['imdb']
                if imdb == None or imdb == '': imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tmdb = item['ids']['tmdb']
                if tmdb == None or tmdb == '': tmdb = '0'
                tmdb = str(tmdb)

                tvdb = item['ids']['tvdb']
                tvdb = re.sub('[^0-9]', '', str(tvdb))

                try: premiered = item['first_aired']
                except: premiered = '0'
                try: premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                except: premiered = '0'

                try: studio = item['network']
                except: studio = '0'
                if studio == None: studio = '0'

                try: genre = item['genres']
                except: genre = '0'
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)

                try: duration = str(item['runtime'])
                except: duration = '0'
                if duration == None: duration = '0'

                try: rating = str(item['rating'])
                except: rating = '0'
                if rating == None or rating == '0.0': rating = '0'

                try: votes = str(item['votes'])
                except: votes = '0'
                try: votes = str(format(int(votes),',d'))
                except: pass
                if votes == None: votes = '0'

                try: mpaa = item['certification']
                except: mpaa = '0'
                if mpaa == None: mpaa = '0'

                try: plot = item['overview']
                except: plot = '0'
                if plot == None: plot = '0'
                plot = client.replaceHTMLCodes(plot)

                country = item.get('country')
                if not country: country = '0'
                else: country = country.upper()

                status = item.get('status')
                if not status: status = '0'

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating,
                                  'votes': votes, 'mpaa': mpaa, 'plot': plot, 'country': country, 'status': status, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'poster': '0', 'page': page, 'next': next})
            except:
                log_utils.log('trakt_list0', 1)
                pass

        try:
            threads = []
            for i in items: threads.append(workers.Thread(items_list, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            return self.list
        except:
            log_utils.log('trakt_list1', 1)
            return self.list


    def trakt_user_list(self, url, user):
        try:
            items = trakt.getTraktAsJson(url)
        except:
            pass

        for item in items:
            try:
                try: name = item['list']['name']
                except: name = item['name']
                name = client.replaceHTMLCodes(name)

                try: url = (trakt.slug(item['list']['user']['username']), item['list']['ids']['slug'])
                except: url = ('me', item['ids']['slug'])
                url = self.traktlist_link % url
                url = six.ensure_str(url)

                self.list.append({'name': name, 'url': url, 'context': url, 'image': 'trakt.png'})
            except:
                pass

        return self.list


    def imdb_list(self, url):
        try:
            url = url.split('&ref')[0]
            for i in re.findall(r'date\[(\d+)\]', url):
                url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days = int(i))).strftime('%Y-%m-%d'))

            # def imdb_watchlist_id(url):
                # r = client.request(url)
                # data = re.findall('<script id="__NEXT_DATA__" type="application/json">({.+?})</script>', r)[0]
                # data = utils.json_loads_as_str(data)
                # lst = data['props']['pageProps']['aboveTheFoldData']['listId']
                # return lst

            # if url == self.imdbwatchlist_link:
                # url = cache.get(imdb_watchlist_id, 8640, url)
                # url = self.imdblist_link % url

            # log_utils.log('imdb_url: ' + repr(url))
        except:
            log_utils.log('imdb_list fail', 1)
            return self.list

        def imdb_userlist(link):
            result = client.request(link)
            #log_utils.log(result[0])
            data = re.findall('<script id="__NEXT_DATA__" type="application/json">({.+?})</script>', result)[0]
            data = utils.json_loads_as_str(data)
            if '/list/' in link:
                data = data['props']['pageProps']['mainColumnData']['list']['titleListItemSearch']['edges']
            elif '/user/' in link:
                data = data['props']['pageProps']['mainColumnData']['predefinedList']['titleListItemSearch']['edges']
            data = [item['listItem'] for item in data if item['listItem']['titleType']['id'] in ['tvSeries', 'tvMiniSeries']]
            return data

        if '/list/' in url or '/user/' in url:
            try:
                data = cache.get(imdb_userlist, 24, url.split('&start')[0])
                if not data: raise Exception()
            except:
                return self.list

            try:
                start = re.findall(r'&start=(\d+)', url)[0]
                items = data[int(start):(int(start) + int(self.items_per_page))]
                if (int(start) + int(self.items_per_page)) >= len(data):
                    next = page = ''
                else:
                    next = re.sub(r'&start=\d+', '&start=%s' % str(int(start) + int(self.items_per_page)), url)
                    #log_utils.log('next_url: ' + next)
                    page = (int(start) + int(self.items_per_page)) // int(self.items_per_page)
            except:
                #log_utils.log('next_fail', 1)
                return self.list

        else:
            count_ = re.findall(r'&count=(\d+)', url)
            if len(count_) == 1 and int(count_[0]) > 250:
                url = url.replace('&count=%s' % count_[0], '&count=250')

            try:
                result = client.request(url, output='extended')
                #log_utils.log(result[0])
                data = re.findall('<script id="__NEXT_DATA__" type="application/json">({.+?})</script>', result[0])[0]
                data = utils.json_loads_as_str(data)
                data = data['props']['pageProps']['searchResults']['titleResults']['titleListItems']
                items = data[-int(self.items_per_page):]
                #log_utils.log(repr(items))
            except:
                return self.list

            try:
                cur = re.findall(r'&count=(\d+)', url)[0]
                if int(cur) > len(data) or cur == '250':
                    items = data[-(len(data) - int(count_[0]) + int(self.items_per_page)):]
                    raise Exception()
                next = re.sub(r'&count=\d+', '&count=%s' % str(int(cur) + int(self.items_per_page)), result[5])
                #log_utils.log('next_url: ' + next)
                page = int(cur) // int(self.items_per_page)
            except:
                #log_utils.log('next_fail', 1)
                next = page = ''

        for item in items:
            try:
                if '/list/' in url or '/user/' in url:
                    try: mpaa = item['certificate']['rating'] or '0'
                    except: mpaa = '0'
                    genre = ' / '.join([i['genre']['text'] for i in item['titleGenres']['genres']]) or '0'
                    title = item['originalTitleText']['text']
                    plot = item['plot']['plotText']['plainText'] or '0'
                    poster = item['primaryImage']['url']
                    if not poster or '/sash/' in poster or '/nopicture/' in poster: poster = '0'
                    else: poster = re.sub(r'(?:_SX|_SY|_UX|_UY|_CR|_AL|_V)(?:\d+|_).+?\.', '_SX500.', poster)
                    rating = str(item['ratingsSummary']['aggregateRating']) or '0'
                    votes = str(item['ratingsSummary']['voteCount']) or '0'
                    year = str(item['releaseYear']['year']) or '0'
                    imdb = item['id']
                else:
                    mpaa = item.get('certificate', '0') or '0'
                    genre = ' / '.join([i for i in item['genres']]) or '0'
                    title = item['originalTitleText']
                    plot = item['plot'] or '0'
                    poster = item['primaryImage']['url']
                    if not poster or '/sash/' in poster or '/nopicture/' in poster: poster = '0'
                    else: poster = re.sub(r'(?:_SX|_SY|_UX|_UY|_CR|_AL|_V)(?:\d+|_).+?\.', '_SX500.', poster)
                    rating = str(item['ratingSummary']['aggregateRating']) or '0'
                    votes = str(item['ratingSummary']['voteCount']) or '0'
                    year = str(item['releaseYear']) or '0'
                    imdb = item['titleId']

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'genre': genre, 'rating': rating, 'votes': votes, 'mpaa': mpaa,
                                  'plot': plot, 'imdb': imdb, 'imdbnumber': imdb, 'tmdb': '0', 'tvdb': '0', 'poster': poster, 'cast': '0', 'page': page, 'next': next})
            except:
                log_utils.log('imdb_json_list fail', 1)
                pass

        return self.list


    def imdb_user_list(self, url):
        try:
            result = client.request(url)
            items = client.parseDOM(result, 'div', attrs = {'class': 'ipc-metadata-list-summary-item__tc'})
        except:
            pass

        for item in items:
            try:
                name = client.parseDOM(item, 'a')[0]
                name = client.replaceHTMLCodes(name)
                name = six.ensure_str(name, errors='ignore')

                url = client.parseDOM(item, 'a', ret='href')[0]
                url = re.findall(r'(ls\d+)/', url)[0]
                url = self.imdblist_link % url
                url = client.replaceHTMLCodes(url)
                url = six.ensure_str(url, errors='replace')

                self.list.append({'name': name, 'url': url, 'context': url, 'image': 'imdb.png'})
            except:
                pass

        return self.list


    def tvmaze_list(self, url):
        try:
            result = client.request(url)

            result = client.parseDOM(result, 'div', attrs = {'id': 'w1'})

            items = client.parseDOM(result, 'span', attrs = {'class': 'title'})
            items = [client.parseDOM(i, 'a', ret='href') for i in items]
            items = [i[0] for i in items if len(i) > 0]
            items = [re.findall(r'/(\d+)/', i) for i in items]
            items = [i[0] for i in items if len(i) > 0]

            next = ''; last = []; nextp = []
            page = int(str(url.split('&page=', 1)[1]))
            next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
            last = client.parseDOM(result, 'li', attrs = {'class': 'last disabled'})
            nextp = client.parseDOM(result, 'li', attrs = {'class': 'next'})
            if last != [] or nextp == []: next = page = ''
        except:
            log_utils.log('tvm-list fail', 1)
            return

        def items_list(i):
            try:
                url = self.tvmaze_info_link % i

                item = self.session.get(url, timeout=16).json()

                title = item['name']
                title = re.sub(r'\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)
                title = six.ensure_str(title)

                premiered = item['premiered']
                try: premiered = re.findall(r'(\d{4}-\d{2}-\d{2})', premiered)[0]
                except: premiered = '0'
                premiered = six.ensure_str(premiered)

                year = item['premiered']
                try: year = re.findall(r'(\d{4})', year)[0]
                except: year = '0'
                year = six.ensure_str(year)

                #if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = item['externals']['imdb']
                if imdb == None or imdb == '': imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                imdb = six.ensure_str(imdb)

                tvdb = item['externals']['thetvdb']
                if tvdb == None or tvdb == '': tvdb = '0'
                else: tvdb = re.sub('[^0-9]', '', str(tvdb))
                tvdb = six.ensure_str(tvdb)

                try: poster = item['image']['original']
                except: poster = '0'
                if poster == None or poster == '': poster = '0'
                poster = six.ensure_str(poster)

                try: studio = item['network']['name']
                except: studio = '0'
                if studio == None: studio = '0'
                studio = six.ensure_str(studio)

                try: genre = item['genres']
                except: genre = '0'
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)
                genre = six.ensure_str(genre)

                try: duration = item['runtime']
                except: duration = '0'
                if not duration or duration == 'None': duration = '0'
                duration = str(duration)
                duration = six.ensure_str(duration)

                try: rating = item['rating']['average']
                except: rating = '0'
                if rating in [None, 'None', '0.0']: rating = '0'
                rating = str(rating)
                rating = six.ensure_str(rating)

                try: plot = item['summary']
                except: plot = '0'
                if plot == None: plot = '0'
                plot = re.sub(r'<.+?>|</.+?>|\n', '', plot)
                plot = client.replaceHTMLCodes(plot)
                plot = six.ensure_str(plot)

                try: content = item['type'].lower()
                except: content = '0'
                if content == None or content == '': content = '0'
                content = six.ensure_str(content)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'plot': plot,
                                  'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0', 'poster': poster, 'content': content, 'page': page, 'next': next})
            except:
                # log_utils.log('tvmaze0', 1)
                pass

        try:
            threads = []
            for i in items: threads.append(workers.Thread(items_list, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            return self.list
        except:
            # log_utils.log('tvmaze1', 1)
            return


    def tmdb_list(self, url, code=None):
        try:
            #log_utils.log('tmdb_url: ' + url)
            result = self.session.get(url, timeout=16)
            result.raise_for_status()
            result.encoding = 'utf-8'
            result = result.json() if six.PY3 else utils.json_loads_as_str(result.text)
            #log_utils.log('tmdb_result: ' + repr(result))
            if 'results' in result:
                items = result['results']
            elif 'cast' in result:
                items = result['cast']
            if not items:
                if 'with_watch_providers' in url:
                    control.infoDialog('Service not available in %s' % self.country)
                return
        except:
            log_utils.log('tmdb_list0', 1)
            return

        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total: raise Exception()
            if 'page=' not in url: raise Exception()
            next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
        except:
            next = page = ''

        for item in items:

            try:
                tmdb = str(item['id'])

                if code:
                    if not self.services_availability(tmdb, code):
                        continue

                title = item['name']

                originaltitle = item.get('original_name', '') or title

                try: rating = str(item['vote_average'])
                except: rating = ''
                if not rating: rating = '0'

                try: votes = str(item['vote_count'])
                except: votes = ''
                if not votes: votes = '0'

                try: premiered = item['first_air_date']
                except: premiered = ''
                if not premiered : premiered = '0'

                try: year = re.findall(r'(\d{4})', premiered)[0]
                except: year = ''
                if not year : year = '0'

                try: plot = item['overview']
                except: plot = ''
                if not plot: plot = '0'

                try: poster_path = item['poster_path']
                except: poster_path = ''
                if poster_path: poster = self.tm_img_link % ('500', poster_path)
                else: poster = '0'

                self.list.append({'title': title, 'originaltitle': originaltitle, 'premiered': premiered, 'year': year, 'rating': rating, 'votes': votes, 'plot': plot,
                                  'imdb': '0', 'tmdb': tmdb, 'tvdb': '0', 'poster': poster, 'page': page, 'next': next})
            except:
                log_utils.log('tmdb_list1', 1)
                pass

        return self.list


    def worker(self):
        self.meta = []
        total = len(self.list)

        for i in range(0, total): self.list[i].update({'metacache': False})

        self.list = metacache.fetch(self.list, self.lang, self.user)

        for r in range(0, total, 40):
            threads = []
            for i in range(r, r+40):
                if i < total: threads.append(workers.Thread(self.super_info, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

        if self.meta: metacache.insert(self.meta)

        self.list = [i for i in self.list if not i['tmdb'] == '0']


    def super_info(self, i):
        try:
            if self.list[i]['metacache'] == True: return

            imdb = self.list[i]['imdb'] if 'imdb' in self.list[i] else '0'
            tmdb = self.list[i]['tmdb'] if 'tmdb' in self.list[i] else '0'
            tvdb = self.list[i]['tvdb'] if 'tvdb' in self.list[i] else '0'
            list_title = self.list[i]['title']

            if tmdb == '0' and not imdb == '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=10).json()
                    id = result['tv_results'][0]
                    tmdb = id['id']
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            if tmdb == '0':
                try:
                    url = self.tm_search_link % (urllib_parse.quote(list_title)) + '&first_air_date_year=' + self.list[i]['year']
                    result = self.session.get(url, timeout=10).json()
                    results = result['results']
                    show = [r for r in results if cleantitle.get(r.get('name')) == cleantitle.get(list_title)][0]# and re.findall(r'(\d{4})', r.get('first_air_date'))[0] == self.list[i]['year']][0]
                    tmdb = show['id']
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            if tmdb == '0': raise Exception()

            en_url = self.tmdb_api_link % (tmdb)
            f_url = en_url + ',translations'
            url = en_url if self.lang == 'en' else f_url
            #log_utils.log('tmdb_url: ' + url)

            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            r.encoding = 'utf-8'
            item = r.json() if six.PY3 else utils.json_loads_as_str(r.text)
            #log_utils.log('tmdb_item: ' + repr(item))

            if imdb == '0':
                try:
                    imdb = item['external_ids']['imdb_id']
                    if not imdb: imdb = '0'
                except:
                    imdb = '0'

            if tvdb == '0':
                try:
                    tvdb = item['external_ids']['tvdb_id']
                    if not tvdb: tvdb = '0'
                    else: tvdb = str(tvdb)
                except:
                    tvdb = '0'

            original_language = item.get('original_language', '')

            if self.lang == 'en':
                en_trans_item = None
            else:
                try:
                    translations = item['translations']['translations']
                    en_trans_item = [x['data'] for x in translations if x['iso_639_1'] == 'en'][0]
                except:
                    en_trans_item = {}

            name = item.get('name', '')
            original_name = item.get('original_name', '')
            en_trans_name = en_trans_item.get('name', '') if not self.lang == 'en' else None
            #log_utils.log('self_lang: %s | original_language: %s | list_title: %s | name: %s | original_name: %s | en_trans_name: %s' % (self.lang, original_language, list_title, name, original_name, en_trans_name))

            if self.lang == 'en':
                title = label = name
            else:
                title = en_trans_name or original_name
                if original_language == self.lang:
                    label = name
                else:
                    label = en_trans_name or name
            if not title: title = list_title
            if not label: label = list_title

            plot = item.get('overview', '')
            if not plot: plot = self.list[i]['plot']

            tagline = item.get('tagline', '')
            if not tagline : tagline = '0'

            if not self.lang == 'en':
                if plot == '0':
                    en_plot = en_trans_item.get('overview', '')
                    if en_plot: plot = en_plot

                if tagline == '0':
                    en_tagline = en_trans_item.get('tagline', '')
                    if en_tagline: tagline = en_tagline

            premiered = item.get('first_air_date', '')
            if not premiered : premiered = '0'

            try: year = re.findall(r'(\d{4})', premiered)[0]
            except: year = ''
            if not year : year = '0'

            status = item.get('status', '')
            if not status : status = '0'

            if status in ['Ended', 'Canceled']:
                cache_upd = 360
            elif not item.get('next_episode_to_air'):
                cache_upd = 168
            else:
                cache_upd = 24

            try: studio = item['networks'][0]['name']
            except: studio = ''
            if not studio: studio = '0'

            try:
                genres = item['genres']
                genres = [d['name'] for d in genres]
                genre = ' / '.join(genres)
            except:
                genre = ''
            if not genre: genre = '0'

            try:
                countries = item['production_countries']
                countries = [c['name'] for c in countries]
                country = ' / '.join(countries)
            except:
                country = ''
            if not country: country = '0'

            try:
                duration = item['episode_run_time'][0]
                duration = str(duration)
            except: duration = ''
            if not duration: duration = '0'

            try:
                m = item['content_ratings']['results']
                mpaa = [d['rating'] for d in m if d['iso_3166_1'] == 'US'][0]
            except: mpaa = ''
            if not mpaa: mpaa = '0'

            try:
                last_ep = item.get('last_episode_to_air')
                if last_ep and not status in ['Ended', 'Canceled']:
                    total_episodes = str(sum([i['episode_count'] for i in item['seasons'] if i['season_number'] < last_ep['season_number'] and i['season_number'] > 0]) + last_ep['episode_number'])
                else:
                    total_episodes = str(item['number_of_episodes'])
            except:
                total_episodes = '0'

            total_seasons = str(item.get('number_of_seasons', '0'))

            try:
                crew = item['aggregate_credits']['crew']
                director = ', '.join([d['name'] for d in crew if any([x['job'] == 'Director' for x in d['jobs']])])
                writer = ', '.join([w['name'] for w in crew if any([x['job'] in ['Writer', 'Screenplay', 'Author', 'Novel', 'Characters'] for x in w['jobs']])])
            except:
                director = writer = ''
            if not director: director = '0'
            if not writer: writer = '0'

            castwiththumb = []
            try:
                c = item['aggregate_credits']['cast'][:30]
                for person in c:
                    _icon = person['profile_path']
                    icon = self.tm_img_link % ('185', _icon) if _icon else ''
                    castwiththumb.append({'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': icon})
            except:
                pass
            if not castwiththumb: castwiththumb = '0'

            poster1 = self.list[i]['poster']

            poster_path = item.get('poster_path')
            if poster_path:
                poster2 = self.tm_img_link % ('500', poster_path)
            else:
                poster2 = None

            fanart_path = item.get('backdrop_path')
            if fanart_path:
                fanart1 = self.tm_img_link % ('1280', fanart_path)
            else:
                fanart1 = '0'

            poster3 = fanart2 = None
            banner = clearlogo = clearart = landscape = '0'
            if self.hq_artwork == 'true' and not tvdb == '0':# and not self.fanart_tv_user == '':

                try:
                    r2 = self.session.get(self.fanart_tv_art_link % tvdb, headers=self.fanart_tv_headers, timeout=10)
                    r2.raise_for_status()
                    r2.encoding = 'utf-8'
                    art = r2.json() if six.PY3 else utils.json_loads_as_str(r2.text)

                    try:
                        _poster3 = art['tvposter']
                        _poster3 = [x for x in _poster3 if x.get('lang') == self.lang][::-1] + [x for x in _poster3 if x.get('lang') == 'en'][::-1] + [x for x in _poster3 if x.get('lang') in ['00', '']][::-1]
                        _poster3 = _poster3[0]['url']
                        if _poster3: poster3 = _poster3
                    except:
                        pass

                    try:
                        _fanart2 = art['showbackground']
                        _fanart2 = [x for x in _fanart2 if x.get('lang') == self.lang][::-1] + [x for x in _fanart2 if x.get('lang') == 'en'][::-1] + [x for x in _fanart2 if x.get('lang') in ['00', '']][::-1]
                        _fanart2 = _fanart2[0]['url']
                        if _fanart2: fanart2 = _fanart2
                    except:
                        pass

                    try:
                        _banner = art['tvbanner']
                        _banner = [x for x in _banner if x.get('lang') == self.lang][::-1] + [x for x in _banner if x.get('lang') == 'en'][::-1] + [x for x in _banner if x.get('lang') in ['00', '']][::-1]
                        _banner = _banner[0]['url']
                        if _banner: banner = _banner
                    except:
                        pass

                    try:
                        if 'hdtvlogo' in art: _clearlogo = art['hdtvlogo']
                        else: _clearlogo = art['clearlogo']
                        _clearlogo = [x for x in _clearlogo if x.get('lang') == self.lang][::-1] + [x for x in _clearlogo if x.get('lang') == 'en'][::-1] + [x for x in _clearlogo if x.get('lang') in ['00', '']][::-1]
                        _clearlogo = _clearlogo[0]['url']
                        if _clearlogo: clearlogo = _clearlogo
                    except:
                        pass

                    try:
                        if 'hdclearart' in art: _clearart = art['hdclearart']
                        else: _clearart = art['clearart']
                        _clearart = [x for x in _clearart if x.get('lang') == self.lang][::-1] + [x for x in _clearart if x.get('lang') == 'en'][::-1] + [x for x in _clearart if x.get('lang') in ['00', '']][::-1]
                        _clearart = _clearart[0]['url']
                        if _clearart: clearart = _clearart
                    except:
                        pass

                    try:
                        if 'tvthumb' in art: _landscape = art['tvthumb']
                        else: _landscape = art['showbackground']
                        _landscape = [x for x in _landscape if x.get('lang') == self.lang][::-1] + [x for x in _landscape if x.get('lang') == 'en'][::-1] + [x for x in _landscape if x.get('lang') in ['00', '']][::-1]
                        _landscape = _landscape[0]['url']
                        if _landscape: landscape = _landscape
                    except:
                        pass
                except:
                    #log_utils.log('fanart.tv art fail', 1)
                    pass

            poster = poster3 or poster2 or poster1
            fanart = fanart2 or fanart1

            item = {'title': title, 'originaltitle': title, 'label': label, 'year': year, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart, 'banner': banner,
                    'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'mpaa': mpaa,
                    'director': director, 'writer': writer, 'castwiththumb': castwiththumb, 'plot': plot, 'status': status, 'tagline': tagline, 'country': country,
                    'total_episodes': total_episodes, 'total_seasons': total_seasons, 'mediatype': 'tvshow', 'cache_upd': cache_upd}
            item = dict((k,v) for k, v in six.iteritems(item) if not v == '0')
            self.list[i].update(item)

            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'lang': self.lang, 'user': self.user, 'item': item}
            self.meta.append(meta)
        except:
            log_utils.log('superinfo_fail', 1)
            pass


    def tvshowDirectory(self, items):
        from sys import argv
        if not items:
            control.idle()
            control.infoDialog('No content')

        sysaddon = argv[0]

        syshandle = int(argv[1])

        addonPoster, addonFanart, addonBanner = control.addonPoster(), control.addonFanart(), control.addonBanner()

        traktCredentials = trakt.getTraktCredentialsInfo()

        kodiVersion = control.getKodiVersion()

        indicators = playcount.getTVShowIndicators(refresh=True) if action == 'tvshows' else playcount.getTVShowIndicators()

        if self.trailer_source == '0': trailerAction = 'tmdb_trailer'
        elif self.trailer_source == '1': trailerAction = 'yt_trailer'
        else: trailerAction = 'imdb_trailer'

        watchedMenu = control.lang(32068) if trakt.getTraktIndicatorsInfo() == True else control.lang(32066)

        unwatchedMenu = control.lang(32069) if trakt.getTraktIndicatorsInfo() == True else control.lang(32067)

        queueMenu = control.lang(32065)

        traktManagerMenu = control.lang(32070)

        nextMenu = control.lang(32053)

        playRandom = control.lang(32535)

        addToLibrary = control.lang(32551)

        findSimilar = control.lang(32100)

        infoMenu = control.lang(32101)

        list_items = []
        for i in items:
            try:
                label = i['label'] if 'label' in i and not i['label'] == '0' else i['title']
                status = i['status'] if 'status' in i else '0'
                try:
                    premiered = i['premiered']
                    if (premiered == '0' and status in ['Rumored', 'Planned', 'In Production', 'Post Production', 'Upcoming']) or (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))) or i['total_episodes'] == '*':
                        label = '[COLOR crimson]%s [I][Upcoming][/I][/COLOR]' % label
                except:
                    pass

                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart
                landscape = i['landscape'] if 'landscape' in i and not i['landscape'] == '0' else fanart
                banner1 = i.get('banner', '')
                banner = banner1 or fanart or addonBanner

                systitle = sysname = urllib_parse.quote_plus(i['title'])
                sysimage = urllib_parse.quote_plus(poster)

                seasons_meta = {'poster': poster, 'fanart': fanart, 'banner': banner, 'clearlogo': i.get('clearlogo', '0'), 'clearart': i.get('clearart', '0'), 'landscape': landscape}

                sysmeta = urllib_parse.quote_plus(json.dumps(seasons_meta))
                #log_utils.log('sysmeta: ' + str(sysmeta))

                imdb, tvdb, tmdb, year = i.get('imdb', ''), i.get('tvdb', ''), i.get('tmdb', ''), i.get('year', '')

                meta = dict((k,v) for k, v in six.iteritems(i) if not v == '0')
                meta.update({'imdbnumber': imdb, 'code': tmdb})
                if not 'mediatype' in meta: meta.update({'mediatype': 'tvshow'})
                meta.update({'tvshowtitle': i['title']})
                meta.update({'trailer': '%s?action=%s&name=%s&tmdb=%s&imdb=%s' % (sysaddon, trailerAction, systitle, tmdb, imdb)})
                if not 'duration' in meta: meta.update({'duration': '45'})
                elif meta['duration'] == '0': meta.update({'duration': '45'})
                try: meta.update({'duration': str(int(meta['duration']) * 60)})
                except: pass
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                except: pass
                if 'castwiththumb' in i and not i['castwiththumb'] == '0': meta.pop('cast', '0')

                meta.update({'poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape})

                try:
                    show_indicators = [i[2] for i in indicators if i[0] == imdb][0]
                    show_indicators = [i for i in show_indicators if i[0] > 0]
                    overlay = 7 if len(show_indicators) >= int(i['total_episodes']) else 6
                    if overlay == 7: meta.update({'playcount': 1, 'overlay': 7})
                    else: meta.update({'playcount': 0, 'overlay': 6})
                except:
                    show_indicators = []
                    overlay = 6
                    meta.update({'playcount': 0, 'overlay': 6})

                url = '%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)

                cm = []

                cm.append((findSimilar, 'Container.Update(%s?action=tvshows&url=%s)' % (sysaddon, urllib_parse.quote_plus(self.related_link % tmdb))))

                cm.append(('[I]Cast[/I]', 'RunPlugin(%s?action=tvcredits&tmdb=%s&status=%s)' % (sysaddon, tmdb, status)))

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=season&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (
                          sysaddon, urllib_parse.quote_plus(systitle), urllib_parse.quote_plus(year), urllib_parse.quote_plus(imdb), urllib_parse.quote_plus(tmdb)))
                          )

                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                cm.append((watchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tmdb=%s&query=7)' % (sysaddon, systitle, imdb, tmdb)))

                cm.append((unwatchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tmdb=%s&query=6)' % (sysaddon, systitle, imdb, tmdb)))

                if traktCredentials == True:
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, sysname, tmdb)))

                if kodiVersion < 17:
                    cm.append((infoMenu, 'Action(Info)'))

                cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, systitle, year, imdb, tmdb)))

                art = {'icon': poster, 'thumb': poster, 'poster': poster, 'tvshow.poster': poster, 'season.poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape}

                if 'clearlogo' in i and not i['clearlogo'] == '0':
                    art.update({'clearlogo': i['clearlogo']})

                if 'clearart' in i and not i['clearart'] == '0':
                    art.update({'clearart': i['clearart']})

                try: item = control.item(label=label, offscreen=True)
                except: item = control.item(label=label)

                item.setArt(art)
                item.addContextMenuItems(cm)

                total_episodes = i.get('total_episodes', '0')
                watched_episodes = len(show_indicators)
                try: show_progress = str(int((float(watched_episodes)/int(total_episodes))*100)) or '0'
                except: show_progress = '0'
                try: unwatched_episodes = str(int(total_episodes) - watched_episodes)
                except: unwatched_episodes = total_episodes

                item.setProperties({'TotalEpisodes': total_episodes, 'WatchedEpisodes': str(watched_episodes), 'UnWatchedEpisodes': unwatched_episodes,
                                    'WatchedProgress': show_progress, 'TotalSeasons': i.get('total_seasons', '0')})

                if kodiVersion < 20:
                    castwiththumb = i.get('castwiththumb')
                    if castwiththumb and not castwiththumb == '0':
                        if kodiVersion >= 18:
                            item.setCast(castwiththumb)
                        else:
                            cast = [(p['name'], p['role']) for p in castwiththumb]
                            meta.update({'cast': cast})

                    item.setProperty('imdb_id', imdb)
                    item.setProperty('tmdb_id', tmdb)
                    try: item.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb})
                    except: pass

                    item.setInfo(type='video', infoLabels=control.metadataClean(meta))

                    video_streaminfo = {'codec': 'h264'}
                    item.addStreamInfo('video', video_streaminfo)

                else:
                    vtag = item.getVideoInfoTag()
                    vtag.setMediaType('tvshow')
                    vtag.setTitle(i['title'])
                    vtag.setOriginalTitle(i['title'])
                    vtag.setTvShowTitle(i['title'])
                    vtag.setPlot(meta.get('plot'))
                    vtag.setPlotOutline(meta.get('plot'))
                    vtag.setYear(int(year))
                    vtag.setRating(float(i['rating']), int(i['votes'].replace(',', '')), 'imdb')
                    vtag.setMpaa(meta.get('mpaa'))
                    vtag.setDuration(int(meta['duration']))
                    vtag.setGenres(meta.get('genre', '').split(' / '))
                    vtag.setCountries(meta.get('country', '').split(' / '))
                    vtag.setTrailer(meta['trailer'])
                    vtag.setTagLine(meta.get('tagline'))
                    vtag.setStudios([meta.get('studio')])
                    vtag.setPremiered(meta.get('premiered'))
                    vtag.setTvShowStatus(meta.get('status'))
                    vtag.setIMDBNumber(imdb)
                    vtag.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb})
                    vtag.setDirectors(meta.get('director', '').split(', '))
                    vtag.setWriters(meta.get('writer', '').split(', '))
                    vtag.setSeason(int(i.get('total_seasons', '0'))) # for Estuary Available seasons info
                    vtag.setEpisode(int(total_episodes)) # for Estuary Available episodes info

                    if overlay > 6:
                        vtag.setPlaycount(1)

                    cast = []
                    if 'castwiththumb' in i and not i['castwiththumb'] == '0':
                        for p in i['castwiththumb']:
                            cast.append(control.actor(p['name'], p['role'], 0, p['thumbnail']))
                    elif 'cast' in i and not i['cast'] == '0':
                        for p in i['cast']:
                            cast.append(control.actor(p, '', 0, ''))
                    vtag.setCast(cast)

                #control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
                list_items.append((url, item, True))
            except:
                log_utils.log('addir_fail0', 1)
                pass

        try:
            url = items[0]['next']
            if url == '': raise Exception()

            icon = control.addonNext()
            url = '%s?action=tvshowPage&url=%s' % (sysaddon, urllib_parse.quote_plus(url))
            if self.code: url += '&code=%s' % urllib_parse.quote(self.code)

            if 'page' in items[0] and items[0]['page']: nextMenu += '[I] (%s)[/I]' % str(int(items[0]['page']) + 1)

            try: item = control.item(label=nextMenu, offscreen=True)
            except: item = control.item(label=nextMenu)

            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon, 'fanart': addonFanart})
            item.setProperty('SpecialSort', 'bottom')

            #control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            list_items.append((url, item, True))
        except:
            pass

        control.addItems(handle=syshandle, items=list_items, totalItems=len(list_items))
        control.content(syshandle, 'tvshows')
        control.directory(syshandle, cacheToDisc=True)
        views.setView('tvshows', {'skin.estuary': 55, 'skin.confluence': 500})


    def addDirectory(self, items, queue=False):
        from sys import argv
        if not items:
            control.idle()
            control.infoDialog('No content')

        sysaddon = argv[0]

        syshandle = int(argv[1])

        addonFanart, addonThumb, artPath = control.addonFanart(), control.addonThumb(), control.artPath()

        queueMenu = control.lang(32065)

        playRandom = control.lang(32535)

        addToLibrary = control.lang(32551)

        kodiVersion = control.getKodiVersion()

        list_items = []
        for i in items:
            try:
                name = i['name']

                plot = i.get('plot') or '[CR]'

                if i['image'].startswith('http'): thumb = i['image']
                elif not artPath == None: thumb = os.path.join(artPath, i['image'])
                else: thumb = addonThumb

                url = '%s?action=%s' % (sysaddon, i['action'])
                try: url += '&url=%s' % urllib_parse.quote_plus(i['url'])
                except: pass

                cm = []

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=show&url=%s)' % (sysaddon, urllib_parse.quote_plus(i['url']))))

                if queue == True:
                    cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try: cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowsToLibrary&url=%s)' % (sysaddon, urllib_parse.quote_plus(i['context']))))
                except: pass

                try: item = control.item(label=name, offscreen=True)
                except: item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb, 'fanart': addonFanart})
                item.addContextMenuItems(cm)

                if kodiVersion < 20:
                    item.setInfo(type='video', infoLabels={'plot': plot})
                else:
                    vtag = item.getVideoInfoTag()
                    vtag.setMediaType('video')
                    vtag.setPlot(plot)

                #control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
                list_items.append((url, item, True))
            except:
                pass

        control.addItems(handle=syshandle, items=list_items, totalItems=len(list_items))
        control.content(syshandle, '')
        control.directory(syshandle, cacheToDisc=True)
