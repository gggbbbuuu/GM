# -*- coding: utf-8 -*-

'''
    Star Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


from sys import argv
from resources.lib import navigator
from tulip.compat import parse_qsl

params = dict(parse_qsl(argv[2].replace('?', '')))

action = params.get('action')
url = params.get('url')
image = params.get('image')
title = params.get('title')
query = params.get('query')


if action is None:
    navigator.Indexer().root()

elif action == 'addBookmark':
    from tulip import bookmarks
    bookmarks.add(url)

elif action == 'deleteBookmark':
    from tulip import bookmarks
    bookmarks.delete(url)

elif action == 'bookmarks':
    navigator.Indexer().bookmarks()

elif action == 'startv':
    navigator.Indexer().startv(query)

elif action == 'news':
    navigator.Indexer().news()

elif action == 'starx':
    navigator.Indexer().starx()

elif action == 'show':
    navigator.Indexer().show(url)

elif action == 'videos':
    navigator.Indexer().videos()

elif action == 'category':
    navigator.Indexer().category(url)

elif action == 'starx_videos':
    navigator.Indexer().starx_videos(url, title)

elif action == 'starx_shows':
    navigator.Indexer().starx_shows()

elif action == 'archive':
    navigator.Indexer().archive()

elif action == 'youtube':
    navigator.Indexer().youtube(url)

elif action == 'selector':
    navigator.Indexer().selector(query=query)

elif action == 'play':
    navigator.Indexer().play(url, query)

elif action == 'cache_clear':
    from tulip import cache
    cache.FunctionCache().reset_cache(True)
