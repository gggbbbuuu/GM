# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Deletes saved subtitles chosen in a multiselect dialog.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import os

import xbmcaddon
import xbmcgui

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

ADDON_ID = 'service.subtitles.subtitles.gr'


def action():

    addon = xbmcaddon.Addon(ADDON_ID)
    folder = addon.getSetting('output_folder')

    if folder.startswith('special://'):
        folder = translatePath(folder)

    try:
        files = sorted(
            f for f in os.listdir(folder)
            if f.lower().endswith(('.srt', '.sub'))
        )
    except Exception:
        files = []

    dialog = xbmcgui.Dialog()

    if not files:
        dialog.notification(
            'Subtitles.gr', addon.getLocalizedString(30322),
            time=3000, sound=False
        )
        return

    picked = dialog.multiselect(addon.getLocalizedString(30320), files)

    if not picked:
        return

    deleted = 0

    for index in picked:
        try:
            os.remove(os.path.join(folder, files[index]))
            deleted += 1
        except Exception:
            continue

    dialog.notification(
        'Subtitles.gr', addon.getLocalizedString(30321).replace('%d', str(deleted)),
        time=3000, sound=False
    )


if __name__ == '__main__':

    action()
