# -*- coding: utf-8 -*-

'''
    Skai Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

BASE = 'https://www.skai.gr'
BASE_TV = BASE + '/tv'

LIVE_PAGE = BASE_TV + '/live'
TRENDING_PAGE = BASE_TV + '/trending'
CINEMA_PAGE = BASE_TV + '/cinema'
PROGRAMMA_PAGE = BASE_TV + '/programma'

SHOWS_PAGE = BASE_TV + '/shows/{0}'

# The TV sections rendered on https://www.skai.gr/tv/ and their own pages.
TV_SECTIONS = (
    ('enimerosi', 30011),
    ('seires', 30012),
    ('psuchagogia', 30013),
    ('ntokimanter', 30014),
    ('athlitika', 30015),
)

# Live radio and the radio archive (podcasts).
RADIO_LIVE_URL = 'https://skai.live24.gr/skai1003'
RADIO_BASE = 'http://www.skairadio.gr'
RADIO_SHOWS_PAGE = RADIO_BASE + '/shows?page={0}'

# My Style Rocks keeps no pages on skai.gr; its dedicated YouTube
# channel is unfolded instead (videos, shorts and season playlists).
MSR_CHANNEL = 'https://www.youtube.com/@MyStyleRocksGR'
MSR_LIMIT = 100

PAGE_SIZE = 20


def bookmarks_file():
    from tulip import kodi
    import os

    return os.path.join(kodi.dataPath, 'bookmarks.db')


# ---------------------------------------------------------------------------
# Playback
#
# Stream resolution is delegated to ResolveURL / PluginsGR's SkaiResolver,
# which targets the current site (live m3u8, episode/show media_item_file
# through the videostream player, YouTube embeds via YouTubeGR).
# ---------------------------------------------------------------------------

PLUGINSGR_ID = 'script.module.resolveurl.pluginsgr'
PLUGINS_PATH = 'special://home/addons/{0}/resources/plugins/'.format(PLUGINSGR_ID)
