from resources.lib.plugins.summary import Summary
from ..plugin import Plugin
import xbmcgui
import base64
import json

import urllib.parse
try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

import xbmcaddon
addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')
default_fanart = xbmcaddon.Addon(addon_id).getAddonInfo('fanart')
    
class default_process_item(Plugin):
    name = "default process item"
    priority = 0

    def process_item(self, item):
        do_log(f'{self.name} - Item = \n {str(item)} ' )  
        is_dir = False
        tag = item["type"]
        link = item.get("link", "")
        summary = item.get("summary")
        context = item.get("contextmenu")
        imdb = item.get("imdb")
        content = item.get("content")
        # if summary:
            # del item["summary"]
        if context:
            del item["contextmenu"]
        if link:
            # if tag == "dir" and link.endswith('.m3u'):
                # import requests, xbmcvfs
                # m3ucontent = requests.get(link, timeout=10)
                # m3ufile = '.'.join(link.split("/")[3:])#.replace('https:..','').replace('http:..','')
                # m3upath = xbmcvfs.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'xml', m3ufile))
                # if m3ucontent.status_code == requests.codes.ok:
                    # m3ucontent = m3ucontent.text
                    # with xbmcvfs.File(m3upath, 'w') as f:
                        # f.write(m3ucontent)
                    # link = f"file://{m3ufile}"
            if tag == "f4m":
                if link.endswith('.m3u'):
                    link = f"plugin.video.f4mTester/?mode=playlist&name=IPTV&url={link}.templink?"
                    link = urllib.parse.quote_plus(str(link))
                    link = f"/run_plug/{link}"
                elif link.endswith('.m3u_plus'):
                    link = f"plugin.video.f4mTester/?mode=playlist&name=IPTV&url={link}?"
                    link = urllib.parse.quote_plus(str(link))
                    link = f"/run_plug/{link}"
            if tag == "dir":
                if link.endswith('.xml'):
                    link = link+'l'
                elif link.endswith(".m3u") or link.endswith(".m3u8"):
                    link = f"m3u|{link}"
                link = f"/get_list/{link}"
                is_dir = True
                
            if tag == "plugin":
                plug_item = urllib.parse.quote_plus(str(link))
                if 'plugin.video.youtube' in plug_item and 'playlist' in plug_item and 'channel' in plug_item:
                    link = f"/run_plug/{plug_item}"
                    is_dir = False
                elif 'youtube' in plug_item:
                    link = f"/get_list/{link}"
                    is_dir = True
                elif 'module.bolt/' in link:
                    if "mode=play" in link:
                        tag = "item"
                        is_dir = False
                    else:
                        link = link.split('module.bolt/')[1]
                        link = f"/daddylive{link}"
                        is_dir = True
                elif 'plugin.video.duffyou' in link and ('playlist' in link or 'channel' in link):
                    if 'channel_playlists/' in link:
                        action = 'ioiIii1II'
                        id = link.split('channel_playlists/')[1]
                    elif 'playlist/' in link:
                        action = 'io1i1I1'
                        id = link.split('playlist/')[1]
                    elif 'channel/' in link:
                        action = 'oio0O00OO'
                        id = link.split('channel/')[1]
                    if id.endswith('/'):
                        id = id[:-1]
                    icon = item.get("thumbnail", default_icon)
                    fanart = item.get("fanart", default_fanart)
                    dufflink = "{'action': '%s', 'id': '%s', 'icon': '%s', 'fanart': '%s'}" % (action,id,icon,fanart)
                    link = "plugin://plugin.video.duffyou/?" + base64.b64encode(dufflink.encode('utf-8')).decode('utf-8')
                    link = urllib.parse.quote_plus(str(link))
                    link = f"/run_plug/{link}"
                    is_dir = False
                else :
                    link = f"/run_plug/{plug_item}"
                    is_dir = False
            if tag == "script":
                script_item = urllib.parse.quote_plus(str(link))
                link = f"/run_script/{script_item}"
                is_dir = False 
        if tag == "item":
            link_item = base64.urlsafe_b64encode(bytes(json.dumps(item), 'utf-8')).decode("utf-8")
            
            if str(link).lower() == 'settings' :
                link = "settings"
            elif str(link).lower() == "clear_cache":
                link = "clear_cache"
                
            elif str(link).lower() == "clear_cache_silent":
                link = "clear_cache_silent"
                
            elif str(link).lower() == "refresh_menu":
                link = "refresh_menu"
            elif str(link).lower() == "daddylive":
                link = "daddylive"
                is_dir = True
            elif str(link).lower() == "sporthd":
                link = "sporthd"
                is_dir = True
            elif str(link).lower() == "streamed":
                link = "streamed"
                is_dir = True
            elif str(link).lower().startswith("message/") :   
                link = f"show_message/{link}"
            else :     
                link = f"play_video/{link_item}"
                        
        # thumbnail = item.get("thumbnail", "")
        # fanart = item.get("fanart", "")
                        
        thumbnail = item.get("thumbnail", default_icon)
        fanart = item.get("fanart", default_fanart)
        list_item = xbmcgui.ListItem(
            item.get("title", item.get("name", "")), offscreen=True
        )
        list_item.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail, "fanart": fanart})
        item["list_item"] = list_item
        item["link"] = link
        item["is_dir"] = is_dir
        if summary:
            item["summary"] = summary
        if context:
            item["contextmenu"] = context
        if item.get("infolabels"):
            list_item.setInfo("video", item["infolabels"])
        if content and not is_dir:
            list_item.setInfo("video", {"mediatype": content, "plot": summary, "imdbnumber": imdb})
            list_item.setUniqueIDs({ 'imdb': imdb }, "imdb")
        elif summary and not is_dir:
            list_item.setInfo("video", {"mediatype": "movie", "plot": summary, "imdbnumber": imdb})
            list_item.setUniqueIDs({ 'imdb': imdb }, "imdb")
        elif summary:
            list_item.setInfo("video", {"plot": summary})
        '''if item.get("infolabels"):
            list_item.setInfo("video", infoLabels=item['infolabels'])
        if item.get("cast"):
            list_item.setCast(item['cast'])'''
        return item
