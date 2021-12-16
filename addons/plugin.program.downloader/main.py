from xbmcswift2 import Plugin
import glob,os
import re
import requests
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import _thread
import json

plugin = Plugin()
ADDON = xbmcaddon.Addon('plugin.program.downloader')
HOME = xbmcvfs.translatePath('special://home/')
ADDONPATH = os.path.join(HOME, 'addons', 'plugin.program.downloader')
ADDONS = os.path.join(HOME, 'addons')

def log(x):
    xbmc.log(repr(x))

def parseDOM(html, name="", attrs={}, ret=False):
    # Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

    if isinstance(html, str):
        try:
            html = [html.decode("utf-8")]
        except:
            html = [html]
    elif isinstance(html, str):
        html = [html]
    elif not isinstance(html, list):
        return ""

    if not name.strip():
        return ""

    ret_lst = []
    for item in html:
        temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
        for match in temp_item:
            item = item.replace(match, match.replace("\n", " "))

        lst = []
        for key in attrs:
            lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"].*?>))', re.M | re.S).findall(item)
            if len(lst2) == 0 and attrs[key].find(" ") == -1:
                lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=' + attrs[key] + '.*?>))', re.M | re.S).findall(item)

            if len(lst) == 0:
                lst = lst2
                lst2 = []
            else:
                test = list(range(len(lst)))
                test.reverse()
                for i in test:
                    if not lst[i] in lst2:
                        del(lst[i])

        if len(lst) == 0 and attrs == {}:
            lst = re.compile('(<' + name + '>)', re.M | re.S).findall(item)
            if len(lst) == 0:
                lst = re.compile('(<' + name + ' .*?>)', re.M | re.S).findall(item)

        if isinstance(ret, str):
            lst2 = []
            for match in lst:
                attr_lst = re.compile('<' + name + '.*?' + ret + '=([\'"].[^>]*?[\'"])>', re.M | re.S).findall(match)
                if len(attr_lst) == 0:
                    attr_lst = re.compile('<' + name + '.*?' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
                for tmp in attr_lst:
                    cont_char = tmp[0]
                    if cont_char in "'\"":
                        if tmp.find('=' + cont_char, tmp.find(cont_char, 1)) > -1:
                            tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char, 1))]

                        if tmp.rfind(cont_char, 1) > -1:
                            tmp = tmp[1:tmp.rfind(cont_char)]
                    else:
                        if tmp.find(" ") > 0:
                            tmp = tmp[:tmp.find(" ")]
                        elif tmp.find("/") > 0:
                            tmp = tmp[:tmp.find("/")]
                        elif tmp.find(">") > 0:
                            tmp = tmp[:tmp.find(">")]

                    lst2.append(tmp.strip())
            lst = lst2
        else:
            lst2 = []
            for match in lst:
                endstr = "</" + name

                start = item.find(match)
                end = item.find(endstr, start)
                pos = item.find("<" + name, start + 1 )

                while pos < end and pos != -1:
                    tend = item.find(endstr, end + len(endstr))
                    if tend != -1:
                        end = tend
                    pos = item.find("<" + name, pos + 1)

                if start == -1 and end == -1:
                    temp = ""
                elif start > -1 and end > -1:
                    temp = item[start + len(match):end]
                elif end > -1:
                    temp = item[:end]
                elif start > -1:
                    temp = item[start + len(match):]

                if ret:
                    endstr = item[end:item.find(">", item.find(endstr)) + 1]
                    temp = match + temp + endstr

                item = item[item.find(temp, item.find(match)) + len(temp):]
                lst2.append(temp)
            lst = lst2
        ret_lst += lst

    return ret_lst

def kodi17Fix():
    addonlist = glob.glob(os.path.join(ADDONS, '*/'))
    disabledAddons = []
    for folder in sorted(addonlist, key = lambda x: x):
        addonxml = os.path.join(folder, 'addon.xml')
        if os.path.exists(addonxml):
            fold   = folder.replace(ADDONS, '')[1:-1]
            f      = xbmcvfs.File(addonxml)
            a      = f.read()
            aid    = parseDOM(a, 'addon', ret='id')
            f.close()
            try:
                if len(aid) > 0: addonid = aid[0]
                else: addonid = fold
                add    = xbmcaddon.Addon(id=addonid)
            except:
                try:
                    log("%s was disabled" % aid[0], xbmc.LOGDEBUG)
                    disabledAddons.append(addonid)
                except:
                    log("Unabled to enable: %s" % folder, xbmc.LOGERROR)
    if len(disabledAddons) > 0:
        for disaddon in disabledAddons:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid": "%s","enabled":true}}' % disaddon)
        xbmcgui.Dialog().notification("[COLOR white]GKoBu-Υπηρεσία Ενημέρωσης[/COLOR]", "[COLOR white]Η ενεργοποίηση προσθέτων ολοκληρώθηκε![/COLOR]")
    forceUpdate()
    xbmc.executebuiltin("ReloadSkin()")

def forceUpdate(silent=False):
    xbmc.executebuiltin('UpdateAddonRepos()')
    xbmc.executebuiltin('UpdateLocalAddons()')
    if silent == False: xbmcgui.Dialog().notification("[COLOR white]GKoBu-Υπηρεσία Ενημέρωσης[/COLOR]", '[COLOR white]Ενημέρωση προσθέτων[/COLOR]')

def openfile(path_to_the_file):
    try:
        fh = xbmcvfs.File(path_to_the_file)
        contents=fh.read()
        fh.close()
        return contents
    except:
        print("Wont open: %s" % path_to_the_file)
        return None

def savefile(path_to_the_file,content):
    try:
        fh = xbmcvfs.File(path_to_the_file, 'w')
        fh.write(content)  
        fh.close()
    except: print("Wont save: %s" % path_to_the_file)

def openwindow(id):
    xbmc.executebuiltin('Dialog.Close(all, true)')
    xbmc.executebuiltin('ActivateWindow(%s)' % id)

def OKdialogClick():
    x = 0
    while not xbmc.getCondVisibility("Window.isActive(okdialog)") and x < 100:
        x += 1
        xbmc.sleep(100)
    
    if xbmc.getCondVisibility("Window.isActive(okdialog)"):
        xbmc.executebuiltin('SendClick(11)')


@plugin.route('/okpn')
def okpn():
    try:
        setaddon = xbmcaddon.Addon('plugin.video.nemesisaio')
        addonInfo = setaddon.getAddonInfo
        addonPath = xbmcvfs.translatePath(addonInfo('path'))
        basepypath = os.path.join(addonPath,'nemesis.py')
        addonversion = addonInfo('version')
        addonname = addonInfo('name')
        pinstatus = setaddon.getSetting('pin')
        basecontent = openfile(basepypath)
        if not addonversion in basecontent:
            newcontent = requests.get('http://gknwizard.eu/repo/Builds/GKoBu/xmls/okpn.xml').content
            match = re.findall('##(.+?)##', newcontent)[0]
            if not str(match) < str(addonversion):
                xbmcvfs.copy(basepypath, newcontent)
                xbmc.sleep(1000)
                setaddon.setSetting('pin', 'Passed')
    except BaseException:
        pass

@plugin.route('/fastskin')
def fastskin():
    try:
        skinxmlpath = xbmcvfs.translatePath('special://home/addons/skin.gkobuK/addon.xml')
        xmlcontent = openfile(skinxmlpath)
        if 'effectslowdown="0.75"' in xmlcontent:
            newcontent = xmlcontent.replace('effectslowdown="0.75"', 'effectslowdown="0.0"')
            savefile(skinxmlpath,newcontent)
            xbmc.sleep(2000)
            openwindow('10000')
            xbmcgui.Dialog().notification("GKoBu", "Έγινε απενεργοποίηση των animations στο GKoBu skin...", xbmcgui.NOTIFICATION_INFO, 3000, False)
            yes = xbmcgui.Dialog().yesno("GKoBu skin - Απενεργοποίηση animations", 'Αν θέλετε να εφαρμοστεί άμεσα η απενεργοποίηση των animations του GKoBu skin, θα πρέπει να γίνει επαναφόρτωση του Kodi profile, το οποίο θα "κολλήσει" για λίγο το σύστημα. Διαφορετικά η αλλαγή θα εφαρμοστεί στην επόμενη εκκίνηση του Kodi.[CR]Θέλετε κάνετε επαναφόρτωση του Kodi profile τώρα?', nolabel='[B]Ακύρωση[/B]', yeslabel='[B]Επαναφόρτωση Kodi profile[/B]')
            if not yes: return
            xbmc.executebuiltin('LoadProfile({})'.format(xbmc.getInfoLabel("system.profilename")))
        elif 'effectslowdown="0.0"' in xmlcontent:
            xbmcgui.Dialog().notification("GKoBu", "Τα animations είναι ήδη απενεργοποιημένα", xbmcgui.NOTIFICATION_INFO, 3000, False)
    except BaseException:
        xbmcgui.Dialog().notification("GKoBu", "Αδυναμία απενεργοποίσης animations...", xbmcgui.NOTIFICATION_INFO, 3000, False)


@plugin.route('/defaultskin')
def defaultskin():
    try:
        skinxmlpath = xbmcvfs.translatePath('special://home/addons/skin.gkobuK/addon.xml')
        xmlcontent = openfile(skinxmlpath)
        if 'effectslowdown="0.0"' in xmlcontent:
            newcontent = xmlcontent.replace('effectslowdown="0.0"', 'effectslowdown="0.75"')
            savefile(skinxmlpath,newcontent)
            xbmc.sleep(2000)
            openwindow('10000')
            xbmcgui.Dialog().notification("GKoBu", "Έγινε επαναφορά των animations στο GKoBu skin...", xbmcgui.NOTIFICATION_INFO, 3000, False)
            yes = xbmcgui.Dialog().yesno("GKoBu skin - Επαναφορά animations", 'Αν θέλετε να εφαρμοστεί άμεσα η επαναφορά των animations του GKoBu skin, θα πρέπει να γίνει επαναφόρτωση του Kodi profile, το οποίο θα "κολλήσει" για λίγο το σύστημα. Διαφορετικά η αλλαγή θα εφαρμοστεί στην επόμενη εκκίνηση του Kodi.[CR]Θέλετε κάνετε επαναφόρτωση του Kodi profile τώρα?', nolabel='[B]Ακύρωση[/B]', yeslabel='[B]Επαναφόρτωση Kodi profile[/B]')
            if not yes: return
            xbmc.executebuiltin('LoadProfile({})'.format(xbmc.getInfoLabel("system.profilename")))
        elif 'effectslowdown="0.75"' in xmlcontent:
            xbmcgui.Dialog().notification("GKoBu", "Τα animations είναι ήδη ενεργοποιημένα", xbmcgui.NOTIFICATION_INFO, 3000, False)
    except BaseException:
        xbmcgui.Dialog().notification("GKoBu", "Αδυναμία επαναφοράς animations...", xbmcgui.NOTIFICATION_INFO, 3000, False)

@plugin.route('/restartstalker')
def restartstalker():
    try:
        xbmcgui.Dialog().notification("GKoBu", "Επανεκκίνηση PVR Stalker...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":7,"params":{"addonid": "pvr.stalker","enabled":false}}')
        xbmc.sleep(1000)
        while isenabled('pvr.stalker') == True:
            xbmc.sleep(1000)
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":6,"params":{"addonid": "pvr.stalker","enabled":true}}')
        xbmc.sleep(1000)
        while isenabled('pvr.stalker') == False:
            xbmc.sleep(1000)
        xbmcgui.Dialog().notification("GKoBu", "PVR Stalker επανεκκινήθηκε", xbmcgui.NOTIFICATION_INFO, 3000, False)
    except:
        xbmcgui.Dialog().notification("GKoBu", "Αδυναμία επανεκκίνησης...", xbmcgui.NOTIFICATION_INFO, 3000, False)

@plugin.route('/stalport')
def stalkerportal(portal):
    try:
        setaddon = xbmcaddon.Addon('pvr.stalker')
        activeportal = setaddon.getSetting('active_portal')
        activemac = setaddon.getSetting('mac_%s' % portal)
        server = setaddon.getSetting('server_%s' % portal)
        if portal == activeportal:
            try:
                maclist_url = 'http://bit.ly/PORTALMACLIST'
                maclist = requests.get(maclist_url, timeout=10).content.decode('utf-8')
            except:
                pass
            portal_macs = re.findall('<mac_%s>(.+?)</mac_%s>'% (server, server), maclist, re.DOTALL)
            if len(portal_macs) >= 1:
                dlabel = "Επιλογή διεύθυνσης MAC"
            else:
                dlabel = "Δεν υπάρχουν διαθέσιμες εναλλακτικές MAC"
            dialog = xbmcgui.Dialog()
            nr = dialog.select(dlabel, portal_macs)
            if nr>=0:
                entry = portal_macs[nr]
            if entry == activemac:
                xbmcgui.Dialog().ok("[B][COLOR blue]GKoBu Build Υποστήριξη PVR[/COLOR][/B]", "Η MAC που επιλέξατε είναι αυτή που χρησιμοποιείτε")
                exit()
            xbmcgui.Dialog().notification("PVR Stalker", "Αλλαγή MAC", xbmcgui.NOTIFICATION_INFO, 3000, False)
            _thread.start_new_thread(OKdialogClick, ())
            xbmc.sleep(200)
            setaddon.setSetting('mac_%s' % portal, entry)
            portal = str(int(portal) + 1)
            xbmc.executebuiltin('Dialog.Close(all, true)')
            xbmc.executebuiltin('ActivateWindowAndFocus(pvrsettings, -100,0, -69,0)')
            xbmc.executebuiltin('SendClick(-69)')
            xbmc.sleep(100)
            xbmc.executebuiltin('SendClick(11)')
            xbmc.executebuiltin('ActivateWindow(10700)')
            xbmcgui.Dialog().notification("PVR Stalker", "Η MAC άλλαξε σε %s" % entry, xbmcgui.NOTIFICATION_INFO, 3000, False)
        else:
            xbmcgui.Dialog().notification("PVR Stalker", "Αλλαγή Πύλης", xbmcgui.NOTIFICATION_INFO, 3000, False)
            _thread.start_new_thread(OKdialogClick, ())
            xbmc.sleep(200)
            setaddon.setSetting("active_portal", portal)
            portal = str(int(portal) + 1)
            xbmc.executebuiltin('Dialog.Close(all, true)')
            xbmc.executebuiltin('ActivateWindowAndFocus(pvrsettings, -100,0, -69,0)')
            xbmc.executebuiltin('SendClick(-69)')
            xbmc.sleep(100)
            xbmc.executebuiltin('SendClick(11)')
            xbmc.executebuiltin('ActivateWindow(10700)')
            xbmcgui.Dialog().notification("PVR Stalker", "Πύλη %s ενεργοποιήθηκε" % portal, xbmcgui.NOTIFICATION_INFO, 3000, False)
    except:
        xbmcgui.Dialog().notification("PVR Stalker", "Αδυναμία εφαρμογής ρύθμισης...", xbmcgui.NOTIFICATION_INFO, 3000, False)

@plugin.route('/extrastalport')
def stalkerextra():
    try:
        addonInfo = xbmcaddon.Addon('pvr.stalker').getAddonInfo
        addonPath = xbmcvfs.translatePath(addonInfo('path'))
        settings_xmlpath = os.path.join(addonPath,'resources','settings.xml')
        addonversion = addonInfo('version')
        addonname = addonInfo('name')
        newcontentpath = xbmcvfs.translatePath('special://home/addons/plugin.program.downloader/resources/stalkertenportals.xml')
        if os.path.exists(settings_xmlpath):
            content = openfile(settings_xmlpath)
            if 'values="1|2|3|4|5"' in content:
                xbmcvfs.copy(newcontentpath, settings_xmlpath)
                # newcontent = openfile(newcontentpath)
                # xbmc.sleep(1000)
                # savefile(settings_xmlpath,newcontent)
                # xbmc.sleep(1000)
    except BaseException:
        xbmcgui.Dialog().notification("[COLOR white]Συντηρητής GKoBu[/COLOR]", "Αδυναμία προσθήκης extra\nπυλών σε %s" % addonname, xbmcgui.NOTIFICATION_INFO, 3000, False)

@plugin.route('/stalport1')
def stalkerport1():
    stalkerportal("0")


@plugin.route('/stalport2')
def stalkerport2():
    stalkerportal("1")


@plugin.route('/stalport3')
def stalkerport3():
    stalkerportal("2")


@plugin.route('/stalport4')
def stalkerport4():
    stalkerportal("3")


@plugin.route('/stalport5')
def stalkerport5():
    stalkerportal("4")


@plugin.route('/stalport6')
def stalkerport6():
    stalkerportal("5")


@plugin.route('/stalport7')
def stalkerport7():
    stalkerportal("6")


@plugin.route('/stalport8')
def stalkerport8():
    stalkerportal("7")


@plugin.route('/stalport9')
def stalkerport9():
    stalkerportal("8")


@plugin.route('/stalport10')
def stalkerport10():
    stalkerportal("9")

@plugin.route('/grgroupselect')
def grgroupselect():
    xbmc.executebuiltin('ActivateWindow(TVChannels)')
    xbmc.executebuiltin('RunScript(%s/resources/libs/groupselect.py,channels,gree)' % ADDONPATH)

@plugin.route('/ytapichange')
def ytapichange():
    from resources.libs import ytapi

@plugin.route('/')
def index():
    items = []

    items.append(
    {
        'label': "Βοηθός Stalker Client",
        'path': plugin.url_for('stalkerindex'),
        'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
    })
    # items.append(
    # {
        # 'label': "Force update Build",
        # 'path': plugin.url_for('forcebuildupdate'),
        # 'thumbnail': 'special://home/addons/plugin.program.downloader/icon.png',
    # })
    items.append(
    {
        'label': "Εγκατάσταση Παρόχων στο Seren",
        'path': plugin.url_for('seren_package_install'),
        'thumbnail': 'special://home/addons/plugin.program.downloader/icon.png',
    })
    items.append(
    {
        'label': "Απενεργοποίηση των animations στο GKoBu skin",
        'path': plugin.url_for('fastskin'),
        'thumbnail': 'special://home/addons/plugin.program.downloader/icon.png',
    })
    items.append(
    {
        'label': "Eνεργοποίηση των animations στο GKoBu skin",
        'path': plugin.url_for('defaultskin'),
        'thumbnail': 'special://home/addons/plugin.program.downloader/icon.png',
    })
    items.append(
    {
        'label': "Αλλαγή κλειδιού API Youtube",
        'path': plugin.url_for('ytapichange'),
        'thumbnail': 'https://raw.githubusercontent.com/anxdpanic/plugin.video.youtube/master/icon.png',
    })
    items.append(
    {
        'label': "Τερματισμός όλων των υπηρεσιών",
        'path': plugin.url_for('stopservice'),
        'thumbnail': 'special://home/addons/plugin.program.downloader/icon.png',
    })
    items.append(
    {
        'label': "Απεγκατάσταση Προσθέτων (Προχωρημένη λειτουργία)",
        'path': plugin.url_for('aauninstall'),
        'thumbnail': 'special://home/addons/plugin.program.aauninstaller/resources/icon.png',
    })
    # items.append(
    # {
        # 'label': "Edit",
        # 'path': plugin.url_for('edit'),
        # 'thumbnail': 'special://home/addons/plugin.program.downloader/icon.png',
    # })
    return items

@plugin.route('/stalkerindex/')
def stalkerindex():
    addonInfo = xbmcaddon.Addon('pvr.stalker').getAddonInfo
    addonPath = xbmcvfs.translatePath(addonInfo('path'))
    settings_xmlpath = os.path.join(addonPath,'resources','settings.xml')
    activeportal = str(int(xbmcaddon.Addon('pvr.stalker').getSetting('active_portal')) + 1)
    activeserver = 'server_' + (xbmcaddon.Addon('pvr.stalker').getSetting('active_portal'))
    activeportalname = portallabel(activeserver)
    items = []

    items.append(
    {
        'label': "[B][COLOR lightgreen]" + "Ενεργή Πύλη στον Stalker είναι η Πύλη " + activeportal + " [COLOR white]--" + activeportalname +"--[/COLOR][/B]",
        'path': plugin.url_for('stalkerindex'),
        'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
    })
    items.append(
    {
        'label': indexlabel('1') + portallabel('server_0'),
        'path': plugin.url_for('stalkerport1'),
        'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
    })
    items.append(
    {
        'label': indexlabel('2') + portallabel('server_1'),
        'path': plugin.url_for('stalkerport2'),
        'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
    })
    items.append(
    {
        'label': indexlabel('3') + portallabel('server_2'),
        'path': plugin.url_for('stalkerport3'),
        'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
    })
    items.append(
    {
        'label': indexlabel('4') + portallabel('server_3'),
        'path': plugin.url_for('stalkerport4'),
        'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
    })
    items.append(
    {
        'label': indexlabel('5') + portallabel('server_4'),
        'path': plugin.url_for('stalkerport5'),
        'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
    })
    if os.path.exists(settings_xmlpath):
        content = openfile(settings_xmlpath)
        if 'values="1|2|3|4|5|6|7|8|9|10"' in content:
            items.append(
            {
                'label': indexlabel('6') + portallabel('server_5'),
                'path': plugin.url_for('stalkerport6'),
                'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
            })
            items.append(
            {
                'label': indexlabel('7') + portallabel('server_6'),
                'path': plugin.url_for('stalkerport7'),
                'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
            })
            items.append(
            {
                'label': indexlabel('8') + portallabel('server_7'),
                'path': plugin.url_for('stalkerport8'),
                'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
            })
            items.append(
            {
                'label': indexlabel('9') + portallabel('server_8'),
                'path': plugin.url_for('stalkerport9'),
                'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
            })
            items.append(
            {
                'label': indexlabel('10') + portallabel('server_9'),
                'path': plugin.url_for('stalkerport10'),
                'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
            })
    if os.path.exists(settings_xmlpath):
        content = openfile(settings_xmlpath)
        if 'values="1|2|3|4|5"' in content:
            items.append(
            {
                'label': "Πρόσθήκη Extra Portals",
                'path': plugin.url_for('stalkerextra'),
                'thumbnail': 'special://home/addons/pvr.stalker/icon.png',
            })
    return items

def portallabel(server):
    try:
        label = (xbmcaddon.Addon('pvr.stalker').getSetting(server)).split('/')[2].split(':')[0].replace('onisat.net', 'test.live')
    except:
        label = 'Κενή...'
    return label

def indexlabel(portalnumber):
    setaddon = xbmcaddon.Addon('pvr.stalker')
    activeportal = str(int(xbmcaddon.Addon('pvr.stalker').getSetting('active_portal')) + 1)
    if portalnumber == activeportal:
        label = "[COLOR lime]Επιλογή εναλλακτικής MAC διεύθυνσης στο [/COLOR]"
    else:
        label = "Αλλαγή σε Πύλη %s - " % portalnumber
    return label


@plugin.route('/forcebuildupdate')
def forcebuildupdate():
    xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εκτελείται αίτημα ενημέρωσης build", xbmcgui.NOTIFICATION_INFO, 3000, False)
    md5path = os.path.join(HOME, 'userdata', 'addon_data', 'service.gkobu.updater', 'build_md5s', 'gkobu_autoexec.zip.md5')
    if xbmc.getCondVisibility('System.HasAddon(service.gkobu.updater)'):
        xbmcaddon.Addon('service.gkobu.updater').setSetting('gkobupvrask2', 'true')
    if xbmc.getCondVisibility('System.HasAddon(pvr.stalker)'):
        _thread.start_new_thread(OKdialogClick, ())
        xbmc.sleep(200)
        xbmcaddon.Addon('pvr.stalker').setSetting('gkobupvrstalgen', '0')
        _thread.start_new_thread(OKdialogClick, ())
        xbmc.sleep(200)
        xbmcaddon.Addon('pvr.stalker').setSetting('gkobupvrstalset', '0')
    if os.path.exists(md5path):
        xbmcvfs.delete(md5path)
    xbmc.sleep(500)
    xbmc.executebuiltin("RunScript(service.gkobu.updater)")

@plugin.route('/seren_package_install')
def seren_package_install():
    xbmc.executebuiltin("RunScript(special://home/addons/plugin.program.downloader/resources/libs/seren_package_install.py)")

@plugin.route('/stopservice')
def stopservice():
    xbmc.executebuiltin("RunScript(special://home/addons/plugin.program.downloader/resources/libs/stopservice.py)")

@plugin.route('/aauninstall')
def aauninstall():
    xbmc.executebuiltin("RunScript(plugin.program.aauninstaller)")

def isenabled(addonid):
    query = '{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails", "params": { "addonid": "%s", "properties" : ["name", "thumbnail", "fanart", "enabled", "installed", "path", "dependencies"] } }' % addonid
    addonDetails = xbmc.executeJSONRPC(query)
    details_result = json.loads(addonDetails)
    if "error" in details_result:
        return False
    elif details_result['result']['addon']['enabled'] == True:
        return True
    else:
        return False

if __name__ == '__main__':
    plugin.run()