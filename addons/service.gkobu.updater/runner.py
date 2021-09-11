# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import main
from resources.lib import extract, addoninstall, addonlinks, set_seren, set_alivegr, set_youtube, set_gui, set_stalker
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
    with busy_dialog():
        set_seren.setSerenSettings()
        set_alivegr.setAliveGRSettings()
        set_youtube.setYoutubeSettings()
        set_gui.setguiSettings()
        set_stalker.setpvrstalker()
        main.skinshortcuts()
        main.updatezip()
        main.SFxmls()
        main.addon_remover()
        main.reporescue()
        needreload()
    if xbmc.getCondVisibility('Window.IsVisible(extendedprogressdialog)'):
        xbmc.executebuiltin('Dialog.Close(extendedprogressdialog, true)')
