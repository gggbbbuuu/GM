# -*- coding: utf-8 -*-

'''
    Ant1 Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
from base64 import b64decode
from zlib import decompress
from tulip.url_dispatcher import urldispatcher
from tulip import cache, control, bookmarks
from .constants import SCRAMBLE
from youtube_registration import register_api_keys


@urldispatcher.register('clear_cache')
def clear_cache():
    cache.FunctionCache().reset_cache(notify=True)


def keys_registration():

    setting = control.addon('plugin.video.youtube').getSetting('youtube.allow.dev.keys') == 'true'

    if setting:

        keys = json.loads(decompress(b64decode(SCRAMBLE)))

        register_api_keys(control.addonInfo('id'), keys['api_key'], keys['id'], keys['secret'])


@urldispatcher.register('addBookmark', ['url'])
def add_bookmark(url):
    bookmarks.add(url)


@urldispatcher.register('deleteBookmark', ['url'])
def delete_bookmark(url):
    bookmarks.delete(url)
