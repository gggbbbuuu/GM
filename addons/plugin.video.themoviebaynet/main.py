# -*- coding: UTF-8 -*-
import sys,re,os
import six
from six.moves import urllib_parse

import requests
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc, xbmcvfs
if six.PY3:
    basestring = str
    unicode = str
    xrange = range
    from resources.lib.cmf3 import parseDOM
else:
    from resources.lib.cmf2 import parseDOM
    
from resources.lib import jsunpack
import resolveurl

import json
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(urllib_parse.parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.themoviebaynet')

PATH            = addon.getAddonInfo('path')
if six.PY2:
    DATAPATH        = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
else:
    DATAPATH        = xbmcvfs.translatePath(addon.getAddonInfo('profile'))

RESOURCES       = PATH+'/resources/'
FANART=RESOURCES+'../fanart.jpg'
if six.PY2:
    napisy = xbmc.translatePath('special://temp/napisy.txt')
else:
    napisy = xbmcvfs.translatePath('special://temp/napisy.txt')


exlink = params.get('url', None)
nazwa= params.get('title', None)
rys = params.get('image', None)

page = params.get('page',[1])[0]
fkatv = addon.getSetting('fkatV')

fkatn = addon.getSetting('fkatN') if fkatv else 'all'

frokv = addon.getSetting('frokV')

frokn = addon.getSetting('frokN') if frokv else 'all'

skatv = addon.getSetting('skatV')

skatn = addon.getSetting('skatN') if skatv else 'all'

srokv = addon.getSetting('srokV')

srokn = addon.getSetting('srokN') if srokv else 'all'





MAIN_URL ='https://vww.themoviebay.net' 

UA= 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0'
TIMEOUT=15

headers = {'User-Agent': UA,}
sess = requests.Session()

def build_url(query):
    return base_url + '?' + urllib_parse.urlencode(query)

def add_item(url, name, image, mode, itemcount=1, page=1,fanart=FANART, infoLabels=False,contextmenu=None,IsPlayable=False, folder=False):

    if six.PY3:    
        list_item = xbmcgui.ListItem(name)

    else:
        list_item = xbmcgui.ListItem(name, iconImage=image, thumbnailImage=image)
    if IsPlayable:
        list_item.setProperty("IsPlayable", 'True')    
        
    if not infoLabels:
        infoLabels={'title': name}    
    list_item.setInfo(type="video", infoLabels=infoLabels)    
    list_item.setArt({'thumb': image, 'poster': image, 'banner': image, 'fanart': fanart})
    
    if contextmenu:
        out=contextmenu
        list_item.addContextMenuItems(out, replaceItems=True)
    else:
        out = []
        out.append(('Informacja', 'XBMC.Action(Info)'),)
        list_item.addContextMenuItems(out, replaceItems=False)

    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url = build_url({'mode': mode, 'url' : url, 'page' : page, 'title':name,'image':image}),            
        listitem=list_item,
        isFolder=folder)
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")
    
def home():
    add_item('https://subsmovies.club/', 'Movies', 'DefaultMovies.png', "menu:movies",fanart=FANART, folder=True)    
    
    add_item('https://subsmovies.club/', 'TV shows', 'DefaultTVShows.png', "menu:tv",fanart=FANART, folder=True)    
    add_item('https://vww.themoviebay.net/reality', 'Reality', 'DefaultStudios.png', "listmovies",fanart=FANART, folder=True)    
    
    add_item('', '[COLOR lightblue]Search[/COLOR]', 'DefaultAddonsSearch.png', "search", folder=True)    
def menuMovies():
    add_item('https://vww.themoviebay.net/movies', 'List movies','DefaultMovies.png', "listmovies",fanart=FANART, folder=True)
    add_item('https://subsmovies.club/', '[COLOR blue]- genres:[/COLOR] [B]'+fkatn+'[/B]', 'DefaultGenre.png', "filtr:fkat",fanart=FANART, folder=False)
    add_item('https://subsmovies.club/', '[COLOR blue]- years:[/COLOR] [B]'+frokn+'[/B]', 'DefaultYear.png', "filtr:frok",fanart=FANART, folder=False)
    
    add_item('f', '[COLOR lightgreen][B]Clear filters[/B][/COLOR]', 'DefaultAddonService.png', "resfil",fanart=FANART, folder=False)
    
    xbmcplugin.endOfDirectory(addon_handle)
    
def menuTv():
    add_item('https://vww.themoviebay.net/tvshows', 'List TV shows', 'DefaultTVShows.png', "listmovies",fanart=FANART, folder=True)
    add_item('https://subsmovies.club/', '[COLOR blue]- genres:[/COLOR] [B]'+skatn+'[/B]', 'DefaultGenre.png', "filtr:skat",fanart=FANART, folder=False)
    add_item('https://subsmovies.club/', '[COLOR blue]- years:[/COLOR] [B]'+srokn+'[/B]', 'DefaultYear.png', "filtr:srok",fanart=FANART, folder=False)
    add_item('s', '[COLOR lightgreen][B]Clear filters[/B][/COLOR]', 'DefaultAddonService.png', "resfil",fanart=FANART, folder=False)
    
    xbmcplugin.endOfDirectory(addon_handle)

def ListLinks(exlink):

    links=getLinks(exlink)
    
    itemz=links
    items = len(links)

    for f in itemz:
        modemy='playLink'
        isplay=True
        fold=False
        add_item(name=f.get('title'), url=f.get('href'), mode=modemy, image=f.get('img'), infoLabels={'code':f.get('code'),'plot':f.get('plot'),'genre':f.get('genre')}, itemcount=items,folder=fold, IsPlayable=isplay)    
    
    if pagination:
        add_item(name='[COLOR blue]>> next page >>[/COLOR]', url=exlink, mode='listsubsmov', image=RESOURCES+'right.png', page=pagination,fanart=FANART, folder=True)        
    xbmcplugin.setContent(addon_handle, 'movies')    
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")
    xbmcplugin.endOfDirectory(addon_handle)


def ResetFilters(typ):
    addon.setSetting(typ+'katN','all')
    addon.setSetting(typ+'katV','')
    addon.setSetting(typ+'rokN','all')
    addon.setSetting(typ+'rokV','')
    xbmc.executebuiltin('Container.Refresh')

def getLinks(url):
    url = url+'?checked=1' if not '?checked=1' in url else url
    html=getUrlReqOk(url)

    player = parseDOM(html,'section', attrs={'class': "player"})[0]
    mainpl = parseDOM(player,'iframe', ret="src")[0]

    outs = getMainPlayer(mainpl,url)
    itemz=outs
    items = len(outs)

    for f in itemz:
        modemy='playVid'
        
        isplay=True
        fold=False
        lab = f.get('title')
        nazw = nazwa if 'main' in lab else nazwa+f.get('title')
        
        href = f.get('streamurl')
        href = href if not f.get('suburl') else href+'|'+f.get('suburl')
        add_item(name=nazw, url=href, mode=modemy, image=rys, infoLabels={'plot':nazwa}, itemcount=items,folder=fold, IsPlayable=isplay)    

    altsrcs = re.findall('<li><a href="(.+?)"',player,re.DOTALL)

    for altsrc in altsrcs:
        host = (urllib_parse.urlparse(altsrc).netloc).replace('www.','')
        nazw = nazwa + ' [COLOR khaki][B](alternativ)[/COLOR][/B] '+'- [I]'+host+'[/I]'

        add_item(name=nazw, url=altsrc, mode=modemy, image=rys, infoLabels={'plot':nazwa}, itemcount=items,folder=fold, IsPlayable=isplay)
    xbmcplugin.endOfDirectory(addon_handle)    
    
def getMainPlayer(url,ref):
    packer = re.compile('(eval\(function\(p,a,c,k,e,(?:r|d).*)')
    html=getUrlReqOk(url,ref)
    out=[]

    packed = packer.findall(html)[0]
    unpacked = jsunpack.unpack(packed)    
    html+=unpacked
    src = re.findall('src\:"(.+?)"\,type\:',html,re.DOTALL)[0]
    out.append({'title':'main','streamurl':src,'suburl':''})

    ssrclab=re.findall('"captions" src="(.+?)".+?label="(.+?)"',html,re.DOTALL)
    for ssrc,lab in ssrclab:
        lab = ' [COLOR gold][B](subtitle: '+lab+')[/COLOR][/B]'
        suburl='https://videyo.net'+ssrc
        out.append({'title':lab,'streamurl':src,'suburl':suburl})    
    return out
    
def ListSubsMov(exlink,page):
    page = int(page) if page else 1    
    filmy,pagination=getSubsMov(exlink,page)
    
    itemz=filmy
    items = len(filmy)

    for f in itemz:
        modemy='getLinks'
        isplay=False
        fold=True
        if 'tvshows/' in f.get('href'): 
            if 'true' in addon.getSetting('groupEpisodes'):
                modemy='listseasons'
                isplay=False
                fold=True
            else:
                modemy='listepisodes'
                isplay=False
                fold=True
        
        
        
        add_item(name=f.get('title'), url=f.get('href'), mode=modemy, image=f.get('img'), infoLabels={'code':f.get('code'),'plot':f.get('plot'),'genre':f.get('genre')}, itemcount=items,folder=fold, IsPlayable=isplay)    
    
    if pagination:
        add_item(name='[COLOR blue]>> next page >>[/COLOR]', url=exlink, mode='listsubsmov', image=RESOURCES+'right.png', page=pagination,fanart=FANART, folder=True)        
    xbmcplugin.endOfDirectory(addon_handle)
    
def getSubsMov(url,page):
    #fkatv
    out=[]
    nxtpage='nastepnastrona'
    if not '/search?q' in url:
        if '/movies' in url or '/tvshow' in url:
            url = url+fkatv+frokv if 'movies' in url else url+skatv+srokv

        nxtpage = url + '&page=%d' %(int(page)+1) if 'genres' in url or 'year' in url else url + '?page=%d' %(int(page)+1)
        url = url + '&page=%d' %page    if 'genres' in url or 'year' in url else url + '?page=%d' %page

    html=getUrlReqOk(url)

    links = parseDOM(html,'li', attrs={'class': "grid-item"})

    for link in links:
        href = parseDOM(link,'a', ret="href")[0]
        tyt = parseDOM(link,'div', attrs={'class': "title"})[0] 
        imag = parseDOM(link,'img', ret="src")[0]
        href = MAIN_URL + href if href.startswith('/') else href
        imag = MAIN_URL + imag if imag.startswith('/') else imag
        imag = (re.split('\-\d+x\d+\-', imag))[0]+'.jpeg' 

        imag = 'https://vww.themoviebay.net/uploads/default/no-image.jpg' if 'no-image' in imag else imag
        
        qual = parseDOM(link,'span', attrs={'class': "quality"})
        qual = qual[0] if qual else ''
        genre = parseDOM(link,'span', attrs={'class': "genre"})
        genre = genre[0] if genre else ''

        ftitle=tyt.strip()+' [COLOR orange][B]('+qual+')[/COLOR][/B]' if qual else tyt.strip()
        plot=PLchar(ftitle)

        out.append({'title':PLchar(ftitle),'href':href,'img':imag,'year':'','plot':plot,'genre':genre,'code':qual})
        
        
    prevpage=False 
    nextpage=False  
    ktora=False

    if html.find(nxtpage)>1:
        nextpage=page+1

    return out,nextpage
    
def ListSeasons(exlink,org_tit):

    episodes =  getEpisodes(exlink)
    #
    imag=episodes[0].get('img')
    seasons =  splitToSeasons(episodes)
    
    for i in sorted(seasons.keys()):
        aa=urllib_parse.quote(str(seasons[i]))
        add_item(name=i, url=urllib_parse.quote(str(seasons[i])), mode='listEpisodes2', image=imag, infoLabels={'plot':org_tit}, folder=True)    
    xbmcplugin.endOfDirectory(addon_handle)
    
def splitToSeasons(input):
    out={}
    seasons = [x.get('season') for x in input]
    for s in set(seasons):
        out['Season %02d'%s]=[input[i] for i, j in enumerate(seasons) if j == s]
    return out
def ListEpisodes2(exlink):
    episodes = eval(urllib_parse.unquote(exlink))
    itemz=episodes
    items = len(episodes)
    
    for f in itemz:
        add_item(name=f.get('title'), url=f.get('href'), mode='getLinks', image=f.get('img'), folder=True, infoLabels={'plot':f.get('title')}, itemcount=items, IsPlayable=False)    
    #xbmcplugin.setContent(addon_handle, 'episodes')    
    xbmcplugin.endOfDirectory(addon_handle)
    
def ListEpisodes(exlink):
    episodes = getEpisodes(exlink)
    itemz=episodes
    items = len(episodes)
    for f in itemz:
        add_item(name=f.get('title'), url=f.get('href'), mode='getLinks', image=f.get('img'), folder=True, infoLabels={'plot':f.get('title')}, itemcount=items, IsPlayable=False)        
    #xbmcplugin.setContent(addon_handle, 'episodes')
    xbmcplugin.endOfDirectory(addon_handle)
    
def getEpisodes(url):
    

    html = getUrlReqOk(url)
    out=[]
    result = parseDOM(html,'section', attrs={'class': "episodes"})[0]
    seasons = re.findall('class="label">(season.*?)<\/ul>',result,re.DOTALL+re.IGNORECASE)
    for seas in seasons:
        ses = re.findall('^season\s*(\d+)<',seas,re.DOTALL+re.IGNORECASE)[0]    
        hreftit = re.findall('href="([^"]+).+?digit">([^<]+)',seas,re.DOTALL+re.IGNORECASE)
        for href,tyt in hreftit:
            epis=re.findall('(\d+)',tyt,re.DOTALL)

            jaki = ' - S%02dE%02d'%(int(ses),int(epis[0]))

            tyt = nazwa + jaki
            out.append({'title':tyt,'href':href,'img':rys,'plot':'','genre':'', 'season' : int(ses),'episode' : int(epis[0]) if epis else '',})
    return out    

def getUrlReqOk(url,ref=''):    

    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
#    'Upgrade-Insecure-Requests': '1',
    'Referer': ref,}
    #'TE': 'Trailers',}
    content=sess.get(url, headers=headersok,verify=False).content
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict') 
    
    return content

def vtttostr(vtt):
    subs=re.findall('^(.+?-->\s+.+)',vtt,re.MULTILINE)
    row=0
    for sub in subs:
        row = row + 1
        d=re.findall('(\d+:\d+:\d+.\d+ -->)',sub) 
        if not d:
            sub2='%02d:%s'%(0,sub)
        else:
            d=re.findall('(\d+):\d+:\d+.\d+ -->',sub)
            sub2='%02d:%s'%(int(d[0]),sub)
        p1=re.findall('(\d+:\d+:\d+.\d+ -->)',sub2)
        p2=re.findall('--> (.+?)$',sub)
        d=re.findall('(\d+:\d+:\d+.\d+)',p2[0]) 
        if not d:
            sub2='%s%02d:%s'%(p1[0],0,p2[0])       
        else:
            p2ok=re.findall('-->\s*\d+:(.+?)$',sub)[0]
            d=re.findall('(\d+):\d+:\d+.\d+',p2[0])
            d=int(d[0])
            sub2='%s %02d:%s'%(p1[0],d,p2ok)
        nx=str(row) +'\n'+sub2
        nx=nx.replace(".",',')

        vtt=vtt.replace(sub,nx)
    vtt = re.sub(r'WEBVTT\n\n', '', vtt)
    vtt = re.sub(r'Kind:[ \-\w]+\n', '', vtt)
    vtt = re.sub(r'Language:[ \-\w]+\n', '', vtt)
    vtt = re.sub(r'<c[.\w\d]*>', '', vtt)
    vtt = re.sub(r'</c>', '', vtt)
    vtt = re.sub(r'<\d\d:\d\d:\d\d.\d\d\d>', '', vtt)
    vtt = re.sub(r'::[\-\w]+\([\-.\w\d]+\)[ ]*{[.,:;\(\) \-\w\d]+\n }\n', '', vtt)
    vtt = re.sub(r'Style:\n##\n', '', vtt)    
    return vtt
    
    
    
def PlayVid(exlink):

    if '|' in exlink:
        subt=exlink.split('|')

        r = requests.get(subt[1], allow_redirects=True)
        content=r.content
        if six.PY3:
            content= content.decode(encoding='utf-8', errors='strict') 
        poprawiony=vtttostr(content)

        if six.PY3:
            open(napisy, 'w', encoding='utf-8').write(poprawiony)
        else:
            open(napisy, 'w').write(poprawiony)





        play_item = xbmcgui.ListItem(path=subt[0])
        play_item.setSubtitles([napisy])
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)    
    else:
        link = exlink
        if not 'videyo.net' in link:
            #try:
            link = resolveurl.resolve(link)

        #    xbmc.log('linklinklinklink: %s' % str(link), xbmc.LOGNOTICE)
        if link:
            play_item = xbmcgui.ListItem(path=link)
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)    
        else:
            xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', "[COLOR red][B]This video doesn't exists in our servers or has been deleted.[/B][/COLOR]", xbmcgui.NOTIFICATION_INFO, 5000)

def PLchar(char):
    if type(char) is not str:
        char=char.encode('utf-8')
    char = char.replace('\\u0105','\xc4\x85').replace('\\u0104','\xc4\x84')
    char = char.replace('\\u0107','\xc4\x87').replace('\\u0106','\xc4\x86')
    char = char.replace('\\u0119','\xc4\x99').replace('\\u0118','\xc4\x98')
    char = char.replace('\\u0142','\xc5\x82').replace('\\u0141','\xc5\x81')
    char = char.replace('\\u0144','\xc5\x84').replace('\\u0144','\xc5\x83')
    char = char.replace('\\u00f3','\xc3\xb3').replace('\\u00d3','\xc3\x93')
    char = char.replace('\\u015b','\xc5\x9b').replace('\\u015a','\xc5\x9a')
    char = char.replace('\\u017a','\xc5\xba').replace('\\u0179','\xc5\xb9')
    char = char.replace('\\u017c','\xc5\xbc').replace('\\u017b','\xc5\xbb')
    char = char.replace('&#8217;',"'")
    char = char.replace('&#8211;',"-")    
    char = char.replace('&#8230;',"...")    
    char = char.replace('&#8222;','"').replace('&#8221;','"')    
    char = char.replace('[&hellip;]',"...")
    char = char.replace('&#038;',"&")    
    char = char.replace('&#039;',"'")
    char = char.replace('&quot;','"').replace('&oacute;','ó').replace('&rsquo;',"'")
    char = char.replace('&nbsp;',".").replace('&amp;','&').replace('&eacute;','e')
    return char    
def PLcharx(char):
    char=char.replace("\xb9","ą").replace("\xa5","Ą").replace("\xe6","ć").replace("\xc6","Ć")
    char=char.replace("\xea","ę").replace("\xca","Ę").replace("\xb3","ł").replace("\xa3","Ł")
    char=char.replace("\xf3","ó").replace("\xd3","Ó").replace("\x9c","ś").replace("\x8c","Ś")
    char=char.replace("\x9f","ź").replace("\xaf","Ż").replace("\xbf","ż").replace("\xac","Ź")
    char=char.replace("\xf1","ń").replace("\xd1","Ń").replace("\x8f","Ź");
    return char    
    
def router(paramstring):
    params = dict(urllib_parse.parse_qsl(paramstring))
    if params:    
        mode = params.get('mode', None)

        if 'menu' in mode:
            mode2 = mode.split(':')[-1]
            
            if mode2 == 'tv':
                menuTv()
            elif mode2 == 'movies':
                menuMovies()
            elif mode2 == 'reality':
                menuReality()
                
        elif 'filtr' in mode:
            mode2 = mode.split(':')[-1]
            if 'kat' in mode2:
                dd='categories:'
                label=['all',"Action","Adventure","Animation","Biography","Comedy","Crime","Documentary","Drama","Family","Fantasy","History","Horror","Music","Musical","Mystery","Other","Politics","Reality","Romance","Sci-Fi","Sport","Talk Show","Thriller","TV Movie","Unknown","War","Western"]
                value=['',"genres[]=action","genres[]=adventure","genres[]=animation","genres[]=biography","genres[]=comedy","genres[]=crime","genres[]=documentary","genres[]=drama","genres[]=family","genres[]=fantasy","genres[]=history","genres[]=horror","genres[]=music","genres[]=musical","genres[]=mystery","genres[]=other","genres[]=politics","genres[]=reality","genres[]=romance","genres[]=sci-fi","genres[]=sport","genres[]=talk-show","genres[]=thriller","genres[]=tv-movie","genres[]=unknown","genres[]=war","genres[]=western"]
        
            elif 'rok' in mode2:
                dd='years:'
                label=['all',"2020","2019","2018","2017","2016","2015","2014","2013","2012","2011","2010","Older"]
                value=['',"year=2020","year=2019","year=2018","year=2017","year=2016","year=2015","year=2014","year=2013","year=2012","year=2011","year=2010","year=older"]

            s = xbmcgui.Dialog().multiselect('Select '+dd,label)    
            if s<=-1: quit()
            if isinstance(s,list):
                if 0 in s: s=[0]

                v = '&'+'%s'%('&'.join( [ value[val].replace('[]','[%s]'%str(i)) for i,val in enumerate(s)])) if s[0]!=0 else ''

                
                n = ', '.join( [ label[i] for i in s])    
            else:
                s = s if s>-1 else quit()

                v = '&'+'%s'%value[s].replace('[]','[0]') if value[s] else ''

                n = label[s]
            v='?'+v[1:] if v.startswith('&g') else v
            addon.setSetting(mode2+'V',v)
            addon.setSetting(mode2+'N',n)
                

            xbmc.executebuiltin('Container.Refresh')
            
            
            
            
            
        elif mode =="listmovies":
            ListSubsMov(exlink,page)

        elif mode =="resfil":
            ResetFilters(exlink)
        elif mode == 'getLinks':

            getLinks(exlink)
        elif mode == 'playVid':
            PlayVid(exlink)    
        elif mode == 'listsubsmov':
            ListSubsMov(exlink,page)    
        elif mode == 'listseasons':
        
            ListSeasons(exlink,nazwa)
        elif mode == 'listEpisodes2':
            ListEpisodes2(exlink)
        elif mode == 'listcateg':
            ListCateg(exlink)
        elif mode == 'listepisodes':
            ListEpisodes(exlink)    
        elif mode=='search':
            query = xbmcgui.Dialog().input(u'Search...', type=xbmcgui.INPUT_ALPHANUM)
            if query:      
                query=query.replace(' ','+')
                ListSubsMov('https://vww.themoviebay.net/search?q='+query,1)
            else:
                pass
    else:
        home()
        xbmcplugin.endOfDirectory(addon_handle)    
if __name__ == '__main__':
    router(sys.argv[2][1:])