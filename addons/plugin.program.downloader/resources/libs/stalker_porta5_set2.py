import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
import requests
import json
import xml.etree.ElementTree as ET
import time
__addon__ = xbmcaddon.Addon(id='pvr.stalker')
__addondir__ = xbmcvfs.translatePath( __addon__.getAddonInfo('profile') )
pth = os.path.join(__addondir__, 'settings.xml')
pDialog = xbmcgui.DialogProgress()
d = xbmcgui.Dialog()
portals = ['Set 1', 'Set 2', 'Set 3' , 'Set 4', 'Set 5', 'Set 6', 'Set 7']
p = d.select('Επιλέξτε Set', portals)

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("NiA9ICcxZTovL2EuOS4yOScKCjE1IDI4KGUpOgoJMWEgZSA9PSAtMToKCQkxOC4xMygpCgkxYSAyZCAyMC41KCcxNy5iKDExLjFjKScpOgoJCWMKCTFhIGUgPT0gMDoKCQkxNiwgMjcgPSAzKCcxZicsIDEpCgkyNToKCQkxNiwgMjcgPSAzKCcyYicsIGUpCgkyNCA9IDJlKDI3LCAxNikKCTMwKDI0KQoKMTUgMyhmLCA4KToKCQkyZiA9IHt9CgkJMmZbJ2YnXSA9IGYKCQkyZlsnMjEnXSA9IDgKCQk3ID0gMTIuMjMoNiArICcvMTQnLCBkPWQuMWIoMmYpKQoJCTJjOgoJCQkzMSA9IGQuMWQoNy4yNikKCQkxOToKCQkJMTAoKQoJCQkxOC4xMygpCgkJMiA9IDMxWycyMiddCgkJNCA9IDMxWycyYSddCgkJYyAyLCA0")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|server_name|get_s_m|server_mac|getCondVisibility|BASE_URL|response|list_nmb|pythonanywhere|ztbhmiddleware|AddonIsEnabled|return|json|set|mode|falsenotify|repository|requests|exit|client|def|se|System|sys|except|if|dumps|gkobu|loads|http|free|xbmc|list|name|post|sm|else|text|m|STR|com|mac|vip|try|not|CX|payload|WX|response_json".split("|")))

def falsenotify():
    d.ok('Βοηθός ρυθμίσεων Stalker', 'Αδυναμία εφαρμογής. Επαναλάβατε με διαφορεικό Set')

def disable_pvr():
  xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":7,"params":{"addonid": "pvr.stalker","enabled":false}}')

def enable_pvr():
  xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":7,"params":{"addonid": "pvr.stalker","enabled":true}}')

def CX(m, u):
    P = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(pth, parser=P)
    root = tree.getroot()
    for setting in root:
        if setting.attrib['id'] == 'active_portal':
            setting.text = '4'
        if setting.attrib['id'] == 'mac_4':
            setting.text = m
        if setting.attrib['id'] == 'server_4':
            setting.text = u
    new_xml = ET.tostring(root, encoding='utf-8')
    return new_xml
def WX(mod):
    with xbmcvfs.File(pth, 'w') as f:
        f.write(mod)

STR(p)
pDialog.create('Βοηθός ρυθμίσεων Stalker', '')
pDialog.update(0, "Επιλογή και άλλαγή ρυθμίσεων σε Πύλη 5")
xbmc.sleep(1000)
pDialog.update(50, "Οι ρυθμίσεις στην Πύλη 5 του Stalker ενημερώθηκαν")
xbmc.sleep(1000)
pDialog.update(100, 'O Πελάτης PVR Client ενημερώθηκε')
xbmc.sleep(2000)
disable_pvr()
pDialog.close()
d.ok('Βοηθός ρυθμίσεων Stalker', 'Σε περίπτωση που δεν λειτουργούν τα κανάλια,[CR]επαναλάβατε με το ίδιο ή διαφορεικό Set')
enable_pvr()
xbmc.sleep(1000)
xbmc.executebuiltin('Dialog.Close(all, true)')
xbmc.executebuiltin('ActivateWindow(10700)')
xbmc.executebuiltin('Container.Refresh')

