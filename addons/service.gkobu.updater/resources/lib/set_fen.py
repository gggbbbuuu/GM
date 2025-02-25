# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
from resources.lib import notify, monitor
import main
transPath  = xbmcvfs.translatePath
logo = transPath('special://home/addons/plugin.video.fen/icon.png')

def setFenSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        addon_data_folder = transPath('special://home/userdata/addon_data/')
        setaddon = xbmcaddon.Addon('plugin.video.fen')
        logo = setaddon.getAddonInfo('icon')
        setversionaddon = main.addon
        gkobufenprev = setversionaddon.getSetting('gkobusetfen')
        gkobufennew = '1.2'
        if gkobufenprev == '' or gkobufenprev is None:
            gkobufenprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.fen')) and (str(gkobufennew) > str(gkobufenprev) or not os.path.exists(os.path.join(addon_data_folder, 'plugin.video.fen', 'settings.xml'))):
            if monitor.waitForAbort(0.5):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του Fen', t=1, image=logo)
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων Fen...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon.setSetting('meta_language_display', 'Greek')
                setaddon.setSetting('provider.external', 'true')
                setaddon.setSetting('external_scraper.name', 'CocoScrapers Module')
                setaddon.setSetting('meta_language', 'el')
                setaddon.setSetting('results.sort_order_display', 'Quality, Size, Provider')
                setaddon.setSetting('results.ignore_filter', '1')
                setaddon.setSetting('subtitles.subs_action', '0')
                setaddon.setSetting('subtitles.language_primary', 'ell')
                setaddon.setSetting('subtitles.language_secondary', 'eng')
                setaddon.setSetting('reuse_language_invoker', 'false')
                setaddon.setSetting('external_scraper.module', 'script.module.cocoscrapers')
                setaddon.setSetting('first_use', 'false')
                if not xbmc.getCondVisibility('System.HasAddon(script.module.cocoscrapers)'):
                    xbmc.executebuiltin('InstallAddon(script.module.cocoscrapers)')
                    xbmc.executebuiltin('SendClick(11)')
                    x = 0
                    while xbmc.getCondVisibility('System.HasAddon(script.module.cocoscrapers)') == False and x < 60:
                        x += 1
                        xbmc.sleep(1000)
                    if not xbmc.getCondVisibility('System.HasAddon(script.module.cocoscrapers)'):
                        notify.progress('Αποτυχία εγκατάστασης CocoScrapers Module', t=3, image=logo)
                        notify.progress('Απαιτείται χειροκίνητη εγκατάσταση του CocoScrapers Module', t=3, image=logo)
                        return
                setversionaddon.setSetting('gkobusetfen', gkobufennew)
                notify.progress('H ρύθμιση του Fen ολοκληρώθηκε', t=1, image=logo)
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Fen...', t=1, image=logo)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Fen...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        # notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Fen...', t=1, image=logo)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Fen...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setFenSettings()

