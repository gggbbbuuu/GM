# -*- coding: utf-8 -*-

'''
    E-Radio Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


import sys
from tulip.compat import parse_qsl
from resources.lib import eradio

params = dict(parse_qsl(sys.argv[2].replace('?','')))

action = params.get('action')
url = params.get('url')

if action is None:
    eradio.Indexer().root()

elif action == 'addBookmark':
    from tulip import bookmarks
    bookmarks.add(url)

elif action == 'deleteBookmark':
    from tulip import bookmarks
    bookmarks.delete(url)

elif action == 'bookmarks':
    eradio.Indexer().bookmarks()

elif action == 'radios':
    eradio.Indexer().radios(url)

elif action == 'dev_picks':
    eradio.Indexer().dev_picks()

elif action == 'search':
    eradio.Indexer().search()

elif action == 'cache_clear':
    from tulip.cache import FunctionCache
    FunctionCache().reset_cache(notify=True, label_success=30008)

elif action in ['play', 'dev_play']:
    eradio.Indexer().play(url, do_not_resolve=action == 'dev_play')
