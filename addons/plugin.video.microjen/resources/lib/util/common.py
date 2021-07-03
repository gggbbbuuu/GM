# used accross all addon
import xbmc, xbmcgui, xbmcaddon
from ..plugin import Plugin
from ..DI import DI

addon_id = xbmcaddon.Addon().getAddonInfo('id')
ownAddon = xbmcaddon.Addon(id=addon_id)
debugMode = ownAddon.getSetting('debug') or 'false' 
      
def do_log(message):   
    if debugMode. lower() == 'true' :                   
        xbmc.log(' > MicroJen Log > ' + str(message), xbmc.LOGINFO)         

class message(Plugin):
    name = "pop up message box"
    priority = 0    
    
    def routes(self, plugin):
        @plugin.route("/show_message/<path:message>")
        def show_message(message, header = 'Information'):
            message = message.replace('message/','')
            if message.lower().startswith("http"):
                message = DI.session.get(message).text
            xbmc.executebuiltin("ActivateWindow(10147)")
            controller = xbmcgui.Window(10147)
            xbmc.sleep(500)
            controller.getControl(1).setLabel(header)
            controller.getControl(5).setText(message)
   