# -*- coding: utf-8 -*-

'''
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
'''


import sys
from tulip.compat import parse_qsl
from xbmc import getInfoLabel
from resources.lib import skai


params = dict(parse_qsl(sys.argv[2].replace('?','')))

action = params.get('action')
url = params.get('url')

fp = getInfoLabel('Container.FolderPath')

if action is None:
    skai.Indexer().root(audio_only='audio' in fp)

elif action == 'addBookmark':
    from tulip import bookmarks
    bookmarks.add(url)

elif action == 'deleteBookmark':
    from tulip import bookmarks
    bookmarks.delete(url)

elif action == 'bookmarks':
    skai.Indexer().bookmarks()

elif action == 'shows':
    skai.Indexer().shows(url)

elif action == 'podcasts':
    skai.Indexer().podcasts(url)

elif action == 'archive':
    skai.Indexer().archive()

elif action == 'episodes':
    skai.Indexer().episodes(url)

elif action == 'latest':
    skai.Indexer().latest()

elif action == 'news':
    skai.Indexer().news()

elif action == 'videos':
    skai.Indexer().videos(url)

elif action == 'play':
    skai.Indexer().play(url)

elif action == 'cache_clear':
    from tulip import cache
    cache.FunctionCache().reset_cache(notify=True)
