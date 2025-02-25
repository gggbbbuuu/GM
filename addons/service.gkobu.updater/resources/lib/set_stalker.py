# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys, json
from resources.lib.addoninstall import latestDB, DATABASE
from resources.lib import notify, monitor
import main
try:    from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

transPath  = xbmcvfs.translatePath
epgdb = os.path.join(DATABASE, latestDB('Epg'))
tvdb = os.path.join(DATABASE, latestDB('TV'))
logo = transPath('special://home/addons/pvr.stalker/icon.png')
def pvrstalkerinstall():
    try:
        setaddon = main.addon
        gkobupvrask2 = setaddon.getSetting('gkobupvrask2')
        if gkobupvrask2 == '' or gkobupvrask2 is None:
            gkobupvrask2 = 'true'
        if gkobupvrask2 == 'true':
            try:
                stalkeraddonpath = transPath('special://home/addons/pvr.stalker/addon.xml')
                if xbmc.getCondVisibility('System.HasAddon(pvr.stalker)') == False and os.path.exists(stalkeraddonpath) == False:
                    while xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
                        if monitor.waitForAbort(0.1):
                            sys.exit()
                    yes = xbmcgui.Dialog().yesno("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Υπάρχει διαθέσιμη (δοκιμαστικά) η επιλογή ενεργοποίησης προρυθμισμένου PVR client για την θέαση ζωντανών ροών καναλιών!!![CR]Αν σας ενδιαφέρει θα πρέπει να εγκαταστήσετε τώρα τον PVR client. Διαφορετικά επιλέξτε [B]Ακύρωση[/B].[CR]Θέλετε να εγκαταστήσετε τον [B][COLOR skyblue]PVR Stalker client[/COLOR][/B] τώρα?", nolabel='[B]Ακύρωση[/B]', yeslabel='[B]Εγκατάσταση[/B]')
                    if yes == False:
                        yes = xbmcgui.Dialog().yesno("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Θέλετε να ερωτηθείτε ξανά σε επόμενη ενημέρωση για την εγκατάσταση του PVR client?", nolabel='[B]Ναι, ξαναρώτησε[/B]', yeslabel='[B]Ποτέ ξανά[/B]')
                        if not yes == False:
                            setaddon.setSetting('gkobupvrask2', 'false')
                            notify.progress('Δεν θα ξαναερωτηθείτε...', t=1)
                            return False
                        else:
                            notify.progress('Την επόμενη φορά λοιπόν!!', t=1)
                            return False
                    else:
                        notify.progress('Ξεκινάει η εγκατάσταση του PVR Stalker', t=1, image=logo)
                        xbmc.executebuiltin('InstallAddon(pvr.stalker)')
                        xbmc.executebuiltin('SendClick(11)')
                        x = 0
                        while xbmc.getCondVisibility('System.HasAddon(pvr.stalker)') == False and x < 60:
                            x += 1
                            if monitor.waitForAbort(1):
                                sys.exit()
                        if xbmc.getCondVisibility('System.HasAddon(pvr.stalker)'):
                            notify.progress('Το PVR Stalker εγκαταστάθηκε', t=1, image=logo)
                            return True
                        else:
                            return False
                else:
                    return True
            except BaseException:
                return False
        else:
            return False
    except BaseException:
        return False

def setpvrstalker():
    if pvrstalkerinstall():
        enablestalker()
        try:
            setaddon = xbmcaddon.Addon('pvr.stalker')
            gkobupvrgenprev = setaddon.getSetting('gkobupvrstalgen')
            gkobupvrgennew = '1.4'
            if gkobupvrgenprev == '' or gkobupvrgenprev is None:
                gkobupvrgenprev = '0'
            gkobupvrsetprev = setaddon.getSetting('gkobupvrstalset')
            gkobupvrsetnew = '4.9'
            if gkobupvrsetprev == '' or gkobupvrsetprev is None:
                gkobupvrsetprev = '0'
            changes = []
            if str(gkobupvrsetnew) > str(gkobupvrsetprev):
                    notify.progress('Ξεκινάει η ρύθμιση του PVR Stalker', t=1, image=logo)
                    setlist = [ ['mac_0', '00:1A:79:07:1A:C4'], ['server_0', 'http://hd-max.org:8080/c/'], ['mac_1', '00:1A:79:8C:2A:39'], ['server_1', 'http://mytv.fun:8080/c/'],
                                ['mac_2', '00:1a:79:5f:d5:fd'], ['server_2', 'http://iptvking.123tv.to:8080/c/'], ['mac_3', '00:1A:79:48:55:29'], ['server_3', 'http://clientportal-proiptv.club:8080/c/'],
                                ['mac_5', '00:1A:79:19:E7:19'], ['server_5', 'http://unityone.ddns.net:9090/c/'], ['mac_6', '00:1a:79:3b:2d:49'], ['server_6', 'http://ccs2.coolmyvip.club:8880/c/'],
                                ['mac_7', '00:1A:79:E2:9F:17'], ['server_7', 'http://powerip.be:8000/c/'], ['mac_8', '00:1A:79:53:C7:B9'], ['server_8', 'http://mainsee.sltv.shop:8080/c/'],
                                ['mac_9', '00:1A:79:58:26:78'], ['server_9', 'http://vip.vprotv.com:25443/c/'], ['gkobupvrstalset', gkobupvrsetnew]]
                    if dissablestalker():
                        notify.progress('Εφαρμογή ρυθμίσεων PVR Stalker...', t=1, image=logo)
                        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων PVR Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                        for setitem in setlist:
                            if monitor.waitForAbort(0.1):
                                sys.exit()
                            setid = setitem[0]
                            setvalue = setitem[1]
                            prevsetvalue = setaddon.getSetting(setid)
                            if setvalue != prevsetvalue:
                                setaddon.setSetting(setid, setvalue)
                                changes.append(setitem)
                    else:
                        notify.progress('Αδυναμία ρύθμισης Πύλης-MAC στον Stalker...', t=1, image=logo)
                        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία ρύθμισης Πύλης-MAC στον Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)

            if str(gkobupvrgennew) > str(gkobupvrgenprev):
                    genlist = [['time_zone_0', 'Europe/London'], ['time_zone_1', 'Europe/London'], ['time_zone_2', 'Europe/London'], ['time_zone_3', 'Europe/London'],
                                ['time_zone_4', 'Europe/London'], ['time_zone_5', 'Europe/London'], ['time_zone_6', 'Europe/London'], ['time_zone_7', 'Europe/London'],
                                ['time_zone_8', 'Europe/London'], ['time_zone_9', 'Europe/London'], ['gkobupvrstalgen', gkobupvrgennew]]
                    if dissablestalker():
                        notify.progress('Εφαρμογή γενικών ρυθμίσεων PVR Stalker...', t=1, image=logo)
                        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή γενικών ρυθμίσεων PVR Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                        for genitem in genlist:
                            genid = genitem[0]
                            genvalue = genitem[1]
                            prevgenvalue = setaddon.getSetting(genid)
                            if genvalue != prevgenvalue:
                                setaddon.setSetting(genid, genvalue)
                                changes.append(genitem)
                    else:
                        notify.progress('Αδυναμία εφαρμογής γενικών ρυθμίσεων Stalker...', t=1, image=logo)
                        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής γενικών ρυθμίσεων Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
            if len(changes) > 0:
                purgeDb(epgdb)
                purgeDb(tvdb)
                enablestalker()
                xbmcgui.Dialog().ok("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "%s ρυθμίσεις του PVR Client ενημερώθηκαν." % str(len(changes)))
                restartstalker()
                return True
            else:
                enablestalker()
                return 
        except BaseException:
            notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Stalker...', t=1, image=logo)
            # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
            return
    else:
        return True


def OKdialogClick():
    x = 0
    while not xbmc.getCondVisibility("Window.isActive(okdialog)") and x < 100:
        x += 1
        xbmc.sleep(100)
    
    if xbmc.getCondVisibility("Window.isActive(okdialog)"):
        xbmc.executebuiltin('SendClick(11)')

def dissablestalker():
    if isenabled('pvr.stalker') == True:
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid": "pvr.stalker","enabled":false}}')
        x = 0
        xbmc.sleep(1000)
        while isenabled('pvr.stalker') == True and x < 10:
            x += 1
            if monitor.waitForAbort(1):
                sys.exit()
        if isenabled('pvr.stalker') == False:
            return True
        else:
            return False
    else:
        return True

def enablestalker():
    if isenabled('pvr.stalker') == False:
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid": "pvr.stalker","enabled":true}}')
        x = 0
        xbmc.sleep(1000)
        while isenabled('pvr.stalker') == False and x < 10:
            x += 1
            if monitor.waitForAbort(1):
                sys.exit()
        if isenabled('pvr.stalker') == True:
            return True
        else:
            return False
    else:
        return True

def restartstalker():
    try:
        notify.progress('Επανεκκίνηση PVR Stalker...', t=1, image=logo)
        # xbmcgui.Dialog().notification("GKoBu", "Επανεκκίνηση PVR Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        # xbmc.executebuiltin('EnableAddon("pvr.stalker")')
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":7,"params":{"addonid": "pvr.stalker","enabled":false}}')
        xbmc.sleep(1000)
        x = 0
        while isenabled('pvr.stalker') == True and x < 10:
            x += 1
            xbmc.sleep(1000)
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":6,"params":{"addonid": "pvr.stalker","enabled":true}}')
        xbmc.sleep(1000)
        x = 0
        while isenabled('pvr.stalker') == False and x < 10:
            x += 1
            xbmc.sleep(1000)
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":7,"params":{"addonid": "pvr.stalker","enabled":false}}')
        xbmc.sleep(1000)
        x = 0
        while isenabled('pvr.stalker') == True and x < 10:
            x += 1
            xbmc.sleep(1000)
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":6,"params":{"addonid": "pvr.stalker","enabled":true}}')
        xbmc.sleep(1000)
        x = 0
        while isenabled('pvr.stalker') == False and x < 10:
            x += 1
            xbmc.sleep(1000)
        notify.progress('PVR Stalker επανεκκινήθηκε', t=1, image=logo)
        # xbmcgui.Dialog().notification("GKoBu", "PVR Stalker επανεκκινήθηκε", xbmcgui.NOTIFICATION_INFO, 3000, False)
    except:
        notify.progress('Αδυναμία επανεκκίνησης...', t=1, image=logo)
        # xbmcgui.Dialog().notification("GKoBu", "Αδυναμία επανεκκίνησης...", xbmcgui.NOTIFICATION_INFO, 3000, False)


def isenabled(addonid):
    query = '{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails", "params": { "addonid": "%s", "properties" : ["name", "thumbnail", "fanart", "enabled", "installed", "path", "dependencies"] } }' % addonid
    addonDetails = xbmc.executeJSONRPC(query)
    details_result = json.loads(addonDetails)
    if "error" in details_result:
        return False
    elif details_result['result']['addon']['enabled'] == True:
        return True
    else:
        return False

def purgeDb(name):
    # log('Purging DB %s.' % name, lognot)
    if os.path.exists(name):
        try:
            textdb = database.connect(name)
            textexe = textdb.cursor()
        except Exception as e:
            # log("DB Connection Error: %s" % str(e), xbmc.LOGERROR)
            return False
    else:
        # log('%s not found.' % name, xbmc.LOGERROR)
        return False
    textexe.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    for table in textexe.fetchall():
        if table[0] == 'version':
            # log('Data from table `%s` skipped.' % table[0], xbmc.LOGDEBUG)
            continue
        try:
            textexe.execute("DELETE FROM %s" % table[0])
            textdb.commit()
            # log('Data from table `%s` cleared.' % table[0], xbmc.LOGDEBUG)
        except Exception:
            # log("DB Remove Table `%s` Error: %s" % (table[0], str(e)), xbmc.LOGERROR)
            pass
    textexe.close()
    # log('%s DB Purging Complete.' % name, lognot)
    show = name.replace('\\', '/').split('/')
    notify.progress('Καθαρισμός %s ολοκληρώθηκε' % show[-1], t=1, image=logo)
    # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Καθαρισμός %s ολοκληρώθηκε" % show[-1], xbmcgui.NOTIFICATION_INFO, 3000, False)

if __name__ == '__main__':
    setpvrstalker()

