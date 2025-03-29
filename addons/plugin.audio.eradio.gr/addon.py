# -*- coding: utf-8 -*-

'''
    E-Radio Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


import sys
from tulip.compat import parse_qsl
from tulip.url_dispatcher import urldispatcher
# noinspection PyUnresolvedReferences
from resources.lib import eradio


def main(argv=None):

    if sys.argv: argv = sys.argv

    params = dict(parse_qsl(argv[2][1:]))
    action = params.get('action', 'root')
    urldispatcher.dispatch(action, params)


if __name__ == '__main__':

    sys.exit(main())
