import os, sys
import xbmcaddon

def plugin_filenames():
    try:
        return {entry.name for entry in os.scandir(os.path.dirname(__file__)) if entry.is_file() and not entry.name.startswith("__") and entry.name.endswith(".py")}
    except FileNotFoundError:
        return set()

addon_id = xbmcaddon.Addon().getAddonInfo("id")

noplugins_argv = ["/settings","/clear_cache","/clear_cache_silent","/refresh_menu","/daddylive","/sporthd","/streamed"]

if addon_id+'/run_plug/' in sys.argv[0]:
    __all__ = ['plug']
elif any(addon_id+x in sys.argv[0] for x in noplugins_argv):
    __all__ = []

else:
    files = plugin_filenames()
    __all__ = [
        filename[:-3]
        for filename in files]
from . import *
