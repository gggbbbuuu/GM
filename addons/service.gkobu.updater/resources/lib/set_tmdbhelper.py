# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
from resources.lib import notify, monitor

transPath  = xbmcvfs.translatePath
logo = transPath('special://home/addons/plugin.video.themoviedb.helper/icon.png')

def setTMDBhSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        setaddon = xbmcaddon.Addon('plugin.video.themoviedb.helper')
        logo = setaddon.getAddonInfo('icon')
        gkobutmdbhprev = setaddon.getSetting('gkobusettmdbh')
        gkobutmdbhnew = '1.3'
        if gkobutmdbhprev == '' or gkobutmdbhprev is None:
            gkobutmdbhprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.themoviedb.helper')) and str(gkobutmdbhnew) > str(gkobutmdbhprev):
            if monitor.waitForAbort(0.5):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του TMDB Helper', t=1, image=logo)
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων TMDB Helper...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon.setSetting('tmdb_details', 'true')
                setaddon.setSetting('widgets_nextpage', 'true')
                setaddon.setSetting('combined_players', 'false')
                setaddon.setSetting('mdblist_apikey', '2y7ofo43lnxrvjapee41z61ke')
                setaddon.setSetting('gkobusettmdbh', gkobutmdbhnew)
                notify.progress('H ρύθμιση του TMDB Helper ολοκληρώθηκε', t=1, image=logo)
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων TMDB Helper...', t=1, image=logo)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων TMDB Helper...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        # notify.progress('Αδυναμία εφαρμογής ρυθμίσεων TMDB Helper...', t=1, image=logo)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων TMDB Helper...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setTMDBhSettings()

