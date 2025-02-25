# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, re, os, glob, _thread, shutil

KODIV = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
transPath  = xbmc.translatePath if KODIV < 19 else xbmcvfs.translatePath

def reset_version(addonid,badversion):
    try:
        addonInfo = xbmcaddon.Addon(addonid).getAddonInfo
        addonPath = xbmc.translatePath(addonInfo('path'))
        addon_xml_path = os.path.join(addonPath,'addon.xml')
        addonversion = addonInfo('version')
        addonname = addonInfo('name')
        if os.path.exists(addon_xml_path):
            if addonversion.startswith(badversion):
                xbmcgui.Dialog().notification("[COLOR white]Συντηρητής GKoBu[/COLOR]", "Επαναφορά έκδοσης %s" % addonname, xbmcgui.NOTIFICATION_INFO, 2000, False)
                content=openfile(addon_xml_path)
                content=content.replace('version="%s"' % addonversion,'version="0.0.1"')
                savefile(addon_xml_path,content)
                xbmcgui.Dialog().notification("[COLOR white]Συντηρητής GKoBu[/COLOR]", "Έκδοση %s ΟΚ\nΕπανεκκινήστε το Kodi!!!" % addonname, xbmcgui.NOTIFICATION_INFO, 4000, False)
            else:
                return
        else:
            return
    except BaseException:
        xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία επαναφοράς έκδοσης %s" % addonname, xbmcgui.NOTIFICATION_INFO, 3000, False)
        return


def openfile(path_to_the_file):
    try:
        fh = xbmcvfs.File(path_to_the_file)
        contents=fh.read()
        fh.close()
        return contents
    except:
        print("Wont open: %s" % filename)
        return None

def savefile(path_to_the_file,content):
    try:
        fh = xbmcvfs.File(path_to_the_file, 'w')
        fh.write(content)  
        fh.close()
    except: print("Wont save: %s" % filename)

if __name__ == '__main__':
    reset_version(sys.argv[1],sys.argv[2])

