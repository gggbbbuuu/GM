
import xbmcaddon
try:
    from urllib.parse import parse_qsl
except:
    from urlparse import parse_qs as parse_qsl
try:
    from urllib.parse import urlencode
except:
    from urllib import urlencode


Addon = xbmcaddon.Addon()



def routing(argv1,argv2):
    from resources.main import refresh_list
    
    refresh_list(argv1,argv2,Addon_id=Addon)
    