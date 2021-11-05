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
    # if monitor.waitForAbort(3):
        # sys.exit()
    # xbmc.executebuiltin('StopScript(%s)' % os.path.join(main.HOME, 'addons', 'script.extendedinfo'))
    # xbmc.executebuiltin('StopScript(script.extendedinfo)')
    # xbmc.executebuiltin('StopScript(%s)' % os.path.join(main.HOME, 'addons', 'script.extendedinfo', 'service.py'))
    # if monitor.waitForAbort(5):
        # sys.exit()
    with busy_dialog():
        set_seren.setSerenSettings()
    with busy_dialog():
        set_alivegr.setAliveGRSettings()
    with busy_dialog():
        set_youtube.setYoutubeSettings()
    with busy_dialog():
        set_gui.setguiSettings()
    with busy_dialog():
        set_stalker.setpvrstalker()
    with busy_dialog():
        main.skinshortcuts()
    with busy_dialog():
        main.updatezip()
    with busy_dialog():
        main.SFxmls()
    with busy_dialog():
        main.addon_remover()
    with busy_dialog():
        main.reporescue()
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":0}}')
        if monitor.waitForAbort(1):
            sys.exit()
        xbmc.executebuiltin('UpdateAddonRepos()')
        # needreload()
    # if xbmc.getCondVisibility('Window.IsVisible(extendedprogressdialog)'):
        # xbmc.executebuiltin('Dialog.Close(extendedprogressdialog, true)')
