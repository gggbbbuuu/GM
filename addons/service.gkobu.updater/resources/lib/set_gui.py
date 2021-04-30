# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs

KODIV = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
transPath  = xbmc.translatePath if KODIV < 19 else xbmcvfs.translatePath

def setguiSettings():
    try:
        setaddon = xbmcaddon.Addon('service.gkobu.updater')
        gkobuguisetprev = setaddon.getSetting('gkobusetguiset')
        gkobuguisetnew = '1.3'
        if gkobuguisetprev == '' or gkobuguisetprev is None:
            gkobuguisetprev = '0'
        if str(gkobuguisetnew) > str(gkobuguisetprev):
            try:
                xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Ενημέρωση ρυθμίσεων....", xbmcgui.NOTIFICATION_INFO, 3000, False)
                xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"pvrplayback.switchtofullscreenchanneltypes","value":0}}')
                xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"locale.audiolanguage","value":"English"}}')
                if xbmc.getCondVisibility('System.HasAddon(service.coreelec.settings)') or xbmc.getCondVisibility('System.HasAddon(service.libreelec.settings)'):
                    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"locale.timezone","value":"Europe/Athens"}}')
                    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"locale.timezonecountry","value":"Greece"}}')
                setaddon.setSetting('gkobusetguiset', gkobuguisetnew)
                return
            except BaseException:
                xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Συστήματος...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Συστήματος...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setguiSettings()

