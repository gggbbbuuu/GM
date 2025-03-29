# -*- coding: utf-8 -*-

'''
    Alpha Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


import sys
from tulip.compat import parse_qsl
from resources.lib import alphatv


params = dict(parse_qsl(sys.argv[2].replace('?','')))

action = params.get('action')
url = params.get('url')
title = params.get('title')
name = params.get('name')
image = params.get('image')
query = params.get('query')


if action is None:
    alphatv.Indexer().root()

elif action == 'addBookmark':
    from tulip import bookmarks
    bookmarks.add(url)

elif action == 'deleteBookmark':
    from tulip import bookmarks
    bookmarks.delete(url)

elif action == 'recent':
    alphatv.Indexer().recent()

elif action == 'bookmarks':
    alphatv.Indexer().bookmarks()

elif action == 'index':
    alphatv.Indexer().index(url)

elif action == 'news':
    alphatv.Indexer().news(url)

elif action == 'episodes':
    alphatv.Indexer().episodes(url, title, name, image)

elif action == 'news_episodes':
    alphatv.Indexer().news_episodes(query)

elif action == 'play':
    alphatv.Indexer().play(url)

elif action == 'cache_clear':
    from tulip.cache import FunctionCache
    FunctionCache().reset_cache(notify=True)

elif action == 'selector':
    alphatv.Indexer().selector()

elif action == 'enter_date':
    alphatv.Indexer().enter_date()

elif action == 'switch':
    alphatv.Indexer().switch(query)

elif action == 'back':
    from tulip.control import execute
    execute('Action(Back)')
