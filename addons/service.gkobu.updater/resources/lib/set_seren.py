# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os

KODIV = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
transPath  = xbmc.translatePath if KODIV < 19 else xbmcvfs.translatePath


def setSerenSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        setaddon = xbmcaddon.Addon('plugin.video.seren')
        gkobuserenprev = setaddon.getSetting('gkobusetseren')
        gkobuserennew = '2.1'
        if gkobuserenprev == '' or gkobuserenprev is None:
            gkobuserenprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.seren')) and str(gkobuserennew) > str(gkobuserenprev):
            try:
                xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων Seren...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon.setSetting('addon.view', '0')
                setaddon.setSetting('episode.view', '0')
                setaddon.setSetting('general.cacheAssistMode', '0')
                setaddon.setSetting('general.cachelocation', '1')
                setaddon.setSetting('general.playstyleEpisodes', '1')
                setaddon.setSetting('general.playstyleMovie', '1')
                setaddon.setSetting('general.setViews', 'true')
                setaddon.setSetting('movie.view', '0')
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
            except BaseException:
                xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Seren...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Seren...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True

if __name__ == '__main__':
    setSerenSettings()

