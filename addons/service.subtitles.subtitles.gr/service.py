# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import sys
from resources.lib.addon import Search, Download
from tulip.compat import parse_qsl

syshandle = int(sys.argv[1])
sysaddon = sys.argv[0]
params = dict(parse_qsl(sys.argv[2][1:]))

action = params.get('action')
source = params.get('source')
url = params.get('url')
query = params.get('searchstring')
langs = params.get('languages')

########################################################################################################################

if action in [None, 'search', 'manualsearch']:
    Search(syshandle, sysaddon, langs, action).run(query)

elif action == 'download':
    Download(syshandle, sysaddon).run(url, source)

########################################################################################################################
