# -*- coding: utf-8 -*-
import xbmc, xbmcgui, os
import main
from resources.lib import extract, addoninstall, addonlinks, set_seren, set_alivegr, set_youtube, set_gui, set_stalker, notify, monitor
from contextlib import contextmanager
updaterversion = main.addon.getAddonInfo('version')

@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def needreload():
    installedversion = main.addon.getSetting('installedver')
    if installedversion == '' or installedversion is None:
        installedversion = '0'

    if str(updaterversion) != str(installedversion):
        main.addon.setSetting('installedver', updaterversion)
        xbmc.executebuiltin('LoadProfile(Master user)')

if __name__ == '__main__':
    xbmc.executebuiltin('StopScript(%s)' % os.path.join(main.HOME, 'addons', 'script.extendedinfo'))
    xbmc.executebuiltin('StopScript(script.extendedinfo)')
    xbmc.executebuiltin('StopScript(%s)' % os.path.join(main.HOME, 'addons', 'script.extendedinfo', 'service.py'))
    if monitor.waitForAbort(5):
        sys.exit()
    query = '{"jsonrpc":"2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"script.extendedinfo","enabled":false}, "id":2}'
    response = xbmc.executeJSONRPC(query)
    if monitor.waitForAbort(1):
        sys.exit()
    with busy_dialog():
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":2}}')
        if monitor.waitForAbort(3):
            sys.exit()
        # notify.progress('Έλεγχος για ενημερωμένη έκδοση ρυθμίσεων Seren', func="setSerenSetting")
        set_seren.setSerenSettings()
        # notify.progress('Έλεγχος για ενημερωμένη έκδοση ρυθμίσεων AliveGR', func="setAliveGRSettings")
        set_alivegr.setAliveGRSettings()
        # notify.progress('Έλεγχος για ενημερωμένη έκδοση ρυθμίσεων Youtube', func="setYoutubeSettings")
        set_youtube.setYoutubeSettings()
        # notify.progress('Έλεγχος για ενημερωμένη έκδοση ρυθμίσεων GUI', func="setguiSettings")
        set_gui.setguiSettings()
        # notify.progress('Ρύθμιση του PVR Stalker', func="setpvrstalker")
        set_stalker.setpvrstalker()
        # notify.progress('Ενημέρωση συντομεύσεων κεντρικού μενού', func="skinshortcuts")
        main.skinshortcuts()
        # notify.progress('Ενημέρωση Zips', func="updatezip")
        main.updatezip()
        # notify.progress('Ενημέρωση SFxmls', func="SFxmls")
        main.SFxmls()
        # notify.progress('Removing Addons', func="addon_remover")
        main.addon_remover()
        # notify.progress('Έλεγχος λειτουργίας GKoBu repository', func="reporescue")
        main.reporescue()
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":0}}')
        query = '{"jsonrpc":"2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"script.extendedinfo","enabled":true}, "id":3}'
        response = xbmc.executeJSONRPC(query)
        if monitor.waitForAbort(1):
            sys.exit()
        xbmc.executebuiltin('UpdateAddonRepos()')
        # needreload()
    # if xbmc.getCondVisibility('Window.IsVisible(extendedprogressdialog)'):
        # xbmc.executebuiltin('Dialog.Close(extendedprogressdialog, true)')
