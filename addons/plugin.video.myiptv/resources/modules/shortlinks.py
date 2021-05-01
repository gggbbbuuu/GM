import xbmc,xbmcaddon,xbmcgui,requests
from resources.modules import control,tools
m3uurl          = control.setting('m3uurl')
hostport        = control.setting('hostport')
hosturl         = control.setting('hosturl')
username        = control.setting('Username')
password        = control.setting('Password')
def Get():
        xbmc.executebuiltin('ActivateWindow(busydialog)')
        m3u  = hosturl+':'+hostport+'/get.php?username='+username+'&password='+password+'&type=m3u_plus&output=ts'
        epg  = hosturl+':'+hostport+'/xmltv.php?username='+username+'&password='+password
        auth = hosturl+':'+hostport+'/enigma2.php?username='+username+'&password='+password+'&type=get_vod_categories'
        auth = tools.OPEN_URL(auth)
        if not auth=="":
            request  = 'https://tinyurl.com/create.php?source=indexpage&url='+m3u+'&submit=Make+TinyURL%21&alias='
            request2 = 'https://tinyurl.com/create.php?source=indexpage&url='+epg+'&submit=Make+TinyURL%21&alias='
            m3u = tools.OPEN_URL(request)
            epg = tools.OPEN_URL(request2)
            shortm3u = tools.regex_from_to(m3u,'<div class="indent"><b>','</b>')
            shortepg = tools.regex_from_to(epg,'<div class="indent"><b>','</b>')
            xbmc.executebuiltin('Dialog.Close(busydialog)')
            return shortm3u,shortepg
            
def showlinks():
    path = xbmcaddon.Addon().getAddonInfo('path')
    win = Window('shortlinks.xml',path,'Default',caption='Powered By proyecto-server')
    win.doModal()
    del win

            
class Window(xbmcgui.WindowXMLDialog):

    def __init__(self,*args,**kwargs):
        self.caption = kwargs.get('caption','')
        self.m3u,self.epg = Get()
        xbmcgui.WindowXMLDialog.__init__(self)

    def onInit(self):
        self.getControl(100).setLabel(self.caption)
        self.getControl(200).setText(self.m3u)
        self.getControl(300).setText(self.epg)