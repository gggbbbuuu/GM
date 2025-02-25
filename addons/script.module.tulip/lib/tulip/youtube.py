# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import absolute_import

import re, json
from datetime import datetime
from tulip.compat import urlparse, parse_qs, quote_plus, range, py3_dec, py2_enc, concurrent_futures
from tulip import client, control, directory, iso8601
from tulip.log import log_debug

MAXRES_THUMBNAIL = 2
HQ_THUMBNAIL = 1
MQ_THUMBNAIL = 0

class youtube(object):

    def __init__(self, key='', api_key_setting='yt_api_key', replace_url=True, max_workers=5):

        self.list = [];  self.data = []

        self.max_workers = max_workers

        self.base_link = 'https://www.youtube.com/'
        self.base_addon = 'plugin://plugin.video.youtube/'
        self.google_base_link = 'https://www.googleapis.com/youtube/v3/'
        self.key_link = '&key={0}'.format(py3_dec(key) or control.setting(api_key_setting))

        self.playlists_link = ''.join([self.google_base_link, 'playlists?part=snippet&maxResults=50&channelId={}'])
        self.playlist_link = ''.join([self.google_base_link, 'playlistItems?part=snippet&maxResults=50&playlistId={}'])
        self.videos_link = ''.join([self.google_base_link, 'search?part=snippet&order=date&maxResults=50&channelId={}'])
        self.content_link = ''.join([self.google_base_link, 'videos?part=contentDetails&id={}'])
        self.search_link = ''.join([self.google_base_link, 'search?part=snippet&type=video&maxResults=5&q={}'])
        self.youtube_search = ''.join([self.google_base_link, 'search?q={}'])

        if not replace_url:
            self.play_link = ''.join([self.base_link, 'watch?v={}'])
        else:
            self.play_link = ''.join([self.base_addon, 'play/?video_id={}'])

    def playlists(self, url, limit=5):

        url = self.playlists_link.format(''.join([url, self.key_link]))
        return self._playlist(url, limit)

    def playlist(self, url, pagination=False, limit=5):

        cid = url.split('&')[0]
        url = self.playlist_link.format(''.join([url, self.key_link]))
        return self._video_list(cid, url, pagination, limit)

    def videos(self, url, pagination=False, limit=5):

        cid = url.split('&')[0]
        url = self.videos_link.format(''.join([url, self.key_link]))
        return self._video_list(cid, url, pagination, limit)

    def _playlist(self, url, limit):

        try:
            result = client.request(url)
            result = json.loads(result)
            items = result['items']
        except Exception:
            log_debug('Youtube: Could not fetch items from the cdn, invalid key or no quota left')
            return

        for i in list(range(1, limit)):
            try:
                if not 'nextPageToken' in result:
                    raise Exception
                next = url + '&pageToken=' + result['nextPageToken']
                result = client.request(next)
                result = json.loads(result)
                items += result['items']
            except Exception:
                pass

        for item in items:
            try:
                title = item['snippet']['title']
                try:
                    title = py2_enc(title)
                except AttributeError:
                    pass

                url = item['id']
                try:
                    url = py2_enc(url)
                except AttributeError:
                    pass

                image = item['snippet']['thumbnails']['high']['url']
                if '/default.jpg' in image:
                    raise Exception
                try:
                    image = py2_enc(image)
                except AttributeError:
                    pass

                self.list.append({'title': title, 'url': url, 'image': image})
            except Exception:
                pass

        return self.list

    def _video_list(self, cid, url, pagination, limit):

        try:
            result = client.request(url)
            result = json.loads(result)
            items = result['items']
        except Exception:
            log_debug('Youtube: Could not fetch items from the cdn, invalid key or no quota left')
            return

        for i in list(range(1, limit)):

            try:
                if pagination is True:
                    raise Exception
                if not 'nextPageToken' in result:
                    raise Exception
                page = url + '&pageToken=' + result['nextPageToken']
                result = client.request(page)
                result = json.loads(result)
                items += result['items']
            except Exception:
                pass

        try:
            if pagination is False:
                raise Exception
            next = cid + '&pageToken=' + result['nextPageToken']
        except Exception:
            next = ''

        for item in items:
            try:
                title = item['snippet']['title']
                try:
                    title = py2_enc(title)
                except AttributeError:
                    pass

                try:
                    url = item['snippet']['resourceId']['videoId']
                except (KeyError, ValueError):
                    url = item['id']['videoId']

                try:
                    url = py2_enc(url)
                except AttributeError:
                    pass

                image = item['snippet']['thumbnails']['high']['url']
                if '/default.jpg' in image:
                    raise Exception
                try:
                    image = py2_enc(image)
                except AttributeError:
                    pass

                try:
                    dateadded = item['snippet']['publishedAt']
                    dateadded = str(iso8601.parse_date(dateadded).strftime('%Y-%m-%d %H:%M:%S'))
                except Exception:
                    dateadded = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                date = '.'.join(dateadded.split()[0].split('-')[::-1])

                data = {
                    'title': title, 'url': url, 'image': image, 'dateadded': dateadded, 'date': date,
                    'premiered': dateadded.split()[0], 'aired': dateadded.split()[0], 'year': int(dateadded[:4])
                }

                if next != '':
                    data['next'] = next
                self.list.append(data)

            except Exception:
                pass

        try:
            urls = [list(range(0, len(self.list)))[i:i+50] for i in list(range(len(list(range(0, len(self.list))))))[::50]]
            urls = [','.join([self.list[x]['url'] for x in i]) for i in urls]
            urls = [self.content_link.format(''.join([i, self.key_link])) for i in urls]

            with concurrent_futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                
                threads = [executor.submit(self.thread, u) for u in urls]

                for future in concurrent_futures.as_completed(threads):

                    item = future.result()

                    if not item:
                        continue

                    self.data.append(item)

            items = []
            for i in self.data:
                items += json.loads(i)['items']
        except Exception:
            pass

        for item in list(range(0, len(self.list))):
            try:
                vid = self.list[item]['url']

                self.list[item]['url'] = self.play_link.format(py3_dec(vid))

                d = [(i['id'], i['contentDetails']) for i in items]
                d = [i for i in d if i[0] == vid]
                d = d[0][1]['duration']

                duration = 0
                try:
                    duration += 60 * 60 * int(re.search(r'(\d*)H', d).group(1))
                except Exception:
                    pass
                try:
                    duration += 60 * int(re.search(r'(\d*)M', d).group(1))
                except Exception:
                    pass
                try:
                    duration += int(re.search(r'(\d*)S', d).group(1))
                except Exception:
                    pass

                self.list[item]['duration'] = duration
            except Exception:
                pass

        return self.list

    def thread(self, url):

        try:
            result = client.request(url)
            return result
        except Exception:
            return

    def play(self, name, url=None, as_script=True, append_string=''):

        try:

            url = self.worker(name, url, append_string)
            if url is None:
                return

            title = control.infoLabel('listitem.title')
            if title == '':
                title = control.infoLabel('listitem.label')
            icon = control.infoLabel('listitem.icon')

            item = control.item(path=url)

            try:
                item.setArt({'icon': icon, 'thumb': icon})
            except Exception:
                pass

            item.setInfo(type='Video', infoLabels={'title': title})

            directory.resolve(url, meta={'title': title}, icon=icon, resolved_mode=not as_script)

        except Exception:

            pass

    def worker(self, name, url, append_string=''):

        try:

            if url.startswith(self.base_link):
                url = self.resolve(url)
                if url is None:
                    raise Exception
                return url
            elif not url.startswith('http://'):
                url = self.play_link.format(py3_dec(url))
                url = self.resolve(url)
                if url is None:
                    raise Exception
                return url
            else:
                raise Exception

        except Exception:

            query = ' '.join([name, append_string])
            query = self.youtube_search.format(py2_enc(query))
            url = self.search(query)

            if url is None:
                return

            return url

    def search(self, url):

        try:

            query = parse_qs(urlparse(url).query)['q'][0]

            url = self.search_link.format(''.join([quote_plus(query), self.key_link]))

            result = client.request(url)

            items = json.loads(result)['items']
            items = [(i['id']['videoId']) for i in items]

            for url in items:
                url = self.resolve(url)
                if url is not None:
                    return url

        except Exception:

            return

    def resolve(self, url):

        try:

            vid = url.split('?v=')[-1].split('/')[-1].split('?')[0].split('&')[0]

            url = self.play_link.format(py3_dec(vid))

            return url

        except Exception:

            return

    def convert(self, items_list, thumb_quality='medium'):

        for item in items_list[:-1]:

            title = item['snippet']['title']
            url = self.play_link.format(py3_dec(item['id']['videoId']))
            image = py3_dec(item['snippet']['thumbnails'][thumb_quality]['url'])
            plot = item['snippet']['description']

            data = {'title': title, 'url': url, 'image': image, 'plot': plot}

            self.list.append(data)

        return self.list


def thumb_maker(video_id, thumbnail_quality=MQ_THUMBNAIL):

    """
    Makes a video thumbnail out of a youtube video id

    :param video_id: A youtube video id <string>
    :param thumbnail_quality: integer, possible values 0, 1, 2
    :return: string
    """

    if thumbnail_quality == 2:
        thumbnail_quality = 'maxresdefault'
    elif thumbnail_quality == 1:
        thumbnail_quality = 'hqdefault'
    else:
        thumbnail_quality = 'mqdefault'

    return 'http://img.youtube.com/vi/{0}/{1}.jpg'.format(video_id, thumbnail_quality)


def feed_parser(url=None, channel_id=None, playlist_id=None, user=None):

    """
    Useful for loading a brief list of videos without API key
    """

    channel_prefix = 'https://www.youtube.com/feeds/videos.xml?channel_id={}'
    playlist_prefix = 'https://www.youtube.com/feeds/videos.xml?playlist_id={}'
    user_prefix = 'https://www.youtube.com/feeds/videos.xml?user={}'

    if channel_id:

        url = channel_prefix.format(channel_id)

    elif playlist_id:

        url = playlist_prefix.format(playlist_id)

    elif user:

        url = user_prefix.format(user)

    elif not url:

        raise TypeError('Did not provide a usable url for the feed parser to work')

    result = []

    xml = client.request(url)

    items = client.parseDOM(xml, 'entry')

    for item in items:

        title = client.parseDOM(item, 'title')[0]
        image = client.parseDOM(item, 'media:thumbnail', ret='url')[0]
        _url = client.parseDOM(item, 'link', ret='href')[0]
        plot = client.parseDOM(item, 'media:description')[0]

        data = {'title': title, 'image': image, 'url': _url, 'plot': plot}

        result.append(data)

    return result
