# -*- coding: utf-8 -*-

'''
    Soma FM Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import sys
from tulip.compat import parse_qsl
from tulip.control import refresh
from tulip.cache import FunctionCache
from resources.lib.indexers import radios
from resources.lib.modules.player import player
from resources.lib.modules import info

syshandle = int(sys.argv[1])
sysaddon = sys.argv[0]
params = dict(parse_qsl(sys.argv[2].replace('?','')))

########################################################################################################################

action = params.get('action')
url = params.get('url')
image = params.get('image')
name = params.get('name')
title = params.get('title')
text = params.get('text')

########################################################################################################################

if action is None:

    radios.Indexer().stations()

########################################################################################################################

elif action == 'play':

    player(url)

elif action == 'description':

    info.description(text)

elif action == 'history':

    info.history(url)

elif action == 'info_cm':

    info.info_cm()

elif action == 'cache_clear':

    FunctionCache().reset_cache(notify=True)

elif action == 'refresh':

    refresh()
