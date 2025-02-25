# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
from resources.lib import notify, monitor

transPath  = xbmcvfs.translatePath
logo = transPath('special://home/addons/service.subtitles.subtitles.gr/icon.png')

def setSubsGRSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        setaddon = xbmcaddon.Addon('service.subtitles.subtitles.gr')
        logo = setaddon.getAddonInfo('icon')
        gkobusubsgrprev = setaddon.getSetting('gkobusetsubssgr')
        gkobusubsgrnew = '1.0'
        if gkobusubsgrprev == '' or gkobusubsgrprev is None:
            gkobusubsgrprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'service.subtitles.subtitles.gr')) and str(gkobusubsgrnew) > str(gkobusubsgrprev):
            if monitor.waitForAbort(0.5):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του Subtitles.gr', t=1, image=logo)
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων Subtitles.gr...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon.setSetting('timeout', '240')
                setaddon.setSetting('download_timeout', '240')
                setaddon.setSetting('gkobusetsubssgr', gkobusubsgrnew)
                notify.progress('H ρύθμιση του Subtitles.gr ολοκληρώθηκε', t=1, image=logo)
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Subtitles.gr...', t=1, image=logo)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Subtitles.gr...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        # notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Subtitles.gr...', t=1, image=logo)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Subtitles.gr...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setSubsGRSettings()

