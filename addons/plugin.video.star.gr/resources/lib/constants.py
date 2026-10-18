# -*- coding: utf-8 -*-

'''
    Star Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

BASE = 'https://www.star.gr'
BASE_TV = BASE + '/tv'
BASE_VIDEO = BASE + '/video'

LIVE_PAGE = BASE_TV + '/live-stream/'
LIVE_INTERNATIONAL_PAGE = BASE_TV + '/star-international-live-stream/'

TV_PAGE = BASE_TV + '/'
PROGRAMMA_PAGE = BASE_TV + '/programma/'
PROGRAMMA_ROWS = BASE_TV + '/$component/ProgramProgramRows'
SEARCH_URL = BASE_TV + '/$component/Search?profile=Autocomplete&view=Autocomplete&q={0}'

VIDEO_PAGE = BASE_VIDEO + '/'

VIDEO_SITEMAP_INDEX = BASE + '/sitemaps/videos/videos.xml'

# The TV sections rendered on https://www.star.gr/tv/ and their own pages.
TV_SECTIONS = (
    ('psychagogia', 30016),
    ('seires', 30002),
    ('starland', 30024),
)

# Curated hubs shown under Videos, mirroring the /video/ index cards.
# Label ids live in the addon strings (30072-30077).
VIDEO_HUBS = (
    ('cash-or-trash', 30072),
    ('gntm', 30073),
    ('first-dates', 30074),
    ('eidiseis', 30010),
    ('starx', 30008),
    ('protos-kafes-me-th-zhna', 30075),
    ('master-syntages', 30076),
    ('farma', 30077),
)

PAGE_SIZE = 20


def bookmarks_file():
    from tulip import kodi
    import os

    return os.path.join(kodi.dataPath, 'bookmarks.db')


# ---------------------------------------------------------------------------
# Playback
#
# Stream resolution is delegated to ResolveURL / PluginsGR's StarResolver,
# which targets the rebuilt site (live m3u8, /video/ kwik m3u8, /tv/ episode
# contentUrl, YouTube iframe embeds).
# ---------------------------------------------------------------------------

PLUGINSGR_ID = 'script.module.resolveurl.pluginsgr'
PLUGINS_PATH = 'special://home/addons/{0}/resources/plugins/'.format(PLUGINSGR_ID)
