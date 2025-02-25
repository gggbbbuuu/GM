"""Autoruns - fightnight's initial work - GKoBu made it for Matrix"""

import xbmc, xbmcvfs, xbmcaddon, xbmcgui, xbmcplugin, os, re, sys
from urllib.parse import quote_plus, unquote_plus

def list_addons():
    #info directory
    addDir('[COLOR blue][B]%s[/B][/COLOR]' % (translate(30001)),'None',None,os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')),'icon.png'))

    #get the path of addons
    pathofaddons = xbmcvfs.translatePath('special://home/addons')

    #list with addons
    listofaddons = os.listdir(pathofaddons)
    addonDirs = []
    for individual_addon in listofaddons:
        #path to individual addon, cycle for all the addons
        path_to_addon = os.path.join(pathofaddons, individual_addon)

        #define addon.xml path
        addon_xml_path=os.path.join(path_to_addon,'addon.xml')

        if os.path.exists(addon_xml_path):
            resetOldVersion(addon_xml_path)
            with xbmcvfs.File(addon_xml_path, 'r') as f:# get addon.xml content
                b        = f.read()
                tservice = parseDOM(b, 'extension', ret='library', attrs = {'point': 'xbmc.service'})
            if len(tservice) > 0:
                servicepath = path_to_addon+'|'+tservice[0]
            else:
                continue
            addon = xbmcaddon.Addon(individual_addon)
            ticon = addon.getAddonInfo('icon')
            tnameorig = addon.getAddonInfo('name')
            tname = re.sub("[\[].*?[\]]", "", tnameorig)
            tname = re.sub("^\s+", "", tname)
            tname = re.sub("^\W+", "", tname)
            if not servicepath.endswith("disabled"):
                tnameorig = tnameorig+' [B][COLOR lime](Enabled)[/COLOR][/B]'
            else:
                tnameorig = tnameorig+' [B][COLOR gold](Disabled)[/COLOR][/B]'
            addoninfo = [tname, servicepath, path_to_addon, ticon, tnameorig]
            addonDirs.append(addoninfo)
    addonDirs.sort(key=lambda x: x[0].lower())
    for dir in addonDirs:
        addDir(dir[4], dir[1],1,os.path.join(dir[2],dir[3]))

             

def change_state(name,path):
        
    #define addon.xml path to change
    addon_xml_path=os.path.join(path.split("|")[0],'addon.xml')
    service = path.split("|")[1]
    try:
        realservice = service.split(".disabled")[0]
    except:
        realservice = service

    #get addon.xml content
    content=openfile(addon_xml_path)

    if re.search('\(Disabled\)',name):
        #service off to on, so we change from fake variable to service variable
        content=content.replace('library="%s"' % service,'library="%s"' % realservice)
    else:
        #service on to off, so we change from service variable to fake variable
        content=content.replace('library="%s"' % realservice,'library="%s.disabled"' % realservice)

    #change state on addon.xml
    savefile(addon_xml_path,content)

    #refresh the list
    xbmc.executebuiltin("Container.Refresh")
    xbmc.executebuiltin("UpdateLocalAddons()")
      

def openfile(path_to_the_file):
    try:
        with xbmcvfs.File(path_to_the_file, 'r') as fh:
            contents=fh.read()
        return contents
    except:
        xbmc.log("Wont open: %s" % path_to_the_file, xbmc.LOGINFO)
        return None

def savefile(path_to_the_file,content):
    try:
        with xbmcvfs.File(path_to_the_file, 'w') as fh:
            fh.write(content)  
    except:
        xbmc.log("Wont save: %s" % path_to_the_file, xbmc.LOGINFO)

def addDir(name,path,mode,iconimage):
      listitem = xbmcgui.ListItem(name)
      listitem.setArt({'thumb': iconimage, 'icon': iconimage})
      return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url="%s?path=%s&mode=%s&name=%s" % (sys.argv[0],quote_plus(path),mode,quote_plus(name)),listitem=listitem,isFolder=False)

def get_params():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
              params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
              splitparams={}
              splitparams=pairsofparams[i].split('=')
              if (len(splitparams))==2:
                    param[splitparams[0]]=splitparams[1]                 
    return param

def translate(text):
    return xbmcaddon.Addon().getLocalizedString(text)

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

def resetOldVersion(xml_path):
    off_pattern = '(<!--<extension.+?xbmc.service.+?>-->)'
    on_pattern = '(<extension.+?xbmc.service.+?>)'
    addonxml_content = openfile(xml_path)
    off_check = re.search(off_pattern, addonxml_content)
    if not off_check == None:
        on_match = re.findall(on_pattern, addonxml_content)[0]
        off_match = re.findall(off_pattern, addonxml_content)[0]
        addonxml_content = addonxml_content.replace(off_match, on_match)
        savefile(xml_path, addonxml_content)
    
params=get_params()
path=None
name=None
mode=None

try: path=unquote_plus(params["path"])
except: pass
try: name=unquote_plus(params["name"])
except: pass
try: mode=int(params["mode"])
except: pass

if mode==None: list_addons()
elif mode==1: change_state(name,path)
                       
xbmcplugin.endOfDirectory(int(sys.argv[1]))