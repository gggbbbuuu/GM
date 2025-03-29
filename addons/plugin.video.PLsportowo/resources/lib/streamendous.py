# -*- coding: UTF-8 -*-
import sys,os,urllib3
import threading
import six
from six.moves import urllib_error, urllib_request, urllib_parse, http_cookiejar

import re
import time
import requests
if six.PY2:
    from resources.lib.cmf2 import parseDOM
else:
    from resources.lib.cmf3 import parseDOM
#import web_pdb
import mydecode
import base64
try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except:
    pass
import xbmc,xbmcgui,xbmcaddon,xbmcvfs
import cfdeco7
addonInfo = xbmcaddon.Addon().getAddonInfo

try:
    dataPath		= xbmcvfs.translatePath(addonInfo('profile'))
except:
    dataPath	   = xbmc.translatePath(addonInfo('profile')).decode('utf-8')

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
import ssl
# from urllib3.util.ssl_ import DEFAULT_CIPHERS
DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
    ]
)

UA='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'

#CIPHERS = ":".join(["DEFAULT","!DHE","!SHA1","!SHA256","!SHA384",])

DEFAULT_CIPHERS += ":!ECDHE+SHA:!AES128-SHA:!AESCCM:!DHE:!ARIA"

CIPHERS = DEFAULT_CIPHERS

class ZoomTVAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        context.set_ecdh_curve("prime256v1")
        context.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1)
        kwargs["ssl_context"] = context
        return super(ZoomTVAdapter, self).init_poolmanager(*args, **kwargs)


    
    
    
    
    
    
    
    
    
    
vleagueFile = os.path.join(dataPath, 'vleague.txt')

scraper = cfdeco7.create_scraper()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
BASEURL='http://www.streamendous.com'
BASEURL2='https://cricfree.stream/home'
BASEURL3='http://strims.top/'
BASEURL4='https://www.soccerstreams100.com/'
BASEURL5='https://livesport.ws/en/'
BASEURL6='https://www.vipleague.lc'
BASEURL7='http://liveonscore.tv'
BASEURL8='http://crackstreams.is'
sess = requests.Session()
sess365 = requests.Session()
#UA='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'

UA = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'


UAbot='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
addon = xbmcaddon.Addon(id='plugin.video.PLsportowo')
my_addon = addon
def getUrl(url,ref=BASEURL2,json=False):
    headers = {'User-Agent': UA,'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8','Referer': ref,}
    html=requests.get(url,headers=headers,verify=False,timeout=30)#.content
    if html.status_code == 503:
        html=scraper.get(url).text
    else:
        if json:
            html=html.json()
        else:
            html=html.text

            if html.find('by DDoS-GUARD')>0:   
                headers = {'User-Agent': UAbot,'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8','Referer': ref,'Cookie':unbkuk}
                html=requests.get(url,headers=headers,verify=False,timeout=30).text 
              #  if six.PY3:
               #	 try:
               #		 html = html.decode(encoding='utf-8', errors='strict')
               #	 except:
               #		 pass
                #or creating a cookie “_ddgu” with random characters
    return html
    
def getUrl2(url,ref=BASEURL2):
    headers = {'User-Agent': UA,'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8','Referer': ref,}
    html=requests.get(url,headers=headers,verify=False,timeout=30)
    if html.status_code == 503:
        html=scraper.get(url)#.text
    last=html.url
    html=html.content
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    return html,last
 




def ListROJA(url) :
    out =[]

    hd = {'User-Agent': UA}

    html=getUrl(url,url)

    html = re.sub('(\\xda)','U',html)
    html = re.sub('(\\xfa)','u',html).replace("\'",'"')

    links = parseDOM(html,'span',attrs = {'class':'\d+'})
    for subset in links:

        czas = parseDOM(subset,'span',attrs = {'class':'t'})[0]

        try:
            dysc = parseDOM(subset,'span',attrs = {'class':'en'})[0]
        except:
            dysc ='other'

        tyt = parseDOM(subset,'span',attrs = {'itemprop':'name'})[0]
        event = re.findall('>([^<]+)<b>',subset,re.DOTALL)[0]
        plot = event+' - ' +tyt
        fg = dysc 
        tyt = '[B][COLOR khaki]%s : [/COLOR][/B][COLOR gold][B]%s[/B][/COLOR]'%(czas,tyt) #czas+ ' - ' +tyt
        
        subs = parseDOM(subset,'tr')[1:]
        dd=[]
       # 
        for sb in subs:
            sb = re.sub('(\\n)','',sb)
            ab = re.findall('>([^<]+)<', sb, re.DOTALL)#[0]
            if ab[0] == 'P2P':
                continue
            else:

                href = parseDOM(sb, 'a', ret='href')[0]

                tit = ab[-7]+' - ' + ab[-5]+' - '+ ab[-3]
                
                
                dd.append({'href':href,'title':tit})

        ff='roja:'+urllib_parse.quote(str(dd))
        out.append({'title':tyt,'href':ff,'image':'','code':fg,'plot':plot})
    
    return out

def getLiveOnScoreStreams(url,srch=''):
    out =[]
    npage = False
    hd = {'User-Agent': UA}

    if srch:
        url = 'http://liveonscore.tv/?s='+srch
        html=getUrl(url,BASEURL7)
    else:
        html=getUrl(url,url)

    result  = parseDOM(html,'ul',attrs = {'class':'competitions'})[0]
    npage = re.findall('page-numbers" href="([^"]+)">next',html.lower(),re.DOTALL)
    npage = npage[0] if npage else False

    links  = parseDOM(result,'div',attrs = {'class':'competition'})
    for link in links:
        href = parseDOM(link,'a',ret='href')[0]
        teams = re.findall('<span class="name">(.+?)<',link,re.DOTALL)
        dt = re.findall('status">(.+?)<',link,re.DOTALL)
        dt = ' ('+dt[0]+')' if dt else ''
        tyt = ' - '.join([x.strip() for x in teams]) if teams else ''
        tyt = tyt.replace('&amp;','&')
        plot = tyt+'[CR]'+dt+'[/CR]'
        out.append({'title':tyt,'href':str(href),'image':'','code':dt,'plot':plot})

    return out,npage
def getplayLiveOnScore(url):
    hd = {'User-Agent': UA}

    html=getUrl(url,url)

    zdj = re.findall("poster: \\'(.+?)\\'",html,re.DOTALL)
    zdj = zdj[0] if zdj else ''

    stream_url =False
    try:
        gethls = re.findall('gethlsUrl\((.+?)\)',html,re.DOTALL)[1]
    except:
        gethls = False
    if gethls:
        regex, serverid, cid = gethls.split(',')
        urlid = re.findall("""var %s\s*=\s*['"](.+?)['"]"""%(regex),html,re.DOTALL)[0]
        params = (
            ('idgstream', urlid),
            ('serverid', serverid),
            ('cid', cid),
        )
        hd.update({'Referer': url})
        response = requests.get('http://liveonscore.tv/gethls.php', headers=hd, params=params)
        data= response.json()
        
        src = data.get("rawUrl",'')
        if src:
            stream_url = src+'|User-Agent='+UA+'&Referer='+url#,False
    return stream_url,zdj
    
    
def ListTVCOM1(url):
    out=[]
    html=getUrl(url)
    
    menus = parseDOM(html,'li',attrs = {'class':'dropdown'}) #<li class="dropdown">
    for menu in menus:
        try:
            href1 = parseDOM(menu,'a',ret='data-href')[0] #parseDOM(html,'a',attrs = {'class':'dropdown'})
            href1='https://www.tvcom.pl'+href1 if href1.startswith('/') else href1
            tyt1 = re.findall('>([^<]+)<span class',menu)[0]
        except:
            pass
        out.append({'href':href1,'title':'[B][COLOR gold]%s[/COLOR][/B]'%tyt1}) #'[COLOR lime]► [/COLOR] [B][COLOR gold] Link 2 - %s[/COLOR][/B]'
    return out
    
def ListTVCOM2(url):
    out=[]
    html=getUrl(url)
    hreftit=re.findall('data-href="(.+?)" class=".+?" data-toggle=".+?" role="button" aria-haspopup=".+?" aria-expanded=".+?">(.+?) <span',html)
    for href,tyt1 in hreftit:
        try:
            href1='https://www.tvcom.pl'+href if href.startswith('/') else href
        except:
            pass

        out.append({'href':href1,'title':'[B][COLOR gold]%s[/COLOR][/B]'%tyt1})
    return out
def ListTVCOMdzis(url):
    out=[]
    html=getUrl(url)
    result = parseDOM(html,'div',attrs = {'id':'calendar-owl'})[0]#<div id="calendar-owl" class="owl-carousel">
    dzis = parseDOM(result,'div',attrs = {'class':"item today"})

    if dzis:
        dat=re.findall('<a href="\/Den\/\?d=(.+?)">DZI',dzis[0])#[0]
        if dat:
            nagr=re.findall('"badge primary">(.+?)<',dzis[0])
            live=re.findall('"badge secondary">(.+?)<',dzis[0])
            wkrot=re.findall('"badge inverse">(.+?)<',dzis[0])
            nagr=nagr[0] if nagr else '0'
            live=live[0] if live else '0'
            wkrot=wkrot[0] if wkrot else '0'
            dod=' - (%s, %s, %s)'%(nagr,live,wkrot)
            out.append({'href':dat[0],'title':'DZIŚ'+dod})
    days = parseDOM(result,'div',attrs = {'class':'item'})
    for day in days:
        hrefday=re.findall('href="\/Den\/\?d=(.+?)">(.+?)<',day)[0]
        nagr=re.findall('"badge primary">(.+?)<',day)
        live=re.findall('"badge secondary">(.+?)<',day)
        wkrot=re.findall('"badge inverse">(.+?)<',day)
        nagr=nagr[0] if nagr else '0'
        live=live[0] if live else '0'
        wkrot=wkrot[0] if wkrot else '0'
        dod=' - (%s, %s, %s)'%(nagr,live,wkrot)

        out.append({'href':hrefday[0],'title':'%s%s'%(hrefday[1],dod)})
    return out

def ListTVCOMlinks(day):
    out=[]
    url='https://json.2017.tvcom.cz/Json/Web2017/BottomCalendarPL.aspx?d='+day
    response=getUrl(url,json=True)
    data = response['Date']
    dane = response['Data']
    for dan in dane:
        tyt=dan['Name']
        href=dan['Url']
        czas=dan['Time']
        dzien=dan['Date']
        dysc=dan['Sport']
        typ=dan['SportVideoType']
        cod=''
        if 'live' in typ:
            cod='Live'
        elif 'wkrótce' in typ:
            cod='nie rozpoczęte'
        href='https://www.tvcom.pl'+href if href.startswith('/') else href
        cod2 = '%s, %s' %(dysc,cod)
        tytul='%s %s'%(czas,tyt)
        plot='%s[CR]%s[CR]%s'%(dysc,czas,tyt)
        out.append({'href':href,'title':tytul,'code':cod2,'plot':plot})
    return out
def getTVCOMstream(url):
    stream_url=''
    html=getUrl(url)

    hls=re.findall('hls:\s*{(.+?)}',html)
    mpd=re.findall('dash:\s*{(.+?)}',html)
    if hls:
        hls=hls[0].replace("\'",'"')
        stream_url=re.findall('src:\s*"(.+?)"',hls)[0]
    return stream_url

    
def ListTVCOMlinksDysc(url):
    out=[]
    response=getUrl(url,json=True)

    dane = response['Data']
    for dan in dane:
        tyt=dan['Name']
        href=dan['Url']
        czas=dan['Time']
        dzien=dan['Date']

        typ=dan['SportVideoType']
        cod=''
        if 'live' in typ:
            cod='Live'
        elif 'wkrótce' in typ:
            cod='nie rozpoczęte'
        href='https://www.tvcom.pl'+href if href.startswith('/') else href
        tytul='(%s %s) %s'%(dzien,czas,tyt)
        out.append({'href':href,'title':tytul})
    return out[::-1]	
    
def ListTVCOMlinksDysc2(html):
    out=[]
    videos  = parseDOM(html,'div',attrs = {'id':"video-selector"})[0]
    vids  = parseDOM(videos,'div',attrs = {'class':"media"})
    for vid in vids:
        try:
            href,tyt=re.findall('href="(.+?)">(.+?)<\/a>',vid)[0]
        except:
            tyt=re.findall('>(.+?)<\/h4>',vid)[0]
            href=re.findall('href="(.+?)"',vid)[0]
        href='https://www.tvcom.pl'+href if href.startswith('/') else href
        imag=re.findall('src="(.+?)"',vid)[0]
        dat=re.findall('<h5>(.+?)<\/h5>',vid)[0]
        tytul='(%s) %s'%(dat,tyt)
        out.append({'href':href,'title':tytul,'imag':imag})
    return out
def ListUnblocked(url):
    out=[]
    html=getUrl(url)
    hrefname=re.findall('col-sm-3.+?"><a class=".+?" href=(.+?) target=_blank role=button>(.+?)<',html,re.DOTALL)
    for href,title in hrefname:
        out.append({'href':href,'title':'[B][COLOR gold]%s[/COLOR][/B]'%title}) #'[COLOR lime]► [/COLOR] [B][COLOR gold] Link 2 - %s[/COLOR][/B]'
    return out	
    
    
    
def getScheduleCR():
    out=[]
    html=getUrl(BASEURL2)
    divs = parseDOM(html,'div',attrs = {'class':'panel_mid_body'})
    for div in divs:
        day = parseDOM(div,'h2')#[0]
        if day:
            day='kiedy|%s'%day[0]
            out.append({'href':day})
        trs = parseDOM(div,'tr')#[0]
        for tr in trs:
            online= '[COLOR lime]► [/COLOR]' if tr.find('images/live.gif')>0 else '[COLOR orangered]■ [/COLOR]'
            if '>VS</td>' in tr:
                czas,dysc,team1,team2,href=re.findall('>(\d+:\d+)</td>.+?<span title="(.+?)".+?href=.+?>(.+?)<.+?>VS<.+?a href.+?>(.+?)</a>.+?<a class="watch_btn" href="(.+?)"',tr,re.DOTALL)[0]
                mecz='%s vs %s'%(team1,team2)
                
                czas=czas.split(':')
                hrs=int(czas[0])+2
                if hrs==24:
                    hrs='00'
                mins=czas[1]
                czas='%s:%s'%(str(hrs),mins)
            else:
                czas,dysc,team1,href=re.findall('>(\d+:\d+)</td>.+?<span title="(.+?)".+?href=.+?>(.+?)<.+?<a class="watch_btn" href="(.+?)"',tr,re.DOTALL)[0]
                mecz=team1
            title = '[B][COLOR khaki]%s%s : [/COLOR][/B][COLOR gold][B]%s[/B][/COLOR]'%(online,czas,mecz)
            out.append({'title':title,'href':href,'code':dysc})
    return out




    
def getChannelsCR():
    out=[]
    html=getUrl(BASEURL2)
    result = parseDOM(html,'ul',attrs = {'class':"nav-sidebar"})[0]#<div class="arrowgreen">
    channels = parseDOM(result,'li')
    for channel in channels:
        if '<ul class="nav-submenu">' in channel:
            continue
        try:
            href = parseDOM(channel,'a',ret='href')[0]
            title = parseDOM(channel,'a',ret='title')[0]
            out.append({'href':href,'title':'[COLOR lime]► [/COLOR] [B][COLOR gold]'+title+'[/COLOR][/B]'})
        except:
            pass
    return out	
    
def getSstreamsStreams(url):
    out=[]
    html=getUrl(url)
    try:
        result = parseDOM(html,'tbody')[0]
        if 'acestream:' in result.lower():
            result = parseDOM(html,'tbody')[1]
        items = parseDOM(result,'tr')
        for item in items:
            dane = parseDOM(item,'td')
            lang=dane[4]
            href = parseDOM(item,'a',ret='href')[1]
            tyt = parseDOM(item,'a')[1]
            tyt='%s [B][%s][/B]'%(tyt,lang)
            out.append({'href':href,'title':tyt})
    except:
        pass
    return out

    
def getF1stream(url):
    out=[]
    html=getUrl(url)
    tithref=re.findall("""<h3>([^>]+)<.+?['"](http.+?)['"]""",html,re.DOTALL)

    if not tithref:
        tithref=re.findall("""<h3>([^>]+)<.+?<source src=['"]([^'"]+)['"]""",html,re.DOTALL)
    for tyt,href in tithref:
        out.append({'href':href,'title':tyt})
    return out

def KSWchannels():
    out=[]
    html=getUrl(BASEURL3+'live/fight.php')
    hreftit=re.findall("""a href=['"](.+?)['"]>(.+?)<\/a><br>""",html)
    for href,tyt in hreftit:
        href = 'http://strims.top'+href
        out.append({'href':href,'title':'[COLOR lime]► [/COLOR] [B][COLOR gold]'+tyt+'[/COLOR][/B]'})
    return out	
    

def getSWstreams(url):
    out=[]
    
    html,basurl=getUrl2(url)
   
   # if six.PY3:
   #	 html = html.decode(encoding='utf-8', errors='strict')
    try:
        try:
            result = parseDOM(html,'font size=3.+?')[0].replace('</a><br><br>','</a>|<br><br>')
        except:
            result = parseDOM(html,'font',attrs = {'size':'3'})[0].replace('</a><br><br>','</a>|<br><br>')

        if '<center><b>' in result or 'zatrzyma' in result or 'prawym doln' in result.lower() or 'lewym dol' in result.lower() or 'playerz' in result.lower():
            result = parseDOM(html,'font',attrs = {'size':'3'})[1]
            
        result=result.replace('\n','').replace('<b>','').replace('</b>','')

        try:
            result2=result.replace('\n','').replace('</a> |',' |').replace('<b>','').replace('</b>','')

            xx=re.findall('(\w+.*?: <a class.+?</a>)',result2,re.DOTALL)
            
            
            for x in xx:
                x=x.replace('br>','')
                lang=re.findall('^(\w+)',x,re.DOTALL)[0]
                
                hreftyt=re.findall('href="(.+?)".+?>(Source \d.+?)<',x)
                if lang and not hreftyt:
                    x=x.replace('</a>','|')
                    hreftyt=re.findall('href="(.+?)".+?>(.+?)\|',x)
                for href,tyt in hreftyt:
                    tyt = tyt.replace('|','')
                    href=basurl+href
                    tyt='%s - [B]%s[/B]'%(lang,tyt)
                    out.append({'href':href,'title':tyt})

        except:
            results=result.split('|')
            
            for result in results:
                href,name=re.findall('href="(.+?)".+?>(.+?)<\/a>',result)[0]
                if '?' in url:
                    url=url.split('?')[0]
                    href=url.replace(url.split('?')[-1],href.split('?')[-1])
                else:
                    href=url+href
                
                out.append({'href':href,'title':name.replace('<b>','').replace('</b>','')})		
        
    except:
        tvp = re.findall('iframe src="(.+?)"',html)

        tvp = tvp[0] if tvp else ''
        if 'sport.tvp' in tvp:
            html,basurl=getUrl2(tvp)
            
            sr = re.findall("""\{src:['"](.+?)['"]""",html)[0]
            
            out.append({'href':sr,'title':'tvp'})	
        pass
    if not out:
        try:
            #print('GET_STR')
            results=result.split('|')
            #print(results)
            if not 'poczekaj' in results[0].lower():# and not 'poczekaj' in results[1].lower():
                #print ''
                for result in results:
                    href,name=re.findall('href="(.+?)".+?>([^>]+?)<\/a>',result)[0]#TO DO: zapobiec wycinaniu linków nieotoczonych <b>....</b>
                    #print(href)
                    #print(name)
                    if '?' in url:
                        #url=url.split('?')[0]
                        href=url.replace(url.split('?')[-1],href.split('?')[-1])
                    else:
                        href=url+href
                    out.append({'href':href,'title':name.replace('<b>','').replace('</b>','')})
                    print(out)
            else:
                pass
        except:
            pass
    
    if not out:#brak źródeł, jest iframe
        try:
            url_tr=parseDOM(html,'iframe',ret='src')
            if len(url_tr)>0:
                if 'chat' not in url_tr[0]:
                    out.append({'href':url_tr[0],'title':'transmisja'})
            return out
        except:
            pass
    #print('OUT')
    #print(out)
    return out
    
    
def getSWstreamsx(url):
    out=[]
    html=getUrl(url)
    
    try:
        result = parseDOM(html,'font',attrs = {'size':'3'})[0]
        if '<center><b>' in result:
            result = parseDOM(html,'font',attrs = {'size':'3'})[1]
        t = re.sub('--.*?>', '', result)
        result= t.replace('\r\n\r\n','')	
        try:
            xx=re.findall('(\w+)\: <a(.+?)adsbygoogle',result,re.DOTALL)
            b=xx[0]
            for x in xx:
                tit='%s'%x[0]
                aa=re.findall('href="(.+?)".+?>(.+?)</a>',x[1],re.DOTALL)
                for a in aa:
                    if 'vjs' in a[0]:
                        continue				
                    href= a[0]
                    tytul= a[1].replace('<b>','').replace('</b>','')
                    tyt='%s - [B]%s[/B]'%(tytul,tit)
                    href=url+href
                    out.append({'href':href,'title':tyt})

        except:
            results=result.split('|')
            for result in results:
                href,name=re.findall('href="(.+?)".+?>(.+?)<\/a>',result)[0]
                href=url+href
                out.append({'href':href,'title':name.replace('<b>','').replace('</b>','')})		
        
    except:
        pass
    return out
def getCRlink(url):

    out=[]
    html=getUrl(url)
    result = parseDOM(html,'div',attrs = {'class':'video_btn'})#[0]
    if result:
        hrefhost=re.findall('link="(.+?)">(.+?)<',result[0],re.DOTALL)
        for href,host in hrefhost:
            out.append({'href':href,'title':host})
    return out
    
def unescapeHtml(hh):
    hh=re.findall('(eval\(unescape.+?</script>)',hh,re.DOTALL)[0]
    vales=re.findall("""['"](.+?)['"]""",hh,re.DOTALL)#[0]
    vale=vales[0] if vales else ''
    a=urllib_parse.unquote(vale)  
    if 'm3u8' in a or 'src="http' in a:
        return a
    else:
        try:
            spl=re.findall("""split\(['"](.+?)['"]\)""",a,re.DOTALL)[0]
            pl=re.findall("""\+\s*['"](.+?)['"]\);""",a,re.DOTALL)[0]
            odj=re.findall('\(i\)\)(.+?)\);',a,re.DOTALL)[0]	
            funkcja='chr((int(k[i%len(k)])^ord(s[i]))'+odj+')'
            tmp=vales[2]
            tmp = tmp.split(spl)
            s = urllib_parse.unquote(tmp[0]);
            k = urllib_parse.unquote(tmp[1] + pl);
            r=''
            for i in range(0, len(s)):
                r+=eval(funkcja)
            return r
        except:
            return a

#def getsport365stream(url,ref):
#	headers = {
#		#'Host': 'www.realstream.space',
#		'User-Agent': UA,
#		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
#		'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
#		'DNT': '1',
#	#	'Referer': 'http://strims.top/',
#		'Upgrade-Insecure-Requests': '1',
#	}
#	html = sess365.get(url, headers=headers, verify=False).content
#
#	iframe = parseDOM(html,'iframe',ret='src')#[0]
#	if not iframe and 'alternate" hreflang=' in html:
#			iframe = re.findall('rel="alternate" hreflang="x\-default" href="(.+?)"',html)#[0]
#	iframe = iframe[0]	
#	sess365.headers.update({'Referer': url})
#	html = sess365.get(iframe, verify=False).content
#
#	#html = html.replace("\'",'"')
#	
#	post = {k: v for k, v in re.findall('<input type="hidden" name="([^"]+)" value="([^"]+)">', html)}
#	action = re.findall("action', '([^']+)", html)
##	payload = urllib.urlencode(post)
#	
#	
#	html = sess365.post(action[0], data=post, verify=False).content
#	sc=''.join(['%s=%s;'%(c.name, c.value) for c in sess365.cookies])
#	#data2, c = getUrlc(action[0], payload, header=header, usecookies=True)
#	hdrs= 'User-Agent=%s&Referer=%s&Cookie=%s' % (urllib.quote(UA), urllib.quote('http://h5.adshell.net/peer5'), urllib.quote(sc))
#	data2 = html
#	data = re.findall("function\(\)\s*{\s*[a-z0-9]{43}\(.*?,.*?,\s*'([^']+)'", data2)[0]
#	import getkey as GK
#	#web_pdb.set_trace()
#	hset,xset, stri, stri2 = GK.getkey()
#	my_addon.setSetting('hset',hset)
#	my_addon.setSetting('xset',xset)
#	my_addon.setSetting('mainkey',stri)
#	my_addon.setSetting('ivkey',stri2)
#	
#	#web_pdb.set_trace()
#	import sport365 as sp365
#	url=sp365.geturlnew(stri,data,data2)
#	#web_pdb.set_trace()
#	return url+'|'+hdrs
#	#ab=html
    
    
def checksp365(url):

    ab=False
    lista = [".6aght43s.realstream.cc", ".adshell.net", ".castasap.pw", ".fastflash.pw", ".flashcast.pw", ".flashlive.pw", ".live365.club", ".live365.world", ".livesportstream.tv", ".livesportstreams.tv", ".realstream.space", ".s365.live", ".sport247.live", ".sport365.bz", ".sport365.club", ".sport365.link", ".sport365.live", ".sport365.pro", ".sport365.sx", ".sport365.world", ".sportstream.live", ".sportstreams.live", ".streamshell.net"]
    for x in lista:
        if x in url:
            ab = True
            break
        else:
            continue
    return ab		
        
def resolvingCR(url,ref):
    vido_url=''
    try:
        html=getUrl(url,ref)
    except:
        html=''
    if 'rojadirecta' in url and 'goto/' in url:

        url = re.findall('a href="([^"]+)"',html,re.DOTALL)[0]
        ref = 'http://www.rojadirecta.me/en?p4'
        html=getUrl(url,ref)
        
    if 'castfree.me' in url:#
        html=html.replace('\n','')
        url_stream=re.compile('return\(\[(.*)\]\.', re.DOTALL).findall(html)[0]
        url_stream=url_stream.replace('"','').replace('"','').replace('\\','').replace(',','')
        vido_url=url_stream+'|User-Agent='+UA+'&Referer='+url
    
    if (not 'manifest.m3u8' in url) and (not'castfree.me' in url):
        iframes= parseDOM(html,'iframe',ret='src')#[0]
        dal=''
        #print('IFRAMES')
        #print(iframes)
        for iframe in iframes:
            if 'unblocked.is' in iframe:
                if 'nullrefer.com' in iframe or 'href.li/' in iframe:
                    iframe = urllib_parse.urlparse(iframe).query
                html2=getUrl(iframe,url)	
                stream=getUnblocked(html2)
                return stream
            elif 'nullrefer.com' in iframe or 'href.li/' in iframe:
                iframe = urllib_parse.urlparse(iframe).query

                html=getUrl(iframe,url)	
                url=iframe
                break

            elif 'sportsbay.org' in iframe:
                if iframe.startswith('//'):
    
                    iframe = 'https:'+iframe
                html=getUrl(iframe,url)	
                url=iframe
                dal=iframe
                break
                        
            elif 'cricplay.' in iframe:#
                if iframe.startswith('//'):
    
                    iframe = 'https:'+iframe
                html=getUrl(iframe,url)	
                url=iframe
                dal=iframe
                break    
                
                
            elif 'daddylive' in iframe:
                if iframe.startswith('//'):
    
                    iframe = 'https:'+iframe
                html=getUrl(iframe,url)	
                url_2=parseDOM(html,'iframe',ret='src')[-1]
                
                html_1=getUrl(url_2,'https://daddylive.fun/')
                url_3=parseDOM(html_1,'iframe',ret='src')[0]
                
                html_2=getUrl(url_3,url_2)
                
                html=html_2
                url=url_3
                dal=url_3
               
                #print('DADDY')
                #print(url)
                #print(dal)
                break
            elif 'strimstv.eu' in iframe:
                if iframe.startswith('//'):
                    iframe = 'https:'+iframe
                html=getUrl(iframe,url)	
                url=iframe
                dal=iframe
                break
        
        if html.find("eval(unescape('")>0:
            try:
                html=unescapeHtml(html)
            except:
                pass
        vido_url=re.findall("""['"](rtmp:.+?)['"]""",html,re.DOTALL)
        if vido_url:
            vido_url = vido_url[0]
        else:
            vido_url=re.findall("""source:\s*['"](.+?)['"]""",html,re.DOTALL)

            if vido_url:
                if 'google.' in vido_url[-1] :
                    vido_url = ''
            vido_url = vido_url[-1]+'|User-Agent='+UA+'&Referer='+dal if vido_url else mydecode.decode(url,html)
            
            if vido_url:
                if 'about:blank' in vido_url:
                    vido_url=mydecode.decode(url,html)	
    else:
        if vido_url=='':#
            vido_url=url
    #print('VIDO'+vido_url)#
    return vido_url

def resolvingCR_SW(url,ref):#TRANSMISJE strims.top
    print('WE_resolv')
    print(url)
    baseurl='https://strims.top'
    vido_url=''
    src_veryf=0    #0 jest iframe inne niż zidentyfikowane 1-iframe zidentyfikowane -1 brak ifram
    
    def srcVeryf(x):
        res=False
        ar=['assia4','cricplay','castfree.me','daddylive','noob4cast','jokerswidget','tvp.pl','givemenbastreams.com','cdnz','wigistream','youtube','embedstream','sportsnights.cc','wikisport.click','f1livegp','eplayer.click','bdnewszh.com']#zidentyfikowane iframy
        for a in ar:
            if a in x:
                res=True
                break
        return res
    
    src_veryf=srcVeryf(url)
    
    while src_veryf==0:
        if 'http' not in url:
            url=baseurl+url
        html=getUrl(url,ref)
        #print(html)
        urls=parseDOM(html,'iframe',ret='src')
        print(urls)
        if len(urls)==0:
            src_veryf=-1
        else:
            if 'chat' in urls[0] or 'f1right.php' in urls[0]:
                src_veryf=-1
            else:
                ref=url
                url=urls[0]
                if not url.startswith('http'):
                    bUrl=ref.split('/')
                    url=bUrl[0]+'//'+bUrl[1]+bUrl[2]+url
                    print(url)
                print('REF')
                print(ref)
                print('URL')
                print(url)
                src_veryf=srcVeryf(urls[0])
                    
        
    if src_veryf==-1:
        if 'youtube' in url:
            return mydecode._youtube(url)
        if 'eval(unescape' in html:
            dec=re.compile('eval\(unescape\(\'(.*)\'' ).findall(html)[0]
            res=bytes.fromhex(dec.replace('%','')).decode('utf-8')
            if 'castfree' in res:
                fid=re.compile('fid=\"(.*)\"; v_w').findall(res)[0]
                hea={'Referer':url}
                url='https://castfree.me/embed.php?player=embedded&live='+fid
                resp=requests.get(url,headers=hea).text
                url_stream=re.compile('return\(\[(.*)\]\.', re.DOTALL).findall(resp)
                if len(url_stream)>0:
                    url_stream=url_stream[0].replace('"','').replace('"','').replace('\\','').replace(',','')
                    vido_url=url_stream+'|User-Agent='+UA+'&Referer='+url
                    return vido_url
            if '/live/r2c' in res:
                hea={'Referer':url}
                url=baseurl+'/live/r2c.php'
                resp=requests.get(url,headers=hea).text
                dec=re.compile('eval\(unescape\(\'(.*)\'' ).findall(resp)[0]
                res=bytes.fromhex(dec.replace('%','')).decode('utf-8')
                if 'castfree' in res:
                    fid=re.compile('fid=\"(.*)\"; v_w').findall(res)[0]
                    hea={'Referer':url}
                    url='https://castfree.me/embed.php?player=embedded&live='+fid
                    resp=requests.get(url,headers=hea).text
                    url_stream=re.compile('return\(\[(.*)\]\.', re.DOTALL).findall(resp)
                    if len(url_stream)>0:
                        url_stream=url_stream[0].replace('"','').replace('"','').replace('\\','').replace(',','')
                        vido_url=url_stream+'|User-Agent='+UA+'&Referer='+url
                        return vido_url
        if 'source:' in html:
            url_stream=re.compile('source: \"(.*)\",' ).findall(html)
            if len(url_stream)>0:
                vido_url=url_stream[0]+'|User-Agent='+UA+'&Referer='+url
                return vido_url
            

    if 'assia4' in url:#
        html=getUrl(url,ref)	
        stream_url=re.compile('source: \'(.*)\'' ).findall(html)
        if len(stream_url)>0:
            vido_url=stream_url[0]+'|User-Agent='+UA+'&Referer='+url
            return vido_url
                
    if 'castfree.me' in url:#
        html=getUrl(url,ref)	
        html=html.replace('\n','')
        url_stream=re.compile('return\(\[(.*)\]\.', re.DOTALL).findall(html)
        if len(url_stream)>0:
            url_stream=url_stream[0].replace('"','').replace('"','').replace('\\','').replace(',','')
            vido_url=url_stream+'|User-Agent='+UA+'&Referer='+url
            return vido_url
            
    if 'noob4cast' in url:#
        html=getUrl(url,ref)	
        html=html.replace('\n','')
        url_stream=re.compile('return\(\[(.*)\]\.', re.DOTALL).findall(html)
        if len(url_stream)>0:
            url_stream=url_stream[0].replace('"','').replace('"','').replace('\\','').replace(',','')
            vido_url=url_stream+'|User-Agent='+UA+'&Referer='+url
            return vido_url
                
    if 'daddylive' in url:
        #print('DADDY')
        html=getUrl(url,ref)	
        url_2=parseDOM(html,'iframe',ret='src')[-1]
        html_1=getUrl(url_2,'https://daddylive.fun/')
        url_3=parseDOM(html_1,'iframe',ret='src')[0]
        html_2=getUrl(url_3,url_2)
        stream_url=re.compile('source:\'(.*)\'' ).findall(html_2)
        if len(stream_url)>0:
            vido_url=stream_url[1]+'|User-Agent='+UA+'&Referer='+url_3
            return vido_url
    
    if 'jokerswidget' in url:
        html=getUrl(url,ref)
        fid=re.compile('fid=\"(.*)\"; v_w').findall(html)[0]
        hea={'Referer':url}
        url='http://www.jokersplayer.xyz/embed.php?u='+fid
        resp=requests.get(url,headers=hea).text
        ifr=re.compile('\"true\" src=(.*)&amp;width').findall(resp)[0]
        hea={'Referer':url}
        url=ifr
        resp=requests.get(url,headers=hea).text
        ifr=url.replace(url.split('/')[-1],re.compile('src=(.*)&amp;width').findall(resp)[0])
        hea={'Referer':url}
        url=ifr
        resp=requests.get(url,headers=hea).text
        url_stream=re.compile('source: \'(.*)\',').findall(resp)
        if len(url_stream)>0:
            vido_url=url_stream[0]+'|User-Agent='+UA+'&Referer='+url
            return vido_url
    
    if 'tvp.pl' in url:
        html=getUrl(url,ref)
        url_stream=re.compile('href=\"(.*)\">').findall(html)
        if len(url_stream)>0:
            vido_url=url_stream[0]#+'|User-Agent='+UA+'&Referer='+url
            return vido_url
    
    if 'givemenbastreams.com' in url:
        html=getUrl(url,ref)
        url_stream=re.compile('source: \'(.*)\',').findall(html)
        if len(url_stream)>0:
            vido_url=url_stream[0]+'|User-Agent='+UA+'&Referer='+url
            return vido_url
            
    if 'wikisport.click' in url:
        html=getUrl(url,ref)
        x=re.compile('atob\(\'(.*)\'\)').findall(html)
        if len(x)>0:
            url_stream=base64.b64decode(x[0]).decode('utf-8')
            if 'nhl.com' in url_stream:
                vido_url=url_stream#+'|User-Agent='+UA+'&Origin=http://wikisport.click'
                proxyport = addon.getSetting('proxyport')
                vido_url='http://127.0.0.1:%s/NHL='%(str(proxyport))+vido_url
                addon.setSetting('replkey','https://mf.svc.nhl.com')
                addon.setSetting('keyurl','https://teko.al4n-smir.workers.dev/?https://retsports.com')
                return vido_url
            else:
                vido_url=url_stream#+'|User-Agent='+UA+'&Referer='+url
                proxyport = addon.getSetting('proxyport')
                vido_url='http://127.0.0.1:%s/WIKISPORT='%(str(proxyport))+vido_url
                return vido_url#GEOBLOKADA!!! (tenis channel)
            
    if 'sportsnights.cc' in url:
        print('SPORTNIGHTS')
        html=getUrl(url,ref)
        url_stream=re.compile('source:\"(.*)\"\}').findall(html)
        if len(url_stream)>0:
            vido_url=url_stream[0]#+'|User-Agent='+UA+'&Origin=http://sportsnights.cc'
            proxyport = addon.getSetting('proxyport')
            vido_url='http://127.0.0.1:%s/NHL='%(str(proxyport))+vido_url
            addon.setSetting('replkey','https://mf.svc.nhl.com')
            addon.setSetting('keyurl','http://sportsnights.cc')
            return vido_url
            
    if 'cdnz' in url:
        fid=re.compile('fid=\'(.*)\'; v_w').findall(html)[0]
        hea={'Referer':url}
        url='https://ragnaru.net/embed.php?player=embedded+&live='+fid
        resp=requests.get(url,headers=hea).text
        url_stream=re.compile('return\(\[(.*)\]\.', re.DOTALL).findall(html)
        if len(url_stream)>0:
            url_stream=url_stream[0].replace('"','').replace('"','').replace('\\','').replace(',','')
            vido_url=url_stream+'|User-Agent='+UA+'&Referer='+url
            return vido_url
            
    if 'wigistream' in url:
        return mydecode._wigistream(url,html,ref)
        
    if 'embedstream.' in url:
        vido_url=mydecode._embedstream(url,html,ref)
        return vido_url
        
    if 'youtube' in url:
        return mydecode._youtube(url)
        
    if 'f1livegp' in url:
        html=getUrl(url,ref)
        url_stream=re.compile('source: \"(.*)\",').findall(html)
        if len(url_stream)>0:
            vido_url=url_stream[0]+'|User-Agent='+UA+'&Referer='+url
            return vido_url
            
    if 'eplayer.click' in url:
        html=getUrl(url,ref)
        id_=url.split('id=')[-1]
        ref=url
        url=re.compile('\.src=`(.*)`;').findall(html)[0]
        url=url.split('id=')[0]+'id='+id_
        html=getUrl(url,ref)
        url_stream=re.compile('source:\'(.*)\',').findall(html)
        if len(url_stream)>0:
            vido_url=url_stream[1]+'|User-Agent='+UA+'&Referer='+url
            return vido_url
    
    if 'bdnewszh.com' in url:
        html=getUrl(url,ref)
        url_stream=re.compile('source: \"(.*)\",').findall(html)
        if len(url_stream)>0:
            vido_url=url_stream[0]+'|User-Agent='+UA+'&Referer=http://bdnewszh.com/'
            return vido_url
            
    if vido_url=='':
        print('OTHERS')
        vido_url=mydecode.decode(url,html)
        return vido_url
    
def getScheduleSE():
    out=[]
    html=getUrl(BASEURL)
    result = parseDOM(html,'table',attrs = {'align':'center'})[1]
    #nt=re.findall("font-size:18px'>Thursday - Feb 14th, 2019<",result)
    tds = parseDOM(result,'tr',attrs = {'style':' height:35px; vertical-align:top;'})#[0]
    dat= parseDOM(result,'span',attrs = {'style':' font-size:18px'})#<span style='font-size:18px'>
    for td in tds:
        
        tdk = parseDOM(td,'td')[0]

        czas = parseDOM(tdk,'td',attrs = {'class':'matchtime'})[0]
        teams = parseDOM(tdk,'td')[2]
        href = parseDOM(tdk,'a',ret='href')[0]
        href = BASEURL+href if href.startswith('/') else href
        dysc=teams.split(':')[0]
        tem=teams.split(':')[1]
        tit='%s - %s'%(czas,tem)
        out.append({'href':href+'|sch','title':tit,'code':dysc})
    return out

def getChannelsSE():
    out=[]
    html=getUrl(BASEURL)
    result = parseDOM(html,'div',attrs = {'class':'arrowgreen'})[0]#<div class="arrowgreen">
    lis = parseDOM(result,'li')#[0]
    for li in lis:
        title = parseDOM(li,'img',ret='alt')#[0]
        if title:
            if 'schedule' in title[0].lower():
                continue
        title=title[0] if title else parseDOM(li,'a')[0]
        href = parseDOM(li,'a',ret='href')[0]
        href = BASEURL+href if href.startswith('/') else href
        imag = parseDOM(li,'img',ret='src')#[0]
        imag= BASEURL+'/'+imag[0] if imag else ''
        out.append({'href':href+'|chan','title':title,'image':imag})
    return out	
    
def getSElink(url):
    
    out=[]
    url2=url.split('|')[0]
    
    query=urllib_parse.urlparse(url2).query
    co=1
    if 'sch' in url.split('|')[1]:
        url3='%s/streams/ss/ss%s.html'%(BASEURL,query)
        html=getUrl(url3,BASEURL)
        xbmc.sleep(2000) 
        stream=mydecode.decode(url3,html)
        if stream:
            out.append({'href':stream,'title':'Link %d'%co})
        return out
    else:
        url='%s/streams/misc/%s.html'%(BASEURL,query)
    html=getUrl(url,BASEURL)
    links=re.findall('id="link\d+" class="class_.+?" href="(.+?)"',html,re.DOTALL)
    
    for link in links:
        link= BASEURL+link if link.startswith('/') else link
        query=urllib_parse.urlparse(link).query
        if not query:
            query=link #if not query
        out.append({'href':query,'title':'Link %d'%co})

        co+=1
    return out
    
    
def getScheduleSWfolder(url):
    baseurl='http://strims.top'
    out=[]
    
    html=getUrl(url)

    first  = parseDOM(html,'td',attrs = {'class':'tb-mid'})
    if first:
           
        first = first[0].replace("\'",'"')
        first_1=first.split('<table')[0]
        hreftit=re.findall('href="([^"]+)">([^<]+)<',first_1,re.DOTALL)
        for ht in hreftit:
            h=ht[0]
            hh=baseurl+h if not 'http' in h else h #and '.php' in href else href
            t=ht[1]
            out.append({'title':t,'href':hh,'image':''})
        
        first_2=(first.split('<table')[1]).split('</table>')[0]
        first_2=first_2.split('</tr>')
        dzien=''
        mecz=''
        for f in first_2:
            if 'xx-large' in f:
                dzien=re.findall('<b>(.*)</b>',f,re.DOTALL)[0]
                out.append({'title':dzien,'href':'','image':''})
            if 'href' in f:
                czas=re.findall('<tr><td>([^td]+?)</td>',f,re.DOTALL)[0]
                mecz=re.findall('<span>(.*)</span>',f,re.DOTALL)[0]
                #href=re.findall('href="([^"]+)">([^<]+)<',first,re.DOTALL)
                href=re.findall('href="([^"]+)"',f,re.DOTALL)
                for h in href:
                    hh=baseurl+h if not 'http' in h else h #and '.php' in href else href
                    out.append({'title':'[B]'+czas+'[/B] '+mecz,'href':hh,'image':''})

    return out	
  
def getScheduleSW():
    out=[]
    html=getUrl(BASEURL3)

    first  = parseDOM(html,'div',attrs = {'class':'tab'})[0].replace("\'",'"')#<div class="tab">
    iddaydate=re.findall("""event,\s*"(.+?)".+?>(.+?)</button""",first,re.DOTALL)
    #print(iddaydate)
       
    for id,day in iddaydate:
        result = parseDOM(html,'div',attrs = {'id':id})[0]
        result=result.replace('a class=""','a class=" "')
        #xxx=re.findall('(\d+:\d+).*<a class="([^"]+)" href="([^"]+)">([^>]+)</a>',result)
        xxx=re.findall('(\d+:\d+).*<a class="([^"]+)" href="([^"]+)">(.*)</a>',result)
        if xxx:
            day=('kiedy|%s'%(day)).replace('FIRDAY','FRIDAY')	
            out.append({'href':day})	
            for czas,ikona,href,tyt in  xxx:
                ikona=ikona.replace(' goldd','').replace(' limee','').replace(' redd','').replace(' aquaa','').replace(' hit','')
                if '\xf0\x9f\x8e\xb1' in ikona:
                    ikona='snooker'
                tyt=re.sub('<font color=.+?>', '', tyt).replace('</font>','')
                if '<b>' in tyt:
                    try:
                        tyt=re.findall('<b>(.*)</b>',tyt)[0]
                    except:
                        tyt=tyt.replace('</b>','').replace('<b>','')
                #tyt=get_image(ikona)+tyt
                if '<a href' in tyt or '<br><br' in tyt:
                    continue
                tyt = '[B][COLOR khaki]%s : [/COLOR][/B][COLOR gold][B]%s[/B][/COLOR]'%(czas,tyt)
                href2='http://strims.top'+href if href.startswith ('/') else 'http://strims.top/'+href
                out.append({'title':tyt,'href':href2,'image':ikona})								
    #print('OUT_SCHE')
    #print(out)
    return out
    
def getScheduleSstreams():
    out=[]
    html=getUrl(BASEURL4)
    result  = parseDOM(html,'div',attrs = {'class':"main-inner group"})[0] 
    items = parseDOM(html,'article',attrs = {'id':"post-\d+"}) 
    for item in items:
        href = parseDOM(item,'a',ret='href')[0]
        imag = parseDOM(item,'img',ret='src')[0]
        tyt = parseDOM(item,'a')[2]
        code = parseDOM(item,'a')[1]
        tyt='[COLOR gold][B]%s[/B][/COLOR]'%tyt
        out.append({'title':tyt,'href':href,'image':imag,'code':code})	
    return out

def getChannelsSW():
    out=[]
    html=getUrl(BASEURL3+'sports-channel/')
    result = parseDOM(html,'tbody')[0]
    hrefimage=re.findall('<a href="(.+?)"><img src="(.+?)"></a>',result,re.DOTALL)
    for href,image in hrefimage:
        tyt=href.split('-stream-online')[0].replace('-',' ').upper()
        href = 'http://strims.top/sports-channel/'+href
        out.append({'href':href,'title':'[COLOR lime]► [/COLOR] [B][COLOR gold]'+tyt+'[/COLOR][/B]','image':image})
    return out	
    
def F1channels():

    out=[]
    html=getUrl(BASEURL3+'live/f1base.php')

    result = parseDOM(html,'h3')#[0]
    result2 = parseDOM(html,'div',attrs = {'id':"news"})#[0]#<div class="arrowgreen">
    result = result[0] if result else result2[0]
    hreftit=re.findall('href="([^"]+)"><.+?>([^>]+)<',result,re.DOTALL)
    for href,tyt in hreftit:
        href = 'http://strims.top'+href
        out.append({'href':href,'title':'[COLOR lime]► [/COLOR] [B][COLOR gold]'+tyt+'[/COLOR][/B]'})
    return out	
    
    
def getUnblocked(html):
    html=re.findall('<script>(.+?)document.write',html,re.DOTALL)[0]
    if html.find('Our Free Server is Full')>0:
        xbmcgui.Dialog().notification('[B]Error[/B]', '[B]Free server is full[/B]',xbmcgui.NOTIFICATION_INFO, 8000,False)	
        return ''
    oile=re.findall('(\d+?)\); }',html,re.DOTALL)[0]
    dane2=re.findall('(\[.+?\])',html,re.DOTALL)[0]
    ht=eval(dane2)
    text=''
    for d in ht:
        a=int(d)-int(oile)
        text+=chr(a)
    source=re.findall('src="(.+?m3u8.+?)"',text)
    if not source:
        source =re.findall('source: "(.+?)"',text,re.DOTALL)
        source = source[0] if source else ''
    else:
        source=source[0] if source else ''
    source = 'http:'+source if source.startswith('//') else source
    return source
def getSWlink(url):
    stream=''
    playt=True
    html=getUrl(url,BASEURL3)
    if 'streamamg.com' in html:
        iframes = parseDOM(html,'iframe',ret='src')#[0]
        for iframe in iframes:
            if 'streamamg.' in iframe:
                html2=getUrl(iframe,url)	
                xx=re.findall('"partnerId":(\d+)',html2,re.DOTALL)[0]
                xx2=re.findall('"rootEntryId":"(.+?)"',html2,re.DOTALL)[0]
                m3u8='http://open.http.mp.streamamg.com/p/%s/playManifest/entryId/%s/format/applehttp'%(xx,xx2)
                return m3u8+'|User-Agent='+UA+'&Referer='+iframe,False
    elif 'unblocked.is' in html:
        iframes= parseDOM(html,'iframe',ret='src')#[0]
        for iframe in iframes:
            if 'unblocked.is' in iframe:
                if 'nullrefer.com' in iframe or 'href.li/' in iframe:
                    iframe = urllib_parse.urlparse(iframe).query
                html2=getUrl(iframe,url)
                
                stream=getUnblocked(html2)
                return stream,False
    else:
        stream=re.findall('source: "(.+?)"',html,re.DOTALL)
    if stream:
        stream=stream[0]	
    else:
        stream=re.findall('source src="(.+?)"',html,re.DOTALL)[0]
        playt=False
    return stream+'|User-Agent='+UA+'&Referer='+url,playt
    
def getSWlink2(url):
    stream=''
    playt=True
    html=getUrl(url,BASEURL3)
    stream=getUnblocked(html)
    return stream,False

    
def getUrlProx(url):
    headers = {
        'Host': 'www.uk-proxy.co.uk',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Referer': 'http://www.uk-proxy.co.uk/',
        'Upgrade-Insecure-Requests': '1',}
        

    #if '/w.php' in url:
    mainurl='http://www.uk-proxy.co.uk'
    params = (('u', url),('b', '4'),('f', 'norefer'),)
    response = requests.get('http://www.uk-proxy.co.uk/w.php', headers=headers, params=params,verify=False).content
    if six.PY3:
        response = response.decode(encoding='utf-8', errors='strict')
    return response
def repdays(day):
    if 'Today' in day:
        day=day.replace('Today','Tomorrow')
    elif 'Yesterday' in day:
        day=day.replace('Yesterday','Today')
    elif 'Tomorrow' in day:
        day=day.replace('Tomorrow','Next day')
    return day	
    
   
def getCrackstreams(url):
    out = []
    hd = {'User-Agent': UA}
    
    html=getUrl(url,BASEURL8)

    result = parseDOM(html,  'div', attrs={'class':"col\-xs\-\d+ col-md\-\d+ col\-sm\-\d+"})[0] 
    links = re.findall('(<a.*?<\/a>)', result,re.DOTALL)
    for link in links:
        href = parseDOM(link,'a',ret='href')[0]
        img = parseDOM(link,'img',ret='src')[0]
        t1 = parseDOM(link,'h4')[0]
        t2 = parseDOM(link,'p')#[0]
        t2 = t2[0] if t2 else ''

        href = BASEURL8+href if href.startswith('/') else href
        img = BASEURL8+img if img.startswith('/') else img

        out.append({'title':t1,'href':href,'image':img,'code':t2})

    return out

def getStreamCrackstreams(url):
    packer = re.compile('(eval\(function\(p,a,c,k,e,(?:r|d).*)')
    stream = ''
    #	
    vidurl =''
    hea = None
    try:
        html=getUrl(url,BASEURL8)
    except:
        html = None
    if html:
        iframe = parseDOM(html, 'iframe', ret='src')#[0]

        if iframe:
    
            nturl = url+iframe[0] if not iframe[0].startswith('http') else iframe[0]
            html=getUrl(nturl,url)
            stream_url = re.findall("""atob\s*\(\s*['"](.+?)['"]""",html,re.DOTALL)

            if stream_url:
                vidurl=base64.b64decode(stream_url[0])
                if six.PY3:
                    vidurl = vidurl.decode(encoding='utf-8', errors='strict')
                vidurl = vidurl#+'|User-Agent='+UA+'&Referer='+url
                hea = '|User-Agent='+UA+'&Referer='+url
            else:
                iframe = parseDOM(html, 'iframe', ret='src')#[0]
                
                if iframe:
                    

                    nturl = url+iframe[0] if not iframe[0].startswith('http') else iframe[0]
                    if 'freefeed' in nturl:
                        html=getUrl(nturl,url).replace("\'",'"')
                        vido_url=re.findall('Clappr.*?source:\s+"(.+?)"',html,re.DOTALL)

                        vidurl = vido_url[0] if vido_url else ''
                        hea = '|User-Agent='+UA+'&Referer='+nturl+'&Origin=https://freefeds.net'
                        vidurl = vido_url[0]+hea if vido_url else ''
                    else:
                        vidurl=mydecode.decode(nturl,html)

    return vidurl,hea		

def VipLeagueStream(url, tit):
    hd = {'User-Agent': UA}

    html=sess.get(url,headers=hd,verify=False).content
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    err=''
    stream=''

    if 'https://cdn.plytv.me/' in html or 'cdn.tvply.me' in html:
    
        stream,err = _plytv	(url,url,BASEURL6,tit)
        

        
    return stream,err

    
#def authcheck(title, referer, stream, code, exts):
def authcheck(title, strName, scode, expires):
    import json

    params = (
        ('stream', strName),
        ('scode', scode),
        ('expires', expires),
    )
    #addon.setSetting('viphdrs',str(headers))
    headersvip=eval(addon.getSetting('viphdrs'))
    
    session = Session()
    session.mount("https://key.seckeyserv.me", ZoomTVAdapter())
    session.headers.update(headersvip)
    try:
        timeout = 0
        response = session.get('https://key.seckeyserv.me/', params=params, verify=False)
        if response.status_code != 200:
            raise Exception("HTTP CODE %s" % response.code)
        data=json.loads(response.text)
        #xc = base64.b64encode(vbvb)
        
        
        
    #try:
    #    timeout = 0
    #
    #    url_authme = 'https://authme.seckeyserv.me?stream=%s&scode=%s&expires=%s' % (stream, code, exts)
    #    ret = httptools.downloadpage(url_authme, headers={'referer': referer})
    #
    #    if ret.code != 200:
    #        raise Exception("HTTP CODE %s" % ret.code)
    #    data = ret.data
    #
        player = xbmc.Player()
        isPlaying = player.isPlaying()
        
        while not isPlaying and timeout < 30:
            xbmc.sleep(1000)
            timeout += 1
            isPlaying = player.isPlaying()
        
        if timeout == 30:
            raise Exception("Timeout")
        
        while player.isPlaying():
            xbmc.log("######################### zaczalem petle #########################", xbmc.LOGNOTICE)

            player_title = ""
            timeout = 0
            while not player_title and timeout < 10:
                xbmc.sleep(1000)
                timeout += 1
                try:
                    player_title = xbmc.Player().getVideoInfoTag().getTitle()
                    player_title2 = xbmc.Player().getPlayingFile()
                    xbmc.log("######################### tytul: %s #########################"%str(player_title), xbmc.LOGNOTICE)
                    xbmc.log("######################### tytul2: %s #########################"%str(player_title2), xbmc.LOGNOTICE)
                except:
                    pass

            res = data
            if not res['success']:
                raise Exception("No Success")

            params = (
                ('stream', strName),
                ('scode', res['scode']),
                ('expires', res['ts']),
            )
            response = session.get('https://key.seckeyserv.me/', params=params, verify=False)
            
            
            if response.status_code != 200:
                raise Exception("HTTP CODE %s" % response.status_code)
            data=json.loads(response.text)

            xbmc.log("######################### authcheck ok #########################", xbmc.LOGNOTICE)
            
            
            xbmc.sleep(300000)
    except Exception as inst:
        xbmc.log("######################### authcheck fail #########################", xbmc.LOGNOTICE)
        xbmc.log("######################### blad %s #########################"%str(inst), xbmc.LOGNOTICE)

    else:

        xbmc.log("######################### authcheck end #########################", xbmc.LOGNOTICE)
def _plytv	(query,url,orig,tit):

    video_url=''
    err=None
    headers = {'User-Agent': UA,'Referer': url}	

    contentVideo=getUrl(query,url)

    html=contentVideo.replace("\'",'"')
    url = 'https://www.tvply.me/sdembed' if 'cdn.tvply.me' in html else 'https://www.plytv.me/sdembed'
    qbc= 'https://www.tvply.me/'  if 'cdn.tvply.me' in html else'https://www.plytv.me/'
    headers = {

        'cache-control': 'max-age=0',
        'upgrade-insecure-requests': '1',
        'origin': orig,
        'content-type': 'application/x-www-form-urlencoded',
        'user-agent': UA,
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-gpc': '1',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-dest': 'iframe',
        'referer': query,
        'accept-language': 'en-US,en;q=0.9',
    }

    pdettxt =re.findall('pdettxt\s*=\s*"(.+?)"',html,re.DOTALL)[0]
    zmid=re.findall('zmid\s*=\s*"(.+?)"',html,re.DOTALL)#[0]
    if zmid:
        zmid=zmid[0]
        edm=re.findall('edm\s*=\s*"(.+?)"',html,re.DOTALL)[0]
        pid = re.findall('pid\s*=\s*(\d+);',html,re.DOTALL)[0]
        
    
        
        params = (
            ('v', zmid),
        )
        
        data = {
        'pid': (str(pid)),
        'ptxt': pdettxt
        }
        urlk = url+'?v='+str(zmid)
    else:
        v_vid= re.findall('v_vid\s*=\s*"(.+?)"',html,re.DOTALL)[0]
        v_vpp= re.findall('v_vpp\s*=\s*"(.+?)"',html,re.DOTALL)[0]
        v_vpv = re.findall('v_vpv\s*=\s*"(.+?)"',html,re.DOTALL)[0]
        edm = re.findall('edm\s*=\s*"(.+?)"',html,re.DOTALL)[0]

        data = {
            'id': v_vid,
            'v': v_vpv,
            'p': v_vpp,
            'ptxt': pdettxt
        }
        params = None
        urlk = "https://" + edm + "/hdembed?p=" + v_vpp + "&id=" + v_vid + "&v=" + v_vpv
        

    response_content = sess.post(urlk, headers=headers, params=params, data=data,verify=False).content

    headersx1 = {
    'User-Agent': UA,
    'Accept': '*/*',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Referer': urlk,
    'Origin': orig,
    'DNT': '1',
    'Connection': 'keep-alive',}
    ntx = 'https://plytv.rocks?v='+str(zmid)+'&d=desktop&u=vipleague.lc&url='+urllib_parse.quote(urlk)
    response = sess.get(ntx, headers=headersx1,verify=False)#.content
    av=response.cookies
    ac=sess.cookies
    sck=''.join(['%s=%s;'%(c.name, c.value) for c in ac])
    
    headers = {
        'Host': 'cdn.tvply.me',
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0',
        'accept': '*/*',
        'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
        'referer': query,
        'dnt': '1',
        'te': 'trailers',
    }
    try:
        response = sess.get('https://cdn.tvply.me/scripts/embed.min.js', headers=headers,verify=False)#.content
        av=response.cookies
        ac=sess.cookies
        sck=''.join(['%s=%s;'%(c.name, c.value) for c in response.cookies])
    except:
        pass

    if six.PY3:
        response_content = response_content.decode(encoding='utf-8', errors='strict')

    skrypty = re.findall('<script>(.+?)<\/script>\\n',response_content,re.DOTALL)#<script>([^<]+)<\/script>',response_content,re.DOTALL)

    payload = """function abs() {%s};\n abs()    """
    a=''
    for skrypt in skrypty:
        if 'let' in skrypt and 'eval' in skrypt:

                a = payload%(skrypt)

                a = a[::-1].replace("eval"[::-1], "return"[::-1], 1)[::-1]

                break

    jsPayload = a 

    import js2py

    js2py.disable_pyimport()
    context = js2py.EvalJs()
    
    try:

        context.execute(jsPayload)
        response_content = context.eval(jsPayload)
        response_content = response_content if response_content else ''
    except Exception as e:

        response_content=''
    

    if 'function(h,u,n,t,e,r)' in response_content:

        import dehunt as dhtr
        ff=re.findall('function\(h,u,n,t,e,r\).*?}\((".+?)\)\)',response_content,re.DOTALL)[0]#.spli
        ff=ff.replace('"','')
        h, u, n, t, e, r = ff.split(',')
        
        cc = dhtr.dehunt (h, int(u), n, int(t), int(e), int(r))

        cc=cc.replace("\'",'"')
        
        fil = re.findall('file:\s*window\.atob\((.+?)\)',cc,re.DOTALL)[0]

        src = re.findall(fil+'\s*=\s*"(.+?)"',cc,re.DOTALL)[0]
        video_url = base64.b64decode(src)
        if six.PY3:
            video_url = video_url.decode(encoding='utf-8', errors='strict')

        str1 = re.findall('"?stream="\s*\+\s*(\w+)\s*\+\s*"',cc,re.DOTALL)[0]
        strName = re.findall('const\s*%s\s*=\s*"([^"]+)"'%(str1),cc,re.DOTALL)[0]

        scode,expires = re.findall('formauthurl\({"scode":\s*"([^"]+)",\s"ts":\s(\d+)\}',cc,re.DOTALL)[0]

        hdrs = 'User-Agent={}&Referer={}&Origin={}'.format(urllib_parse.quote(UA),
                                                           urllib_parse.quote(urlk),
                                                           urllib_parse.quote(orig))



        headersx = {
        'User-Agent': UA,
        'Accept': '*/*',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Referer': urlk,
        'Origin': qbc,
        'DNT': '1',
        'Connection': 'keep-alive',}

        
        headers5 = {
            'User-Agent': UA,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Referer': urlk,
            'Origin': qbc,
            'Connection': 'keep-alive',
            'TE': 'Trailers',
        }
        
        params = (
            ('stream', strName),
            ('scode', scode),
            ('expires', expires),
        )
        headers = {
            "Referer": urlk,
            "Origin": qbc,
            "User-Agent": UA,
            "Accept-Language": "en",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        addon.setSetting('viphdrs',str(headers))
        
#		thread = threading.Thread(name='authcheck', target=authcheck, args=[tit, strName, scode, expires])
#		thread.setDaemon(True)
#		thread.start()
    #	strName, scode, expires
        session = Session()
        session.mount("https://key.seckeyserv.me", ZoomTVAdapter())
        session.headers.update(headers)
        
        response = session.get('https://key.seckeyserv.me/', params=params, verify=False)

        vbvb=response.text


        headers = {
            "Referer": urllib_parse.quote(urlk),#   
            "Origin": urllib_parse.quote(qbc),
            "User-Agent": urllib_parse.quote(UA),
            "Accept-Language": urllib_parse.quote("en"),
            "Accept": urllib_parse.quote("application/json, text/javascript, */*; q=0.01"),
        }
        
        
        headers2x = {
            "Referer": urlk,#   
            "Origin": qbc,
            "User-Agent": UA,
            "Accept-Language": "en",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        addon.setSetting('heaNHL2',str(headers2x))									   
        hdrs= '&'.join(['%s=%s' % (name, value) for (name, value) in headers.items()])	

        video_url=video_url+ '|'+hdrs

    else:
        err='The stream will start soon. Please check again after a moment'
        #if err in response 
        response_content = response_content.replace("\'",'"')

        video_url = re.findall('soureUrl = "(.+?)"',response_content,re.DOTALL)#[0]
        if video_url:
            video_url=base64.b64decode(video_url[0])
            headersx = {
            'User-Agent': UA,
            'Accept': '*/*',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Referer': urlk,
            'Origin': orig,
            'DNT': '1',
            'Connection': 'keep-alive',}
    
            hea= '&'.join(['%s=%s' % (name, value) for (name, value) in headersx.items()])
            addon.setSetting('heaNHL2',str(headersx))
            hdrs = 'User-Agent={}&Referer={}&Origin={}&CustomKeyUri={}'.format(urllib_parse.quote(UA),
                                                            urllib_parse.quote(urlk),
                                                            urllib_parse.quote(orig))
            video_url=video_url+ '|'+hea
    addon.setSetting('vipurlk',urlk)
    addon.setSetting('viporig',orig)

    return video_url,err

def getLinksVipLeague(id,tyt):
    
    out = []
    import json
    f = xbmcvfs.File(vleagueFile)
    b = f.read()
    f.close()
    data =json.loads(b)

    dt = re.findall('(\(.+?\))',tyt,re.DOTALL)
    p1 = re.findall('^(.+?)\[COLOR',tyt,re.DOTALL)
    p1 =p1[0] if p1 else tyt
    f=data.get(id,{})
    if f:
        f = f.replace("\'",'"') if f else f#1#base
    
        datas = re.findall('class="col-12 text(.+?)\/button><\/div',f,re.DOTALL)
        l=1
        for data in datas:
    
            aa=''
            hrefs= re.findall('data-uri="(.+?)"',data,re.DOTALL)#[0]
            
            for href in hrefs:
    
                ql = re.findall(href+'.+?mr-1">(.+?)<',data,re.DOTALL)
                ql= ql[0] if ql else ''
                href = BASEURL6+href if href.startswith('/') else href
                
                data = re.sub("<[^>]*>","",data) #if qual else ''
                t2 = re.findall('\#(\w+)',data,re.DOTALL)#[0]
                t2 = t2[0] if t2 else ''
    
                tytul= t2+' Link %d %s'%(l,ql)
    
                out.append({'title':tytul,'href':str(href),'image':'','code':dt[0] if dt else tytul,'plot':p1})
                l+=1
    
    return out	
def getVipLeagueStreams(url,srch=""):

    out =[]
    dif = gettimedif()

    hd = {'User-Agent': UA}
    if srch:
        data = {'searchbox': srch}
        headersx = {
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Referer': 'https://www.vipleague.lc',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.vipleague.lc',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'TE': 'Trailers',
        }
        html = sess.post('https://www.vipleague.lc/explore-'+srch+'-stream', headers=headersx, data=data).content

    else:
        html=sess.get(url,headers=hd,verify=False).content
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')

    result = parseDOM(html,'div',attrs = {'id':".+?",'class':"invisible"})#[0]		 #<div class="arrowgreen"><div id="btyTUX" class="invisible">   invisible
    if result:

        schdata=re.findall('schdata":"(.+?)"',html,re.DOTALL)[0]
        headers5 = {
            'User-Agent': UA,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Referer': url,
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'TE': 'Trailers',}
    
        params = (('lds', schdata),)
        
        nturl = 'https://www.vipleague.lc/loadschdata?ids='+schdata
        html=sess.get(nturl,headers=headers5, params=params,verify=False).content

        if six.PY3:
            html = html.decode(encoding='utf-8', errors='strict')
        f = xbmcvfs.File(vleagueFile, 'w')
        f.write(html.encode('utf-8') if six.PY2 else html)
        f.close()

        tithrefikondt = re.findall('title="([^"]+)".*?data-target=".*?(\d+)".*?<span class="vleague (\w+).*?".*?span content="([^"]+)"',result[0],re.DOTALL)#[0]

        for tyt,href,ikon,dt in tithrefikondt:

            dt = getrealtime(dt,dif)
            tit = '%s [COLOR gold](%s)[/COLOR]'%(tyt,dt)
            out.append({'title':tit,'href':str(href),'image':ikon,'code':dt})
    return out
def gettimedif():
    import datetime
    import time
    a=datetime.datetime.utcnow()
    readable1 = a.strftime('%Y-%m-%dT%H:%M')
    b=datetime.datetime.now()
    readable2 = b.strftime('%Y-%m-%dT%H:%M')

    try:
        date_time_obj=datetime.datetime.strptime(readable1, '%Y-%m-%dT%H:%M')+datetime.timedelta(hours=1)
        date_time_obj2=datetime.datetime.strptime(readable2, '%Y-%m-%dT%H:%M')

    except TypeError:
        date_time_obj=datetime.datetime(*(time.strptime(readable1, '%Y-%m-%dT%H:%M')[0:6]))+datetime.timedelta(hours=1)
        date_time_obj2=datetime.datetime(*(time.strptime(readable2, '%Y-%m-%dT%H:%M')[0:6]))

    def to_timestamp(a_date):
        from datetime import datetime
        try:
            import pytz
        except:
            pass
        if a_date.tzinfo:
            epoch = datetime(1970, 1, 1, tzinfo=pytz.UTC)
            diff = a_date.astimezone(pytz.UTC) - epoch
        else:
            epoch = datetime(1970, 1, 1)
            diff = a_date - epoch
        return int(diff.total_seconds())*1000	
    tst4 =	 to_timestamp(date_time_obj)
    tst5 =	 to_timestamp(date_time_obj2)
    dif = tst5-tst4
    return int(dif)/3600000


def getrealtime(dt,dif):
    import datetime
    try:
        date_time_obj=datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M')
    except TypeError:
        date_time_obj=datetime.datetime(*(time.strptime(dt, '%Y-%m-%dT%H:%M')[0:6]))
    
    rltime = date_time_obj + datetime.timedelta(hours=dif)
    rltime = rltime.strftime('%Y-%m-%d %H:%M')

    return rltime

def getVipLeague(url):
    out =[]
    hd = {'User-Agent': UA}

    html=getUrl(url,BASEURL6)

    links = parseDOM(html,  'div', attrs={'class':'col-\d+ col-md-\d+ col-lg-\d+.+?'})
    for link in links:

        href,tyt = re.findall("href ='(.+?)' title='(.+?)'",link,re.DOTALL)[0]
        title = tyt.split(' Online Stream')[0] if 'online ' in tyt.lower() else tyt

        href = BASEURL6+href if href.startswith('/') else href

        icn = re.findall("div class='vlgh (\w+)",link,re.DOTALL)
        icn = icn[0] if icn else ''

        out.append({'title':title,'href':href,'image':icn,'code':title})
    return out

def getLiveSport():
    out =[]
    resp=requests.get(BASEURL5)

    if resp.status_code == 403:
        my_addon.setSetting('proksWS', 'true')
        
        html = getUrlProx(BASEURL5)
    else:
        my_addon.setSetting('proksWS', 'false')
        html=getUrl(BASEURL5,BASEURL5)
    result = parseDOM(html,'ul',attrs = {'class':"drop-list"})

    acts = parseDOM(result,'li',attrs = {'class':"active"})
    for act in acts:
        kiedy = re.findall('"text">(.+?)<\/span><\/a>',act)[0] #>12 September, Today</span></a>
        if my_addon.getSetting('proksWS')=='true':
            kiedy=repdays(kiedy)
        day='kiedy|%s'%kiedy
        out.append({'href':day})	
        
        act=act.replace("\'",'"')
        links = parseDOM(act,'li')#[0]
        for link in links:
            href = parseDOM(link,'a',ret='href')[0]
            href = 'https://livesport.ws'+href if href.startswith('/') else href
            try:
                team1 = re.findall('right;">(.+?)<\/div>',link)[0]
                team2 = re.findall('left;">(.+?)<\/div>',link)[0]
                mecz='%s vs %s'%(team1,team2)
            except:
                mecz=re.findall('center;.+?>(.+?)<',link)[0]
            dysc = re.findall('"competition">(.+?)</',link)#[0]
            dysc =dysc[0] if dysc else ''
            ikon = parseDOM(link,'img',ret='src')[0]
            datas = parseDOM(link,'span',attrs = {'class':"date"})[0] 
            liv = parseDOM(datas,'i')[0]
            
            online= '[COLOR lime]► [/COLOR]' if 'live' in liv.lower() else '[COLOR orangered]■ [/COLOR]'
            id = parseDOM(link,'i',ret='id')#[0]
            if id:
                postid=re.findall('(\d+)\-',href)[0]
                eventid=id[0]
                href+='|event_id=%s|post_id=%s|'%(eventid,postid)

            czas = parseDOM(datas,'i',ret='data-datetime')[0]#attrs = {'class':"date"})
            st=re.findall('(\d+:\d+)',czas)[0]
            czas1 = str(int(st.split(':')[0])-2)
            czas = re.sub('\d+:', czas1+':', czas)
            title = '[B][COLOR khaki]%s%s : [/COLOR][/B][COLOR gold][B]%s[/B][/COLOR]'%(online,czas,mecz)
            out.append({'title':title,'href':href,'image':ikon,'code':dysc})

    return out

def getLinksLiveSport(url,tytul):
    proksWS=my_addon.getSetting('proksWS')
    out=[]

    ref=url.split('|')[0]
    evpo = re.findall('(\d+)\|post_id=(\d+)\|',url)[0]

    event_id=evpo[0]
    post_id=evpo[1]
    cookies = {
        'dle_time_zone_offset': '7200',
    }

    headers = {
        'User-Agent': UA,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'X-Requested-With': 'XMLHttpRequest',

        'Referer': ref,

    }
    
    dane = (
        ('from', 'event'),
        ('event_id', event_id),
        ('tab_id', 'undefined'),
        ('post_id', post_id),
        ('lang', 'en'),
    )
    if proksWS=='true':
        cd=urllib_parse.urlencode(dane)
        url='https://livesport.ws/engine/modules/sports/sport_refresh.php?'+cd
        html = getUrlProx(url)
        import json
        response=json.loads(html)
    else:
        response = sess.get('https://livesport.ws/engine/modules/sports/sport_refresh.php', headers=headers, params=dane, cookies=cookies,verify=False,timeout=30).json()
    try:
        broadcast=response['broadcast']
        flashes = parseDOM(broadcast,'li',attrs = {'class':"flashtable",'id':'.+?'})#[0]
        if flashes:
            flashes  = parseDOM(flashes[0],'tbody')
        links = parseDOM(flashes,'tr')
        co=1
        for link in links:
            code = parseDOM(link,'img',ret='title')#[0]
            code = code[0] if code else ''
            href = parseDOM(link,'a',ret='href')
            href = href[0] if href else ''
            
            tyt = 'Link %s - [COLOR violet]%s[/COLOR]'%(co,code)

            if href:
                out.append({'title':tyt,'href':href,'image':'','code':code})	
                co+=1
            else:
                continue
    except:
        pass
    return out

def getStreamLiveSport(url):
    proksWS=my_addon.getSetting('proksWS')

    headers = {
        'Host': 'stream.livesport.ws',
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
    }

    html = sess.get(url, headers=headers,verify=False,timeout=30).text
    if proksWS=='true':
        html = getUrlProx(url)

    iframe = parseDOM(html,'iframe',ret='src')[0]
    if '/w.php?' in iframe:
        iframe=urllib_parse.unquote(iframe)
        iframe=re.findall('\?u=(.+?)\&amp;',iframe)[0]

    if 'vamosplay' in iframe:
        headers = {
            'User-Agent': UA,
            'Accept': '*/*',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Connection': 'keep-alive',
            'Referer': iframe,
        }
        
        html = sess.get('http://vamosplay.tech/js/config-stream.js', headers=headers,verify=False,timeout=30).text
        html=html.replace("\'",'"')
        servers = re.findall('var servers\s*=\s*"([^"]+)"',html)
        
        headers = {
            'User-Agent': UA,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Origin': 'http://vamosplay.tech',
            'Connection': 'keep-alive',
            'Referer': iframe,
    
        }
        
        response = sess.get(servers[0], headers=headers,verify=False,timeout=30).json()
        stream_adr=response['data']['url']
        rodzaj = re.findall('(\/\w+)',iframe)[-1]
        source = 'http://' + stream_adr + '/channels' + rodzaj + '/stream.m3u8'

    else:
        if 'sportba.com' in iframe:
            source=mydecode.getsportba(iframe,url)	
        elif 'sportsbay' in iframe:
            source=mydecode._sportsbayorg(iframe,url,url)	
            
        elif '365lives.' in iframe:
            source=mydecode._365live(iframe,url)	
            
        elif 'dummyview.online' in iframe:
            source=mydecode._dummyview(iframe,url)	
            #http://dummyview.online
            
            
            
            
        else:
            source=mydecode.decode(url,html)

    return source
    
    

    