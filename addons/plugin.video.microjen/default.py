import xbmc, xbmcaddon, xbmcgui
try:
    from resources.lib.DI import DI
    from resources.lib.plugin import run_hook, register_routes
except ImportError:
    from .resources.lib.DI import DI
    from .resources.lib.plugin import run_hook, register_routes

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *
    
#root_xml_url = ownAddon.getSetting('root_xml') or "file://main.xml"
root_xml_url = "http://gknwizard.eu/repo/Builds/GKoBu/xmls/microjenmain.json"
#root_xml_url =  "file://scraper_list.json"

plugin = DI.plugin
short_checker = ([
    'Adf.ly', 
    'Bit.ly', 
    'Chilp.it', 
    'Clck.ru', 
    'Cutt.ly', 
    'Da.gd', 
    'Git.io', 
    'goo.gl', 
    'Is.gd', 
    'NullPointer', 
    'Os.db', 
    'Ow.ly', 
    'Po.st', 
    'Qps.ru', 
    'Short.cm', 
    'Tiny.cc', 
    'TinyURL.com', 
    'Git.io', 
    'Tiny.cc', 
     ])

@plugin.route("/")
def root() -> None:
    get_list(root_xml_url)

@plugin.route("/get_list/<path:url>")
def get_list(url: str) -> None:
    #do_log(f" Reading url at route >  {url}" )
    url = url[:-len(".xmll")]+".xml" if url.endswith(".xmll") else url #replace .xmll from the end of url with .xml
    _get_list(url)

def _get_list(url):
    #do_log(f" Reading url >  {url}" )
    if "&list_page=" in url:
        list_page = int(url.split("&list_page=")[1])
        url = url.split("&list_page=")[0]
    else:
        list_page = 1
    if any(check.lower() in url.lower() for check in short_checker):
        url = DI.session.get(url).url
    response = run_hook("get_list", url)
    if response:           
        #do_log(f'default - response = \n {str(response)} ' )
        if ownAddon.getSettingBool("use_cache") and not "tmdb/search" in url:
            DI.db.set(url, response)
        jen_list = run_hook("parse_list", url, response)
        pages = 1
        meta_item = 0
        if xbmcaddon.Addon().getSettingBool("item_meta") and not "tmdb/" in url:
            for item in jen_list:
                if meta_item == 20:
                    meta_item = 0
                    pages = pages + 1
                if any (x in item for x in ["tmdb", "tmdb_id", "imdb", "imdb_id"]):
                    meta_item += 1
                item.update({"list_page":pages})
                
            jen_list = [run_hook("process_item", item) for item in jen_list if item.get("list_page") == list_page]
            for page in range(1,pages+1):
                if page == list_page:
                    continue
                page_item = xbmcgui.ListItem(f"Page{str(page)}")
                page_icon = xbmcaddon.Addon().getAddonInfo("icon")
                page_fanart = xbmcaddon.Addon().getAddonInfo("fanart")
                page_item.setArt({"icon": page_icon, "thumb": page_icon, "poster": page_icon, "fanart": page_fanart})
                jen_list.append({"type": "dir", "link": f"/get_list/{url}&list_page={str(page)}", "list_item": page_item, "is_dir": True})
        else:
            #do_log(f'default - jen list = \n {str(jen_list)} ')
            jen_list = [run_hook("process_item", item) for item in jen_list]
        jen_list = [
        run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list
        ]
        run_hook("display_list", jen_list)
    else:
        run_hook("display_list", [])

@plugin.route("/play_video/<path:video>")
def play_video(video: str):
    _play_video(video)

def _play_video(video):
    import base64
    video_link = '' 
    video = base64.urlsafe_b64decode(video)      
    if '"link":' in str(video) :
        video_link = run_hook("pre_play", video)
        if video_link : 
            run_hook("play_video", video_link)        
    else :
        run_hook("play_video", video)

@plugin.route("/settings")
def settings():
    xbmcaddon.Addon().openSettings()

@plugin.route("/clear_cache")
def clear_cache():
    DI.db.clear_cache()
    #xbmc.sleep(1000)
    xbmc.executebuiltin("Container.Refresh")

@plugin.route("/clear_cache_silent")
def clear_cache_silent():
    DI.db.clear_cache(False)
    #xbmc.sleep(1000)
    xbmc.executebuiltin("Container.Refresh")

@plugin.route("/refresh_menu")
def refresh_menu():
    DI.db.refresh_menu()
    xbmc.executebuiltin("Container.Refresh")

@plugin.route("/daddylive")
def daddylive():
    from resources.lib.external.daddy import daddy
    # xbmc.executebuiltin("Container.Refresh")


@plugin.route("/sporthd")
def sporthd():
    from resources.lib.external.sporthd import sporthd
    # xbmc.executebuiltin("Container.Refresh")


@plugin.route("/streamed")
def streamed():
    from resources.lib.external.streamed import default
    # xbmc.executebuiltin("Container.Refresh")

register_routes(plugin)

def main():
    plugin.run()
    return 0

if __name__ == "__main__":
    main()
