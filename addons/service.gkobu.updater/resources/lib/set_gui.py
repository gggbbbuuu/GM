# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, sys
from resources.lib import notify, monitor
import main

def setguiSettings():
    try:
        setaddon = main.addon
        gkobuguisetprev = setaddon.getSetting('gkobusetguiset')
        gkobuguisetnew = '1.3'
        if gkobuguisetprev == '' or gkobuguisetprev is None:
            gkobuguisetprev = '0'
        if str(gkobuguisetnew) > str(gkobuguisetprev):
            if monitor.waitForAbort(0.5):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του GUI', t=1)
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Ενημέρωση ρυθμίσεων....", xbmcgui.NOTIFICATION_INFO, 3000, False)
                xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"pvrplayback.switchtofullscreenchanneltypes","value":0}}')
                xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"locale.audiolanguage","value":"English"}}')
                if xbmc.getCondVisibility('System.HasAddon(service.coreelec.settings)') or xbmc.getCondVisibility('System.HasAddon(service.libreelec.settings)'):
                    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"locale.timezone","value":"Europe/Athens"}}')
                    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"locale.timezonecountry","value":"Greece"}}')
                setaddon.setSetting('gkobusetguiset', gkobuguisetnew)
                notify.progress('H ρύθμιση του GUI ολοκληρώθηκε', t=1)
                return
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Συστήματος...', t=1)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Συστήματος...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Συστήματος...', t=1)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Συστήματος...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setguiSettings()

