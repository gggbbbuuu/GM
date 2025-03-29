#encoding=utf-8
import sys
import xbmcgui
import xbmcplugin
import xbmc
import xbmcvfs
import xbmcaddon
import os
import json
import urllib.request as urllib2
from urllib.parse import parse_qs, urlencode

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = parse_qs(sys.argv[2][1:])
my_addon = xbmcaddon.Addon()
PATH = my_addon.getAddonInfo('path')
def build_url(query):
    return base_url + '?' + urlencode(query)
mode = args.get('mode', None)
headers = { 'User-Agent' : 'Mozilla/5.0' }
req = urllib2.Request("http://bit.ly/YOYTAPIS")
req.add_header('User-Agent', 'Mozilla/5.0')
response = urllib2.urlopen(req)
link=response.read().decode('utf-8').replace('\r', '').replace('\n', '').replace('\t', '').replace(' ','').replace('},]','}]')
response.close()

if mode[0] == 'ytapichange':
    keys = sorted(json.loads(link),key=lambda i:i['n'],reverse=False)
    for key in keys:
        url = build_url({'mode': 'change_the_fucking_key', 'n': key['n'], 'key': key['key'], 'id': key['id'],'secret': key['secret']})
        li = xbmcgui.ListItem('API κλειδί ' + str(key['n']))
        li.setInfo(type="Video", infoLabels={"plot": 'Αλλαγή κλειδιού API Youtube'})
        li.setArt({'fanart': PATH + '/fanart.jpg', 'icon' : PATH + '/icon.png', 'thumb' : PATH + '/icon.png' })
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)
elif mode[0] == 'change_the_fucking_key':
    HOME = xbmcvfs.translatePath('special://home/')
    USERDATA = os.path.join(HOME, 'userdata')
    ADDON_DATA = os.path.join(USERDATA, 'addon_data')
    YOUTUBE = os.path.join(ADDON_DATA, 'plugin.video.youtube')
    SETTINGS_FILE = os.path.join(YOUTUBE, 'settings.xml')
    if os.path.isfile(SETTINGS_FILE) == True:
        f = xbmcvfs.File(SETTINGS_FILE)
        contenido = f.read()
        f.close()
        funcionando = 0
        keys = sorted(json.loads(link),key=lambda i:i['n'],reverse=False)
        key_num = int(args['n'][0])
        total_keys = len(keys)
        DIALOG_PROGRESS = xbmcgui.DialogProgress()
        DIALOG_PROGRESS.create("Δοκιμή διαθέσιμων κλειδιών API Youtube", "")
        WINDOW_PROGRESS = xbmcgui.Window(10101)
        xbmc.sleep(100)
        CANCEL_BUTTON = WINDOW_PROGRESS.getControl(10)
        for x in range(key_num, total_keys+1):
            if DIALOG_PROGRESS.iscanceled():
                DIALOG_PROGRESS.close()
                break
            xbmc.sleep(500)
            DIALOG_PROGRESS.update(int((x)*100/total_keys), "[B]Έλεγχος κατάστασης κλειδιού " + str(keys[x-1]['n']) + " ...[/B]")
            try:
                test = urllib2.urlopen(urllib2.Request("https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=UCUV33rOY6Cmu1OptrDYLr7w&maxResults=50&key=" + keys[x-1]['key']),timeout=60).read().decode(encoding='UTF-8')
            except:
                test = ''
            if '"kind"' in test:
                funcionando = 1
                xbmcaddon.Addon('plugin.video.youtube').setSetting('youtube.api.enable', 'true')
                xbmcaddon.Addon('plugin.video.youtube').setSetting('youtube.api.key', keys[x-1]['key'])
                xbmcaddon.Addon('plugin.video.youtube').setSetting('youtube.api.id', keys[x-1]['id'])
                xbmcaddon.Addon('plugin.video.youtube').setSetting('youtube.api.secret', keys[x-1]['secret'])
                DIALOG_PROGRESS.close()
                xbmc.executebuiltin('Notification(%s, %s, %s, %s)' % ('API κλειδί ΟΚ!', 'Το κλειδί API άλλαξε σε ' + str(x), 4000, PATH + '/icon.png'))
                break
            else:
                xbmc.sleep(500)
        DIALOG_PROGRESS.close()
        if funcionando == 0:
            xbmc.executebuiltin('Notification(%s, %s, %s, %s)' % ('Πρόβλημα', 'Το κλειδί API δεν λειτουργεί...', 4000, PATH + '/icon.png'))
    else:
        xbmc.executebuiltin('Notification(%s, %s, %s, %s)' % ('Πρόβλημα', 'Αδυναμία αλλαγής κλειδιού', 4000, PATH + '/icon.png'))