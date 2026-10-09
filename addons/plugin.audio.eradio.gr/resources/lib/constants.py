# -*- coding: utf-8 -*-

'''
    E-Radio Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from tulip.kodi import cacheDirectory, join
from pickled import FunctionCache

# Bump whenever fetch/parse logic changes so stale cached listings can never
# be served after an update.
CACHE_VERSION = 'v2'

_cache_path = join(cacheDirectory, CACHE_VERSION)

cache_function = FunctionCache(_cache_path).cache_function
reset_cache = FunctionCache(_cache_path).reset_cache

BASE_LINK = 'https://eradio.mobi'
IMAGE_LINK = 'https://cdn.e-radio.gr/logos/{0}'
ALL_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist.json'])
TRENDING_LINK = ''.join([BASE_LINK, '/cache/1/1/medialistTop_trending.json'])
POPULAR_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist_top20.json'])
NEW_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist_new.json'])
CATEGORIES_LINK = ''.join([BASE_LINK, '/cache/1/1/categories.json'])
REGIONS_LINK = ''.join([BASE_LINK, '/cache/1/1/regions.json'])
CATEGORY_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist_categoryID{0}.json'])
REGION_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist_regionID{0}.json'])
RESOLVE_LINK = ''.join([BASE_LINK, '/cache/1/1/media/{0}.json'])
DEV_PICKS_LINK = 'https://gist.githubusercontent.com/Twilight0/f74c12af7c572fac716f9d3b9e05f569/raw/radios.json'
# "Internet Radios" region; external developer picks are merged into it.
INTERNET_LINK = REGION_LINK.format('16')


def cache_duration(minutes):
    from tulip import kodi
    try:
        if kodi.setting('debug') == 'true':
            return 0
    except Exception:
        pass
    return minutes
