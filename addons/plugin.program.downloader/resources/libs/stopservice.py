# -*- coding: utf-8 -*-
import re, os, glob
import xbmcvfs, xbmc, xbmcgui
from contextlib import contextmanager
HOME = xbmcvfs.translatePath('special://home/')
ADDONS = os.path.join(HOME, 'addons')
@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

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

def StopAllRunning():
    addonlist = glob.glob(os.path.join(ADDONS, '*/'))
    serviceAddons = 0
    for folder in sorted(addonlist, key = lambda x: x):
        addonxml = os.path.join(folder, 'addon.xml')
        if os.path.exists(addonxml):
            f        = xbmcvfs.File(addonxml, 'r')
            b        = f.read()
            tid      = parseDOM(b, 'addon', ret='id')
            tname    = parseDOM(b, 'addon', ret='name')
            tservice = parseDOM(b, 'extension', ret='library', attrs = {'point': 'xbmc.service'})
            try:
                if len(tid) > 0:
                    addonid = tid[0]
                if len(tservice) > 0:
                    if "/" in tservice[0]:
                        servicepath = tservice[0].split("/")
                        servicepath = os.path.join(*servicepath)
                    else:
                        servicepath = tservice[0]
                    xbmc.executebuiltin('StopScript(%s)' % os.path.join(ADDONS, addonid))
                    xbmc.executebuiltin('StopScript(%s)' % addonid)
                    xbmc.executebuiltin('StopScript(%s)' % os.path.join(ADDONS, addonid, servicepath))
                    paths = os.path.join(ADDONS, addonid, servicepath)
                    xbmc.sleep(100)
                    serviceAddons += 1
            except:
                pass
    xbmcgui.Dialog().notification("GKoBu Tools", "Όλες οι υπηρεσίες τερματίστηκαν", xbmcgui.NOTIFICATION_INFO, 5000, False)

with busy_dialog():
    StopAllRunning()

