import sys, re

try:
    from resources.lib.DI import DI
    from resources.lib.plugin import run_hook, register_routes
except ImportError:
    from .resources.lib.DI import DI
    from .resources.lib.plugin import run_hook, register_routes

import xbmc, xbmcgui, xbmcaddon
addon_id = xbmcaddon.Addon().getAddonInfo('id')
ownAddon = xbmcaddon.Addon(id=addon_id)
import base64



root_xml_url = ownAddon.getSetting('root_xml')
if not 'file:' in root_xml_url and not 'http' in root_xml_url:
    root_xml_url = base64.b64decode(root_xml_url + '=' * (-len(root_xml_url) % 4))
   
# root_xml_url = "file://main.json" 
root_xml_url = "http://gknwizard.eu/repo/Builds/GKoBu/xmls/microjenmain.json"


plugin = DI.plugin

@plugin.route("/")
def root() -> None:
    get_list(root_xml_url)


@plugin.route("/get_list/<path:url>")
def get_list(url: str) -> None:
    _get_list(url)


def _get_list(url):
    response = run_hook("get_list", url)    
    if response:
        reg1 = '(<\?)(.+?)(\?>)' 
        # reg2 = '(<\?xml-stylesheet)(.+?)(\?>)'
        reg2 = '(<layouttype)(.+?)(\/layouttype>)' 
        reg3 = '(<\!-)(.+?)(->)' 
        reg_list = [reg1, reg2, reg3] 
        response1 = response
        
        for reg in reg_list :
            dBlock = re.compile(reg,re.DOTALL).findall(response1)
            for d in dBlock : 
                response1 = response1.replace(str(''.join(d)),'')
               
        jen_list = run_hook("parse_list", url, response1)       
        # jen_list = run_hook("parse_list", url, response)      
 
        jen_list = [run_hook("process_item", item) for item in jen_list]
        jen_list = [
            run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list
        ]    
        run_hook("display_list", jen_list)
    else:
        run_hook("display_list", [])

@plugin.route("/play_video/<path:video>")
def play_video(video: str):
    import urllib.parse
    video = urllib.parse.unquote_plus(video)
    _play_video(video)

def _play_video(video):
    video = video.replace("'", '"')
    run_hook("play_video", video)

@plugin.route("/settings/<path:url>")
def settings(url):
    xbmcaddon.Addon().openSettings()

register_routes(plugin)

def main():
    plugin.run()
    return 0


if __name__ == "__main__":
    main()
