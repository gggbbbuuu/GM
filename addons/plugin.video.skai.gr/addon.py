# -*- coding: utf-8 -*-

'''
    Skai Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
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
