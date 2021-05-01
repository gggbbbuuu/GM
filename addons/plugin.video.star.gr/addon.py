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


from sys import argv
from resources.lib import star
from tulip.compat import parse_qsl

params = dict(parse_qsl(argv[2].replace('?', '')))

action = params.get('action')
url = params.get('url')
image = params.get('image')
title = params.get('title')
query = params.get('query')


if action is None:
    star.Indexer().root()

elif action == 'addBookmark':
    from tulip import bookmarks
    bookmarks.add(url)

elif action == 'deleteBookmark':
    from tulip import bookmarks
    bookmarks.delete(url)

elif action == 'bookmarks':
    star.Indexer().bookmarks()

elif action == 'startv':
    star.Indexer().startv()

elif action == 'news':
    star.Indexer().news()

elif action == 'starx':
    star.Indexer().starx()

elif action == 'show':
    star.Indexer().show(url)

elif action == 'videos':
    star.Indexer().videos()

elif action == 'category':
    star.Indexer().category(url)

elif action == 'starx_videos':
    star.Indexer().starx_videos(url, title)

elif action == 'starx_shows':
    star.Indexer().starx_shows()

elif action == 'archive':
    star.Indexer().archive()

elif action == 'youtube':
    star.Indexer().youtube(url)

elif action == 'selector':
    star.Indexer().selector(query=query)

elif action == 'play':
    star.Indexer().play(url, query)

elif action == 'cache_clear':
    from tulip import cache
    cache.FunctionCache().reset_cache(True)
