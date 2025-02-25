# -*- coding: utf-8 -*-

'''
    E-Radio Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

BASE_LINK = 'http://eradio.mobi'
IMAGE_LINK = 'http://cdn.e-radio.gr/logos/{0}'
ALL_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist.json'])
TRENDING_LINK = ''.join([BASE_LINK, '/cache/1/1/medialistTop_trending.json'])
POPULAR_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist_top20.json'])
NEW_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist_new.json'])
CATEGORIES_LINK = ''.join([BASE_LINK, '/cache/1/1/categories.json'])
REGIONS_LINK = ''.join([BASE_LINK, '/cache/1/1/regions.json'])
CATEGORY_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist_categoryID{0}.json'])
REGION_LINK = ''.join([BASE_LINK, '/cache/1/1/medialist_regionID{0}.json'])
RESOLVE_LINK = ''.join([BASE_LINK, '/cache/1/1/media/{0}.json'])
