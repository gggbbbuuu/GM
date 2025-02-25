from ..plugin import Plugin
import xbmc, xbmcgui, xbmcaddon
import json, re
import resolveurl

addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')
playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

class default_play_video(Plugin):
    name = "default video playback"
    priority = 0
    
    def play_video(self, item):
        item = json.loads(item)
        link = item.get("link", "")
        if link == "":
            return False
        # title = item["title"]
        title = clean_title(item["title"])
        thumbnail = item.get("thumbnail", default_icon)
        summary = item.get("summary", "")
        imdb = item.get("imdb", "")
        liz = xbmcgui.ListItem(title)
        if item.get("infolabels"):
            liz.setInfo("video", item["infolabels"])
        else:
            liz.setInfo("video", {"title": title, "plot": summary, "imdbnumber": imdb})
        liz.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail})
        playlist.clear()
        if resolveurl.HostedMediaFile(link).valid_url():
            url = resolveurl.HostedMediaFile(link).resolve()
            playlist.add(url,liz)
            return xbmc.Player().play(url,liz)
        playlist.add(link,liz)
        return xbmc.Player().play(link,liz)
    
def clean_title(title):
    title = re.sub('(?i)\[color.+?\]', '', title)
    title = re.sub('(?i)\[/color\]', '', title)
    title = re.sub('(?i)\[b\]', '', title)
    title = re.sub('(?i)\[/b\]', '', title)
    return title
        