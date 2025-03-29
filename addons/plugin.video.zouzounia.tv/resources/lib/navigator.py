# -*- coding: utf-8 -*-

"""
    Zouzounia TV Addon
    Author: Twilight0

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
from __future__ import print_function

import json
from base64 import b64decode
from tulip import youtube, directory, control, cache, bookmarks, client
from tulip.url_dispatcher import urldispatcher
from tulip.compat import iteritems
from youtube_resolver import resolve as resolver

key = b64decode('RFkTsdWbPFDTt1ETxU1TEFnWtxkNRNlTMRUa391Y2IVQ5NVY6lUQ'[::-1])  # please do not copy this key
function_cache = cache.FunctionCache().cache_function


def channel_id():

    if control.setting('language') == '0':
        if control.infoLabel('System.Language') == 'Greek':
            main_id = 'UC9QSJuIBLUT2GbjgKymkTaQ'
        elif control.infoLabel('System.Language') == 'Japanese':
            main_id = 'UCGVTSfgmHJBzpq1gVq1ofhA'
        else:
            main_id = 'UCzsQf6eiWz4gIHgx0oYadXA'
    elif control.setting('language') == '2':
        main_id = 'UC9QSJuIBLUT2GbjgKymkTaQ'
    elif control.setting('language') == '3':
        main_id = 'UCGVTSfgmHJBzpq1gVq1ofhA'
    else:
        main_id = 'UCzsQf6eiWz4gIHgx0oYadXA'

    return main_id


@urldispatcher.register('main')
def main():

    self_list = [
        {
            'title': control.lang(30001),
            'action': 'videos',
            'icon': 'videos.jpg'
        }
        ,
        {
            'title': control.lang(30002),
            'action': 'playlists',
            'icon': 'playlists.jpg'
        }
        ,
        {
            'title': control.lang(30003),
            'action': 'bookmarks',
            'icon': 'heart.jpg'
        }
        ,
        {
            'title': control.lang(30004),
            'action': 'settings',
            'icon': 'settings.jpg',
            'isFolder': 'False',
            'isPlayable': 'False'
        }
    ]

    cc = {'title': 30005, 'query': {'action': 'cache_clear'}}

    for item in self_list:
        item.update({'cm': [cc]})

    directory.add(self_list)


@function_cache(2880)
def yt_playlists():
    return youtube.youtube(key=key).playlists(channel_id())


@function_cache(720)
def yt_playlist(url):
    
    return youtube.youtube(key=key).playlist(url, limit=10)


@function_cache(360)
def yt_videos():
    
    return youtube.youtube(key=key).videos(channel_id(), limit=2)


@urldispatcher.register('playlists')
def playlists():

    self_list = yt_playlists()

    for p in self_list:
        p.update({'action': 'youtu'})
        bookmark = dict((k, v) for k, v in iteritems(p) if not k == 'next')
        bookmark['bookmark'] = p['url']
        bm_cm = {'title': 30006, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}
        refresh = {'title': 30008, 'query': {'action': 'refresh'}}
        cache_clear = {'title': 30005, 'query': {'action': 'cache_clear'}}
        p.update({'cm': [refresh, cache_clear, bm_cm]})

    directory.add(self_list)


@urldispatcher.register('youtu', ['url'])
def youtu(url):

    self_list = yt_playlist(url)

    if self_list is None:
        return

    for v in self_list:
        try:
            title = v['title'].decode('utf-8')
        except AttributeError:
            title = v['title']
        v.update({'action': 'play', 'isFolder': 'False', 'title': client.replaceHTMLCodes(title)})

    for item in self_list:
        bookmark = dict((k, v) for k, v in iteritems(item) if not k == 'next')
        bookmark['bookmark'] = item['url']
        bm_cm = {'title': 30006, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}
        refresh = {'title': 30008, 'query': {'action': 'refresh'}}
        cache_clear = {'title': 30005, 'query': {'action': 'cache_clear'}}
        item.update({'cm': [refresh, cache_clear, bm_cm]})

    directory.add(self_list)


@urldispatcher.register('videos')
def videos():

    self_list = yt_videos()

    if self_list is None:
        return

    for v in self_list:
        try:
            title = v['title'].decode('utf-8')
        except AttributeError:
            title = v['title']
        v.update({'action': 'play', 'isFolder': 'False', 'title': client.replaceHTMLCodes(title)})

    for item in self_list:
        bookmark = dict((k, v) for k, v in iteritems(item) if not k == 'next')
        bookmark['bookmark'] = item['url']
        bm_cm = {'title': 30006, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}
        refresh = {'title': 30008, 'query': {'action': 'refresh'}}
        cache_clear = {'title': 30005, 'query': {'action': 'cache_clear'}}
        item.update({'cm': [refresh, cache_clear, bm_cm]})

    directory.add(self_list)


@urldispatcher.register('bookmarks')
def bm_list():

    bm = bookmarks.get()

    na = [{'title': 30012, 'action': None, 'icon': 'not-found.jpg'}]

    if not bm:
        directory.add(na)
        return na

    for item in bm:
        bookmark = dict((k, v) for k, v in iteritems(item) if not k == 'next')
        bookmark['delbookmark'] = item['url']
        item.update({'cm': [{'title': 30007, 'query': {'action': 'deleteBookmark', 'url': json.dumps(bookmark)}}]})

    self_list = sorted(bm, key=lambda k: k['title'].lower())

    directory.add(self_list)


def session(link):

    streams = resolver(link)

    try:
        addon_enabled = control.addon_details('inputstream.adaptive').get('enabled')
    except KeyError:
        addon_enabled = False

    if not addon_enabled:
        streams = [s for s in streams if 'mpd' not in s['title'].lower()]

    stream = streams[0]['url']

    return stream


@urldispatcher.register('play', ['url'])
def play(url):

    stream = session(url)

    directory.resolve(stream, dash='.mpd' in stream)
