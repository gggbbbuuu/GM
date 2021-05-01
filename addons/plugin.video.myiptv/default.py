 #############Imports#############
import xbmc,xbmcaddon,xbmcgui,xbmcvfs,xbmcplugin,base64,os,re,unicodedata,requests,time,string,sys,urllib.request,urllib.parse,urllib.error,json,datetime,zipfile,shutil
from resources.modules import client,control,tools,user
from datetime import date
import xml.etree.ElementTree as ElementTree


#################################

#############Defined Strings#############
icon         = xbmcvfs.translatePath(os.path.join('special://home/addons/' + user.id, 'icon.png'))
fanart       = xbmcvfs.translatePath(os.path.join('special://home/addons/' + user.id , 'fanart.jpg'))
m3uurl          = control.setting('m3uurl')
hostport        = control.setting('hostport')
hosturl         = control.setting('hosturl')
username        = control.setting('Username')
password        = control.setting('Password')

search_play  = '%s:%s/' % (hosturl,hostport)
live_url     = '%s:%s/enigma2.php?username=%s&password=%s&type=get_live_categories'%(hosturl,hostport,username,password)
series_url   = '%s:%s/enigma2.php?username=%s&password=%s&type=get_series_categories'%(hosturl,hostport,username,password)
vod_url      = '%s:%s/enigma2.php?username=%s&password=%s&type=get_vod_categories'%(hosturl,hostport,username,password)
panel_api    = '%s:%s/panel_api.php?username=%s&password=%s'%(hosturl,hostport,username,password)
panel_api1    = '%s:%s/panel_api.php?username=%s&password=%s&type=get_series'%(hosturl,hostport,username,password)
play_url     = '%s:%s/live/%s/%s/'%(hosturl,hostport,username,password)


Guide = xbmcvfs.translatePath(os.path.join('special://home/addons/addons/'+user.id+'/resources/catchup', 'guide.xml'))
GuideLoc = xbmcvfs.translatePath(os.path.join('special://home/addons/addons/'+user.id+'/resources/catchup', 'g'))

advanced_settings           =  xbmcvfs.translatePath('special://home/addons/'+user.id+'/resources/advanced_settings')
advanced_settings_target    =  xbmcvfs.translatePath(os.path.join('special://home/userdata','advancedsettings.xml'))

KODIV        = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
#########################################

def buildcleanurl(url):
    url = str(url).replace('USERNAME',username).replace('PASSWORD',password)
    return url
def startm3u():
    if username=="":
        if m3uurl=="":
            fullm3uurl = m3uurlpopup()
        else:
            fullm3uurl = m3uurl
        if fullm3uurl != False and fullm3uurl!="":
            control.setSetting('m3uurl',fullm3uurl)
            try:
                urldata = re.findall('(.+?)/get.php\?username=(.+?)&password=(.+?)&type', fullm3uurl, re.DOTALL)[0]
                musername = urldata[1]
                mpassword = urldata[2]
                mhosturl = urldata[0].rsplit(':', 1)[0]
                if mhosturl == 'http' or mhosturl == 'https':
                    mhosturl = urldata[0]
                mhostport = urldata[0].split(':')[-1]
                if '/' in mhostport:
                    mhostport = ''
                control.setSetting('hostport', mhostport)
                control.setSetting('hosturl', mhosturl)
                control.setSetting('Username', musername)
                control.setSetting('Password', mpassword)
                # xbmc.executebuiltin('Container.Refresh')
                auth = '%s:%s/enigma2.php?username=%s&password=%s&type=get_vod_categories'%(mhosturl,mhostport,musername,mpassword)
                auth = tools.OPEN_URL(auth)
                if auth == "":
                    line1 = "Λάθος στοιχεία λογαριασμού"
                    line2 = "Προσπαθείστε ξανά" 
                    line3 = "" 
                    xbmcgui.Dialog().ok('Προσοχή', line1+'[CR]'+line2+'[CR]'+line3)
                    xbmcaddon.Addon().setSetting('m3uurl','')
                    xbmcaddon.Addon().setSetting('hosturl','')
                    xbmcaddon.Addon().setSetting('hostport','')
                    xbmcaddon.Addon().setSetting('Username','')
                    xbmcaddon.Addon().setSetting('Password','')
                    dialog = xbmcgui.Dialog().yesno(user.name,'Θέλετε να προσπαθήσετε ξανά με άλλη m3u διεύθυνση?')
                    if dialog:
                        startm3u()
                    else:
                        xbmc.executebuiltin('XBMC.ActivateWindow(Videos,addons://sources/video/)')
                else:
                    line1 = "Επιτυχής σύνδεση"
                    line2 = "Καλώς ήρθατε [B][COLOR orangered]%s[/COLOR][/B]"%musername
                    line3 = 'στο [B][COLOR orangered]MyIPTV[/COLOR][/B]'
                    xbmcgui.Dialog().ok(user.name, line1+'[CR]'+line2+'[CR]'+line3)
                    # tvguidesetup()
                    addonsettings('','')
                    xbmc.executebuiltin('Container.Refresh')
                    home()
            except:
                dialog = xbmcgui.Dialog().yesno(user.name,'Μη αποδεκτή διεύθυνση M3U[CR]Θέλετε να προσπαθήσετε ξανά με άλλη m3u διεύθυνση?')
                if dialog:
                    startm3u()
        else:
            urlhost = hostpopup()
            porthost = portpopup()
            usern = userpopup()
            passw= passpopup()
            try:
                control.setSetting('hosturl',urlhost)
                control.setSetting('hostport',porthost)
                control.setSetting('Username',usern)
                control.setSetting('Password',passw)
                xbmc.executebuiltin('Container.Refresh')
                auth = '%s:%s/enigma2.php?username=%s&password=%s&type=get_vod_categories'%(urlhost,porthost,usern,passw)
                auth = tools.OPEN_URL(auth)
                if auth == "":
                    line1 = "Λάθος στοιχεία λογαριασμού"
                    line2 = "Προσπαθείστε ξανά" 
                    line3 = "" 
                    xbmcgui.Dialog().ok('Προσοχή', line1+'[CR]'+line2+'[CR]'+line3)
                    start()
                else:
                    line1 = "Επιτυχής σύνδεση"
                    line2 = "Καλώς ήρθατε [B][COLOR orangered]%s[/COLOR][/B]"%usern
                    line3 = 'στο [B][COLOR orangered]MyIPTV[/COLOR][/B]'
                    xbmcgui.Dialog().ok(user.name, line1+'[CR]'+line2+'[CR]'+line3)
                    # tvguidesetup()
                    addonsettings('','')
                    xbmc.executebuiltin('Container.Refresh')
                    home()
            except:
                xbmcaddon.Addon().setSetting('m3uurl','')
                xbmcaddon.Addon().setSetting('hosturl','')
                xbmcaddon.Addon().setSetting('hostport','')
                xbmcaddon.Addon().setSetting('Username','')
                xbmcaddon.Addon().setSetting('Password','')
                line1 = "Αποτυχία σύνδεσης"
                line2 = "Αποτύχατε να συνδεθείτε."
                line3 = 'Θα γίνει έξοδος.'
                xbmcgui.Dialog().ok(user.name, line1+'[CR]'+line2+'[CR]'+line3)
                xbmc.executebuiltin('XBMC.ActivateWindow(Videos,addons://sources/video/)')

    else:
        auth = '%s:%s/enigma2.php?username=%s&password=%s&type=get_vod_categories'%(hosturl,hostport,username,password)
        auth = tools.OPEN_URL(auth)
        if not auth=="":
            tools.addDir('Πληροφορίες λογαριασμού','url',6,icon,fanart,'')
            tools.addDir('Ζωντανή Τηλεόραση','live',1,icon,fanart,'')
            if xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)'):
                tools.addDir('Οδηγός TV','pvr',7,icon,fanart,'')
            tools.addDir('Σειρές','series',18,icon,fanart,'')
            tools.addDir('Ταινίες','vod',3,icon,fanart,'')
            tools.addDir('Αναζήτηση','url',5,icon,fanart,'')
            tools.addDir('Επιλογές','url',8,icon,fanart,'')
            tools.addDir('Εργαλεία','url',16,icon,fanart,'')
            tools.addDir('Αποσύνδεση','LO',10,icon,fanart,'')
def start():
    if username=="":
        urlhost = hostpopup()
        porthost = portpopup()
        usern = userpopup()
        passw= passpopup()
        control.setSetting('hosturl',urlhost)
        control.setSetting('hostport',porthost)
        control.setSetting('Username',usern)
        control.setSetting('Password',passw)
        xbmc.executebuiltin('Container.Refresh')
        auth = '%s:%s/enigma2.php?username=%s&password=%s&type=get_vod_categories'%(urlhost,porthost,usern,passw)
        auth = tools.OPEN_URL(auth)
        if auth == "":
            line1 = "Λάθος στοιχεία λογαριασμού"
            line2 = "Προσπαθείστε ξανά" 
            line3 = "" 
            xbmcgui.Dialog().ok('Προσοχή', line1+'[CR]'+line2+'[CR]'+line3)
            start()
        else:
            line1 = "Επιτυχής σύνδεση"
            line2 = "Καλώς ήρθατε               "+user.name 
            line3 = ('[B][COLOR orangered]                                       %s[/COLOR][/B]'%usern)
            xbmcgui.Dialog().ok(user.name, line1+'[CR]'+line2+'[CR]'+line3)
            # tvguidesetup()
            addonsettings('','')
            xbmc.executebuiltin('Container.Refresh')
            home()
    else:
        auth = '%s:%s/enigma2.php?username=%s&password=%s&type=get_vod_categories'%(hosturl,hostport,username,password)
        auth = tools.OPEN_URL(auth)
        if not auth=="":
            tools.addDir('Πληροφορίες λογαριασμού','url',6,icon,fanart,'')
            tools.addDir('Ζωντανή Τηλεόραση','live',1,icon,fanart,'')
            if xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)'):
                tools.addDir('Οδηγός TV','pvr',7,icon,fanart,'')
            tools.addDir('Σειρές','series',18,icon,fanart,'')
            tools.addDir('Ταινίες','vod',3,icon,fanart,'')
            tools.addDir('Αναζήτηση','url',5,icon,fanart,'')
            tools.addDir('Επιλογές','url',8,icon,fanart,'')
            tools.addDir('Εργαλεία','url',16,icon,fanart,'')
            tools.addDir('Αποσύνδεση','LO',10,icon,fanart,'')
                
def home():
    tools.addDir('Πληροφορίες λογαριασμού','url',6,icon,fanart,'')
    tools.addDir('Ζωντανή Τηλεόραση','live',1,icon,fanart,'')
    if xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)'):
        tools.addDir('Οδηγός TV','pvr',7,icon,fanart,'')
    tools.addDir('Σειρές','series',18,icon,fanart,'')
    tools.addDir('Ταινίες','vod',3,icon,fanart,'')
    tools.addDir('Αναζήτηση','',5,icon,fanart,'')
    tools.addDir('Επιλογές','url',8,icon,fanart,'')
    tools.addDir('Εργαλεία','url',16,icon,fanart,'')
    tools.addDir('Αποσύνδεση','LO',10,icon,fanart,'')
        
def livecategory(url):
    
    open = tools.OPEN_URL(live_url)
    all_cats = tools.regex_get_all(open,'<channel>','</channel>')
    for a in all_cats:
        name = tools.regex_from_to(a,'<title>','</title>')
        name = base64.b64decode(name).decode('utf-8', errors='ignore')
        url1  = tools.regex_from_to(a,'<playlist_url>','</playlist_url>').replace('<![CDATA[','').replace(']]>','')
        if xbmcaddon.Addon().getSetting('hidexxx')=='true':
            tools.addDir('%s'%name,url1,2,icon,fanart,'')
        else:
            if not 'XXX |' in name:
                tools.addDir('%s'%name,url1,2,icon,fanart,'')
        
def Livelist(url):
    url  = buildcleanurl(url)
    open = tools.OPEN_URL(url)
    all_cats = tools.regex_get_all(open,'<channel>','</channel>')
    for a in all_cats:
        name = tools.regex_from_to(a,'<title>','</title>')
        name = base64.b64decode(name).decode('utf-8', errors='ignore')
        xbmc.log(str(name))
        name = re.sub('\[.*?min ','-',name)
        thumb= tools.regex_from_to(a,'<desc_image>','</desc_image>').replace('<![CDATA[','').replace(']]>','')
        url1  = tools.regex_from_to(a,'<stream_url>','</stream_url>').replace('<![CDATA[','').replace(']]>','')
        desc = tools.regex_from_to(a,'<description>','</description>')
        if xbmcaddon.Addon().getSetting('hidexxx')=='true':
            tools.addDir(name,url1,4,thumb,fanart,base64.b64decode(desc))
        else:
            if not 'XXX:' in name:
                if not 'XXX VOD:' in name:
                    tools.addDir(name,url1,4,thumb,fanart,base64.b64decode(desc))
        
        
    
def vod(url):
    if url =="vod":
        open = tools.OPEN_URL(vod_url)
    else:
        url  = buildcleanurl(url)
        open = tools.OPEN_URL(url)
    all_cats = tools.regex_get_all(open,'<channel>','</channel>')
    for a in all_cats:
        if '<playlist_url>' in open:
            name = tools.regex_from_to(a,'<title>','</title>')
            url1  = tools.regex_from_to(a,'<playlist_url>','</playlist_url>').replace('<![CDATA[','').replace(']]>','')
            tools.addDir(str(base64.b64decode(name).decode('utf-8', errors='ignore')).replace('?',''),url1,3,icon,fanart,'')
        else:
            if xbmcaddon.Addon().getSetting('meta') == 'true':
                try:
                    name = tools.regex_from_to(a,'<title>','</title>')
                    name = base64.b64decode(name).decode('utf-8', errors='ignore')
                    thumb= tools.regex_from_to(a,'<desc_image>','</desc_image>').replace('<![CDATA[','').replace(']]>','')
                    url  = tools.regex_from_to(a,'<stream_url>','</stream_url>').replace('<![CDATA[','').replace(']]>','')
                    desc = tools.regex_from_to(a,'<description>','</description>')
                    desc = base64.b64decode(desc).decode('utf-8', errors='ignore')
                    plot = tools.regex_from_to(desc,'PLOT:','\n')
                    plot = re.compile('-.*?-.*?-(.*?)-',re.DOTALL).findall(plot)
                    cast = tools.regex_from_to(desc,'CAST:','\n')
                    ratin= tools.regex_from_to(desc,'RATING:','\n')
                    year = tools.regex_from_to(desc,'RELEASEDATE:','\n').replace(' ','-')
                    year = re.compile('-.*?-.*?-(.*?)-',re.DOTALL).findall(year)
                    runt = tools.regex_from_to(desc,'DURATION_SECS:','\n')
                    genre= tools.regex_from_to(desc,'GENRE:','\n')
                    tools.addDirMeta(str(name).replace('[/COLOR][/B].','.[/COLOR][/B]'),url,4,thumb,fanart,plot,str(year).replace("['","").replace("']",""),str(cast).split(),ratin,runt,genre)
                except:pass
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
            else:
                name = tools.regex_from_to(a,'<title>','</title>')
                name = base64.b64decode(name).decode('utf-8', errors='ignore')
                thumb= tools.regex_from_to(a,'<desc_image>','</desc_image>').replace('<![CDATA[','').replace(']]>','')
                url  = tools.regex_from_to(a,'<stream_url>','</stream_url>').replace('<![CDATA[','').replace(']]>','')
                desc = tools.regex_from_to(a,'<description>','</description>')
                tools.addDir(name,url,4,thumb,fanart,base64.b64decode(desc).decode('utf-8', errors='ignore'))
                
def series(url):
    if url =="series":
        open = tools.OPEN_URL(series_url)
    else:
        url  = buildcleanurl(url)
        open = tools.OPEN_URL(url)
    all_cats = tools.regex_get_all(open,'<channel>','</channel>')
    for a in all_cats:
        if '<playlist_url>' in open:
            name = tools.regex_from_to(a,'<title>','</title>')
            url1  = tools.regex_from_to(a,'<playlist_url>','</playlist_url>').replace('<![CDATA[','').replace(']]>','')
            tools.addDir(str(base64.b64decode(name).decode('utf-8', errors='ignore')).replace('?',''),url1,3,icon,fanart,'')
        else:
            if xbmcaddon.Addon().getSetting('meta') == 'true':
                try:
                    name = tools.regex_from_to(a,'<title>','</title>')
                    name = base64.b64decode(name).decode('utf-8', errors='ignore')
                    thumb= tools.regex_from_to(a,'<desc_image>','</desc_image>').replace('<![CDATA[','').replace(']]>','')
                    url  = tools.regex_from_to(a,'<stream_url>','</stream_url>').replace('<![CDATA[','').replace(']]>','')
                    desc = tools.regex_from_to(a,'<description>','</description>')
                    desc = base64.b64decode(desc).decode('utf-8', errors='ignore')
                    plot = tools.regex_from_to(desc,'PLOT:','\n')
                    plot = re.compile('-.*?-.*?-(.*?)-',re.DOTALL).findall(plot)
                    cast = tools.regex_from_to(desc,'CAST:','\n')
                    ratin= tools.regex_from_to(desc,'RATING:','\n')
                    year = tools.regex_from_to(desc,'RELEASEDATE:','\n').replace(' ','-')
                    year = re.compile('-.*?-.*?-(.*?)-',re.DOTALL).findall(year)
                    runt = tools.regex_from_to(desc,'DURATION_SECS:','\n')
                    genre= tools.regex_from_to(desc,'GENRE:','\n')
                    tools.addDirMeta(str(name).replace('[/COLOR][/B].','.[/COLOR][/B]'),url,4,thumb,fanart,plot,str(year).replace("['","").replace("']",""),str(cast).split(),ratin,runt,genre)
                except:pass
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
            else:
                name = tools.regex_from_to(a,'<title>','</title>')
                name = base64.b64decode(name)
                thumb= tools.regex_from_to(a,'<desc_image>','</desc_image>').replace('<![CDATA[','').replace(']]>','')
                url  = tools.regex_from_to(a,'<stream_url>','</stream_url>').replace('<![CDATA[','').replace(']]>','')
                desc = tools.regex_from_to(a,'<description>','</description>')
                tools.addDir(name,url,4,thumb,fanart,base64.b64decode(desc).decode('utf-8', errors='ignore'))
                
                
        
##############################################
#### RULE NO.1 - DONT WRITE CODE THAT IS  ####
#### ALREADY WRITTEN AND PROVEN TO WORK :)####
##############################################


def catchup():
    listcatchup()
        
def listcatchup():
    open = tools.OPEN_URL(panel_api)
    all  = tools.regex_get_all(open,'{"num','direct')
    for a in all:
        if '"tv_archive":1' in a:
            name = tools.regex_from_to(a,'"epg_channel_id":"','"').replace('\/','/')
            thumb= tools.regex_from_to(a,'"stream_icon":"','"').replace('\/','/')
            id   = tools.regex_from_to(a,'stream_id":"','"')
            if not name=="":
                tools.addDir(name,'url',13,thumb,fanart,id)
            

def tvarchive(name,description):
    days = 5
    
    now = str(datetime.datetime.now()).replace('-','').replace(':','').replace(' ','')
    date3 = datetime.datetime.now() - datetime.timedelta(days)
    date = str(date3)
    date = str(date).replace('-','').replace(':','').replace(' ','')
    APIv2 = base64.b64decode("JXM6JXMvcGxheWVyX2FwaS5waHA/dXNlcm5hbWU9JXMmcGFzc3dvcmQ9JXMmYWN0aW9uPWdldF9zaW1wbGVfZGF0YV90YWJsZSZzdHJlYW1faWQ9JXM=")%(hosturl,hostport,username,password,description)
    link=tools.OPEN_URL(APIv2)
    match = re.compile('"title":"(.+?)".+?"start":"(.+?)","end":"(.+?)","description":"(.+?)"').findall(link)
    for ShowTitle,start,end,DesC in match:
        ShowTitle = base64.b64decode(ShowTitle).decode('utf-8', errors='ignore')
        DesC = base64.b64decode(DesC).decode('utf-8', errors='ignore')
        format = '%Y-%m-%d %H:%M:%S'
        try:
            modend = dtdeep.strptime(end, format)
            modstart = dtdeep.strptime(start, format)
        except:
            modend = datetime.datetime(*(time.strptime(end, format)[0:6]))
            modstart = datetime.datetime(*(time.strptime(start, format)[0:6]))
        StreamDuration = modend - modstart
        modend_ts = time.mktime(modend.timetuple())
        modstart_ts = time.mktime(modstart.timetuple())
        FinalDuration = int(modend_ts-modstart_ts) / 60
        strstart = start
        Realstart = str(strstart).replace('-','').replace(':','').replace(' ','')
        start2 = start[:-3]
        editstart = start2
        start2 = str(start2).replace(' ',' - ')
        start = str(editstart).replace(' ',':')
        Editstart = start[:13] + '-' + start[13:]
        Finalstart = Editstart.replace('-:','-')
        if Realstart > date:
            if Realstart < now:
                catchupURL = base64.b64decode("JXM6JXMvc3RyZWFtaW5nL3RpbWVzaGlmdC5waHA/dXNlcm5hbWU9JXMmcGFzc3dvcmQ9JXMmc3RyZWFtPSVzJnN0YXJ0PQ==")%(hosturl,hostport,username,password,description)
                ResultURL = catchupURL + str(Finalstart) + "&duration=%s"%(FinalDuration)
                kanalinimi = "[B][COLOR red]%s[/COLOR][/B] - %s"%(start2,ShowTitle)
                tools.addDir(kanalinimi,ResultURL,4,icon,fanart,DesC)

    
                    
def DownloaderClass(url, dest):
    dp = xbmcgui.DialogProgress()
    dp.create('Λήψη τελευταίου Catch Up',"Λήψη τελευταίου Catch Up...")
    dp.update(0)
    start_time=time.time()
    urllib.request.urlretrieve(url, dest, lambda nb, bs, fs: _pbhook(nb, bs, fs, dp, start_time))

def _pbhook(numblocks, blocksize, filesize, dp, start_time):
        try: 
            percent = min(numblocks * blocksize * 100 / filesize, 100) 
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
            kbps_speed = numblocks * blocksize / (time.time() - start_time) 
            if kbps_speed > 0: 
                eta = (filesize - numblocks * blocksize) / kbps_speed 
            else: 
                eta = 0 
            kbps_speed = kbps_speed / 1024 
            mbps_speed = kbps_speed / 1024 
            total = float(filesize) / (1024 * 1024) 
            mbs = '[B][COLOR red]%.02f MB of less than 5MB[/COLOR][/B]' % (currently_downloaded)
            e = '[B][COLOR red]Speed:  %.02f Mb/s ' % mbps_speed  + '[/COLOR][/B]'
            dp.update(percent, mbs+'[CR]'+e)
        except: 
            percent = 100 
            dp.update(percent) 
        if dp.iscanceled():
            dialog = xbmcgui.Dialog()
            dialog.ok(user.name, 'Η λήψη ακυρώθηκε.')
                
            sys.exit()
            dp.close()
#####################################################################

def tvguide():
        xbmc.executebuiltin('ActivateWindow(TVGuide)')
def stream_video(url):
    url = buildcleanurl(url)
    url = str(url).replace('USERNAME',username).replace('PASSWORD',password)
    liz = xbmcgui.ListItem('')
    liz.setArt({'icon': 'DefaultVideo.png', 'thumb': icon})
    liz.setInfo(type='Video', infoLabels={'Title': '', 'Plot': ''})
    liz.setProperty('IsPlayable','true')
    liz.setPath(str(url))
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
    
    
def searchdialog():
    search = control.inputDialog(heading='Search '+user.name+':')
    if search=="":
        return
    else:
        return search

    
def search():
    if mode==3:
        return False
    text = searchdialog()
    if not text:
        xbmc.executebuiltin("XBMC.Notification([B][COLOR red][B]Η αναζήτηση είναι κενή[/B][/COLOR][/B],Ακύρωση αναζήτησης,4000,"+icon+")")
        return
    xbmc.log(str(text))
    open = tools.OPEN_URL(panel_api)
    all_chans = tools.regex_get_all(open,'{"num":','epg')
    for a in all_chans:
        name = tools.regex_from_to(a,'name":"','"').replace('\/','/')
        url  = tools.regex_from_to(a,'"stream_id":"','"')
        thumb= tools.regex_from_to(a,'stream_icon":"','"').replace('\/','/')
        if text in name.lower():
            tools.addDir(name,play_url+url+'.ts',4,thumb,fanart,'')
        elif text not in name.lower() and text in name:
            tools.addDir(name,play_url+url+'.ts',4,thumb,fanart,'')
    # all_chans = tools.regex_get_all(open,'{"num":','tv_arch')
    # for a in all_chans:
        # name = tools.regex_from_to(a,'name":"','"').replace('\/','/')
        # url  = tools.regex_from_to(a,'"stream_id":"','"')
        # comp  = tools.regex_from_to(a,'"container_extension":"','"')
        # lms  = tools.regex_from_to(a,'"stream_type":"','"')
        # thumb= tools.regex_from_to(a,'stream_icon":"','"').replace('\/','/')
        # if lms == 'live':
            # if text in name.lower():
                # tools.addDir(name,search_play+'live/'+username+'/'+password+'/'+url+'.ts',4,thumb,fanart,'')
            # elif text not in name.lower() and text in name:
                # tools.addDir(name,search_play+'live/'+username+'/'+password+'/'+url+'.ts',4,thumb,fanart,'')
        # else:
            # if text in name.lower():
                # tools.addDir(name,search_play+lms+'/'+username+'/'+password+'/'+url+'.'+comp,4,thumb,fanart,'')
            # elif text not in name.lower() and text in name:
                # tools.addDir(name,search_play+lms+'/'+username+'/'+password+'/'+url+'.'+comp,4,thumb,fanart,'')
    # textenc = text.encode("utf-8")          
    # xbmc.log(str(base64.b64encode(textenc)))
    # open = tools.OPEN_URL(panel_api1)
    # all_chans = tools.regex_get_all(open,'<channel>','</channel>')
    # for a in all_chans:
        # name = tools.regex_from_to(a,'<title>','</title>')
        # name = base64.b64decode(name).decode('utf-8', errors='ignore')
        # url  = tools.regex_from_to(a,'<playlist_url>','</playlist_url>').replace('<![CDATA[','').replace(']]>','')
        # lms  = tools.regex_from_to(a,'"stream_type":"','"')
        # thumb= tools.regex_from_to(a,'stream_icon":"','"').replace('\/','/')
        # if text in name.lower():
            # tools.addDir(name,url,34,thumb,fanart,'')
        # elif text not in name.lower() and text in name:
            # tools.addDir(name,url,34,thumb,fanart,'')
    
def settingsmenu():
    if xbmcaddon.Addon().getSetting('meta')=='true':
        META = '[B][COLOR lime] ON[/COLOR][/B]'
    else:
        META = '[B][COLOR red]  OFF[/COLOR][/B]'
    if xbmcaddon.Addon().getSetting('hidexxx')=='true':
        XXX = '[B][COLOR red]   OFF[/COLOR][/B]'
    else:
        XXX = '[B][COLOR lime]  ON[/COLOR][/B]'
    #tools.addDir('Configuracion Avanzada','ADS',10,icon,fanart,'')
    tools.addDir('Απενεργοποίηση Ταινιών %s'%META,'META',10,icon,fanart,META)
    tools.addDir('Απενεργοποίηση ΧΧΧ %s'%XXX,'XXX',10,icon,fanart,XXX)
    # tools.addDir('Αποσύνδεση','LO',10,icon,fanart,'')
    

def addonsettings(url,description):
    url  = buildcleanurl(url)
    if   url =="CC":
        tools.clear_cache()
    elif url =="AS":
        xbmc.executebuiltin('Addon.OpenSettings(%s)'%user.id)
    elif url =="ADS":
        dialog = xbmcgui.Dialog().select('Edit Advanced Settings', ['Enable Fire TV Stick AS','Enable Fire TV AS','Enable 1GB Ram or Lower AS','Enable 2GB Ram or Higher AS','Enable Nvidia Shield AS','Disable AS'])
        if dialog==0:
            advancedsettings('stick')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings')
        elif dialog==1:
            advancedsettings('firetv')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings')
        elif dialog==2:
            advancedsettings('lessthan')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings 1GB')
        elif dialog==3:
            advancedsettings('morethan')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings 2GB')
        elif dialog==4:
            advancedsettings('shield')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings NVIDIA')
        elif dialog==5:
            advancedsettings('remove')
            xbmcgui.Dialog().ok(user.name, 'Advanced Settings Removed')
    elif url =="ADS2":
        dialog = xbmcgui.Dialog().select('Select Your Device Or Closest To', ['Fire TV Stick ','Fire TV','1GB Ram or Lower','2GB Ram or Higher','Nvidia Shield'])
        if dialog==0:
            advancedsettings('stick')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings')
        elif dialog==1:
            advancedsettings('firetv')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings')
        elif dialog==2:
            advancedsettings('lessthan')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings 1GB')
        elif dialog==3:
            advancedsettings('morethan')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings 2GB')
        elif dialog==4:
            advancedsettings('shield')
            xbmcgui.Dialog().ok(user.name, 'Set Advanced Settings NVIDIA')
    elif url =="tv":
        dialog = xbmcgui.Dialog().yesno(user.name,'Would You like us to Setup the TV Guide for You??')
        if dialog:
            pvrsetup()
            xbmcgui.Dialog().ok(user.name, 'PVR Integration Complete, Restart Kodi to apply changes')
    elif url =="ST":
        xbmc.executebuiltin('Runscript("special://home/addons/'+user.id+'/resources/modules/speedtest.py")')
    elif url =="META":
        if 'ON' in description:
            xbmcaddon.Addon().setSetting('meta','false')
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcaddon.Addon().setSetting('meta','true')
            xbmc.executebuiltin('Container.Refresh')
    elif url =="XXX":
        if 'OFF' in description:
            xbmcaddon.Addon().setSetting('hidexxx','false')
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcaddon.Addon().setSetting('hidexxx','true')
            xbmc.executebuiltin('Container.Refresh')
    elif url =="LO":
        dialog = xbmcgui.Dialog().yesno(user.name,'Θέλετε να αποσυνδέσετε τον λογαριασμό σας?')
        if dialog:
            xbmcaddon.Addon().setSetting('m3uurl','')
            xbmcaddon.Addon().setSetting('hosturl','')
            xbmcaddon.Addon().setSetting('hostport','')
            xbmcaddon.Addon().setSetting('Username','')
            xbmcaddon.Addon().setSetting('Password','')
            xbmcgui.Dialog().ok(user.name, 'Ο λογαριασμός σας αποσυνδέθηκε!!')
            xbmc.executebuiltin('XBMC.ActivateWindow(Videos,addons://sources/video/)')
            xbmc.executebuiltin('Container.Refresh')
    elif url =="UPDATE":
        if 'ON' in description:
            xbmcaddon.Addon().setSetting('update','false')
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcaddon.Addon().setSetting('update','true')
            xbmc.executebuiltin('Container.Refresh')
    
        
def advancedsettings(device):
    if device == 'stick':
        file = open(os.path.join(advanced_settings, 'stick.xml'))
    elif device == 'firetv':
        file = open(os.path.join(advanced_settings, 'firetv.xml'))
    elif device == 'lessthan':
        file = open(os.path.join(advanced_settings, 'lessthan1GB.xml'))
    elif device == 'morethan':
        file = open(os.path.join(advanced_settings, 'morethan1GB.xml'))
    elif device == 'shield':
        file = open(os.path.join(advanced_settings, 'shield.xml'))
    elif device == 'remove':
        os.remove(advanced_settings_target)
    
    try:
        read = file.read()
        f = open(advanced_settings_target, mode='w+')
        f.write(read)
        f.close()
    except:
        pass
        
    
def pvrsetup():
    correctPVR()
    return
        
        
def asettings():
    choice = xbmcgui.Dialog().yesno(user.name, 'Please Select The RAM Size of Your Device', yeslabel='Less than 1GB RAM', nolabel='More than 1GB RAM')
    if choice:
        lessthan()
    else:
        morethan()
    

def morethan():
    file = open(os.path.join(advanced_settings, 'morethan.xml'))
    a = file.read()
    f = open(advanced_settings_target, mode='w+')
    f.write(a)
    f.close()


def lessthan():
    file = open(os.path.join(advanced_settings, 'lessthan.xml'))
    a = file.read()
    f = open(advanced_settings_target, mode='w+')
    f.write(a)
    f.close()


def userpopup():
    kb =xbmc.Keyboard ('', 'heading', True)
    kb.setHeading('Εισάγετε το Username')
    kb.setHiddenInput(False)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        return text
    else:
        return False


def passpopup():
    kb =xbmc.Keyboard ('', 'heading', True)
    kb.setHeading('Εισάγετε το Password')
    kb.setHiddenInput(False)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        return text
    else:
        return False
        

def hostpopup():
    kb =xbmc.Keyboard ('', 'heading', True)
    kb.setHeading('Εισάγετε την διεύθυνση Host')
    kb.setHiddenInput(False)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        return text
    else:
        return False

def portpopup():
    kb =xbmc.Keyboard ('', 'heading', True)
    kb.setHeading('Εισάγετε Πόρτα')
    kb.setHiddenInput(False)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        return text
    else:
        return False

def m3uurlpopup():
    kb =xbmc.Keyboard ('', 'heading', True)
    kb.setHeading('Εισάγετε την διεύθυνση M3U - Αν δεν υπάρχει πατήστε ΑΚΥΡΟ')
    kb.setHiddenInput(False)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        return text
    else:
        return False


def accountinfo():
    try:
        open = tools.OPEN_URL(panel_api)
        username   = tools.regex_from_to(open,'"username":"','"')
        password   = tools.regex_from_to(open,'"password":"','"')
        status     = tools.regex_from_to(open,'"status":"','"')
        connects   = tools.regex_from_to(open,'"max_connections":"','"')
        active     = tools.regex_from_to(open,'"active_cons":"','"')
        expiry     = tools.regex_from_to(open,'"exp_date":"','"')
        if not expiry=="":
            expiry    = datetime.datetime.fromtimestamp(int(expiry)).strftime('%d/%m/%Y - %H:%M')
            expreg    = re.findall('^(.*?)/(.*?)/(.*?)$', expiry, re.DOTALL)[0]
            day       = expreg[0]
            month     = tools.MonthNumToName(expreg[1])
            year      = re.sub(' -.*?$','',expreg[2])
            expiry    = day+'-'+month+'-'+year
        else:
            expiry    = 'Άγνωστο'
        ip        = tools.getlocalip()
        extip     = tools.getexternalip()
        tools.addDir('[B][COLOR orangered]Username :[/COLOR][/B] '+username,'','',icon,fanart,'')
        tools.addDir('[B][COLOR orangered]Password :[/COLOR][/B] '+password,'','',icon,fanart,'')
        tools.addDir('[B][COLOR orangered]Ημερ. Λήξης:[/COLOR][/B] '+expiry,'','',icon,fanart,'')
        tools.addDir('[B][COLOR orangered]Κατάσταση Λογαριασμού :[/COLOR][/B] %s'%status,'','',icon,fanart,'')
        tools.addDir('[B][COLOR orangered]Ενεργές Συνδέσεις:[/COLOR][/B] '+ active,'','',icon,fanart,'')
        tools.addDir('[B][COLOR orangered]Επιτρεπτές Συνδέσεις:[/COLOR][/B] '+connects,'','',icon,fanart,'')
        tools.addDir('[B][COLOR orangered]Τοπική Διεύθυνση IP:[/COLOR][/B] '+ip,'','',icon,fanart,'')
        tools.addDir('[B][COLOR orangered]Εξωτερική Διεύθυνση IP:[/COLOR][/B] '+extip,'','',icon,fanart,'')
        tools.addDir('[B][COLOR orangered]Έκδοση Kodi:[/COLOR][/B] '+str(KODIV),'','',icon,fanart,'')
    except:
        pass
        

        
    
def correctPVR():

    addon = xbmcaddon.Addon(user.id)
    username_text = addon.getSetting(id='Username')
    password_text = addon.getSetting(id='Password')
    jsonSetPVR = '{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"pvrmanager.enabled", "value":true},"id":1}'
    IPTVon     = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.iptvsimple","enabled":true},"id":1}'
    nulldemo   = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.demo","enabled":false},"id":1}'
    loginurl   = hosturl+':'+hostport+"/get.php?username=" + username_text + "&password=" + password_text + "&type=m3u_plus&output=mpegts"
    EPGurl     = hosturl+':'+hostport+"/xmltv.php?username=" + username_text + "&password=" + password_text + "&type=m3u_plus&output=mpegts"

    xbmc.executeJSONRPC(jsonSetPVR)
    xbmc.executeJSONRPC(IPTVon)
    xbmc.executeJSONRPC(nulldemo)
    
    moist = xbmcaddon.Addon('pvr.iptvsimple')
    moist.setSetting(id='m3uUrl', value=loginurl)
    moist.setSetting(id='epgUrl', value=EPGurl)
    moist.setSetting(id='m3uCache', value="false")
    moist.setSetting(id='epgCache', value="false")
    xbmc.executebuiltin("Container.Refresh")

    
def tvguidesetup():
        dialog = xbmcgui.Dialog().yesno(user.name,'Θέλετε να ρυθμίσουμε τον οδηγό TV για εσάς?[CR]Ισχύει μόνο για όσους έχουν εγκατεστημένο το PVR Simple Client?')
        if dialog:
                pvrsetup()
                xbmcgui.Dialog().ok(user.name, 'Η ρύθμιση του PVR Simple Client ολοκληρώθηκε, επανεκκινήστε το Kodi για να εφαρμόσετε τις αλλαγές')

def num2day(num):
    if num =="0":
        day = 'monday'
    elif num=="1":
        day = 'tuesday'
    elif num=="2":
        day = 'wednesday'
    elif num=="3":
        day = 'thursday'
    elif num=="4":
        day = 'friday'
    elif num=="5":
        day = 'saturday'
    elif num=="6":
        day = 'sunday'
    return day
    
def extras():
    # tools.addDir('Create M3U list','url',17,icon,fanart,'')
    # tools.addDir('Run a Speed Test','ST',10,icon,fanart,'')
    tools.addDir('Clear Cache','CC',10,icon,fanart,'')
    

params=tools.get_params()
url=None
name=None
mode=None
iconimage=None
description=None
query=None
type=None

try:
    url=urllib.parse.unquote_plus(params["url"])
except:
    pass
try:
    name=urllib.parse.unquote_plus(params["name"])
except:
    pass
try:
    iconimage=urllib.parse.unquote_plus(params["iconimage"])
except:
    pass
try:
    mode=int(params["mode"])
except:
    pass
try:
    description=urllib.parse.unquote_plus(params["description"])
except:
    pass
try:
    query=urllib.parse.unquote_plus(params["query"])
except:
    pass
try:
    type=urllib.parse.unquote_plus(params["type"])
except:
    pass

if mode==None or url==None or len(url)<1:
    startm3u()

elif mode==1:
    livecategory(url)
    
elif mode==2:
    Livelist(url)
    
elif mode==3:
    vod(url)
    
elif mode==4:
    stream_video(url)
    
elif mode==5:
    search()
    
elif mode==6:
    accountinfo()
    
elif mode==7:
    tvguide()
    
elif mode==8:
    settingsmenu()
    
elif mode==9:
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    tools.Trailer().play(url) 
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    
elif mode==10:
    addonsettings(url,description)
    
elif mode==11:
    pvrsetup()
    
elif mode==12:
    catchup()

elif mode==13:
    tvarchive(name,description)
    
elif mode==14:
    listcatchup2()
    
elif mode==15:
    ivueint()
    
elif mode==16:
    extras()
    
elif mode==17:
    from resources.modules import shortlinks
    shortlinks.showlinks()

elif mode==18:
    series(url)

elif mode==9999:
    xbmcgui.Dialog().ok('[B][COLOR orangered]Wildside[/COLOR][/B]','This Category Will Be Available Soon!')
    livecategory('url')

xbmcplugin.endOfDirectory(int(sys.argv[1]))