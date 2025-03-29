from ..plugin import Plugin
from xbmcplugin import addDirectoryItem, endOfDirectory,setContent
from ..DI import DI
import sys
import urllib.parse

route_plugin = DI.plugin


class display(Plugin):
    name = "display"

    def display_list(self, jen_list):
        for item in jen_list:
            item = item
            link = item["link"]
            list_item = item["list_item"]
            is_dir = item["is_dir"]
            if link.startswith('plugin://'):
              addDirectoryItem(
                route_plugin.handle, link, list_item, is_dir
            )
            else:
                addDirectoryItem(
                route_plugin.handle, route_plugin.url_for_path(link), list_item, is_dir
            )
        setContent(int(sys.argv[1]), 'files') 
        endOfDirectory(route_plugin.handle)
        return True
