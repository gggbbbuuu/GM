# -*- coding: utf-8 -*-

'''
    Ant1 Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import sys
from tulip.compat import parse_qsl
from resources.lib import antenna

params = dict(parse_qsl(sys.argv[2].replace('?','')))

action = params.get('action')
url = params.get('url')
query = params.get('query')


if action is None:
    antenna.Indexer().root()

elif action == 'listing':
    antenna.Indexer().listing(url)

elif action == 'videos':
    antenna.Indexer().videos(url)

elif action == 'webtv':
    antenna.Indexer().webtv()

elif action == 'youtube_channel':
    antenna.Indexer().youtube_channel()

elif action == 'playlists':
    antenna.Indexer().playlists()

elif action == 'play':
    antenna.Indexer().play(url)

elif action == 'addBookmark':
    from tulip import bookmarks
    bookmarks.add(url)

elif action == 'deleteBookmark':
    from tulip import bookmarks
    bookmarks.delete(url)

elif action == 'bookmarks':
    antenna.Indexer().bookmarks()

elif action == 'switch':
    antenna.Indexer().switch(query)

elif action == 'cache_clear':
    from tulip import cache
    cache.FunctionCache().reset_cache(notify=True)
