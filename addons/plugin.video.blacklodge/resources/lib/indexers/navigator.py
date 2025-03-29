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


import os, sys

from six.moves.urllib_parse import quote

from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import api_keys
from resources.lib.modules.justwatch import providers


artPath = control.artPath() ; addonFanart = control.addonFanart()
imdbCredentials = False if control.setting('imdb.user') == '' else True
traktCredentials = trakt.getTraktCredentialsInfo()
traktIndicators = trakt.getTraktIndicatorsInfo()
queueMenu = control.lang(32065)
enabledServices = providers.enabled_services()

hasScraper = control.condVisibility('System.HasAddon(script.module.blackscrapers)')
hasResolver = control.condVisibility('System.HasAddon(script.module.resolveurl)')
hasTMDb = control.condVisibility('System.HasAddon(plugin.video.themoviedb.helper)')


class navigator:
    def root(self):
        self.addDirectoryItem(32001, 'movieNavigator', 'movies.png', 'DefaultMovies.png')
        self.addDirectoryItem(32002, 'tvNavigator', 'tvshows.png', 'DefaultTVShows.png')

        if not control.setting('lists.widget') == '0':
            self.addDirectoryItem(32003, 'mymovieNavigator', 'mymovies.png', 'DefaultVideoPlaylists.png')
            self.addDirectoryItem(32004, 'mytvNavigator', 'mytvshows.png', 'DefaultVideoPlaylists.png')

        if not control.setting('movie.widget') == '0':
            self.addDirectoryItem(32005, 'movieWidget', 'latest-movies.png', 'DefaultRecentlyAddedMovies.png')

        if (traktIndicators == True and not control.setting('tv.widget.alt') == '0') or (traktIndicators == False and not control.setting('tv.widget') == '0'):
            self.addDirectoryItem(32006, 'tvWidget', 'latest-episodes.png', 'DefaultRecentlyAddedEpisodes.png')

        if not control.setting('channels') == '0':
            self.addDirectoryItem(32007, 'channels', 'channels.png', 'DefaultMovies.png')

        self.addDirectoryItem(32013, 'persons', 'people.png', 'DefaultMovies.png')

        downloads = True if control.setting('downloads') == 'true' and (len(control.listDir(control.setting('movie.download.path'))[0]) > 0 or len(control.listDir(control.setting('tv.download.path'))[0]) > 0) else False
        if downloads == True:
            self.addDirectoryItem(32009, 'downloadNavigator', 'downloads.png', 'DefaultFolder.png')

        self.addDirectoryItem(32010, 'searchNavigator', 'search.png', 'DefaultAddonsSearch.png')

        self.addDirectoryItem(32008, 'toolNavigator', 'tools.png', 'DefaultAddonProgram.png')

        self.endDirectory()


    def movies(self, lite=False):
        if control.setting('lists.provider') == '0':
            self.addDirectoryItem(32011, 'movieGenres', 'genres.png', 'DefaultMovies.png')
            self.addDirectoryItem(32012, 'movieYears', 'years.png', 'DefaultMovies.png')
            self.addDirectoryItem(32123, 'movieDecades', 'years.png', 'DefaultMovies.png')
            self.addDirectoryItem(32014, 'movieLanguages', 'languages.png', 'DefaultMovies.png')
            self.addDirectoryItem(32015, 'movieCertificates', 'certificates.png', 'DefaultMovies.png')
            self.addDirectoryItem('Movie Mosts', 'movieMosts', 'featured.png', 'DefaultMovies.png')
            self.addDirectoryItem(32017, 'movies&url=trending', 'people-watching.png', 'DefaultRecentlyAddedMovies.png')
            self.addDirectoryItem(32018, 'movies&url=popular', 'most-popular.png', 'DefaultMovies.png')
            self.addDirectoryItem(32321, 'movies&url=featured', 'featured.png', 'DefaultRecentlyAddedMovies.png')
            self.addDirectoryItem(32023, 'movies&url=rating', 'highly-rated.png', 'DefaultMovies.png')
            self.addDirectoryItem(32019, 'movies&url=views', 'most-voted.png', 'DefaultMovies.png')
            self.addDirectoryItem(32022, 'movies&url=theaters', 'in-theaters.png', 'DefaultRecentlyAddedMovies.png')
            self.addDirectoryItem(32020, 'movies&url=boxoffice', 'box-office.png', 'DefaultMovies.png')
            self.addDirectoryItem(32580, 'movies&url=added', 'latest-movies.png', 'DefaultRecentlyAddedMovies.png')
        else:
            self.addDirectoryItem(32011, 'movieTmdbGenres&code=', 'genres.png', 'DefaultMovies.png')
            self.addDirectoryItem(32012, 'movieYears&code=&tmdb=True', 'years.png', 'DefaultMovies.png')
            self.addDirectoryItem(32123, 'movieDecades&code=&tmdb=True', 'years.png', 'DefaultMovies.png')
            self.addDirectoryItem(32014, 'movieLanguages&code=&tmdb=True', 'languages.png', 'DefaultMovies.png')
            self.addDirectoryItem(32015, 'movieCertificates&code=&tmdb=True', 'certificates.png', 'DefaultMovies.png')
            self.addDirectoryItem('Movie Mosts', 'movieMosts', 'featured.png', 'DefaultMovies.png')
            self.addDirectoryItem(32017, 'movies&url=trending', 'people-watching.png', 'DefaultRecentlyAddedMovies.png')
            self.addDirectoryItem(32018, 'movies&url=tmdb_pop', 'most-popular.png', 'DefaultMovies.png')
            self.addDirectoryItem(32321, 'movies&url=tmdb_featured', 'featured.png', 'DefaultRecentlyAddedMovies.png')
            self.addDirectoryItem(32023, 'movies&url=tmdb_rating', 'highly-rated.png', 'DefaultMovies.png')
            self.addDirectoryItem(32019, 'movies&url=tmdb_voted', 'most-voted.png', 'DefaultMovies.png')
            self.addDirectoryItem(32022, 'movies&url=tmdb_theaters', 'in-theaters.png', 'DefaultRecentlyAddedMovies.png')
            self.addDirectoryItem(32020, 'movies&url=tmdb_boxoffice', 'box-office.png', 'DefaultMovies.png')
            self.addDirectoryItem(32580, 'movies&url=tmdb_added', 'latest-movies.png', 'DefaultRecentlyAddedMovies.png')
        self.addDirectoryItem(32579, 'movies&url=tmdb_upcoming', 'new-tvshows.png', 'DefaultRecentlyAddedMovies.png')
        self.addDirectoryItem(32021, 'movies&url=oscars', 'oscar-winners.png', 'DefaultMovies.png')
        self.addDirectoryItem(32124, 'movieKeywords', 'imdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('More IMDb Keywords', 'movieKeywords2', 'imdb.png', 'DefaultMovies.png')
        self.addDirectoryItem(32125, 'movieCustomLists', 'imdb.png', 'DefaultMovies.png')

        if lite == False:
            if not control.setting('lists.widget') == '0':
                self.addDirectoryItem(32003, 'mymovieliteNavigator', 'mymovies.png', 'DefaultVideoPlaylists.png')

        self.addDirectoryItem(32028, 'peopleSearch&content=movies', 'people-search.png', 'DefaultAddonsSearch.png')
        self.addDirectoryItem(32010, 'movieSearch', 'search.png', 'DefaultAddonsSearch.png')

        self.endDirectory()


    def mymovies(self, lite=False):
        self.accountCheck()

        if providers.SCRAPER_INIT:
            self.addDirectoryItem('My Services', 'movieServicesMenu', 'mymovies.png', 'DefaultMovies.png')

        if traktCredentials == True and imdbCredentials == True:
            self.addDirectoryItem(32094, 'movies&url=onDeck', 'trakt.png', 'DefaultMovies.png', queue=True)
            self.addDirectoryItem(32036, 'movies&url=trakthistory', 'trakt.png', 'DefaultMovies.png', queue=True)
            self.addDirectoryItem(32032, 'movies&url=traktcollection', 'trakt.png', 'DefaultMovies.png', queue=True, context=(32551, 'moviesToLibrary&url=traktcollection'))
            self.addDirectoryItem(32033, 'movies&url=traktwatchlist', 'trakt.png', 'DefaultMovies.png', queue=True, context=(32551, 'moviesToLibrary&url=traktwatchlist'))
            self.addDirectoryItem(32034, 'movies&url=imdbwatchlist', 'imdb.png', 'DefaultMovies.png', queue=True)
            self.addDirectoryItem(32039, 'movieUserlists', 'userlists.png', 'DefaultMovies.png')
            self.addDirectoryItem(32035, 'movies&url=traktfeatured', 'trakt.png', 'DefaultMovies.png', queue=True)

        elif traktCredentials == True:
            self.addDirectoryItem(32094, 'movies&url=onDeck', 'trakt.png', 'DefaultMovies.png', queue=True)
            self.addDirectoryItem(32036, 'movies&url=trakthistory', 'trakt.png', 'DefaultMovies.png', queue=True)
            self.addDirectoryItem(32032, 'movies&url=traktcollection', 'trakt.png', 'DefaultMovies.png', queue=True, context=(32551, 'moviesToLibrary&url=traktcollection'))
            self.addDirectoryItem(32033, 'movies&url=traktwatchlist', 'trakt.png', 'DefaultMovies.png', queue=True, context=(32551, 'moviesToLibrary&url=traktwatchlist'))
            self.addDirectoryItem(32039, 'movieUserlists', 'userlists.png', 'DefaultMovies.png')
            self.addDirectoryItem(32035, 'movies&url=traktfeatured', 'trakt.png', 'DefaultMovies.png', queue=True)

        elif imdbCredentials == True:
            self.addDirectoryItem(32034, 'movies&url=imdbwatchlist', 'imdb.png', 'DefaultMovies.png', queue=True)
            self.addDirectoryItem(32039, 'movieUserlists', 'userlists.png', 'DefaultMovies.png')

        if lite == False:
            self.addDirectoryItem(32031, 'movieliteNavigator', 'movies.png', 'DefaultMovies.png')

        self.endDirectory()


    def tvshows(self, lite=False):
        if control.setting('lists.provider') == '0':
            self.addDirectoryItem(32011, 'tvGenres', 'genres.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32016, 'tvNetworks', 'networks.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32012, 'tvYears', 'years.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32123, 'tvDecades', 'years.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32014, 'tvLanguages', 'languages.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32015, 'tvCertificates', 'certificates.png', 'DefaultTVShows.png')
            self.addDirectoryItem('TV Show Mosts', 'tvMosts', 'featured.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32017, 'tvshows&url=trending', 'people-watching.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32018, 'tvshows&url=popular', 'most-popular.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32023, 'tvshows&url=rating', 'highly-rated.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32019, 'tvshows&url=views', 'most-voted.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32026, 'tvshows&url=premiere', 'new-tvshows.png', 'DefaultTVShows.png')
        else:
            self.addDirectoryItem(32011, 'tvTmdbGenres&code=', 'genres.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32016, 'tvNetworks', 'networks.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32012, 'tvYears&code=&tmdb=True', 'years.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32123, 'tvDecades&code=&tmdb=True', 'years.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32014, 'tvLanguages&code=&tmdb=True', 'languages.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32015, 'tvCertificates&code=True', 'certificates.png', 'DefaultTVShows.png')
            self.addDirectoryItem('TV Show Mosts', 'tvMosts', 'featured.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32017, 'tvshows&url=trending', 'people-watching.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32018, 'tvshows&url=tmdb_pop', 'most-popular.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32023, 'tvshows&url=tmdb_rating', 'highly-rated.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32019, 'tvshows&url=tmdb_voted', 'most-voted.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32026, 'tvshows&url=tmdb_premiere', 'new-tvshows.png', 'DefaultTVShows.png')
        self.addDirectoryItem(32024, 'tvshows&url=tmdb_airing', 'airing-today.png', 'DefaultTVShows.png')
        self.addDirectoryItem(32025, 'tvshows&url=tmdb_active', 'returning-tvshows.png', 'DefaultTVShows.png')
        self.addDirectoryItem(32006, 'calendar&url=added', 'latest-episodes.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
        self.addDirectoryItem(32027, 'calendars', 'calendar.png', 'DefaultRecentlyAddedEpisodes.png')

        if lite == False:
            if not control.setting('lists.widget') == '0':
                self.addDirectoryItem(32004, 'mytvliteNavigator', 'mytvshows.png', 'DefaultVideoPlaylists.png')

        self.addDirectoryItem(32028, 'peopleSearch&content=tvshows', 'people-search.png', 'DefaultAddonsSearch.png')
        self.addDirectoryItem(32010, 'tvSearch', 'search.png', 'DefaultAddonsSearch.png')

        self.endDirectory()


    def mytvshows(self, lite=False):
        self.accountCheck()

        if providers.SCRAPER_INIT:
            self.addDirectoryItem('My Services', 'tvServicesMenu', 'mytvshows.png', 'DefaultTVShows.png')

        if traktCredentials == True and imdbCredentials == True:

            self.addDirectoryItem(32094, 'calendar&url=onDeck', 'trakt.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32036, 'calendar&url=trakthistory', 'trakt.png', 'DefaultTVShows.png', queue=True)
            self.addDirectoryItem(32037, 'calendar&url=progresswatched', 'trakt.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
            self.addDirectoryItem(32038, 'calendar&url=progressaired', 'trakt.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
            self.addDirectoryItem(32006, 'calendar&url=mycalendar', 'trakt.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
            self.addDirectoryItem(32032, 'tvshows&url=traktcollection', 'trakt.png', 'DefaultTVShows.png', context=(32551, 'tvshowsToLibrary&url=traktcollection'))
            self.addDirectoryItem(32033, 'tvshows&url=traktwatchlist', 'trakt.png', 'DefaultTVShows.png', context=(32551, 'tvshowsToLibrary&url=traktwatchlist'))
            self.addDirectoryItem(32034, 'tvshows&url=imdbwatchlist', 'imdb.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32040, 'tvUserlists', 'userlists.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32041, 'episodeUserlists', 'userlists.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32035, 'tvshows&url=traktfeatured', 'trakt.png', 'DefaultTVShows.png')

        elif traktCredentials == True:
            self.addDirectoryItem(32094, 'calendar&url=onDeck', 'trakt.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32036, 'calendar&url=trakthistory', 'trakt.png', 'DefaultTVShows.png', queue=True)
            self.addDirectoryItem(32037, 'calendar&url=progresswatched', 'trakt.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
            self.addDirectoryItem(32038, 'calendar&url=progressaired', 'trakt.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
            self.addDirectoryItem(32006, 'calendar&url=mycalendar', 'trakt.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
            self.addDirectoryItem(32032, 'tvshows&url=traktcollection', 'trakt.png', 'DefaultTVShows.png', context=(32551, 'tvshowsToLibrary&url=traktcollection'))
            self.addDirectoryItem(32033, 'tvshows&url=traktwatchlist', 'trakt.png', 'DefaultTVShows.png', context=(32551, 'tvshowsToLibrary&url=traktwatchlist'))
            self.addDirectoryItem(32040, 'tvUserlists', 'userlists.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32041, 'episodeUserlists', 'userlists.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32035, 'tvshows&url=traktfeatured', 'trakt.png', 'DefaultTVShows.png')

        elif imdbCredentials == True:
            self.addDirectoryItem(32034, 'tvshows&url=imdbwatchlist', 'imdb.png', 'DefaultTVShows.png')
            self.addDirectoryItem(32040, 'tvUserlists', 'userlists.png', 'DefaultTVShows.png')

        if lite == False:
            self.addDirectoryItem(32031, 'tvliteNavigator', 'tvshows.png', 'DefaultTVShows.png')

        self.endDirectory()


    def tools(self):
        self.addDirectoryItem('[B]Blacklodge[/B] : Changelog', 'changelog', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32047, 'openSettings&query=0.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        if hasScraper:
            self.addDirectoryItem(32079, 'blackscrapersettings', 'iconT.png', 'DefaultAddonProgram.png', isFolder=False)
            if hasResolver:
                self.addDirectoryItem(32076, 'smuSettings', 'resolveurl.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32049, 'viewsNavigator', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32556, 'libraryNavigator', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32046, 'cacheNavigator', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem('[B]Blacklodge[/B] : Log Functions', 'logNavigator', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32073, 'authTrakt', 'trakt.png', 'DefaultAddonProgram.png', isFolder=False)
        if hasTMDb:
            self.addDirectoryItem(32045, 'copyPlayerFile', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        if not hasScraper or not hasResolver:
            self.addDirectoryItem('Enter Dev Menu', 'devMenu', 'tools.png', 'DefaultAddonProgram.png')

        self.endDirectory()


    def library(self):
        self.addDirectoryItem(32557, 'openSettings&query=5.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32558, 'updateLibrary&query=tool', 'library_update.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32559, control.setting('library.movie'), 'movies.png', 'DefaultMovies.png', isAction=False)
        self.addDirectoryItem(32560, control.setting('library.tv'), 'tvshows.png', 'DefaultTVShows.png', isAction=False)

        if trakt.getTraktCredentialsInfo():
            self.addDirectoryItem(32561, 'moviesToLibrary&url=traktcollection', 'trakt.png', 'DefaultMovies.png', isFolder=False)
            self.addDirectoryItem(32562, 'moviesToLibrary&url=traktwatchlist', 'trakt.png', 'DefaultMovies.png', isFolder=False)
            self.addDirectoryItem(32563, 'tvshowsToLibrary&url=traktcollection', 'trakt.png', 'DefaultTVShows.png', isFolder=False)
            self.addDirectoryItem(32564, 'tvshowsToLibrary&url=traktwatchlist', 'trakt.png', 'DefaultTVShows.png', isFolder=False)

        self.endDirectory()


    def downloads(self):
        movie_downloads = control.setting('movie.download.path')
        tv_downloads = control.setting('tv.download.path')

        if len(control.listDir(movie_downloads)[0]) > 0:
            self.addDirectoryItem(32001, movie_downloads, 'movies.png', 'DefaultMovies.png', isAction=False)
        if len(control.listDir(tv_downloads)[0]) > 0:
            self.addDirectoryItem(32002, tv_downloads, 'tvshows.png', 'DefaultTVShows.png', isAction=False)

        self.endDirectory()


    def cache_functions(self):
        self.addDirectoryItem(32108, 'cleanSettings', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32604, 'clearCacheSearch&select=all', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32050, 'clearSources', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32116, 'clearDebridCheck', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32052, 'clearCache', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32611, 'clearAllCache', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)

        self.endDirectory()


    def log_functions(self):
        self.addDirectoryItem('[B]Blacklodge[/B] : View Log', 'viewLog', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('[B]Blacklodge[/B] : Upload Log to hastebin', 'uploadLog', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('[B]Blacklodge[/B] : Empty Log', 'emptyLog', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)

        self.endDirectory()


    def movie_services_menu(self):
        if enabledServices:
            codes = '|'.join([i[1] for i in enabledServices])
            if len(enabledServices) > 1:
                self.addDirectoryItem('Mixed', 'movieServices&code=%s' % quote(codes), 'mymovies.png', 'DefaultMovies.png', plot='[I]Provided by JustWatch[/I]')
            for i in enabledServices:
                self.addDirectoryItem(i[0], 'movieServices&code=%s' % quote(i[1]), 'services/{}.png'.format(i[0]), 'DefaultMovies.png', plot='[I]Provided by JustWatch[/I]')
            self.addDirectoryItem(32642, 'movieSearch&code=%s' % quote(codes), 'search.png', 'DefaultAddonsSearch.png')

            self.endDirectory()


    def tv_services_menu(self):
        if enabledServices:
            codes = '|'.join([i[1] for i in enabledServices])
            if len(enabledServices) > 1:
                self.addDirectoryItem('Mixed', 'tvServices&code=%s' % quote(codes), 'mytvshows.png', 'DefaultTVShows.png', plot='[I]Provided by JustWatch[/I]')
            for i in enabledServices:
                self.addDirectoryItem(i[0], 'tvServices&code=%s' % quote(i[1]), 'services/{}.png'.format(i[0]), 'DefaultTVShows.png', plot='[I]Provided by JustWatch[/I]')
            self.addDirectoryItem(32643, 'tvSearch&code=%s' % quote(codes), 'search.png', 'DefaultAddonsSearch.png')

            self.endDirectory()


    def search(self):
        self.addDirectoryItem(32001, 'movieSearch', 'search.png', 'DefaultAddonsSearch.png')
        self.addDirectoryItem(32002, 'tvSearch', 'search.png', 'DefaultAddonsSearch.png')
        if enabledServices:
            codes = '|'.join([i[1] for i in enabledServices])
            self.addDirectoryItem(32640, 'movieSearch&code=%s' % quote(codes), 'search.png', 'DefaultAddonsSearch.png')
            self.addDirectoryItem(32641, 'tvSearch&code=%s' % quote(codes), 'search.png', 'DefaultAddonsSearch.png')
        self.addDirectoryItem(32013, 'peopleSearch', 'people-search.png', 'DefaultAddonsSearch.png')

        self.endDirectory()


    def views(self):
        try:
            control.idle()

            items = [ (control.lang(32001), 'movies'), (control.lang(32002), 'tvshows'), (control.lang(32054), 'seasons'), (control.lang(32326), 'episodes') ]

            select = control.selectDialog([i[0] for i in items], control.lang(32049))

            if select == -1: return

            content = items[select][1]

            title = control.lang(32059)
            url = '%s?action=addView&content=%s' % (sys.argv[0], content)

            poster, banner, fanart = control.addonPoster(), control.addonBanner(), control.addonFanart()

            item = control.item(label=title)
            item.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': fanart, 'banner': banner})

            if control.getKodiVersion() < 20:
                item.setInfo(type='video', infoLabels={'title': title})
            else:
                vtag = item.getVideoInfoTag()
                vtag.setMediaType('video')
                vtag.setTitle(title)

            control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=False)
            control.content(int(sys.argv[1]), content)
            control.directory(int(sys.argv[1]), cacheToDisc=True)

            from resources.lib.modules import views
            views.setView(content, {})
        except:
            return


    def accountCheck(self):
        if traktCredentials == False and imdbCredentials == False and providers.SCRAPER_INIT == False:
            control.idle()
            control.infoDialog(control.lang(32042), sound=True, icon='WARNING')
            sys.exit()


    def clearCache(self):
        yes = control.yesnoDialog(control.lang(32056))
        if not yes: return
        from resources.lib.modules import cache
        cache.cache_clear()
        control.infoDialog(control.lang(32057), sound=True, icon='INFO')

    def clearCacheMeta(self):
        yes = control.yesnoDialog(control.lang(32056))
        if not yes: return
        from resources.lib.modules import cache
        cache.cache_clear_meta()
        control.infoDialog(control.lang(32057), sound=True, icon='INFO')

    def clearCacheProviders(self):
        # yes = control.yesnoDialog(control.lang(32056))
        # if not yes: return
        from resources.lib.modules import cache
        cache.cache_clear_providers()
        cache.cache_clear_debrid()
        control.infoDialog(control.lang(32057), sound=True, icon='INFO')

    def clearCacheSearch(self, select):
        yes = control.yesnoDialog(control.lang(32056))
        if not yes: return
        from resources.lib.modules import cache
        cache.cache_clear_search(select)
        control.infoDialog(control.lang(32057), sound=True, icon='INFO')

    def clearDebridCheck(self):
        yes = control.yesnoDialog(control.lang(32056))
        if not yes: return
        from resources.lib.modules import cache
        cache.cache_clear_debrid()
        control.infoDialog(control.lang(32057), sound=True, icon='INFO')

    def clearCacheAll(self):
        yes = control.yesnoDialog(control.lang(32056))
        if not yes: return
        from resources.lib.modules import cache
        cache.cache_clear_all()
        control.infoDialog(control.lang(32057), sound=True, icon='INFO')

    def uploadLog(self):
        yes = control.yesnoDialog(control.lang(32056))
        if not yes: return
        from resources.lib.modules import log_utils
        log_utils.upload_log()

    def emptyLog(self):
        yes = control.yesnoDialog(control.lang(32056))
        if not yes: return
        from resources.lib.modules import log_utils
        log_utils.empty_log()

    def dev_menu(self):
        k = control.keyboard('', 'PIN code required to enter Dev menu')
        k.doModal()
        c = k.getText() if k.isConfirmed() else ''
        if c == api_keys.pin:
            if not hasScraper:
                self.addDirectoryItem('Install external scraper package', 'installAddon&addon_id=script.module.blackscrapers', 'iconT.png', 'DefaultAddonProgram.png', isFolder=False)
            if not hasResolver:
                self.addDirectoryItem('Install external resolvers package', 'installAddon&addon_id=script.module.resolveurl', 'iconT.png', 'DefaultAddonProgram.png', isFolder=False)
            self.endDirectory()
        else:
            return

    def addDirectoryItem(self, name, query, thumb, icon, plot='[CR]', context=None, queue=False, isAction=True, isFolder=True):
        from sys import argv
        sysaddon = argv[0]
        syshandle = int(argv[1])
        try: name = control.lang(name)
        except: pass
        url = '%s?action=%s' % (sysaddon, query) if isAction == True else query
        if not thumb.startswith('http'):
            thumb = os.path.join(artPath, thumb) if not artPath == None else icon
        cm = []
        if queue == True: cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))
        if not context == None: cm.append((control.lang(context[0]), 'RunPlugin(%s?action=%s)' % (sysaddon, context[1])))
        try: item = control.item(label=name, offscreen=True)
        except: item = control.item(label=name)
        item.addContextMenuItems(cm)
        item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': addonFanart})
        if control.getKodiVersion() < 20:
            item.setInfo(type='video', infoLabels={'plot': plot})
        else:
            vtag = item.getVideoInfoTag()
            vtag.setMediaType('video')
            vtag.setPlot(plot)
        control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)

    def endDirectory(self, cache=True):
        from sys import argv
        syshandle = int(argv[1])
        control.content(syshandle, '')
        control.directory(syshandle, cacheToDisc=cache)
