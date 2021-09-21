# -*- coding: utf-8 -*-

"""
    TheOath Add-on
"""


import sys
import simplejson as json
import re
import requests
import six
from six.moves import urllib_parse

from resources.lib.modules import api_keys
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import utils


class YT_trailer:
    def __init__(self):
        self.mode = control.setting('trailer.select')
        self.content = control.infoLabel('Container.Content')
        self.base_link = 'https://www.youtube.com'
        self.key = control.addon('plugin.video.youtube').getSetting('youtube.api.key') or api_keys.yt_key

        if self.mode == '1':
            self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=9&q=%s&key=%s' % ('%s', self.key)
        elif self.mode == '2':
            if self.content in ['seasons', 'episodes']:
                self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=9&q=%s&key=%s' % ('%s', self.key)
            else:
                self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=id&type=video&maxResults=2&q=%s&key=%s' % ('%s', self.key)
        else:
            self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=id&type=video&maxResults=2&q=%s&key=%s' % ('%s', self.key)
        self.youtube_watch = 'https://www.youtube.com/watch?v=%s'

    def play(self, name='', url='', tmdb='', imdb='', season='', episode='', windowedtrailer=0):
        try:
            name = control.infoLabel('ListItem.Title')
            if not name:
                name = control.infoLabel('ListItem.Label')
            if self.content == 'movies':
                name += ' ' + control.infoLabel('ListItem.Year')
            name += ' trailer'
            if self.content in ['seasons', 'episodes']:
                season = control.infoLabel('ListItem.Season')
                episode = control.infoLabel('ListItem.Episode')
                if season != '':
                    name = control.infoLabel('ListItem.TVShowTitle')
                    name += ' season %01d trailer' % int(season)
                    if episode != '':
                        name = name.replace('season ', '').replace(' trailer', '')
                        name += 'x%02d' % int(episode)

            url = self.worker(name, url)
            if not url:
                #control.infoDialog('Trying TMDb...', 'API key quota limit reached')
                raise Exception('YT_trailer failed, trying TMDb')
            elif url == 'Canceled': return

            icon = control.infoLabel('ListItem.Icon')

            item = control.item(label=name, path=url)
            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
            item.setInfo(type='video', infoLabels={'title': name})

            item.setProperty('IsPlayable', 'true')
            control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)
            if windowedtrailer == 1:
                # The call to the play() method is non-blocking. So we delay further script execution to keep the script alive at this spot.
                # Otherwise this script will continue and probably already be garbage collected by the time the trailer has ended.
                control.sleep(1000)  # Wait until playback starts. Less than 900ms is too short (on my box). Make it one second.
                while control.player.isPlayingVideo():
                    control.sleep(1000)
                # Close the dialog.
                # Same behaviour as the fullscreenvideo window when :
                # the media plays to the end,
                # or the user pressed one of X, ESC, or Backspace keys on the keyboard/remote to stop playback.
                control.execute('Dialog.Close(%s, true)' % control.getCurrentDialogId)
        except:
            TMDb_trailer().play(tmdb, imdb, season, episode)

    def worker(self, name, url):
        try:
            if url.startswith(self.base_link):
                url = self.resolve(url)
                if not url: raise Exception()
                return url
            elif not url.startswith('http'):
                url = self.youtube_watch % url
                url = self.resolve(url)
                if not url: raise Exception()
                return url
            else:
                raise Exception()
        except:
            query = self.search_link % urllib_parse.quote_plus(name)
            return self.search(query)

    def search(self, url):
        try:
            apiLang = control.apiLanguage().get('youtube', 'en')

            if apiLang != 'en':
                url += '&relevanceLanguage=%s' % apiLang

            r = requests.get(url)
            r.raise_for_status()
            r.encoding = 'utf-8'
            result = r.json() if six.PY3 else utils.json_loads_as_str(r.text)

            json_items = result['items']
            items = [i.get('id').get('videoId') for i in json_items]

            if self.mode == '1' or (self.mode == '2' and self.content in ['seasons', 'episodes']):
                labels = [i.get('snippet', {}).get('title') for i in json_items]
                labels = [client.replaceHTMLCodes(i) for i in labels]
                select = control.selectDialog(labels, control.lang(32121) % 'YouTube')
                if select == -1: return 'Canceled'
                items = [items[select]]

            for vid_id in items:
                url = self.resolve(vid_id)
                if url:
                    return url
        except:
            return

    def resolve(self, url):
        try:
            id = url.split('?v=')[-1].split('/')[-1].split('?')[0].split('&')[0]
            result = client.request(self.youtube_watch % id)

            message = client.parseDOM(result, 'div', attrs={'id': 'unavailable-submessage'})
            message = ''.join(message)

            alert = client.parseDOM(result, 'div', attrs={'id': 'watch7-notification-area'})

            if len(alert) > 0: raise Exception()
            if re.search('[a-zA-Z]', message): raise Exception()

            url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % id
            return url
        except:
            return


class TMDb_trailer:
    def __init__(self):
        self.mode = control.setting('trailer.select')
        self.content = control.infoLabel('Container.Content')
        self.tm_user = control.setting('tm.user') or api_keys.tmdb_key
        self.lang = control.apiLanguage()['tmdb']
        self.lang_link = 'en,null' if self.lang == 'en' else 'en,%s,null' % self.lang
        self.movie_url = 'https://api.themoviedb.org/3/movie/%s/videos?api_key=%s&include_video_language=%s' % ('%s', self.tm_user, self.lang_link)
        self.show_url = 'https://api.themoviedb.org/3/tv/%s/videos?api_key=%s&include_video_language=%s' % ('%s', self.tm_user, self.lang_link)
        self.season_url = 'https://api.themoviedb.org/3/tv/%s/season/%s/videos?api_key=%s&include_video_language=%s' % ('%s', '%s', self.tm_user, self.lang_link)
        self.episode_url = 'https://api.themoviedb.org/3/tv/%s/season/%s/episode/%s/videos?api_key=%s&include_video_language=%s' % ('%s', '%s', '%s', self.tm_user, self.lang_link)
        self.yt_plugin_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s'

    def play(self, tmdb, imdb=None, season=None, episode=None, windowedtrailer=0):
        t_url = self.show_url % tmdb
        s_url = self.season_url % (tmdb, season)
        if self.content == 'tvshows':
            if not tmdb or tmdb == '0': return control.infoDialog('No ID found')
            api_url = t_url
        elif self.content == 'seasons':
            if not tmdb or tmdb == '0': return control.infoDialog('No ID found')
            api_url = s_url
        elif self.content == 'episodes':
            if not tmdb or tmdb == '0': return control.infoDialog('No ID found')
            api_url = self.episode_url % (tmdb, season, episode)
        else:
            id = tmdb if not tmdb == '0' else imdb
            if not id or id == '0': return control.infoDialog('No ID found')
            api_url = self.movie_url % id
        #log_utils.log('api_url: ' + api_url)

        results = self.get_items(api_url, t_url, s_url)
        url = self.get_url(results)
        if not url: return

        icon = control.infoLabel('ListItem.Icon')
        name = control.infoLabel('ListItem.Title')

        item = control.item(label=name, path=url)
        item.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
        item.setInfo(type='video', infoLabels={'title': name})

        item.setProperty('IsPlayable', 'true')
        control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)
        if windowedtrailer == 1:
            control.sleep(1000)
            while control.player.isPlayingVideo():
                control.sleep(1000)
            control.execute('Dialog.Close(%s, true)' % control.getCurrentDialogId)

    def get_items(self, url, t_url, s_url):
        try:
            r = requests.get(url)
            r.raise_for_status()
            r.encoding = 'utf-8'
            results = r.json() if six.PY3 else utils.json_loads_as_str(r.text)
            results = results['results']
            results = [r for r in results if r.get('site') == 'YouTube']
            results = [x for x in results if x.get('iso_639_1') == self.lang] + [x for x in results if x.get('iso_639_1') == 'en'] + [x for x in results if x.get('iso_639_1') not in [self.lang, 'en']]

            if not results:
                if self.content in ['movies', 'tvshows']:
                    return
                elif self.content == 'seasons':
                    results = self.get_items(t_url, '', '')
                    if not results:
                        return
                elif self.content == 'episodes':
                    results = self.get_items(s_url, '', '')
                    if not results:
                        results = self.get_items(t_url, '', '')
                        if not results:
                            return

            return results
        except:
            log_utils.log('TMDb_trailer get_items', 1)
            return

    def get_url(self, results):
        try:
            if not results: return control.infoDialog('No trailer found')
            items = [i.get('key') for i in results]
            if self.mode == '1' or (self.mode == '2' and self.content in ['seasons', 'episodes']):
                labels = [' | '.join((i.get('name'), i.get('type', ''))) for i in results]
                select = control.selectDialog(labels, control.lang(32121) % 'TMDb')
                if select == -1: return
                vid_id = items[select]
                return self.yt_plugin_url % vid_id
            else:
                results = [x for x in results if x.get('type') == 'Trailer'] + [x for x in results if x.get('type') != 'Trailer']
                items = [i.get('key') for i in results]
                return self.yt_plugin_url % items[0]
        except:
            log_utils.log('TMDb_trailer get_url', 1)
            return


