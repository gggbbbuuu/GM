# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

from xbmcaddon import Addon
from collections import OrderedDict
from urllib.parse import urljoin
from datetime import datetime
from tulip.kodi import dataPath, join, cacheDirectory, i18n
from pickled import FunctionCache

cache_function = FunctionCache(cacheDirectory).cache_function
cache_method = FunctionCache(cacheDirectory).cache_method

########################################################################################################################

ART_ID = 'resource.images.alivegr.artwork'
LOGOS_ID = 'resource.images.alivegr.logos'
PLUGINS_ID = 'script.module.resolveurl.pluginsgr'
PLUGINS_PATH = 'special://home/addons/{0}/resources/plugins/'.format(PLUGINS_ID)
YT_ADDON_ID = 'plugin.video.youtube'
YT_ADDON = 'plugin://{0}'.format(YT_ADDON_ID)
YT_URL = 'https://www.youtube.com/watch?v='
YT_API = 'https://www.youtube.com/youtubei/v1/browse?key={}'
YT_PREFIX = YT_ADDON + '/play/?video_id='
PLAY_ACTION = '?action=play&url='
ALIVEGR = (
    '42bzpmLoN2Xyd2L3FmcvYmY0IGN3YmZ2QDZ0EGN4EWMwQGOzcDZxYGZ1EjYyUzYvADdodWasl2dU9SbvNmL05WZ052bj'
    'JXZzVnY1hGdpdmL0NXan9yL6MHc0RHa'
)

########################################################################################################################

WEBSITE = 'https://github.com/Twilight0/plugin.video.alivegr'
FACEBOOK = 'https://www.facebook.com/alivegr/'
TWITTER = 'https://x.com/TwilightZer0'
PAYPAL = 'https://www.paypal.me/AliveGR'
PATREON = 'https://www.patreon.com/twilight0'
SUPPORT = 'https://github.com/Twilight0/plugin.video.alivegr/issues'
FORUM = 'https://github.com/Twilight0/plugin.video.alivegr/discussions'

########################################################################################################################

M3U_LINK = 'https://raw.githubusercontent.com/komhsgr/m3u/refs/heads/main/Greekstreamtv.m3u'

########################################################################################################################

GM_BASE = 'https://greek-movies.com/'
GM_MOVIES = urljoin(GM_BASE, 'movies.php')
GM_SHOWS = urljoin(GM_BASE, 'shows.php')
GM_SERIES = urljoin(GM_BASE, 'series.php')
GM_ANIMATION = urljoin(GM_BASE, 'animation.php')
GM_THEATER = urljoin(GM_BASE, 'theater.php')
GM_SPORTS = urljoin(GM_BASE, 'sports.php')
GM_SHORTFILMS = urljoin(GM_BASE, 'shortfilm.php')
GM_MUSIC = urljoin(GM_BASE, 'music.php')
GM_SEARCH = urljoin(GM_BASE, 'search.php')
GM_PERSON = urljoin(GM_BASE, 'person.php')
GM_EPISODE = urljoin(GM_BASE, 'ajax.php?type=episode&epid={0}&view={1}')

########################################################################################################################

GF_BASE = 'https://greekfun.net'
GFM_GETTER = (
        'u92cq5ycllmdv12Xmd2L3FmcvMjZhZTOhZmMiZDZkhzNzIzNhJTYiJWYxQTM2QTYxgjZvADdodWas'
        'l2dU9SbvNmL05WZ052bjJXZzVnY1hGdpdmL0NXan9yL6MHc0RHa'
    )

GFS_GETTER = (
        'u92cq5ycllmclN3Xmd2L3FmcvcjYwMDZxgTO3MWYilTNxETZ0UzY1ITZ4EWO1EWN0cDNvADdodWasl2d'
        'U9SbvNmL05WZ052bjJXZzVnY1hGdpdmL0NXan9yL6MHc0RHa'
    )

GFK_GETTER = (
    '==gbvNnauMHZpt2Xmd2L3FmcvAzYhlDM3EGOhVmZ3IjNkV2Y3MGZhZTMmhjZkJ2NmJjMvADdodWasl2dU9S'
    'bvNmL05WZ052bjJXZzVnY1hGdpdmL0NXan9yL6MHc0RHa'
)

########################################################################################################################

LIVE_GROUPS = OrderedDict(
    [
        ('Panhellenic', 30201), ('Pancypriot', 30202), ('International', 30203), ('Regional', 30207),
        ('Music', 30125), ('Cinema', 30205), ('Kids', 30032), ('Sports', 30094), ('Web TV', 30210)
    ]
)

QUERY_MAP = OrderedDict(
            [
                ('Live TV Channel', 30113), ('Movie', 30130), ('TV Serie', 30305), ('TV Show', 30133),
                ('Theater', 30068), ('Cartoon', 30097), ('Person', 30101)
            ]
        )

########################################################################################################################

GENRES = {
    'κωμωδία': i18n(30021),
    'δράμα': i18n(30023),
    'δράση': i18n(30024),
    'έγκλημα': i18n(30026),
    'ρομαντική': i18n(30029),
    'κοινωνική': i18n(30038),
    'θρίλλερ': i18n(30040),
    'μυστηρίου': i18n(30041),
    'οικογενειακή': i18n(30042),
    'μιούσικαλ': i18n(30044),
    'βιογραφία': i18n(30069),
    'επιστημονικής φαντασίας': i18n(30065),
    'ιστορική': i18n(30070),
    'πολεμική': i18n(30071),
    'πολιτική': i18n(30061),
    'ερωτική': i18n(30116),
    'μυθοπλασία': i18n(30118),
    'παιδικό': i18n(30117),
    'ντοκυμαντέρ': i18n(30077),
    'περιπέτεια': i18n(30084),
    'κινουμένων σχεδίων': i18n(30087),
    'αστυνομική': i18n(30088),
    'άλλο': i18n(30089),
    'τρόμου': i18n(30132),

}

########################################################################################################################

VOD_FILTER_MAP = {
    '1': ('A', 'Α'),
    '2': ('B', 'V', 'Β'),
    '3': ('G', 'Γ'),
    '4': ('D', 'Δ'),
    '5': ('E', 'Ε'),
    '6': ('Z', 'Ζ'),
    '7': ('H', 'Η'),
    '8': 'Θ',
    '9': ('I', 'Ι'),
    '10': ('K', 'Q', 'Κ'),
    '11': ('L', 'Λ'),
    '12': ('M', 'Μ'),
    '13': ('N', 'Ν'),
    '14': ('J', 'Ξ'),
    '15': ('O', 'Ο'),
    '16': ('P', 'Π'),
    '17': ('R', 'Ρ'),
    '18': ('S', 'Σ'),
    '19': ('T', 'Τ'),
    '20': ('U', 'Y', 'Υ'),
    '21': ('F', 'Φ'),
    '22': ('X', 'Χ'),
    '23': ('C', 'Ψ'),
    '24': ('W', 'Ω'),
    '25': tuple('0123456789.')
}

VOD_YEAR_FILTER_MAP = {
    '1': range(0, 1950),
    '2': range(1950, 1960),
    '3': range(1960, 1970),
    '4': range(1970, 1980),
    '5': range(1980, 1990),
    '6': range(1990, 2000),
    '7': range(2000, 2010),
    '8': range(2010, 2020),
    '9': range(2020, datetime.now().year + 1)
}

VOD_GENRE_FILTER_MAP = {
    '1': ('κωμωδία',),
    '2': ('δράμα',),
    '3': ('δράση',),
    '4': ('κοινωνική',),
    '5': ('έγκλημα',),
    '6': ('ντοκυμαντέρ',),
    '7': ('ρομαντική',),
    '8': ('κινουμένων σχεδίων',),
    '9': ('μιούσικαλ',),
    '10': ('ιστορική',),
    '11': ('θρίλλερ',),
    '12': ('μυστηρίου',),
    '13': ('περιπέτεια',),
    '14': ('επιστημονικής φαντασίας',),
    '15': ('πολιτική',),
    '16': ('πολεμική',),
    '17': ('μυθοπλασία',),
    '18': ('ερωτική',),
    '19': ('βιογραφία',),
    '20': ('παιδικό',)
}

ALL_VOD_CHARS = {char for chars in VOD_FILTER_MAP.values() for char in chars}

########################################################################################################################

PINNED = join(dataPath, 'pinned.txt')
SEARCH_HISTORY = join(dataPath, 'search_history.csv')
PLAYBACK_HISTORY = join(dataPath, 'playback_history.list')

########################################################################################################################

CACHE_DEBUG = Addon().getSetting('do_not_use_cache') == 'true' and Addon().getSetting('debug') == 'true'
SEPARATOR = ' - ' if Addon().getSetting('wrap_labels') == '1' else '[CR]'


def cache_duration(duration):
    if CACHE_DEBUG:
        return 0
    else:
        return duration
