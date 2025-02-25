# -*- coding: utf-8 -*-

"""
    TheOath Add-on
    ///Updated for BlackLodge///
"""


import sys
import re
import six
from six.moves import urllib_parse

from resources.lib.modules import api_keys
from resources.lib.modules import cache
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import utils
from resources.lib.modules import imdb_api


class YT_trailer:
    def __init__(self):
        self.mode = control.setting('trailer.select') or '1'
        self.content = control.infoLabel('Container.Content')
        self.base_link = 'https://www.youtube.com'
        self.key = control.addon('plugin.video.youtube').getSetting('youtube.api.key') or api_keys.yt_key

        if self.mode == '0':
            self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=id&type=video&maxResults=3&q=%s&key=%s' % ('%s', self.key)
        else:
            self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=10&q=%s&key=%s' % ('%s', self.key)
        self.youtube_watch = 'https://www.youtube.com/watch?v=%s'
        self.yt_plugin_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s'

    def play(self, name='', url='', tmdb='', imdb='', season='', episode='', windowedtrailer=0):
        try:
            if self.content not in ['tvshows', 'seasons', 'episodes']:
                name += ' %s' % control.infoLabel('ListItem.Year')
            elif self.content in ['seasons', 'episodes']:
                if season and episode:
                    name += ' %sx%02d' % (season, int(episode))
                elif season:
                    name += ' season %01d' % int(season)
            if self.content != 'episodes':
                name += ' trailer'

            url = self.worker(name, url)
            if not url:
                raise Exception('YT_trailer failed, trying TMDb')
            elif url == 'canceled': return

            icon = control.infoLabel('ListItem.Icon')

            item = control.item(label=name, path=url)
            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
            item.setProperty('IsPlayable', 'true')
            if control.getKodiVersion() < 20:
                item.setInfo(type='video', infoLabels={'title': name})
            else:
                vtag = item.getVideoInfoTag()
                vtag.setMediaType('video')
                vtag.setTitle(name)
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
            log_utils.log('YT_trailer play fail', 1)
            TMDb_trailer().play(tmdb, imdb, season, episode)

    def worker(self, name, url):
        try:
            if url.startswith(self.base_link):
                url = resolve(url)
                if not url: raise Exception()
                return url
            elif not url.startswith('http'):
                url = self.youtube_watch % url
                url = resolve(url)
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

            r = cache.get(client.request, 24, url)
            result = utils.json_loads_as_str(r)

            json_items = result['items']
            ids = [i['id']['videoId'] for i in json_items]
            if not ids: return

            if self.mode == '1':
                vids = []

                for i in json_items:
                    name = client.replaceHTMLCodes(i['snippet']['title'])
                    if control.getKodiVersion() >= 17:
                        icon = i['snippet']['thumbnails']['default']['url']
                        li = control.item(label=name)
                        li.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
                        vids.append(li)
                    else:
                        vids.append(name)

                select = control.selectDialog(vids, control.lang(32121) % 'YouTube', useDetails=True)
                if select == -1: return 'canceled'
                vid_id = ids[select]
                url = self.yt_plugin_url % vid_id
                return url

            for vid_id in ids:
                url = resolve(vid_id)
                if url:
                    return url
            return
        except:
            return


class TMDb_trailer:
    def __init__(self):
        self.mode = control.setting('trailer.select') or '1'
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
        try:
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
            if not url: return control.infoDialog('No trailer found')
            elif url == 'canceled': return

            icon = control.infoLabel('ListItem.Icon')
            name = control.infoLabel('ListItem.Title')

            item = control.item(label=name, path=url)
            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
            item.setProperty('IsPlayable', 'true')
            if control.getKodiVersion() < 20:
                item.setInfo(type='video', infoLabels={'title': name})
            else:
                vtag = item.getVideoInfoTag()
                vtag.setMediaType('video')
                vtag.setTitle(name)
            control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)

            if windowedtrailer == 1:
                control.sleep(1000)
                while control.player.isPlayingVideo():
                    control.sleep(1000)
                control.execute('Dialog.Close(%s, true)' % control.getCurrentDialogId)
        except:
            log_utils.log('TMDb_trailer fail', 1)
            return

    def get_items(self, url, t_url, s_url):
        try:
            r = cache.get(client.request, 24, url)
            items = utils.json_loads_as_str(r)
            items = items['results']
            items = [r for r in items if r.get('site') == 'YouTube']
            results = [x for x in items if x.get('iso_639_1') == self.lang]
            if not self.lang == 'en': results += [x for x in items if x.get('iso_639_1') == 'en']
            results += [x for x in items if x.get('iso_639_1') not in set([self.lang, 'en'])]

            if not results:
                if '/season/' in url and '/episode/' in url:
                    results = self.get_items(s_url, t_url, None)
                elif '/season/' in url:
                    results = self.get_items(t_url, None, None)
                else:
                    return

            return results
        except:
            log_utils.log('TMDb_trailer get_items', 1)
            return

    def get_url(self, results):
        try:
            if not results: return
            if self.mode == '1':
                items = [i.get('key') for i in results]
                labels = [' | '.join((i.get('name', ''), i.get('type', ''))) for i in results]
                select = control.selectDialog(labels, control.lang(32121) % 'TMDb')
                if select == -1: return 'canceled'
                vid_id = items[select]
                url = self.yt_plugin_url % vid_id
                return url

            results = [x for x in results if x.get('type') == 'Trailer'] + [x for x in results if x.get('type') != 'Trailer']
            items = [i.get('key') for i in results]
            for vid_id in items:
                url = resolve(vid_id)
                if url:
                    return url
            return
        except:
            log_utils.log('TMDb_trailer get_url', 1)
            return


class IMDb_trailer:
    def __init__(self):
        self.mode = control.setting('trailer.select') or '1'

    def play(self, imdb, name, tmdb='', season='', episode='', windowedtrailer=0):
        try:
            if not imdb or imdb == '0': raise Exception()

            item_dict = self.get_items(imdb, name)
            if not item_dict: raise Exception('IMDb_trailer failed, trying TMDb')
            elif item_dict == 'canceled': return
            title = item_dict['title']
            url = self.resolve_imdb(item_dict['id'])

            icon = control.infoLabel('ListItem.Icon')

            item = control.item(label=title, path=url)
            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
            item.setProperty('IsPlayable', 'true')
            if control.getKodiVersion() < 20:
                item.setInfo(type='video', infoLabels={'title': title, 'plot': item_dict['description'], 'tagline': item_dict['type']})
            else:
                vtag = item.getVideoInfoTag()
                vtag.setMediaType('video')
                vtag.setTitle(title)
                vtag.setTagLine(item_dict['type'])
                vtag.setPlot(item_dict['description'])
            control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)

            if windowedtrailer == 1:
                control.sleep(1000)
                while control.player.isPlayingVideo():
                    control.sleep(1000)
                control.execute('Dialog.Close(%s, true)' % control.getCurrentDialogId)
        except:
            log_utils.log('IMDb_trailer fail', 1)
            TMDb_trailer().play(tmdb, imdb, season, episode)

    def get_items(self, imdb, name):
        try:
            listItems = cache.get(imdb_api._get_imdb_trailers, 48, imdb)
            #log_utils.log(repr(listItems))
            listItems = listItems['data']['title']['primaryVideos']['edges']
            vids_list = []
            for item in listItems:
                try:
                    item = item['node']
                    desc = item['description']['value'] or ''
                    videoId = item['id']
                    title = item['name']['value']
                    content_type = item['contentType']['displayName']['value']
                    icon = item['thumbnail']['url']
                    if icon: icon = re.sub(r'(?:_SX|_SY|_UX|_UY|_CR|_AL|_V)(?:\d+|_).+?\.', '_SX500.', icon)
                    # related_to = item['primaryTitle']['id'] or imdb
                    # if (not related_to == imdb) and (not name.lower() in ' '.join((title, desc)).lower()):
                        # continue
                    vids_list.append({'id': videoId, 'title': title, 'icon': icon, 'description': desc, 'type': content_type})
                except:
                    pass

            if not vids_list: return
            vids_list = [v for v in vids_list if 'trailer' in v['type'].lower()] + [v for v in vids_list if 'trailer' not in v['type'].lower()]

            if self.mode == '1':
                vids = []
                for v in vids_list:
                    if control.getKodiVersion() >= 17:
                        li = control.item(label=v['title'], label2=v['type'])
                        li.setArt({'icon': v['icon'], 'thumb': v['icon'], 'poster': v['icon']})
                        vids.append(li)
                    else:
                        vids.append(v['title'])

                select = control.selectDialog(vids, control.lang(32121) % 'IMDb', useDetails=True)
                if select == -1: return 'canceled'
                return vids_list[select]

            return vids_list[0]
        except:
            log_utils.log('IMDb_trailer get_items fail', 1)
            return

    def resolve_imdb(self, video_id):
        try:
            vidurl = 'https://www.imdb.com/video/{0}/'.format(video_id)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
                'Referer': 'https://www.imdb.com/',
                'Origin': 'https://www.imdb.com'
            }
            r = cache.get(client.request, 48, vidurl, headers=headers)
            r = re.findall(r'("playbackURLs":\[.+?\])', r)[0]
            r = '{'+r+'}'
            vids = utils.json_loads_as_str(r)
            #log_utils.log(repr(vids))
            vid = [i['url'] for i in vids['playbackURLs'] if i['videoMimeType'] == 'MP4'][0]
            return vid
        except:
            log_utils.log('IMDb_trailer resolve fail', 1)
            return None


def resolve(url):
    try:
        id = url.split('?v=')[-1].split('/')[-1].split('?')[0].split('&')[0]
        url = 'https://www.youtube.com/watch?v=%s' % id
        result = client.request(url)

        message = client.parseDOM(result, 'div', attrs={'id': 'unavailable-submessage'})
        message = ''.join(message)

        alert = client.parseDOM(result, 'div', attrs={'id': 'watch7-notification-area'})

        if len(alert) > 0: raise Exception()
        if re.search('[a-zA-Z]', message): raise Exception()

        url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % id
        return url
    except:
        return

