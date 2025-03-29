# -*- coding: UTF-8 -*-
import sys,re,os
import six
from six.moves import urllib_error, urllib_request, urllib_parse, http_cookiejar
if six.PY2:
    from resources.lib.cmf2 import parseDOM
    LOGNOTICE = xbmc.LOGNOTICE
else:
    from resources.lib.cmf3 import parseDOM
    LOGNOTICE = xbmc.LOGINFO

if six.PY3:

    xrange = range
    unicode = str

import urllib3
import requests
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc,xbmcvfs
import threading
import base64

import inputstreamhelper
import resolveurl
import requests
import json
from urllib.parse import quote

packer = re.compile('(eval\(function\(p,a,c,k,e,(?:r|d).*)')
clappr = re.compile('new\s+Clappr\.Player\(\{\s*?source:\s*?["\'](.+?)["\']')
source = re.compile('sources\s*:\s*\[\s*\{\s*(?:type\s*:\s*[\'\"].+?[\'\"],|)src\s*:\s*[\'\"](.+?)[\'\"]')
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(urllib_parse.parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.PLsportowo')
PATH			= addon.getAddonInfo('path')

try:
    DATAPATH		= xbmcvfs.translatePath(addon.getAddonInfo('profile'))
except:
    DATAPATH		= xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')

proxyport = addon.getSetting('proxyport')
RESOURCES	   = PATH+'/resources/'
FANART=RESOURCES+'fanart.jpg'
blad=RESOURCES+'sworld.png'
bugats=RESOURCES+'bugatsinho.png'
sys.path.append( os.path.join( RESOURCES, "lib" ) )

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#ICON=RESOURCES+'sport365.png'
import jsunpack
#import sport365 as sport365
import streamendous as se
args			= urllib_parse.parse_qs(sys.argv[2][1:])
se.unbkuk = addon.getSetting('unbkuk')
ex_link = params.get('ex_link',[''])
imig= params.get('iconImage',[''])
tit= params.get('foldername',[''])
params2 = args.get('params2', [{}])[0]
BASEURLse='http://www.streamendous.com'
base="https://livetv.sx"

livelooker_url='http://livelooker.com/events.php?lang=pl'
UA='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'
UAX='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'
UAiphone='Mozilla/5.0 (iPhone; CPU iPhone OS 10_3 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) CriOS/56.0.2924.75 Mobile/14E5239e Safari/602.1'
s = requests.Session()

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

CIPHERS = ":".join(["DEFAULT","!DHE","!SHA1","!SHA256","!SHA384",])

class ZoomTVAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        context.set_ecdh_curve("secp384r1")
        kwargs["ssl_context"] = context
        return super(ZoomTVAdapter, self).init_poolmanager(*args, **kwargs)

headers = {
    "Referer": "https://www.tvply.me/sdembed?v=soc22sd",
    "Origin": "https://www.tvply.me",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.0.0 Safari/537.36",
    "Accept-Language": "en",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}
session = Session()
session.mount("https://key.seckeyserv.me", ZoomTVAdapter())
session.headers.update(headers)






def add_item(url, name, image, folder, mode, infoLabels=False,pusto=False,odtworz=True,fanart=FANART):	
    if not image:
        image=RESOURCES+'empty.png'
    if pusto:
        param={}
        param={'mode': mode, 'url': url}
        list_item = xbmcgui.ListItem(label=name)
        if not infoLabels:
            infoLabels={"title": name,'plot':name}
        list_item.setInfo(type="video", infoLabels=infoLabels)			
        list_item.setProperty("IsPlayable", 'false')
        list_item.setArt({'thumb': image, 'fanart': fanart})
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url(param),
            listitem=list_item,
            isFolder=False
        )	
    else:
        list_item = xbmcgui.ListItem(label=name)
        if folder:
            list_item.setProperty("IsPlayable", 'false')
        else:
            if odtworz:
                list_item.setProperty("IsPlayable", 'true')
            else:
                list_item.setProperty("IsPlayable", 'false')
        if not infoLabels:
            infoLabels={"title": name,'plot':name}
        list_item.setInfo(type="video", infoLabels=infoLabels)	
        list_item.setArt({'thumb': image, 'poster': image, 'banner': image, 'fanart': fanart})		
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url({'mode': mode, 'url': url,'image':image,'title':name}), 
            listitem=list_item,
            isFolder=folder
        )
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")

def addDir(name, ex_link=None, params2=1, mode='folder', iconImage='DefaultFolder.png', infoLabels=None, fanart=FANART, contextmenu=None):
    list_item = xbmcgui.ListItem(label=name)
    folder = False if mode == 'take_stream' else True
    if not infoLabels:
        infoLabels={"title": name,'plot':name}
    list_item.setInfo(type="video", infoLabels=infoLabels)	
    list_item.setArt({'thumb': iconImage, 'poster': iconImage, 'banner': iconImage, 'fanart': fanart})		
    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url=build_url({'mode': mode, 'foldername': name, 'ex_link': ex_link, 'params2': params2,'iconImage':iconImage}), 
        listitem=list_item,
        isFolder=folder
    )
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")

def addLinkItem(name, url, mode, params2=1, iconimage='DefaultFolder.png', infoLabels=False, IsPlayable=True,
                fanart=FANART, itemcount=1, contextmenu=None):
    u = build_url({'mode': mode, 'foldername': name, 'ex_link': url, 'params2': params2})

    liz = xbmcgui.ListItem(name)

    art_keys = ['thumb', 'poster', 'banner', 'fanart', 'clearart', 'clearlogo', 'landscape', 'icon']
    art = dict(zip(art_keys, [iconimage for x in art_keys]))
    art['landscape'] = fanart if fanart else art['landscape']
    art['fanart'] = fanart if fanart else art['landscape']
    liz.setArt(art)

    if not infoLabels:
        infoLabels = {"title": name}
    liz.setInfo(type="video", infoLabels=infoLabels)
    if IsPlayable:
        liz.setProperty('IsPlayable', 'true')

    if contextmenu:
        contextMenuItems = contextmenu
        liz.addContextMenuItems(contextMenuItems, replaceItems=True)

    ok = xbmcplugin.addDirectoryItem(handle=addon_handle, url=u, listitem=liz, isFolder=False, totalItems=itemcount)
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask="%R, %Y, %P")
    return ok
    
    
    
    
    
def encoded_dict(in_dict):
    try:
        # Python 2
        iter_dict = in_dict.iteritems
    except AttributeError:
        # Python 3
        iter_dict = in_dict.items
    out_dict = {}
    for k, v in iter_dict():
        if isinstance(v, unicode):
            v = v.encode('utf8')
        elif isinstance(v, str):
            # Must be encoded in UTF-8
            v.decode('utf8')
        out_dict[k] = v
    return out_dict
    
def build_url(query):
    return base_url + '?' + urllib_parse.urlencode(encoded_dict(query))
    
def home():	
    import rtmpcheck as rtc
    #aa=rtc.get_addon()
    ab=rtc.get_addon('inputstream.adaptive')
    ac=rtc.get_addon('inputstream.rtmp')
    setUnblockKuk()
    #addDir('Sport365 LIVE [COLOR red] (nie działa) [/COLOR]', ex_link='', params2={'_service':'sport365','_act':'ListChannels'}, mode='xxx', iconImage=RESOURCES+'sport365.png', fanart=FANART)
    #add_item('http://livelooker.com/pl/dzisiaj.html', 'LiveLooker', RESOURCES+'vipl.png', True, "livelooker", infoLabels=False)
    add_item('http://liveonscore.tv', 'LiveOnScore', RESOURCES+'liveonscor.png', True, "liveonscore2", infoLabels=False)
    add_item('https://www.vipleague.lc', 'VipLeague', RESOURCES+'vipl.png', True, "vipleague2", infoLabels=False)
    
    add_item('{}/enx/allupcoming/'.format(base), 'LiveTV.sx', RESOURCES+'livetv.png', True, "livetvsx", infoLabels=False)
    add_item('https://sport.tvp.pl/transmisje', 'TVP Sport - Transmisje', RESOURCES+'tvpsport.png', True, "listTVP")	
    add_item('cricfree', 'Crickfree', RESOURCES+'crfree.png', True, 'scheduleCR')	
    add_item('http://strims.top', 'Strims Top (Strumyk.tv)', RESOURCES+'sworld.png', True, 'scheduleSW')	
    
    add_item('http://strims.top', 'LiveSport.ws', RESOURCES+'logoc.png', True, 'livesportws')	
    add_item('http://strims.top', 'SportsBay', RESOURCES+'logosb.png', True, 'getsportsbay')	
    add_item('https://www.tvcom.pl/', 'TVCOM', RESOURCES+'tvcom.png', True, 'gettvcom')	
    add_item('http://www.rojadirecta.eu/en?p4', 'rojadirecta', RESOURCES+'roja.jpg', True, 'getroja')  
    
    add_item('http://crackstreams.io/', 'Crackstreams', RESOURCES+'icon.png', True, "crackstreamsmenu", infoLabels=False)
   
    add_item('', 'Live channels', RESOURCES+'chan2.png', True, "liveChannels")		
    xbmcplugin.endOfDirectory(addon_handle)

    
def CrackstreamsMenu():


    add_item("https://crackstreams.io/nbastreams", 'NBA streams', 'https://crackstreams.io/images/nba2.png', True, "crackstreams", infoLabels=False)
    add_item("https://crackstreams.io/nflstreams", 'NFL streams', 'https://crackstreams.io/images/nfl.png', True, "crackstreams", infoLabels=False)
    add_item("https://crackstreams.io/nhlstreams", 'NHL streams', 'https://crackstreams.io/images/nhl.svg', True, "crackstreams", infoLabels=False)
    add_item("https://crackstreams.io/mlbstreams", 'MLB streams', 'https://crackstreams.io/images/mlb.svg', True, "crackstreams", infoLabels=False)
    
    
    add_item("https://crackstreams.io/cfbstreams", 'NCAAF streams', 'https://crackstreams.io/images/ncaafz.png', True, "crackstreams", infoLabels=False)

    add_item("https://crackstreams.io/mmastreams", 'MMA/UFC streams', 'https://crackstreams.io/images/mma.png', True, "crackstreams", infoLabels=False)
    add_item("https://crackstreams.io/boxingstreams", 'Boxing streams', 'https://crackstreams.io/images/box.jpg', True, "crackstreams", infoLabels=False)
    
#	add_item("http://ronaldo7.io/soccerstreams", 'SOCCER streams', 'http://ronaldo7.io/soccer-logo/soccer-ball.svg', True, "ronaldo", infoLabels=False)
    
    xbmcplugin.endOfDirectory(addon_handle)  
    
def GetCrackstreams():
    url = params.get('url', None)
    
    links= se.getCrackstreams(url)
    if links:
        for f in links:

            add_item(f.get('href'), f.get('title'),f.get('image'), False,'playcrackstreams', infoLabels={'plot':f.get('title'),'code':f.get('code')},odtworz=False)	

        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle) 
def PlayCrackstreams():
    url = params.get('url', None)
    tytul = params.get('title', None)
    zdj = params.get('image', None)
    stream_url,hea = se.getStreamCrackstreams(url)

    if stream_url:
        play_item = xbmcgui.ListItem(path=stream_url,label=tytul)
        play_item.setArt({'thumb': zdj, 'poster': zdj, 'banner': zdj, 'fanart': FANART})
        play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':tytul})
        if not 'cdnfox' in stream_url:
            if six.PY3:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
            else:
                play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
            play_item.setProperty("IsPlayable", "true")
            if hea:
                play_item.setProperty('inputstream.adaptive.stream_headers', hea)
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            play_item.setMimeType('application/vnd.apple.mpegurl')
            play_item.setContentLookup(False)
        
        xbmc.Player().play(stream_url,play_item)	
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)

def LiveOnScoreMenu():

    add_item('', 'Soccer', RESOURCES+'liveonscor.png', True, "liveonscoresocmenu", infoLabels=False)
    add_item('http://liveonscore.tv/category/mma-boxing/', 'Mma - boxing', RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    add_item('http://liveonscore.tv/category/motor-sports/', 'Motorsports', RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    add_item('http://liveonscore.tv/category/nba-stream/', 'NBA', RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)

    add_item('http://liveonscore.tv/category/nfl-streams/', 'NFL', RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)

    add_item('', 'Search', RESOURCES+'liveonscor.png', True, "liveonscoresearch", infoLabels=False)

    xbmcplugin.endOfDirectory(addon_handle)	
    
def LiveOnScoreSocMenu():

    add_item("http://liveonscore.tv/category/soccer-streams/premier-league/","Premier League", RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    add_item("http://liveonscore.tv/category/soccer-streams/la-liga/","La Liga", RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    add_item("http://liveonscore.tv/category/soccer-streams/serie-a/","Serie A", RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    add_item("http://liveonscore.tv/category/soccer-streams/england-fa-cup/","England & FA Cup", RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    add_item("http://liveonscore.tv/category/soccer-streams/uefa-europa-league/","UEFA Europa League", RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    add_item("http://liveonscore.tv/category/soccer-streams/england-championship/","England Championship", RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    add_item("http://liveonscore.tv/category/soccer-streams/major-league-soccer/","Major League Soccer", RESOURCES+'liveonscor.png', True, "liveonscorestreams", infoLabels=False)
    xbmcplugin.endOfDirectory(addon_handle)	
    
    
def getLiveOnScoreStreams(urlk=''):
    url = params.get('url', None)

    links,npage = se.getLiveOnScoreStreams(url,urlk)
    if links:
        for f in links:

            ikona=ikony(f.get('image'))
            
            add_item(f.get('href'), f.get('title'),ikona, False,'playLiveOnScore', infoLabels={'plot':f.get('title'),'code':f.get('code')},odtworz=False)	
        if npage:
            add_item(npage, '>> Next page >>',ikona, True,'liveonscorestreams', infoLabels={'plot':f.get('title'),'code':f.get('code')})
        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	

def playLiveOnScore():
    url = params.get('url', None)
    tytul = params.get('title', None)
    
    
    stream_url,zdj = se.getplayLiveOnScore(url)
    if stream_url:

        play_item = xbmcgui.ListItem(path=stream_url,label=tytul)
        play_item.setArt({'thumb': zdj, 'poster': zdj, 'banner': zdj, 'fanart': FANART})
        play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':tytul})
        if six.PY3:
            play_item.setProperty('inputstream', 'inputstream.adaptive')
        else:
            play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        play_item.setProperty("IsPlayable", "true")
        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        play_item.setMimeType('application/vnd.apple.mpegurl')
        play_item.setContentLookup(False)
        
        xbmc.Player().play(stream_url,play_item)

    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)

def getroja():
    url = params.get('url', None)
    links = se.ListROJA(url)	
   
    if links:
        for f in links:
            imag=((f.get('code')).lower()).replace('football','soccer').replace('nba','basketball').replace('boxing','fighting').replace('wwe','fighting').replace('ncaa','basketball')
            if 'ufc' in imag:
                imag='fighting'
            if 'motors' in imag:
                imag='f1'
            add_item(f.get('href'), f.get('title'), RESOURCES+'%s.png'%imag, True, 'linksCR',infoLabels={'code':f.get('code'),'plot':f.get('title')})	
  
    xbmcplugin.setContent(addon_handle, 'videos')
    xbmcplugin.endOfDirectory(addon_handle)	
        
def gettvcom():
    url = params.get('url', None)
    links = se.ListTVCOM1(url)	
    add_item(url, 'Transmisje z dni', RESOURCES+'tvcom.png', True, 'gettvcomdzis')	
    if links:
        for f in links:
            add_item(f.get('href'), f.get('title'), RESOURCES+'tvcom.png', True, 'gettvcom2')	
    xbmcplugin.endOfDirectory(addon_handle)

def gettvcom2():
    url = params.get('url', None)
    links = se.ListTVCOM2(url)	

    if links:
        for f in links:
            add_item(f.get('href'), f.get('title'), RESOURCES+'tvcom.png', True, 'gettvcomdysc')	
    xbmcplugin.endOfDirectory(addon_handle)

def gettvcomdzis():
    url = params.get('url', None)

    links = se.ListTVCOMdzis(url)	
    if links:
        items = len(links)
        if links:
            t = [ x.get('title') for x in links]
            h = [ x.get('href') for x in links]
            al = "Dzień - (nagrania, live, wkrótce)"	
        
            select = xbmcgui.Dialog().select(al, t)
            if select>-1:

                href=h[select]
                linki=se.ListTVCOMlinks(href)

                if linki:
                    for f in linki:
                        add_item(f.get('href'), f.get('title'), RESOURCES+'tvcom.png', False, 'playtvcom',infoLabels={'code':f.get('code'),'plot':f.get('plot'),})	
                    xbmcplugin.setContent(addon_handle, 'videos')
                    xbmcplugin.endOfDirectory(addon_handle)
                else:
                    xbmcgui.Dialog().notification('[COLOR red][B]Uwaga[/B][/COLOR]', '[COLOR red][B] Brak wydarzeń z tego dnia[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000,False)

                    
def gettvcomdysc():
    url = params.get('url', None)	
    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'TE': 'Trailers',}	
    html=requests.get(url,headers=headersok,verify=False,timeout=30).text
    html=html.replace("\'",'"')	
    sportid,sportlig=re.findall('CalendarLeagueVideos\("(.+?)",\s*"(.+?)"',html)[0]
    seas = parseDOM(html,'select', attrs={'id': "season"})[0]
    sez=re.findall('option value="(.+?)"',seas)[0]
    url='https://json.2017.tvcom.cz/Json/Web2017/BottomCalendarSportLeaguePL.aspx?sportId=%s&sportLeagueId=%s&yearId=%s'%(sportid,sportlig,sez)
    linki=se.ListTVCOMlinksDysc(url)
    if len(linki)>10:

        for f in linki:	
            add_item(f.get('href'), f.get('title'), RESOURCES+'tvcom.png', False, 'playtvcom')	
        xbmcplugin.endOfDirectory(addon_handle)
    else:
        linki=se.ListTVCOMlinksDysc2(html)
        if linki:
            for f in linki:	
                add_item(f.get('href'), f.get('title'), f.get('imag'), False, 'playtvcom')	
        xbmcplugin.endOfDirectory(addon_handle)
                    
                    
def PlayTVCOM():
    url = params.get('url', None)
    stream_url = se.getTVCOMstream(url)
    if stream_url:	
        xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=stream_url))

    
def getsportsbay():

    add_item('https://sportsbay.org/page/1', 'All events', RESOURCES+'calendar.png', True, 'getsportsbayschedule')	
    add_item('', 'Most popular', RESOURCES+'soccer.png', True, 'getsportsbaypopular')
    add_item('https://sportsbay.org/sports/football/1', 'Football', RESOURCES+'soccer.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/sports/hockey/1', 'Hockey', RESOURCES+'hockey.png', True, 'getsportsbayschedule')
    add_item('https://sportsbay.org/competition/nfl-football/1', 'NFL', RESOURCES+'football.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/sports/basketball/1', 'Basketball', RESOURCES+'basketball.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/sports/baseball/1', 'Baseball', RESOURCES+'baseball.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/competition/ncaa-football/1', 'NCAA', RESOURCES+'basketball.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/sports/tennis/1', 'Tennis', RESOURCES+'tennis.png', True, 'getsportsbayschedule')
    add_item('https://sportsbay.org/sports/cricket/1', 'Cricket', RESOURCES+'cricket.png', True, 'getsportsbayschedule')
    add_item('https://sportsbay.org/sports/motorsports/1', 'Motorsport', RESOURCES+'f1.png', True, 'getsportsbayschedule')	
    xbmcplugin.endOfDirectory(addon_handle)	
    
def getsportsbayschedule():
    url = params.get('url', None)
    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'TE': 'Trailers',}	
    html=requests.get(url,headers=headersok,verify=False,timeout=30).text
    html=html.replace("\'",'"')	
    result = parseDOM(html,'tbody')[0]
    links = parseDOM(result,'tr')
    npage = parseDOM(html,'div', attrs={'class': "loadmore"})

    for link in links:
        dt = parseDOM(link,'th')
        if dt:
            data = dt[0]
            title='[B][COLOR blue]						%s[/B][/COLOR]'%data
            add_item('', title, RESOURCES+'calendar.png', True, '', infoLabels=False, pusto=True)
            continue
        czas = parseDOM((parseDOM(link,'td', attrs={'class': "time dtstart"})[0]),'span')[0]
        czas=czas.split(':')

        hrs =int(czas[0])+6
        min=int(czas[1])
        if hrs >23:
            hrs = hrs-24
            czas =".%02d:%02d" % (hrs, min)
        else:
            czas ="%02d:%02d" % (hrs, min)

        imagi = parseDOM((parseDOM(link,'td', attrs={'class': "type"})[0]),'img',ret='src')[0]

        ikona=ikony(imagi)
        if 'american football' in imagi.lower():
            ikona = RESOURCES+'football.png'

        competition = parseDOM((parseDOM(link,'td', attrs={'class': "competition"})[0]),'a')[0] #<td class="competition">
        event = parseDOM((parseDOM(link,'td', attrs={'class': "event"})[0]),'span',ret='title')[0]#<td class="event">
        href = parseDOM((parseDOM(link,'td', attrs={'class': "play"})[0]),'a',ret='href')[0]#<td class="play">
        tytul = u'[B]%s [COLOR gold]%s[/COLOR][COLOR khaki] - %s [/COLOR][/B]'%(czas,event,competition)
        add_item('https://sportsbay.org'+href, tytul, ikona, True, 'getsportsbayLinks')
    
    if npage:
        href = 'https://sportsbay.org'+parseDOM(npage[0],'a',ret='href')[0]
        add_item(href, 'Next page', RESOURCES+'nextpage.png', True, 'getsportsbayschedule')
    xbmcplugin.endOfDirectory(addon_handle)	

def getsportsbaypopular():
    add_item('https://sportsbay.org/competition/english-premier-league/1', 'English Premier League', 'https://github.com/Proximus2000/mb-support/raw/master/flags/prlig.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/competition/uefa-champions-league/1', 'UEAFA Champions League', 'https://github.com/Proximus2000/mb-support/raw/master/flags/champlig.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/competition/uefa-europa-league/1', 'UEAFA Europa League', 'https://github.com/Proximus2000/mb-support/raw/master/flags/eurlig.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/competition/germany-bundesliga/1', 'Germany Bundesliga', 'https://github.com/Proximus2000/mb-support/raw/master/flags/bundesli.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/competition/french-ligue-1/1', 'French Ligue 1', 'https://github.com/Proximus2000/mb-support/raw/master/flags/lig1.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/competition/primera-division-espana/1', 'Spain Primera Division', 'https://github.com/Proximus2000/mb-support/raw/master/flags/lalig.png', True, 'getsportsbayschedule')	
    add_item('https://sportsbay.org/competition/italy-serie-a/1', 'Italy Serie A', 'https://github.com/Proximus2000/mb-support/raw/master/flags/seriea.png', True, 'getsportsbayschedule')	
    xbmcplugin.endOfDirectory(addon_handle)
    
def getSportsbaychan():
    url = params.get('url', None)
    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'TE': 'Trailers',}	
    html=requests.get(url,headers=headersok,verify=False,timeout=10).text
    html=html.replace("\'",'"')	
    links=parseDOM(html,'tr', attrs={'class': "vevent"})#<tr id="45711" class="vevent"
    
    for link in links:
        kraj=''
        try:
            kraj = parseDOM((parseDOM(link,'td', attrs={'class': "country"})[0]),'span', attrs={'title': ".+?"},ret='title')[0]
        except:
            pass
        event = parseDOM(link,'td', attrs={'class': "event"})[0]
        tyt = parseDOM(event,'a', ret='title')[1]
        href = parseDOM(event,'a', ret='href')[0]
        imag = parseDOM(event,'img', ret='src')[0]
        imag = 'https:'+imag if imag.startswith('//') else imag#<img src="//1079020916.rsc.cdn77.org/images/teams/Logo-The-Tennis-Channel.png"
        tytul = u'[B][COLOR gold]%s[/B][/COLOR][COLOR khaki] (%s)[/COLOR]'%(tyt,kraj)

        add_item('https://sportsbay.org'+href, tytul, imag, True, 'getsportsbayLinks')
    
    xbmcplugin.endOfDirectory(addon_handle)		

def getsportsbayLinks():

    url = params.get('url', None)
    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'TE': 'Trailers',}	
    html=requests.get(url,headers=headersok,verify=False,timeout=10).text
    html=html.replace("\'",'"')	
    result=parseDOM(html,'div', attrs={'id': 'content'})[0] #<div id="content" class="vevent streamview">
    imag = parseDOM(result,'img', ret='src')[0]
    imag = 'https:'+imag if imag.startswith('//') else imag
    tyt = parseDOM(result,'span', ret='title')[0]
    links =parseDOM(result,'p', attrs={'class': 'buttons'})#[0]
    if links:
        links = links[0]

        zrodla = re.findall("""a href=['"](.+?)['"]""",links)
    else:
        links = parseDOM(result,'div', attrs={'class': 'player'})[0]
        zrodla = parseDOM(result,'iframe', ret='src')#attrs={'class': 'player'})[0]
    #<div class='player'>
    co=1
    for href in zrodla:
        if href.startswith('/'): href = 'https://sportsbay.org'+href
        #href='https://sportsbay.org'+href
        tytul = '%s - Link %s'%(tyt,co)
        add_item(href, u'[COLOR lime]► [/COLOR][B][COLOR gold]'+tytul+'[/B][/COLOR]', imag, False, 'playsportsbaytv')
        co+=1	
    xbmcplugin.endOfDirectory(addon_handle)		
    
def playsportsbaytv():

    url = params.get('url', None)

    UAipad = 'AppleCoreMedia/1.0 ( iPad; compatible; 3ivx HLS Engine/2.0.0.382; Win8; x64; 264P AACP AC3P AESD CLCP HTPC HTPI HTSI MP3P MTKA)'
    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',}
    headersok = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0_1 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A402 Safari/604.1',
        'Accept': '*/*',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Origin': 'https://espn-live.stream',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://espn-live.stream/',
    }
    html=requests.get(url,headers=headersok,verify=False,timeout=30)#.text
    headersok3 = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0_1 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A402 Safari/604.1',
        'Accept': '*/*',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Origin': 'https://espn-live.stream',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://espn-live.stream/',
    }
    sc = html.cookies
    xbmc.log('kukis : %s' % str(sc), LOGNOTICE)
    html=html.text
    
    html=html.replace("\'",'"')	
    src = clappr.findall(html)#[0]

    if src:

        stream=src[0]+'|User-Agent='+UA+'&Referer='+url	
        xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=stream))

    else:

        if '"dash":' in html or '"hls":' in html:
            src = re.findall('"dash":\s*"(.+?)"',html)
            if src:
                src = src[0]
                tt = 'mpd'
            else:
                src = re.findall('"hls":\s*"(.+?)"',html)[0]
                tt = 'hls'
            #if 'function override(url)' in html:
            
            #else:
                
            headersok2 = {'User-Agent': UAipad,'Referer': url}
            hea= '&'.join(['%s=%s' % (name, value) for (name, value) in headersok2.items()])	
    
            play_item = xbmcgui.ListItem(path=src)
            if six.PY3:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
            else:
                play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', tt)
            play_item.setProperty('inputstream.adaptive.stream_headers', hea)
            play_item.setProperty('inputstream.adaptive.license_key', "|" + hea)
            play_item.setMimeType("application/x-mpegURL")
            play_item.setContentLookup(False)

            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        #	return 
        elif 'text/javascript">var _0x' in html:
            script =re.findall('(var _0x.*?)<\/script>',html,re.DOTALL)[0]	
            import getkeyTelerium as TRD
            decscript = TRD.getkey(script)
            scriptdeco = decscript.replace("'+'",'').replace("\'",'"').replace('"+"','')
            import mydecode

            mpd, lic_url,data  = mydecode.espnstreamget(scriptdeco)

            headersok2 = {'User-Agent': UA,'Referer': url}
            hea= '&'.join(['%s=%s' % (name, value) for (name, value) in headersok2.items()])	
            PROTOCOL = 'mpd'
            DRM = 'com.widevine.alpha'
            play_item = xbmcgui.ListItem(path=mpd)
            
            if six.PY3:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
            else:
                play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
            play_item.setProperty('inputstream.adaptive.license_type', DRM)

            play_item.setProperty('inputstream.adaptive.license_key',lic_url+'|'+hea+'|'+data+'|')					
            play_item.setProperty('inputstream.adaptive.license_flags', "persistent_storage")
            
            
            play_item.setMimeType("application/x-mpegURL")
            play_item.setContentLookup(False)

            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        else:
            src = re.findall('var source = "(.+?)"',html)
            if src:
                #from urlparse import urlparse
                parsed_url = urllib_parse.urlparse(src[0])

                cdn = parsed_url.netloc

                if not 'nhl.com' in cdn: 

                    repl = re.findall('source\.replace\(cdn, "(.+?)"',html)
                    if repl:
                        str1 = src[0].replace(cdn, repl[0])
                        ntrepl = re.findall('source\.replace\(".m3u8", "(.+?)"',html)
                        if ntrepl:
                            str1 = str1.replace('.m3u8',ntrepl[0])
                        
                        ab=''
                    keyurl,replkey  = re.findall('rewrittenUrl\s*=\s*url;.+?\(url.indexOf\("(.+?)"\).+?rewrittenUrl = "(.+?)"',html,re.DOTALL)[0]
                    try:
                        addon.setSetting('replkey',replkey)	
                        addon.setSetting('keyurl',keyurl)	
                    except:
                        addon.setSetting('replkey','')	
                        addon.setSetting('keyurl','')
                    stream=src[0]
                    hea= '&'.join(['%s=%s' % (name, value) for (name, value) in headersok3.items()])
                    try:
                        addon.setSetting('streamMLB',stream)	
                        addon.setSetting('heaMLB',str(headersok3))
                    except:
                        addon.setSetting('streamMLB','')	
                        addon.setSetting('heaMLB','')	
                    stream = PROXY_PATH='http://127.0.0.1:%s/manifest='%(str(proxyport))+stream
                    PROXY_PATH2='http://127.0.0.1:%s/license='%(str(proxyport))#+stream
                    
                else:

                    replkey  = re.findall('var replace = "(.+?)"',html)
                    keyurl  = re.findall('var keyurl = "(.+?)"',html)
                    try:
                        addon.setSetting('replkey',replkey[0])	
                        addon.setSetting('keyurl',keyurl[0])	
                    except:
                        addon.setSetting('replkey','')	
                        addon.setSetting('keyurl','')
                    str1 = src[0]
                    stream=str1
                    hea= '&'.join(['%s=%s' % (name, value) for (name, value) in headersok3.items()])
                    try:
                        addon.setSetting('streamNHL',stream)	
                        addon.setSetting('heaNHL',str(headersok3))
                    except:
                        addon.setSetting('streamNHL','')	
                        addon.setSetting('heaNHL','')	


                    stream = PROXY_PATH='http://127.0.0.1:%s/manifest='%(str(proxyport))+stream
                    PROXY_PATH2='http://127.0.0.1:%s/license='%(str(proxyport))#+stream
                    #html=requests.get(stream,headers=headersok3,verify=False,timeout=30).text

                headersok2 = {
                'User-Agent': UAipad,
                'Referer': url}

                hea= '&'.join(['%s=%s' % (name, value) for (name, value) in headersok2.items()])	


                hea= '&'.join(['%s=%s' % (name, value) for (name, value) in headersok3.items()])

                play_item = xbmcgui.ListItem(path=stream+'|'+hea)

                if six.PY3:
                    play_item.setProperty('inputstream', 'inputstream.adaptive')
                else:
                    play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
                
                play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                play_item.setProperty('inputstream.adaptive.stream_headers', hea)
                play_item.setProperty('inputstream.adaptive.license_key', '|'+hea)

                xbmc.log('Blad w : %s' % stream, LOGNOTICE)

                xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

            else:

                import mydecode
                stream = mydecode.decode(url,html)
                play_item = xbmcgui.ListItem(path=stream)
    
                xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
            #	return ok

def LiveSched():
    add_item('cricfree', 'Crickfree', RESOURCES+'crfree.png', True, 'scheduleCR')	
    add_item('http://strims.top', 'Strims Top (strumyk.tv)', RESOURCES+'sworld.png', True, 'scheduleSW')		
    xbmcplugin.endOfDirectory(addon_handle)	
    
def LiveChannels():
    links=[]
    links.append({'href':'cricfree',					 'title':'Crickfree',		'img':RESOURCES+'crfree.png',		'mode':'channelsCR'	})	
    links.append({'href':'http://strims.top',			'title':'Strims Top (Strumyk.tv)',		'img':RESOURCES+'sworld.png',		'mode':'channelsSW'	})	
    links.append({'href':'http://unblocked.is/tv',		'title':'Unblocked.is',		'img':RESOURCES+'unbl.png',			'mode':"unblocked"	})	
    links.append({'href':'https://sportsbay.org/sports/tv-channels/1',		'title':'Sportsbay',		'img':RESOURCES+'logosb.png',			'mode':"getsportsbayschedule"	})	

    for f in links:
        add_item(f.get('href'), f.get('title'), f.get('img'), True, f.get('mode'))	
    xbmcplugin.endOfDirectory(addon_handle)	
    
def ListStrimW():
    add_item('','[COLOR gold]Streams[/COLOR]', RESOURCES+'calendar.png', True, 'scheduleSW')	
    add_item('','[COLOR gold]Channels[/COLOR]', RESOURCES+'chan2.png', True, 'channelsSW')	
    xbmcplugin.endOfDirectory(addon_handle)	

def setUnblockKuk():	
    import uuid
    hash = uuid.uuid4().hex					
    aa='1679497221'
    kuk='__ddgu=%s.%s'%(hash,aa)		
    addon.setSetting('unbkuk',kuk)
    return kuk

def ListUnblocked():
    url = params.get('url', None)
    links = se.ListUnblocked(url)	
    if links:
        for f in links:
            add_item(f.get('href'), f.get('title'), RESOURCES+'unbl.png', True, 'getUnbLinks')	
    xbmcplugin.endOfDirectory(addon_handle)		
    
def getUnbLinks():
    url = params.get('url', None)
    tyt = params.get('title', None)
    add_item(url, '[COLOR lime]► [/COLOR] [B][COLOR gold] Link 1 - %s[/COLOR]'%tyt, RESOURCES+'unbl.png', False, 'linksSW2')
    add_item(url+'?player=1', '[COLOR lime]► [/COLOR] [B][COLOR gold] Link 2 - %s[/COLOR]'%tyt, RESOURCES+'unbl.png',False, 'linksSW2')	
    xbmcplugin.endOfDirectory(addon_handle)	
    
def ListStreamendous():
    url = params.get('url', None)
    mod='CR'
    if 'streamendous' in url:
        mod='SE'
    add_item('','[COLOR gold]Schedule[/COLOR]', RESOURCES+'calendar.png', True, 'schedule%s'%mod)			
    add_item('','[COLOR gold]Channels[/COLOR]', RESOURCES+'chan2.png', True, 'channels%s'%mod)	
    xbmcplugin.endOfDirectory(addon_handle)	
    
def getSuperSport():		
    add_item('https://supersportowo.com/stream1.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Canal+ HD[/COLOR][/B]', "https://i.imgur.com/UUCy060.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream2.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Canal+ Sport HD[/COLOR][/B]', "https://i.imgur.com/mqnZ2Io.png", False, "playsupersportowo")		
    add_item('https://supersportowo.com/stream3.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Canal+ Sport 2 HD[/COLOR][/B]', "https://i.imgur.com/UYxVd2W.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream4.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eurosport HD[/COLOR][/B]', "https://i.imgur.com/yCgj02s.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream5.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eurosport 2 HD[/COLOR][/B]', "https://i.imgur.com/3IA1QAd.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream6.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]nSport+ HD[/COLOR][/B]', "https://i.imgur.com/GDTICof.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream7.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]TVP Sport HD[/COLOR][/B]', "https://i.imgur.com/A34dfve.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream8.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eleven Sports 1 HD[/COLOR][/B]', "https://i.imgur.com/6KvZtpg.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream9.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eleven Sports 2 HD[/COLOR][/B]', "https://i.imgur.com/yt3tfHm.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream10.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eleven Sports 3 HD[/COLOR][/B]', "https://i.imgur.com/FQkKANW.png", False, "playsupersportowo")	
    add_item('https://supersportowo.com/stream11.html', '[COLOR lime]► [/COLOR] [B][COLOR gold]Polsat Sport HD[/COLOR][/B]', "https://i.imgur.com/VkY8zNV.png", False, "playsupersportowo")	

    
    
def getLiveSport():
    links = se.getLiveSport()
    if links:
        for f in links:
            if 'kiedy' in f.get('href'):
                title=(f.get('href')).split('|')[1]
                title='[B][COLOR blue]						%s[/B][/COLOR]'%title
                add_item('', title, RESOURCES+'calendar.png', True, '', infoLabels=False, pusto=True)
            else:
                ikona=ikony(f.get('image'))
                add_item(f.get('href'), f.get('title'), ikona, False,'getLinksLiveSport', infoLabels={'plot':f.get('title'),'code':f.get('code')},odtworz=False)			

        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	
        
def getLinksLiveSport():

    
    url = params.get('url', None)
    tytul = params.get('title', None)
    links = se.getLinksLiveSport(url,tytul)
    
    

    
    items = len(links)
    if links:
        t = [ x.get('title') for x in links]
        u = [ x.get('href') for x in links]
        al = "Links"	
    
        if items>1:	
            select = xbmcgui.Dialog().select(al, t)
            
            if select > -1:
                link = u[select];	
                stream_url = se.getStreamLiveSport(link)	
    
            else:
                quit()
        else:
            link = u[0];
            stream_url = se.getStreamLiveSport(link)	
        if stream_url:
            if 'youtube.com' in stream_url or 'youtu.be' in stream_url:
                stream_url = resolveurl.resolve(stream_url)
            play_item = xbmcgui.ListItem(path=stream_url,label=tytul)
            play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':tytul})
            if six.PY3:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
            else:
                play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
            play_item.setProperty("IsPlayable", "true")
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            play_item.setMimeType('application/vnd.apple.mpegurl')
            play_item.setContentLookup(False)

            xbmc.Player().play(stream_url,play_item)
        else:
            xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)
            return	
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]No links available.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)	
        return	
    return

def PlayLiveSport():
    url = params.get('url', None)
    tytul = params.get('title', None)
    stream_url = se.getStreamLiveSport(url)	

    is_helper = inputstreamhelper.Helper('hls')
    if is_helper.check_inputstream():
        play_item = xbmcgui.ListItem(path=stream_url)
        if six.PY3:
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
        else:
            play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
       #play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        play_item.setMimeType('application/x-mpegurl')
        play_item.setContentLookup(False)
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

        
def GetSwfolder():

    url = params.get('url', None)
    
    if '/f1/' in url: #katalog z F1-> pominięcie archiwum i potraktowanie jak strony z linkami
        return getStreamsSW()

    links = se.getScheduleSWfolder(url)  
    if links:
        for f in links:

            ikona=ikony(f.get('image'))

            ab = f.get('href')
            if ab=='':
                add_item(ab, '[COLOR blue][B]'+f.get('title')+'[/B][/COLOR]', RESOURCES+'calendar.png', True, '', infoLabels=False, pusto=True)
            else:
                if ab.endswith('/'):
                    add_item(ab, '[COLOR yellow]'+f.get('title')+'[/COLOR]', ikona, True,'streamsSWfolder', odtworz=False)
                else:
                    add_item(ab, '[COLOR yellow]'+f.get('title')+'[/COLOR]', ikona, False,'streamsSW', odtworz=False)				
    
        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]No schedule links.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)	
        
def getScheduleSW():
     
    links = se.getScheduleSW()

    if links:
        for f in links:
            if 'kiedy' in f.get('href'):
                title=(f.get('href')).split('|')[1]
                title='[B][COLOR blue]<<<%s>>>[/B][/COLOR]'%title
                add_item('', title, RESOURCES+'calendar.png', True, '', infoLabels=False, pusto=True)
            else:
                ikona=ikony(f.get('image'))
                ab = f.get('href')
                if ab.endswith('/'):
                    add_item(ab, f.get('title'), ikona, True,'streamsSWfolder', odtworz=False)
                else:
                    add_item(ab, f.get('title'), ikona, False,'streamsSW', odtworz=False)				

        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]No schedule links.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)	

def getScheduleSstreams():

    links = se.getScheduleSstreams()
    if links:
        for f in links:
            add_item(f.get('href'), f.get('title'), f.get('image'), False, 'streamsSstreams',infoLabels={'plot':f.get('title'),'code':f.get('code')})				

        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]No schedule links.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)	
    
        
        
        
def getScheduleCR():
    links = se.getScheduleCR()
    if links:
        for f in links:
            if 'kiedy' in f.get('href'):
                title=(f.get('href')).split('|')[1]
                title='[B][COLOR blue]						%s[/B][/COLOR]'%title
                add_item('', title, RESOURCES+'calendar.png', True, '', infoLabels=False, pusto=True)
            else:
                imag=((f.get('code')).lower()).replace('football','soccer').replace('nba','basketball').replace('boxing','fighting').replace('wwe','fighting').replace('ncaa','basketball')
                if 'ufc' in imag:
                    imag='fighting'
                if 'motors' in imag:
                    imag='f1'
                add_item(f.get('href'), f.get('title'), RESOURCES+'%s.png'%imag, False, 'linksCR',infoLabels={'code':'[COLOR lightgreen][B]'+f.get('code')+'[/B][/COLOR]','plot':f.get('title')})	
        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]No schedule links.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)	

#canalsport_2.php
def getChannelsSW():
    add_item("http://strims.top/live/e1.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Eleven Sports 1[/COLOR][/B]', "http://epg.ovh/logo/Eleven+Sports+1.png", False, 'streamsSW2', odtworz=False) # , '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport[/COLOR][/B]', "http://epg.ovh/logo/Eleven+Sports+1.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/e2.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Eleven Sports 2[/COLOR][/B]', "http://epg.ovh/logo/Eleven+Sports+2.png", False, 'streamsSW2', odtworz=False)#, '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport[/COLOR][/B]', "http://epg.ovh/logo/Eleven+Sports+2.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/cs.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport[/COLOR][/B]', "http://epg.ovh/logo/Canal++Sport.png", False, 'streamsSW2', odtworz=False) #, '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport[/COLOR][/B]', "http://epg.ovh/logo/Canal++Sport.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/canalsport_2.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport(rezerw)[/COLOR][/B]', "http://epg.ovh/logo/Canal++Sport.png", False, 'streamsSW2', odtworz=False) #, '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport[/COLOR][/B]', "http://epg.ovh/logo/Canal++Sport.png", False, 'streamsSW2', odtworz=False)    
    #add_item("http://strims.top/tv/canalsport2_2.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport 2(rezerw)[/COLOR][/B]', "http://epg.ovh/logo/Canal++Sport+2.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/cs2.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport 2[/COLOR][/B]', "http://epg.ovh/logo/Canal++Sport+2.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/live/cs2.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport 2[/COLOR][/B]', "http://epg.ovh/logo/Canal++Sport+2.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/ps.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Polsat Sport[/COLOR][/B]', "http://epg.ovh/logo/Polsat+Sport.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/pse.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Polsat Sport Extra[/COLOR][/B]', "https://i.imgur.com/YrZBH5Z.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/es1.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Eurosport[/COLOR][/B]', "http://epg.ovh/logo/Eurosport.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/es2.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Eurosport 2[/COLOR][/B]', "http://epg.ovh/logo/Eurosport+2.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/ns.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]NSport[/COLOR][/B]', "https://i.imgur.com/POFALS0.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/live/tvps.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]TVPSport[/COLOR][/B]', "http://epg.ovh/logo/TVP+Sport.png", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=bbtsp1", '[COLOR lime] ► [/COLOR] [B][COLOR gold]BT SPORT 1[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=bbtsp2", '[COLOR lime] ► [/COLOR] [B][COLOR gold]BT SPORT 2[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=bbtsp3", '[COLOR lime] ► [/COLOR] [B][COLOR gold]BT SPORT 3[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=bbtespn", '[COLOR lime] ► [/COLOR] [B][COLOR gold]BT SPORT ESPN[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skyspnews", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports News[/COLOR][/B]', "http://epg.ovh/logo/Sky+Sports+News.png", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skysare", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports Arena[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skyspnews", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports Main Event[/COLOR][/B]', "https://i.imgur.com/3PRJ8wr.png", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skysprem", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports Premier League[/COLOR][/B]', "https://i.imgur.com/3PRJ8wr.png", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skysfott", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports Football[/COLOR][/B]', "https://i.imgur.com/hiWZR8p.jpeg", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skysact", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports Action[/COLOR][/B]', "https://i.imgur.com/AcrjYK8.png", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skysfor1", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports F1[/COLOR][/B]', "https://i.imgur.com/suOnoEs.png", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skyscric", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports Cricket[/COLOR][/B]', "https://i.imgur.com/R1HXQ68.jpg", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skysgol", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports Golf[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=skysmixx", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Sky Sports Mix[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=eurosp1", '[COLOR lime] ► [/COLOR] [B][COLOR gold]EUROSPORT 1 UK[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=eurosp2", '[COLOR lime] ► [/COLOR] [B][COLOR gold]EUROSPORT 2 UK[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=usafox1", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Fox Sport 1[/COLOR][/B]', "https://i.imgur.com/2Ex4jgi.jpeg", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=usafox2", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Fox Sport 2[/COLOR][/B]', "https://i.imgur.com/aBgxN8I.jpg", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=espnusa", '[COLOR lime] ► [/COLOR] [B][COLOR gold]ESPN[/COLOR][/B]', "http://epg.ovh/logo/ESPN.png", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=espn2", '[COLOR lime] ► [/COLOR] [B][COLOR gold]ESPN2[/COLOR][/B]', "http://epg.ovh/logo/ESPN+2.png", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=premieru", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Premier Sports 1[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://castfree.me/embed.php?player=desktop&live=hdchnl2", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Premier Sports 2[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    
    add_item("http://strims.top/tv/tennischannel.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Tennis Channel[/COLOR][/B]', "https://i.imgur.com/SYh1XSX.png", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/tv/beinxtra.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]BEIN Xtra[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("https://embedstream.me/nba-tv-stream-1", '[COLOR lime] ► [/COLOR] [B][COLOR gold]NBA TV[/COLOR][/B]', "https://i.imgur.com/G7NmIs7.png", False, 'streamsSW2', odtworz=False)#todo
    add_item("https://embedstream.me/nfl-network-stream-1", '[COLOR lime] ► [/COLOR] [B][COLOR gold]NFL Network[/COLOR][/B]', "https://i.imgur.com/1D21agq.jpeg", False, 'streamsSW2', odtworz=False)#todo
    add_item("http://strims.top/tv/fightnetwork.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Fight Network[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/tv/fightsportstv.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Fight Sports TV[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    add_item("http://strims.top/tv/impactwrestling.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Impact Wrestling[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    
    add_item("http://strims.top/l/TVN24.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]TVN24[/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    
    #add_item("", '[COLOR lime] ► [/COLOR] [B][COLOR gold][/COLOR][/B]', "", False, 'streamsSW2', odtworz=False)
    
    
    #add_item("http://strims.top/live/espnu.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]ESPN U[/COLOR][/B]', "http://epg.ovh/logo/ESPN+US.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/nbcsn.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]NBCSN[/COLOR][/B]', "https://i.imgur.com/zWLKpx4.jpeg", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/olympic.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Olympic Channel[/COLOR][/B]', "https://i.imgur.com/rsEzakt.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/golftv.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Golf TV[/COLOR][/B]', "https://i.imgur.com/uOfnnEz.png", False, 'streamsSW2', odtworz=False)
    
    #add_item("http://strims.top/tv/realtv.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Real Madrid TV[/COLOR][/B]', "https://i.imgur.com/ofDzqEz.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/bayerntv.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Bayern TV[/COLOR][/B]', "https://i.imgur.com/rjpd1qW.jpeg", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/mutv.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]MU TV[/COLOR][/B]', "https://i.imgur.com/osIoxdx.jpeg", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/mlbnetwork.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]MLB Network[/COLOR][/B]', "https://i.imgur.com/03SxlGv.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/redbulltv.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]RedBull TV[/COLOR][/B]', "https://i.imgur.com/40jXktK.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/tvpinfo.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]TVP Info[/COLOR][/B]', "https://i.imgur.com/Tx13btL.jpeg", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/tvppolonia.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]TVP Polonia[/COLOR][/B]', "https://i.imgur.com/md0Z9WV.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/republica.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]TV REPUBLIKA[/COLOR][/B]', "https://i.imgur.com/yH1mOfB.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/dw.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Deutsche Welle[/COLOR][/B]', "https://i.imgur.com/nXnm93M.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/rtnews.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Russia Today[/COLOR][/B]', "https://i.imgur.com/t4IasEv.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/aljazeera.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Al-Jazeera[/COLOR][/B]', "https://i.imgur.com/ZLY2lF9.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/cbsnews.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]CBS news[/COLOR][/B]', "https://i.imgur.com/Vq1TvOJ.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/france24.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]France24[/COLOR][/B]', "https://i.imgur.com/MmhMBkC.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/bloombergus.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Bloomberg US[/COLOR][/B]', "https://i.imgur.com/AAd6ST4.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/skynews.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]SKY News[/COLOR][/B]', "https://i.imgur.com/uRQ8t0q.jpg", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/weather.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]The Weather Channel[/COLOR][/B]', "https://i.imgur.com/xVlB96b.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/nasa.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Nasa[/COLOR][/B]', "https://i.imgur.com/QUAi0Or.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/tnt.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]TNT[/COLOR][/B]', "https://i.imgur.com/AegYixv.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/abc.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]ABC[/COLOR][/B]', "https://i.imgur.com/FMdgGl0.jpeg", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/hbo.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]HBO[/COLOR][/B]', "https://i.imgur.com/3w1l19K.png", False, 'streamsSW2', odtworz=False)
    #add_item("http://strims.top/tv/4funtv.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]4fun.tv[/COLOR][/B]', "https://i.imgur.com/Tjo882m.jpg", False, 'streamsSW2', odtworz=False)


  #  add_item("http://strims.top/tv/canalsport.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Canal + Sport[/COLOR][/B]', "http://epg.ovh/logo/Canal++Sport.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/polsatsport.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Polsat Sport[/COLOR][/B]', "http://epg.ovh/logo/Polsat+Sport.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/polsatsportextra.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Polsat Sport Extra[/COLOR][/B]', "http://epg.ovh/logo/Polsat+Sport+Extra.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/eurosport.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Eurosport[/COLOR][/B]', "http://epg.ovh/logo/Eurosport.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/eurosport2.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]Eurosport 2[/COLOR][/B]', "http://epg.ovh/logo/Eurosport+2.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/espn.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]ESPN[/COLOR][/B]', "http://epg.ovh/logo/ESPN.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/espn2.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]ESPN 2[/COLOR][/B]', "http://epg.ovh/logo/ESPN+2.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/espnu.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]ESPN U[/COLOR][/B]', "http://epg.ovh/logo/ESPN+US.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/skysportnews.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]SKY SPORT NEWS[/COLOR][/B]', "http://epg.ovh/logo/Sky+Sports+News.png", False, 'streamsSW2', odtworz=False)	
  #  add_item("http://strims.top/tv/nbcsn.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]NBCSN[/COLOR][/B]', "https://i.imgur.com/vcqi9Hb.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/nbatv.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]NBA TV[/COLOR][/B]', "https://i.imgur.com/IooE7PF.png", False, 'streamsSW')			
  #  add_item("http://strims.top/tv/tennistv.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]Tennis TV[/COLOR][/B]', "https://i.imgur.com/JTWxqrd.png", False, 'streamsSW')			
  #  add_item("http://strims.top/tv/mlbnetwork.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]MLB TV[/COLOR][/B]', "https://i.imgur.com/Jlju3ox.png", False, 'streamsSW2', odtworz=False)		
  #  add_item("http://strims.top/tv/golftv.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]GOLF TV[/COLOR][/B]', "https://i.imgur.com/uOfnnEz.png", False, 'streamsSW2', odtworz=False)			
  #
  #  add_item("http://strims.top/tv/nhlnetwork.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]NHL TV[/COLOR][/B]', "https://i.imgur.com/U3BgbZH.png", False, 'linksSW')	
  #  add_item("http://strims.top/tv/realtv.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]Real TV[/COLOR][/B]', "https://i.imgur.com/ofDzqEz.png", False, 'linksSW')	
  #
  #  add_item("http://strims.top/tv/f1base.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]F1 Base[/COLOR][/B]', "https://i.imgur.com/K5scJB9.png", False, 'streamsSW')		
  #  add_item("http://strims.top/tv/f1base.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]F1 FULL VIDEO REPLAYS [/COLOR][/B]', "https://i.imgur.com/K5scJB9.png", True, 'channF1')		
  #  add_item("http://strims.top/tv/f1base.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]KSW & FAME MMA [/COLOR][/B]', "https://i.imgur.com/BS0tUI0.png", True, 'chanksw')	
  #  add_item("http://strims.top/tv/redbulltv.php", '[COLOR lime] ► [/COLOR] [B][COLOR gold]RED BULL TV[/COLOR][/B]', "https://i.imgur.com/40jXktK.png", False, 'streamsSW2', odtworz=False)		
  #
    
#F1 FULL VIDEO REPLAYS 
#	add_item("http://strims.top/live/tennistv2.php", '[COLOR lime]► [/COLOR] [B][COLOR gold]Tennis TV[/COLOR][/B]', "https://i.imgur.com/JTWxqrd.png", False, 'streamsSW')			
    xbmcplugin.setContent(addon_handle, 'videos')	
    xbmcplugin.endOfDirectory(addon_handle)	
    
def StrimsTv():
    add_item('http://strims.tv/tv5/cs.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Canal+ Sport[/COLOR][/B]', "https://i.imgur.com/mqnZ2Io.png", False, 'playStrimsTv')		
    add_item('http://strims.tv/tv5/cs2.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Canal+ Sport 2[/COLOR][/B]', "https://i.imgur.com/UYxVd2W.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/e1.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eleven Sports 1[/COLOR][/B]', "https://i.imgur.com/6KvZtpg.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/e2.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eleven Sports 2[/COLOR][/B]', "https://i.imgur.com/yt3tfHm.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/e3.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eleven Sports 3[/COLOR][/B]', "https://i.imgur.com/FQkKANW.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/ps.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Polsat Sport[/COLOR][/B]', "https://i.imgur.com/VkY8zNV.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/pse.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Polsat Sport EXTRA[/COLOR][/B]', "https://i.imgur.com/PBOxzIJ.png", False, 'playStrimsTv')	
    
    add_item('http://strims.tv/tv5/psp1.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Polsat Sport Premium 1[/COLOR][/B]', "https://i.imgur.com/mQXMgAD.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/psp2.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Polsat Sport Premium 2[/COLOR][/B]', "https://i.imgur.com/3m0RZFs.png", False, 'playStrimsTv')	
    
    
    add_item('http://strims.tv/tv5/es1.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eurosport[/COLOR][/B]', "https://i.imgur.com/yCgj02s.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/es2.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Eurosport 2[/COLOR][/B]', "https://i.imgur.com/3IA1QAd.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/ns.php  ', '[COLOR lime]► [/COLOR] [B][COLOR gold]nSport+[/COLOR][/B]', "https://i.imgur.com/GDTICof.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/tvps.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]TVP Sport[/COLOR][/B]', "https://i.imgur.com/A34dfve.png", False, 'playStrimsTv')	
    add_item('http://strims.tv/tv5/sp.php', '[COLOR lime]► [/COLOR] [B][COLOR gold]Super Polsat[/COLOR][/B]', "https://i.imgur.com/WMM1NnQ.png", False, 'playStrimsTv')	
    xbmcplugin.setContent(addon_handle, 'videos')	
    xbmcplugin.endOfDirectory(addon_handle)	


def chanksw():
    #url = params.get('url', None)
    channels = se.KSWchannels()
    if channels:
        for f in channels:
            add_item(f.get('href'), f.get('title'), RESOURCES+'chan2.png', False,'streamsSW')	
    xbmcplugin.setContent(addon_handle, 'videos')	
    xbmcplugin.endOfDirectory(addon_handle)	
    
def PlayStrimsTv():
    url = params.get('url', None)
    #url = params.get('url', None)
    
    #r = requests.get(
    #	url, 
    #	verify=False)	
    data=''
    import mydecode
    stream_url = mydecode._strimstv(url,data,url)
    if stream_url:
        play_item = xbmcgui.ListItem(path=stream_url)
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    
    
    
def getChannelsCR():
    channels = se.getChannelsCR()
    if channels:
        for f in channels:
            add_item(f.get('href'), f.get('title'), RESOURCES+'chan2.png', False, 'linksCR')		
    xbmcplugin.setContent(addon_handle, 'videos')	
    xbmcplugin.endOfDirectory(addon_handle)		

def playcr():
    url = params.get('url', None)
    
    stream_url=se.resolvingCR(url,url)
    if stream_url:
        play_item = xbmcgui.ListItem(path=stream_url)
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', "[COLOR red][B]Can't resolve this link.[/B][/COLOR]", xbmcgui.NOTIFICATION_INFO, 5000)
        play_item = xbmcgui.ListItem(path=stream_url)
        
        xbmcplugin.setResolvedUrl(addon_handle, False, listitem=play_item)
        return
    
    
    
def getLinksCR():
    url = params.get('url', None)

    if 'roja:' in url:
        links = eval(urllib_parse.unquote(url.split(':')[1]))
    else:
        links=se.getCRlink(url)
    stream_url=''
    items = len(links)
    if links:
        for f in links:
            add_item(f.get('href'), f.get('title'), RESOURCES+'chan2.png', False, 'playcr')		
    xbmcplugin.setContent(addon_handle, 'videos')	
    xbmcplugin.endOfDirectory(addon_handle) 
    
    
    
    
 #   if links:
 #	   t = [ x.get('title') for x in links]
 #	   u = [ x.get('href') for x in links]
 #	   al = "Links"	
 #	   
 #	   if items>1:	
 #   
 #		   
 #		   select = xbmcgui.Dialog().select(al, t)
 #		   
 #		   if select > -1:
 #			   link = u[select];	
 #			   stream_url=se.resolvingCR(link,url)
 #	   else:
 #		   link = u[0];
 #		   stream_url=se.resolvingCR(link,url)
 #	   if stream_url:
 #		   play_item = xbmcgui.ListItem(path=stream_url)
 #		   xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
 #	   else:
 #		   xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', "[COLOR red][B]Can't resolve this link.[/B][/COLOR]", xbmcgui.NOTIFICATION_INFO, 5000)
 #		   play_item = xbmcgui.ListItem(path=stream_url)
 #		   
 #		   xbmcplugin.setResolvedUrl(addon_handle, False, listitem=play_item)
 #		   return
 #   else:
 #	   xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)
 #	   return
  
    
    
def getLinksCRx():
    url = params.get('url', None)
    if 'roja:' in url:
        links = eval(urllib_parse.unquote(url.split(':')[1]))
    else:
        links=se.getCRlink(url)
    stream_url=''
    items = len(links)
    if links:
        t = [ x.get('title') for x in links]
        u = [ x.get('href') for x in links]
        al = "Links"	
        
        if items>1:	
    
            
            select = xbmcgui.Dialog().select(al, t)
            
            if select > -1:
                link = u[select];	
                stream_url=se.resolvingCR(link,url)
        else:
            link = u[0];
            stream_url=se.resolvingCR(link,url)
        if stream_url:
            play_item = xbmcgui.ListItem(path=stream_url)
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        else:
            xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', "[COLOR red][B]Can't resolve this link.[/B][/COLOR]", xbmcgui.NOTIFICATION_INFO, 5000)
            play_item = xbmcgui.ListItem(path=stream_url)
            
            xbmcplugin.setResolvedUrl(addon_handle, False, listitem=play_item)
            return
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)
        return


def getStreamsSstreams():	
    stream_url=''
    url = params.get('url', None)
    links=se.getSstreamsStreams(url)	
    items = len(links)
    if links:
        t = [ x.get('title') for x in links]
        u = [ x.get('href') for x in links]
        al = "Links"	

        if items>1:	
            select = xbmcgui.Dialog().select(al, t)
            
            if select > -1:
                link = u[select];	

                stream_url=se.resolvingCR(link,url)
                
            else:
                quit()
        else:
            link = u[0];
            stream_url=se.resolvingCR(link,url)
        if stream_url:
            play_item = xbmcgui.ListItem(path=stream_url)
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        else:
            xbmcgui.Dialog().notification('[COLOR orangered][B]Error[/B][/COLOR]', '[COLOR orangered][B]This link is NOT working[/B][/COLOR]', blad, 5000)
            play_item = xbmcgui.ListItem(path=stream_url)
            xbmcplugin.setResolvedUrl(addon_handle, False, listitem=play_item)
            return
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)
        return	


def getF1channels():
    channels = se.F1channels()
    if channels:
        for f in channels:
            add_item(f.get('href'), f.get('title'), RESOURCES+'chan2.png', False, 'F1stream')		
    xbmcplugin.setContent(addon_handle, 'videos')	
    xbmcplugin.endOfDirectory(addon_handle)	

def getStreamsSW2():
    stream_url=''
    url = params.get('url', None)
    tytul = params.get('title', None)
    stream_url=se.resolvingCR(url,url)
    if stream_url:
        if 'video.assia' in stream_url: 
            
            is_helper = inputstreamhelper.Helper('hls')
            if is_helper.check_inputstream():
                play_item = xbmcgui.ListItem(path=stream_url,label=tytul)
                play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':tytul})
                play_item.setProperty("IsPlayable", "true")
                if six.PY3:
                    play_item.setProperty('inputstream', is_helper.inputstream_addon)
                else:
                    play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
            #   play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
                play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                
                play_item.setMimeType('application/vnd.apple.mpegurl')
                play_item.setContentLookup(False)
                xbmc.Player().play(stream_url,play_item)

            
        elif 'us/ingest' in stream_url:

            play_item = xbmcgui.ListItem(path=stream_url)
        
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    
    
        else:	
            play_item = xbmcgui.ListItem(path=stream_url,label=tytul)
            play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':tytul})
            play_item.setProperty("IsPlayable", "true")
            xbmc.Player().play(stream_url,play_item)
    
            
    else:
        if stream_url !='':
            play_item = xbmcgui.ListItem(path=stream_url,label=tytul)
            play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':tytul})
            play_item.setProperty("IsPlayable", "true")
            xbmc.Player().play(stream_url,play_item)
        
        else:
            xbmcgui.Dialog().notification('[COLOR orangered][B]Error[/B][/COLOR]', '[COLOR orangered][B]This link is NOT working[/B][/COLOR]', blad, 5000)
            play_item = xbmcgui.ListItem(path=stream_url)
            play_item.setProperty("IsPlayable", "false")
            xbmcplugin.setResolvedUrl(addon_handle, False, listitem=play_item)
            return
  
def getStreamsSW():
    
    
    stream_url=''
    url = params.get('url', None)
    tytul = params.get('title', None)

    links=se.getSWstreams(url)	

    items = len(links)
    #idle()
    if links:
        t = [ x.get('title') for x in links]
        u = [ x.get('href') for x in links]
        al = "Links"	

        if items>1:	
            select = xbmcgui.Dialog().select(al, t)
            
            if select > -1:
                link = u[select];	

                stream_url=se.resolvingCR_SW(link,url)
                if stream_url.startswith('//'):
                    stream_url='http:'+stream_url

            else:
                quit()
        else:
            link = u[0];
            stream_url=se.resolvingCR_SW(link,url)
            if stream_url.startswith('//'):
                stream_url=stream_url='http:'+stream_url
            
        if stream_url:
            
            if ('assia' in stream_url) or ('prd.dlive' in stream_url) or ('nhl.com' in stream_url) or ('wikisport' in stream_url): 
                print('runISA')
                is_helper = inputstreamhelper.Helper('hls')
                if is_helper.check_inputstream():
                    play_item = xbmcgui.ListItem(path=stream_url,label=tytul)
                    play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':tytul})
                    play_item.setProperty("IsPlayable", "true")
                    if six.PY3:
                        play_item.setProperty('inputstream', is_helper.inputstream_addon)
                    else:
                        play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
                        
                    if 'wikisport' in stream_url:
                        play_item.setProperty('inputstream.adaptive.stream_headers', 'Origin=http://wikisport.click')
                    play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                    play_item.setMimeType('application/vnd.apple.mpegurl')
                    play_item.setContentLookup(False)
                    xbmc.Player().play(stream_url,play_item)

                
            elif 'us/ingest' in stream_url:

                play_item = xbmcgui.ListItem(path=stream_url)
            
                xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        
    
            else:	
                #play_item = xbmcgui.ListItem(path=stream_url)
            
                #xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
                play_item = xbmcgui.ListItem(path=stream_url,label=tytul)
                play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':tytul})
                play_item.setProperty("IsPlayable", "true")
                xbmc.Player().play(stream_url,play_item)

                
        else:
            xbmcgui.Dialog().notification('[COLOR orangered][B]Error[/B][/COLOR]', '[COLOR orangered][B]This link is NOT working[/B][/COLOR]', blad, 5000)
            play_item = xbmcgui.ListItem(path=stream_url)
            play_item.setProperty("IsPlayable", "false")
            xbmcplugin.setResolvedUrl(addon_handle, False, listitem=play_item)
            return
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)
        return			
    return
def getF1stream():
    stream_url=''
    url = params.get('url', None)

    links=se.getF1stream(url)	
    items = len(links)
    if links:
        t = [ x.get('title') for x in links]
        u = [ x.get('href') for x in links]
        al = "Links"	

        if items>1:	
            select = xbmcgui.Dialog().select(al, t)
            
            if select > -1:
                link = u[select];	

                try:
                    src = resolveurl.resolve(link)
                except:
                    pass
                if src:
                    stream_url=src
                else:
                    stream_url=link
            else:
                quit()
        else:
            link = u[0];
            try:
                src = resolveurl.resolve(link)
            except:
                pass
            if src:
                stream_url=src
            else:
                stream_url=link
        if stream_url:
            
            play_item = xbmcgui.ListItem(path=stream_url)
            
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        else:
            xbmcgui.Dialog().notification('[COLOR orangered][B]Error[/B][/COLOR]', '[COLOR orangered][B]This link is NOT working[/B][/COLOR]', blad, 5000)
            play_item = xbmcgui.ListItem(path=stream_url)
            xbmcplugin.setResolvedUrl(addon_handle, False, listitem=play_item)
            return
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)
        return	



    
def getLinksSW():
    url = params.get('url', None)
    link,playt=se.getSWlink(url)
    if link:
        if playt:
            is_helper = inputstreamhelper.Helper('hls')
            if is_helper.check_inputstream():
                play_item = xbmcgui.ListItem(path=link)
                if six.PY3:
                    play_item.setProperty('inputstream', is_helper.inputstream_addon)
                else:
                    play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
                play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                play_item.setMimeType('application/x-mpegurl')
                play_item.setContentLookup(False)
        else:
            play_item = xbmcgui.ListItem(path=link)
        
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    else:

        xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem(path=None))#
        return	

def getLinksSW2():
    url = params.get('url', None)
    link,playt=se.getSWlink2(url) 
    if link:
        if playt:
            is_helper = inputstreamhelper.Helper('hls')
            if is_helper.check_inputstream():
                play_item = xbmcgui.ListItem(path=link)
                if six.PY3:
                    play_item.setProperty('inputstream', is_helper.inputstream_addon)
                else:
                    play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
                play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                play_item.setMimeType('application/x-mpegurl')
                play_item.setContentLookup(False)
        else:
            play_item = xbmcgui.ListItem(path=link)
        
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    else:

        xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem(path=None))#
        return	
        
def ListTVP():	
    import tvpsport
    url = params.get('url', None)
    links = tvpsport.getChannels(url)
    if links:
        items = len(links)

        for f in links:
            add_item(f.get('href'), f.get('title'), f.get('image'), False, 'playTVP',infoLabels={'code':f.get('code'),'plot':f.get('plot')})	


        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	
    else:
        xbmcgui.Dialog().ok('[COLOR red]Problem[/COLOR]','Brak materiałów do wyświetlenia.')	
def PlayTVP():
    import tvpsport
    url = params.get('url', None)
    link,proxy = tvpsport.getChannelVideo(url)
    if link:
        is_helper = inputstreamhelper.Helper('hls')
        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=link)
            if six.PY3:
                play_item.setProperty('inputstream', is_helper.inputstream_addon)
            else:
                play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            play_item.setMimeType('application/x-mpegurl')
            play_item.setContentLookup(False)
        
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    else:

        xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem(path=None))#
    
def PlaySW():
    url = params.get('url', None)
    if link:
        is_helper = inputstreamhelper.Helper('hls')
        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=link)
            if six.PY3:
                play_item.setProperty('inputstream', is_helper.inputstream_addon)
            else:
                play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            play_item.setMimeType('application/x-mpegurl')
            play_item.setContentLookup(False)
        
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
    else:

        xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem(path=None))#	
def getDysc(imag):
    if "pilka_nozna.png" in imag: 
        return RESOURCES+'soccer.png', u'Piłka nożna'
    elif "lekkoatletyka.png" in imag: 
        return RESOURCES+'athletics.png', u'Lekkoatletyka'		
    elif "koszykowka.png" in imag: 
        return RESOURCES+'basketball.png', u'Koszykówka'
    elif "siatkowka.png" in imag: 
        return RESOURCES+'volleyball.png', u'Siatkówka'
    elif "specjalne.png" in imag: 
        return RESOURCES+'vipl.png', u'Specjalne'
    elif "pilka_reczna.png" in imag: 
        return RESOURCES+'handball.png', u'Piłka ręczna'
    elif "baseball.png" in imag: 
        return RESOURCES+'baseball.png', u'Baseball'
    elif "tenis.png" in imag: 
        return RESOURCES+'tennis.png', u'Tenis'
    elif "wyscigi_samochodowe.png" in imag: 
        return RESOURCES+'F1.png', u'Wyścigi samochodowe'
    elif "78.png" in imag: 
        return RESOURCES+'golf.png', u'Golf'
    elif "hokej.png" in imag: 
        return RESOURCES+'hockey.png', u'Hokej na lodzie'
    elif "football_amerykanski.png" in imag: 
        return RESOURCES+'football.png', u'Futbol amerykański'
    elif "zuzel.png" in imag: 
        return RESOURCES+'looker.png', u'Żużel'
    elif "kolarstwo.png" in imag: 
        return RESOURCES+'cycling.png', u'Kolarstwo'
    elif "boks.png" in imag: 
        return RESOURCES+'fighting.png', u'Sporty walki'
    elif "specjalne.png" in imag: 
        return RESOURCES+ 'specjalne.png', u'Specjalne'
    elif "snooker.png" in imag: 
        return RESOURCES+'snooker.png', u'Snooker'
    elif "motorbike.png" in imag: 
        return RESOURCES+'F1.png', u'Motorbikes'
    elif "darts.png" in imag: 
        return RESOURCES+'darts.png', u'Darts'
    elif "23.png" in imag: 
        return RESOURCES+'f1.png', u'Formuła 1'
    elif "badminton.png" in imag: 
        return RESOURCES+'badminton.png', u'Badminton'
    elif "rugby.png" in imag: 
        return RESOURCES+'rugby.png', u'Rugby'
    elif "43.png" in imag: 
        return RESOURCES+'rowing.png', u'Wioślarstwo'
    elif "88.png" in imag: 
        return RESOURCES+'skiing.png', u'Sporty zimowe'		
    elif "skoki_narciarskie.png" in imag: 
        return RESOURCES+'ski_jumping.png', u'Skoki narciarskie'			
    elif "boks.png" in imag: 
        return RESOURCES+'fighting.png', u'Wrestling'
    elif "biathlon.png" in imag: 
        return RESOURCES+'biathlon.png', u'Biathlon'
    elif "currling.png" in imag: 
        return RESOURCES+'curling.png', u'Curling'
    elif "ping_pong.png" in imag:
        return RESOURCES+'table_tennis.png', u'Tenis stołowy'
    else:
        return RESOURCES+'vipl.png',''

def categories(html):

    cats = re.findall('<tr>\s*<[^<]*<a class="main" href="([^"]*allupcomingsports/(\d+)/)"><img[^>]*src="([^"]+)"></a></td>\s*<td align="left">[^<]*<a[^<]*<b>([^<]*)</b></a>\s*</td>\s*<td width=\d+ align="center">\s*<a [^<]*<b>\+(\d+)</b></a>\s*</td>\s*</tr>', html)
    cats = __prepare_cats(cats)
    return cats

def events(url):

    import requests
    html = requests.get(url).text
    main = parseDOM(html,'table',attrs = {'class':'main'})
    
    events = parseDOM(main,'td',attrs = { 'colspan':'2', 'height':'38'})
    events = __prepare_events(events)
    return events

def links(url,tyt):
    import requests
    html = requests.get(url).text
    links = parseDOM(html, "table", attrs = { "class": "lnktbj" })
    
    links = __prepare_links(links,tyt)
    return links	
    
def __prepare_cats(cats):
    new = []
    for cat in cats:
        url = base + cat[0]
        title = cat[3] + ' (%s)'%cat[4]
        id = get_id(cat[3])
        img = '%s.png'%id
        new.append((url,title,img))

    return new	

def __prepare_links(links,tyt):
    new = []
    for link in links:
        try:
            try:
                bitrate = parseDOM(link, "td", attrs={"class":"bitrate"}) [0]
                bitrate = ' ' + re.sub("<[^>]*>","",bitrate)
            except:
                bitrate = ' '

            try:
                lang = parseDOM(link,"img",ret="title") [0]
                lang = ' ' + re.sub("<[^>]*>","",lang)
            except:
                lang = ' '
            health = re.findall('&nbsp;(\d+)',link)#[0]
            health =health[0] if health else ''

            try:
                streamer_tmp,video,eid,lid,ci,si,jj,url = re.findall('show_webplayer\("(\w+)",\s*"(\w+)",\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+),\s*"(\w+)"\).+?href="(.+?)">',link)[0]
                
                streamer_tmp= re.findall('show_webplayer\("(\w+)",',link)[0]
            except:
                url=re.findall('href="([^"]+)"><img OnMouseOver',link,re.DOTALL)#[0]
                streamer_tmp='flash'
                if url:
                    url=url[0]
                else:
                    url=re.findall('href="([^"]+)">',link,re.DOTALL)[0]
                    streamer_tmp='aliez'

            title = "%s (health %s%%) %s %s"%(streamer_tmp,health,lang, bitrate)
            if 'cast3d' not in title and 'acestream' not in title and 'sopcast' not in title:
                new.append((url+'|'+tyt,title.replace('ifr','flash')))
        except:
            pass
    return new
        
def get_id(id):
    id = id.lower().replace(' ','_')
    id = id.replace('ice_hockey','hockey').replace('football','soccer').replace('american_soccer','football').replace('rugby_union','rugby').replace('combat_sport','fighting').replace('rugby_league','rugby').replace('field_hockey','fieldhockey').replace('ncaa','basketball')
    id = id.replace('winter_sport','skiing').replace('water_sports','waterpolo').replace('billiard','snooker').replace('racing','f1').replace('boxing','fighting').replace('water_polo','waterpolo').replace('e-sports','esports')
    return id	

def __prepare_events(events):
    new=[]
    for ev in events:
    
    
    

        url= base+ str(parseDOM(ev, 'a', ret='href')[0])		
        event= str(parseDOM(ev, 'a')[0])		
        info = str(parseDOM(ev, "span", attrs = { "class": "evdesc" }))
        try:
            league = re.findall('\((.+?)\)',info)[0]
        except:
            league = ''

        time = re.findall('(\d+:\d+)',info)[0]
        li = time.split(':')
        hour,minute=li[0],li[1]
        hour=int(li[0])+1
        hour=('{:02}'.format(hour))
        time=hour+':'+minute
        day,month = re.findall('(\d+) (\w+) at',info)[0]
        color = u'[COLOR orangered]■ '
        if 'live.gif' in str(ev):
            color = u'[COLOR lime]► '
        title = PLchar('%s[/COLOR][B][COLOR khaki]%s  : [/COLOR][/B] [B][COLOR gold]%s[/COLOR] [B][COLOR lightgreen]%s[/COLOR][/B]'%(color,time,event,league))		
        new.append((url,title))
    return new
        
def getLivetvsx():
    import requests
    url = params.get('url', None)
    url = url.replace('{uri.scheme}://{uri.netloc}/'.format(uri=urllib_parse.urlparse(url)), '{uri.scheme}://{uri.netloc}/'.format(uri=urllib_parse.urlparse(base)))
    html = requests.get(
        url,
        verify=False).text
    cats=categories(html)
    for cat in cats:
        add_item(cat[0], cat[1], RESOURCES+cat[2], True, 'livetvevents')
    xbmcplugin.endOfDirectory(addon_handle)	

def getLiveEvents():
    url = params.get('url', None)
    img = params.get('image', None)
    event=events(url)
    for even in event:
        add_item(even[0],even[1], img, True, 'livelinks')	
    xbmcplugin.endOfDirectory(addon_handle)	
    
def getLinks():
    url = params.get('url', None)
    tyt = params.get('title', None)
    link=links(url,tyt)
    for new in link:
        add_item('http:'+new[0], new[1], RESOURCES+'play.png', False, 'playlivetvsx')
    xbmcplugin.endOfDirectory(addon_handle)		
  
def authme():
    headers = dict(urlparse.parse_qsl(headers))
  

  
  
  
def playVipLeague()	:
    url = params.get('url', None)

    tit = params.get('title', None)
    stream,err = se.VipLeagueStream(url,tit)
    if err and not stream:
        xbmcgui.Dialog().notification('[B]Error[/B]', '[B]'+err+'[/B]',xbmcgui.NOTIFICATION_INFO, 8000,False)
    else:
        if stream:

        
        
        
        
        
        
        
            stream_url, hdrs = stream.split('|')
            
            
            stream = PROXY_PATH='http://127.0.0.1:%s/dd='%(str(proxyport))+stream

            play_item = xbmcgui.ListItem(path=stream,label=tit)
            

        #	if six.PY3:
        #		play_item.setProperty('inputstream', 'inputstream.adaptive')
        #	else:
        #		play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        #	play_item.setProperty("IsPlayable", "true")
        #	play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        #	play_item.setProperty('inputstream.adaptive.stream_headers', hdrs)
        #	play_item.setMimeType('application/vnd.apple.mpegurl')
        #	play_item.setProperty('inputstream.adaptive.license_key', 'http://127.0.0.1:%s/dd=fghjikl'%(str(proxyport)))
            play_item.setContentLookup(False)
            xbmc.Player().play(stream,play_item)
            #xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)


def getLinksVipLeague():
    id = params.get('url', None)

    tit = params.get('title', None)
    vids = se.getLinksVipLeague(id,tit)
    if vids:
        for f in vids:

            plot = f.get('plot')
            plot = plot if plot else f.get('title')
            add_item(f.get('href'), f.get('title'), '', False,'playVipLeague', infoLabels={'plot':plot,'code':f.get('code')},odtworz=False)	

        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	
def getVipleagueStreams(urlk=''):
    url = params.get('url', None)

    links = se.getVipLeagueStreams(url,urlk)
    if links:
        for f in links:

            ikona=ikony(f.get('image'))
            
            add_item(f.get('href'), f.get('title'),ikona, True,'getLinksVipLeague', infoLabels={'plot':f.get('title'),'code':f.get('code')})	

        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	
    
    
def getVipleague()	:
    url = params.get('url', None)
    links = se.getVipLeague(url)

    if links:
        for f in links:	
            
            ikona=ikony(f.get('image'))		
            add_item(f.get('href'), f.get('title'), ikona, True, 'vipleaguestreams')	
        xbmcplugin.setContent(addon_handle, 'videos')	
        xbmcplugin.endOfDirectory(addon_handle)	

def VipleagueMenu():
    add_item('https://www.vipleague.lc/live-now-games', 'OnGoing Games', RESOURCES+'vipl.png', True, "vipleaguestreams", infoLabels=False)
    add_item('https://www.vipleague.lc/upcoming-games', 'Starting Soon', RESOURCES+'vipl.png', True, "vipleaguestreams", infoLabels=False)
    add_item('https://www.vipleague.lc/big-games', 'Top Games', RESOURCES+'vipl.png', True, "vipleaguestreams", infoLabels=False)
    add_item('https://www.vipleague.lc', 'VipLeague', RESOURCES+'vipl.png', True, "vipleague", infoLabels=False)
    
    add_item('', 'Search', RESOURCES+'vipl.png', True, "vipleaguesearch", infoLabels=False)

    xbmcplugin.endOfDirectory(addon_handle)	
def getLivelooker():
    url = params.get('url', None)
    r = requests.get(
        url, 
        verify=False)  
    r_content = r.content		
    if six.PY3:
        r_content = r_content.decode(encoding='utf-8', errors='strict')
    result = parseDOM(r_content, 'div', attrs={'id': "content"})
    links = parseDOM(result,  'div', attrs={'class':'transmisja'})
    if not links:
        r = requests.get(
            "http://livelooker.com/pl/jutro.html", 
            verify=False)	
        result = parseDOM(r_content, 'div', attrs={'id': "content"})
        links = parseDOM(result,  'div', attrs={'class':'transmisja'})		
    for link in links:	
        if 'img_front/live.gif' in link:
            live=u'[COLOR lime]► [/COLOR]'
        else:	
            live=u'[COLOR orangered]■ [/COLOR]'			
        godz=parseDOM(link,  'span', attrs={'style':'font-weight: bold'})[0]
        li = godz.split(':')
        hour,minute=li[0],li[1]
        hour=int(li[0])+1
        hour=('{:02}'.format(hour))
        godz=hour+':'+minute
        title=parseDOM(link, 'b')[0]
        title=title
        imag= parseDOM(link, 'img', ret='src')[0]
        
        if "png" in imag:
            imag,dysc=getDysc(imag)
        else:
            imag= parseDOM(link, 'img', ret='src')[1]
            imag,dysc=getDysc(imag)
        if 'biegi narciarskie' in title.lower():
            imag=RESOURCES+'skiing.png'
            dysc=u'Sporty zimowe'	
        elif u'Łyżwiarstwo szybkie' in title.lower() or 'short track' in title.lower():
            imag=RESOURCES+'speed_skating.png'
            dysc=u'Łyżwiarstwo szybkie'	
        count = 0
        kody='%s (%s)'%(title,dysc)
        linkstrans = parseDOM(link,  'a', ret='href')   
        xx=[]
        out=[]
        for linktransm in linkstrans:
            url=linktransm
            if 'tele-wizja' in url:
                count+=1
                host = urllib_parse.urlparse(url).netloc
                tytul= '-	Link %s (%s)'%(str(count),host)
                out.append({'title':tytul,'href':url,'mode':'playtvru'})

            elif 'supersportowo' in url:
                count+=1
                host = urllib_parse.urlparse(url).netloc
                tytul= '-	Link %s (%s)'%(str(count),host)	
                out.append({'title':tytul,'href':url,'mode':'playSupersportowo'})
                
            elif 'zobacz.ws' in url:
                count+=1
                host = urllib_parse.urlparse(url).netloc
                tytul= '-	Link %s (%s)'%(str(count),host)	
                out.append({'title':tytul,'href':url,'mode':'playZobaczws'})				
            elif 'typertv' in url:
                count+=1
                host = urllib_parse.urlparse(url).netloc
                tytul= '-	Link %s (%s)'%(str(count),host)
                out.append({'title':tytul,'href':url,'mode':'PlayTyperTV'})				
            elif 'ustreamix' in url:
                count+=1
                host = urllib_parse.urlparse(url).netloc
                tytul= '-	Link %s (%s)'%(str(count),host) 
                out.append({'title':tytul,'href':url,'mode':'playUstreamix'})	
            #elif 'ustreamyx' in url:
            #	count+=1
            #	host = urlparse.urlparse(url).netloc
            #	tytul= '-	Link %s (%s)'%(str(count),host) 
            #	out.append({'title':tytul,'href':url,'mode':'playUstreamix'})	
           #
            elif 'drhtv.com.pl' in url:
                count+=1
                host = urllib_parse.urlparse(url).netloc
                tytul= '-	Link %s (%s)'%(str(count),host) 
                out.append({'title':tytul,'href':url,'mode':'playDRhtv'})	

                
        add_item(urllib_parse.quote(str(out)),live+'[B][COLOR khaki]'+godz+'[/COLOR] [/B]''[B][COLOR khaki] : [/COLOR] [/B]'+'[B][COLOR gold]'+title+'[/COLOR] [/B]', imag, False, 'dal2',infoLabels={'code':'[B][COLOR lightgreen]'+dysc+'[/COLOR][/B]','plot':godz+' : '+'[B][COLOR gold]'+title+'[/COLOR] [/B]'}) 

    xbmcplugin.setContent(addon_handle, 'videos')
    xbmcplugin.endOfDirectory(addon_handle)		

def playZobaczws(newurl):
    import cloudflare6
    scraper = cloudflare6.create_scraper()	
    html=scraper.get(url,verify=False).content
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    stream=getTelerium(html,newurl)
    if stream:
        play_item = xbmcgui.ListItem(path=stream)
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)	
    else:
        xbmcgui.Dialog().notification('[COLOR orangered][B]Błąd[/B][/COLOR]', '[COLOR orangered][B]Brak działającego streama[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)
        
def ikony(imag):
    if "pi\xc5\x82ka no\xc5\xbcna" in imag.lower() or 'yFgOa2K.png' in imag: 
        return RESOURCES+'soccer.png'
    elif "soccer" in imag.lower() or 'pilkanozna' in imag.lower():
        return RESOURCES+'soccer.png'
    elif "football" in imag.lower():
        return RESOURCES+'soccer.png'
    elif "GPAn874.png" in imag: 
        return RESOURCES+'ski_jumping.png'		
    elif "6zo69E6.png" in imag or 'magazyn' in imag.lower():
        return RESOURCES+'chan2.png'	
    elif "QN5kYMV.png" in imag or 'wyscigi' in imag.lower():
        return RESOURCES+'f1.png'			

    elif "basketball" in imag.lower() or 'koszykowka' in imag.lower():
        return RESOURCES+'basketball.png'	
        
    elif "koszyk\xc3\xb3wka" in imag.lower() or 'Du3nKmW.png' in imag: 
        return RESOURCES+'basketball.png'
    elif "boxing" in imag.lower(): 
        return RESOURCES+'fighting.png'	
    elif "hockey" in imag.lower() or 'Kt3vNRI' in imag or 'hokej' in imag:
        return RESOURCES+'hockey.png'	
    elif "tenis" in imag.lower() or 'GHqJGj4.png' in imag:
        return RESOURCES+'tennis.png'		
    elif "cricket" in imag.lower(): 
        return RESOURCES+'cricket.png'		
    elif "handball" in imag.lower() or 'FUuvZQ9.png' in imag or 'pilkareczna' in imag:
        return RESOURCES+'handball.png'		
    elif "volleyball" in imag.lower() or 'KIZQeih.png' in imag or 'siatkowka' in imag: 
        return RESOURCES+'volleyball.png'		
    elif "rugby" in imag.lower(): 
        return RESOURCES+'rugby.png'		
    elif 'mixed martial' in imag.lower() or '1gUH8gM.png' in imag or 'walki' in imag: 
        return RESOURCES+'fighting.png'		
    elif 'golf' in imag.lower(): 
        return RESOURCES+'golf.png'		
    elif 'darts' in imag.lower(): 
        return RESOURCES+'darts.png'	
    elif 'snooker' in imag.lower(): 
        return RESOURCES+'snooker.png'
    elif 'motorsports' in imag.lower(): 
        return RESOURCES+'f1.png'
    elif 'baseball' in imag.lower(): 
        return RESOURCES+'baseball.png'	
    elif 'afl' in imag.lower(): 
        return RESOURCES+'rugby.png'	
    elif 'cycling' in imag.lower(): 
        return RESOURCES+'cycling.png'
    elif 'tennis' in imag.lower(): 
        return RESOURCES+'tennis.png'
        
    else:
        return RESOURCES+'play.png'

def playDRhtv(newurl):	
    import mydecode
    r = requests.get(newurl,verify=False)
    html=r.content
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    src = mydecode.decode(newurl,html)
    if src:
        play_item = xbmcgui.ListItem(path=src)
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

        
def playUstreamix(newurl):
    headers = {
        'Host': 'ssl.ustreamix.com',
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Referer': newurl,
        'Upgrade-Insecure-Requests': '1',}	
    r = requests.get(newurl,verify=False)
    content=r.content
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    next = re.compile("window.open\('(.*?)'").findall(content)
    nxtu='https://ssl.ustreamix.com%s'%next[0]
    r = requests.get(nxtu,headers=headers,verify=False)	
    content=r.content
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    packed = packer.findall(content)[0]
    unpacked = jsunpack.unpack(packed)		
    next2=re.findall('replace\("(.+?)"',unpacked,re.DOTALL)[0]
    headers2 = {
                'User-Agent': UA,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
                'Referer': nxtu,
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',}
    
    r = requests.get(next2,headers=headers2,verify=False)	
    content=r.content
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    unpacked=''
    packeds = packer.findall(content)#[0]
    for packed in packeds:
        unpacked += jsunpack.unpack(packed)
    varhost=re.compile('var host_tmg="(.*?)"').findall(unpacked)
    varfname=re.compile('var file_name="(.*?)"').findall(unpacked)
    varjdtk=re.compile('var jdtk="(.*?)"').findall(unpacked)
    stream_url = 'https://' + varhost[0] + '/' + varfname[0] + '?token=' + varjdtk[0] +'|User-Agent='+urllib_parse.quote(UA)+'&Referer='+next2
    play_item = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        
def PlayAdaptive(link):	
    is_helper = inputstreamhelper.Helper('hls')
    if is_helper.check_inputstream():
        play_item = xbmcgui.ListItem(path=link)
        if six.PY3:
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
        else:
            play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        play_item.setMimeType('application/x-mpegurl')
        play_item.setContentLookup(False)
    
    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)	

    
def playSupersportowo(newurl=None):
    if not newurl:
    
        newurl = params.get('url', None)
    stream_url=''
    r = requests.get(
        newurl,
        verify=False)
    r_content   = r.content
    if six.PY3:
        r_content = r_content.decode(encoding='utf-8', errors='strict')
    if 'whostreams' in (r_content).lower():
        stream_url=	getWhostreams(r_content,newurl)
    elif 'nlive.club' in (r_content).lower():
        stream_url=	getNlive(r_content,newurl)
    if stream_url:
        play_item = xbmcgui.ListItem(path=stream_url)
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)	
    else:
        xbmcgui.Dialog().ok('[COLOR red]Problem[/COLOR] ','Brak działającego streama!!!')

def playLivetvsx():
    url = params.get('url', None)
    tyt = url.split('|')[1]
    url =url.split('|')[0]
    url = url.replace('http:http','http')
    r = requests.get(
        url,
        verify=False)
    content=r.text
   # if six.PY3:
   #	 content = content.decode(encoding='utf-8', errors='strict')
    streamurl=getLivetvsxStream(content,url)
    #
    if streamurl:

        play_item = xbmcgui.ListItem(path=streamurl,label=tyt)

        play_item.setInfo(type="Video", infoLabels={"title": tyt,'plot':tyt})

        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)	

    else:
        xbmcgui.Dialog().notification('[COLOR orangered][B]Error[/B][/COLOR]', '[COLOR orangered][B]This link is NOT working[/B][/COLOR]', blad, 5000)
def getLivetvsxStream(content,url):
    src=''

    iframes = parseDOM(content, 'iframe', ret='src')#[0]	
    
    for iframe in iframes:
        if '/ads.' in iframe:
            continue
        if'live.php' in iframe:
            iframe=iframe.replace('\r ','')
            nxturl=iframe
            nxturl = 'https:'+nxturl if nxturl.startswith('//') else nxturl		
            headers = {
            'User-Agent': UA,
            'Accept': '*/*',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Referer': url,
            'Connection': 'keep-alive',}			
            result = requests.get(nxturl,headers=headers,verify=False).content
            if six.PY3:
                result = result.decode(encoding='utf-8', errors='strict')
            result=result.replace("\'",'"')

            try:
                src=re.findall("source: '(.+?)'",result,re.DOTALL)[0]	
            except:
                src=re.findall('\.init\("([^"]+)"',result,re.DOTALL)[0]	
            #
            src=src+'|User-Agent='+urllib_parse.quote(UA)+'&Referer='+nxturl			
            break
        elif 'youtube.com' in iframe:
            src = resolveurl.resolve(iframe)
            break
        elif 'livestream.com/accounts' in iframe:
            headers = {
            'User-Agent': UA,
            'Accept': '*/*',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Referer': url,
            'Connection': 'keep-alive',}	
            nxturl=iframe
            nxturl = 'https:'+nxturl if nxturl.startswith('//') else nxturl	
            result = requests.get(nxturl,headers=headers,verify=False).content
            if six.PY3:
                result = result.decode(encoding='utf-8', errors='strict')
            result=result.replace("\'",'"')
            src = re.findall('m3u8_url":"([^"]+)"',result,re.DOTALL)[0]
            src=src+'|User-Agent='+urllib_parse.quote(UA)+'&Referer='+nxturl	
            break
        elif 'streameast.live' in iframe:
            headers = {
            'User-Agent': UA,
            'Accept': '*/*',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Referer': url,
            'Connection': 'keep-alive',}	
            nxturl=iframe
            nxturl = 'https:'+nxturl if nxturl.startswith('//') else nxturl	
            result = requests.get(nxturl,headers=headers,verify=False).content
            if six.PY3:
                result = result.decode(encoding='utf-8', errors='strict')
            result=result.replace("\'",'"')
            try:
                src=re.findall("""source:\s*['"](.+?)['"]""",result,re.DOTALL)[0]	
            except:
                src=re.findall('\.init\("([^"]+)"',result,re.DOTALL)[0]	
            #
            src=src+'|User-Agent='+urllib_parse.quote(UA)+'&Referer='+nxturl			
            break
        else:

            import mydecode
            src = mydecode.decode(url,content)
            break


    return src

def decode(content2,strona):
    if 'telerium' in content2:
        stream_url=getTelerium(content2,strona[0])
        return stream_url
    elif 'wiz1.net' in content2:
        stream_url=getWiz1net(content2,strona)
        return stream_url		
    return None

def getTelerium(content2,strona):
    try:
        id=re.compile("""'>id=\'(.*?)'; width=""").findall(content2)
        embedd= "http://telerium.tv/embed/" + id[0] + ".html"
    except:		
        url = parseDOM(content2, 'iframe', ret='src')
        embedd=url[0]
    #str = _telerium(query,data,url)
    import mydecode
    str=mydecode._telerium(embedd,data,strona)
    return str
def rev(a_string):
    return a_string[::-1]	

    
def resolve(embedd,stronka):
    resp = s.get(embedd, headers={'User-Agent':UA, 'Referer':stronka},verify=False,allow_redirects=False)#.content
    data=resp.content
    if six.PY3:
        data = data.decode(encoding='utf-8', errors='strict')
    try:
        packed = packer.findall(data)[0]
    except:
        return ''
    unpacked = jsunpack.unpack(packed)	
    src = re.compile('source:([^,]*)').findall(unpacked)	
    patern3	='var '+src[0]+'=atob\((.+?)\)'
    
    src6=re.compile(patern3).findall(unpacked)	
    patern6=src6[0]+'="(.*?)"'		
    src7=re.compile(patern6).findall(unpacked)	 #poprawny poczatek adresu
    d=src7[0]
    d1=base64.b64decode(d)	
    #varNames = re.compile('ajax\(\{url:atob\((.+?)\)\+atob\((.+?)\),dataType\:')#\$\.ajax\(\s*\{\s*url\s*:\s*atob\(\w+\((.+?)\)\)\s*\+\s*atob\(\w+\((.+?)\)\)\s*,dataType\s*:\s*[\'\"]json[\'\"]')
    varNames = re.compile('url:\s*atob\((.+?)\)\s*\+\s*atob\((.+?)\).\s*dataType')#\$\.ajax\(\s*\{\s*url\s*:\s*atob\(\w+\((.+?)\)\)\s*\+\s*atob\(\w+\((.+?)\)\)\s*,dataType\s*:\s*[\'\"]json[\'\"]')
    vars = varNames.findall(unpacked)[0]
    part1Reversed = re.compile('{0}\s*=\s*[\'\"](.+?)[\'\"];'.format(vars[0])).findall(unpacked)[0]
    part2Reversed = re.compile('{0}\s*=\s*[\'\"](.+?)[\'\"];'.format(vars[1])).findall(unpacked)[0]	
    part1 = base64.b64decode(part1Reversed)
    part2 = base64.b64decode(part2Reversed)	 
    realtoken = getRealToken('https://telerium.tv'+part1+part2, embedd)
    stream = 'https:{0}{1}|Referer={2}&User-Agent={3}&Origin=https://telerium.tv&Connection=keep-alive&Accept=*/*'
    stream = stream.format(d1, realtoken, urllib_parse.quote(embedd, safe=''), UA) 
    return stream	

    
def getRealToken(link, referer):

    h = {
        'User-Agent': UA,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Referer': referer,
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',}	

    realResp = s.get(link, headers=h,verify=False).content#[1:-1]
    if six.PY3:
        realResp = realResp.decode(encoding='utf-8', errors='strict')
    realResp=re.findall('"(.+?)"',realResp)[0]	
    return realResp[::-1]	
        
def getm3u8(content2,strona):
    m3u8playlist = re.compile('["\'](http.*?\\.m3u[8])["\']').findall(content2)
    if m3u8playlist:
        str = m3u8playlist[0]+'|User-Agent='+UA+'&Referer='+strona
    return str
    
def getDecodeSaw(content):
    mainsaw='http://www.sawlive.tv/embed/stream/'

    var = re.compile("""var\s+\w+\s+=\s*['"](.*?)['"]""").findall(content) #[0][1]
    ##print var

    vars=var[0].split(';')
    var1=vars[0]
    var2=vars[1]
    dec= mainsaw+var2+'/'+var1
    return dec
    
def getWiz1net(content2,strona):

    nexturls = parseDOM(content2, 'iframe',ret='src')
    for nexturl in nexturls:
        if 'wiz1.net' in nexturl:
            break
        else:
            continue
    headers = {
    'User-Agent': UAX,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Referer': strona,
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

    content = requests.get(nexturl,headers=headers,verify=False).content	
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    nexturl2 = re.compile('"text/javascript"\s+src="(.*?)"').findall(content)[0]
    headers = {
    'User-Agent': UAX,
    'Accept': '*/*',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Referer': nexturl,
    'Connection': 'keep-alive',}
    
    content = requests.get(nexturl2,headers=headers,verify=False).content
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    decSawUrl=getDecodeSaw(content)
    str=	_sawlivetv2(decSawUrl,nexturl)
    return str
    
def _sawlivetv2(url,ref):

    video_url=''
    headers = {
    'User-Agent': UAX,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Referer': ref,
    'Connection': 'keep-alive',}
    try:
        result = requests.get(url,headers=headers,verify=False).text
        replac = requests.get('http://sawlive.tv/ey.js',headers=headers,verify=False).text
        replac=re.findall('"(.+?)";',replac)
        if replac:
            zmiana=replac[0]
        else:
            zmiana='v6uevdvd'
    except:
        zmiana='v6uevdvd'
    packer = re.compile('(eval\(function\(p,a,c,k,e,(?:r|d).*)')
    unpacked = ''
    packed= packer.findall(result)
    
    for i in packed: 
        #print i
        try: unpacked += jsunpack.unpack(i)
        except: pass
    result += unpacked
    
    result = urllib_parse.unquote_plus(result).decode('string_escape')#.replace("\'",'"')
    gribs=re.findall('gribs="(.+?)"',result)#[-1]
    if not gribs:
        xbmcgui.Dialog().ok('[COLOR red]Problem[/COLOR]','Stream offline')	
        return
    else:
        gribs=gribs[-1]
    
    liczby=re.findall('=([^=]+)\sunescape\(qaz\)',result)[0]
    li=re.findall('var '+liczby+'\= (.+?)\s+(.+?)\s+(.+?);',result)[0]
    kod=0
    for lk in li:
        try:
            sut=re.findall('var '+lk+'\=(\d+);',result)[0]
            kod+=int(sut)
        except:
            continue

    has=re.findall("\(qaz\)\s+'(.+?)';",result)[-1].replace(zmiana,'M')
    rss=re.findall('rsss\s+=\s+"(.+?)"',result,re.DOTALL)[-1]
    usa=urllib_parse.quote(UAX)
    dal=str(kod)+'?'+has+rss 
    swfUrl='http://static3.sawlive.tv/player.swf'
    url2='%s playpath=%s swfUrl=%s pageUrl=%s live=1 swfVfy=1'%(gribs,dal,swfUrl,url)
    return url2	

def getAliezme(content2,strona):
    next_url = re.compile('src="(http://emb.aliez.me.*?)"').findall(content2)
    headers = {

        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        }
    r = requests.get(
        next_url[0],
        headers=headers,
        verify=False)

    cur=r.content
    if six.PY3:
        cur = cur.decode(encoding='utf-8', errors='strict')
    str   = re.compile("""['"]*(http[^'^"]+?\.m3u8[^'^"]*?)['"]""").findall(cur)
    str=str[0] +'|User-Agent='+UA+'&Referer='+next_url[0]  # '|User-Agent='+UA+'&Referer='+next_url[0] #' live=true swfVfy=1 swfUrl=http://i.aliez.me/swf/playernew.swf flashver=WIN\2024,0,0,221 pageUrl=' +next_url[0]
    if str:
        return str		
    else: return None
    
def getPxstream(content2,strona):	
    next_url = re.compile('src="(.*?)"').findall(content2)
    for url in next_url:
        if 'pxstream.tv' in url:
            pxurl=url
        else:
            continue
    header = {'User-Agent':UA,
        'Referer': strona,
        'Host':'pxstream.tv'}		
    r = requests.get(
        pxurl,
        headers=header,
        verify=False)
    a=r.content
    if six.PY3:
        a = a.decode(encoding='utf-8', errors='strict')
    m3u8playlist = re.compile("""file:.['"](.*?)['"]""").findall(at)	
    if m3u8playlist:
        str = m3u8playlist[0]+'|User-Agent='+UA+'&Referer='+pxurl+'&X-Requested-With=ShockwaveFlash/24.0.0.186'	
        return str	
    else: return None



def NLheaders(ref):
    hea = {
        'Host': 'edge.nlive.club',
        'User-Agent': UAX,
        'Accept': '*/*',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Referer': ref,
        'Origin': 'https://nlive.club',
    }
    
    hed = ['%s=%s' % (name, value) for (name, value) in hea.items()]
    return '&'.join(hed)	
def getNlive(html, ref):
    embedd= parseDOM(html, 'iframe', ret='src')[0]
    header = {'User-Agent':UAX,'Referer': ref, }	
    r = requests.get(embedd, headers=header,	verify=False)#.text
    header2 = {
        'User-Agent': UAX,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Referer': embedd,
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',}	
    str=re.findall('curl = "(.+?)"',r.text,re.DOTALL)
    if str:
        token= requests.get('https://nlive.club/getToken.php', headers=header2,	cookies=r.cookies,verify=False).text
        token=re.findall('"token":"(.+?)"',token)#[0]	
    stream_url=''
    if token and str:
        hea=NLheaders(embedd)
        stream_url='%s%s|%s'%(str[0],token[0],hea)
    return stream_url
    
def getWhostreams(content2,strona):
    embedd= parseDOM(content2, 'iframe', ret='src')[0]
    header = {'User-Agent':UAiphone,'Referer': strona, }		
    page = requests.get(embedd, headers=header,	verify=False).text
    packed = packer.findall(page)[0]
    unpacked = jsunpack.unpack(packed)
    try:
        str = clappr.findall(unpacked)[0]
    except:
        str = source.findall(unpacked)[0]
    str += '|User-Agent={ua}&Referer={ref}'.format(ua=UAiphone, ref=embedd)
    return str

    
def getChanx():	
    getSuperSport()
    xbmcplugin.setContent(addon_handle, 'videos')		
    xbmcplugin.endOfDirectory(addon_handle)	
    
    
def getChan():	
    try:
            
        url = params.get('url', None)
        headersok = {
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers',}	
        html=requests.get(url,headers=headersok,verify=False,timeout=10).text
        html=html.replace("\'",'"')	
        links=parseDOM(html,'div', attrs={'class': "channelContainer"})
        
        for link in links:
            title = parseDOM(link, 'h4')[0].strip()
            href = parseDOM(link, 'iframe', ret='src')[0]	
            href  = href .replace('beisport3.php','beinsport3.php')
            html= requests.get(href,headers=headersok,verify=False).text
            try:
                href = parseDOM(html, 'iframe', ret='src')[0]	
            except:
                pass
            imag = parseDOM(link, 'img', ret='src')[0]	
            add_item(href, u'[COLOR lime]► [/COLOR][B][COLOR gold]'+title+'[/B][/COLOR]', imag, False, 'playchan')
        xbmcplugin.setContent(addon_handle, 'videos')		
        xbmcplugin.endOfDirectory(addon_handle)		
    except:
        pass

    
def PlayChan():
    url = params.get('url', None)
    url = url.replace('beisport3.php','beinsport3.php')
    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'TE': 'Trailers',}	
    html=requests.get(url,headers=headersok,verify=False).text
    html=html.replace("\'",'"')	
    src=re.findall('source:*"(.+?)"',html,re.DOTALL)#[0]
    src2=re.findall('<source(.+?)</video>',html,re.DOTALL)#[0]
    src3 = re.findall('(path to the HLS m3u8)',html,re.DOTALL)#[0]
    src4 = re.findall("""window.atob\(['"]([^"]+)['"]""",html,re.DOTALL)
    if src:
        stream=src[0]+'|User-Agent='+UA+'&Referer='+url	
        xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=stream))	
    elif src2:
        src = re.findall("""src=['"](.+?)['"]""",src2[0])
        if src:
            stream=src[0]+'|User-Agent='+UA+'&Referer='+url	
            if stream.startswith("/live/"):
                stream = 'https://www.vipsportslive.eu'+stream
            xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=stream))
    elif src3:
        dan = re.findall("sources: (\[.+?\])",html,re.DOTALL)[0]
        src = re.findall("""src:\s*['"]([^'"]+)['"]""",dan)
        if src:
            stream=src[0]+'|User-Agent='+UA+'&Referer='+url	
            xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=stream))
    elif src4:
        src = base64.b64decode(src4[0])#
        if 'manifest.mpd' in src:
            play_item = xbmcgui.ListItem(path=src)
            if six.PY3:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
            else:
                play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
           # play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
            play_item.setMimeType('video/mp4')
            play_item.setContentLookup(False)
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        else:
            stream=src+'|User-Agent='+UA+'&Referer='+url
            xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=stream))
    else:
        xbmcplugin.setResolvedUrl(addon_handle, False,  xbmcgui.ListItem(path=''))		
def PlayTyperTV(url):
    headers = {'User-Agent': UA,}	
    html = requests.get(url,headers=headers,verify=False).content
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    iframe = parseDOM(html, 'iframe', ret='src')[0]
    headers = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Referer': url,
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',}
    html = requests.get(iframe,headers=headers,verify=False).content
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    src=decode(html,iframe)
    if not src:
        import mydecode
        src = mydecode.decode(url,html)
    if src:
        play_item = xbmcgui.ListItem(path=src)
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

def PLchar(char):
    if type(char) is not str:
        char=char.encode('utf-8')
    char = char.replace('\xc4\x85','ą').replace('\xc4\x84','Ą')
    char = char.replace('\xc4\x87','ć').replace('\xc4\x86','Ć')
    char = char.replace('\xc4\x99','ę').replace('\xc4\x98','Ę')
    char = char.replace('\xc5\x82','ł').replace('\xc5\x81','Ł')
    char = char.replace('\xc5\x84','ń').replace('\xc5\x83','Ń')
    char = char.replace('\xc3\xb3','ó').replace('\xc3\x93','Ó')
    char = char.replace('\xc5\x9b','ś').replace('\xc5\x9a','Ś')
    char = char.replace('\xc5\xba','ź').replace('\xc5\xb9','Ź')
    char = char.replace('\xc5\xbc','ż').replace('\xc5\xbb','Ż')
    char = char.replace('&ndash;','-') #.replace('\xc4\x84','Ą')	
    return char	
    


def play_stream(params2):
    import rtmpcheck as rtc
    aa=rtc.disable_addon()
    params2 = eval(params2)
    service = params2.get('_service')
    act = params2.get('_act')
    mod = __import__(service)
    if act == 'ListChannels':
        items = mod.getChannels(ex_link)
        img_service = '%s.png' % (RESOURCES + service)
        for one in items:
            ikona=ikony(one.get('image'))
            params2.update({'title': one.get('title', '')})
            addDir(one.get('title', ''), one['url'], params2=params2, mode='get_streams_play', infoLabels=one,iconImage=ikona, fanart=FANART)

def get_streams_play(params2,img,tit):
    params2 = eval(params2)
    orig_title = params2.get('title')
    import sport365 as mod
    frames = mod.getStreams(ex_link)
    if frames:
        for frame in frames:
            params2.update({"title": orig_title})
            #addLinkItem(frame.get('title', ''), json.dumps(frame), mode='take_stream',
            #			params2=params2, iconimage=img, fanart=FANART, infoLabels={'plot':tit},IsPlayable=True)
    
            addDir(frame.get('title', ''), json.dumps(frame), params2=params2,mode='take_stream', iconImage=img, fanart=FANART, infoLabels={'plot':tit})
        xbmcplugin.endOfDirectory(addon_handle)	
    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', '[COLOR red][B]This video is not available at the moment.[/B][/COLOR]', xbmcgui.NOTIFICATION_INFO, 5000)


def take_stream(params2):
    params2 = eval(params2)
    orig_title = params2.get('title')
    import sport365 as mod
    busy()
    stream_url, url, header, title = mod.getChannelVideo(json.loads(ex_link))
    if stream_url:
        
        liz = xbmcgui.ListItem(label=orig_title)
        iconimage = xbmc.getInfoImage("ListItem.Thumb")
        liz.setArt({"fanart": FANART, "icon": iconimage})
        liz.setInfo(type="Video", infoLabels={"title": orig_title})
        liz.setProperty("IsPlayable", "true")
        if addon.getSetting('sport365') == 'Inputstream':
            stream_url, hdrs = stream_url.split('|')
            stream_url = stream_url.replace('/i', '/index.m3u8')
            liz.setPath(stream_url)
            if float(xbmc.getInfoLabel('System.BuildVersion')[0:4]) >= 17.5:
                liz.setMimeType('application/vnd.apple.mpegurl')
                liz.setProperty('inputstream.adaptive.manifest_type', 'hls')
                liz.setProperty('inputstream.adaptive.stream_headers', str(header))
            else:
                liz.setProperty('inputstreamaddon', None)
                liz.setContentLookup(True)
    
            idle()

            try:
                import threading
                thread = threading.Thread(name='sport356Thread', target=sport356Thread2, args=[url, header])
                thread.start()
                xbmc.Player().play(stream_url, liz)
            except BaseException:

                pass
                
                
        #elif addon.getSetting('sport365') == 'Streamlink':
        ##else:
        #	stream_url, hdrs = stream_url.split('|')
        #	import streamlink.session
        #	session = streamlink.session.Streamlink()
        #	session.set_option('hls-live-edge', 15) 
        #	#session.set_option('hls-playlist-reload-attempts',15)
        #	#session.set_option('hls-live-restart',1)
        #	#stream_url, hdrs = stream_url.split('|')
        #	#stream_url = 'hls://' + stream_url
        #	stream_url = 'hls://' + stream_url.replace('/i', '/index.m3u8')
        #	
        #	hdrs += '&Origin=http://h5.adshell.net'
        #	session.set_option("http-headers", hdrs)
        #
        #	streams = session.streams(stream_url)
        #	stream_url = streams['best'].to_url() + '|' + hdrs
        #
        #	liz.setPath(stream_url)
        #	idle()
        #	import threading
        #	thread = threading.Thread(name='sport356Thread', target=sport356Thread2, args=[url, header])
        #	thread.start()
        #	xbmc.Player().play(stream_url, liz)
    
        else:
        
            stream_url = 'plugin://plugin.video.f4mTester/?streamtype=HLSRETRY&url={0}&name={1}'.format(
                urllib_parse.quote_plus(stream_url), urllib_parse.quote_plus(orig_title))
            liz.setPath(stream_url)
            idle()
            try:
                xbmc.executebuiltin('RunPlugin(' + stream_url + ')')
            except BaseException:
                pass
    
    else:
        xbmcgui.Dialog().ok("Sorry for that", 'plz contact Dev')

def sport356Thread2(url, header):
    import re, sport365 as s

    player = xbmc.Player()
    xbmc.sleep(2000) #3minutes
    player.pause()

    while player.isPlaying():
        ##########################
       ##print 'sport356Thread: KODI IS PLAYING, sleeping 4s'
        a, c = s.getUrlc(url, header=header, usecookies=True)
        banner = re.compile('url:["\'](.*?)[\'"]').findall(a)[0]
        xbmc.log(banner)
        xbmc.sleep(2000)
        s.getUrlc(banner)
        xbmc.sleep(2000)
   # #print 'sport356Thread: KODI STOPED, OUTSIDE WHILE LOOP ... EXITING'


        
def idle():

    if float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[:4]) > 17.6:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    else:
        xbmc.executebuiltin('Dialog.Close(busydialog)')


def busy():

    if float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[:4]) > 17.6:
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    else:
        xbmc.executebuiltin('ActivateWindow(busydialog)')



    

def Dalej2()	:
    url = params.get('url', None)
    
    streams = eval(urllib_parse.unquote(url))
    t = [ x.get('title') for x in streams]
    u = [ x.get('href') for x in streams]
    m = [ x.get('mode') for x in streams]
    al = "Źródła"
    
    select = xbmcgui.Dialog().select(al, t)
    
    if select > -1:
        link = u[select];
        mod = m[select];
        graj='%s("%s")'%(mod,link)
        eval(graj)

        
        

if __name__ == '__main__':
    mode = params.get('mode', None)
    if not mode:
        home()
    elif mode == 'canalespo':
        getChan()	
    elif mode == 'supersport':
        getChanx()	
        
    elif mode == 'strimstv':
        StrimsTv()	
        
    elif mode == 'listTVP':
        ListTVP()
        
    elif mode == 'sport365':
        getSport365()	
    elif mode == 'playchan':
        PlayChan()		   
    elif mode == 'playtyper' :
        PlayTyperTV()	   
    elif mode == 'livelooker':
        getLivelooker()		
    
    
    elif mode =='playVipLeague':
        playVipLeague()	
    
    
    elif mode=='getLinksVipLeague':
        getLinksVipLeague()	
    
    elif mode =="vipleague"	:
        getVipleague()	
        
    elif mode=='liveonscore2':
        LiveOnScoreMenu()
        
    elif mode =="liveonscoresocmenu":
        LiveOnScoreSocMenu()
    
    elif mode =="liveonscorestreams":
        getLiveOnScoreStreams()
    
    elif mode =='playLiveOnScore':
        playLiveOnScore()

        #http://liveonscore.tv/?s=liverpool
        
    elif mode =="liveonscoresearch":
        query = xbmcgui.Dialog().input(u'Szukaj, Co szukasz?', type=xbmcgui.INPUT_ALPHANUM)
        if query:
            getLiveOnScoreStreams(query.replace(' ','+'))
        
    
    elif mode =="vipleague2"	:
        VipleagueMenu()	
        
    elif mode =="vipleaguesearch":
        query = xbmcgui.Dialog().input(u'Szukaj, Co szukasz?', type=xbmcgui.INPUT_ALPHANUM)
        if query:
            getVipleagueStreams(query.replace(' ','+'))
            
    elif mode =='vipleaguestreams':
        getVipleagueStreams()	
        
    elif mode == 'playlivetvsx':
        playLivetvsx()		
    elif mode == 'livetvsx':
        getLivetvsx()
    elif mode == 'livelinks':
        getLinks()
    elif mode == 'livetvevents':
        getLiveEvents()		
    elif mode == 'playsupersportowo':
        playSupersportowo()
    elif mode == 'playsport':
        playSport()	
    elif mode == 'playsport2':
        playSport2()			
    elif mode == 'playustreamix':
        playUstreamix()	
    elif mode == 'playTVP':
        PlayTVP	()		
    
    
    elif mode == 'streamendous':
        ListStreamendous()
    elif mode == 'unblocked':
        ListUnblocked()
    elif mode == 'getUnbLinks':
        getUnbLinks	()		
    
        
        
    elif mode == 'strimw':
        ListStrimW()		
    elif mode == 'dal2':
        Dalej2()	
        
    elif mode == 'channelsSW':
        getChannelsSW()			
    elif mode == 'channelsSE':
        getChannelsSE()	
    elif mode == 'scheduleSE':
        getScheduleSE()		
    elif mode == 'linksSE':
        getLinksSE()			
    elif mode == 'playSE':
        PlaySE()			
    elif mode == 'channelsCR':
        getChannelsCR()	
    elif mode == 'scheduleCR':
        getScheduleCR()		
    elif mode == 'linksCR':
        getLinksCR()	

        

        
    elif mode == 'scheduleSW':
        getScheduleSW()	
    elif mode == 'scheduleSstreams':
        getScheduleSstreams()	
    
    
    elif mode=='livesportws':
        getLiveSport()


        
    elif mode == 'linksSW':
        getLinksSW()
    elif mode == 'linksSW2':
        getLinksSW2()		
        
    elif mode == 'liveChannels':
        LiveChannels()	
    elif mode == 'liveSched':
        LiveSched()	

    elif mode == 'playStrimsTv'	:
        PlayStrimsTv()
#getF1channels	
    elif mode == 'channF1':
        getF1channels	()		
        
    elif mode == 'chanksw':
        chanksw()	
        
        
        
    elif mode == 'streamsSW':
        #busy()
        getStreamsSW()	
    
    elif mode == 'streamsSW2':
        getStreamsSW2()	
    
    
    
    
    elif mode == 'F1stream':
        getF1stream()	
    
    
    
    elif mode == 'streamsSstreams':
        getStreamsSstreams()	
    
    
    elif mode == 'playCR':
        PlayCR()

    elif mode == 'site2':
        xbmcgui.Dialog().notification('[COLOR red][B]Sports365[/B][/COLOR]', '[COLOR red][B] by BUGATSINHO[/B][/COLOR]', bugats, 7000)
        play_stream(params2)
        xbmcplugin.endOfDirectory(addon_handle)
    elif mode == 'folder':
        pass
    
    elif mode == 'take_stream':
        take_stream(params2)
        #xbmcplugin.endOfDirectory(addon_handle)
        #xbmcplugin.endOfDirectory(addon_handle)
    elif mode == 'get_streams_play':
        get_streams_play(params2,imig,tit)
    elif mode == 'getLinksLiveSport':
        getLinksLiveSport()
    elif mode == 'playLiveSport':
        PlayLiveSport()
    elif mode == 'sportsbaychan':
        getSportsbaychan()	
    elif mode == 'getsportsbayLinks':
        getsportsbayLinks()		
    elif mode == 'playsportsbaytv':
        playsportsbaytv()		
    elif mode == 'getsportsbay':
        getsportsbay()
    elif mode == 'getsportsbaypopular':
        getsportsbaypopular()
    elif mode == 'getsportsbayschedule':
        getsportsbayschedule()	
        
    elif mode == 'gettvcom':
        gettvcom()
    elif mode == 'gettvcom2':
        gettvcom2()	

    elif mode == 'gettvcomdzis':
        gettvcomdzis()	
    elif mode == 'playtvcom':
        PlayTVCOM()	
    elif mode == 'gettvcomdysc'	:
        gettvcomdysc()	
    elif mode == 'getroja':
        getroja()
    elif mode == 'playcr':
        playcr()
    elif mode == "crackstreamsmenu":
        CrackstreamsMenu()
    elif mode =="crackstreams":
        GetCrackstreams()
    elif mode == 'playcrackstreams':
        PlayCrackstreams()
    elif mode == 'streamsSWfolder':
        GetSwfolder()
else:
    pass
