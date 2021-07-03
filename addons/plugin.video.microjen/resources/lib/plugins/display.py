from ..plugin import Plugin
from xbmcplugin import addDirectoryItem, endOfDirectory, setContent
from ..DI import DI
import sys

route_plugin = DI.plugin


class display(Plugin):
    name = "display"

    def display_list(self, jen_list):
        for item in jen_list:
            item = item
            link = item["link"]
            list_item = item["list_item"]
            is_dir = item["is_dir"]
            addDirectoryItem(
                route_plugin.handle, route_plugin.url_for_path(link), list_item, is_dir
            )
        setContent(int(sys.argv[1]), 'videos') 
        endOfDirectory(route_plugin.handle)
        return True
