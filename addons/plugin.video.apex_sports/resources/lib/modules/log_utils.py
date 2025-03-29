import xbmc
import xbmcaddon
import sys

addon = xbmcaddon.Addon()
name = addon.getAddonInfo('name')


def log(msg, level=xbmc.LOGINFO):

    if addon.getSetting('addon_debug') == 'true':
        if sys.version_info[0] == 3:
            level = xbmc.LOGINFO
        else:
            level = xbmc.LOGNOTICE
    
    try:

        xbmc.log('%s: %s' % (name, msg), level)
    except Exception as e:
        try: xbmc.log('Logging Failure: %s' % (e), level)
        except: pass  # just give up
