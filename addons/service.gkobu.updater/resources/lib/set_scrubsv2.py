# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
from resources.lib import notify, monitor
import main
transPath  = xbmcvfs.translatePath
logo = transPath('special://home/addons/plugin.video.scrubsv2/resources/images/icon.png')

def setScrubsSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        addon_data_folder = transPath('special://home/userdata/addon_data/')
        setaddon = xbmcaddon.Addon('plugin.video.scrubsv2')
        logo = setaddon.getAddonInfo('icon')
        setversionaddon = main.addon
        gkobuscrubsv2prev = setversionaddon.getSetting('gkobusetscrubsv2')
        gkobuscrubsv2new = '1.2'
        if gkobuscrubsv2prev == '' or gkobuscrubsv2prev is None:
            gkobuscrubsv2prev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.scrubsv2')) and (str(gkobuscrubsv2new) > str(gkobuscrubsv2prev) or not os.path.exists(os.path.join(addon_data_folder, 'plugin.video.scrubsv2', 'settings.xml'))):
            if monitor.waitForAbort(0.5):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του Scrubs v2', t=1, image=logo)
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων Scrubs v2...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon.setSetting('show.artwork', 'false')
                setaddon.setSetting('subtitles', 'true')
                setaddon.setSetting('subtitles.lang.1', 'Greek')
                setaddon.setSetting('subtitles.notify', 'true')
                setversionaddon.setSetting('gkobusetscrubsv2', gkobuscrubsv2new)
                notify.progress('H ρύθμιση του Scrubs v2 ολοκληρώθηκε', t=1, image=logo)
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Scrubs v2...', t=1, image=logo)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Scrubs v2...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        # notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Scrubs v2...', t=1, image=logo)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Scrubs v2...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setScrubsSettings()

