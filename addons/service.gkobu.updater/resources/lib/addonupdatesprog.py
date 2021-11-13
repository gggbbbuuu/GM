# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcaddon, sys, json
from resources.lib import notify, monitor
from contextlib import contextmanager
addon = xbmcaddon.Addon()
addonid = addon.getAddonInfo('id')
addontitle = addon.getAddonInfo('name')
lang = addon.getLocalizedString

dp = xbmcgui.DialogProgressBG()

@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def percentage(part, whole):
    return 100 * float(part)/float(whole)

def UpdatesStatus():
    request='{"jsonrpc":"2.0","method":"XBMC.GetInfoLabels","params":{"labels": ["System.AddonUpdateCount"] },"id":1}'
    response = xbmc.executeJSONRPC(request)
    response_result = json.loads(response)
    num = response_result['result']['System.AddonUpdateCount']
    return num

def progress():
    notify.progress('Έλεγχος για[CR]ενημερώσεις προσθέτων', t=2)
    while not UpdatesStatus() >= '0':
        if monitor.waitForAbort(1):
            xbmc.executebuiltin('Dialog.Close(all,true)')
            sys.exit()

    print ("UPDATESTATUS" , UpdatesStatus())
    if UpdatesStatus() > '0':
        xbmc.executebuiltin('Dialog.Close(all,true)')
        if monitor.waitForAbort(0.5):
            sys.exit()
        xbmc.executebuiltin('ActivateWindow(10040)')
        with busy_dialog():
            totalupdates = int(UpdatesStatus())
            notify.progress('Υπάρχουν %s [CR]ενημερώσεις προσθέτων' % str(totalupdates))
            dp.create('Ενημερώσεις προσθέτων', 'Διαθέσιμες %s ενημερώσεις προσθέτων' % UpdatesStatus())
            if monitor.waitForAbort(2):
                dp.close()
                sys.exit()
            x = 0
            dismiss = 120
            while not UpdatesStatus() == '0'  and x < dismiss and xbmc.getCondVisibility("Window.isActive(busydialognocancel)"):
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
        if monitor.waitForAbort(0.5):
            sys.exit()
        xbmc.executebuiltin('ActivateWindow(10000)')
        return True
    else:
        notify.progress('Δεν υπάρχουν[CR]ενημερώσεις προσθέτων', t=2)
        return
