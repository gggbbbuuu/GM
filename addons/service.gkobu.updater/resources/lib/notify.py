# -*- coding: utf-8 -*-
import os
import xbmc, xbmcgui, xbmcvfs, xbmcaddon, sys
import main
from resources.lib import set_seren, set_alivegr, set_youtube, set_gui, set_stalker, monitor

addon          = xbmcaddon.Addon()
ADDON_ID       = addon.getAddonInfo('id')
VERSION        = addon.getAddonInfo('version')
ADDONPATH      = addon.getAddonInfo('path')
ADDONTITLE     = addon.getAddonInfo('name')
HOME           = xbmcvfs.translatePath('special://home/')
ADDONS         = os.path.join(HOME,     'addons')
FANART         = os.path.join(ADDONPATH,   'fanart.jpg')
ICON           = os.path.join(ADDONPATH,   'icon.png')
SKINFOLD       = os.path.join(ADDONPATH,   'resources', 'skins', 'DefaultSkin', 'media')


ACTION_PREVIOUS_MENU            =  10   ## ESC action
ACTION_NAV_BACK                 =  92   ## Backspace action
ACTION_MOVE_LEFT                =   1   ## Left arrow key
ACTION_MOVE_RIGHT               =   2   ## Right arrow key
ACTION_MOVE_UP                  =   3   ## Up arrow key
ACTION_MOVE_DOWN                =   4   ## Down arrow key
ACTION_MOUSE_WHEEL_UP           = 104   ## Mouse wheel up
ACTION_MOVE_MOUSE               = 107   ## Down arrow key
ACTION_SELECT_ITEM              =   7   ## Number Pad Enter
ACTION_BACKSPACE                = 110   ## ?
ACTION_MOUSE_LEFT_CLICK         = 100
ACTION_MOUSE_LONG_CLICK         = 108


##########################
### Converted to XML
##########################

def progress(msg="", func="", t=1, image=ICON, dw='Progress.xml'):
        class MyWindow(xbmcgui.WindowXMLDialog):
            def __init__(self, *args, **kwargs):
                if monitor.waitForAbort(0.5):
                    sys.exit()
                self.title = '[COLOR white]%s[/COLOR]' % ADDONTITLE
                self.image = image
                if "ERROR" in kwargs["msg"]:
                    self.image = os.path.join(ADDONPATH,   'resources', 'skins', 'DefaultSkin', 'media', 'Icons', 'defaulticonerror.png')
                self.fanart = FANART
                self.msg = '[COLOR darkorange]%s[/COLOR]' % kwargs["msg"]
                if "ERROR" in kwargs["msg"]:
                    self.msg = '[COLOR red]%s[/COLOR]' % kwargs["msg"]


            def onInit(self):
                self.fanartimage = 101
                self.titlebox = 102
                self.imagecontrol = 103
                self.textbox = 104
                self.showdialog()

            def showdialog(self):
                self.getControl(self.imagecontrol).setImage(self.image)
                self.getControl(self.fanartimage).setImage(os.path.join(SKINFOLD, 'Background', 'progress-dialog-bg.png'))
                self.getControl(self.fanartimage).setColorDiffuse('9FFFFFFF')
                self.getControl(self.textbox).setText(self.msg)
                self.getControl(self.titlebox).setLabel(self.title)
                if func == "setSerenSettings":
                    set_seren.setSerenSettings()
                elif func == "setAliveGRSettings":
                    set_alivegr.setAliveGRSettings()
                elif func == "setYoutubeSettings":
                    set_youtube.setYoutubeSettings()
                elif func == "setguiSettings":
                    set_gui.setguiSettings()
                elif func == "setpvrstalker":
                    set_stalker.setpvrstalker()
                elif func == "skinshortcuts":
                    main.skinshortcuts()
                elif func == "updatezip":
                    main.updatezip()
                elif func == "SFxmls":
                    main.SFxmls()
                elif func == "addon_remover":
                    main.addon_remover()
                elif func == "reporescue":
                    main.reporescue()
                elif func == "":
                    pass
                if monitor.waitForAbort(t):
                    sys.exit()
                self.close()
                
            def onAction(self,action):
                if   action == ACTION_PREVIOUS_MENU: self.close()
                elif action == ACTION_NAV_BACK: self.close()

        cw = MyWindow( dw , main.addon.getAddonInfo('path'), 'DefaultSkin', title=ADDONTITLE, fanart=FANART, image=image, msg='[B]'+msg+'[/B]', func=func, t=t)
        cw.doModal()
        del cw
