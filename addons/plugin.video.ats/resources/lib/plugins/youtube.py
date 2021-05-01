import json

import xbmc

from ..plugin import Plugin


class Youtube(Plugin):
    name = "play with youtube"
    priority = 100    

    def get_list(self, url):
        if "youtube" in url:
            parts = url.split("/")
            if parts[-2] == 'channel':
                channel_id = parts[-1]
                xbmc.executebuiltin("Dialog.Close(all,true)")             
                xbmc.executebuiltin(
                    f"ActivateWindow(10025,plugin://plugin.video.youtube/channel/{channel_id}/, return)"
                )

    def play_video(self, item):
        item = json.loads(item)        
        if "youtube" in item["link"]:
                parts = item["link"].split("/")
                video_id = parts[-1]
                xbmc.executebuiltin(
                        f"RunPlugin(plugin://plugin.video.youtube/play/?video_id={video_id})"
                    )
                return True            
