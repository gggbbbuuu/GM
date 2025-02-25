from ..plugin import Plugin
import xbmcgui
import urllib.parse


class default_process_item(Plugin):
    name = "default process item"
    priority = 0

    def process_item(self, item):
        is_dir = False
        tag = item["type"]
        link = item.get("link", "")
        if link:
            if tag == "dir":
                link = f"/get_list/{link}"
                is_dir = True
        if tag == "item":
            link_item = urllib.parse.quote_plus(str(item))
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
        return item
