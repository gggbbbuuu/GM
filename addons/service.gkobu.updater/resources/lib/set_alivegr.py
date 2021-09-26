# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
from resources.lib import notify, monitor

transPath  = xbmcvfs.translatePath
logo = transPath('special://home/addons/plugin.video.AliveGR/resources/media/icon.png')

def setAliveGRSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        setaddon = xbmcaddon.Addon('plugin.video.AliveGR')
        gkobualivegrprev = setaddon.getSetting('gkobusetalivegr')
        gkobualivegrnew = '1.1'
        if gkobualivegrprev == '' or gkobualivegrprev is None:
            gkobualivegrprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.AliveGR')) and str(gkobualivegrnew) > str(gkobualivegrprev):
            if monitor.waitForAbort(0.5):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του AliveGR', t=1, image=logo)
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων AliveGR...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon = xbmcaddon.Addon('plugin.video.AliveGR')
                setaddon.setSetting('show_alt_live', 'true')
                setaddon.setSetting('show_alt_vod', 'true')
                setaddon.setSetting('sl_quality_picker', '1')
                setaddon.setSetting('yt_quality_picker', '1')
                setaddon.setSetting('gkobusetalivegr', gkobualivegrnew)
                notify.progress('H ρύθμιση του AliveGR ολοκληρώθηκε', t=1, image=logo)
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων AliveGR...', t=1, image=logo)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων AliveGR...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        notify.progress('Αδυναμία εφαρμογής ρυθμίσεων AliveGR...', t=1, image=logo)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων AliveGR...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setAliveGRSettings()

