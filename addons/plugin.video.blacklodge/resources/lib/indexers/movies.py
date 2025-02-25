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
from resources.lib.modules import bookmarks
from resources.lib.modules import cleangenre
from resources.lib.modules import cleantitle
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
from six.moves import urllib_parse, zip, range

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

import requests


params = dict(urllib_parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()
action = params.get('action')


class movies:
    def __init__(self):
        self.list = []
        self.code = ''

        self.session = requests.Session()

        self.imdb_link = 'https://www.imdb.com'
        self.trakt_link = 'https://api.trakt.tv'
        self.tmdb_link = 'https://api.themoviedb.org/3'
        self.datetime = datetime.datetime.utcnow()# - datetime.timedelta(hours = 5)
        self.systime = self.datetime.strftime('%Y%m%d%H%M%S%f')
        self.year_date = (self.datetime - datetime.timedelta(days = 365)).strftime('%Y-%m-%d')
        self.year_plus_date = (self.datetime + datetime.timedelta(days = 365)).strftime('%Y-%m-%d')
        self.months_date = (self.datetime - datetime.timedelta(days = 90)).strftime('%Y-%m-%d')
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.tm_user = control.setting('tm.user') or api_keys.tmdb_key
        self.fanart_tv_user = control.setting('fanart.tv.user')
        self.fanart_tv_headers = {'api-key': api_keys.fanarttv_key}
        if not self.fanart_tv_user == '':
            self.fanart_tv_headers.update({'client-key': self.fanart_tv_user})
        self.user = str(control.setting('fanart.tv.user')) + str(control.setting('tm.user'))
        self.lang = control.apiLanguage()['tmdb']
        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.imdb_sort = 'alpha,asc' if control.setting('imdb.sort.order') == '1' else 'date_added,desc'
        self.hq_artwork = control.setting('hq.artwork') or 'false'
        self.trailer_source = control.setting('trailer.source') or '2'
        self.country = control.setting('official.country') or 'US'

        self.fanart_tv_art_link = 'http://webservice.fanart.tv/v3/movies/%s'
        self.fanart_tv_level_link = 'http://webservice.fanart.tv/v3/level'

        ## TMDb ##
        self.tmdb_api_link = 'https://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s&append_to_response=credits,release_dates,external_ids' % ('%s', self.tm_user, self.lang)
        self.tmdb_by_imdb = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', self.tm_user)
        self.tm_search_link = 'https://api.themoviedb.org/3/search/movie?api_key=%s&language=en-US&query=%s&page=1' % (self.tm_user, '%s')
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.related_link = 'https://api.themoviedb.org/3/movie/%s/similar?api_key=%s&page=1' % ('%s', self.tm_user)

        self.tmdb_pop_link = 'https://api.themoviedb.org/3/movie/popular?api_key=%s&page=1' % self.tm_user
        self.tmdb_voted_link = 'https://api.themoviedb.org/3/discover/movie?sort_by=vote_count.desc&api_key=%s&page=1' % self.tm_user
        self.tmdb_rating_link = 'https://api.themoviedb.org/3/movie/top_rated?api_key=%s&page=1' % self.tm_user
        self.tmdb_theaters_link = 'https://api.themoviedb.org/3/movie/now_playing?api_key=%s&page=1' % self.tm_user
        self.tmdb_featured_link = 'https://api.themoviedb.org/3/trending/movie/week?api_key=%s&page=1' % self.tm_user
        self.tmdb_upcoming_link = 'https://api.themoviedb.org/3/discover/movie?with_original_language=en&release_date.gte=%s&release_date.lte=%s&with_release_type=3|2&api_key=%s&page=1' % (self.today_date, self.year_plus_date, self.tm_user)
        self.tmdb_boxoffice_link = 'https://api.themoviedb.org/3/discover/movie?sort_by=revenue.desc&api_key=%s&page=1' % self.tm_user
        self.tmdb_added_link = 'https://api.themoviedb.org/3/discover/movie?primary_release_date.gte=%s&primary_release_date.lte=%s&with_release_type=4|5|6&api_key=%s&page=1' % (self.months_date, self.today_date, self.tm_user)

        self.tmdb_genre_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&with_genres=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s')
        self.tmdb_year_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&primary_release_year=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s')
        self.tmdb_decade_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&primary_release_date.gte=%s&primary_release_date.lte=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s', '%s')
        self.tmdb_language_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&with_original_language=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s')
        self.tmdb_certification_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&certification_country=US&certification=%s&language=en-US&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', '%s', '%s')

        self.tmdb_providers_avail_link = 'https://api.themoviedb.org/3/movie/%s/watch/providers?api_key=%s' % ('%s', self.tm_user)
        self.tmdb_providers_pop_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', self.country)
        self.tmdb_providers_voted_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&sort_by=vote_count.desc&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', self.country)
        self.tmdb_providers_rated_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&sort_by=vote_average.desc&vote_count.gte=500&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, '%s', self.country)
        self.tmdb_providers_added_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&primary_release_date.gte=%s&primary_release_date.lte=%s&sort_by=primary_release_date.desc&with_watch_providers=%s&watch_region=%s&page=1' % (self.tm_user, self.year_date, self.today_date, '%s', self.country)

        ## IMDb ##
        self.genre_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&genres=%s&release_date=,date[0]&sort=moviemeter,asc&count=%s'% ('%s', self.items_per_page)
        self.year_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&release_date=%s,%s&sort=moviemeter,asc&count=%s'% ('%s', '%s', self.items_per_page)
        self.language_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&release_date=,date[0]&sort=moviemeter,asc&primary_language=%s&count=%s'% ('%s', self.items_per_page)
        self.certification_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&certificates=US:%s&release_date=,date[0]&sort=moviemeter,asc&count=%s' % ('%s', self.items_per_page)

        self.popular_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&release_date=,date[0]&sort=moviemeter,asc&groups=top_1000&count=%s' % self.items_per_page
        self.featured_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&release_date=date[365],date[60]&sort=moviemeter,asc&count=%s' % self.items_per_page
        self.rating_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&genres=!documentary&release_date=,date[0]&sort=user_rating,desc&num_votes=10000,&count=%s' % self.items_per_page
        self.views_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&sort=num_votes,desc&count=%s' % self.items_per_page
        self.theaters_link = 'https://www.imdb.com/search/title/?title_type=feature&release_date=date[120],date[0]&sort=moviemeter,asc&count=%s' % self.items_per_page
        self.boxoffice_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&sort=boxoffice_gross_us,desc&count=%s' % self.items_per_page
        self.added_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&release_date=%s,%s&sort=release_date,desc&num_votes=500,&languages=en&count=%s' % (self.year_date, self.today_date, self.items_per_page)
        self.oscars_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&sort=year,desc&groups=best_picture_winner&count=%s' % self.items_per_page

        self.keyword_link = 'https://www.imdb.com/search/title/?title_type=feature,short,tv_movie&release_date=,date[0]&sort=moviemeter,asc&keywords=%s&count=%s' % ('%s', self.items_per_page)
        self.customlist_link = 'https://www.imdb.com/list/%s/?view=detail&sort=list_order,asc&title_type=feature,tv_movie&start=0'

        self.imdblists_link = 'https://www.imdb.com/user/ur%s/lists?tab=all&sort=modified&order=desc&filter=titles' % self.imdb_user
        self.imdblist_link = 'https://www.imdb.com/list/%s/?sort=%s&title_type=feature,short,tv_movie,video&start=0' % ('%s', self.imdb_sort)
        self.imdbwatchlist_link = 'https://www.imdb.com/user/ur%s/watchlist/?sort=%s&title_type=feature,short,tv_movie,video&start=0' % (self.imdb_user, self.imdb_sort)

        ## Trakt ##
        self.trending_link = 'https://api.trakt.tv/movies/trending?limit=%s&page=1' % self.items_per_page
        self.mosts_link = 'https://api.trakt.tv/movies/%s/%s?limit=%s&page=1' % ('%s', '%s', self.items_per_page)
        self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
        self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000'
        self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items'
        self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/movies'
        self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/movies'
        self.traktfeatured_link = 'https://api.trakt.tv/recommendations/movies?ignore_collected=true&ignore_watchlisted=true&limit=40'
        self.trakthistory_link = 'https://api.trakt.tv/users/me/history/movies?limit=%s&page=1' % self.items_per_page
        self.onDeck_link = 'https://api.trakt.tv/sync/playback/movies?limit=%s' % self.items_per_page
        # self.search_link = 'https://api.trakt.tv/search/movie?limit=20&page=1&query='
        # self.related_link = 'https://api.trakt.tv/movies/%s/related'


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
                    if url == self.trakthistory_link: raise Exception()
                    #if not '/users/me/' in url: raise Exception()
                    if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user): raise Exception()
                    self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                except:
                    self.list = self.trakt_list(url, self.trakt_user)

                if '/users/me/' in url and '/collection/' in url:
                    self.list = sorted(self.list, key=lambda k: utils.title_key(k['title']))

                if idx == True: self.worker()

            elif u in self.trakt_link and '/sync/playback/' in url:
                self.list = self.trakt_list(url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['paused_at']), reverse=True)
                if idx == True: self.worker()

            elif u in self.trakt_link:
                self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                if idx == True: self.worker()

            elif u in self.imdb_link:
                self.list = cache.get(self.imdb_list, 24, url)
                if idx == True: self.worker()

            elif u in self.tmdb_link:
                self.list = cache.get(self.tmdb_list, 24, url, self.code)
                if self.code and not self.list:
                    return control.infoDialog('Nothing found on your services')
                if idx == True: self.worker()


            #log_utils.log('movies_get_list: ' + str(self.list))
            if idx == True and create_directory == True: self.movieDirectory(self.list)
            return self.list
        except:
            log_utils.log('movies_get', 1)
            pass


    def widget(self):
        setting = control.setting('movie.widget')

        if setting == '2':
            self.get(self.trending_link)
        elif setting == '3':
            self.get(self.popular_link)
        elif setting == '4':
            self.get(self.theaters_link)
        elif setting == '5':
            self.get(self.added_link)
        else:
            self.get(self.featured_link)


    def search(self, code=''):
        code = urllib_parse.quote(code) if code else ''

        navigator.navigator().addDirectoryItem(32603, 'movieSearchnew&code=%s' % code, 'search.png', 'DefaultMovies.png')

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.executescript("CREATE TABLE IF NOT EXISTS movies (ID Integer PRIMARY KEY AUTOINCREMENT, term);")
        except:
            pass

        dbcur.execute("SELECT * FROM movies ORDER BY ID DESC")
        lst = []

        delete_option = False
        for (id, term) in dbcur.fetchall():
            if term not in str(lst):
                delete_option = True
                navigator.navigator().addDirectoryItem(term.title(), 'movieSearchterm&name=%s&code=%s' % (term, code), 'search.png', 'DefaultMovies.png', context=(32644, 'movieDeleteterm&name=%s' % term))
                lst += [(term)]
        dbcur.close()

        if delete_option:
            navigator.navigator().addDirectoryItem(32605, 'clearCacheSearch&select=movies', 'tools.png', 'DefaultAddonProgram.png')

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
        dbcur.execute("DELETE FROM movies WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO movies VALUES (?,?)", (None,q))
        dbcon.commit()
        dbcur.close()
        url = self.tm_search_link % urllib_parse.quote(q)
        self.get(url, code=code)


    def search_term(self, q, code=''):
        control.idle()
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM movies WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO movies VALUES (?,?)", (None, q))
        dbcon.commit()
        dbcur.close()
        url = self.tm_search_link % urllib_parse.quote(q)
        self.get(url, code=code)


    def delete_term(self, q):
        control.idle()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM movies WHERE term = ?", (q,))
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
                'action': 'movies'
            })
        self.addDirectory(self.list)
        return self.list


    def keywords(self): # Poseidon lists/icons (by Soulless)
        keywords = [
            ('anime', 'anime.jpg'),
            ('avant-garde', 'avant.jpg'),
            ('b-movie', 'bmovie.png'),
            ('based-on-true-story', 'true.jpg'),
            ('biker', 'biker.jpg'),
            ('breaking-the-fourth-wall', 'breaking.jpg'),
            ('business', 'business.jpg'),
            ('caper', 'caper.jpg'),
            ('car-chase', 'chase.png'),
            ('chick-flick', 'chick.png'),
            ('christmas', 'christmas.png'),
            ('coming-of-age', 'coming.jpg'),
            ('competition', 'comps.jpg'),
            ('cult', 'cult.png'),
            ('cyberpunk', 'cyber.jpg'),
            ('dc-comics', 'dc.png'),
            ('disney', 'disney.png'),
            ('drugs', 'drug.png'),
            ('dystopia', 'dystopia.jpg'),
            ('easter', 'easter.png'),
            ('epic', 'epic.png'),
            ('espionage', 'espionage.jpg'),
            ('existential', 'exis.jpg'),
            ('experimental-film', 'experimental.jpg'),
            ('fairy-tale', 'fairytale.png'),
            ('farce', 'farce.jpg'),
            ('femme-fatale', 'femme.jpg'),
            ('futuristic', 'futuristic.jpg'),
            ('halloween', 'halloween.png'),
            ('hearing-characters-thoughts', 'character.jpg'),
            ('heist', 'heist.png'),
            ('high-school', 'highschool.jpg'),
            ('horror-movie-remake', 'horror.jpg'),
            ('kidnapping', 'kidnapped.jpg'),
            ('kung-fu', 'kungfu.png'),
            ('loner', 'loner.jpg'),
            ('marvel-comics', 'marvel.png'),
            ('monster', 'monster.jpg'),
            ('neo-noir', 'neo.jpg'),
            ('new-year', 'newyear.png'),
            ('official-james-bond-series', 'bond.png'),
            ('parenthood', 'parenthood.png'),
            ('parody', 'parody.jpg'),
            ('post-apocalypse', 'apocalypse.png'),
            ('private-eye', 'dick.png'),
            ('racism', 'race.png'),
            ('remake', 'remake.jpg'),
            ('road-movie', 'road.png'),
            ('robot', 'robot.png'),
            ('satire', 'satire.jpg'),
            ('schizophrenia', 'schiz.jpg'),
            ('serial-killer', 'serial.jpg'),
            ('slasher', 'slasher.png'),
            ('spirituality', 'spiritual.png'),
            ('spoof', 'spoof.jpg'),
            ('star-wars', 'starwars.png'),
            ('steampunk', 'steampunk.png'),
            ('superhero', 'superhero.png'),
            ('supernatural', 'supernatural.png'),
            ('tech-noir', 'tech.jpg'),
            ('thanksgiving', 'thanksgiving.png'),
            ('time-travel', 'time.png'),
            ('vampire', 'vampire.png'),
            ('virtual-reality', 'vr.png'),
            ('wilhelm-scream', 'wilhelm.png'),
            ('zombie', 'zombie.png')
        ]

        for i in keywords:
            title = urllib_parse.unquote(i[0]).replace('-', ' ').title()
            self.list.append(
                {
                    'name': title,
                    'url': self.keyword_link % i[0],
                    'image': 'poseidon/' + i[1],
                    'action': 'movies'
                })
        self.addDirectory(self.list)
        return self.list


    def keywords2(self):
        url = 'https://www.imdb.com/search/keyword/?s=kw'
        r = cache.get(client.request, 168, url)
        rows = client.parseDOM(r, 'a', attrs={'class': 'ipc-chip ipc-chip--on-base-accent2'})
        for row in rows:
            kw = client.parseDOM(row, 'span')[0].replace('&#x27;', "'")
            self.list.append(
                {
                    'name': kw.title(),
                    'url': self.keyword_link % urllib_parse.quote(kw),
                    'image': 'imdb.png',
                    'action': 'movies'
                })
        self.addDirectory(self.list)
        return self.list


    def custom_lists(self):
        lists = [('ls004043006', 'Modern Horror: Top 150'),
                 ('ls054656838', 'Horror Movie Series'),
                 ('ls027849454', 'Horror Of The Skull Posters'),
                 ('ls076464829', 'Top Satirical Movies'),
                 ('ls009668082', 'Greatest Science Fiction'),
                 ('ls057039446', 'Famous and Infamous Movie Couples'),
                 ('ls003062015', 'Top Private Eye Movies'),
                 ('ls027822154', 'Sleeper Hit Movies'),
                 ('ls004943234', 'Cult Horror Movies'),
                 ('ls020387857', 'Heist Caper Movies'),
                 ('ls062392787', 'Artificial Intelligence'),
                 ('ls051289348', 'Stephen King Movies and Adaptations'),
                 ('ls063259747', 'Alien Invasion'),
                 ('ls063204479', 'Contract Killers'),
                 ('ls062247190', 'Heroic Bloodshed'),
                 ('ls062218265', 'Conspiracy'),
                 ('ls075582795', 'Top Kung Fu'),
                 ('ls075785141', 'Movies Based In One Room'),
                 ('ls058963815', 'Movies For Intelligent People'),
                 ('ls069754038', 'Inspirational Movies'),
                 ('ls070949682', 'Tech Geeks'),
                 ('ls077141747', 'Movie Clones'),
                 ('ls062760686', 'Obscure Underrated Movies'),
                 ('ls020576693', 'Smut and Trash'),
                 ('ls066797820', 'Revenge'),
                 ('ls066222382', 'Motivational'),
                 ('ls062746803', 'Disaster & Apocalyptic'),
                 ('ls066191116', 'Music or Musical Movies'),
                 ('ls066746282', 'Mental, Physical Illness and Disability Movies'),
                 ('ls066370089', 'Best Twist Ending Movies'),
                 ('ls066780524', 'Heists, Cons, Scams & Robbers'),
                 ('ls066135354', 'Road Trip & Travel'),
                 ('ls066367722', 'Spy - CIA - MI5 - MI6 - KGB'),
                 ('ls066502835', 'Prison & Escape'),
                 ('ls066198904', 'Courtroom'),
                 ('ls068335911', 'Father - Son'),
                 ('ls057631565', 'Based on a True Story'),
                 ('ls064685738', 'Man Vs. Nature'),
                 ('ls066176690', 'Gangster'),
                 ('ls066113037', 'Teenage'),
                 ('ls069248253', 'Old Age'),
                 ('ls063841856', 'Serial Killers'),
                 ('ls066788382', 'Addiction'),
                 ('ls066184124', 'Time Travel'),
                 ('ls021557769', 'Puff Puff Pass'),
                 ('ls008462416', 'Artists'),
                 ('ls057723258', 'Love'),
                 ('ls057106830', 'Winter Is Here'),
                 ('ls064085103', 'Suicide'),
                 ('ls057104247', 'Alchoholic'),
                 ('ls070389024', 'Video Games'),
                 ('ls051708902', 'Shocking Movie Scenes'),
                 ('ls057785252', 'Biographical'),
                 ('ls051072059', 'Movies to Teach You a Thing or Two')
        ]

        for i in lists: self.list.append(
            {
                'name': i[1],
                'url': self.customlist_link % i[0],
                'image': 'imdb.png',
                'action': 'movies'
            })

        self.list = sorted(self.list, key=lambda k: k['name'])
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
            ('History', 'history', True),
            ('Horror', 'horror', True),
            ('Music ', 'music', True),
            ('Musical', 'musical', True),
            ('Mystery', 'mystery', True),
            ('Romance', 'romance', True),
            ('Science Fiction', 'sci_fi', True),
            ('Sport', 'sport', True),
            ('Superhero', 'superhero', False),
            ('Thriller', 'thriller', True),
            ('War', 'war', True),
            ('Western', 'western', True)
        ]

        for i in genres: self.list.append(
            {
                'name': cleangenre.lang(i[0], self.lang),
                'url': self.genre_link % (i[1] + ',!documentary' if i[1] != 'documentary' else i[1]) if i[2] else self.keyword_link % i[1],
                'image': 'genres/{}.png'.format(i[1]),
                'action': 'movies'
            })
        self.addDirectory(self.list)
        return self.list


    def tmdb_genres(self, code=''):
        genres = [
            ('Action', '28', 'action'),
            ('Adventure', '12', 'adventure'),
            ('Animation', '16', 'animation'),
            ('Comedy', '35', 'comedy'),
            ('Crime', '80', 'crime'),
            ('Documentary', '99', 'documentary'),
            ('Drama', '18', 'drama'),
            ('Family', '10751', 'family'),
            ('Fantasy', '14', 'fantasy'),
            ('History', '36', 'history'),
            ('Horror', '27', 'horror'),
            ('Music', '10402', 'music'),
            ('Mystery', '9648', 'mystery'),
            ('Romance', '10749', 'romance'),
            ('Science Fiction', '878', 'sci_fi'),
            ('TV Movie', '10770', 'reality_tv'),
            ('Thriller', '53', 'thriller'),
            ('War', '10752', 'war'),
            ('Western', '37', 'western')
        ]

        region = self.country if code else ''

        for i in genres: self.list.append(
            {
                'name': cleangenre.lang(i[0], self.lang),
                'url': self.tmdb_genre_link % (i[1], code, region),
                'image': 'genres/{}.png'.format(i[2]),
                'action': 'movies'
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
            ('Macedonian', 'mk'),
            ('Norwegian', 'no'),
            ('Persian', 'fa'),
            ('Polish', 'pl'),
            ('Portuguese', 'pt'),
            ('Punjabi', 'pa'),
            ('Romanian', 'ro'),
            ('Russian', 'ru'),
            ('Serbian', 'sr'),
            ('Slovenian', 'sl'),
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
                'action': 'movies'
            })
        self.addDirectory(self.list)
        return self.list


    def certifications(self, code='', tmdb=False):
        certificates = ['G', 'PG', 'PG-13', 'R', 'NC-17']

        region = self.country if code else ''

        for i in certificates: self.list.append(
            {
                'name': i,
                'url': self.certification_link % i if not tmdb else self.tmdb_certification_link % (i, code, region),
                'image': 'mpaa/{}.png'.format(i),
                'action': 'movies'
            })
        self.addDirectory(self.list)
        return self.list


    def years(self, code='', tmdb=False):
        region = self.country if code else ''

        year = (self.datetime.strftime('%Y'))
        for i in range(int(year)-0, 1900, -1): self.list.append(
            {
                'name': str(i),
                'url': self.year_link % (str(i), str(i)) if not tmdb else self.tmdb_year_link % (str(i), code, region),
                'image': 'years.png',
                'action': 'movies'
            })
        self.addDirectory(self.list)
        return self.list


    def decades(self, code='', tmdb=False):
        region = self.country if code else ''

        year = (self.datetime.strftime('%Y'))
        dec = int(year[:3]) * 10
        for i in range(dec, 1890, -10): self.list.append(
            {
                'name': str(i) + 's',
                'url': self.year_link % (str(i), str(i+9)) if not tmdb else self.tmdb_decade_link % (str(i) + '-01-01', str(i+9) + '-12-31', code, region),
                'image': 'years.png',
                'action': 'movies'
            })
        self.addDirectory(self.list)
        return self.list


    def services(self, code):
        _code = urllib_parse.quote(code)

        navigator.navigator().addDirectoryItem(32011, 'movieTmdbGenres&code=%s' % _code, 'genres.png', 'DefaultMovies.png')
        navigator.navigator().addDirectoryItem(32012, 'movieYears&code=%s&tmdb=True' % _code, 'years.png', 'DefaultMovies.png')
        navigator.navigator().addDirectoryItem(32123, 'movieDecades&code=%s&tmdb=True' % _code, 'years.png', 'DefaultMovies.png')
        navigator.navigator().addDirectoryItem(32015, 'movieCertificates&code=%s&tmdb=True' % _code, 'certificates.png', 'DefaultMovies.png')
        navigator.navigator().addDirectoryItem(32014, 'movieLanguages&code=%s&tmdb=True' % _code, 'languages.png', 'DefaultMovies.png')

        self.list.append(
            {
                'name': control.lang(32018),
                'url': self.tmdb_providers_pop_link % code,
                'image': 'people-watching.png',
                'action': 'movies'
            })
        self.list.append(
            {
                'name': control.lang(32023),
                'url': self.tmdb_providers_rated_link % code,
                'image': 'highly-rated.png',
                'action': 'movies'
            })
        self.list.append(
            {
                'name': control.lang(32019),
                'url': self.tmdb_providers_voted_link % code,
                'image': 'most-voted.png',
                'action': 'movies'
            })
        self.list.append(
            {
                'name': control.lang(32568),
                'url': self.tmdb_providers_added_link % code,
                'image': 'latest-movies.png',
                'action': 'movies'
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
            self.list[i].update({'action': 'movies'})
        self.list = sorted(self.list, key=lambda k: (k['image'], k['name'].lower()))
        self.addDirectory(self.list, queue=True)
        return self.list


    def trakt_list(self, url, user):
        try:
            q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib_parse.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q
            #log_utils.log('movies_trakt_list_u: ' + str(u))

            result = trakt.getTraktAsJson(u)

            items = []
            for i in result:
                try: items.append(i['movie'])
                except: pass
            if len(items) == 0:
                items = result
            #log_utils.log('movies_trakt_list_items: ' + str(items))
        except:
            log_utils.log('movies_trakt_list0', 1)
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

        for item in items:
            try:
                title = item['title']
                title = client.replaceHTMLCodes(title)

                year = item.get('year')
                if year: year = re.sub(r'[^0-9]', '', str(year))
                else: year = '0'
                #if int(year) > int((self.datetime).strftime('%Y')): raise Exception()

                imdb = item.get('ids', {}).get('imdb')
                if not imdb: imdb = '0'
                else: imdb = 'tt' + re.sub(r'[^0-9]', '', str(imdb))

                tmdb = item.get('ids', {}).get('tmdb')
                if not tmdb: tmdb == '0'
                else: tmdb = str(tmdb)

                premiered = item.get('released')
                if premiered: premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                else: premiered = '0'

                genre = item.get('genres')
                if genre:
                    genre = [i.title() for i in genre]
                    genre = ' / '.join(genre)
                else: genre = '0'

                duration = item.get('runtime')
                if duration: duration = str(duration)
                else: duration = '0'

                rating = item.get('rating')
                if rating and not rating == '0.0': rating = str(rating)
                else: rating = '0'

                try: votes = str(item['votes'])
                except: votes = '0'
                try: votes = str(format(int(votes),',d'))
                except: pass
                if votes == None: votes = '0'

                mpaa = item.get('certification')
                if not mpaa: mpaa = '0'

                country = item.get('country')
                if not country: country = '0'
                else: country = country.upper()

                tagline = item.get('tagline')
                if tagline: tagline = client.replaceHTMLCodes(tagline)
                else: tagline = '0'

                plot = item.get('overview')
                if plot: plot = client.replaceHTMLCodes(plot)
                else: plot = '0'

                paused_at = item.get('paused_at', '0') or '0'
                paused_at = re.sub('[^0-9]+', '', paused_at)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes,
                                  'mpaa': mpaa, 'plot': plot, 'tagline': tagline, 'imdb': imdb, 'imdbnumber': imdb, 'tmdb': tmdb, 'country': country, 'tvdb': '0', 'poster': '0',
                                  'paused_at': paused_at, 'mediatype': 'movie', 'page': page, 'next': next})
            except:
                log_utils.log('movies_trakt_list1', 1)
                pass

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

            #log_utils.log('imdb_url: ' + repr(url))
        except:
            log_utils.log('imdb_list fail', 1)
            return self.list

        def imdb_userlist(link):
            result = client.request(link)
            data = re.findall('<script id="__NEXT_DATA__" type="application/json">({.+?})</script>', result)[0]
            data = utils.json_loads_as_str(data)
            #log_utils.log(repr(data))
            if '/list/' in link:
                data = data['props']['pageProps']['mainColumnData']['list']['titleListItemSearch']['edges']
            elif '/user/' in link:
                data = data['props']['pageProps']['mainColumnData']['predefinedList']['titleListItemSearch']['edges']
            data = [item['listItem'] for item in data if item['listItem']['titleType']['id'] in ['movie', 'tvMovie', 'short', 'video']]
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
                #log_utils.log(repr(items))
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
                #log_utils.log(repr(data))
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
                    duration = item.get('runtime', {}).get('seconds', 0)
                    if duration: duration = str(int(duration / 60))
                    else: duration = '0'
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
                    duration = item.get('runtime')
                    if duration: duration = str(int(duration / 60))
                    else: duration = '0'
                    imdb = item['titleId']

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa,
                                  'director': '0', 'plot': plot, 'tagline': '0', 'imdb': imdb, 'imdbnumber': imdb, 'tmdb': '0', 'tvdb': '0', 'poster': poster, 'cast': '0',
                                  'mediatype': 'movie', 'page': page, 'next': next})
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


    def tmdb_list(self, url, code):
        try:
            #log_utils.log(url)
            result = self.session.get(url, timeout=16)
            result.raise_for_status()
            result.encoding = 'utf-8'
            result = result.json() if six.PY3 else utils.json_loads_as_str(result.text)
            items = result['results']
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

                title = item['title']

                originaltitle = item.get('original_title', '') or title

                try: rating = str(item['vote_average'])
                except: rating = ''
                if not rating: rating = '0'

                try: votes = str(item['vote_count'])
                except: votes = ''
                if not votes: votes = '0'

                try: premiered = item['release_date']
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

                self.list.append({'title': title, 'originaltitle': originaltitle, 'premiered': premiered, 'year': year, 'rating': rating, 'votes': votes, 'plot': plot, 'imdb': '0',
                                  'tmdb': tmdb, 'tvdb': '0', 'mpaa': '0', 'poster': poster, 'mediatype': 'movie', 'page': page, 'next': next})
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

        self.list = [i for i in self.list if not i['imdb'] == '0']

        #self.list = metacache.local(self.list, self.tm_img_link, 'poster', 'fanart')


    def super_info(self, i):
        try:
            if self.list[i]['metacache'] == True: return

            imdb = self.list[i]['imdb'] if 'imdb' in self.list[i] else '0'
            tmdb = self.list[i]['tmdb'] if 'tmdb' in self.list[i] else '0'
            list_title = self.list[i]['title']

            if tmdb == '0' and not imdb == '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=16).json()
                    id = result['movie_results'][0]
                    tmdb = id['id']
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            # if tmdb == '0':
                # try:
                    # url = self.tm_search_link % (urllib_parse.quote(list_title)) + '&year=' + self.list[i]['year']
                    # result = self.session.get(url, timeout=16).json()
                    # results = result['results']
                    # movie = [r for r in results if cleantitle.get(r.get('name')) == cleantitle.get(list_title)][0]# and re.findall(r'(\d{4})', r.get('first_air_date'))[0] == self.list[i]['year']][0]
                    # tmdb = movie.get('id')
                    # if not tmdb: tmdb = '0'
                    # else: tmdb = str(tmdb)
                # except:
                    # pass

            id = tmdb if not tmdb == '0' else imdb
            if id == '0': raise Exception()

            en_url = self.tmdb_api_link % (id)
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

            original_language = item.get('original_language', '')

            if self.lang == 'en':
                en_trans_item = None
            else:
                try:
                    translations = item['translations']['translations']
                    en_trans_item = [x['data'] for x in translations if x['iso_639_1'] == 'en'][0]
                except:
                    en_trans_item = {}

            name = item.get('title', '')
            original_name = item.get('original_title', '')
            en_trans_name = en_trans_item.get('title', '') if not self.lang == 'en' else None
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

            plot = item.get('overview') or self.list[i]['plot']

            tagline = item.get('tagline') or '0'

            if not self.lang == 'en':
                if plot == '0':
                    en_plot = en_trans_item.get('overview', '')
                    if en_plot: plot = en_plot

                if tagline == '0':
                    en_tagline = en_trans_item.get('tagline', '')
                    if en_tagline: tagline = en_tagline

            status = item.get('status') or '0'

            premiered = item.get('release_date') or '0'

            if premiered == '0' or (int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date)))):
                cache_upd = 48
            else:
                cache_upd = 360

            try: _year = re.findall(r'(\d{4})', premiered)[0]
            except: _year = ''
            if not _year : _year = '0'
            year = self.list[i]['year'] if not self.list[i]['year'] == '0' else _year

            try: studio = item['production_companies'][0]['name']
            except: studio = ''
            if not studio: studio = '0'

            try:
                genre = item['genres']
                genre = [d['name'] for d in genre]
                genre = ' / '.join(genre)
            except:
                genre = ''
            if not genre: genre = '0'

            try:
                country = item['production_countries']
                country = [c['name'] for c in country]
                country = ' / '.join(country)
            except:
                country = ''
            if not country: country = '0'

            try:
                duration = str(item['runtime'])
            except:
                duration = ''
            if not duration: duration = '0'

            mpaa = self.list[i]['mpaa']
            if mpaa == '0':
                try:
                    m = item['release_dates']['results']
                    m = [i['release_dates'] for i in m if i['iso_3166_1'] == 'US'][0]
                    for c in m:
                        if c['certification']:
                            if c['type'] not in [3, 4, 5, 6]:
                                continue
                            mpaa = c['certification']
                            break
                except:
                    pass

            # rating = self.list[i]['rating']
            # votes = self.list[i]['votes']
            # if rating == votes == '0':
                # try: rating = str(item['vote_average'])
                # except: rating = ''
                # if not rating: rating = '0'
                # try: votes = str(item['vote_count'])
                # except: votes = ''
                # if not votes: votes = '0'

            castwiththumb = []
            try:
                c = item['credits']['cast'][:30]
                for person in c:
                    _icon = person['profile_path']
                    icon = self.tm_img_link % ('185', _icon) if _icon else ''
                    castwiththumb.append({'name': person['name'], 'role': person['character'], 'thumbnail': icon})
            except:
                pass
            if not castwiththumb: castwiththumb = '0'

            try:
                crew = item['credits']['crew']
                director = ', '.join([d['name'] for d in [x for x in crew if x['job'] == 'Director']])
                writer = ', '.join([w['name'] for w in [y for y in crew if y['job'] in ['Writer', 'Screenplay', 'Author', 'Novel']]])
            except:
                director = writer = '0'

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
            banner = clearlogo = clearart = landscape = discart = '0'
            if self.hq_artwork == 'true' and not imdb == '0':# and not self.fanart_tv_user == '':

                try:
                    r2 = self.session.get(self.fanart_tv_art_link % imdb, headers=self.fanart_tv_headers, timeout=10)
                    r2.raise_for_status()
                    r2.encoding = 'utf-8'
                    art = r2.json() if six.PY3 else utils.json_loads_as_str(r2.text)

                    try:
                        _poster3 = art['movieposter']
                        _poster3 = [x for x in _poster3 if x.get('lang') == self.lang][::-1] + [x for x in _poster3 if x.get('lang') == 'en'][::-1] + [x for x in _poster3 if x.get('lang') in ['00', '']][::-1]
                        _poster3 = _poster3[0]['url']
                        if _poster3: poster3 = _poster3
                    except:
                        pass

                    try:
                        if 'moviebackground' in art: _fanart2 = art['moviebackground']
                        else: _fanart2 = art['moviethumb']
                        _fanart2 = [x for x in _fanart2 if x.get('lang') == self.lang][::-1] + [x for x in _fanart2 if x.get('lang') == 'en'][::-1] + [x for x in _fanart2 if x.get('lang') in ['00', '']][::-1]
                        _fanart2 = _fanart2[0]['url']
                        if _fanart2: fanart2 = _fanart2
                    except:
                        pass

                    try:
                        _banner = art['moviebanner']
                        _banner = [x for x in _banner if x.get('lang') == self.lang][::-1] + [x for x in _banner if x.get('lang') == 'en'][::-1] + [x for x in _banner if x.get('lang') in ['00', '']][::-1]
                        _banner = _banner[0]['url']
                        if _banner: banner = _banner
                    except:
                        pass

                    try:
                        if 'hdmovielogo' in art: _clearlogo = art['hdmovielogo']
                        else: _clearlogo = art['clearlogo']
                        _clearlogo = [x for x in _clearlogo if x.get('lang') == self.lang][::-1] + [x for x in _clearlogo if x.get('lang') == 'en'][::-1] + [x for x in _clearlogo if x.get('lang') in ['00', '']][::-1]
                        _clearlogo = _clearlogo[0]['url']
                        if _clearlogo: clearlogo = _clearlogo
                    except:
                        pass

                    try:
                        if 'hdmovieclearart' in art: _clearart = art['hdmovieclearart']
                        else: _clearart = art['clearart']
                        _clearart = [x for x in _clearart if x.get('lang') == self.lang][::-1] + [x for x in _clearart if x.get('lang') == 'en'][::-1] + [x for x in _clearart if x.get('lang') in ['00', '']][::-1]
                        _clearart = _clearart[0]['url']
                        if _clearart: clearart = _clearart
                    except:
                        pass

                    try:
                        if 'moviethumb' in art: _landscape = art['moviethumb']
                        else: _landscape = art['moviebackground']
                        _landscape = [x for x in _landscape if x.get('lang') == self.lang][::-1] + [x for x in _landscape if x.get('lang') == 'en'][::-1] + [x for x in _landscape if x.get('lang') in ['00', '']][::-1]
                        _landscape = _landscape[0]['url']
                        if _landscape: landscape = _landscape
                    except:
                        pass

                    try:
                        if 'moviedisc' in art: _discart = art['moviedisc']
                        _discart = [x for x in _discart if x.get('lang') == self.lang][::-1] + [x for x in _discart if x.get('lang') == 'en'][::-1] + [x for x in _discart if x.get('lang') in ['00', '']][::-1]
                        _discart = _discart[0]['url']
                        if _discart: discart = _discart
                    except:
                        pass
                except:
                    #log_utils.log('fanart.tv art fail', 1)
                    pass

            poster = poster3 or poster2 or poster1
            fanart = fanart2 or fanart1

            item = {'title': title, 'originaltitle': title, 'label': label, 'year': year, 'imdb': imdb, 'tmdb': tmdb, 'poster': poster, 'banner': banner, 'fanart': fanart, 'clearlogo': clearlogo,
                    'clearart': clearart, 'landscape': landscape, 'discart': discart, 'premiered': premiered, 'genre': genre, 'duration': duration, 'mpaa': mpaa, 'director': director, 'writer': writer,
                    'castwiththumb': castwiththumb, 'plot': plot, 'tagline': tagline, 'status': status, 'studio': studio, 'country': country, 'mediatype': 'movie', 'cache_upd': cache_upd}
            item = dict((k,v) for k, v in six.iteritems(item) if not v == '0')
            self.list[i].update(item)

            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0', 'lang': self.lang, 'user': self.user, 'item': item}
            self.meta.append(meta)
        except:
            log_utils.log('superinfo_fail', 1)
            pass


    def movieDirectory(self, items):
        from sys import argv
        if not items:
            control.idle()
            control.infoDialog('No content')

        sysaddon = argv[0]

        syshandle = int(argv[1])

        addonPoster, addonFanart, addonBanner = control.addonPoster(), control.addonFanart(), control.addonBanner()

        traktCredentials = trakt.getTraktCredentialsInfo()

        kodiVersion = control.getKodiVersion()

        isPlayable = True if not 'plugin' in control.infoLabel('Container.PluginName') else False

        indicators = playcount.getMovieIndicators(refresh=True) if action == 'movies' else playcount.getMovieIndicators()

        if self.trailer_source == '0': trailerAction = 'tmdb_trailer'
        elif self.trailer_source == '1': trailerAction = 'yt_trailer'
        else: trailerAction = 'imdb_trailer'

        playbackMenu = control.lang(32063) if control.setting('hosts.mode') == '2' else control.lang(32064)

        watchedMenu = control.lang(32068) if trakt.getTraktIndicatorsInfo() == True else control.lang(32066)

        unwatchedMenu = control.lang(32069) if trakt.getTraktIndicatorsInfo() == True else control.lang(32067)

        queueMenu = control.lang(32065)

        traktManagerMenu = control.lang(32070)

        nextMenu = control.lang(32053)

        addToLibrary = control.lang(32551)

        clearProviders = control.lang(32081)

        findSimilar = control.lang(32100)

        infoMenu = control.lang(32101)

        list_items = []
        for i in items:
            try:
                imdb, tmdb, title, year = i['imdb'], i['tmdb'], i['originaltitle'], i['year']
                label = i['label'] if 'label' in i and not i['label'] == '0' else title
                label = '%s (%s)' % (label, year)
                status = i['status'] if 'status' in i else '0'
                try:
                    premiered = i['premiered']
                    if (premiered == '0' and status in ['Rumored', 'Planned', 'In Production', 'Post Production', 'Upcoming']) or (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))):
                        label = '[COLOR crimson]%s [I][Upcoming][/I][/COLOR]' % label
                except:
                    pass

                sysname = urllib_parse.quote_plus('%s (%s)' % (title, year))
                systitle = urllib_parse.quote_plus(title)

                meta = dict((k,v) for k, v in six.iteritems(i) if not v == '0')
                meta.update({'imdbnumber': imdb, 'code': tmdb})
                meta.update({'trailer': '%s?action=%s&name=%s&tmdb=%s&imdb=%s' % (sysaddon, trailerAction, systitle, tmdb, imdb)})
                if not 'mediatype' in meta: meta.update({'mediatype': 'movie'})
                if not 'duration' in meta or meta['duration'] in ['0', 'None']: meta.update({'duration': '120'})
                try: meta.update({'duration': str(int(meta['duration']) * 60)})
                except: pass
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                except: pass
                if 'castwiththumb' in i and not i['castwiththumb'] == '0': meta.pop('cast', '0')

                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart
                banner = i['banner'] if 'banner' in i and not i['banner'] == '0' else addonBanner
                landscape = i['landscape'] if 'landscape' in i and not i['landscape'] == '0' else fanart
                meta.update({'poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape})

                sysmeta = urllib_parse.quote_plus(json.dumps(meta))

                url = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta, self.systime)
                sysurl = urllib_parse.quote_plus(url)

                #path = '%s?action=play&title=%s&year=%s&imdb=%s' % (sysaddon, systitle, year, imdb)

                cm = []

                cm.append((findSimilar, 'Container.Update(%s?action=movies&url=%s)' % (sysaddon, urllib_parse.quote_plus(self.related_link % tmdb))))

                cm.append(('[I]Cast[/I]', 'RunPlugin(%s?action=moviecredits&tmdb=%s&status=%s)' % (sysaddon, tmdb, status)))

                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try:
                    overlay = int(playcount.getMovieOverlay(indicators, imdb))
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=moviePlaycount&imdb=%s&query=6)' % (sysaddon, imdb)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=moviePlaycount&imdb=%s&query=7)' % (sysaddon, imdb)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except:
                    overlay = 6

                if traktCredentials == True:
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&imdb=%s&content=movie)' % (sysaddon, sysname, imdb)))

                cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))

                if kodiVersion < 17:
                    cm.append((infoMenu, 'Action(Info)'))

                cm.append((addToLibrary, 'RunPlugin(%s?action=movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, sysname, systitle, year, imdb, tmdb)))

                cm.append(('[I]Scrape Filterless[/I]', 'RunPlugin(%s?action=playUnfiltered&title=%s&year=%s&imdb=%s&meta=%s&t=%s)' % (sysaddon, systitle, year, imdb, sysmeta, self.systime)))

                cm.append(('[I]Custom Scrape[/I]', 'RunPlugin(%s?action=playCustom&title=%s&year=%s&imdb=%s&meta=%s&t=%s)' % (sysaddon, systitle, year, imdb, sysmeta, self.systime)))

                cm.append((clearProviders, 'RunPlugin(%s?action=clearCacheProviders)' % sysaddon))

                #cm.append(('[I]Clear All Cache[/I]', 'RunPlugin(%s?action=clearAllCache)' % sysaddon))

                art = {'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape}

                if 'clearlogo' in i and not i['clearlogo'] == '0':
                    art.update({'clearlogo': i['clearlogo']})

                if 'clearart' in i and not i['clearart'] == '0':
                    art.update({'clearart': i['clearart']})

                if 'discart' in i and not i['discart'] == '0':
                    art.update({'discart': i['discart']})

                try: item = control.item(label=label, offscreen=True)
                except: item = control.item(label=label)

                item.setArt(art)
                item.addContextMenuItems(cm)

                if isPlayable:
                    item.setProperty('IsPlayable', 'true')

                if kodiVersion < 20:
                    castwiththumb = i.get('castwiththumb')
                    if castwiththumb and not castwiththumb == '0':
                        if kodiVersion >= 18:
                            item.setCast(castwiththumb)
                        else:
                            cast = [(p['name'], p['role']) for p in castwiththumb]
                            meta.update({'cast': cast})

                    offset = bookmarks.get('movie', imdb, '', '', True)
                    if float(offset) > 120:
                        percentPlayed = int(float(offset) / float(meta['duration']) * 100)
                        item.setProperty('resumetime', str(offset))
                        item.setProperty('percentplayed', str(percentPlayed))

                    item.setProperty('imdb_id', imdb)
                    item.setProperty('tmdb_id', tmdb)
                    try: item.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb})
                    except: pass

                    item.setInfo(type='video', infoLabels=control.metadataClean(meta))

                    video_streaminfo = {'codec': 'h264'}
                    item.addStreamInfo('video', video_streaminfo)

                else:
                    vtag = item.getVideoInfoTag()
                    vtag.setMediaType('movie')
                    vtag.setTitle(title)
                    vtag.setOriginalTitle(title)
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
                    vtag.setDirectors(meta.get('director', '').split(', '))
                    vtag.setWriters(meta.get('writer', '').split(', '))
                    vtag.setPremiered(meta.get('premiered'))
                    vtag.setIMDBNumber(imdb)
                    vtag.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb})

                    cast = []
                    if 'castwiththumb' in i and not i['castwiththumb'] == '0':
                        for p in i['castwiththumb']:
                            cast.append(control.actor(p['name'], p['role'], 0, p['thumbnail']))
                    elif 'cast' in i and not i['cast'] == '0':
                        for p in i['cast']:
                            cast.append(control.actor(p, '', 0, ''))
                    vtag.setCast(cast)

                    if overlay > 6:
                        vtag.setPlaycount(1)

                    offset = bookmarks.get('movie', imdb, '', '', True)
                    if float(offset) > 120:
                        vtag.setResumePoint(float(offset))#, float(meta['duration']))

                #control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
                list_items.append((url, item, False))
            except:
                log_utils.log('movies_dir', 1)
                pass

        try:
            url = items[0]['next']
            if url == '': raise Exception()

            icon = control.addonNext()
            url = '%s?action=moviePage&url=%s' % (sysaddon, urllib_parse.quote_plus(url))
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
        control.content(syshandle, 'movies')
        control.directory(syshandle, cacheToDisc=True)
        control.sleep(1000)
        views.setView('movies', {'skin.estuary': 55, 'skin.confluence': 500})


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

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=movie&url=%s)' % (sysaddon, urllib_parse.quote_plus(i['url']))))

                if queue == True:
                    cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try: cm.append((addToLibrary, 'RunPlugin(%s?action=moviesToLibrary&url=%s)' % (sysaddon, urllib_parse.quote_plus(i['context']))))
                except: pass

                try: item = control.item(label=name, offscreen=True)
                except: item = control.item(label=name)

                item.addContextMenuItems(cm)
                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb, 'fanart': addonFanart})

                if kodiVersion < 20:
                    item.setInfo(type='video', infoLabels={'plot': plot})
                else:
                    vtag = item.getVideoInfoTag()
                    vtag.setMediaType('video')
                    vtag.setPlot(plot)

                #control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
                list_items.append((url, item, True))
            except:
                log_utils.log('mov_addDir', 1)
                pass

        control.addItems(handle=syshandle, items=list_items, totalItems=len(list_items))
        control.content(syshandle, '')
        control.directory(syshandle, cacheToDisc=True)
