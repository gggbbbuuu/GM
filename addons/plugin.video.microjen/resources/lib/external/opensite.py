import xbmc
import webbrowser

def platform():
    if xbmc.getCondVisibility('system.platform.android'):
        return 'android'
    elif xbmc.getCondVisibility('system.platform.linux'):
        return 'linux'
    elif xbmc.getCondVisibility('system.platform.windows'):
        return 'windows'
    elif xbmc.getCondVisibility('system.platform.osx'):
        return 'osx'
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return 'atv2'
    elif xbmc.getCondVisibility('system.platform.ios'):
        return 'ios'

myplatform = platform()

def open_site(url):
    if myplatform == 'android':
        intent_url = '"{}"'.format(url)
        xbmc.executebuiltin('StartAndroidActivity(,android.intent.action.VIEW,,{})'.format(intent_url))
    else:
        webbrowser.open(url)
