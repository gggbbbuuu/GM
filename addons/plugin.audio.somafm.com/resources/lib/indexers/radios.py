# -*- coding: utf-8 -*-

'''
    Soma FM Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from tulip import directory, client, cache, control
from tulip.compat import urljoin, zip
import json, re
import datetime

method_cache = cache.FunctionCache().cache_method


class Indexer:

    def __init__(self):

        self.list = [] ; self.data = []
        self.main = 'http://somafm.com/'
        self.index = urljoin(self.main, 'channels.xml')

    @method_cache(int(control.setting('period') * 60))
    def get_stations(self):

        year = datetime.datetime.now().year

        xml = client.request(self.index)
        stations = client.parseDOM(xml, 'channel')
        ids = client.parseDOM(xml, 'channel', ret='id')

        items = list(zip(ids, stations))

        for sid, item in items:

            station = client.parseDOM(item, 'title')[0].partition('A[')[2][:-3]
            image = client.parseDOM(item, 'image')[0]
            urls = re.findall('<.+?pls.+?>(.+?)</.+?pls>', item)
            streams = repr(urls)
            listeners = client.parseDOM(item, 'listeners')[0]
            now = client.parseDOM(item, 'lastPlaying')[0].partition('A[')[2][:-3]
            song = now.partition(' - ')[2]
            artist = now.partition(' - ')[0]
            history = urljoin(self.main, sid + '/songhistory.html')
            genre = client.parseDOM(item, 'genre')[0]
            description = client.parseDOM(item, 'description')[0].partition('A[')[2][:-3]

            title = ' - '.join([station, song])

            data = {
                'title': title, 'image': image, 'url': streams, 'listeners': int(listeners), 'history': history,
                'genre': genre, 'artist': artist, 'album': station, 'year': year, 'comment': description,
                'mediatype': 'music'
            }

            self.list.append(data)

        return self.list

    def stations(self):

        self.list = self.get_stations()

        if self.list is None:
            return

        self.list = sorted(self.list, key=lambda k: k['album'].lower())

        for item in self.list:

            refresh = {'title': 30015, 'query': {'action': 'refresh'}}
            cache_clear = {'title': 30002, 'query': {'action': 'cache_clear'}}
            info_cm = {'title': 30020, 'query': {'action': 'info_cm'}}
            station_info = {'title': 30016, 'query': {'action': 'description', 'text': item['comment']}}
            history = {'title': 30017, 'query': {'action': 'history', 'url': item['history']}}

            if control.kodi_version() < 17.0:
                item.update({'cm': [refresh, cache_clear, history], 'action': 'play', 'isFolder': 'False'})
            else:
                item.update(
                    {
                        'cm': [refresh, cache_clear, history, station_info, info_cm],
                        'action': 'play', 'isFolder': 'False'
                    }
                )

        for count, item in list(enumerate(self.list, start=1)):
            item.setdefault('tracknumber', count)

        control.sortmethods()
        control.sortmethods('album')
        control.sortmethods('genre')
        control.sortmethods('listeners')

        directory.add(self.list, infotype='music')
