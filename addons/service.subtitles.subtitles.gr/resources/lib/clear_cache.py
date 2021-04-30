# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from shutil import rmtree
from xbmc import translatePath
from xbmcgui import Dialog


def action():

    filepath = translatePath('special://profile/addon_data/service.subtitles.subtitles.gr/cache')

    try:
        rmtree(filepath)
    except Exception:
        pass


if __name__ == '__main__':

    action()

    Dialog().notification('Subtitles.gr', 'OK', time=2, sound=False)
