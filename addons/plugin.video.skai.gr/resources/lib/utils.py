# -*- coding: utf-8 -*-

'''
    Skai Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

from tulip import kodi, bookmarks
from urldispatcher import urldispatcher

try:
    from pickled import FunctionCache

    cache = FunctionCache(kodi.cacheDirectory)
except Exception:
    cache = None


from .constants import bookmarks_file


@urldispatcher.register('clear_cache')
def clear_cache():

    if cache is not None:
        cache.reset_cache()

    kodi.infoDialog(kodi.i18n(30402))


@urldispatcher.register('settings')
def settings():

    kodi.openSettings()


@urldispatcher.register('addBookmark', ['url'])
def add_bookmark(url):

    bookmarks.add(url, path=bookmarks_file())


@urldispatcher.register('deleteBookmark', ['url'])
def delete_bookmark(url):

    bookmarks.delete(url, path=bookmarks_file())


@urldispatcher.register('clear_bookmarks')
def clear_bookmarks():

    bookmarks.clear(['bookmark'], path=bookmarks_file())
    kodi.sleep(200)
    kodi.refresh()
