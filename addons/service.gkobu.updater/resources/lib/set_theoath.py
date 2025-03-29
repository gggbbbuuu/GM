# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
from resources.lib import notify, monitor

transPath  = xbmcvfs.translatePath
logo = transPath('special://home/addons/plugin.video.theoath/icon.png')

def setTheOathSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        setaddon = xbmcaddon.Addon('plugin.video.theoath')
        logo = setaddon.getAddonInfo('icon')
        gkobutheoathprev = setaddon.getSetting('gkobusettheoath')
        gkobutheoathnew = '1.2'
        if gkobutheoathprev == '' or gkobutheoathprev is None:
            gkobutheoathprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.theoath')) and str(gkobutheoathnew) > str(gkobutheoathprev):
            if monitor.waitForAbort(0.5):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του TheOath', t=1, image=logo)
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων TheOath...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon.setSetting('tm.user', 'ab56201f58598d30890a785c7683c28a')
                xbmcaddon.Addon('script.module.oathscrapers').setSetting('url.myvideolink', 'https://new.myvideolinks.net/')
                setaddon.setSetting('gkobusettheoath', gkobutheoathnew)
                notify.progress('H ρύθμιση του TheOath ολοκληρώθηκε', t=1, image=logo)
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων TheOath...', t=1, image=logo)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων TheOath...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        # notify.progress('Αδυναμία εφαρμογής ρυθμίσεων TheOath...', t=1, image=logo)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων TheOath...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setTheOathSettings()

