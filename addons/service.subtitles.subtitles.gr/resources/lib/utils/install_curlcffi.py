# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Installs and enables script.module.curlcffi, which the Subs4Series
    provider needs for browser TLS impersonation.

    Uses Kodi's built-in installer plus the Addons.SetAddonEnabled JSON-RPC,
    since InstallAddon leaves a previously disabled addon disabled and
    System.HasAddon reports true for disabled addons, so it cannot be used
    to tell "installed" from "usable".

    Dependency paths are resolved when Kodi starts, so a freshly installed
    module only becomes importable after a restart. This script therefore
    verifies state and reports honestly instead of claiming success early.

    Deliberately avoids tulip: it calls xbmcaddon.Addon() at import time,
    which fails under RunScript(path).

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json

import xbmc
import xbmcaddon
import xbmcgui

ADDON_ID = 'script.module.curlcffi'
SELF_ID = 'service.subtitles.subtitles.gr'


def rpc(method, params=None):

    command = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params if params is not None else {},
        'id': 1,
    }

    try:
        response = xbmc.executeJSONRPC(json.dumps(command))
    except Exception:
        return None

    try:
        result = json.loads(response).get('result')
    except Exception:
        return None

    return result


def details():

    '''Returns {enabled, version} or None when the addon is absent.'''

    for props in (['enabled', 'version'], ['addonid', 'enabled', 'version'], None):

        try:
            result = rpc('Addons.GetAddonDetails', {'addonid': ADDON_ID, 'properties': props})
        except Exception:
            result = None

        if isinstance(result, dict) and result.get('addon'):
            addon = result['addon']
            return {
                'enabled': bool(addon.get('enabled')),
                'version': addon.get('version', 'unknown'),
            }

    return None


def set_enabled(enabled=True):

    return rpc('Addons.SetAddonEnabled', {'addonid': ADDON_ID, 'enabled': enabled})


def importable():

    try:
        from resources.lib.utils import impersonate

        return impersonate.AVAILABLE
    except Exception:
        return False


def lang(string_id):

    # RunScript(path) carries no addon id, so it must be passed explicitly
    return xbmcaddon.Addon(SELF_ID).getLocalizedString(string_id)


if __name__ == '__main__':

    dialog = xbmcgui.Dialog()

    state = details()

    if state and state['enabled'] and importable():
        dialog.notification('Subtitles.gr', lang(30277), time=3000, sound=False)
        raise SystemExit

    if state and not state['enabled']:
        question = lang(30276) % (ADDON_ID, state['version'])
    else:
        question = lang(30271) % ADDON_ID

    if not dialog.yesno('Subtitles.gr', question):
        raise SystemExit

    if not state:
        xbmc.executebuiltin('InstallAddon({0})'.format(ADDON_ID))

        for _ in range(15):

            if details():
                break

            xbmc.sleep(1000)

        state = details()

    if not state:
        dialog.ok('Subtitles.gr', lang(30272) % ADDON_ID)
        raise SystemExit

    if not state['enabled']:
        set_enabled(True)

        for _ in range(10):

            state = details()

            if state and state['enabled']:
                break

            xbmc.sleep(500)

    if state and state['enabled']:
        dialog.notification('Subtitles.gr', lang(30273), time=5000, sound=False)
    else:
        dialog.ok('Subtitles.gr', lang(30274) % ADDON_ID)