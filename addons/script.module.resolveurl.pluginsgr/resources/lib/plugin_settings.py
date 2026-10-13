# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Per-plugin enable/disable backed by this addon's own settings
    (resources/settings.xml, <ClassName>_enabled booleans), plus generic
    read helpers for resolver-specific options.

    Note this deliberately bypasses ResolveURL's base _is_enabled: that
    one reads the *calling* addon's settings (no addon id), which is the
    wrong settings manager for resolvers invoked from other addons.
'''

try:
    import xbmcaddon
except ImportError:
    xbmcaddon = None

ADDON_ID = 'script.module.resolveurl.pluginsgr'


def plugin_enabled(name, default=True):
    '''True unless the user explicitly toggled this plugin off (or on).

    Missing/unreadable settings fall back to `default`, so fresh installs
    behave exactly like before.
    '''
    if xbmcaddon is None:
        return default
    try:
        value = xbmcaddon.Addon(ADDON_ID).getSetting(name + '_enabled')
    except Exception:
        return default
    if value == 'true':
        return True
    if value == 'false':
        return False
    return default


def get_setting(key, default=''):
    '''Raw string setting, or `default` when unset/unreadable.

    Every setting read here must also exist in resources/settings.xml;
    an undeclared id silently reads as '' forever.
    '''
    if xbmcaddon is None:
        return default
    try:
        value = xbmcaddon.Addon(ADDON_ID).getSetting(key)
    except Exception:
        return default
    return value or default


def get_bool(key, default=False):
    '''Boolean setting, honouring Kodi's 'true'/'false' string encoding.'''
    value = get_setting(key, '').strip().lower()
    if value in ('true', '1'):
        return True
    if value in ('false', '0'):
        return False
    return default
