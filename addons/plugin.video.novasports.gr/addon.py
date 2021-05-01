# -*- coding: utf-8 -*-

'''
    Novasports.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


import sys
from resources.lib import novasports
from tulip.compat import parse_qsl

params = dict(parse_qsl(sys.argv[2].replace('?','')))

action = params.get('action')
url = params.get('url')
query = params.get('query')

if action is None or action == 'root':
    novasports.Indexer().root()

elif action == 'videos':
    novasports.Indexer().videos(url=url, query=query)

elif action == 'matches':
    novasports.Indexer().matches(query=query)

elif action == 'event':
    novasports.Indexer().event(url)

elif action == 'add_date':
    novasports.Indexer().add_date()

elif action == 'webtv':
    novasports.Indexer().webtv()

elif action == 'teams_index':
    novasports.Indexer().teams_index()

elif action == 'categories':
    novasports.Indexer().categories()

elif action == 'switch':
    novasports.Indexer().switch()

elif action == 'bookmarks':
    novasports.Indexer().bookmarks()

elif action == 'go_to_root':
    from tulip.directory import run_builtin
    run_builtin(action='root', path_history='replace')

elif action == 'play':
    novasports.Indexer().play(url)

elif action == 'cache_clear':
    from tulip import cache
    cache.FunctionCache().reset_cache(notify=True)
