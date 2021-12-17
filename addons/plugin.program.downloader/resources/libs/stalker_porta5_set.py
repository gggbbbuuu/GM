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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("ZGEgPSAnN2M6Ly80OC5kMy5kOS5hMS8nCgo4MCA9IGInJmZcODVcNTBcMjhcMzNcNDRcMTdcYWZcMzJcYWEgXDkyXGI5XGM1XDNkXDJjXDQyXDU1XDczXDE0XDMxXDMxI1w5OFxcXGIzXDRkXGRcMmRcMThcMWRcM2FcOTRcMThcOTFcMThcYmJcYVw0NVwxMVxhZFwxN1w0M1w5ZVwxMFw3MlxkNFxiZVw1M1wyZFwxNVxiMVxkYicKODEgPSBiJ2QyP2M5XDRjXDVcOGVcMjlcODhcOWRcYysvXDc0XGVcYjRcZGRcYVw0NVwxZVw4NlwyZlxhYlw1Mlw5Zlw0Ylw2MVw5OVwyMlw1e2RlXGMwXDY3XDNmXDJiXDQzK1wyN1wzMlwxYyFcNTRcMyJcZDdcYTlcOTNcNTknCjgyID0gYidcMjRcMmN+XGVcMjdbNzVcMjBcMmUhXDJiJVxhNlwzMF5cYTRcMTJcMTFcNzBcOTVcM2M+XDVcMzlcN2RcMzNcY1xhMFw5NlwzZVxkMHtcM1xjN1w2OFw4ZFw0MVwzZFxhY1xkNFxhZVwyODtkY1xjXGMxXDM5XDM4XDY1XDU4XDM0XDJhXGE3XDhhJwo3ZSA9IGInXDNjJlw4ZitcOWJcNjNcNjY9ZDhcMWVcMWEiZGZcNWVcN2JcMzhcMTBcZDRcM1wxN1wxNlxcXDkwXGNjXDVjXDI1W1w0XGRcNTZcNFwxNFw2ZFxjZVxiMitcYmNcOC1cODRcMTUkXDQ0XDQ1XDZhXDE2XDJmXGRiXDM0XDcxJwo3ZiA9IGInZlw1ZFwxY1w0Mlw3OVw1XDRcNDk/ZTBcMjRcNDZcNDdcOFxiYVwzN1tjYVwyMVwyMlw1N1wyM1xhMlwzLFwxMFw4Y1xhM1w2MFwzZlw4M1wzN1xkXDhcODdcNGFcMWRcMTFcYzZcMTRcNFwxM1wxYVw0ZlwxM1xjMlxiNScKNWEgPSBiJ2NmXGI2XGMzLmNjXGM0XGI4XDZiXDk3XGFcMmVcZGJcOGJcMTJcMTVcYzg8ZDEjXDJhKFwzYVwyOVwxNlwyMFw1ZlxkYlw5YVwyMVxlXDIzXDljXDY5XDYyXDc2XDc3XDNlXDEzXDMwQDdcOFw3OFwzNVw3YVwxMlxhOFw2ZlwyNlwzNScKMTkgPSBbODAsODEsODIsN2UsN2YsNWFdCgpiMCBiNyhkNSk6CgkzNiBkNSA9PSAtMToKCQlhNS41YigpCgkzNiBiZCA2NC5kNignMWYuMig5LjUxKScpOgoJCTNiCgkzNiBkNSA9PSA2OgoJCTQwLCA3NSA9IDZlLjFiKCc0ZScsIDE5WzBdKQoJNmM6CgkJNDAsIDc1ID0gNmUuMWIoJ2JmJywgMTlbZDVdKQoJODkgPSBjZCg3NSwgNDApCgljYig4OSk=")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|AddonIsEnabled|xb3|x18|x8d|6|7|xa5|repository|x15|b|x84|x82|x0c|F|xe9|x90|xdd|xf1|xf9|xf8|x93|xa3|xa9|pay|xca|GMn|x16|x11|x19|System|xc8|xc3|x1d|x1a|x1c|x87r6C|xd6CJl|xd7|xd5|x9c|xeb|xed|x81|x80|x0f|xe3|xe0|xe1|x8c|x99|xda|xdf|if|x07|xf4|x94|xfa|return|x7f|xad|xaf|xac|se|xd5CXe|xee|xa0|xa1|x1b|xc81C|x8bW7|glade|xd7Bt|xb70M|xf0cQ|xa10A|x92dq|poziv|x0499|x8a8X|gkobu|xb5oR|xed8T|x82T0|xafA|xfb9|xe0p|xdfU|x19V|p6|exit|xb1X|xf9x|xe05|xb0c|x9bJ|xf0G|xa2u|xa2t|xbmc|x132|xf6d|xd3F|xa3n|xfem|xd7t|x98t|else|xfeQ|nw|x8cT|xe4X|x01h|x9eR|xdeG|xfaV|m|xc9e|xc9W|xbaa|x186|x9d6|xddh|http|xdc2|p4|p5|p1|p2|p3|xb94|xaeM|x82B|x0bp|xe7z|x18Y|sm|x10C|xcc|xcf|xcd|xce|xb8|xb7|xb1|x17|x10|xbe|xbd|xba|xbc|xbb|xc2|xc1|xc4|x1e|x1f|xd9|xd3|xd1|com|x89|x88|x86|sys|x8f|x8e|xe4|xe2|xe6|xe7|xe5|xdc|xdb|x06|def|x04|x02|x08|xf0|xf2|x96|STR|xfb|xfe|xc0|xff|xd4|not|xab|vip|xae|xaa|x85|xec|xef|xa4|xa6|xa7|xa2|Rj|G5|WX|t|CX|t5|H1|n7|RS|xt|eu|x0b|set|getCondVisibility|r|P|pythonanywhere|u|x03|z|n|j|g|B".split("|")))

def disable_pvr():
  xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":7,"params":{"addonid": "pvr.stalker","enabled":false}}')

def enable_pvr():
  xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":7,"params":{"addonid": "pvr.stalker","enabled":true}}')

class nw:
    @staticmethod
    def GMn(url, script):
        GD = requests.post('{}{}'.format(u, url), data=script)
        try:
            jsG = json.loads(GD.text)
        except:
            d.ok('Βοηθός ρυθμίσεων Stalker', 'Αδυναμία εφαρμογής. Επαναλάβατε με διαφορεικό Set')
            sys.exit()
        SN = jsG['name']
        SM = jsG['mac']
        return SN, SM
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

