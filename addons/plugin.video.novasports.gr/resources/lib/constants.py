# -*- coding: utf-8 -*-

'''
    Novasports.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

BASE_LINK = 'https://www.novasports.gr'

# The site is a WordPress install. The legacy /api/v1 endpoints this add-on
# used to scrape were retired along with the old front-end, so browsing is
# built on the public REST API.
REST_LINK = ''.join([BASE_LINK, '/wp-json'])
VIDEO_REST_LINK = ''.join([REST_LINK, '/wp/v2/video'])
MATCHCENTER_LINK = ''.join([REST_LINK, '/nova/match-center'])

# Keep listings light: these are the only fields the listing needs.
VIDEO_FIELDS = 'id,date,link,title,featured_media_url,acf,taxonomies'

# WordPress taxonomies exposed by the video post type.
TAX_SPORT = 'sport'
TAX_EVENT = 'event'
TAX_TEAM = 'team-sport'
TAX_SHOW = 'show'

# The site no longer streams live, but NovaSports keeps its channel on
# YouTube and embeds those broadcasts in the web tv listings.
YT_CHANNEL = 'https://www.youtube.com/@novasports'
YT_WATCH = 'https://www.youtube.com/watch?v='

# Stream resolution lives in the PluginsGR resolver, this is where Kodi keeps it.
PLUGINSGR_ID = 'script.module.resolveurl.pluginsgr'
PLUGINS_PATH = 'special://home/addons/{0}/resources/plugins/'.format(PLUGINSGR_ID)