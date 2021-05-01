﻿# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, _thread

KODIV = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
transPath  = xbmc.translatePath if KODIV < 19 else xbmcvfs.translatePath

def pvrstalkerinstall():
    try:
        setaddon = xbmcaddon.Addon('service.gkobu.updater')
        gkobupvrask2 = setaddon.getSetting('gkobupvrask2')
        if gkobupvrask2 == '' or gkobupvrask2 is None:
            gkobupvrask2 = 'true'
        if gkobupvrask2 == 'true':
            try:
                stalkeraddonpath = transPath('special://home/addons/pvr.stalker/addon.xml')
                if xbmc.getCondVisibility('System.HasAddon(pvr.stalker)') == False and os.path.exists(stalkeraddonpath) == False:
                    while xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
                        xbmc.sleep(100)
                    yes = xbmcgui.Dialog().yesno("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Υπάρχει διαθέσιμη (δοκιμαστικά) η επιλογή ενεργοποίησης προρυθμισμένου PVR client για την θέαση ζωντανών ροών καναλιών!!![CR]Αν σας ενδιαφέρει θα πρέπει να εγκαταστήσετε τώρα τον PVR client. Διαφορετικά επιλέξτε [B]Ακύρωση[/B].[CR]Θέλετε να εγκαταστήσετε τον [B][COLOR skyblue]PVR Stalker client[/COLOR][/B] τώρα?", nolabel='[B]Ακύρωση[/B]', yeslabel='[B]Εγκατάσταση[/B]')
                    if yes == False:
                        yes = xbmcgui.Dialog().yesno("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Θέλετε να ερωτηθείτε ξανά σε επόμενη ενημέρωση για την εγκατάσταση του PVR client?", nolabel='[B]Ναι, ξαναρώτησε[/B]', yeslabel='[B]Ποτέ ξανά[/B]')
                        if not yes == False:
                            setaddon.setSetting('gkobupvrask2', 'false')
                            return False
                        else:
                            return False
                    else:
                        xbmc.executebuiltin('InstallAddon(pvr.stalker)')
                        while xbmc.getCondVisibility('System.HasAddon(pvr.stalker)') == False:
                            xbmc.sleep(1000)
                        return True
                else:
                    return True
            except BaseException:
                return True
        else:
            return False
    except BaseException:
        return False

def setpvrstalker():
    if pvrstalkerinstall():
        try:
            setaddon = xbmcaddon.Addon('pvr.stalker')
            gkobupvrgenprev = setaddon.getSetting('gkobupvrstalgen')
            gkobupvrgennew = '1.4'
            if gkobupvrgenprev == '' or gkobupvrgenprev is None:
                gkobupvrgenprev = '0'
            gkobupvrsetprev = setaddon.getSetting('gkobupvrstalset')
            gkobupvrsetnew = '4.5'
            if gkobupvrsetprev == '' or gkobupvrsetprev is None:
                gkobupvrsetprev = '0'
            if str(gkobupvrgennew) > str(gkobupvrgenprev):
                genlist = [['time_zone_0', 'Europe/London'], ['time_zone_1', 'Europe/London'], ['time_zone_2', 'Europe/London'], ['time_zone_3', 'Europe/London'],
                            ['time_zone_4', 'Europe/London'], ['time_zone_5', 'Europe/London'], ['time_zone_6', 'Europe/London'], ['time_zone_7', 'Europe/London'],
                            ['time_zone_8', 'Europe/London'], ['time_zone_9', 'Europe/London'],
                            ['guide_preference_0', '1'], ['guide_preference_1', '1'], ['guide_preference_2', '1'], ['guide_preference_3', '1'],
                            ['guide_preference_5', '1'], ['guide_preference_6', '1'], ['guide_preference_7', '1'], ['guide_preference_8', '1'], ['guide_preference_9', '1'],
                            ['guide_cache_0', 'true'], ['guide_cache_1', 'true'], ['guide_cache_2', 'true'], ['guide_cache_3', 'true'],
                            ['guide_cache_5', 'true'], ['guide_cache_6', 'true'], ['guide_cache_7', 'true'], ['guide_cache_8', 'true'], ['guide_cache_9', 'true'],
                            ['xmltv_url_0', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'], ['xmltv_url_1', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'], ['xmltv_url_2', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'],
                            ['xmltv_url_3', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'], ['xmltv_url_5', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'],
                            ['xmltv_url_6', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'], ['xmltv_url_7', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'], ['xmltv_url_8', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'],
                            ['xmltv_url_9', 'https://github.com/GreekTVApp/epg-greece-cyprus/releases/download/EPG/epg.xml.gz'], ['gkobupvrstalgen', gkobupvrgennew]]
                try:
                    xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή γενικών ρυθμίσεων PVR Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                    for genitem in genlist:
                        genid = genitem[0]
                        genvalue = genitem[1]
                        prevgenvalue = setaddon.getSetting(genid)
                        if genvalue != prevgenvalue:
                            _thread.start_new_thread(OKdialogClick, ())
                            xbmc.sleep(200)
                            setaddon.setSetting(genid, genvalue)
                except BaseException:
                    pass

            if str(gkobupvrsetnew) > str(gkobupvrsetprev):
                setlist = [['mac_0', '00:1A:79:4E:78:B6'], ['server_0', 'http://mytv.fun:8080/c/'], ['mac_1', '00:1a:79:44:ac:7e'], ['server_1', 'http://rocksat.ddns.net:25461/c/'],
                            ['mac_2', '00:1A:79:C8:72:CC'], ['server_2', 'http://portal.unblkservice2.xyz:8080/c/'], ['mac_3', '00:1a:79:09:DF:F8'], ['server_3', 'http://satfrog-tv.ddns.net:5890/c/'],
                            ['mac_5', '00:1A:79:19:E7:19'], ['server_5', 'http://unityone.ddns.net:9090/c/'], ['mac_6', '00:1a:79:3b:2d:49'], ['server_6', 'http://ccs2.coolmyvip.club:8880/c/'],
                            ['mac_7', '00:1A:79:18:25:F9'], ['server_7', 'http://admin-mainpanel.club:8080/c/'], ['mac_8', '00:1A:79:37:E1:05'], ['server_8', 'http://mainsee.sltv.shop:8080/c/'],
                            ['mac_9', '00:1A:79:58:26:78'], ['server_9', 'http://vip.vprotv.com:25443/c/'], ['gkobupvrstalset', gkobupvrsetnew]]
                try:
                    xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων PVR Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                    for setitem in setlist:
                        setid = setitem[0]
                        setvalue = setitem[1]
                        prevsetvalue = setaddon.getSetting(setid)
                        if setvalue != prevsetvalue:
                            _thread.start_new_thread(OKdialogClick, ())
                            xbmc.sleep(200)
                            setaddon.setSetting(setid, setvalue)
                    xbmcgui.Dialog().ok("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Οι ρυθμίσεις του PVR Client ενημερώθηκαν. [CR]Για να φορτωθεί η ενημερωμένη λίστα καναλιών, θυμηθείτε να επανεκκινήσετε το Kodi.")
                    return
                except BaseException:
                    xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                    return
            else:
                return
        except BaseException:
            xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
            return
        return True
    else:
        return False


def OKdialogClick():
    x = 0
    while not xbmc.getCondVisibility("Window.isActive(okdialog)") and x < 100:
        x += 1
        xbmc.sleep(100)
    
    if xbmc.getCondVisibility("Window.isActive(okdialog)"):
        xbmc.executebuiltin('SendClick(11)')


if __name__ == '__main__':
    setpvrstalker()
