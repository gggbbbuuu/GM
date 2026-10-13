# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Program entry point: opens the addon settings dialog directly.
'''

from xbmc import executebuiltin
ADDON_ID = 'script.module.resolveurl.pluginsgr'
executebuiltin('Addon.OpenSettings({0})'.format(ADDON_ID))
