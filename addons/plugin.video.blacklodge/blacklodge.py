# -*- coding: utf-8 -*-

'''
    Blacklodge Add-on
'''

import sys
from resources.lib.modules import router

router.routing(sys.argv[2])
if router.external():
    sys.exit(1)
