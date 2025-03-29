from ..plugin import Plugin
from xbmcplugin import addDirectoryItems, endOfDirectory, setContent
from ..DI import DI
import sys

route_plugin = DI.plugin


class display(Plugin):
    name = "display"

    def display_list(self, jen_list):
        display_list2=[]
        for item in jen_list:
            link = item["link"]
            list_item = item["list_item"]
            if item.get('is_playable'):
                list_item.setProperty('IsPlayable', 'true')
            is_dir = item["is_dir"]
            display_list2 .append((route_plugin.url_for_path(link), list_item, is_dir))
        try:
            mediatype=item.get("mediatype","videos")
        except:
            mediatype="videos"
        if mediatype=="movie":
            mediatype="movies"
        addDirectoryItems(route_plugin.handle, display_list2, len(display_list2))
        setContent(int(sys.argv[1]), mediatype) 
        endOfDirectory(route_plugin.handle)
        return True
