# -*- coding: UTF-8 -*-

import sys, os, re, json, base64
if sys.version_info >= (3,0,0):
# for Python 3
    to_unicode = str
    from resources.lib.cmf3 import parseDOM
    from resources.lib.cmf3 import replaceHTMLCodes
    from urllib.parse import unquote, parse_qs, parse_qsl, quote, urlencode, quote_plus

else:
    # for Python 2
    to_unicode = unicode
    from resources.lib.cmf2 import parseDOM
    from resources.lib.cmf2 import replaceHTMLCodes
    from urllib import unquote, quote, urlencode, quote_plus
    from urlparse import parse_qsl, parse_qs
    
import io

from resources.lib import recaptcha_v2

import xbmc, xbmcvfs

import requests
import xbmcgui
import xbmcplugin
import xbmcaddon

import resolveurl 

#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.fmoviesto')

PATH            = addon.getAddonInfo('path')
try:
    DATAPATH        = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
except:
    DATAPATH    = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
    
if not os.path.exists(DATAPATH):
    os.makedirs(DATAPATH)
jfilename = os.path.join(DATAPATH,'jfilename')
napisy = os.path.join(DATAPATH,'napisy')


RESOURCES       = PATH+'/resources/'

FANART=RESOURCES+'fanart.jpg'

exlink = params.get('url', None)
nazwa= params.get('title', None)
rys = params.get('image', None)
page = params.get('page',[1])[0]


fsortv = addon.getSetting('fsortV')
fsortn = addon.getSetting('fsortN') if fsortv else 'default'

fkatv = addon.getSetting('fkatV')
fkatn = addon.getSetting('fkatN') if fkatv else 'all'

fkrajv = addon.getSetting('fkrajV')
fkrajn = addon.getSetting('fkrajN') if fkrajv else 'all'

frokv = addon.getSetting('frokV')
frokn = addon.getSetting('frokN') if frokv else 'all'

fwerv = addon.getSetting('fwerV')
fwern = addon.getSetting('fwerN') if fwerv else 'all'

fnapv = addon.getSetting('fnapV')
fnapn = addon.getSetting('fnapN') if fnapv else 'all'

snapv = addon.getSetting('snapV')
snapn = addon.getSetting('snapN') if fnapv else 'all'

ssortv = addon.getSetting('ssortV')
ssortn = addon.getSetting('ssortN') if ssortv else 'default'

skatv = addon.getSetting('skatV')
skatn = addon.getSetting('skatN') if skatv else 'all'

skrajv = addon.getSetting('skrajV')
skrajn = addon.getSetting('skrajN') if skrajv else 'all'

srokv = addon.getSetting('srokV')
srokn = addon.getSetting('srokN') if srokv else 'all'

swerv = addon.getSetting('swerV')
swern = addon.getSetting('swerN') if swerv else 'all'

dataf =  addon.getSetting('fdata')    
datas =  addon.getSetting('sdata')    

wybornapisow = True

UA='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0'

headers = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'TE': 'Trailers',
}
sess = requests.Session()
def build_url(query):
    return base_url + '?' + urlencode(query)

def add_item(url, name, image, mode, folder=False, IsPlayable=False, infoLabels=False, movie=True,itemcount=1, page=1,fanart=FANART,moviescount=0):
    list_item = xbmcgui.ListItem(label=name)

    if IsPlayable:
        list_item.setProperty("IsPlayable", 'True')
    if not infoLabels:
        infoLabels={'title': name,'plot':name}
    list_item.setInfo(type="video", infoLabels=infoLabels)    
    list_item.setArt({'thumb': image, 'poster': image, 'banner': image, 'icon': image, 'fanart': FANART})
    ok=xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url = build_url({'mode': mode, 'url' : url, 'page' : page, 'moviescount' : moviescount,'movie':movie,'title':name,'image':image}),            
        listitem=list_item,
        isFolder=folder)
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")
    return ok
    
def menuMovies():
    add_item('https://fmovies.to/filter?type[]=movie', 'List movies', 'DefaultMovies.png', "listmovies", True)    
    add_item('', "-      [COLOR lightblue]sort:[/COLOR] [B]"+fsortn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:fsort', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]country:[/COLOR] [B]"+fkrajn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:fkraj', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]genre:[/COLOR] [B]"+fkatn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:fkat', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]year:[/COLOR] [B]"+frokn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:frok', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]quality:[/COLOR] [B]"+fwern+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:fwer', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]subtitles:[/COLOR] [B]"+fnapn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:fnap', folder=False,fanart='')
    add_item('', '[COLOR lightblue]Search[/COLOR]', 'DefaultAddonsSearch.png', "search", True)    
    add_item('f', "[I][COLOR violet][B]Reset all filters[/COLOR][/I][/B]",'DefaultAddonService.png', "resetfil", folder=False)

    xbmcplugin.endOfDirectory(addon_handle)
    
def menuTVshows():
    add_item('https://fmovies.to/filter?type[]=series', 'List tv-series', 'DefaultMovies.png', "listmovies", True)    
    add_item('', "-      [COLOR lightblue]sort:[/COLOR] [B]"+ssortn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:ssort', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]country:[/COLOR] [B]"+skrajn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:skraj', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]genre:[/COLOR] [B]"+skatn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:skat', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]year:[/COLOR] [B]"+srokn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:srok', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]quality:[/COLOR] [B]"+swern+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:swer', folder=False,fanart='')
    add_item('', "-      [COLOR lightblue]subtitles:[/COLOR] [B]"+snapn+'[/B]','DefaultRecentlyAddedMovies.png', 'filtr:snap', folder=False,fanart='')
    
    
    add_item('s', "[I][COLOR violet][B]Reset all filters[/COLOR][/I][/B]",'DefaultAddonService.png', "resetfil", folder=False)
    add_item('', '[COLOR lightblue]Search[/COLOR]', 'DefaultAddonsSearch.png', "search", True)    
    xbmcplugin.endOfDirectory(addon_handle)
def home():
    add_item('https://fmovies.to/movies', 'Movies', 'DefaultMovies.png', "menumov", True)    
    add_item('https://fmovies.to/movies', 'TV-Series', 'DefaultMovies.png', "menutvs", True)    
    add_item('', '[COLOR lightblue]Search[/COLOR]', 'DefaultAddonsSearch.png', "search", True)    

    xbmcplugin.endOfDirectory(addon_handle)
    

def ListMovies(exlink,page):

    links, serials, pagin = getMovies(exlink,page)

    itemz=links
    items = len(links)
    mud='getLinks'
    fold=True
    for f in itemz:
        add_item(name=f.get('title'), url=f.get('href'), mode=mud, image=f.get('img'), folder=fold, infoLabels={'plot':f.get('title'),'title':f.get('title')}, itemcount=items, IsPlayable=False)    
    itemz=serials
    items = len(serials)
    mud='getseasons'
    fold=True
    for f in itemz:
        add_item(name=f.get('title'), url=f.get('href'), mode=mud, image=f.get('img'), folder=fold, infoLabels={'plot':f.get('title'),'title':f.get('title')}, itemcount=items)    
    
    if pagin:
        add_item(name='[COLOR blue]>> Nastepna strona [/COLOR]', url=exlink, mode='listmovies', image='', folder=True, page=pagin)
    if links or serials:
        xbmcplugin.setContent(addon_handle, 'videos')    

        xbmcplugin.endOfDirectory(addon_handle)        

def getMovies(url,page=1):
    if not 'search?keyword' in url:
        datax = datas if '=series' in url else dataf
    
        if '&page=' in url:
        
            url = re.sub('\&page=\\d+','&page=%d'%int(page),url)
        else:
        
            url = url +datax+ '&page=%d' %int(page)
    
    nturl = '&amp;page=%d"' %(int(page)+1) 
    
    r = sess.get(url,verify=False, headers=headers)
    html=r.content
    if sys.version_info >= (3,0,0):
        html = html.decode(encoding='utf-8', errors='strict')
    out=[]
    serout=[]

    npage=False

    pagination = parseDOM(html, 'ul', attrs={'class': "pagination"}) #[0]
    if pagination:
        npage = str(int(page)+1)if nturl in pagination[0] else False

    result = parseDOM(html, 'div', attrs={'class': "filmlist\s+.*?"}) [0]
    ids = [(a.start(), a.end()) for a in re.finditer('<div class="item"', result)]
    ids.append( (-1,-1) )
    out=[]
    serout=[]
    for i in range(len(ids[:-1])):
        link = result[ ids[i][1]:ids[i+1][0] ]

        imag= parseDOM(link, 'img', ret='src')[0]
        imag = 'https:'+imag if imag.startswith('//') else imag
        title= parseDOM(link, 'a', ret='title')[0] 
        href = parseDOM(link, 'a', ret='href')[0]
        id =re.findall('([^\-]+$)',href)[0]
        href = 'https://fmovies.to'+href if href.startswith('/') else href
        typ = parseDOM(html, 'i', attrs={'class': "type"})#[0]  <i class="type">
        typ = typ[0].strip() if typ else ''
            
        
        
        
        plot =''

        ploturl = re.findall('data\-tip\s*=\s*"(.+?)"',link)[0]
        ploturl = 'https://fmovies.to/ajax/film/tooltip/'+ ploturl
        genre =''
        code =''
        year =''
        if '=series' in url or 'TV' in typ:
            serout.append({'title':PLchar(title),'href':href+'|'+id,'img':imag,'plot':PLchar(plot),'genre':genre,'year':year,'code':code})
        else:
            out.append({'title':PLchar(title),'href':href+'|'+id,'img':imag,'plot':PLchar(plot),'genre':genre,'year':year,'code':code})
    return (out,serout, npage) 
    
def getVerid(id):

    ab='aaaaaa'#AAAAAAAAAA'#ABBDEEBBAABBAABB'#ggo()
    ac = id

    hj = dekodujNowe (ab,ac)

    if sys.version_info >= (3,0,0):
        hj=hj.encode('Latin_1')

    hj2 = encode2(hj)   
    if sys.version_info >= (3,0,0):
        hj2=(hj2.decode('utf-8'))
        

    hjkl = ab + hj2
    return hjkl
    
def getLinks(exlink):
    href,id = exlink.split('|')

    html = sess.get(href, headers=headers, verify=False).content
    if sys.version_info >= (3,0,0):
        html = html.decode(encoding='utf-8', errors='strict')
    result = parseDOM(html, 'section', attrs={'class': "info"})[0]  
    plot = parseDOM(result, 'div', attrs={'itemprop': "description"})
    plot = PLchar(plot[0]) if plot else ''
    imag = parseDOM(result, 'img', ret='src')#[0]
    imag = imag[0] if imag else ''
    imag = 'https:'+imag if imag.startswith('//') else imag
    
    genres = re.findall('Genre\:(.+?)<\/div>',result)
    genres = genres[0] if genres else ''

    gg = re.findall('>([^<]+)<\/a>',genres)
    genre = ', '.join([(x.strip()).lower() for x in gg]) if gg else ''

    countries = re.findall('Country\:(.+?)<\/div>',result) # 
    countries = countries[0] if countries else ''
    cc = re.findall('>([^<]+)<\/a>',countries)
    country = ', '.join([x.strip() for x in cc]) if gg else ''

    tim = re.findall('span>(\d+)\s*min<',result)
    tim = int(tim[0])*60 if tim else ''

    
    
    qual = parseDOM(result, 'span', attrs={'class': "quality"}) 
    qual = qual[0].strip() if qual else ''

    yr = parseDOM(result, 'span', attrs={'itemprop': "dateCreated"})  
    yr = yr[0].strip() if yr else ''
    infol = {'plot':plot,'genre': genre,'country':country,'duration':tim,'year':yr}

    headers.update({'Referer': href})
    
    

    verid = getVerid(id)
    recap="03AGdBq25eDJkrezDo2y"
    params = (
        ('id', id),
       # ('verified', verid),
        ('vrf', verid),
        ('token', recap),
    )

    response = sess.get('https://fmovies.to/ajax/film/servers', headers=headers, params=params, verify=False)#
    
    html= (response.content)
    if sys.version_info >= (3,0,0):
        html = html.decode(encoding='utf-8', errors='strict')
    html= html.replace('\\"','"')

    if 'sitekey=' in html:

        sitek=re.findall('data\-sitekey="(.+?)"',html)[0]

        token = recaptcha_v2.UnCaptchaReCaptcha().processCaptcha(sitek, lang='en')

        data = {
                'g-recaptcha-response': token}
        
        response = sess.post('https://fmovies.to/waf-verify', headers=headers, data=data, cookies=sess.cookies, verify=False)#
        
        params = (
            ('id', id),
            ('token', token),
        )
        response = sess.get('https://fmovies.to/ajax/film/servers', headers=headers, params=params, cookies=response.cookies, verify=False)#

    html = (response.content)#.replace('\\"','"')
    if sys.version_info >= (3,0,0):
        html = html.decode(encoding='utf-8', errors='strict')
    html= html.replace('\\"','"')

   # linki = re.findall('data-id="([^"]+).*?<b>([^<]+).*?<span>([^<]+)',html)
  #  for linkid,host,qual in linki:
  #      tyt = nazwa+' - [I][COLOR khaki]'+host+'[/I] '+'- [B]('+qual+')[/COLOR][/B]'
  #      add_item(name=tyt, url=linkid+'|'+href, mode='playlink', image=imag, folder=False, infoLabels=infol, IsPlayable=True)

    
    linki = re.findall('data-id="([^"]+).*?<div>([^<]+)',html)
    for linkid1,host in linki:
        tyt = nazwa+' - [I][COLOR khaki]'+host+'[/I] '+' [B][/COLOR][/B]'

        linkid = re.findall(linkid1+'"\:"([^"]+)',html)#[0]
        if linkid:
            add_item(name=tyt, url=linkid[0]+'|'+href, mode='playlink', image=imag, folder=False, infoLabels=infol, IsPlayable=True)
    
    


    if len(linki)>0:

        xbmcplugin.setContent(addon_handle, 'videos')
        xbmcplugin.endOfDirectory(addon_handle)    
    else:
        xbmcgui.Dialog().notification('[B]Błąd[/B]', 'Brak materiałów do wyświetlenia',xbmcgui.NOTIFICATION_INFO, 8000,False)
        
def dec(chra):

    try:    
        if sys.version_info >= (3,0,0):
            chra =repr(chra.encode('utf-8'))
            chra = chra.replace('\\xc3\\xaa','ę').replace('\\xc3\\x8a','Ę')
            chra = chra.replace('\\xc3\\xa6','ć').replace('\\xc3\\x86','Ć')
            chra = chra.replace('\\xc2\\xbf','ż').replace('\\xc2\\x9f','Ż')
            chra = chra.replace('\\xc2\\xb9','ą').replace('\\xc2\\x99','Ą')
            
            chra = chra.replace('\\xc5\\x93','ś').replace('\\xc5\\x92','Ś')
            chra = chra.replace('\\xc3\\xb3','ó').replace('\\xc3\\x93','Ó')
            
            chra = chra.replace('\\xc5\\xb8','ź').replace('\\xc5\\xb7','Ź')
            
            chra = chra.replace('\\xc2\\xb3','ł').replace('\\xc2\\x93','Ł')
            
            chra = chra.replace('\\xc3\\xb1','ń').replace('\\xc3\\x91','Ń')
            chra = chra .replace("b\'",'')

            chra = chra .replace("\\n",'\n').replace("\\r",'\r') 
            chra = chra .replace("\\'","'")

        else:

            chra = chra.replace('\xc3\xaa','ę').replace('\xc3\x8a','Ę')
            chra = chra.replace('\xc3\xa6','ć').replace('\xc3\x86','Ć')
            chra = chra.replace('\xc2\xbf','ż').replace('\xc2\x9f','Ż')
            chra = chra.replace('\xc2\xb9','ą').replace('\xc2\x99','Ą')
            
            chra = chra.replace('\xc5\x93','ś').replace('\xc5\x92','Ś')
            chra = chra.replace('\xc3\xb3','ó').replace('\xc3\x93','Ó')
            
            chra = chra.replace('\xc5\xb8','ź').replace('\xc5\xb7','Ź')
            
            chra = chra.replace('\xc2\xb3','ł').replace('\xc2\x93','Ł')
            
            chra = chra.replace('\xc3\xb1','ń').replace('\xc3\x91','Ń')



    except:
        pass
        
    return chra
    
def transPolish(subtlink):

    try:
        response = sess.get(subtlink, headers=headers, verify=False)#.content

        if sys.version_info >= (3,0,0):
        
            response  = response.text
        else:
            response  = response.content
        gg=dec(response)

        open(napisy, 'w').write(gg)

        return True
    except:
        return False
    
def PlayLink(exlink):
    id,href = exlink.split('|')

    params = (
        ('id', id),
    )

    headers.update({'Referer': href})
    response = sess.get('https://fmovies.to/ajax/episode/info', headers=headers, params=params, verify=False)#

    ab=response.content
    if sys.version_info >= (3,0,0):
        ab = ab.decode(encoding='utf-8', errors='strict')
    
    
    try:
        jsonab = json.loads(ab)
    except:
        pass
    if jsonab:
        url = jsonab.get('url',None)

    link2 = DecodeLink(url)

    reg = '?sub.info='
    reg = reg if reg in link2 else '?subtitle_json='

    link,subt = link2.split(reg)
    
    
    subsout=[]
    subtx = unquote(subt)
    subt = False
    if subtx:
        response = sess.get(subtx, headers=headers, verify=False).json()

        for subtitle in response:
            subt = subtitle.get('src',None)
            subt2 = subtitle.get('file',None)
            subt = subt if subt else subt2
            label = subtitle.get('label',None)
            subsout.append({'label':label,'subt':subt})
    if wybornapisow and subsout:
        labels = [x.get('label') for x in subsout]
        sel = xbmcgui.Dialog().select('Subtitle language',labels)    
        if sel>-1:
            subt=subsout[sel].get('subt')
            if subsout[sel].get('label') == 'Polish':
            
                subt = napisy if transPolish(subt) else subt
                
        else:
            subt = False

    if not 'mcloud' in link2:
        stream_url = resolveurl.resolve(link)
    else:

        link = link2.replace('/embed/','/info/')
        response = sess.get(link, headers=headers, verify=False).json()
        outz=[]
        if response.get('success',None):
            srcs = response.get('media',None).get('sources',None)
            for src in srcs:
                fil = src.get('file',None)
                if 'm3u8' in fil:
                    stream_url = fil+'|User-Agent='+UA+'&Referer='+link2
                    break

    play_item = xbmcgui.ListItem(path=stream_url)

    if subt:
        play_item.setSubtitles([subt])
    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

def DecodeLink(mainurl):

    ab=mainurl[0:6]   #23.09.21
    ac2 = mainurl[6:]    #23.09.21

    ac= decode2(ac2)
    
    link = dekodujNowe(ab,ac)
    link = unquote(link)
    return link

#def getFileJson():
#    with xbmcvfs.File(jfilename) as f:
#        jsondata = json.loads(f.read())
#    html =     jsondata.get('html',None)
#    return html


    
    
def getFileJson():

    from contextlib import closing
    from xbmcvfs import File
    
    with closing(File(jfilename)) as f:
        jsondata = f.read()
        
    jsondata = json.loads(jsondata)

    html =     jsondata.get('html',None)
    return html


def getLinksSerial(hrefx):
    try:
        sez,ep = hrefx.split('-')
    except:
        sez,ep,sh = hrefx.split('-')
    a=''
    
    htmlx =     getFileJson()
    href = re.findall('href="([^"]+)',htmlx)[0]
    href = 'https://fmovies.to'+href if href.startswith('/') else href
    
    
    html = sess.get(href, headers=headers, verify=False).content
    if sys.version_info >= (3,0,0):
        html = html.decode(encoding='utf-8', errors='strict')
    
    result = parseDOM(html, 'section', attrs={'class': "info"})[0]  
    plot = parseDOM(result, 'div', attrs={'itemprop': "description"})
    
    mname = parseDOM(result, 'h1', attrs={'itemprop': "name","class":"title"}) # = <h1 itemprop="name" class="title">
    mname = '[B]'+mname[0]+'[/B] ' if mname else ''
    
    plot = mname+'[CR]'+plot[0] if plot else ''
    imag = parseDOM(result, 'img', ret='src')#[0]
    imag = imag[0] if imag else ''
    imag = 'https:'+imag if imag.startswith('//') else imag
    
    genres = re.findall('Genre\:(.+?)<\/div>',result)
    genres = genres[0] if genres else ''
    
    gg = re.findall('>([^<]+)<\/a>',genres)
    genre = ', '.join([(x.strip()).lower() for x in gg]) if gg else ''
    
    countries = re.findall('Country\:(.+?)<\/div>',result) # 
    countries = countries[0] if countries else ''
    cc = re.findall('>([^<]+)<\/a>',countries)
    country = ', '.join([x.strip() for x in cc]) if gg else ''
    
    tim = re.findall('span>(\d+)\s*min<',result)
    tim = int(tim[0])*60 if tim else ''
    
    
    
    qual = parseDOM(result, 'span', attrs={'class': "quality"}) 
    qual = qual[0].strip() if qual else ''
    
    yr = parseDOM(result, 'span', attrs={'itemprop': "dateCreated"})  
    yr = yr[0].strip() if yr else ''
    infol = {'plot':plot,'genre': genre,'country':country,'duration':tim,'year':yr}
    
    
    servid = 1
    try:
        href1,serwery = re.findall("""href="([^"]+)"\\n\s*data-kname="%s".*?data\-ep=\\'({.*?)}"""%(hrefx),htmlx,re.DOTALL)[0]
    except:
        servid = 0

    href = 'https://fmovies.to'+href1 if href1.startswith('/') else href1

    linki = re.findall('data-id="([^"]+).*?<div>([^<]+)',htmlx,re.DOTALL)
    
    
    
    
    
    
    
    
    nazwax = '- '+nazwa if mname else nazwa
    
    for linkid1,host in linki:
        tyt = mname + nazwax+' - [I][COLOR khaki]'+host+'[/I][/COLOR] '#+'- [B]('+qual+')[/COLOR][/B]'
    
        linkid = re.findall(linkid1+'"\:"([^"]+)',serwery)#[0]
        if linkid:
            add_item(name=tyt, url=linkid[0]+'|'+href, mode='playlink', image=imag, folder=False, infoLabels=infol, IsPlayable=True)
    
    
    
    
    
    
       
#    for serv,linkid,href in servid :
#    
#        href = 'https://fmovies.to'+href if href.startswith('/') else href
#    
#        nazwax = '- '+nazwa if mname else nazwa
#        host = re.findall('data-id="%s".*?>(.+?)<'%str(serv),servers,re.DOTALL)[0]
#        tyt = mname + nazwax+' - [I][COLOR khaki]'+host+'[/I][/COLOR] '#+'- [B]('+qual+')[/COLOR][/B]'
#        add_item(name=tyt, url=linkid+'|'+href, mode='playlink', image=imag, folder=False, infoLabels=infol, IsPlayable=True)
    
    #if len(servid)>0:
    if servid:
        xbmcplugin.setContent(addon_handle, 'videos')
        xbmcplugin.endOfDirectory(addon_handle)    
    else:
        xbmcgui.Dialog().notification('[B]Błąd[/B]', 'Brak materiałów do wyświetlenia',xbmcgui.NOTIFICATION_INFO, 8000,False)

def ListEpisodes(exlink):

    links= getEpisodes(exlink)    
    items = len(links)
    for f in links:
        add_item(name=f.get('title'), url=f.get('href'), mode='getLinksSerial', image=f.get('img'), folder=True, infoLabels= {'plot':nazwa}, itemcount=items, IsPlayable=True)        
    xbmcplugin.setContent(addon_handle, 'files')    

    xbmcplugin.endOfDirectory(addon_handle)    
    
def getEpisodes(href):
    seas,serv = href.split('|')

    html =     getFileJson() 

   # episodes = re.findall('data-season="%s"(.*?)<\/ul>'%str(seas),html,re.DOTALL)[0]

    
    episodes = parseDOM(html,'div', attrs={'class': "episodes",'data\-season': str(seas)})[0] 
    
    
    
    out=[]

    #<div class="episode">
    epizody = parseDOM(episodes, 'div', attrs={'class': "episode"})#[0] 
    for epi in epizody:
    
   # for kname,title in re.findall('data-kname="([^"]+).*?>(.+?)<\/',episodes,re.DOTALL):
        kname = re.findall('data\-kname="([^"]+)',epi,re.DOTALL)[0]

        try:
            sez,epis = kname.split('-')
        except:
            sez,epis,sh = kname.split('-')
        seas = 'S%02d'%int(sez)
        try:
            episod = 'E%02d'%int(epis)
        except:
            episod = 'E-%s'%str(epis)
        title = re.findall('class="name">([^<]+)',epi,re.DOTALL)#[0]
        if title:
            title = re.sub("<[^>]*>","",title[0].strip())
        else:
            title = nazwa.split('-')[-1]
        title = title+' ('+seas+episod+')'
        out.append({'title':title ,'href':kname,'img':rys})

    return out
def ListSeasons(exlink):

    links= getSerial(exlink)    
    items = len(links)
    for f in links:
        add_item(name=f.get('title'), url=f.get('href'), mode='getEpisodes', image=f.get('img'), folder=True, infoLabels= {'plot':nazwa}, itemcount=items, IsPlayable=True)        
    xbmcplugin.setContent(addon_handle, 'files')    

    xbmcplugin.endOfDirectory(addon_handle)    
    
def getSerial(href):

    out=[]
    href,id = href.split('|')

    headers.update({'Referer': href})

    recap =         addon.getSetting('cap_token')
    if not recap:
    
    
        recap="03AGdBq25eDJkrezDo2y"
 
    verid = getVerid(id)    
    params = (
        ('id', id),
        ('vrf', verid),

    )

    response = sess.get('https://fmovies.to/ajax/film/servers', headers=headers, params=params, verify=False)#
    
    html = (response.content)

    if sys.version_info >= (3,0,0):
        html = html.decode(encoding='utf-8', errors='strict')
    html= html.replace('\\"','"')
 
    if 'sitekey=' in html:

        sitek=re.findall('data\-sitekey="(.+?)"',html)[0]

        token = recaptcha_v2.UnCaptchaReCaptcha().processCaptcha(sitek, lang='en')

        data = {
                'g-recaptcha-response': token}
        
        response = sess.post('https://fmovies.to/waf-verify', headers=headers, data=data, cookies=sess.cookies, verify=False)#
        
        params = (
            ('id', id),
            ('token', token),
        )
        response = sess.get('https://fmovies.to/ajax/film/servers', headers=headers, params=params, cookies=response.cookies, verify=False)#
    
        
    jsondata = response.json()

    with io.open(jfilename, 'w', encoding='utf8') as f:
        str_ = json.dumps(jsondata,
            indent=4, sort_keys=True,
            separators=(',', ': '), ensure_ascii=False)
        f.write(to_unicode(str_))

    html = jsondata.get('html',None)
    

  #  sezony = parseDOM(html, 'ul', attrs={'class': "seasons"})[0]
  #  sezonyx = re.findall('<li(.*?)<\/li>',sezony,re.DOTALL)
    sezony = parseDOM(html, 'div', attrs={'id': "seasons"})[0]
    
    

    sezonyx = re.findall('<li(.*?)<\/li>',sezony,re.DOTALL)

    for sez in sezonyx:

       # sesid,servers,title = re.findall('data-id="([^"]+).+?data\-servers="([^"]+).+?>(.+?)<span>',sez,re.DOTALL)[0]
     #   sesid,servers,title = re.findall('data-number="([^"]+).+?data\-servers="([^"]+).+?>(.+?)<span>',sez,re.DOTALL)[0]
        

        sesid = re.findall('value="([^"]+)',sez,re.DOTALL)[0]
        title= re.findall('>([^<]+)<span',sez,re.DOTALL)[0]
        servers = ''
        out.append({'title':title.strip()+nazwa,'href':sesid+'|'+servers,'img':rys})
    return out
    

try:
    import string
    STANDARD_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    CUSTOM_ALPHABET =   'eST4kCjadnvlAm5b1BOGyLJzrE90Q6oKgRfhV+M8NDYtcxW3IP/qp2i7XHuwZFUs'

    ENCODE_TRANS = string.maketrans(STANDARD_ALPHABET, CUSTOM_ALPHABET)
    DECODE_TRANS = string.maketrans(CUSTOM_ALPHABET, STANDARD_ALPHABET)
except:
    STANDARD_ALPHABET = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    CUSTOM_ALPHABET =   b'eST4kCjadnvlAm5b1BOGyLJzrE90Q6oKgRfhV+M8NDYtcxW3IP/qp2i7XHuwZFUs'
    ENCODE_TRANS = bytes.maketrans(STANDARD_ALPHABET, CUSTOM_ALPHABET)
    DECODE_TRANS = bytes.maketrans(CUSTOM_ALPHABET, STANDARD_ALPHABET)

    
    
    
def encode2(input):
    return base64.b64encode(input).translate(ENCODE_TRANS)
def decode2(input):
    try:    
        xx= input.translate(DECODE_TRANS)
    except:
        xx= str(input).translate(DECODE_TRANS)
    return base64.b64decode(xx)


def dekodujNowe(t,n): #16.08.21
    #n = encode2(n)
    r=[]
    i=[]
    u=0
    x=''
    c = 256
    for o in range(c):
        i.append(o)
    o=0

    for o in range(c):
        #u = (u + i[o] + t.charCodeAt(o % t.length)) % c
        u = (u + i[o] + ord(t[o%len(t)]))%c
        r = i[o]
        i[o] = i[u]
        i[u] = r
    e = 0
    u = 0
    o =0
    for e in range(len(n)):
    #e+=1
        o = (o + e) % c
        u = (u + i[o]) % c
        r = i[o]
        i[o] = i[u]
        i[u] = r
    #x += String.fromCharCode(n.charCodeAt(e) ^ i[(i[o] + i[u]) % c])
        if sys.version_info >= (3,0,0):
            try:
                x += chr((n[e])^ i[(i[o] + i[u]) % c] )
            except:
                x += chr(ord(n[e])^ i[(i[o] + i[u]) % c] )
        else:
            x += chr(ord(n[e])^ i[(i[o] + i[u]) % c] )
    return x


def dekoduj(r,o):

    t = []
    e = []
    n = 0
    a = ""
    for f in range(256): 
        e.append(f)

    for f in range(256):

        n = (n + e[f] + ord(r[f % len(r)])) % 256
        t = e[f]
        e[f] = e[n]
        e[n] = t

    f = 0
    n = 0
    for h in range(len(o)):
        f = f + 1
        n = (n + e[f % 256]) % 256
        if not f in e:
            f = 0
            t = e[f]
            e[f] = e[n]
            e[n] = t

            a += chr(ord(o[h]) ^ e[(e[f] + e[n]) % 256])
        else:
            t = e[f]
            e[f] = e[n]
            e[n] = t
            if sys.version_info >= (3,0,0):
                a += chr((o[h]) ^ e[(e[f] + e[n]) % 256])
            else:
                a += chr(ord(o[h]) ^ e[(e[f] + e[n]) % 256])

    return a

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
    char = char.replace("&gt;",">")    
    char = char.replace("&Iacute;","Í").replace("&iacute;","í")
    char = char.replace("&icirc;","î").replace("&Icirc;","Î")
    char = char.replace('&oacute;','ó').replace('&Oacute;','Ó')
    char = char.replace('&quot;','"').replace('&amp;quot;','"')
    char = char.replace('&bdquo;','"').replace('&rdquo;','"')
    char = char.replace("&Scaron;","Š").replace("&scaron;","š")
    char = char.replace("&ndash;","-").replace("&mdash;","-")
    char = char.replace("&Auml;","Ä").replace("&auml;","ä")

    char = char.replace('&#8217;',"'")
    char = char.replace('&#8211;',"-")    
    char = char.replace('&#8230;',"...")    
    char = char.replace('&#8222;','"').replace('&#8221;','"')    
    char = char.replace('[&hellip;]',"...")
    char = char.replace('&#038;',"&")    
    char = char.replace('&#039;',"'")
    char = char.replace('&quot;','"')
    char = char.replace('&nbsp;',".").replace('&amp;','&')
    
    
    
    char = char.replace('Napisy PL',"[COLOR lightblue](napisy pl)[/COLOR]")
    char = char.replace('Lektor PL',"[COLOR lightblue](lektor pl)[/COLOR]")
    char = char.replace('Dubbing PL',"[COLOR lightblue](dubbing pl)[/COLOR]")    
    return char    

    
exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("MTI1IGQxKDIwKToKCTEwYiA1Zi4xMjEgYWIgMTM1CgoJMTJiOgoJCTFiID0gMTM1LmYwKDE0Yi4zNSgnMTQ1JyksICc0Yi5lMycpCgljYToKCQkxYiA9IGUxCgoJMzMgPSBmYig2NSgyMCkpCgkKCTFhIDMzOgoJCTE0YSA9IDMzLjExYSgnMTRhJywgZmMpCgoJCTFhIDE0YSA9PSAnNTYnOgoJCQkxMyg1LGZlKQoJCTE0OSAxNGEgPT0gJzE0MSc6CgkJCTE0MSg1KQkKCQkxNDkgMTRhID09ICc2OSc6CgkJCTEzZSg1KQoJCQkKCQkxNDkgMTRhID09ICc5YSc6CgkJCTRlKCkKCQkxNDkgMTRhID09ICc4Yyc6CgkJCTNlKCkKCQkJCgkJMTQ5ICdkZScgMWYgMTRhOgoJCQlmZiA9IDE0YS5kNSgnOicpWzFdCgkJCTFhICcxMjgnIDFmIGZmOgoJCQkJZGQ9J2U6JwoJCQkJCgkJCQljPVsnJywiZVtdPTEwMyIsImVbXT01MCIsImVbXT0xMTQiLCJlW109MTExIiwiZVtdPWFjIl0KCQkJCTk9WycxZCcsIjEwMyIsIjUwIiwiMTE0IiwiMTExIiwiYWMiXQoKCQkJCgkJCTE0OSAnMjEnIDFmIGZmOgoJCQkJZGQ9J2MzOicKCQkJCWM9WycnLCJjM1tdPTIiLCJjM1tdPTgiLCJjM1tdPWIyIiwiYzNbXT0xMSIsImMzW109YmQiLCJjM1tdPTM2IiwiYzNbXT1hNiIsImMzW109YTgiLCJjM1tdPTE4IiwiYzNbXT1iYyIsImMzW109MTA3IiwiYzNbXT0xMDgiLCJjM1tdPWFkIiwiYzNbXT03OSIsImMzW109MzQiLCJjM1tdPWEyIiwiYzNbXT1hOSIsImMzW109Y2UiLCJjM1tdPWEwIiwiYzNbXT1hMSIsImMzW109YTciLCJjM1tdPWNiIiwiYzNbXT1hNSIsImMzW109YWYiLCJjM1tdPWNkIiwiYzNbXT1hYSIsImMzW109YjQiLCJjM1tdPWIxIiwiYzNbXT1iMCIsImMzW109YmUiLCJjM1tdPWNjIiwiYzNbXT1jOSIsImMzW109Y2YiLCJjM1tdPWMwIiwiYzNbXT1iYiIsImMzW109OTQiLCJjM1tdPTEwZSJdCgkJCQk5PVsnMWQnLCIzMiBjNiIsIjMyIDk2IiwiYzciLCJiNiIsIjEwMSAxMzYiLCJkOCIsIjYxIiwiZTciLCIyZCIsImRiIiwiZjcgMTAyIiwiZTIiLCI5MyIsImViIiwiZDkiLCI5NyIsIjhhIiwiYTMiLCIxMmEgODkiLCIzZCIsImU2IGQzIiwiZDAiLCJiNSIsIjNhIiwiOWMiLCJkYSA4NSIsImQ0IiwiYWUiLCIxNDAiLCI5ZCIsImMxIiwiOTkiLCJjNCIsIjk1IiwiMTQ0IiwiNjYiLCJiMyJdCgoJCQkKCQkJCgkJCQoJCQkxNDkgJzEyNCcgMWYgZmY6CgkJCQlkZD0nODc6JwoJCQkJYz1bJycsIjliW109NzIiLCI5YltdPTY4IiwiOWJbXT03YSIsIjliW109N2IiLCI5YltdPTdjIiwiOWJbXT03ZCIsIjliW109N2UiLCI5YltdPTdmIiwiOWJbXT04MCIsIjliW109ODEiLCI5YltdPTc2IiwiOWJbXT04MiIsIjliW109NmEiLCI5YltdPTcxIiwiOWJbXT02ZCIsIjliW109ODYiLCI5YltdPTZjIiwiOWJbXT02YiIsIjliW109NzAiLCI5YltdPTZmIiwiOWJbXT02ZSIsIjliW109NDkiLCI5YltdPTUxIiwiOWJbXT00OCIsIjliW109NDIiLCI5YltdPTRjIiwiOWJbXT01YiIsIjliW109NTkiLCI5YltdPTU0IiwiOWJbXT00ZCIsIjliW109NDYiLCI5YltdPTVjIl0KCQkJCTk9WycxZCcsIjcyIiwiNjgiLCI3YSIsIjdiIiwiN2MiLCI3ZCIsIjdlIiwiN2YiLCI4MCIsIjgxIiwiNzYiLCI4MiIsIjZhIiwiNzEiLCI2ZCIsIjg2IiwiNmMiLCI2YiIsIjcwIiwiNmYiLCI2ZSIsIjQ5IiwiNTEiLCI0OCIsIjQyIiwiNGMiLCI1YiIsIjU5IiwiNTQiLCI0ZCIsIjQ2IiwiNWMiXQoKCQkJMTQ5ICcxMjYnIDFmIGZmOgoJCQkJZGQ9JzM6JwoJCQkJCgkJCQljPVsnNWE9MTE5JywiM1tdPTI1IiwiM1tdPTE3IiwiM1tdPTEwIiwiM1tdPTExOCIsIjNbXT0xMDAiLCIzW109MTQiLCIzW109MjYiLCIzW109MTMxIiwiM1tdPTEiLCIzW109NDMiLCIzW109MzEiLCIzW109MTE3IiwiM1tdPTQ3IiwiM1tdPTc0IiwiM1tdPTExNiIsIjNbXT0xMjkiLCIzW109NjQiLCIzW109NCIsIjNbXT0yMyIsIjNbXT0xNSIsIjNbXT00NCIsIjNbXT03IiwiM1tdPTEzOSIsIjNbXT01OCIsIjNbXT0yOCJdCgkJCQk5PVsnMWQnLCJiNyIsIjYwIiwiNWQiLCI1ZSIsIjhlIiwiOWYiLCJlYSIsIjQwIiwiZTUiLCJjOCIsIjhkIiwiMTEzLTc3IiwiOTgiLCI5ZSIsImJhIiwiZWMiLCI5MSIsIjhmLTEwZCIsIjkwIiwiMTI3LTE0MyIsImVkIiwiMTNmIiwiMTBkIDc3IiwiMTFkIiwiOGIiXQoKCQkJMTQ5ICdkJyAxZiBmZjoKCQkJCWRkPSdkICgxMzQpOicKCQkJCWM9WyJkPTEyIiwiZD02MjoyYSIsImQ9ZTQ6MmEiLCJkPWY0OjExZiIsImQ9ODg6MmEiLCJkPTg3OjJhIl0KCQkJCTk9WyIxMiIsIjgzIGYxIiwiZjkgOTIiLCIxMGYiLCI4OCIsIjliIDEyMCJdCgoJCQkxNDkgJ2I5JyAxZiBmZjoKCQkJCWRkPSc2MzonCgkJCQljPVsiIiwgIjI3W109MSIsIjI3W109MCJdCgkJCQk5PVsiMWQiLCIxM2QiLCIxMTUiXQoJCQkJCgkJCTFhICdkJyAxZiBmZiAxMzMgJ2I5JyAxZiBmZjoKCQkJCWIgPSBmLjFlKCkuYzUoJzM4ICcrZGQsOSkKCQkJMTM3OgoJCQkKCQkJCWIgPSBmLjFlKCkuM2YoJzM4ICcrZGQsOSkKCQkJMWEgYjojPD0tMTogMjIoKSMxMjI9MAoJCQkKCQkJCTFhIDQ1KGIsZmQpOgoJCQkJCQoJCQkJCTFhIDAgMWYgYjogYj1bMF0KCQkJCQkxMWMgPSAnJicrJyUxMjInJSgnJicuNzgoIFsgY1sxMTJdIGJmIDExMiAxZiBiXSkpIDFhIGJbMF0hPTAgMTM3ICcnCgkJCQkJMTFiID0gJywgJy43OCggWyA5WzExMl0gYmYgMTEyIDFmIGJdKQoJCQkJMTM3OgoJCQkJCWIgPSBiIDFhIGI+LTEgMTM3IDIyKCkKCQkJCQkxMWMgPSAnJicrJyUxMjInJWNbYl0gMWEgY1tiXSAxMzcgJycKCQkJCQkxMWIgPSA5W2JdCgkJCQkKCQkJCTE0Yi4xNDcoZmYrJzE0OCcsMTFjKQoJCQkJMTRiLjE0NyhmZisnMTRjJywxMWIpCgkJCQkKCQkJCTJlID0gMTRiLjYoJ2E0JykKCQkJCQoJCQkJNTUgPSAxNGIuNignZjUnKQoJCQkJCgkJCQkzMCA9IDE0Yi42KCdjMicpCgkJCQkKCQkJCTEyZCA9IDE0Yi42KCdlMCcpCgkJCQkKCQkJCTU3ID0gMTRiLjYoJ2VmJykKCQkJCQoJCQkJMTFlID0gMTRiLjYoJ2QyJykKCQkJCQoJCQkJNTIgPSAxNGIuNignZGMnKQoJCQkJCgkJCQkzNyA9IDE0Yi42KCdiOCcpCgkJCQkKCQkJCTRmID0gMTRiLjYoJ2Y2JykKCQkJCQoJCQkJNDEgPSAxNGIuNignZDYnKQoJCQkJCgkJCQkxNDI9NTUrZjMrNTcrMmUrMTJkKzMwCgkJCQkxMmU9NTIrZTkrNDErMTFlKzRmKzM3CgkJCQkKCQkJCTE0Yi4xNDcoJ2RmJywxNDIpCgkJCQkxNGIuMTQ3KCdkNycsMTJlKQoJCQkJNzMuMTNjKCcyNC4yYycpCgkJCTEzNzoKCQkJCTIyKCkKCQkxNDkgMTRhID09JzRhJzoKCQkJM2IoNSkKCQkKCQkxNDkgMTRhID09JzNjJzoKCQkJMTMwKDUpCgoJCTE0OSAxNGEgPT0gJzEyMyc6CgkJCTEyMyg1KQoJCQoJCTE0OSAxNGEgPT0gIjg0IjoKCgkJCTE0Yi4xNDcoNSsnZjInLCcxMicpCgkJCTE0Yi4xNDcoNSsnZWUnLCcmZD0xMicpCgkJCQoJCQkxNGIuMTQ3KDUrJzEwNicsJzFkJykKCQkJMTRiLjE0Nyg1KycxMTAnLCcnKQoJCQkKCQkJMTRiLjE0Nyg1KycxMDQnLCcxZCcpCgkJCTE0Yi4xNDcoNSsnZTgnLCcnKQoJCQkKCQkJMTRiLjE0Nyg1KycxMDUnLCcxZCcpCgkJCTE0Yi4xNDcoNSsnZmEnLCcnKQoJCQkKCQkJMTRiLjE0Nyg1KycxMGMnLCcxZCcpCgkJCTE0Yi4xNDcoNSsnMTBhJywnJykKCQkJCgkJCQoJCQkxNGIuMTQ3KDUrJ2Y4JywnJmQ9MTInKQoJCQk3My4xM2MoIjI0LjJjIikgCgkJCQoJCTE0OSAxNGE9PScxM2EnOgoJCQlhID0gZi4xZSgpLjUzKDEyZicyZi4uLicsIDc1PWYuMTkpCgkJCTFhIGE6ICAKCQkJCTEzYiA9IDI5KGEpCgkJCQkxMmMgPSAnMTQ2Oi8vMWMuNjcvMTNhPzE2PScrYS4xMzgoJyAnLCcrJykrJyYxMzI9JysxM2IKCQkJCTFhIDFiOgoJCQkJCTEyYyA9ICcxNDY6Ly8xYy42Ny8xM2E/MTY9JythLjEzOCgnICcsJysnKSsnJjEzMj0nKzEzYi4xMzgoJysnLCAnJTJiJykKCQkJCTEzKDEyYywnMScpCgoJCQkxMzc6CgkJCQkyMigpCgkJMTQ5IDE0YT09JzM5JzoKCQkJYSA9IGYuMWUoKS41MygxMmYnMmYuLi4nLCA3NT1mLjE5KQoJCQkxYSBhOiAgCgkJCQkxM2IgPSAyOShhKQoJCQkJMTJjID0gJzE0NjovLzFjLjY3LzEzYT8xNj0nK2EuMTM4KCcgJywnKycpKycmMTMyPScrMTNiCgkJCQkxYSAxYjoKCQkJCQkxMmMgPSAnMTQ2Oi8vMWMuNjcvMTNhPzE2PScrYS4xMzgoJyAnLCcrJykrJyYxMzI9JysxM2IuMTM4KCcrJywgJyUyYicpCgkJCQkxMygxMmMsJzEnKQoKCQkJMTM3OgoJCQkJMjIoKQoJMTM3OgoJCTEwOSgp")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|2|genre|4|exlink|getSetting|7|8|label|query|sel|value|sort|quality|xbmcgui|10|11|default|ListMovies|14|15|keyword|17|18|INPUT_ALPHANUM|if|REPO_OK|fmovies|all|Dialog|in|paramstring|kraj|quit|23|Container|25|26|subtitle|28|getVerid|desc|2B|Refresh|International|fsortv|Search|fkrajv|31|United|args|34|getAddonInfo|36|skrajv|Select|gkobuplayer|Switzerland|ListSeasons|getEpisodes|Netherlands|menuTVshows|multiselect|documentary|swerv|1970s|43|44|isinstance|1910s|47|1980s|2000s|getseasons|repository|1960s|1920s|menuMovies|srokv|HDRip|1990s|skatv|input|1930s|fkatv|listmovies|fwerv|58|1940s|genre_mode|1950s|1900s|animation|biography|resources|adventure|Australia|post_date|subtitles|64|parse_qsl|Thailand|to|2020|playlink|2009|2004|2005|2007|2001|2002|2003|2008|2021|xbmc|74|type|2011|show|join|79|2019|2018|2017|2016|2015|2014|2013|2012|2010|recently|resetfil|Republic|2006|year|imdb|Zealand|Denmark|western|menutvs|fantasy|costume|reality|romance|mystery|watched|Ireland|94|Romania|Kingdom|Belgium|history|Finland|menumov|release|Austria|Hungary|horror|comedy|181847|181848|181849|Sweden|fsortV|181852|181851|181850|181857|181855|181859|import|CAM|181862|Russia|181869|181863|181860|181861|Taiwan|181867|Mexico|France|action|skrajV|nap|kungfu|181878|181871|181873|181876|for|181895|Poland|fkrajV|country|Israel|select|States|Canada|family|181877|except|181901|181880|181882|181883|181887|Norway|router|ssortV|Africa|Brazil|split|swerV|sdata|Japan|India|Czech|Spain|skatV|dd|filtr|fdata|frokV|False|China|gkobu|views|drama|South|Italy|krajV|snapv|crime|Korea|music|sport|sortV|fwerV|check|added|sortN|fnapv|title|fkatV|srokV|Hong|data|most|rokV|dict|None|list|page|ff|1693|West|Kong|HD|krajN|rokN|katN|2630|108|home|napV|from|napN|tv|1434|name|katV|TS|i|game|SD|off|248|212|215|and|get|n|v|war|ssortv|asc|date|lib|s|getLinksSerial|rok|def|kat|sci|wer|199|New|try|url|frokv|datas|u|ListEpisodes|131|vrf|or|by|recontrol|Germany|else|replace|139|search|verid|executebuiltin|on|PlayLink|thriller|Argentina|getLinks|dataf|fi|Luxembourg|id|https|setSetting|V|elif|mode|addon|N".split("|")))

if __name__ == '__main__':
    router(sys.argv[2][1:])
