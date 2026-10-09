# -*- coding: utf-8 -*-

'''
    E-Radio Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from sys import argv
from urllib.parse import parse_qsl

from urldispatcher import urldispatcher

from resources.lib import eradio  # noqa: F401


def main(argv=argv):

    params = dict(parse_qsl(argv[2][1:]))
    urldispatcher.dispatch(params.get('action') or 'root', params)


if __name__ == '__main__':

    main()
