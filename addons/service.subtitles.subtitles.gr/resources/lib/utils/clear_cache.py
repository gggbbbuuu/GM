# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from shutil import rmtree

import xbmcaddon

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath
from xbmcgui import Dialog

ADDON_ID = 'service.subtitles.subtitles.gr'


def action():

    filepath = translatePath('special://profile/addon_data/service.subtitles.subtitles.gr/cache')

    try:
        rmtree(filepath)
    except Exception:
        pass


if __name__ == '__main__':

    action()

    # RunScript(path) carries no addon id, so it must be passed explicitly
    message = xbmcaddon.Addon(ADDON_ID).getLocalizedString(30280)

    Dialog().notification('Subtitles.gr', message, time=3000, sound=False)
