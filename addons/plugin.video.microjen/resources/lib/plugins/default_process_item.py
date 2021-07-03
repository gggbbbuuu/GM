from resources.lib.plugins.summary import Summary
from ..plugin import Plugin
import xbmcgui, xbmc

import urllib.parse
try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *
    
class default_process_item(Plugin):
    name = "default process item"
    priority = 0

    def process_item(self, item):
        do_log('do_log - ' + self.name + ' - Item \n' + str(item))  
        is_dir = False
        tag = item["type"]
        link = item.get("link", "")
        summary = item.get("summary")
        if summary:
            del item["summary"]
        if link:
            if tag == "dir":
                link = f"/get_list/{link}"
                is_dir = True
                
            if tag == "plugin":   
                plug_item = urllib.parse.quote_plus(str(link))  
                if 'youtube' in plug_item:
                    link = f"/get_list/{link}"
                    is_dir = True
                else :
                    link = f"/run_plug/{plug_item}"                 
                    is_dir = False
                
        if tag == "item":
            link_item = urllib.parse.quote_plus(str(item))      
            
            if str(link).lower() == 'settings' :
                link = f"settings/{link}"        
            
            elif str(link).lower().startswith("message/") :   
                link = f"show_message/{link}" 
                               
            else :     
                link = f"play_video/{link_item}"
                        
        thumbnail = item.get("thumbnail", "")
        fanart = item.get("fanart", "")
        list_item = xbmcgui.ListItem(
            item.get("title", item.get("name", "")), offscreen=True
        )
        list_item.setArt({"thumb": thumbnail, "fanart": fanart})
        item["list_item"] = list_item
        item["link"] = link
        item["is_dir"] = is_dir
        if summary:
            item["summary"] = summary
        return item
