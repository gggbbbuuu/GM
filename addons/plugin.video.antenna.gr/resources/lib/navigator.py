# -*- coding: utf-8 -*-

'''
    Ant1 Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import absolute_import

import re
import json
from tulip import directory, cache, control, client, bookmarks as bms
from tulip.parsers import itertags
from tulip.compat import iteritems
from tulip.url_dispatcher import urldispatcher
from youtube_resolver import resolve as yt_resolver
from .constants import *

cache_function = cache.FunctionCache().cache_function


@urldispatcher.register('root')
def root():

    self_list = [
        {
            'title': control.lang(30001),
            'action': 'play',
            'isFolder': 'False',
            'icon': 'live.jpg',
            'url': LIVE_LINK
        }
        ,
        {
            'title': control.lang(30002),
            'action': 'radios',
            'icon': 'radio.jpg'
        }
        ,
        {
            'title': control.lang(30014),
            'action': 'videos',
            'url': VIDEOS_LINK
        }
        ,
        {
            'title': control.lang(30003),
            'action': 'youtube',
            'icon': 'youtube.jpg',
            'isFolder': 'False',
            'isPlayable': 'False',
            'url': YT_ID
        }
        ,
        {
            'title': control.lang(30013),
            'action': 'bookmarks',
            'icon': 'bookmarks.jpg'
        }
    ]

    for item in self_list:
        cache_clear = {'title': 30011, 'query': {'action': 'clear_cache'}}
        item.update({'cm': [cache_clear]})

    directory.add(self_list, content='videos')


@urldispatcher.register('bookmarks')
def bookmarks():

    self_list = bms.get()

    if not self_list:
        na = [{'title': control.lang(30012), 'action': None}]
        directory.add(na)
        return

    for i in self_list:
        bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
        bookmark['delbookmark'] = i['url']
        i.update({'cm': [{'title': 30502, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

    control.sortmethods()
    control.sortmethods('title')

    directory.add(self_list)


@cache_function(172800)
def video_list(url):

    html = client.request(url)

    next_url = [i.attributes for i in itertags(html, 'a') if 'WRC' in i.attributes.get('onclick', '')][-1]['onclick']
    next_url = ''.join([VIDEOS_BASE, next_url.replace('getdata("', '').replace('","WRC")', '')])

    items = [i.text for i in itertags(html, 'article')]

    self_list = []

    for item in items:

        title = client.parseDOM(item, 'h3')[0]
        try:
            image = client.parseDOM(item, 'img', ret='src')[0]
        except IndexError:
            image = control.icon()
        url = client.parseDOM(item, 'a', ret='href')[0]
        url = ''.join([VIDEOS_BASE, url])
        self_list.append({'title': title, 'url': url, 'image': image, 'next': next_url})

    return self_list


@urldispatcher.register('videos', ['url'])
def videos(url):

    self_list = video_list(url)

    for i in self_list:
        i.update(
            {
                'action': 'play', 'isFolder': 'False', 'nextaction': 'videos',
                'nexticon': control.addonmedia('next.jpg'), 'nextlabel': 30015
            }
        )
        bookmark = dict((k, v) for k, v in iteritems(i) if not k == 'next')
        bookmark['bookmark'] = i['url']
        i.update({'cm': [{'title': 30501, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}]})

    directory.add(self_list)


@cache_function(172800)
def radio_list():

    html = client.request(LIVE_RADIO)

    items = client.parseDOM(html, 'div', attrs={'data-index': '\d'})

    self_list = []

    for item in items:

        title = client.parseDOM(item, 'span')[0]
        image = client.parseDOM(item, 'img', attrs={'class': 'sc-3izq3s-0 gRHEnj'}, ret='src')[0]
        url = client.parseDOM(item, 'a', ret='href')[0]
        self_list.append({'title': title, 'url': url, 'image': image})

    return self_list


@urldispatcher.register('radios')
def radios():

    self_list = radio_list()

    for i in self_list:
        i.update({'action': 'play', 'isFolder': 'False'})

    directory.add(self_list)


@cache_function(172800)
def cached_resolve(url):

    if RADIO_BASE in url:

        html = client.request(url)
        url = re.search(r'"stationAACStream":"(.+?)\?', html).group(1)

    else:

        vid = re.search(r'watch/(\d+)/', url).group(1)
        json_ = client.request(PLAYER_LINK.format(vid), output='json')
        url = json_['url']

    return url


def resolve(url):

    if RADIO_BASE in url:

        return cached_resolve(url)

    elif 'plugin://' in url:

        vid = re.search(r'video_id=([\w-]{11})', url).group(1)

        streams = yt_resolver(vid)

        try:
            addon_enabled = control.addon_details('inputstream.adaptive').get('enabled')
        except KeyError:
            addon_enabled = False

        if not addon_enabled:
            streams = [s for s in streams if 'mpd' not in s['title'].lower()]

        stream = streams[0]['url']

        return stream

    else:

        return cached_resolve(url)


@urldispatcher.register('play', ['url'])
def play(url):

    if '.m3u8' not in url:
        url = resolve(url)

    dash = ('.m3u8' in url or '.mpd' in url) and control.kodi_version() >= 18.0

    meta = None

    if url == LIVE_LINK:
        meta = {'title': 'ANT1'}

    directory.resolve(
        url, dash=dash, meta=meta,
        mimetype='application/vnd.apple.mpegurl' if 'm3u8' in url else None,
        manifest_type='hls' if 'm3u8' in url else None
    )


@urldispatcher.register('youtube', ['url'])
def youtube(url):

    if not url.startswith('plugin://'):
        url = ''.join(['plugin://plugin.video.youtube/channel/', url, '/?addon_id=', control.addonInfo('id')])

    control.execute('Container.Update({},return)'.format(url))
