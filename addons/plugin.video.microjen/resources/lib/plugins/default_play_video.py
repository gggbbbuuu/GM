from ..plugin import Plugin
import sys
import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import json, re

addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')
# playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

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
        summary = item.get("summary", title)
        imdb = item.get("imdb", "")
        # if '.m3u8' in link:
            # from urllib.parse import quote_plus
            # f4m_link = 'plugin://plugin.video.f4mTester/?streamtype=HLSRETRY&name=' + quote_plus(str(title)) + '&iconImage=' + quote_plus(str(thumbnail)) + '&thumbnailImage=' + quote_plus(str(thumbnail)) + '&description=' + quote_plus(summary) + '&url=' + quote_plus(link)
            # return xbmc.executebuiltin('RunPlugin(%s)' % f4m_link)
        liz = xbmcgui.ListItem(title)
        if item.get("infolabels"):
            liz.setInfo("video", item["infolabels"])
        else:
            liz.setInfo("video", {"title": title, "plot": summary, "imdbnumber": imdb})
        liz.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail})
        try:
            import resolveurl
            hmf = resolveurl.HostedMediaFile(link)
            if hmf.valid_url():
                link = hmf.resolve()
        except:
            pass
        
        liz.setPath(link)
        if item.get('is_playable'):
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
        else:
            xbmc.Player().play(link, liz)
        return True
    
def clean_title(title):
    title = re.sub('(?i)\[color.+?\]', '', title)
    title = re.sub('(?i)\[/color\]', '', title)
    title = re.sub('(?i)\[b\]', '', title)
    title = re.sub('(?i)\[/b\]', '', title)
    return title
        