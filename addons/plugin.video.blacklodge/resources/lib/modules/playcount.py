# -*- coding: utf-8 -*-

from resources.lib.modules import bookmarks
from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import log_utils


def getMovieIndicators(refresh=False):
    try:
        if trakt.getTraktIndicatorsInfo() == True: raise Exception()
        indicators_ = bookmarks._indicators('movie')
        return [i[2] for i in indicators_]
    except:
        pass
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        if refresh == False: timeout = 360
        elif trakt.getWatchedActivity() < trakt.timeoutsyncMovies(): timeout = 360
        else: timeout = 0
        indicators_ = trakt.cachesyncMovies(timeout=timeout)
        return indicators_
    except:
        pass


def getTVShowIndicators(refresh=False):
    try:
        if trakt.getTraktIndicatorsInfo() == True: raise Exception()
        indicators_ = bookmarks._indicators('episode')
        indicators_ = [(i[2], 0, [(int(i[4]), int(i[5]))]) for i in indicators_]
        indicators = []
        n = {}
        for k, t, s in indicators_:
            if k not in n:
                indicators.append((k, t, s))
                n[k] = len(n)
            else:
                indicators[n[k]][2].extend(s)
        return indicators
    except:
        pass

    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        if refresh == False: timeout = 360
        elif trakt.getWatchedActivity() < trakt.timeoutsyncTVShows(): timeout = 360
        else: timeout = 0
        indicators_ = trakt.cachesyncTVShows(timeout=timeout)
        return indicators_
    except:
        pass


def getSeasonIndicators(imdb):
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        indicators_ = trakt.syncSeason(imdb)
        return indicators_
    except:
        pass


def getMovieOverlay(indicators_, imdb):
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            overlay = bookmarks._get_watched('movie', imdb, '', '')
            return str(overlay)
        else:
            playcount = [i for i in indicators_ if i == imdb]
            overlay = 7 if len(playcount) > 0 else 6
            return str(overlay)
    except:
        return '6'


def getTVShowOverlay(indicators_, imdb, tmdb):
    try:
        if trakt.getTraktIndicatorsInfo():
            playcount = [i[0] for i in indicators_ if i[0] == imdb and len(i[2]) >= int(i[1])]
            playcount = 7 if len(playcount) > 0 else 6
            return str(playcount)
        # else:
            # playcount = bookmarks._get_watched('tvshow', imdb, '', '')
            # return str(playcount)
    except:
        return '6'


def getSeasonOverlay(indicators_, imdb, season):
    try:
        if trakt.getTraktIndicatorsInfo():
            playcount = [i for i in indicators_ if int(season) == int(i)]
            playcount = 7 if len(playcount) > 0 else 6
            return str(playcount)
        # else:
            # playcount = bookmarks._get_watched('season', imdb, season, '')
            # return str(playcount)
    except:
        return '6'


def getEpisodeOverlay(indicators_, imdb, tmdb, season, episode):
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            overlay = bookmarks._get_watched('episode', imdb, season, episode)
            return str(overlay)
        else:
            playcount = [i[2] for i in indicators_ if i[0] == imdb]
            playcount = playcount[0] if len(playcount) > 0 else []
            playcount = [i for i in playcount if int(season) == int(i[0]) and int(episode) == int(i[1])]
            overlay = 7 if len(playcount) > 0 else 6
            return str(overlay)
    except:
        return '6'


def markMovieDuringPlayback(imdb, watched, meta):
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        # Playback start ('6'): nothing is sent to Trakt. A "remove from
        # history" here deleted every play of the item when the watched ticks
        # were older than a play made elsewhere (another device or app).
        if int(watched) != 7: raise Exception()
        # script.trakt scrobbles this playback itself: nothing is sent here.
        # Adding the play and then removing it (as before) deleted every play
        # of the item, older ones too (/sync/history/remove without a date).
        if trakt.getTraktAddonMovieInfo() == True: raise Exception()

        trakt.markMovieAsWatched(imdb)
        trakt.cachesyncMovies()
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'movie', imdb, meta, '', '')
    except:
        pass


def markEpisodeDuringPlayback(imdb, tmdb, season, episode, watched, meta):
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        # Playback start ('6'): nothing is sent to Trakt (see above).
        if int(watched) != 7: raise Exception()
        # script.trakt scrobbles this playback itself: nothing is sent here
        # (see above).
        if trakt.getTraktAddonEpisodeInfo() == True: raise Exception()

        trakt.markEpisodeAsWatched(imdb, season, episode)
        trakt.cachesyncTVShows()
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'episode', imdb, meta, season, episode)
    except:
        pass


def movies(imdb, watched, meta):
#    control.busy()
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        if int(watched) == 7: trakt.markMovieAsWatched(imdb)
        else: trakt.markMovieAsNotWatched(imdb)
        trakt.cachesyncMovies()
        control.refresh()
#        control.idle()
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'movie', imdb, meta, '', '')
        else:
            bookmarks._update_watched(int(watched), imdb, '', '')
        if trakt.getTraktIndicatorsInfo() == False: control.refresh()
#        control.idle()
    except:
        pass


def episodes(imdb, tmdb, season, episode, watched, meta):
#    control.busy()
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        if int(watched) == 7: trakt.markEpisodeAsWatched(imdb, season, episode)
        else: trakt.markEpisodeAsNotWatched(imdb, season, episode)
        trakt.cachesyncTVShows()
        control.refresh()
#        control.idle()
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'episode', imdb, meta, season, episode)
        else:
            bookmarks._update_watched(int(watched), imdb, season, episode)
        if trakt.getTraktIndicatorsInfo() == False: control.refresh()
#        control.idle()
    except:
        pass


def tvshows(tvshowtitle, imdb, tmdb, season, watched, meta):
    control.busy()
    try:
        import sys

        if not trakt.getTraktIndicatorsInfo() == False: raise Exception()

        from resources.lib.indexers import episodes

        name = control.addonInfo('name')

        dialog = control.progressDialogBG
        dialog.create(str(name), str(tvshowtitle))
        dialog.update(0, str(name), str(tvshowtitle))

        #log_utils.log('playcount_season: ' + str(season))
        items = []
        if season:
            items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=season, idx=False)
            items = [i for i in items if int('%01d' % int(season)) == int('%01d' % int(i['season']))]
            items = [{'label': '%s S%02dE%02d' % (tvshowtitle, int(i['season']), int(i['episode'])), 'season': int('%01d' % int(i['season'])), 'episode': int('%01d' % int(i['episode'])), 'unaired': i['unaired']} for i in items]

            for i in range(len(items)):
                if control.monitor.abortRequested(): return sys.exit()

                dialog.update(int((100 / float(len(items))) * i), str(name), str(items[i]['label']))

                _season, _episode, unaired = items[i]['season'], items[i]['episode'], items[i]['unaired']
                if int(watched) == 7:
                    if not unaired == 'true':
                        bookmarks.reset(1, 1, 'episode', imdb, meta, _season, _episode)
                    else: pass
                else:
                    bookmarks._update_watched(int(watched), imdb, _season, _episode)

        else:
            seasons = episodes.seasons().get(tvshowtitle, '0', imdb, tmdb, meta=None, idx=False)
            seasons = [i['season'] for i in seasons]
            #log_utils.log('playcount_seasons: ' + str(seasons))
            for s in seasons:
                items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=s, idx=False)
                items = [{'label': '%s S%02dE%02d' % (tvshowtitle, int(i['season']), int(i['episode'])), 'season': int('%01d' % int(i['season'])), 'episode': int('%01d' % int(i['episode'])), 'unaired': i['unaired']} for i in items]
                #log_utils.log('playcount_items2: ' + str(items))

                for i in range(len(items)):
                    if control.monitor.abortRequested(): return sys.exit()

                    dialog.update(int((100 / float(len(items))) * i), str(name), str(items[i]['label']))

                    _season, _episode, unaired = items[i]['season'], items[i]['episode'], items[i]['unaired']
                    if int(watched) == 7:
                        if not unaired == 'true':
                            bookmarks.reset(1, 1, 'episode', imdb, meta, _season, _episode)
                        else: pass
                    else:
                        bookmarks._update_watched(int(watched), imdb, _season, _episode)

        try: dialog.close()
        except: pass
    except:
        log_utils.log('playcount_local_shows', 1)
        try: dialog.close()
        except: pass


    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()

        #log_utils.log('playcount_season: ' + str(season))
        if season:
            from resources.lib.indexers import episodes
            items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=season, idx=False)
            # Unaired episodes are not marked watched (as with the local marks).
            if int(watched) == 7: items = [i for i in items if not i.get('unaired') == 'true']
            items = [(int(i['season']), int(i['episode'])) for i in items]
            items = [i[1] for i in items if int('%01d' % int(season)) == int('%01d' % i[0])]
            # One request for the whole season instead of one per episode.
            if int(watched) == 7: trakt.markEpisodesAsWatched(imdb, season, items)
            else: trakt.markEpisodesAsNotWatched(imdb, season, items)
        else:
            if int(watched) == 7: trakt.markTVShowAsWatched(imdb)
            else: trakt.markTVShowAsNotWatched(imdb)
        trakt.cachesyncTVShows()
    except:
        log_utils.log('playcount_trakt_shows', 1)
        pass

    control.refresh()
    control.idle()

