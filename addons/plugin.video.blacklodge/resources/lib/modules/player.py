# -*- coding: utf-8 -*-

import sys
import simplejson as json
from kodi_six import xbmc

import six
from six.moves import urllib_parse

from resources.lib.modules import bookmarks
from resources.lib.modules import control
from resources.lib.modules import cleantitle
from resources.lib.modules import opensubtitles
from resources.lib.modules import playcount
from resources.lib.modules import trakt
from resources.lib.modules import log_utils


class player(xbmc.Player):
    def __init__ (self):
        xbmc.Player.__init__(self)


    def run(self, title, year, season, episode, imdb, tmdb, url, meta):
        try:
            control.sleep(1000)

            self.totalTime = 0 ; self.currentTime = 0
            self.content = 'movie' if season == None or episode == None else 'episode'

            self.sysmeta = json.dumps(meta)

            self.title = title ; self.year = year
            self.name = urllib_parse.quote_plus(title) + urllib_parse.quote_plus(' (%s)' % year) if self.content == 'movie' else urllib_parse.quote_plus(title) + urllib_parse.quote_plus(' S%01dE%01d' % (int(season), int(episode)))
            self.name = urllib_parse.unquote_plus(self.name)
            self.season = '%01d' % int(season) if self.content == 'episode' else ''
            self.episode = '%01d' % int(episode) if self.content == 'episode' else ''

            self.DBID = None
            self.imdb = imdb if not imdb == None else '0'
            self.tmdb = tmdb if not tmdb == None else '0'
            self.ids = {'imdb': self.imdb, 'tmdb': self.tmdb}
            self.ids = dict((k,v) for k, v in six.iteritems(self.ids) if not v == '0')

            self.offset = bookmarks.get(self.content, imdb, season, episode)

            item = control.item(path=url)
            item.setContentLookup(False)

            art, meta = self.getMeta(meta)
            if art:
                item.setArt(art)

            control.processListItem(item, meta)

            if 'plugin' in control.infoLabel('Container.PluginName'):
                control.player.play(url, item)

            control.resolve(int(sys.argv[1]), True, item)

            control.window.setProperty('script.trakt.ids', json.dumps(self.ids))

            self.keepPlaybackAlive()

            control.window.clearProperty('script.trakt.ids')
        except:
            log_utils.log('player_fail', 1)
            return


    def getMeta(self, meta):

        if 'art' in meta: # played through library
            try:
                if not 'plugin' in control.infoLabel('Container.PluginName'):
                    self.DBID = meta['movieid'] if self.content == 'movie' else meta['episodeid']

                art = dict((k, urllib_parse.unquote(v.strip('image:').strip('/'))) for k, v in six.iteritems(meta['art']))
                if self.content == 'movie':
                    poster = art['poster']
                    thumb = art.get('thumb') or poster
                    art = {'icon': thumb, 'thumb': thumb, 'poster': poster, 'fanart': art['fanart'], 'clearlogo': art.get('clearlogo'), 'clearart': art.get('clearart'), 'discart': art.get('discart')}
                else:
                    poster = art['tvshow.poster']
                    thumb = art.get('thumb') or poster
                    season_poster = art.get('season.poster') or poster
                    art = {'icon': thumb, 'thumb': thumb, 'tvshow.poster': poster, 'season.poster': season_poster, 'fanart': art['tvshow.fanart'], 'clearlogo': art.get('tvshow.clearlogo'), 'clearart': art.get('tvshow.clearart')}
                art = dict((k,v) for k, v in six.iteritems(art) if v and not v == '0')
            except:
                log_utils.log('lib_art', 1)
                art = {}

            return art, meta

        try:
            poster = meta['poster']
            thumb = meta.get('thumb') or poster
            fanart = meta['fanart']
            clearlogo = meta.get('clearlogo')
            clearart = meta.get('clearart')
            discart = meta.get('discart')

            if self.content == 'movie':
                art = {'icon': thumb, 'thumb': thumb, 'poster': poster, 'fanart': fanart, 'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart}
            else:
                art = {'icon': thumb, 'thumb': thumb, 'tvshow.poster': poster, 'season.poster': poster, 'fanart': fanart, 'clearlogo': clearlogo, 'clearart': clearart}
            art = dict((k,v) for k, v in six.iteritems(art) if v and not v == '0')
            return art, meta
        except:
            pass

        meta = {'title': self.title, 'mediatype': self.content, 'imdb': self.imdb, 'tmdb': self.tmdb, 'year': self.year, 'season': self.season, 'episode': self.episode}
        return {}, meta


    def keepPlaybackAlive(self):
        pname = '%s.player.overlay' % control.addonInfo('id')
        control.window.clearProperty(pname)


        if self.content == 'movie':
            overlay = playcount.getMovieOverlay(playcount.getMovieIndicators(), self.imdb)

        elif self.content == 'episode':
            overlay = playcount.getEpisodeOverlay(playcount.getTVShowIndicators(), self.imdb, self.tmdb, self.season, self.episode)

        else:
            overlay = '6'


        for i in range(0, 240):
            if self.isPlayingVideo(): break
            xbmc.sleep(1000)


        if overlay == '7':

            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()
                except:
                    pass
                xbmc.sleep(2000)


        elif self.content == 'movie':

            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = (self.currentTime / self.totalTime >= .92)
                    property = control.window.getProperty(pname)

                    if watcher == True and not property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markMovieDuringPlayback(self.imdb, '7', self.sysmeta)

                    elif watcher == False and not property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markMovieDuringPlayback(self.imdb, '6', self.sysmeta)
                except:
                    pass
                xbmc.sleep(2000)


        elif self.content == 'episode':

            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = (self.currentTime / self.totalTime >= .92)
                    property = control.window.getProperty(pname)

                    if watcher == True and not property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '7', self.sysmeta)

                    elif watcher == False and not property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '6', self.sysmeta)
                except:
                    pass
                xbmc.sleep(2000)


        control.window.clearProperty(pname)


    def libForPlayback(self):
        try:
            if self.DBID == None: raise Exception()

            if self.content == 'movie':
                rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : %s, "playcount" : 1 }, "id": 1 }' % str(self.DBID)
            elif self.content == 'episode':
                rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount" : 1 }, "id": 1 }' % str(self.DBID)

            control.jsonrpc(rpc)
            control.refresh()
        except:
            pass


    def idleForPlayback(self):
        for i in range(0, 400):
            if control.condVisibility('Window.IsActive(busydialog)') == 1 or control.condVisibility('Window.IsActive(busydialognocancel)') == 1:
                control.idle()
            else:
                break
            control.sleep(100)


    def onAVStarted(self):
        control.execute('Dialog.Close(all,true)')

        if control.setting('bookmarks') == 'true' and int(self.offset) > 120 and self.isPlayingVideo():
            if control.setting('bookmarks.auto') == 'true':
                self.seekTime(float(self.offset))
            else:
                self.pause()
                minutes, seconds = divmod(float(self.offset), 60)
                hours, minutes = divmod(minutes, 60)
                label = '%02d:%02d:%02d' % (hours, minutes, seconds)
                label = control.lang2(12022).format(label)
                if control.setting('rersume.source') == '1' and trakt.getTraktCredentialsInfo() == True:
                    yes = control.yesnoDialog(label + '[CR]  (Trakt scrobble)', heading=control.lang2(13404))
                else:
                    yes = control.yesnoDialog(label, heading=control.lang2(13404))
                if yes:
                    self.seekTime(float(self.offset))
                control.sleep(1000)
                self.pause()

        if control.setting('subtitles') == 'true':
            opensubtitles.getSubs(self.imdb, self.season, self.episode)

        self.idleForPlayback()


    def onPlayBackStarted(self):
        if control.getKodiVersion() < 18:
            control.execute('Dialog.Close(all,true)')

            if control.setting('bookmarks') == 'true' and int(self.offset) > 120 and self.isPlayingVideo():
                if control.setting('bookmarks.auto') == 'true':
                    self.seekTime(float(self.offset))
                else:
                    self.pause()
                    minutes, seconds = divmod(float(self.offset), 60)
                    hours, minutes = divmod(minutes, 60)
                    label = '%02d:%02d:%02d' % (hours, minutes, seconds)
                    label = control.lang2(12022).format(label)
                    if control.setting('rersume.source') == '1' and trakt.getTraktCredentialsInfo() == True:
                        yes = control.yesnoDialog(label + '[CR]  (Trakt scrobble)', heading=control.lang2(13404))
                    else:
                        yes = control.yesnoDialog(label, heading=control.lang2(13404))
                    if yes:
                        self.seekTime(float(self.offset))
                    control.sleep(1000)
                    self.pause()

            if control.setting('subtitles') == 'true':
                opensubtitles.getSubs(self.imdb, self.season, self.episode)

            self.idleForPlayback()
        else:
            pass


    def onPlayBackStopped(self):
        if self.totalTime == 0 or self.currentTime == 0:
            control.sleep(2000)
            return
        bookmarks.reset(self.currentTime, self.totalTime, self.content, self.imdb, self.sysmeta, self.season, self.episode)
        if (trakt.getTraktCredentialsInfo() == True and control.setting('trakt.scrobble') == 'true'):
            bookmarks.set_scrobble(self.currentTime, self.totalTime, self.content, self.imdb, self.season, self.episode)

        if float(self.currentTime / self.totalTime) >= 0.92:
            self.libForPlayback()
            if control.setting('crefresh') == 'true':
                control.refresh()


    def onPlayBackEnded(self):
        #self.libForPlayback()
        self.onPlayBackStopped()

