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
        # if 'mainmenu' in item:
            # if addon.getSetting('overwritemain') == 'false' and not (str(old_ver) == '19.0.9' or str(old_ver) == '19.0.8' or str(old_ver) == '19.0.7' or str(old_ver) == '19.0.6' or str(old_ver) == '19.0.5' or str(old_ver) == '19.0.4' or str(old_ver) == '19.0.3' or str(old_ver) == '19.0.2' or str(old_ver) == '19.0.1' or str(old_ver) == '19.0.0'):
                # continue
        if item.endswith('.hash'):
            skinhashpath = os.path.join(skinshortcutsdir, item)
            continue
        old  = os.path.join(skinshortcutsdir, item)
        new = os.path.join(newdatapath, item)
        dp.update(perc, addontitle, (lang(30001)+"...%s") % item)
        if matchmd5(old, new):
            continue
        if item.endswith('.xml') and addon.getSetting('keepmyshortcuts') == 'true' and versioncheck('19.0.10', old_ver) == False:
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

    for item in xmllinks:
        if monitor.waitForAbort(0.5):
            sys.exit()
        skin_xml = os.path.join(newdatapath, item[0])
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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("NTEoIjI1IGE3OzI1IDI0Iik7NTEoKGZkIGY4LGVlOihmZCBlNCxiLGY6YTcuZDQoZTQsYixmLjIzKCc4Mi04JykpKShlNiIoWzAtOWEtZl0rKSIsZmQgZjA6ZjgoZjAsZWUpLDI0LjQxKCJmMiIpKSkoZmQgYSxiOmJbNzIoImU1IithLjg1KDEpLDE2KV0sIjB8MXwyfDN8NHw1fGQ2fGE1fDh8YWZ8YXxlMXw3fDFjfDc4fGZ8MTB8ZmJ8YjF8NWF8MzF8Mzd8MTZ8M2J8NnxiN3w0Y3xhZXwzY3xiNnw2OHwxNHwyMHw2Nnw2N3xlYnwyZXxlZHwxN3wxYnwxZXw4MHxmNXw5fDI4fGM1fDEzfDU1fGFifGV8MzJ8MzR8NmN8NmZ8Mzh8Mzl8MTV8NjV8YmF8Y2F8NDR8NDd8NTB8MWF8MWZ8ZWZ8NGJ8YTl8MjJ8Yjh8Yjl8YmV8ZWF8Mjd8ZjN8MmF8NTl8NWR8MmR8YTR8MzB8YjB8MzN8YzB8NDB8Y2R8NDN8NDh8NDV8N2V8ZGF8NDZ8ZmN8YjR8YWN8NTJ8NTR8Y3xiY3w4Ynw4ZHwxMXxkOXw5ZnxkY3w2MHw2MXxmN3w2MnxmMXwxOHwxOXw3YXxjNHw2Ynw4MXxiYnw3MXw2OXw3ZHxkMHw3NXw3N3wyMXw3OXxjZnw3ZnwyNnwyOXwyYnw4YXw5M3wyY3xlMnw4OHw5NXw5OXw5N3w4Y3wzNXwzNnwzYXxmNHxhMHw5OHxhMnxjOHxjOXwzZnxkMXwzZHw0MnxkOHw0OXwzZXw0YXxlN3xhM3xhYXxlNnw1M3xiMnxmZnxhOHxhNnw0Znw1N3xiZHw1OHw1Ynw1ZXw1Y3w2NHw1ZnxiZnw2YXxkZnxlY3w2ZHwyZnw3MHxjYnw3M3w3NHw3Nnw3Y3xlOHxkM3w2ZXwyM3wxMDJ8ODN8Y2N8OWJ8ODZ8OGV8OGZ8OTB8OTF8OTJ8OTR8ZTB8OTZ8ODd8ODl8OWN8OWR8ODR8OWV8YTF8YjN8YWR8Zjl8YjV8MTJ8YzF8YzJ8YzN8Yzd8ZGR8YzZ8NzJ8Y2V8NGV8NjN8ZDd8ZDV8MTAwfGQyfDgyfGRifGRlfGU5fDU2fGY2fDdifDFkfDEwMXxmYXwxMDN8ZTN8ZmV8NGR8ZCIuZTAoInwiKSkp")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|2|3|4|5|local_md5_filename|local_linkfilename|8|UpdateLocalAddons|a|b|removeaddonslist|downloaded_urls|SHORTLATESTDATA|f|10|allWithProgress|old_updatesver|local_filename|executebuiltin|remote_md5_url|16|skinshortcuts|addonDatabase|addon_remover|getAddonInfo|changelogtxt|waitForAbort|linkfilename|versionaddon|shortcutsver|20|iter_content|ZIP_JSON_URL|decode|base64|import|addoninstall|versionpath|status_code|yesnodialog|mainxmlsver|repo_rescue|addonlinks|reporescue|setSetting|versionxml|chunk_size|addontitle|32|BUILD_MD5S|getSetting|addonslist|percentage|remote_md5|updatesver|urlcontent|textViewer|updatedata|changelog|gknbuilds|xbmcaddon|gggbbbuuu|isVisible|b64decode|goldenrod|newverxml|local_md5|totalurls|ADDONDATA|runSFxmls|oldverxml|RunScript|makedirs|starturl|requests|progress|filename|okdialog|jsondata|exec|userdata|gitfront|autoexec|DOWNLOAD|continue|endswith|Finished|tmp_md5|addonid|replace|extract|timeout|updates|Updates|itemmd5|special|xbmcgui|xbmcvfs|filemd5|version|monitor|success|delete|Dialog|github|giturl|exists|encode|SFxmls|except|verify|rsplit|int|stream|rename|create|extend|addrep|notify|DELETE|return|folder|ignore|Window|append|update|FAILED|NEEDED|utf|RENAME|loads|group|while|30003|COLOR|30017|magic|write|https|codes|30013|30012|30010|30014|Addon|sleep|30009|30004|30005|30006|30007|30008|9a|30016|30015|ascii|gkobu|False|chunk|30011|close|pass|join|lang|HOME|re|elif|else|home|True|None|1024|runskinshortcuts|addonlinkremote|link|xbmc|text|main|with|URLS|path|translatePath|item|urls|File|perc|read|json|exit|NOT|sys|tmp|rmv|MD5|len|url|x50|def|rep|get|log|zip|build_update_version|and|500|md5|for|add|ZIP|raw|sub|x04|old_shortcutsver|x03|txt|xml|not|com|try|x4b|str|is|split|if|TO|GM|o|0x|r|as|CR|io|in|4afd12ecadd18930fa40d1c5e51453721572757a|rb|addon|y|rmvaddonlist|m|ok|ZGEgNGUoKToKCTYgPSAyNS4zMygnNDAnKQoJYiA2ID09ICcnIDhlIDYgYjAgNWU6CgkJNiA9ICcwLjAuMCcKCWQ2ID0gMjUuMzMoJzM2JykKCWIgZDYgPT0gJycgOGUgZDYgYjAgNWU6CgkJZDYgPSAnMC4wLjAnCgllYSA9IDI1LjMzKCc0YicpCgliIGVhID09ICcnIDhlIGVhIGIwIDVlOgoJCWVhID0gJzAuMC4wJwoJNDQgPSAnOGE6Ly9hMC5lOC85Zi85Ni8yMy9mMC1hZC9iYi9hYS5hNycKCQoJNzIgPSAnOGE6Ly9hZi5lNi85NC80ZS9iYi9kMi84MS5iNScKCQoJNDYgPSBbNzJdCgkKCTkgPSBbXQoJCgk0Ni5iOCg4NC5kNSkKCQoJZS5mMig3KDg5KSwgYmU9MikKCSMgNmIuNzkoMTQsIDcoODkpKQoJNjg6CgkJMzcgPSAxYS45Myg0NCwgNGQ9MTApCgkzNToKCQllLmYyKDcoY2MpLCBiZT0zKQoJCTcwCgliIDM3LjJjID09IDFhLjY0LjZkOgoJCTY4OgoJCQkzZSA9IGE3LmNmKDM3LmExKQoJCQk3OCA0NSA0OCAzZToKCQkJCTE3ID0gM2VbNDVdCgkJCQliICI1MSIgNDggNDU6CgkJCQkJOTUgPSAxN1siOTUiXQoJCQkJCTkyID0gMTdbIjkyIl0KCQkJCQk3YSA9ICg5NSwgOTIpCgkJCQkJOS41OSg3YSkKCQkJCWEzIDQ1ID09ICI2MSI6CgkJCQkJNDEgPSAxN1siZDgiXQoJCQkJCQoJCQkJNDM6CgkJCQkJYiAiMWMiIDQ4IDQ1OgoJCQkJCQljMCA9IDQ1LmM5KCJmMSIpWzFdCgkJCQkJNTEgPSAxN1siMmQiXQoJCQkJCTY5ID0gMTdbIjdkIl0KCQkJCQllYyA9IDUxLjc1KCcvJywgMSlbLTFdCgkJCQkJYyA9IDRhLjFkLjRmKDUyLCAoZWMgKyAiLjdkIikpCgkJCQkJYiAnMjYnIDQ4IGVjIDU1IDYgPT0gJzAuMC4wJzoKCQkJCQkJZTAuMWUoYykKCQkJCQlhMyAiMWMiIDQ4IGVjIDU1IGQ2ID09ICcwLjAuMCc6CgkJCQkJCWUwLjFlKGMpCgkJCQkJMTEgPSBlMC4zYShjLCJiMSIpLjYyKClbOjMyXQoJCQkJCWIgMTEgNTUgMTEgPT0gNjk6CgkJCQkJCTEyLjNiKCgiWyU1Y10gMmYgYWUgNzM6ICIgJSAxMykgKyBlYykKCQkJCQkJZTkKCQkJCQliIDUxIDQ4IDQ2OgoJCQkJCQllOQoJCQkJCTQ2LjU5KDUxKQoJCTM1OgoJCQllLmYyKDcoYzQpLCBiZT0zKQoJNDM6CgkJZS5mMig3KGMzKSwgYmU9MykKCWIgNWEgNzEoOSkgPiAwOgoJCTkgPSA4YgoJZWIgPSBhNAoJNjg6CgkJYiA1YSA0YS4xZC4zNChlMC4xOShlYikpOgoJCQk0YS45YihlMC4xOShlYikpCgkzNToKCQk5ZAoJNTggPSA3MSg0NikKCTQyID0gMAoJZjMgPSBbXQoJMWIgPSA2NwoJM2QgPSA2NwoJNzggMmQgNDggNDY6CgkJYiAiMWMuOTgiIDQ4IDJkOgoJCQllYiA9IDViCgkJNDM6CgkJCWViID0gYTQKCQliIDIxLmQoMC41KToKCQkJNTMuNDcoKQoJCTQyICs9IDEKCQk3NCA9IGRkKDhjKDQyLCA1OCkpCgkJZGYgPSAyZC43NSgnLycsIDEpWy0xXQoJCWIgNWEgZGY6CgkJCWU5CgkJMmUgPSA0YS4xZC40ZihlYiwgZGYpCgkJYTIgPSAyZSArICIuZDciCgkJMTggPSA0YS4xZC40Zig1MiwgKGRmICsgIi43ZCIpKQoJCTM4ID0gMmQgKyAiLjdkIgoKCQkzYyA9IGUwLjNhKDE4LCJiMSIpLjYyKClbOjMyXQoJCTE1ID0gNWUKCQk2ODoKCQkJOWYgPSAxYS45MygzOCwgNGQ9MTApCgkJCWIgOWYuMmMgPT0gMWEuNjQuNmQ6CgkJCQkxNSA9IDlmLmExLmIyKCdjZScsICdiOScpWzozMl0uYmQoJ2U1LTgnKQoJCTM1OgoJCQk5ZAoKCQliIDNjIDU1IDE1IDU1IDNjID09IDE1OgoJCQkxMi4zYigoIlslNWNdIDJmIGFlIDczOiAiICUgMTMpICsgMmQpCgkJCWU5CgkJZS5mMigoNyg5MCkrIltiYV0uLi4lNWMiKSAlIGRmKQoJCSMgNmIuN2UoNzQsIDE0LCAoNyg5MCkrIi4uLiU1YyIpICUgZGYpCgkJNWQgZTAuM2EoYTIsImVkIikgOWMgZjoKCQkJNjg6CgkJCQk5ZiA9IDFhLjkzKDJkLCBiNj0zMCwgYjQ9NjcsIDRkPTIwKQoJCQkJYiA5Zi4yYyA9PSAxYS42NC42ZDoKCQkJCQk1MCA9IDE2ICogZDMKCQkJCQk3OCA4ZiA0OCA5Zi43Yig1MCk6CgkJCQkJCWYuNjMoOGYpCgkJCQkJZjMuNTkoMmQpCgkJCQk0MzoKCQkJCQkxMi4zYigoIlslNWNdIDI5IDg1IDJmOiAiICUgMTMpICsgMmQpCgkJCQkJZTAuMWUoYTIpCgkJCQkJZTkKCQkJMzU6CgkJCQkxMi4zYigoIlslNWNdIDI5IDg1IDJmOiAiICUgMTMpICsgMmQpCgkJCQllMC4xZShhMikKCQkJCWU5CgkJNGMgPSBhYyhhMikKCgkJYiAxNSA1NSA0YyAhPSAxNToKCQkJMTIuM2IoKCJbJTVjXSAyOSBkOTogIiAlIDEzKSArIDJkKQoJCQllOQoKCQliIDRhLjFkLjM0KDJlKToKCQkJMjIgPSBlMC4xZSgyZSkKCQkJYiA1YSAyMjoKCQkJCTEyLjNiKCgiWyU1Y10gMjkgODUgN2M6ICIgJSAxMykgKyAyZSkKCQkJCWU5CgoJCTIyID0gZTAuYjcoYTIsMmUpCgkJYiA1YSAyMjoKCQkJMTIuM2IoKCJbJTVjXSAyOSA4NSBiZjogIiAlIDEzKSArIDJlKQoJCQllMC4xZShhMikKCQkJZTkKCgkJNWQgZTAuM2EoMTgsImVlIikgOWMgYToKCQkJYS42Myg0YykKCQk4MiA9IGUwLjNhKDJlLCJiMSIpLjYyKDQpCgkJYiA4MiA9PSAiXGRjXGRiXGUxXGUyIjoKCQkJNmIuNzkoMTQsIDcoY2IpKyJbODYgOTddIitkZisiWy84Nl0iKQoJCQlhYi42NSgyZSwgZWIsIDZiKQoJCQllLmYyKCgiJTVjLi4uW2JhXSIrNyg4OCkpICUgZGYpCgkJCTZiLjkxKCkKCQkJYiAiMjYuYjUiIDQ4IDJlOgoJCQkJMWIgPSAzMAoJCQkJM2QgPSAzMAoJCQkjIDZiLjdlKDc0LCAxNCwgKCIlNWMuLi4iKzcoODgpKSAlIGRmKQoJCQkjIDEyLjgzKGRlKQoJCQliIDRhLjFkLjM0KDJlKToKCQkJCTIyID0gZTAuMWUoMmUpCgkJCQliIDVhIDIyOgoJCQkJCTEyLjNiKCgiWyU1Y10gMjkgODUgN2MgZTQ6ICIgJSAxMykgKyAyZSkKCTEyLjNiKCJbJTVjXSBhOCAlNWMiICUgKDEzLCBkZikpCgliIDFiOgoJCTI1LjI0KCc0MCcsICcwLjAuMCcpCgkJMjYoMzEsIDMwLCAzMCwgYzApCgliIDNkIDhlIGVhID09ICcwLjAuMCc6CgkJMjUuMjQoJzRiJywgJzAuMC4wJykKCQliYygzMSwgMzAsIGMwKQoJYiA3MShmMykgPiAwOgoJCWUuZjIoNyhjNikgJSBlNyg3MShmMykpKQoJCTdmLjZlKDksIDEsIDMwKQoJCTEyLjFmKCcyYigpJykKCQliIDIxLmQoMyk6CgkJCTUzLjQ3KCkKCQkyOCA9IDlhLmM3KCczOS5kMCcpCgkJNDkgPSBlMC4xOSgyOC4zZignMWQnKSkKCQliMyA9IDRhLjFkLjRmKDQ5LCAnMjUuNjYnKQoJCTc4IGVmIDQ4IGYzOgoJCQliIGVmLmE2KCcxYy45OCcpOgoJCQkJMjUuMjQoJzM2JywgJzAuMC4wJykKCQkJCTZmKDQxKQoJCQkJYiAyMS5kKDMpOgoJCQkJCTUzLjQ3KCkKCQkJCTVkIGUwLjNhKGIzLCAnOWYnKSA5YyA1NzoKCQkJCQk2NiA9IDU3LjYyKCkKCQkJCQk2NiA9IDY2LmE5KCczOT0iJTVjIicgJSAyOC4zZignMzknKSwgJzM5PSIlNWMiJyAlIGMwKQoJCQkJNWQgZTAuM2EoYjMsICdlZCcpIDljIDU2OgoJCQkJCTU2LjYzKDY2KQoJCQkJYiAyMS5kKDEpOgoJCQkJCTUzLjQ3KCkKCQkJCTI1LjI0KCczNicsIGMwKQoJCQkJMjcgPSA0YS4xZC40Zig1YiwgIjFjLjk4IikKCQkJCTEyLjFmKCcyYigpJykKCQkJCWMyICgxMi4yYSgiNzcuNTQoODApIikgOGUgMTIuMmEoIjc3LjU0KGE1KSIpKToKCQkJCQkxMi44MyhlMykKCQkJCWIgNGEuMWQuMzQoMjcpOgoJCQkJCTZkID0gNmMuNzYoKS42ZCgxNCwgNyg4NykrIltiYV0iKzcoY2EpKQoJCQkJCWIgNmQ6CgkJCQkJCThkKDI3KQoJCQkJNDM6CgkJCQkJNmMuNzYoKS42ZCgxNCwgNyg4NykpCgkJCQllLmYyKDcoY2QpICUgYzAsIGJlPTIpCgk0MzoKCQllLmYyKDcoYzEpLCBiZT0yKQoJIyA2Yi45MSgpCgkjIGUuZjIoNyhjOCkpCgkjIGUuZjIoNyhjNSkpCgkKCWIgNGEuMWQuMzQoZTAuMTkoJzZhOi8vOWUvNWYvNjAuZDQnKSk6CgkJYiAyMS5kKDAuNSk6CgkJCTUzLjQ3KCkKCQkxMi4xZignOTkoNmE6Ly85ZS81Zi82MC5kNCknKQoJYiAyMS5kKDAuNSk6CgkJNTMuNDcoKQoJZS5mMig3KGQxKSkKCTcwIDMw|os|or|getCondVisibility|old_mainxmlsver|dp|p|py|wb|md5_local_linkfilename|s|lambda|_|local_temp_filename|100|w|t|x".split("|")))

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

