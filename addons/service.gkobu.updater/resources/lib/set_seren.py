# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
from resources.lib import notify, monitor

transPath  = xbmcvfs.translatePath
logo = transPath('special://home/addons/plugin.video.seren/ico-seren-2.jpg')

def setSerenSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        setaddon = xbmcaddon.Addon('plugin.video.seren')
        logo = setaddon.getAddonInfo('icon')
        gkobuserenprev = setaddon.getSetting('gkobusetseren')
        gkobuserennew = '2.2'
        if gkobuserenprev == '' or gkobuserenprev is None:
            gkobuserenprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.seren')) and str(gkobuserennew) > str(gkobuserenprev):
            if monitor.waitForAbort(1.0):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του Seren', t=1, image=logo)
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων Seren...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon.setSetting('addon.view', '0')
                setaddon.setSetting('episode.view', '0')
                setaddon.setSetting('general.cacheAssistMode', '0')
                setaddon.setSetting('general.cachelocation', '1')
                setaddon.setSetting('general.playstyleEpisodes', '1')
                setaddon.setSetting('general.playstyleMovie', '1')
                setaddon.setSetting('general.setViews', 'true')
                setaddon.setSetting('movie.view', '0')
                setaddon.setSetting('general.metalocation', '2')
                setaddon.setSetting('preem.cloudfiles', 'false')
                setaddon.setSetting('preem.enabled', 'false')
                setaddon.setSetting('providers.autoupdates', 'true')
                setaddon.setSetting('rd.auth_start', '')
                setaddon.setSetting('realdebrid.enabled', 'true')
                setaddon.setSetting('season.view', '0')
                setaddon.setSetting('show.view', '0')
                setaddon.setSetting('smartPlay.preScrape', 'false')
                setaddon.setSetting('general.enablesizelimit', 'false')
                setaddon.setSetting('general.hideUnAired', 'false')
                setaddon.setSetting('general.meta.showoriginaltitle', 'true')
                setaddon.setSetting('gkobusetseren', gkobuserennew)
                notify.progress('H ρύθμιση του Seren ολοκληρώθηκε', t=1, image=logo)
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Seren...', t=1, image=logo)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Seren...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        # notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Seren...', t=1, image=logo)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Seren...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True

if __name__ == '__main__':
    setSerenSettings()

