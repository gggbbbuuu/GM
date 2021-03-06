# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, os, json
import main
from resources.lib import set_fen, set_theoath, set_tmdbhelper, set_subsgr, set_seren, set_alivegr, set_youtube, set_gui, set_stalker, monitor, addonupdatesprog, stopservices
from contextlib import contextmanager
from datetime import date, datetime, timedelta

addon = main.addon
lasttimecheck = addon.getSetting('lasttimecheck')
latest_version = addon.getAddonInfo('version')
serviceversion = addon.getSetting('service_ver')
if lasttimecheck == '' or lasttimecheck is None:
    lasttimecheck = '2000-01-01 12:00:00.000000'
if serviceversion == '' or serviceversion is None:
    serviceversion = '0.0.0'

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
    if datetime.now() - timechecked > timedelta(minutes=age) or serviceversion != latest_version:
        # with busy_dialog():
            # set_theoath.setTheOathSettings()
        with busy_dialog():
            set_fen.setFenSettings()
        with busy_dialog():
            set_tmdbhelper.setTMDBhSettings()
        with busy_dialog():
            set_subsgr.setSubsGRSettings()
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
            update_toggle = '{"jsonrpc":"2.0", "method":"Settings.GetSettingValue","params":{"setting":"general.addonupdates"}, "id":1}'
            resp_toggle = xbmc.executeJSONRPC(update_toggle)
            toggle = json.loads(resp_toggle)
            if toggle['result']['value'] != 0:
                xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":0}}')
            if monitor.waitForAbort(1):
                sys.exit()
        addon.setSetting('service_ver', latest_version)
        if main.addon.getSetting('addon.updates.monitor') == 'true':
            xbmc.executebuiltin('RunScript("special://home/addons/service.gkobu.updater/resources/lib/addonupdatesprog.py")')
            # with busy_dialog():
                # addonupdatesprog.progress()
        else:
            xbmc.executebuiltin('UpdateAddonRepos()')
    else:
        update_toggle = '{"jsonrpc":"2.0", "method":"Settings.GetSettingValue","params":{"setting":"general.addonupdates"}, "id":1}'
        resp_toggle = xbmc.executeJSONRPC(update_toggle)
        toggle = json.loads(resp_toggle)
        if toggle['result']['value'] != 0:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":0}}')
        if monitor.waitForAbort(1):
            sys.exit()
        xbmc.executebuiltin('UpdateAddonRepos()')
    if len(servicelisttostop) > 0:
        if monitor.waitForAbort(10):
            sys.exit()
        with busy_dialog():
            stopservices.StopAllRunning(servicelisttostop)
