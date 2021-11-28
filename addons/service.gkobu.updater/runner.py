# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, os
import main
from resources.lib import set_seren, set_alivegr, set_youtube, set_gui, set_stalker, monitor, addonupdatesprog, stopservices
from contextlib import contextmanager
from datetime import date, datetime, timedelta

addon = main.addon
lasttimecheck = addon.getSetting('lasttimecheck')
if lasttimecheck == '' or lasttimecheck is None:
    lasttimecheck = '2000-01-01 12:00:00.000000'

age = int(float(addon.getSetting('mininsleep')))
servicelisttostop = []

@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')



if __name__ == '__main__':
    while xbmc.getCondVisibility("Window.isVisible(yesnodialog)") or xbmc.getCondVisibility("Window.isVisible(okdialog)"):
        if monitor.waitForAbort(3):
            sys.exit()
    xbmc.executebuiltin('Dialog.Close(all,true)')
    xbmc.executebuiltin('ActivateWindow(10000)')
    try:
        timechecked = datetime.strptime(lasttimecheck, '%Y-%m-%d %H:%M:%S.%f')
    except:
        import time
        timechecked = datetime(*(time.strptime(lasttimecheck, '%Y-%m-%d %H:%M:%S.%f')[0:6]))
    if datetime.now() - timechecked > timedelta(minutes=age):
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
            main.reporescue()
            addon.setSetting('lasttimecheck', str(datetime.now()))
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":0}}')
            if monitor.waitForAbort(1):
                sys.exit()
        if main.addon.getSetting('addon.updates.monitor') == 'true':
            with busy_dialog():
                addonupdatesprog.progress()
        else:
            xbmc.executebuiltin('UpdateAddonRepos()')
    else:
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":0}}')
        if monitor.waitForAbort(1):
            sys.exit()
        xbmc.executebuiltin('UpdateAddonRepos()')
    if len(servicelisttostop) > 0:
        if monitor.waitForAbort(10):
            sys.exit()
        with busy_dialog():
            stopservices.StopAllRunning(servicelisttostop)
