import xbmc
from resources.lib.WindowManager import wm
from resources.lib.library import addon_ID_short

xbmc.log(str('SERVICE2')+'===>PHIL', level=xbmc.LOGINFO)
return

xbmc.log(str('SERVICE2')+'!!===>PHIL', level=xbmc.LOGINFO)
xbmc.log(str('SERVICE2')+'===>PHIL', level=xbmc.LOGINFO)
xbmc.log(str('SERVICE2')+'!!===>PHIL', level=xbmc.LOGINFO)
xbmc.log(str('SERVICE2')+'===>PHIL', level=xbmc.LOGINFO)
xbmc.log(str('SERVICE2')+'!!===>PHIL', level=xbmc.LOGINFO)

player = xbmc.Player()
monitor = KodiMonitor()

class KodiMonitor(xbmc.Monitor):

    def __init__(self, **kwargs):
        xbmc.Monitor.__init__(self)

    def onNotification(self, sender, method, data):
        if sender == addon_ID_short():
            command_info = json.loads(data)
            #xbmc.log(str(command_info)+'onNotification===>PHIL', level=xbmc.LOGINFO)
            container = command_info['command_params']['container']
            position = command_info['command_params']['position']
            xbmc.log(str(wm.global_dialog())+'===>PHIL', level=xbmc.LOGINFO)

while(not monitor.abortRequested()):
    xbmc.sleep(500)
    if monitor.abortRequested():
        exit()