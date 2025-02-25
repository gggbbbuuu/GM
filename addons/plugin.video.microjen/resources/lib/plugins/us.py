import xbmc
import xbmcgui
import re
import json
from ..plugin import Plugin

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
HEADERS = {"User-Agent": USER_AGENT, 'Referer': 'https://ustv247.tv'}
PATTERN = re.compile("var hls_src='(.+?)';")

class us(Plugin):
    name = "us"
    priority = 1

    def play_video(self, item):
        item = json.loads(item)
        title = item.get('title', 'Unknown Title')
        link = item.get('link')
        thumbnail = item.get('thumbnail', '')
        if link and 'ustv247.tv/player.php' in link:         
            from ..DI import DI
            try:
                play_link = PATTERN.findall(DI.session.get(link, headers=HEADERS).text)[0]
            except IndexError:
                return
            liz=xbmcgui.ListItem(title)
            liz.setInfo('video', {'title': title})
            liz.setArt({'icon': thumbnail, 'thumb': thumbnail, 'poster': thumbnail})
            xbmc.Player().play(play_link, listitem=liz)
            return True