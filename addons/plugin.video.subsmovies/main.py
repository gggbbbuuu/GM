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
    
import resolveurl as urlresolver

import json
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(urllib_parse.parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.subsmovies')

PATH            = addon.getAddonInfo('path')

if six.PY2:
    DATAPATH        = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
else:
    DATAPATH        = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    
RESOURCES       = PATH+'/resources/'
FANART=RESOURCES+'rolka.png'
if six.PY2:
    napisy = xbmc.translatePath('special://temp/napisy.txt')
else:
    napisy = xbmcvfs.translatePath('special://temp/napisy.txt')

exlink = params.get('url', None)
name= params.get('title', None)

page = params.get('page',[1])[0]

MAIN_URL ='https://subsmovies.club/'  #https://isubsmovies.com/movies

UA= 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0'
TIMEOUT=15

headers = {'User-Agent': UA,}
sess = requests.Session()

def build_url(query):
    return base_url + '?' + urllib_parse.urlencode(query)

def add_item(url, name, image, mode, infoLabels=False, itemcount=1, page=1,fanart=FANART,contextmenu=None,IsPlayable=False, folder=False):
    list_item = xbmcgui.ListItem(label=name)
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
        url = build_url({'mode': mode, 'url' : url, 'page' : page, 'title':name}),            
        listitem=list_item,
        isFolder=folder)
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")
    
def home():
    add_item('https://subsmovies.club/', 'All movies', RESOURCES+'videoz.png', "listsubsmov",fanart=FANART, folder=True)    
    add_item('https://subsmovies.club/', ' Categories', RESOURCES+'videoz.png', "listcateg",fanart=FANART, folder=True)    
    add_item('', '[COLOR lightblue]Search[/COLOR]', RESOURCES+'search2.png', "search", folder=True)    

def ListSubsMov(exlink,page):
    page = int(page) if page else 1    
    filmy,pagination=getSubsMov(exlink,page)
    
    itemz=filmy
    items = len(filmy)

    for f in itemz:
        modemy='getLinks'
        isplay=True
        fold=False
        add_item(name=f.get('title'), url=f.get('href'), mode=modemy, image=f.get('img'), infoLabels=f, itemcount=items,folder=fold, IsPlayable=isplay)    
    
    if pagination:
        add_item(name='[COLOR blue]>> next page >>[/COLOR]', url=exlink, mode='listsubsmov', image=RESOURCES+'right.png', page=pagination,fanart=FANART, folder=True)        
    xbmcplugin.setContent(addon_handle, 'movies')    
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")
    xbmcplugin.endOfDirectory(addon_handle)
    
def getSubsMov(url,page):
    if '?s=' in url:
        url = url.replace('https://subsmovies.club/','https://subsmovies.club/page/%s/'%page    )
    else:
        url = url + '/page/%d' %page    
    out=[]

    html=getUrlReqOk(url)

    links = parseDOM(html,'article', attrs={'id': "post\-\d+"})

    for link in links:
        href = parseDOM(link,'a', ret="href")[0]
        tyt = parseDOM(link,'a', ret="title")[0]
        imag = parseDOM(link,'img', ret="src")[0]
        href = MAIN_URL + href if href.startswith('/') else href
        imag = MAIN_URL + imag if imag.startswith('/') else imag

        ftitle=tyt.strip()
        plot=ftitle

        out.append({'title':ftitle,'href':href,'img':imag,'year':'','plot':plot,'genre':''})
        
        
    prevpage=False 
    nextpage=False  
    ktora=False

    if html.find('>Next Page')>1:
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
        add_item(name=f.get('title'), url=f.get('href'), mode='getLinks', image=f.get('img'), folder=False, infoLabels=f, itemcount=items, IsPlayable=True)    
    xbmcplugin.setContent(addon_handle, 'episodes')    
    xbmcplugin.endOfDirectory(addon_handle)
    
def ListEpisodes(exlink):
    episodes = getEpisodes(exlink)
    itemz=episodes
    items = len(episodes)
    for f in itemz:
        add_item(name=f.get('title'), url=f.get('href'), mode='getLinks', image=f.get('img'), folder=False, infoLabels=f, itemcount=items, IsPlayable=True)        
    xbmcplugin.setContent(addon_handle, 'episodes')
    xbmcplugin.endOfDirectory(addon_handle)
    
def getEpisodes(url):
    

    html = getUrlReqOk(url)
    out=[]
    dane = re.findall(r'ld\+json">([^>]+)</script>',html,re.DOTALL)

    imag = None
    plot = None
    genr = None
    if dane:
        #xxx = 
        try:
            dane=json.loads(json.loads(json.dumps(dane[0])))

            plot = dane.get('description','')
            imag = dane.get('image','')
            tyt = dane.get('name','')
            
            genres = dane.get('genre','')
            try:
                genr = ','.join(genres)
            except:
                genr = ''
        except:
            plot = parseDOM(html,'div', attrs={'class': "description col-md-9"})   # <div class="description col-md-9">
            plot = plot [0] if plot else None
            dane2  = parseDOM(html,'div', attrs={'class': "container movie-header"})[0]#<div class="container movie-header">
            imag = re.findall('img src="([^"]+)"',dane2)[0]
            imag = MAIN_URL+imag
            genredane  = parseDOM(html,'div', attrs={'class': "categories col-md-9 text-center"})[0] #<div class="categories col-md-9 text-center">
            genres = re.findall('title="([^"]+)">',genredane)
            genr = ','.join(genres)
            pass

    plot = plot if plot else ''
    imag = imag if imag else ''
    genr = genr if genr else ''

    sezons=parseDOM(html,'div', attrs={'class': "subtitles col-md-.+?"}) 
    for sezon in sezons:
        try:
            ses = re.findall('S(\d+)</th>',sezon,re.DOTALL)[0]
            hreftit=re.findall('href="([^"]+)">([^>]+)<',sezon,re.DOTALL)
            for href,tyt in hreftit:
                href=MAIN_URL+href
                ftitle=tyt.strip()
                
                epis=re.findall(' E(\d+)',ftitle,re.DOTALL)

                jaki = ' - S%02dE%02d'%(int(ses),int(epis[0]))

                tyt = re.sub(' E\d+',jaki,ftitle)
                out.append({'title':tyt,'href':href,'img':imag,'plot':plot,'genre':genr, 'season' : int(ses),'episode' : int(epis[0]) if epis else '',})
        except:
            continue
    return out    
def ListCateg(url):
    categs=getCateg(url)
    itemz=categs
    items = len(categs)
    for f in itemz:
        add_item(name=f.get('title'), url=f.get('href'), mode='listsubsmov', image=RESOURCES+'videoz.png', folder=True, infoLabels=f, itemcount=items)    
    xbmcplugin.setContent(addon_handle, 'videos')
    xbmcplugin.endOfDirectory(addon_handle)    
    
def getCateg(url):
    out=[]
    html=getUrlReqOk(url)

    result=parseDOM(html,'ul', attrs={'id': "menu\-.+?"})[0]

    
    hrefcat=re.findall('<a href="([^"]+)">([^>]+)</a>',result,re.DOTALL)
    for href,cat in hrefcat:

        ftitle=cat.strip()
        out.append({'title':ftitle,'href':href,'img':'','plot':ftitle})
    return out

def getPost(ref=''):
    headersok = {
    'User-Agent': UA,
    'Accept': '*/*',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Referer': ref,
    'X-Requested-With': 'XMLHttpRequest',
    'Connection': 'keep-alive',
    'TE': 'Trailers',}
    content = sess.post('https://isubsmovies.com/dbquery.php?action=loadPlayer', headers=headersok).json() #https://isubsmovies.com/dbquery.php?action=loadPlayer
    return content
    
def getUrlReqOk(url,ref=''):    

    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': ref,
    'TE': 'Trailers',}
    content=sess.get(url, headers=headersok,verify=False).text    
    return content.replace("\'",'"')    

def PlayVid(exlink):
    
    subt=exlink.split('|')
    try:
        if subt[1]:
            r = requests.get(subt[0], allow_redirects=True)
            content=r.content
            if six.PY3:
                content= content.decode(encoding='utf-8', errors='strict')
            if six.PY3:
                open(napisy, 'w', encoding='utf-8').write(content)
            else:
                open(napisy, 'w').write(content)
            open(napisy, 'w').write(content)
            play_item = xbmcgui.ListItem(path=subt[1])
            play_item.setSubtitles([napisy])
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)    
    except:
        play_item = xbmcgui.ListItem(path=subt[0])
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)    
        
def getLinks(url):
    html=getUrlReqOk(url)
    
    plot = re.findall('>Descriptions:<.+?>(.+?)<',html)#[0]

    tytul = parseDOM(html, 'h3')[0] #<h3>
    plot = plot[0] if plot else tytul
    #html = jdata.get('Data','').get('Player','')

    href = parseDOM(html, 'iframe', ret='src')[0]
    href = href.replace('&amp;','&')
    html=getUrlReqOk(href,url)

    href = parseDOM(html, 'iframe', ret='src')[0]
    href = href.replace('&amp;','&')
    html=getUrlReqOk(href,url)
    link = parseDOM(html, 'source', ret='src')#[0]

    if link:

        play_item = xbmcgui.ListItem(path=link[0])
        play_item.setInfo(type="Video", infoLabels={"title": tytul,'plot':plot})
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)    

    else:
        xbmcgui.Dialog().notification('[COLOR red][B]Error[/B][/COLOR]', "[COLOR red][B]This video doesn't exists in our servers or has been deleted.[/B][/COLOR]", xbmcgui.NOTIFICATION_INFO, 5000)

def PLchar(char):
    char=char.replace("\xb9","ą").replace("\xa5","Ą").replace("\xe6","ć").replace("\xc6","Ć")
    char=char.replace("\xea","ę").replace("\xca","Ę").replace("\xb3","ł").replace("\xa3","Ł")
    char=char.replace("\xf3","ó").replace("\xd3","Ó").replace("\x9c","ś").replace("\x8c","Ś")
    char=char.replace("\x9f","ź").replace("\xaf","Ż").replace("\xbf","ż").replace("\xac","Ź")
    char=char.replace("\xf1","ń").replace("\xd1","Ń").replace("\x8f","Ź");
    return char    
    
if __name__ == '__main__':
    mode = params.get('mode', None)
    
    if not mode:
        home()
    
        xbmcplugin.endOfDirectory(addon_handle)            
    elif mode == 'getLinks':
        getLinks(exlink)
    elif mode == 'PlayVid':
        PlayVid(exlink)    
    elif mode == 'listsubsmov':
        ListSubsMov(exlink,page)    
    elif mode == 'listseasons':

        ListSeasons(exlink,name)
    elif mode == 'listEpisodes2':
        ListEpisodes2(exlink)
    elif mode == 'listcateg':
        ListCateg(exlink)
    elif mode == 'listepisodes':
        ListEpisodes(exlink)    
    elif mode=='search':
        query = xbmcgui.Dialog().input(u'Search...', type=xbmcgui.INPUT_ALPHANUM)
        if query:      
            ListSubsMov('https://subsmovies.club/?s='+query,1)
        else:
            pass
