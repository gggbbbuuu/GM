# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os

KODIV = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
transPath  = xbmc.translatePath if KODIV < 19 else xbmcvfs.translatePath


def setAliveGRSettings():
    try:
        addons_folder = transPath('special://home/addons/')
        setaddon = xbmcaddon.Addon('plugin.video.AliveGR')
        gkobualivegrprev = setaddon.getSetting('gkobusetalivegr')
        gkobualivegrnew = '1.1'
        if gkobualivegrprev == '' or gkobualivegrprev is None:
            gkobualivegrprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.AliveGR')) and str(gkobualivegrnew) > str(gkobualivegrprev):
            try:
                xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων AliveGR...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon = xbmcaddon.Addon('plugin.video.AliveGR')
                setaddon.setSetting('show_alt_live', 'true')
                setaddon.setSetting('show_alt_vod', 'true')
                setaddon.setSetting('sl_quality_picker', '1')
                setaddon.setSetting('yt_quality_picker', '1')
                setaddon.setSetting('gkobusetalivegr', gkobualivegrnew)
            except BaseException:
                xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων AliveGR...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων AliveGR...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return
    return True


if __name__ == '__main__':
    setAliveGRSettings()

