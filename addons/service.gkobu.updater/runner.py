# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import main
from resources.lib import extract, addoninstall, addonlinks, set_seren, set_alivegr, set_youtube, set_gui, set_stalker

if __name__ == '__main__':
    set_seren.setSerenSettings()
    set_alivegr.setAliveGRSettings()
    set_youtube.setYoutubeSettings()
    set_gui.setguiSettings()
    set_stalker.setpvrstalker()
    main.skinshortcuts()
    main.updatezip()
    main.SFxmls()
    main.reporescue()
