# -*- coding: utf-8 -*-

'''
    ANT1 Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

BASE = 'https://www.antenna.gr'
CY_BASE = 'https://www.ant1live.com'

REGION_GR = 'GR'
REGION_CY = 'CY'

REGIONS = (
    (REGION_GR, 30074),
    (REGION_CY, 30075),
)

# ---------------------------------------------------------------------------
# Live
#
# Four channels, each with its own unauthenticated JSON endpoint. The playlist
# is a plain multi-bitrate HLS on mcdn.antennaplus.gr; only the main channel
# reports is_permited=1 but the variants serve regardless.
# ---------------------------------------------------------------------------

LIVE_CHANNELS = (
    ('live', 30040),
    ('livemak', 30041),
    ('livecomedy', 30042),
    ('livedrama', 30043),
)

LIVE_JSON = BASE + '/templates/data/{channel}?cache=1'

# ---------------------------------------------------------------------------
# Shows
#
# The shows index carries every show with its category and letter on one page
# (no paging JS): /<showslug>, title, image and data-category-id from the
# index itself. Categories filter server-side with the same markup.
# ---------------------------------------------------------------------------

SHOWS_PAGE = BASE + '/shows'
SHOW_CATEGORY = BASE + '/shows/ALL/{category_id}/{category_slug}'

SHOW_CATEGORIES = (
    ('2657', 'ellinikes-seires', 30044),
    ('2662', 'enimerosi', 30045),
    ('2663', 'psyxagogia', 30046),
    ('2652', 'eidiseis', 30047),
    ('2714', 'athlitikes-ekpompes', 30048),
)

# A show's videos live under /<showslug>/videos. The first page is inlined and
# a single "load more" call (templates/data/morevideos.aspx) returns the rest
# of the archive, keyed by the currentShowId embedded in the page.
SHOW_VIDEOS = BASE + '/{slug}/videos'
MORE_VIDEOS = BASE + '/templates/data/morevideos.aspx?showid={show_id}'

# ---------------------------------------------------------------------------
# News
#
# Section archives paginate server-side via categories.aspx (siteid=4):
# ?cid=<section>&p=<n>. Items are a mix of /watch/ clips (playable) and
# text articles (info only).
# ---------------------------------------------------------------------------

NEWS_SECTIONS = (
    ('2488', 'politics', 30049),
    ('2646', 'economy', 30050),
    ('2654', 'society', 30051),
    ('2655', 'world', 30052),
    ('2653', 'sports', 30053),
    ('18732', 'mellon', 30054),
    ('2656', 'health', 30055),
    ('2755', 'culture', 30056),
    ('2756', 'tech', 30057),
    ('2757', 'weather', 30058),
    ('17587', 'eidiseisimeras', 30059),
)

NEWS_PAGE = BASE + '/templates/data/categories.aspx?cid={cid}&p={page}&siteid=4'
NEWS_SECTION_PAGE = BASE + '/news/{slug}'

# The "related videos" rail some news section pages carry.
NEWS_RELATED = BASE + '/{section}/'

# ---------------------------------------------------------------------------
# Lifestyle
#
# Same paging machinery as news but on siteid=57 (fthis_categories.aspx).
# Almost entirely text articles; only /watch/ items are playable.
# ---------------------------------------------------------------------------

LIFESTYLE_SECTIONS = (
    ('5857', 'celebrity', 30060),
    ('5860', 'beauty', 30061),
    ('5861', 'fashion', 30062),
    ('5859', 'life', 30063),
    ('5858', 'videos', 30064),
    ('5854', 'latest', 30065),
)

LIFESTYLE_PAGE = BASE + '/templates/data/fthis_categories.aspx?cid={cid}&p={page}&siteid=57'
LIFESTYLE_SECTION_PAGE = BASE + '/lifestyle-showbiz/{slug}'
LIFESTYLE_VIDEOS = BASE + '/lifestyle-showbiz/videos'

# ---------------------------------------------------------------------------
# Sports highlights
#
# /f1 and /football are data hubs whose videoplay fragments bootstrap the
# same PlayerDataGraphQL player as /watch/ pages; the cids resolve identically.
# ---------------------------------------------------------------------------

SPORTS_SECTIONS = (
    ('f1', 30066),
    ('football', 30067),
)

# ---------------------------------------------------------------------------
# Radio
#
# soundis.gr is an Angular app, so the markup carries no stream. The public
# config exposes the API root; general-config (no auth) lists every station
# with a direct revma stream url. The edge redirects with a 5s token which
# Kodi follows natively, so the base stream url is all the add-on needs.
# ---------------------------------------------------------------------------

RADIO_CONFIG = 'https://api.soundis.gr/api/general-config'

# ---------------------------------------------------------------------------
# Web TV latest
# ---------------------------------------------------------------------------

WEBTV_PAGE = BASE + '/webtv'

# ---------------------------------------------------------------------------
# Cyprus (ant1live.com, Drupal)
#
# The Cypriot portal mirrors the Greek structure (live, indexes, player)
# but the paths differ and the two CDNs are per-site (cloudskep vs mcdn).
# Single-shot indexes: no paging machinery found, 404s confirm nothing
# paginates (e.g. /webtv/series/ellinikes-seires/paged/2).
# ---------------------------------------------------------------------------

CY_LIVE_PAGE = CY_BASE + '/webtv/live'

# Each section renders all its cards on one page.
CY_SECTIONS = (
    ('enimerosi', 30076),
    ('psyhagogia', 30077),
    ('podcasts', 30078),
    ('series', 30079),
    ('tainies', 30080),
)

CY_SECTION_PAGE = CY_BASE + '/webtv/{section}'

# Series/movies live one level deeper; any /webtv/<section>/<a>/<b> page is
# either a card sub-index or a playable episode, told apart at fetch time.
CY_SUBINDEX_PAGE = CY_BASE + '/webtv/{section}/{slug}'

# ---------------------------------------------------------------------------
# Playback
#
# Stream resolution is delegated to ResolveURL / PluginsGR's Ant1GRResolver,
# which already targets this site. /watch/ pages either carry a direct mp4
# (url) or bounce to ANT1+ originals (video_url + should_redirect), which is
# surfaced as an info dialog instead of a failed playback.
# ---------------------------------------------------------------------------

PLAYER_JSON = BASE + '/templates/data/PlayerDataGraphQL_v2?cid={cid}'

PLUGINSGR_ID = 'script.module.resolveurl.pluginsgr'
PLUGINS_PATH = 'special://home/addons/{0}/resources/plugins/'.format(PLUGINSGR_ID)


def bookmarks_file():
    from tulip import kodi
    import os

    return os.path.join(kodi.dataPath, 'bookmarks.db')
