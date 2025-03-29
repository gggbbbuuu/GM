# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcvfs, sys, json, os, re
from threading import Thread

dp = xbmcgui.DialogProgressBG()

HOME           = xbmcvfs.translatePath('special://home/')
ADDONS         = os.path.join(HOME,     'addons')
ADDONPATH      = os.path.join(ADDONS, 'service.gkobu.updater')
FANART         = os.path.join(ADDONPATH, 'fanart.jpg')
ICON           = os.path.join(ADDONPATH, 'icon.png')
SKINFOLD       = os.path.join(ADDONPATH, 'resources', 'skins', 'DefaultSkin', 'media')
ADDONTITLE     = '[B]GKoBu Υπηρεσία Ενημέρωσης[/B]'

class MainMonitor(xbmc.Monitor):
    def __init__(self):
        super(MainMonitor, self).__init__()

monitor = MainMonitor()

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

def progress(msg="", t=1, image=ICON, dw='Progress.xml'):
        class MyWindow(xbmcgui.WindowXMLDialog):
            def __init__(self, *args, **kwargs):
                if monitor.waitForAbort(0.5):
                    sys.exit()
                # xbmc.sleep(500)
                self.title = '[COLOR white]%s[/COLOR]' % ADDONTITLE
                self.image = image
                if "ERROR" in kwargs["msg"]:
                    self.image = os.path.join(SKINFOLD, 'Icons', 'defaulticonerror.png')
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
                if monitor.waitForAbort(t):
                    sys.exit()
                self.close()
                
            def onAction(self,action):
                if   action == ACTION_PREVIOUS_MENU: self.close()
                elif action == ACTION_NAV_BACK: self.close()

        cw = MyWindow( dw , ADDONPATH, 'DefaultSkin', title=ADDONTITLE, fanart=FANART, image=image, msg='[B]'+msg+'[/B]', t=t)
        cw.doModal()
        del cw

def percentage(part, whole):
    return 100 * float(part)/float(whole)

def UpdatesStatus():
    request='{"jsonrpc":"2.0","method":"XBMC.GetInfoLabels","params":{"labels": ["System.AddonUpdateCount"] },"id":1}'
    response = xbmc.executeJSONRPC(request)
    response_result = json.loads(response)
    num = response_result['result']['System.AddonUpdateCount']
    return num

def updateprogress():
    progress('Έλεγχος για[CR]ενημερώσεις προσθέτων', t=2)
    xbmc.executebuiltin('UpdateAddonRepos()')
    while not UpdatesStatus() >= '0':
        if monitor.waitForAbort(1):
            xbmc.executebuiltin('Dialog.Close(all,true)')
            sys.exit()
    totalupdates = int(UpdatesStatus())
    free_mem = int(re.sub(r'\D', '', xbmc.getInfoLabel('System.FreeMemory')))
    if UpdatesStatus() > '0':
        if free_mem > 600:
            xbmc.executebuiltin('Dialog.Close(all,true)')
            if monitor.waitForAbort(0.5):
                sys.exit()
            xbmc.executebuiltin('ActivateWindow(10040,"addons://outdated/")')
            if UpdatesStatus() > '0':
                progress('Υπάρχουν %s [CR]ενημερώσεις προσθέτων' % UpdatesStatus())
                dp.create('Ενημερώσεις προσθέτων', 'Διαθέσιμες %s ενημερώσεις προσθέτων' % UpdatesStatus())
            else:
                dp.create('Ενημερώσεις προσθέτων', 'Οι ενημερώσεις ολοκληρώθηκαν')
                if monitor.waitForAbort(2):
                    dp.close()
                    sys.exit()
                dp.close()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin('Action(Back)')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin('ActivateWindow(10000)')
                return True
            Thread(target=progress_notification, daemon=True).start()
            if monitor.waitForAbort(2):
                dp.close()
                sys.exit()
            x = 0
            dismiss = 120
            while not UpdatesStatus() == '0'  and x < dismiss and not monitor.abortRequested():
                x += 1
                msg1 = 'Εκκρεμούν %s ενημερώσεις προσθέτων - κλείνω σε %s' % (UpdatesStatus(), str(dismiss-x))
                msg2 = 'Επιστρέφετε με το πλήκτρο back - κλείνω σε %s' % str(dismiss-x)
                if (x % 2) == 0:
                    msg = msg1
                else:
                    msg = msg2
                updateperc = int(percentage(int(UpdatesStatus()), totalupdates))
                dp.update(updateperc, 'Ενημερώσεις προσθέτων', msg)
                if monitor.waitForAbort(1):
                    dp.close()
                    break
                    sys.exit()
            if UpdatesStatus() == '0':
                dp.update(0, 'Ενημερώσεις προσθέτων', 'Οι ενημερώσεις ολοκληρώθηκαν')
                if monitor.waitForAbort(2):
                    dp.close()
                    sys.exit()
                dp.close()
            elif x == 120:
                dp.update(0, 'Ενημερώσεις προσθέτων', 'Λήξη χρόνου, οι ενημερώσεις δεν έχουν ολοκληρωθει')
                if monitor.waitForAbort(2):
                    dp.close()
                    sys.exit()
                dp.close()
            else:
                dp.update(0, 'Ενημερώσεις προσθέτων', 'Οι ενημερώσεις θα συνεχιστούν στο background')
                if monitor.waitForAbort(2):
                    dp.close()
                    sys.exit()
                dp.close()
            xbmc.executebuiltin('Action(Back)')
            xbmc.executebuiltin('Dialog.Close(all,true)')
            xbmc.executebuiltin('ActivateWindow(10000)')
            return True
    else:
        progress('Δεν υπάρχουν[CR]ενημερώσεις προσθέτων', t=2)
        return

def progress_notification():
    progress('Περιμένετε να ολοκληρωθουν[CR]οι ενημερώσεις προσθέτων', t=120, dw='Progress2.xml')
    
if __name__ == '__main__':
    updateprogress()
