# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcvfs, sys, os
from resources.lib import notify, monitor
import main
KODIV = xbmc.getInfoLabel("System.BuildVersion")[:2]

def gkobu_version_check():
    addon = main.addon
    gkobu_version = addon.getSetting('shortcutsver') or addon.getSetting('updatesver')
    gkobu_kodi_version = gkobu_version.replace(gkobu_version[0:2], KODIV, 1)
    # if gkobuguisetprev == '' or gkobuguisetprev is None:
        # gkobuguisetprev = '0'
    versionaddon = xbmcaddon.Addon('version.gkobu')
    versionpath = xbmcvfs.translatePath(versionaddon.getAddonInfo('path'))
    versionxml = os.path.join(versionpath, 'addon.xml')
    with xbmcvfs.File(versionxml, 'r') as oldverxml:
        xml = oldverxml.read()
        xml = xml.replace('version="%s"' % versionaddon.getAddonInfo('version'), 'version="%s"' % gkobu_kodi_version)
    with xbmcvfs.File(versionxml, 'w') as newverxml:
        newverxml.write(xml)
    if monitor.waitForAbort(1):
        sys.exit()
    xbmc.executebuiltin('UpdateLocalAddons()')
    addon.setSetting('gkobu_version_fixed', KODIV)


if __name__ == '__main__':
    gkobu_version_check()

