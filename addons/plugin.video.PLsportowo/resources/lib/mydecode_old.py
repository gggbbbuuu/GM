# -*- coding: utf-8 -*-

import sys
import re
import six
from six.moves import urllib_error, urllib_request, urllib_parse, http_cookiejar

import base64

import jsunpack

import requests
import gzip
import xbmc, xbmcaddon
#import web_pdb
try:
    from StringIO import StringIO ## for Python 2
    LOGNOTICE = xbmc.LOGNOTICE

except ImportError:
    from io import StringIO ## for Python 3
    LOGNOTICE = xbmc.LOGINFO
    
    
addon = xbmcaddon.Addon(id='plugin.video.PLsportowo')
my_addon = addon
proxyport = addon.getSetting('proxyport')
sess=requests.Session()

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












UACHR = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'

#UACHR = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36"
UA='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0'
packer = re.compile('(eval\(function\(p,a,c,k,e,(?:r|d).*)')
clappr = re.compile('new\s+Clappr\.Player\(\{\s*?source:\s*?["\'](.+?)["\']')


clappr2x=re.compile('new\s+Clappr\.Player\(.*?{.*?source:\s*?["\'](.+?)["\']')

source = re.compile('sources\s*:\s*\[\s*\{\s*(?:type\s*:\s*[\'\"].+?[\'\"],|)src\s*:\s*[\'\"](.+?)[\'\"]')

def getUrl(url,data=None,header={},cookies=None):
    if not header:
        header = {'User-Agent':UA}
    req = urllib_request.Request(url,data,headers=header)
    try:
        response = urllib_request.urlopen(req, timeout=10)
        link = response.read()
        response.close()
    except:
        link=''
    return link

def get_url_(url,cj,header={},cookies=None):
    headers = {'User-Agent':UA}
    headers.update(header)
    opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(cj))
    urllib_request.install_opener(opener)
    req = urllib_request.Request(url,data=None,headers=header)
    response = urllib_request.urlopen(req, timeout=15)
    link = response.read()
    response.close()
    return link
def decodeSecur(data):
    srcs = []
    if 'iframe-secure' in data:
        ifrSec = re.compile('src="(//iframe-secure.*?)"',re.DOTALL|re.IGNORECASE).findall(data)
        id = ifrSec[0].split('/')[-1] if ifrSec else ''
        url = 'http://iframe-secured.com/embed/iframe.php?u='+id
        header= {'User-Agent':UA,'Referer':'http://iframe-secured.com/embed/'+id}
        contentDec = getUrl(url,header=header)
        if six.PY3:
            contentDec = contentDec.decode(encoding='utf-8', errors='strict')

        
        match = re.compile('(eval\\(function\\(p,a,c,k,e,d\\).*?)\n').findall(contentDec)
        if match:
            contentVideo = jsunpack.unpack(match[0]).decode('string_escape')
            srcs=re.findall('window.location.replace\\([\'"](.*?)[\'"]',contentVideo)
    return srcs
def debug(deb):
    pass
def decode(url,data):

    data =re.sub('(<\!\-\-.*?\-\-\>)','',data, flags=re.DOTALL)
    srcs=re.compile('src=["\']\\s*((?:http|).*?)["\']',re.DOTALL+re.IGNORECASE).findall(data)
    dosuniecia =['jquery.','googleapis','googletagmanager','googlecode.','platform.twitter']

    srcs = [el for el in srcs if not any(ignore in el for ignore in dosuniecia)]
    
    
    

    xbmc.log('@#@htmlhtml: %s' % str(srcs), LOGNOTICE)
    
    m3ux=re.findall("""source: atob\(["\'](.+?)["\']""",data,re.DOTALL)
    if m3ux:
        vidurl=base64.b64decode(m3ux[0])
        if six.PY3:
            vidurl = vidurl.decode(encoding='utf-8', errors='strict')
        return vidurl+'|User-Agent'+urllib_parse.quote(UA)+'&Referer='+url
    
    try:

        for query in srcs:    

            query = query.replace('\n','').replace('\r','').replace('\\n','').replace('\\r','')
            if 'livecounter' in query or 'pagead2.google' in query or 'imgur.com' in query or 'platform.twitter' in query or 'googletagmanager.com' in query or 'cloudfront.net/?' in query:
                continue
            if 'jquery-1.6.min.js'in query or 'minilogo.gif' in query or 'getbanner.php' in query or 'top.mail.ru' in query or 'ads.cpxinteractive.com' in query or 'counter.yadro.ru' in query:#
                continue
            if '.png'in query or '.jpg' in query:
                continue

            if 'ripple.is' in query:

                return _rippleis(query,data,url)
        
            if '/embed/' in query and 'exprestream.com' in url:

                return _exprestreamcom(query,data,url)
                
            if './../ss' in query and 'dubs.to' in url:

                return _dubsto(query,data,url)
                
            elif query.startswith ('/live') and 'strumyk.tv' in url:

                return _strimsworld(query,data,url)
            elif 'ufckhabib.com' in query:
                return _ufckhabib    (query,data,url)

            elif 'newdmn.' in query:
                return _newdmn   (query,data,url)  
				
				
            elif 'worlwidestream.' in query:
                return _wigistream   (query,data,url)  	
				
            
            elif 'macron.' in query:
                return _macron    (query,data,url)  
                
            elif 'mygoodstream' in query:
                return _mygoodstream    (query,data,url)
            elif 'streamsport.icu' in query:
                return _streamsport    (query,data,url)

            elif 'capodeportes.'  in query:
                return _capodeportes   (query,data,url)  
            elif 'cr7soccer' in query and '.php' in query:
                return _cr7soccer    (query,data,url)
                
            elif 'showsport.xyz' in query:
                return _showsport    (query,data,url)
            elif 'sport-streaming' in query:
                return _sport_streaming    (query,data,url)  
                
            elif 'streammart.' in query:
                return _streammart    (query,data,url)
                
                
            elif 'espn-live.stream' in query:
                return _espn_live    (query,data,url)
                
                
            elif 'castmax.' in query:
                return _castmax    (query,data,url)
            elif 'paheplayer' in query:
                return _paheplayer    (query,data,url)
                
            elif 'mazymedias.com' in query:
                return _mazymedias    (query,data,url)
            elif 'wigistream.' in query:
                return _wigistream    (query,data,url)
            elif 'embedstream.'  in query:
                return _embedstream    (query,data,url)
            elif 'prd.dlive' in query:
                return _dlive    (query,data,url)
#"username": "            
            elif 'telerium.tv' in query or 'telerium.net' in query or 'telerium' in query :
                
                debug('@telerium')

                return _telerium(query,data,url)
                
                
                
            elif 'weakspellz.com' in query:
                return _weakspellzcom(query,data,url)
            elif 'www.dubsstreamz.com' in query:
                return _dubsstreamz(query,data,url)
            elif 'hindimean.com' in query:
                return _hindimean(query,data,url)
            elif 'wiz1.net/' in query:
                debug('@telerium')

                return _wiz1net(query,data,url)
            elif 'givemeredditstreams.' in query:
                debug('@telerium')

                return _givemeredditstreams(query,data,url)    
                
            elif 'givemenbastreams.'    in query:
                debug('@telerium')

                return _givemenbastreams(query,data,url)    
                
                
                
            elif 'vecdn.pw' in query:    
                return _vecdnpw(query,data,url)
                
            elif 'sportz.pw' in query:
                return _sportzpw(query,data,url)
            elif 'streamhd247.live' in query:
                return _streamhd247(query,data,url)
            elif 'limetvv.com' in query:
                return _limetvvcom(query,data,url)
            elif 'sports-stream.link' in query:
                #sports_streamlink
                return _sports_streamlink(query,data,url)
                
            elif 'daddylive'     in query:
                return _daddylive(query,data,url)
                
            elif 'soccerlive.xyz' in query:
                return _soccerlivexyz(query,data,url)
            
            elif 'livesport4u.pw' in query:
                return _livesport4upw(query,data,url)
            
            
            
            elif 'arembed.com' in query:
                return _arembedcom(query,data,url)
            
            #$"http://sportlive.site
            elif 'sportlive.site' in query:
                return _sportlivesite(query,data,url)
                
            elif 'streamcdn.to' in query:
                return _streamcdnto(query,data,url)    
                
            elif 'http://wizhdsports.net' in query:
                return _wizhdsportsnet(query,data,url)    
                
            elif 'flowframes.online' in query:
                return _flowframesonline(query,data,url)

            elif 'strims.tv' in query:
            
                return _strimstv(query,data,url)    


        
            elif 'sportsbay.org' in query:
                return _sportsbayorg(query,data,url)
        
        #    elif '.realstream.' in query:
        #        return _realstream(query,data,url)
        
        
        
            #elif 'crackstreams.com' in query:
            #    return _crackstreamscom(query,data,url)
        
        
            elif 'tvsport.ws' in query:
                return _tvsportws(query,data,url)
            
            elif 'whd365.pro' in query:
                return _whd365pro(query,data,url)    

                
            elif 'olimp-app.ru' in query:
                return _olimpappru(query,data,url)    
            elif 'sport7.biz' in query:
                return _sport7biz(query,data,url)    
                
            #yoursports.stream
            elif 'youtube.com' in query or 'youtu.be' in query:
                return query
                
            elif 'yoursports.stream' in query:
                return _yoursportsstream(query,data,url)
            
            
            elif 'yrsprts.xyz' in query:
                return _yrsprts(query,data,url)

            
            elif 'h247bay.js' in query:
                return _h247bay(query,data,url)
            
            
            
            elif 'soccerlive.uk' in query:
                return _soccerliveuk(query,data,url)        
                
                
            elif 'wstream.to' in query:
                return _wstreamto(query,data,url)
        
                

            elif 'hazmolive.stream' in query:
                return _hazmostream(query,data,url)
            elif 'hazmo.stream' in query:
                return _hazmostream2(query,data,url)
    
            elif 'soccershow.xyz' in query:
                return _hdstreamsclub2(query,data,url)
        
            elif 'hdstreams.club/page' in query:
                return _hdstreamsclub2(query,data,url)
    
            elif 'streamcdn.co' in query:
                return _streamcdnco(query,data,url)
                
            elif 'studiojunction.live' in query:
                return _studiojunctionlive(query,data,url)
        
            elif 'dailyhealthandcare.com' in query:
                return _dailyhealthandcare(query,data,url)
        
        
            elif '7streams.pro' in query:
                return _7streamspro(query,data,url)
        
        
            elif 'strimstv.eu' in query:
                return _strimstveu(query,data,url)
                
            elif 'bnk.sportz.is' in query:
                return _bnksportzis(query,data,url)
                
            elif 'sdfgdf.xyz' in query:

                return _sdfgdfxyz(query,data,url)            
                
            elif 'bfst.to' in query:

                return _bfstto(query,data,url)                    
            elif 'vsdea.me' in query:

                return _vsdeame(query,data,url)

                
            elif 'twojetv.ws' in query:
                debug('@@aliez')
                return _twojetv(query,data,url)    
                
            elif 'bankai.stream' in query:
                debug('@@aliez')
                return _bankaistream(query,data,url)                    
            elif 'aliez.me' in query:
                debug('@@aliez')
                return _aliezme(query,data,url)                
            elif '1me.club' in url:
                return _1meclub(data,url)    
            
            elif 'pcast.pw/static/embed' in query:
                return _pcastpw(query,data,url)    
            
            elif 'sports-stream.net/ch/sps.php' in query:
                return _sportsstreamnet(query,data,url)    
                
            elif 'sportzonline.pw' in query:
                return _sportzonlinepw(query,data,url)    

            elif 'sportzonline' in query:
                return _sportzonlinepw(query,data,url)    

                
            elif 'tumarcador.xyz' in query:
                return _tumarcadorxyz(query,data,url)    

                
            elif 'realcam.pw/embed' in query:
                return _realcampw(query,data,url)                
                            
            elif 'livesport4u.com' in query:
                return _livesport4ucom(query,data,url)
                
            elif 'nowlive.pro' in query:
                return _nowlivepro(query,data,url)                    
                
            elif 'streamup.me/livetv/' in query:
                return _streamupme(query,data,url)                
                
            elif 'hdstreams.club/page' in url:
                return _hdstreamsclub(data,url)
                            
            elif 'bonstreams.net/footstream/hd.php' in url:
                return _bonstreams(data,url)
                
            elif 'whostreams' in query:
                return _whostreams(query,data,url)
        
            elif 'ucasterplayer.com/static/scripts/hucaster' in query:
                return _ucasterplayer(query,data,url)    
            
            
            elif 'webtv.ws' in query:
                return _webtv(query,data,url)
            elif 'www.wlive.tv/embed' in query:
                return _wlivetv(query,data,url)
                
            elif 'assia.tv' in query or 'assia1.' in query:

                return _assiatv(query,data,url)                

            elif 'assia' in query:

                return _assiatv(query,data,url)  
            elif 'sawlive.tv' in url:
                return _sawlivetv2(query,data,url)                
                            
            elif 'hdcast.me/' in query:
                return _hdcastme(query,data,url)    

            elif 'fstream.me' in query:
                return _fstreamme(query,data,url)
            

            elif 'sportbar.biz' in query:
                return _sportbarbiz(query,data,url)
            
            
            elif 'watch.sporcanli' in query:
                return _watchsporcanli(query,data,url)
            
            
            elif '.playerfs.com' in query:
                return _playerfscom(query,data,url)
            
            elif 'embed.pot-iptv' in query:
                debug('@embed.pot-iptv')
                return _embedpot_iptv(query,data,url)
            elif 'vvcast' in query:
                debug('@vvcast')
                return _vvcast(query,data,url)
            elif 'tvp.pl/sess/tvplayer.php' in query:
                debug('@tvp.pl tvplayer')
                return _tvpPlayer(query,data,url)
            elif 'byetv' in query:
                debug('@byetv')
                return _byetv(query,data,url)
            elif 'veecast' in query:
                debug('@veecast')
                return _veecast(query,data,url)
            elif 'srkcast' in query:
                debug('@_srkcast')
                return _srkcast(query,data,url)
            elif 'sharecast' in query:
                debug('@_sharecast')
                return _sharecast(query,data,url)
            elif 'lima-city.de' in query:
                debug('@_lima-city.de')
                return _limacity(query,data,url)
            elif 'ustream.tv' in query:
                debug('@_ustream.tv')
                return _ustream(query,data,url)
            elif 'ustreamix.com' in query or 'ustreamyx' in query:
                debug('@_ustreamix.com')
                return _ustreamix(query,data,url)
            elif 'dailymotion.com' in query:
                debug('@dailymotion.com')
                return _dailymotion(query,data,url)
            elif 'www.jazztv.co' in query:
                debug('@jazztv.co')
                return _jazztv(query,data,url)
            elif 'urhd.tv' in query:
                debug('@urhd.tv')
                return _urhdtv(query,data,url)
            elif 'tv.jardello.com' in query:
                debug('@tv.jardello.com')
                return _jardello(query,data,url)
            elif 'cricfree.sc' in query:
                debug('@cricfree.sc')
                return _cricfree(query,data,url)
            elif 'static.nowlive.club' in query:
                debug('@static.nowlive.club')
                return _staticnowliveclub(query,data,url)
            elif 'abcast.net' in query:
                debug('@abcast.net')
                return _abcastnet(query,data,url)
            elif 'freelive365.com' in query:
                debug('@freelive365.com')
                return _freelive365(query,data,url)
            elif 'cast4u.tv' in query:
                debug('@cast4u.tv')
                return _cast4utv(query,data,url)
            elif 'osgchmura.tk' in query:
                debug('@osgchmura')
                return _osgchmura(query,data,url)
            elif 'static.u-pro.fr' in query:
                debug('@static.u-pro.fr')
                return _staticu_profr(query,data,url)
            elif 'widestream.io' in query:
                debug('@@widestream.io')
                return _widestream(query,data,url)
            elif 'static.nowlive.xyz' in query:
                debug('@@static.nowlive')
                return _staticnowlive(query,data,url)
            elif 'delta-live.pro' in query:
                debug('@@delta-live.pro')
                return _deltalivepro(query,data,url)
            elif 'openlive.org' in query:
                debug('@@openlive.org')
                return _openliveorg(query,data,url)
            elif 'sawlive.tv' in query:
                debug('@@sawlive.tv' )

                return _sawlivetv(query,data,url)
            elif 'pxstream.tv' in query:
                debug('@@pxstream')
                return _pxstream(query,data,url)
            elif 'myfreshinfo' in query:
                debug('@@myfreshinfo')
                return _myfreshinfo(query,data,url)
            elif 'cinema-tv.xyz' in query:
                debug('@@cinema-tv.xyz')
                return _cinematvxyz(query,data,url)
            elif 'flowplayer' in query:
                debug('@@flowplayer')
                return _flowplayer(query,data,url)
            elif 'shidurlive' in query:
                debug('@@shidurlive')
                return _shidurlive(query,data,url)
            elif 'freedocast' in query:
                debug('@@freedocast')
                return _freedocast(query,data,url)
            elif 'tvope' in query:
                debug('@@tvope')
                return _tvope(query,data,url)
            elif 'dotstream.tv' in query:
                debug('@@dotstream')
                return _dotstream(query,data,url)
            elif 'bro.adca.st' in query:
                debug('@@bro.adca.st')
                return _broadcast(query,data,url)
            elif 'jwpsrv.com' in query:
                debug('@@jwpsrv')
                return _jwpsrv(query,data)
            elif 'jwpcdn.com' in query:
                debug('@@jwpcdn')
                return _jwpcdn(query,data,url)        

            elif 'ustream' in query:
                debug('@@ustream')
                return _ustream(query,data)
            elif 'castto.me' in query:
                debug('@@castto')
                return _casttome(query,url,data)
            elif 'privatestream' in query:
                debug('@@privatestream')
                return _privatestream(query,data)
            elif 'sebnsc.club' in url:
                return _sebnsc(url,data,url)
                
            #elif 'bfst.to' in url:
            #    query=url
            #    return _bfstto(query,data,url)    
                
            else:
                if 'http' in query and 'm3u' in query:
                    return 'http'+query.split('http')[-1]
    except:
        pass
    if 'player.cloud.wowza.com' in data:
        return _playercloudwowza(data,url)
    elif 'youtube' in url:
        return _youtube(url)    
    return None
	
def worlwidestream   (query,data,url)  :
	headers = {'User-Agent': UA,'Referer': url}    
	
	contentVideo=getUrl(query,header=headers)
	if six.PY3:
		contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

	html=contentVideo.replace("\'",'"')
	packeds = packer.findall(contentVideo)#[0]
	
	unpacked=contentVideo
	for packed in packeds:
	
		unpacked += jsunpack.unpack(packed)
	
	
	c=''
def _newdmn   (query,data,url)  :
    query = query.replace('newdmn.icu','lowend.xyz')
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    video_url = clappr.findall(html)
    clappr2='new\s+Clappr\.Player\(.*?{.*?source:\s*?["\'](.+?)["\']'
    video_url2 = re.findall(clappr2,html,re.DOTALL)

    if video_url or video_url2:
        video_url = video_url[0] if video_url else video_url2[0]

    if video_url:

        video_url = 'https:'+video_url if video_url.startswith('//') else video_url
        video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)
        vido_url = video_url
    return vido_url 
def _macron    (query,data,url)  :
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    
    
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,html)
    return vido_url 
def _sport_streaming    (query,data,url) :
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    
    
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,html)
    return vido_url 
def _capodeportes   (query,data,url)  :
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,html)
    return vido_url 

def _showsport    (query,data,url):
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

    html=contentVideo.replace("\'",'"')

    
def _ufckhabib    (query,data,url):
    
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    
    
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    
    html=contentVideo.replace("\'",'"')
    atob = re.findall('window.atob\("([^"]+)"',html,re.DOTALL)#[0]
    if atob:
        vidurl=base64.b64decode(atob[0])
        if six.PY3:
            vidurl = vidurl.decode(encoding='utf-8', errors='strict')
        return vidurl+'|User-Agent'+urllib_parse.quote(UA)+'&Referer='+query
    else:
        vido_url=decode(query,html)
        return vido_url 
def _espn_live    (query,data,url):
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

    html=contentVideo.replace("\'",'"')
    video_url = clappr.findall(html)
    clappr2='new\s+Clappr\.Player\(.*?{.*?source:\s*?["\'](.+?)["\']'
    video_url2 = re.findall(clappr2,html,re.DOTALL)

    if video_url or video_url2:
        video_url = video_url[0] if video_url else video_url2[0]

    if video_url:

        video_url = 'https:'+video_url if video_url.startswith('//') else video_url
        video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)
        vido_url = video_url
    return vido_url 
def _streammart    (query,data,url):
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

    html=contentVideo.replace("\'",'"')
    packed = packer.findall(contentVideo)[0]

    unpacked = jsunpack.unpack(packed)

    video_url = clappr.findall(unpacked)#[0]
    video_ur2 = source.findall(unpacked)#[0]

    if video_url or video_url2:
        video_url = video_url[0] if video_url else video_url2[0]
        video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)
    
    return video_url
    
def _cr7soccer    (query,data,url):
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    
    
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

    html=contentVideo.replace("\'",'"')
    vido_url=decode(url,html)
    return vido_url 
def _streamsport    (query,data,url):
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

    html=contentVideo.replace("\'",'"')
    video_url = clappr.findall(html)
    clappr2='new\s+Clappr\.Player\(.*?{.*?source:\s*?["\'](.+?)["\']'
    video_url2 = re.findall(clappr2,html,re.DOTALL)

    if video_url or video_url2:
        video_url = video_url[0] if video_url else video_url2[0]

    if video_url:

        video_url = 'https:'+video_url if video_url.startswith('//') else video_url
        video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)
        vido_url = video_url
    return vido_url 
  #  a=''
def _sebnsc(url,data,ref):

    nturlx = re.findall('STREAM SOURCE.*?iframe.*?src="(.+?)"', data,re.DOTALL+re.IGNORECASE)[0]
    
    hh=url.split('/')[-1]
    nturl = url.replace(hh,nturlx)
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(nturl,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(url,html)
    return vido_url 
    #a=''

  
def _mygoodstream    (query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
def _castmax    (query,data,url):
    data=data.replace("\'",'"')
    id = re.findall('id="([^"]+)"',data)#[0]

    if id:
        nturl = 'https://castmax.net/embed/'+id[0]+'.html'
    

    else:
        nturl = query
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(nturl,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')

    html=contentVideo.replace("\'",'"')

    a=''
def _givemenbastreams(query,data,url)    :
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    video_url = clappr.findall(html)
    clappr2='new\s+Clappr\.Player\(.*?{.*?source:\s*?["\'](.+?)["\']'
    video_url2 = re.findall(clappr2,html,re.DOTALL)

    if video_url or video_url2:
        video_url = video_url[0] if video_url else video_url2[0]

    if video_url:

        video_url = 'https:'+video_url if video_url.startswith('//') else video_url
        video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)
        vido_url = video_url
    return vido_url 

def _givemeredditstreams(query,data,url)    :
    headers = {'User-Agent': UA,'Referer': url}    
    #query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
  #  if six.PY3:
  #      html = html.decode(encoding='utf-8', errors='strict')
    vido_url=decode(query,html)
    return vido_url 
    
def _dlive    (query,data,url):

    html=data.replace("\'",'"')

    st=re.findall('"username":\s*"(.+?)"',html,re.DOTALL)[0]
    src = "https://live.prd.dlive.tv/hls/live/%s.m3u8"%st
    return src
#"username": "    
def _embedstream    (query,data,url):
    orig = 'https://embedstream.me'
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
       contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    headers = {
        'authority': 'www.plytv.me',
        'cache-control': 'max-age=0',
        'upgrade-insecure-requests': '1',
        'origin': 'https://embedstream.me',
        'content-type': 'application/x-www-form-urlencoded',
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-gpc': '1',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-dest': 'iframe',
        'referer': 'https://embedstream.me/',
        'accept-language': 'en-US,en;q=0.9',
    }

    pdettxt =re.findall('pdettxt\s*=\s*"(.+?)"',html,re.DOTALL)[0]
    zmid=re.findall('zmid\s*=\s*"(.+?)"',html,re.DOTALL)[0]
    edm=re.findall('edm\s*=\s*"(.+?)"',html,re.DOTALL)[0]
    pid = re.findall('pid\s*=\s*(\d+);',html,re.DOTALL)[0]
    
    qbc= 'https://www.tvply.me/'  if 'cdn.tvply.me' in html else'https://www.plytv.me/'
    
    params = (
        ('v', zmid),
    )
    
    data = {
    'pid': (str(pid)),
    'ptxt': pdettxt
    }
#urlk

    urlk = 'https://%s/sdembed'%(edm)+'?v='+str(zmid)
    response_content = sess.post('https://%s/sdembed'%(edm), headers=headers, params=params, data=data,verify=False).content

    if six.PY3:
        response_content = response_content.decode(encoding='utf-8', errors='strict')
    #qbc= 'https://www.plytv.me/'

   # response_content=response_content.replace("\'",'"')
    
    
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
        
#        thread = threading.Thread(name='authcheck', target=authcheck, args=[tit, strName, scode, expires])
#        thread.setDaemon(True)
#        thread.start()
    #    strName, scode, expires
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
    
    
        stream ='http://127.0.0.1:%s/dd='%(str(proxyport))+video_url
    
    
    
    
    
    
    
    
    
#    if 'function(h,u,n,t,e,r)' in response_content or 't,e,r' in response_content:
#        import dehunt as dhtr
#       # ff=re.findall('function\(h,u,n,t,e,r\).*?}\((".+?)\)\)',response_content,re.DOTALL)[0]#.spli74
#        ff=re.findall(',e,r\).*?}\((".+?)\)\)',response_content,re.DOTALL)[0]#.spli
#        ff=ff.replace('"','')
#        h, u, n, t, e, r = ff.split(',')
#        
#        cc = dhtr.dehunt (h, int(u), n, int(t), int(e), int(r))
#        cc=cc.replace("\'",'"')
#
#    fil = re.findall('file:\s*window\.atob\((.+?)\)',cc,re.DOTALL)[0]
#
#    src = re.findall(fil+'\s*=\s*"(.+?)"',cc,re.DOTALL)[0]
#    video_url = base64.b64decode(src)#[0]
#    if six.PY3:
#        video_url = video_url.decode(encoding='utf-8', errors='strict')
#    UAb= 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Safari/537.36'
#
#    qbc= 'https://www.plytv.me/'
#    video_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UAb, ref=qbc)
#

    return stream

def _plytv    (query,url,orig):
    video_url=''
    err=None
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
       contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    url = 'https://www.tvply.me/sdembed' if 'cdn.tvply.me' in html else 'https://www.plytv.me/sdembed'
    qbc= 'https://www.tvply.me/'  if 'cdn.tvply.me' in html else'https://www.plytv.me/'
    headers = {
       # 'authority': 'www.plytv.me',
        'cache-control': 'max-age=0',
        'upgrade-insecure-requests': '1',
        'origin': orig,
        'content-type': 'application/x-www-form-urlencoded',
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-gpc': '1',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-dest': 'iframe',
        'referer': query,
        'accept-language': 'en-US,en;q=0.9',
    }

    pdettxt =re.findall('pdettxt\s*=\s*"(.+?)"',html,re.DOTALL)[0]
    zmid=re.findall('zmid\s*=\s*"(.+?)"',html,re.DOTALL)[0]
    edm=re.findall('edm\s*=\s*"(.+?)"',html,re.DOTALL)[0]
    pid = re.findall('pid\s*=\s*(\d+);',html,re.DOTALL)[0]
    

    
    params = (
        ('v', zmid),
    )
    
    data = {
    'pid': (str(pid)),
    'ptxt': pdettxt
    }
    
    response_content = sess.post(url, headers=headers, params=params, data=data,verify=False).content

    if six.PY3:
        response_content = response_content.decode(encoding='utf-8', errors='strict')
    

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
        UAb= 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Safari/537.36'
    
      #  qbc= 'https://www.plytv.me/'
        video_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UAb, ref=qbc)

    else:
        err='The stream will start soon. Please check again after a moment'
    return video_url,err
    
    
def derot(hset,xset,key,src):
    #url=re.findall('src="(http://s1.medianetworkinternational.com/js/[A-z0-9]{32}.js)',data2)[-2]
    #  xbmc.log('@#@CHANNEL-VIDEO-LINK: %s' % str(url), LOGNOTICE)
    #url=re.findall('src="(.+?.js\?\d+)"',data2)[0]
    #html=requests.get(url).content
    ##xset=eval(re.findall('xset=(\[.+?\])',html)[0])
    #
    #xset=re.findall("""xset\=Array\[['"]from['"]\]\(['"](.+?)['"]\)""",html)[0]
    #
    #
    #hset=re.findall("""hset\=Array\[['"]from['"]\]\(['"](.+?)['"]\)""",html)[0]
    #hset=eval(re.findall('hset=(\[.+?\])',html)[0])
    import string
    o=''
    u=''
    il=0

    for first in hset:
        u+=first
        o+=xset[il]    
        il+=1
    rot13=string.maketrans(o,u)

    try:
        link=string.translate(src, rot13)
    except:
        o=0
        for i in range(len(hset)):
            a1=xset[o]
            a2=hset[o]
            src=src.replace(xset[o],hset[o])
            o+=1
        link=src

    from binascii import unhexlify, hexlify
    import pyaes

    msg = unhexlify(link)
    key = key[:32]
    #if len(key) != 32: return out
    
    decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationECB(key))
    plain_text = decrypter.feed(msg)
    plain_text += decrypter.feed()
    
    src = plain_text.decode('hex')

    return src

def _realstream(query,data,url):

    headers = {'User-Agent': UA,'Referer': url}    
    #query = 'https:'+query if query.startswith('//') else query
    contentVideo=sess.get(query,headers=headers, verify=False).content
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    #if six.PY3:
    #   html = html.decode(encoding='utf-8', errors='strict')
    iframe = re.findall("""iframe.*?src\s*=\s*['"](.+?)['"]""",html)[0]
    headers = {'User-Agent': UA,'Referer': query}    
    contentVideo=sess.get(iframe,headers=headers, verify=False).content
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    
    post = {k: v for k, v in re.findall('<input type="hidden" name="([^"]+)" value="([^"]+)">', html)}
    action = re.findall("""action['"]\,\s*['"](.+?)['"]""", html,re.DOTALL)
    payload = urllib_parse.urlencode(post)
    

    html = sess.post(action[0], data=post, verify=False).content
    
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    
    sc=''.join(['%s=%s;'%(c.name, c.value) for c in sess.cookies])
#    #data2, c = getUrlc(action[0], payload, header=header, usecookies=True)
    hdrs= 'User-Agent=%s&Referer=%s&Cookie=%s' % (urllib_parse.quote(UA), urllib_parse.quote('http://h5.adshell.net/peer5'), urllib_parse.quote(sc))
    data2 = html
    data = re.findall("function\(\)\s*{\s*[a-z0-9]{43}\(.*?,.*?,\s*'([^']+)'", data2)[0]

#    import getkeyOK as GK

#    hset,xset, stri, stri2 = GK.getkey()
#    mainkey=stri
#    ivkey=stri2
#    keyiv = mainkey.split('|')
#    try:
#        key = keyiv[0]
#        iv = keyiv[0]        
#    except:
#        key = keyiv#[0]
#        iv =''
#    key = key[:32]
    
    
    
    
    
    
    
    
    html = html.replace("\'",'"')

    vidjs = re.findall("""videojs\(['"](.+?)['"]""",html,re.DOTALL)[0]
    strim = re.findall("""%s['"]\,\s*['"](.+?)['"]"""%(vidjs),html,re.DOTALL)[0]
    
    
    hset = u'21c5e76d80a3b9f4'
    il = 0
    key = '2QO0dhFhpMsnNzpFkdhuxuMQgOlQCfwg'
    o = ''
    src = 'MywLTLuMyhrtVynPLTzMPxLzVhHHLhrTwxHuTnTMVPzhVPTxyHhxuPrwxxxhMPTVVwrLxThuxtWnyrPWrHMtMyryPPuwLhPMwnHxxyLnnztPtynuWtrPyLTxPxrPHnPLxVVWxnWuPtWxMPxunTwxhxLuxTPhLTTzhthwHTtrMuhWhxMytwVMunMxMwhVrwrPyzPnnnHWhztPHxHyWwxVHrxxHTnLWzHWTrhtnnzyPHxnzxtWzPyHtVxMWztuhWHhHnMxnHwzrMnxrWuznhPwxPuWMxxMuxVzTnWMHyWxxnyMPyMuzPztxMVxLhwWtWtHLthyHtrMzMThyxWhtVWwzttVrywPrWzTVwWWyMMHLuPyMxLHruxLnrzMuMrutxutzxWhVuVtzThMVPVxPwPPtnnhLhhhtMtPwhwThHwyWLVPrxntWWPMuLTrzyzrHzrMzwMTzwttTMHzMxWhtuyhTMPwwwWVyhuhLyxzVMytrxtnrzLwzHLwrHPnTWznwrnhrruLMMwTLHTunMLMPutyPynhxryhwMHnMyyhzLThhTtPMzTrVzznMnyhTMnPHuxxxHhrLzxtwVhhnuTyyrMWHnVWyyuWHVLHPxHnMtrHwxhMwPLtHzyuWWrtxWrTPwPzPurrPrPxtrytzuVxrunuuxnVhzxhHLhThVWxuThnLhPwtPnynVtLMLMWyPVyhzyyWuywVzrWzntwxTuLnWyzhLzyTVuhPWhnnrWuHWhnyzVLuLyVuxxtVnywwVtxWVHLxWyyHrWhMMWtWHMzLyLLnVxyVHrTtrMHxnHPTrzxhtWTTzLLVhVLrhruMhrwyVHnhtwtTthMzMuHVWzPVuwHnutrLyPuzHVzMxPwLLuwrnxrMxHwHHhWTVTTrTTzyMThxuxrPhTuxxhnWzuzMLLwHxWMHMMtwrnHTPuMrwHnVVhxVuHPVtwVTVzVxTurrwVxVWwzPxMxzxzTTMHrLxywrLyWwunrwLWTrhTywLtVrLywWxwryhyVTWzhzyhtLVnrzHTTxVWHtuTMHynVTLnuxwnzwTVVWLhuLtTuPuzMTMwPyyyynTLnMtWWxHLWwruM'
    
    xset = u'TxuHWrntMLzVwyPh'
    
    
    
    
    data=derot(hset,xset,key,strim)
    stream_url = data.replace('/i', '/index.m3u8') if data.endswith('/i') else data
    return stream_url
    
    
    
#    my_addon.setSetting('hset',hset)
#    my_addon.setSetting('xset',xset)
#    my_addon.setSetting('mainkey',stri)
#    my_addon.setSetting('ivkey',stri2)
#    

#    import sport365 as sp365
#    url=sp365.geturlnew(stri,data,data2)
    
    
    
    
    
    
    av=''
    
def espnstreamget2(scrip,chno):
    import datetime
    try:
        import pytz
    except:
        pass

    my_ct1 = datetime.datetime.now(tz=pytz.UTC)+datetime.timedelta(hours=2)
    my_ct2 = datetime.datetime.now(tz=pytz.UTC)+datetime.timedelta(hours=-1)#datetime.timedelta(hours=2)
    readable1 = my_ct1.strftime('%Y%m%dT%H0000Z')
    readable2 = my_ct2.strftime('%Y%m%dT%H0000Z')

    dash = re.findall("""\[['"]dash['"]\]\s*=\s*['"](.+?)['"]""",scrip)[0]
   # tt=re.findall("""\[['"]i['"]\]\s*=\s*(0[xX][0-9a-fA-F]+)""",scrip)[0]
    
   # tt=str(int(tt,16))
    mpd='https:'+dash+str(chno)+'/'+readable2+'/'+readable1+'.mpd'
    licurl=re.findall("""\[['"]LA_URL['"]\]\s*=\s*['"](.+?)['"]""",scrip)
    lic_url=''
    for lic in licurl:
        if not 'playready' in lic:
        
            lic_url = 'https:'+lic
            break
        
    #xbmc.log('@#@scripscripscripscripscripscrip: %s' % str(scrip), LOGNOTICE)
    env = re.findall("""\[['"]env['"]\]\s*=\s*['"](.+?)['"]""",scrip)
    if env:
        env = env[0]
    else:
        env_var=re.findall("""\[['"]env['"]\]\s*=\s*_0[xX][0-9a-fA-F]+(\[.+?\])""",scrip)[0]
        env = re.findall("""%s\s*=\s*['"](.+?)['"]"""%(env_var.replace('[','\[').replace(']','\]')),scrip)[0]
   # user_id = re.findall("""\[['"]user_id['"]\]\s*=\s*['"](.+?)['"]""",scrip)    
    #if user_id:
   #     user_id = user_id[0]
   # else:
   #     user_id_var=re.findall("""\[['"]user_id['"]\]\s*=\s*_0[xX][0-9a-fA-F]+(\[.+?\])""",scrip)[0]
    #    user_id = re.findall("""%s\s*=\s*['"](.+?)['"]"""%(user_id_var.replace('[','\[').replace(']','\]')),scrip)[0]
#
    #channel_id = re.findall("""\[['"]channel_id['"]\]\s*=\s*['"](.+?)['"]""",scrip)    
    #if channel_id:
   #     channel_id = channel_id[0]
    #else:
        #user_id_var=re.findall("""\[['"]user_id['"]\]\s*=\s*_0[xX][0-9a-fA-F]+(\[.+?\])""",scrip)[0]
        #user_id = re.findall("""%s\s*=\s*['"](.+?)['"]"""%(user_id_var.replace('[','\[').replace(']','\]')),scrip)[0]
        
        
        
        
     #   channel_id_var=re.findall("""\[['"]channel_id['"]\]\s*=\s*_0[xX][0-9a-fA-F]+(\[.+?\])""",scrip)[0]



    #    channel_id = re.findall("""%s\s*=\s*['"](.+?)['"]"""%(channel_id_var.replace('[','\[').replace(']','\]')),scrip)[0]
    data = '{"env":"'+env+'","message":"b{SSM}"}'    #message":"CAQ="  
    
    a=''
    return mpd, lic_url,data
    
    
def espnstreamget(scrip):
    import datetime
    try:
        import pytz
    except:
        pass

    my_ct1 = datetime.datetime.now(tz=pytz.UTC)+datetime.timedelta(hours=2)
    my_ct2 = datetime.datetime.now(tz=pytz.UTC)+datetime.timedelta(hours=-1)#datetime.timedelta(hours=2)
    readable1 = my_ct1.strftime('%Y%m%dT%H0000Z')
    readable2 = my_ct2.strftime('%Y%m%dT%H0000Z')

    dash = re.findall("""\[['"]dash['"]\]\s*=\s*['"](.+?)['"]""",scrip)[0]
    tt=re.findall("""\[['"]i['"]\]\s*=\s*(0[xX][0-9a-fA-F]+)""",scrip)[0]
    
    tt=str(int(tt,16))
    mpd='https:'+dash+tt+'/'+readable2+'/'+readable1+'.mpd'
    licurl=re.findall("""\[['"]LA_URL['"]\]\s*=\s*['"](.+?)['"]""",scrip)
    lic_url=''
    for lic in licurl:
        if 'widev' in lic:
            lic_url = 'https:'+lic
            break
        
    #xbmc.log('@#@scripscripscripscripscripscrip: %s' % str(scrip), LOGNOTICE)
    env = re.findall("""\[['"]env['"]\]\s*=\s*['"](.+?)['"]""",scrip)
    if env:
        env = env[0]
    else:
        env_var=re.findall("""\[['"]env['"]\]\s*=\s*_0[xX][0-9a-fA-F]+(\[.+?\])""",scrip)[0]
        env = re.findall("""%s\s*=\s*['"](.+?)['"]"""%(env_var.replace('[','\[').replace(']','\]')),scrip)[0]
    user_id = re.findall("""\[['"]user_id['"]\]\s*=\s*['"](.+?)['"]""",scrip)    
    if user_id:
        user_id = user_id[0]
    else:
        user_id_var=re.findall("""\[['"]user_id['"]\]\s*=\s*_0[xX][0-9a-fA-F]+(\[.+?\])""",scrip)[0]
        user_id = re.findall("""%s\s*=\s*['"](.+?)['"]"""%(user_id_var.replace('[','\[').replace(']','\]')),scrip)[0]

    channel_id = re.findall("""\[['"]channel_id['"]\]\s*=\s*['"](.+?)['"]""",scrip)    
    if channel_id:
        channel_id = channel_id[0]
    else:
        #user_id_var=re.findall("""\[['"]user_id['"]\]\s*=\s*_0[xX][0-9a-fA-F]+(\[.+?\])""",scrip)[0]
        #user_id = re.findall("""%s\s*=\s*['"](.+?)['"]"""%(user_id_var.replace('[','\[').replace(']','\]')),scrip)[0]
        
        
        
        
        channel_id_var=re.findall("""\[['"]channel_id['"]\]\s*=\s*_0[xX][0-9a-fA-F]+(\[.+?\])""",scrip)[0]



        channel_id = re.findall("""%s\s*=\s*['"](.+?)['"]"""%(channel_id_var.replace('[','\[').replace(']','\]')),scrip)[0]
    data = '{"env":"'+env+'","user_id":"'+user_id+'","channel_id":"'+channel_id+'","message":"b{SSM}"}'    #message":"CAQ="  
    
    a=''
    return mpd, lic_url,data
def _vecdnpw(query,data,url):

    headers = {'User-Agent': UA,'Referer': url}    
    #query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)

    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,html)
    return vido_url 
    
def _mazymedias    (query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    video_url = clappr.findall(html)
    clappr2='new\s+Clappr\.Player\(.*?{.*?source:\s*?["\'](.+?)["\']'
    video_url2 = re.findall(clappr2,html,re.DOTALL)


    if video_url or video_url2:
        video_url = video_url[0] if video_url else video_url2[0]

    if video_url:

        video_url = 'https:'+video_url if video_url.startswith('//') else video_url
        video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)
        vido_url = video_url
    
    return vido_url 

def _daddylive(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    #query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,html)
    return vido_url 
    
    
def _wigistream(query,data,url):
	if 'daddylive' in url:
		url = 'https://daddylive.co/'
	headers = {'User-Agent': UA,'Referer': url}    
	video_url=''
	contentVideo=getUrl(query,header=headers)
	if six.PY3:
		contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
	
	packeds = packer.findall(contentVideo)#[0]
	unpacked=contentVideo
	for packed in packeds:
	
		unpacked += jsunpack.unpack(packed)
	
	video_url = clappr.findall(unpacked)
	video_url2 = source.findall(unpacked)
	
	video_url3 = re.findall("""new\s+Clappr\.Player\(.*?source\s* :\s*['"](.+?)['"]""",unpacked,re.DOTALL)
	
	
	video_url4 = re.findall("""else\{src\=['"](.+?)['"]""",unpacked,re.DOTALL)
	if video_url:
		video_url = video_url[0]
	elif video_url2:
		video_url = video_url2[0]
	elif video_url3:
		video_url = video_url3[0]
	elif video_url4:
		video_url = video_url4[0]
	
	if video_url:
	
		video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)
	
	return video_url
def _paheplayer    (query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,html)
    return vido_url
    
def _strimsworld(query,data,url):

    if not 'strumyk.tv' in query:
        headers = {'User-Agent': UA,'Referer': url}    
        query = 'http://strumyk.tv' + query
        contentVideo=getUrl(query,header=headers)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        video_url=''
        vido_url=''
    
        html=contentVideo.replace("\'",'"')
    else:
        html = data
        

    if 'eval(unescape' in html:
        html    =  urllib_parse.unquote(re.findall("""unescape\(['"](.+?)['"]""",html)[0])
        video_url = clappr.findall(html)#[0]source:"
        clappr2 = re.compile('new\s+Clappr\.Player\(\{\\\\nsource:\s*?["\'](.+?)["\']')
        video_url2 = clappr2.findall(html)

        if video_url or video_url2:
            video_url = video_url[0] if video_url else video_url2[0]

        if video_url:
            video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)
            vido_url = video_url
    if not video_url:
        html = html.replace("\\'",'"')

        vido_url=decode(query,html)
    return vido_url 
    
    
def _playerfscom(query,data,url):

    chang=re.findall('channel\="(.+?)"\,\s*g\="(.+?)"',data)[0]

    newurl = 'https://www.playerfs.com/hembedplayer/%s/%s/720/480'%(str(chang[0]),str(chang[1]))
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(newurl,header=headers) 
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    balurl=re.findall('ajax\(\{ur\l:\s*"(.+?)"\s*\+\s*(\d+)',html)[0]
    bal_url=balurl[0]+balurl[1]
    headers = {'User-Agent': UA,'Referer': 'https://www.playerfs.com/'}    
    contentVideo=getUrl(bal_url,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    ea = contentVideo.split('=')[1]
    urlpart2 = re.findall('hlsurl\s*\=\s*".+?".+?"(.+?)"',html,re.I)[0]
    urlpart3 = re.findall('enableVideo\("([^"]+)',html)[0]
    mainurl = 'https://'+ea+urlpart2+urlpart3

    return mainurl+'|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref='https://www.playerfs.com/')
def _streamhd247(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    #query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    
    
    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,html)
    return vido_url 
def  _sportzpw(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    #query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,html)
    return vido_url 
    
def _limetvvcom(query,data,url):

    id = re.findall('>fid="([^"]+)"',data)#[0]
    if id:
        url = 'https://www.limetvv.com/embeddx.php?live=%s&vw=700&vh=440'%id[0]
    else:
        url = query
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(url,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    video_url=''
    try:
        video_url = re.findall('{source:([^:]+)}',html)[0]
    except:
        video_url = re.findall('source:\s*"([^"]+)"',html)[0]
    if video_url:
        video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    
        
    return video_url
    
    
    
    #vido_url=decode(url,html)
    #return vido_url 
def _hindimean(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    #query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,html)
    return vido_url 
    
def _sports_streamlink(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    #query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,html)
    return vido_url 
    

def _wizhdsportsnet(query,data,url)    :
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    src= re.findall("""iframe\s*src\s*=\s*['"](.+?)['"]""",contentVideo)
    src = src[0] if src else ''
    headers = {'User-Agent': UA,'Referer': query}    
    src = 'https:'+src if src.startswith('//') else src
    contentVideo=getUrl(src,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,html)
    return vido_url 
    
    
def _watchsporcanli(query,data,url):    
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)  
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,html)
    return vido_url 

    #vid_url = re.findall("""videoLink\s*=\s['"](.+?)['"]""",html)[0]
    #vid_url= 'https:'+vid_url if vid_url.startswith('//') else vid_url
    #vid_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    
    #
    #return vid_url    
def getsportba(iframe,url)    :
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(iframe,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    
    
    contentVideo = contentVideo.replace("\'",'"')
    src= re.findall("""videoLink = ['"](.+?)['"]""",contentVideo)
    src = src[0]+'|auth=SSL/TLS&verifypeer=false&User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=url) if src else ''
    return src
def _streamcdnto(query,data,url):
    video_url=''

    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    packed = packer.findall(contentVideo)[0]
    unpacked = jsunpack.unpack(packed)

    try:
        video_url = clappr.findall(unpacked)[0]
    except:
        video_url = source.findall(unpacked)[0]
    if video_url:
        video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    
        
    return video_url
    
def getDecodeSaw(content):
    try:
        mainsaw='http://www.sawlive.tv/embed/stream/'
    
        var = re.compile("""var\s+\w+\s+=\s*['"](.*?)['"]""").findall(content) #[0][1]
        #print var
    
        vars=var[0].split(';')
        var1=vars[0]
        var2=vars[1]
        dec= mainsaw+var2+'/'+var1
    except:
        dec = re.compile('"text/javascript"\s+src="(.*?)"').findall(content)[0]
    return dec
    
def _sawlivetv2(url,ref):

    video_url=''
    headers = {
    'User-Agent': UA,
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
    #    print i
        try: unpacked += jsunpack.unpack(i)
        except: pass
    result += unpacked

    war,dd=re.findall('var (\w+)\s*=\s*"(.+?)"',result)[0]
    dd1=dd.split(';')
    war2 = re.findall('var (\w+)\s*=\s*%s'%war,result)[0]
    jed,dwa = re.findall("""\+%s\[(\d+)\]\+"""%(war2),result)#    re.findall('%s\[(\d+)\]\+\\'\/\\'+')
    url='http://www.sawlive.tv/embedm/stream/'+dd1[int(jed)]+'/'+dd1[int(dwa)]
    result = requests.get(url,headers=headers,verify=False).text
    
    
#    headers = {
#    'Host': 'www.sawlive.tv',
#    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
#    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
#    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
#    'DNT': '1',
#    'Referer': 'http://www.wiz1.net/',
#    'Upgrade-Insecure-Requests': '1',
#}
    
    
    str_url = "".join("".join(chr(int(x))) for x in re.findall('var \w+ = \[(.+?)\]',result)[0].split(','))
    return str_url+'|User-Agent'+urllib_parse.quote(UA)+'&Referer='+url
    
#    result = urllib.unquote_plus(result).decode('string_escape')#.replace("\'",'"')
#    gribs=re.findall('gribs="(.+?)"',result)#[-1]
#    if not gribs:
#        #xbmcgui.Dialog().ok('[COLOR red]Problem[/COLOR]','Stream offline')    
#        return
#    else:
#        gribs=gribs[-1]
#    
#    liczby=re.findall('=([^=]+)\sunescape\(qaz\)',result)[0]
#    li=re.findall('var '+liczby+'\= (.+?)\s+(.+?)\s+(.+?);',result)[0]
#    kod=0
#    for lk in li:
#        try:
#            sut=re.findall('var '+lk+'\=(\d+);',result)[0]
#            kod+=int(sut)
#        except:
#            continue
#
#    has=re.findall("\(qaz\)\s+'(.+?)';",result)[-1].replace(zmiana,'M')
#    rss=re.findall('rsss\s+=\s+"(.+?)"',result,re.DOTALL)[-1]
#    usa=urllib.quote(UAX)
#    dal=str(kod)+'?'+has+rss 
#    swfUrl='http://static3.sawlive.tv/player.swf'
#    url2='%s playpath=%s swfUrl=%s pageUrl=%s live=1 swfVfy=1'%(gribs,dal,swfUrl,url)
#    return url2    
    
def _wiz1net(query,data,url):
    video_url=''

    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    nexturl2 = re.compile('"iframe"\s+src="(.*?)"').findall(contentVideo)[0]
    headers = {'User-Agent': UA,'Referer': query}    
    contentVideo=getUrl(nexturl2 ,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    decSawUrl=getDecodeSaw(contentVideo)

    str=    _sawlivetv2(decSawUrl,nexturl2)
    return str


    a=''

    b=''
def _pcastpw(query,data,url):

    id = re.findall('>id="([^"]+)"; width="',data)[0]
    url = 'http://pcast.pw/embed/%s.php?width=700&height=480&stretching=uniform'%id
    headers = {'User-Agent': UA,'Referer': url}    

    contentVideo=getUrl(url,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url=decode(url,html)
    return vido_url 

def _sportlivesite(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,html)
    return vido_url 
    
    
def _livesport4upw(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,html)
    return vido_url 
def _strimstv(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)  
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    try:
        video_url = clappr.findall(html)[0]
    except:
        video_url = source.findall(html)[0]
    
    return video_url

def _sport7biz(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)   
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vid_url = re.findall("""videoLink\s*=\s['"](.+?)['"]""",html)[0]
    vid_url= 'https:'+vid_url if vid_url.startswith('//') else vid_url
    vid_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    
    return vid_url
    
def _olimpappru(query,data,url)    :

    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=requests.get(query,headers=headers,verify=False).text#getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    src = re.findall('"file": "(.+?)"',html)[0]
    src = src.replace('\\/','/')
    vid_url= 'https:'+src if src.startswith('//') else src
    vid_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    

    return vid_url
    
def _dummyview(iframe,url)    :
    headers = {'User-Agent': UA,'Referer': url}    
    chan=iframe.split('/')[-1]
    contentVideo=getUrl(iframe,header=headers)   
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    sver=re.findall('STREAM_VERSION=(.+?)<',html)[0]

    headers = {'User-Agent': UA,'Referer':iframe}    
    nt=getUrl('http://dummyview.online/js/legacyPlayerComponent.js',header=headers)  
    if six.PY3:
        nt = nt.decode(encoding='utf-8', errors='strict')
    html=nt.replace("\'",'"')

    url=re.findall("""url:\s*['"](.+?)['"]""",html)
    url=url[0]+'%s/channels/%s'%(sver,chan)
    xx=getUrl(url,header=headers)    
    if six.PY3:
        xx = xx.decode(encoding='utf-8', errors='strict')
    import json
    response=json.loads(xx)
    sourceurl=response['data']["sourceUrl"]
    contentVideo=getUrl(sourceurl,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(sourceurl,html)
    return vido_url 
    
def _365live(iframe,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(iframe,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    
    html=contentVideo.replace("\'",'"')
    dchan=re.findall("""data\-channel=['"](.+?)['"]""",html)
    
    headers = {
        'User-Agent': UA,
        'Accept': '*/*',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Origin': 'https://365lives.net',
        'Connection': 'keep-alive',
        'Referer': iframe,
    }
    response = requests.get('https://api.livesports24.online/gethost', headers=headers).content
    if six.PY3:
        response = response.decode(encoding='utf-8', errors='strict')
    src='https://%s/%s.m3u8'%(response,dchan[0])
    return src+'|auth=SSL/TLS&verifypeer=false&User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=iframe)

    
    
def _sportsbayorg(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,html)
    return vido_url 
    
def _flowframesonline(query,data,url):
    
    dod = re.findall('(\d+)',query)[-1]
    headers = {'User-Agent': UA,'Referer': url}    
    nturl='http://185.255.96.166:3007/api/channels/'+dod
    response = sess.get(nturl, headers=headers,verify=False,timeout=30).json()
    
    vid_url2=response['data']['sourceUrl']
    
    contentVideo=getUrl(vid_url2,header=headers)    

    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    try:
        vido_url = clappr.findall(html)[0]
        vid_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=vid_url2)    
    except:
        vido_url = source.findall(html)[0]
        vid_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=vid_url2)    
    
    if not vido_url:
        vido_url=decode(vid_url,html)
    return vido_url 

    
def _whd365pro(query,data,url):
    vido_url=''
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    
    data_channel=re.findall("""data-channel=['"](.+?)['"]""",html)
    data_channel = data_channel[0] if data_channel else ''
    
    headers = {
        'User-Agent': UA,
        'Accept': '*/*',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Origin': 'https://whd365.pro',
        'Connection': 'keep-alive',
        'Referer': query,
        'TE': 'Trailers',
    }
    
    headers = {
        'Host': 'api.livesports24.online:8443',
        'User-Agent': UA,
        'Accept': '*/*',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Origin': 'https://whd365.pro',
        'DNT': '1',
        'Referer': 'https://whd365.pro/',
    }
    

    host = requests.get('https://api.livesports24.online:8443/gethost', headers=headers).text #https://api.livesports24.online:8443/gethost
    if data_channel and host:
        vido_url= "https://" + host + "/" + data_channel  + ".m3u8"
    return vido_url
    
    
    
    
def _tvsportws(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url = re.findall("""videoLink\s*=\s*['"](.+?)['"]""",html)#[0]
    vido_url = vido_url[0] if vido_url else ''

    return vido_url
    
def _yoursportsstream(query,data,url):
    
    headers = {'User-Agent': UA,'Referer': url}    
    if 'yoursports' in url:
        dod= '&'.join(['%s=%s' % (name, value) for (name, value) in headers.items()])
    else:
        headersx = {'User-Agent': UA,'Referer': query}    
        dod= '&'.join(['%s=%s' % (name, value) for (name, value) in headersx.items()])
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    match = re.compile("""mustave\s*=\s*atob\(['"](.+?)['"]""",  re.DOTALL).search(html)

    if match:   
        vid = base64.b64decode(match.group(1))
        if six.PY3:
            vid = vid.decode(encoding='utf-8', errors='strict')
        dod = '|'+dod
        vido_url = vid+dod
    else:
        vido_url=decode(query,html)
    return vido_url 
    
    
def _yrsprts(query,data,url):
    
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    
    video_url=''
    html=getUrl(query,header=headers)
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    html = html.replace("\'",'"')    
    
    try:
        pattern = re.findall('{source:([^:]+)}',html)[0]
        regex = 'var %s\s*=\s*atob\("(.+?)"'%pattern
        b64src = re.findall(regex,html)[0]
        vid = base64.b64decode(b64src)
        if six.PY3:
            vid = vid.decode(encoding='utf-8', errors='strict')
        if not vid.startswith("http"):
            video_url='https://yrsprts.xyz'+vid
        
    except:
        dane = (re.findall('var\s+.+?=\[(\d+.+?)\]',html)[0]).split(',')
        co = re.findall('fromCharCode\(parseInt\(value\).(\d+)\)',html)[0]
        htmlx=''
        for x in dane:
            htmlx+=chr(int(x)-int(co))
        try:
            video_url = re.findall('{source:([^:]+)}',htmlx)[0]
        except:
            video_url = re.findall('source:\s*"([^"]+)"',htmlx)[0]
        if video_url.startswith('//'):
            video_url='http:'+video_url
        try:
            co1,co2 =re.findall('rewrittenUrl\=rewrittenUrl.replace\("(.+?)","(.+?)"\);if',html)[0]
            video_url=video_url.replace(co1,co2)
        except:
            pass
    video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    
    return video_url
    
    
    
def _wstreamto(query,data,url):

    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    packed = packer.findall(contentVideo)[0]
    unpacked = jsunpack.unpack(packed)
    video_url = re.findall('\({src\:"(.+?)"',unpacked)
    if not video_url:
        try:
            video_url = clappr.findall(unpacked)[0]
        except:
            video_url = source.findall(unpacked)[0]
    else:
        video_url = video_url[0]
    video_url += '|verifypeer=false&User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)        
    return video_url

def _arembedcom(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vido_url=decode(query,contentVideo)
    return vido_url 

def _h247bay(query,data,url):
    
    data=data.replace("\'",'"')
    
    channel,g = re.findall('channel="([^"]+)",\s*g="([^"]+)"',data)[0] #channel="([^"]+)",\s*g="([^"]+)"
    ifrurl='https://www.247bay.tv/hembedplayer/'+channel+'/'+g+'/700/400'
    
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(ifrurl,header=headers)   
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    adres = re.findall('hlsUrl = "([^"]+)".+?"([^"]+)"',html)[0]
    eaurl = re.findall('url: "([^"]+)" \+ (\d+),',html)[0]
    eaadres = eaurl[0]+eaurl[1]
    headers = {'User-Agent': UA,'Referer': ifrurl}    
    contentVideo=getUrl(eaadres,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    ea = html.split('=')[1]
    vidurl= '%s%s%s'%(adres[0],ea,adres[1])
    return vidurl + '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=ifrurl)    
    
    
def _soccerlivexyz(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    video_url=re.findall('source: "([^"]+)"',html,re.DOTALL)[0]
    video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)        
    return video_url
    
def _soccerliveuk(query,data,url)    :
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)   
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,contentVideo)
    return vido_url

    
    
    
def  _hdstreamsclub2(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    ab=re.findall("""source:\s+window.atob\(["\'](.+?)["\']""",html)[0]

    
    video_url=base64.b64decode(ab)
    if six.PY3:
        video_url = video_url.decode(encoding='utf-8', errors='strict')
    video_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    
    return video_url


def _hazmostream(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)  
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    vido_url=decode(query,contentVideo)
    return vido_url

def _hazmostream2(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers) 
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    try:
        video_url = clappr.findall(html)[0]
    except:
        video_url = source.findall(html)[0]
    video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)        
    return video_url
    
def _streamcdnco(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')
    packed = packer.findall(contentVideo)[0]
    unpacked = jsunpack.unpack(packed)

    try:
        video_url = clappr.findall(unpacked)[0]
    except:
        video_url = source.findall(unpacked)[0]
    video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)        
    return video_url
    
def _7streamspro(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)   
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vidurl=re.findall('var videoLink = "(.+?)"',html,re.DOTALL)[0]
    return vidurl
    
    
    
    
def _strimstveu(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vidurl=re.findall('sources:.+?src: "(.+?)"',html,re.DOTALL)[0]
    return vidurl
    
    
def _studiojunctionlive(query,data,url):
    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers) 
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    vido_url=decode(query,contentVideo)    
    return vido_url    
    
def _dailyhealthandcare(query,data,url):

    query = 'https:'+query if query.startswith('//') else query
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)  
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    vido_url=decode(query,contentVideo)    
    return vido_url    
    
def _bnksportzis(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)   
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    m3ux=re.findall("""source: ["\'](.+?)["\']""",contentVideo,re.DOTALL)[0]
    if not '/' in m3ux:
        
        m3ux='http://bnk.sportz.is/'+m3ux
    return m3ux+'|User-Agent='+UA+'&Referer='+url
    
def _hdstreamsclub(data,url):
    video_url=''

    video_url=base64.b64decode(re.findall("""source:\s+window.atob\(["\'](.+?)["\'].*mimeType""",data)[0])
    if six.PY3:
        video_url = video_url.decode(encoding='utf-8', errors='strict')
    video_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=url)    
    return video_url
    
    
def _sdfgdfxyz(query,data,url):
    urlk=re.findall("""hanturl\s*=\s*["\'](.+?)["\']""",data)[0]

    return urlk+'|User-Agent='+UA+'&Referer='+url
    
def _dubsto(query,data,url):
    urlk='http://www.dubs.to'+re.findall('\.\.(.+?)$',query)[0]

    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(urlk,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    video_url=_hdstreamsclub(contentVideo,urlk)
    return video_url
def _exprestreamcom(query,data,url):
    
    urlk='https://exprestream.com'+query
    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(urlk,header=headers) 
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    src=re.findall('iframe src="(.+?)"',contentVideo)[0]
    headers = {'User-Agent': UA,'Referer': src}    
    urlk='https://exprestream.com'+src
    contentVideo=getUrl(urlk,header=headers)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    m3ux=re.findall("""source: ["\'](.+?)["\']""",contentVideo,re.DOTALL)
    return m3ux[0]+'|User-Agent='+UA+'&Referer='+urlk

def _dubsstreamz(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    html=getUrl(query,header=headers)    
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    html = html.replace('\r','').replace('\n','')

    ff=re.findall("""var (.+?) =\s*"";\s*var (.+?) =\s*(\[.+?\]).+?String.fromCharCode.+?\\'\\'\)\) (.+?) (\d+)\)""",html,re.DOTALL+re.IGNORECASE)[0]
    mDe=eval(ff[2])
    gXW=''

    for x in mDe:
        try:
            x1=base64.b64decode(x)
            if six.PY3:
                x1 = x1.decode(encoding='utf-8', errors='strict')
            x1d = re.findall('(\d+)',x1)[0]
            gXW += chr(int(x1d) - int(ff[4]));
        except:
            pass
    vido_url=re.findall("""source\:\s*['"](.+?)['"]""",gXW)[0]
    return vido_url    +'|User-Agent='+UA+'&Referer='+query

def _weakspellzcom    (query,data,url):
    import json
    headers = {'User-Agent': UA,'Referer': url}    
    html=getUrl(query,header=headers)    
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    html = html.replace('\r','').replace('\n','')

    ab= html
    nturl = re.findall('ajax\({\s*type:\s*"GET",\s*url:\s*"(.+?)"', html)[0]
    vidgstream = re.findall('vidgstream\s*=\s*"(.+?)"',html)[0]
    headers = {'User-Agent': UA,'Referer': query}
    nturl+='?idgstream='+urllib_parse.quote(vidgstream)+'&serverid='
    html=getUrl(nturl,header=headers)
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    ab = json.loads(html)

    vido_url=ab.get("rawUrl","")
    return vido_url    +'|User-Agent='+UA+'&Referer='+query
def _vsdeame(query,data,url):

    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers)   
    if six.PY3:
        html = contentVideo.decode(encoding='utf-8', errors='strict')
    atob=re.findall("""atob\(['"](.+?)['"]""",contentVideo)#[0]
    if atob:
        unpacked=base64.b64decode(atob[0])
        if six.PY3:
            unpacked = unpacked.decode(encoding='utf-8', errors='strict')
    else:
        return ''
    return unpacked+'|User-Agent='+UA+'&Referer='+query
def _bfstto(query,data,url):

    headers = {'User-Agent': UA,'Referer': url}    
    contentVideo=getUrl(query,header=headers) 
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    vido_url=decode(query,contentVideo)    
    return vido_url        
    
def _rippleis(query,data,url):

    cookies2 = {
        'challenge': 'BitMitigate.com',
    }
    
    headers2 = {
        'Host': 'ripple.is',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

    contentVideo=sess.get(query,headers=headers2,cookies=cookies2).text

    nxturl = re.findall('src="([^"]+live.+?)" width',contentVideo)[0]
    
    contentVideo=sess.get(nxturl).text
    html=contentVideo.replace("\'",'"')
    vidurl=re.findall('source:\s+"(.+?.m3u8)"',html,re.DOTALL)[0]    
    vidurl = vidurl+'|User-Agent'+urllib_parse.quote(UA)+'&Referer='+nxturl #if vidurl else ''    
    return vidurl        
    
def _twojetv(query,data,url):
    import uuid
    hash = uuid.uuid4().hex                    
    aa='1679497221'
    kuk='__ddgu=%s.%s'%(hash,aa)


    headers = {'User-Agent': UA,'Referer': url,'Cookie':kuk}    
    query=query.replace('&amp;','&')

    contentVideo=getUrl(query,header=headers)  
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    contentVideo=contentVideo.replace("\'",'"')

    try:
        vidurl=re.findall('source:\s+"(.+?.m3u8)"',contentVideo,re.DOTALL)[0]    
    except:
        vidurl=re.findall('source src="(.+?.m3u8)"',contentVideo,re.DOTALL)[0]    
    
    vidurl = 'http:'+vidurl if vidurl.startswith('//') else vidurl
    vidurl = vidurl+'|User-Agent'+urllib_parse.quote(UA)+'&Referer='+query if vidurl else ''    
    return vidurl        
    
def _1meclub(data,url):
    src=re.findall('iframe src="(.+?)"',data)[0]
    headers = {'User-Agent': UA,'Referer': url}
    
    contentVideo=getUrl(src,header=headers) 
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    vido_url=decode(src,contentVideo)

    return vido_url    
def _sportzonlinepw(query,data,url):
    
    headers = {'User-Agent': UA,'Referer': url}
    html=getUrl(query,header=headers)
    if six.PY3:
        html = html.decode(encoding='utf-8', errors='strict')
    query =query.replace('sportzonline.co/','sportzonline.to/')

    vido_url = decode(query,html)
    return vido_url    

def _sportsstreamnet(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}
    contentVideo=getUrl(query,header=headers)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    
    vido_url = decode(url,contentVideo)
    return vido_url
    
def _realcampw(query,data,url):
    
    feed=re.compile('zmid = "(.+?)", pid = (.+?); edm = "(.+?)"').findall(data)
    headers = {'User-Agent': UA,'Referer': url,'Content-Type': 'application/x-www-form-urlencoded','Connection': 'keep-alive','Upgrade-Insecure-Requests': '1',}
    url_main='https://%s/sdembed?v=%s'%(feed[0][2],feed[0][0])
    
    params='pid=%s'%feed[0][1]
    contentVideo=getUrl(url_main,header=headers,data=params)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    return
    
def _sportbarbiz(query,data,url):
    headers = {'User-Agent': UA,'Referer': url}    
    query = 'https:'+query if query.startswith('//') else query
    contentVideo=getUrl(query,header=headers)   
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    html=contentVideo.replace("\'",'"')

    vid_url = re.findall("""videoLink\s*=\s['"](.+?)['"]""",html)[0]
    vid_url= 'https:'+vid_url if vid_url.startswith('//') else vid_url
    vid_url+= '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    
    
    return vid_url    
    
    
def _fstreamme(query,data,url):
    video_url=''    
    data=data.replace("\'",'"')
    feed = re.compile('width=(.*?), height=(.*?), channel="(.*?)", g="(.*?)";').findall(data)
    if feed:        
        header = {'User-Agent':UA,'Referer': url}
        url_main='https://www.playerfs.com//hembedplayer/%s/%s/%s/%s'%(feed[0][2],feed[0][3],feed[0][0],feed[0][1])                
        contentVideo = getUrl(url_main,header=header) 
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        main_url=re.findall("""['"]src['"].+?['"](.+?)['"].+?['"](.+?)['"]""",contentVideo)[0]
        id=re.findall('url:.+?".+?lquest.+?".+?(\d+).+?&',contentVideo)[0]        
        idurl="https://www.lquest123b.top/loadbalancer?%s"%str(id) + "&"
        header = {'User-Agent':UA,'Referer': url_main}
        contentVideo = getUrl(idurl,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        ea = contentVideo.split('=')[1]
        video_url=main_url[0]+ea+main_url[1]
        return video_url    

def _livesport4ucom(query,data,url):
    video_url=''
    header = {'User-Agent':UA,'Referer': url}    
    content = getUrl(query,header=header)
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    feed = re.compile('id=["\'](.*?)["\']; width=["\'](.*?)["\']; height=["\'](.*?)["\'];').findall(content)
    if feed:
        url_main='http://hdcast.pw/stream_jw2.php?id=%s&width=%s&height=%s&stretching=uniform'%(feed[0][0],feed[0][1],feed[0][2])        
        header = {'User-Agent':UA,'Referer': url}            
        contentVideo = getUrl(url_main,header=header)      
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        video_url=re.findall('curl.+?"(.+?)"',contentVideo)[0] #
        video_url=base64.b64decode(re.findall('curl.+?"(.+?)"',contentVideo)[0])
        if six.PY3:
            video_url = video_url.decode(encoding='utf-8', errors='strict')
        video_url=video_url+'|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=url_main)    
    return video_url    

def _nowlivepro    (query,data,url):

    video_url=''
    header = {'User-Agent':UA,'Referer': url}        
    content = getUrl(query,header=header)  
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    unescs=re.findall('unescape\("(.+?)"',content)
    for unesc in unescs:
        link = urllib_parse.unquote(unesc)
        video_url=re.findall('"application/x-mpegurl", src: "(.+?)"',link)
        if video_url:
            video_url = 'http:'+video_url[0] if video_url[0].startswith('//') else video_url[0]    
            break    
    return video_url    
        
def _streamupme    (query,data,url):
    video_url=''
    content = getUrl(query,header=header)
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    data=data.replace("\'",'"')
    feed = re.compile('fid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='http://www.webtv.ws/embed.php?live=%s&vw=%s&vh=%s'%(feed[0][0],feed[0][1],feed[0][2])        
        header = {'User-Agent':UA,'Referer': url}            
        contentVideo = getUrl(url_main,header=header)  
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        video_url=re.findall('source\s+src="(.+?)"\s+type',contentVideo)[0] #
        video_url=video_url+'|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=url_main)    
        return video_url    
def _webtv(query,data,url):
    video_url=''
    data=data.replace("\'",'"')
    feed = re.compile('fid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='http://www.webtv.ws/embed.php?live=%s&vw=%s&vh=%s'%(feed[0][0],feed[0][1],feed[0][2])        
        header = {'User-Agent':UA,'Referer': url}            
        contentVideo = getUrl(url_main,header=header) 
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        video_url=re.findall('source\s+src="(.+?)"\s+type',contentVideo)[0] #
        video_url=video_url+'|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=url_main)    
        return video_url    

def _youtube(url):
    video_url=re.findall("(.+?)\?",url)[0]    
    vid=urllib_parse.urlparse(video_url).path.split('/')[-1]
    video_url = 'plugin://plugin.video.youtube/play/?video_id=' + vid    
    return video_url
    


def _bonstreams(data,url):
    video_url=''    
    data=data.replace("\'",'"')
    id=re.findall(""">id="(.+?)"; width=""",data)[0]
    vidurl='https://telerium.tv/embed/%s.html'%id
    header = {'User-Agent':UA,'Referer': url}    
    
    contentVideo = getUrl(vidurl,header=header)  
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    video_url=_telerium(contentVideo,contentVideo,vidurl)    
    return video_url    


    

def _hdcastme(query,data,url):
    
    video_url=''    
    feed = re.compile('fid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='https://www.hdcast.me/embed.php?player=desktop&live=%s&vw=%s&vh=%s'%(feed[0][0],feed[0][1],feed[0][2])        
        header = {'User-Agent':UA,'Referer': url}    
        contentVideo = getUrl(url_main,header=header)  
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        video_url=re.findall("""source:\s+["\'](.+?)['"].*mimeType""",contentVideo)[0]
        video_url='https:'+video_url+'|verifypeer=false&User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=url)
        return video_url

    
def _ucasterplayer(query,data,url):
    video_url=''    
    feed = re.compile('width=(.*?), height=(.*?), channel=["\'](.*?)["\'], g=["\'](.*?)["\'];').findall(data)
    if feed:        
        header = {'User-Agent':UA,'Referer': url}
        url_main='https://www.ucasterplayer.com/hembedplayer/%s/%s/%s/%s'%(feed[0][2],feed[0][3],feed[0][0],feed[0][1])                
        contentVideo = getUrl(url_main,header=header)  
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        main_url=re.findall("""['"]src['"].+?['"](.+?)['"].+?['"](.+?)['"]""",contentVideo)[0]
        id=re.findall('url:.+?".+?lquest.+?".+?(\d+).+?&',contentVideo)[0]        
        idurl="https://www.lquest123b.top/loadbalancer?%s"%str(id) + "&"
        header = {'User-Agent':UA,'Referer': url_main}
        contentVideo = getUrl(idurl,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        ea = contentVideo.split('=')[1]
        video_url=main_url[0]+ea+main_url[1]
        return video_url
        
def _whostreams(query,data,url):
    if '\r' in url:
        url=url.replace('\r','')    
    
    ref_url = 'http:'+query if query.startswith('//') else query
    header = {'User-Agent':UA,'Referer': url}    
    contentVideo = getUrl(ref_url,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    packed = packer.findall(contentVideo)[0]
    unpacked = jsunpack.unpack(packed)
    try:
        video_url = clappr.findall(unpacked)[0]
    except:
        video_url = source.findall(unpacked)[0]
    video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=ref_url)        
    return video_url
    
def rev(a_string):
    return a_string[::-1]

def getRequestAdv (url, headers, isReplace=True):
    UTF8 = 'utf-8'
    request = urllib_request.Request(url.encode(UTF8), None, headers)

    try:
        response = urllib_request.urlopen(request)
        
        if response.info().getheader('Content-Encoding') == 'gzip':
          #  print ("Content Encoding == gzip")

            buf = StringIO( response.read() )
            f = gzip.GzipFile(fileobj=buf)
            link1 = f.read()
        else:
            link1=response.read()
    except:
        link1 = ""
        
    if (isReplace):
        link1 = str(link1).replace('\n','')

    return(link1)    
def getRequest (url, referUrl, userAgent, xRequestedWith=""):
    UTF8 = 'utf-8'
    headers = {'User-Agent':userAgent, 'Referer':referUrl, 'X-Requested-With': xRequestedWith, 'Accept':"text/html", 'Accept-Encoding':'gzip,deflate,sdch', 'Accept-Language':'en-US,en;q=0.8'} 
    request = urllib_request.Request(url.encode(UTF8), None, headers)

    try:
        response = urllib_request.urlopen(request)
        
        if response.info().getheader('Content-Encoding') == 'gzip':
          #  print ("Content Encoding == gzip")

            buf = StringIO( response.read() )
            f = gzip.GzipFile(fileobj=buf)
            link1 = f.read()
        else:
            link1=response.read()
    except:
        link1 = ""
    
    link1 = str(link1).replace('\n','')
    return(link1)    
    
def _telerium(query,data,url):
    parsed_url = urllib_parse.urlparse(query)
    domain = parsed_url.netloc
    if 'embed.' in domain:
        domain = 'telerium.digital'
    import json
    import datetime

    from resources.lib import getkeyTelerium as TRD
    sessx=requests.Session()
    
    headers22 = {
        'User-Agent': UACHR,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': url,
        'Upgrade-Insecure-Requests': '1',
    }

    htmlx=sessx.get(query,headers=headers22,verify=False).text
    
    cid = re.findall("""cid\s*=\s['"](.+?)['"]""",htmlx)    
    if not cid:
        data=data.replace("\'",'"')

        id =re.findall('>id\s*=\s*"([^"]+)"',data,re.DOTALL)[-1]
        urlx = 'https://telerium.digital/embed/'+id+'.html'
        htmlx=sessx.get(urlx,headers=headers22,verify=False).text
        cid = re.findall("""cid\s*=\s['"](.+?)['"]""",htmlx) 
        query = urlx
    script =re.findall('(var _0x.*?)<\/script>',htmlx,re.DOTALL)[0]    

    decscript = TRD.getkey(script)
    scriptdeco = decscript.replace("'+'",'').replace("\'",'"')
    data=''
    htmlx=''

    azz = re.findall('token\s*=\s*_0x.+?\(reverse\s*\,\s*_0x.+?\[(.+?)\]',scriptdeco)#[0]
    azz = azz[0] if azz else re.findall('token\s*=\s*reverse.*?\[(.+?)\]',scriptdeco)[0] 
    
    abcz=re.findall('(0[xX][0-9a-fA-F]+)',azz)
    
    def unhex(txt):
        if six.PY3:
            ab =  re.sub('\\\\x[a-f0-9][a-f0-9]', lambda m: bytes.fromhex(m.group()[2:]).decode('utf-8'), txt)
        else:
            ab = re.sub('\\\\x[a-f0-9][a-f0-9]', lambda m: m.group()[2:].decode('hex'), txt)
        return ab
    
    
   # def unhex(txt):
     #$   return re.sub('\\\\x[a-f0-9][a-f0-9]', lambda m: m.group()[2:].decode('hex'), txt)
    for az in  abcz:
        x = str(int(unhex(az) ,16))
        azz = re.sub(az+'(?![a-f0-9])',x,azz)

    spech = eval(azz)
    
    
    
    timeurls = eval(re.findall('var timeUrls=(\[.+?\])',scriptdeco)[0])
    sessx.headers = {
    #    'authority': 'bamtech.sc.omtrdc.net',
        'accept': '*/*',
        'user-agent': UACHR,
        'origin': 'https://%s'%(domain),
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': query,
        'accept-language': 'en-US,en;q=0.9,pl;q=0.8',
    }

    tur=re.findall("""['"]head['"].+?\[['"]ajax['"]\]\(\{['"]url['"]:_0[xX][0-9a-fA-F]+\[(.+?)\]""",scriptdeco)[0]
    turls=re.findall('(0[xX][0-9a-fA-F]+)',tur)
    for turl in  turls:
        x = str(int(unhex(turl) ,16))
        #tur = tur.replace(turl,x)
        tur = re.sub(turl+'(?![a-f0-9])',x,tur)
    tur = eval(tur)

    html = sessx.head(timeurls[tur],headers=sessx.headers)

    a= html.headers#('')
    c= a['last-modified'] 
    #xbmc.log('@#@last-modifiedlast-modified: %s' % str(c), LOGNOTICE)
    date_time_str= c#re.findall('^(.+?) G',c)[0]

    import time
    try:
        date_time_obj=datetime.datetime.strptime(date_time_str, '%a, %d %b %Y %H:%M:%S %Z')
    except TypeError:
        date_time_obj=datetime.datetime(*(time.strptime(date_time_str, '%a, %d %b %Y %H:%M:%S %Z')[0:6]))
        
        
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
        
        
        
    tst4 =     to_timestamp(date_time_obj)

    nturl = 'https://%s/streams/%s/%s.json'%(domain,str(cid[0]),str(tst4))

    headers4 = {
        'Connection': 'keep-alive',
        'User-Agent': UACHR,
        'Accept': '*/*',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',

        'Accept-Language': 'en-US,en;q=0.9,pl;q=0.8',
        
    }  
    cookies = {
        'volume': '365',

    }  

    data = sessx.get(nturl,headers=sessx.headers,cookies=cookies).text

    data = sessx.get(nturl,headers=sessx.headers,cookies=cookies).json()
    
    urln = data.get("url",None)
    tokenurl = data.get("tokenurl",None)

    basurl='https://%s'%(domain)
    

    nxturl=basurl+tokenurl

    realtoken = getRealToken(nxturl, query,spech)
    
    path = 'https:'+urln+realtoken

    path+='|User-Agent='+UACHR+'&Referer='+urllib_parse.quote(query, safe='')+'&Sec-Fetch-Mode=cors&Origin=https://%s'%domain
    
    return path    


def getRealToken(link, referer,spech):
    parsed_url = urllib_parse.urlparse(link)
    domain = parsed_url.netloc
    cookies = {
        'ChorreameLaJa': '100',
        'setVolumeSize': '100',
        'NoldoTres': '100',
    }
    
    cookies = {
        'elVolumen': '100',
    }
    
    headers = {
        'Host': '%s'%domain,
        'User-Agent': UACHR,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': referer,
    }
    
    
    
    cookies = {
        'volume': '0',
    }
    
    headers = {
        'Host': '%s'%domain,
        'user-agent': UACHR,
        'accept': '*/*',
        'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
        'referer': referer,
        'te': 'trailers',
    }
    
    
    
    
    
    
    
    
    #headers = {
    #    'Host': 'telerium.tv',
    #    'User-Agent': UACHR,
    #    'Accept': 'application/json, text/javascript, */*; q=0.01',
    #    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    #    'X-Requested-With': 'XMLHttpRequest',
    #    'Referer': referer,
    #}
    #h = {
    #    'User-Agent': UACHR,
    #    'Accept': 'application/json, text/javascript, */*; q=0.01',
    #    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    #    'Referer': referer,
    #    'X-Requested-With': 'XMLHttpRequest',
    #    'Connection': 'keep-alive',}    


    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Accept': '*/*',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Referer': referer,
        'Alt-Used': domain,
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    }
    

    realResp = requests.get(link, headers=headers,cookies=cookies,verify=False).content#[1:-1]
    if six.PY3:
        realResp = realResp.decode(encoding='utf-8', errors='strict')

    realResp=re.findall('"(.+?)"',realResp)[spech]    

    return realResp[::-1]    


def _assiatv(query,data,url):
    video_url=''
    header = {'User-Agent':UA,'Referer': url}
    content = getUrl(query,header=header)   
    if six.PY3:
       content = content.decode(encoding='utf-8', errors='strict')
    content=content.replace("\'",'"')
    video_url=re.findall('file:"([^"]+)"',content)#[0]
    #

    if video_url:
        video_url=video_url[0]+'|User-Agent='+UA+'&Referer='+query    
    else:
        try:
            
            content=content.replace("\'",'"')
            video_url=re.findall('<source src="([^"]+)" type="application',content)[0]
            video_url=video_url+'|User-Agent='+UA+'&Referer='+query    
        except:
            try:
                video_url = clappr.findall(content)[0]
            except:
                video_url = source.findall(content)[0]
            if video_url:
                video_url += '|User-Agent={ua}&Referer={ref}'.format(ua=UA, ref=query)    
    return video_url

def _wlivetv(query,data,url):
    video_url=''
    feed = re.compile('fid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        
        header = {'User-Agent':UA,'Referer': url}
        if data.find('wlive.tv/embedra.js')>0:
            url_main='http://www.wlive.tv/embedra.php?player=desktop&live=%s&vw=660&vh=420'%feed[0][0]            
        else:
            url_main='http://www.wlive.tv/embedhd.php?player=desktop&live=%s&vw=660&vh=420'%feed[0][0]
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        pi = re.findall('return\\((.*?)\\);',contentVideo)
        pi=pi[0]
        if pi:        
            join = re.findall('(\\[.*?\\]).join',pi)
            el_id = re.findall('(\\w+).join',pi)
            aa = re.findall('document.getElementById\\("(.*?)"',pi)
            if join:
                join = ''.join(eval(join[0])).replace('\\','')
            if el_id:
                tmp = re.findall('var %s\\s*=\\s*(\\[.*?\\])'%el_id[0],contentVideo)
                el_id = ''.join(eval(tmp[0])) if tmp else ''
            if aa:
                aa = re.findall('%s\\s*>(.*?)<'%aa[0],contentVideo)
                aa = aa[0] if aa else ''
                video_url = join + el_id + aa +'|User-Agent='+UA+'&Referer='+url
        return video_url
def _tumarcadorxyz(query,data,url):
    import requests
    str_url=''
    header = {'User-Agent':UA,'Referer': url}    
    content = requests.get(query,headers=header,verify=False).content
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    str_url=re.findall("""file:\s+['"](.+?)['"]""",content,re.DOTALL)
    if str_url:
        str_url=str_url[0]
    return str_url    
def _embedpot_iptv(query,data,url):
    video_url=''
    feed = re.compile('cid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='http://embed.pot-iptv.pl/playerr/%s?vw=600&vh=450'%feed[0][0]
        header = {'User-Agent':UA,
                'Referer': url}
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        src = re.findall('{ src\\s*:\\s*[\'"](http.*?)[\'"]',contentVideo)
        if src:
            header['Referer']=url_main
            req = urllib_request.Request(src[0],data=None,headers=header)
            try:
                response = urllib_request.urlopen(req, timeout=10)
                link = response.geturl()
                response.close()
            except:
                link=''
            if link:
                video_url = link+'|User-Agent='+UA+'&Referer='+url_main
    return video_url
def _vvcast(query,data,url):
    video_url=''
    feed = re.compile('fid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='http://www.vvcast.tv/embedhd.php?live=%s&vw=%s&vh=%s'%feed[0]
        header = {'User-Agent':UA,
                'Referer': url}
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        szuk = re.findall('return\\((.*?)\\);',contentVideo)
        if szuk:
            szuk = szuk[0]
            join = re.findall('(\\[.*?\\]).join',szuk)
            el_id = re.findall('(\\w+).join',szuk)
            aa = re.findall('document.getElementById\\("(.*?)"',szuk)
            if join:
                join = ''.join(eval(join[0])).replace('\\','')
            if el_id:
                tmp = re.findall('var %s\\s*=\\s*(\\[.*?\\])'%el_id[0],contentVideo)
                el_id = ''.join(eval(tmp[0])) if tmp else ''
            if aa:
                aa = re.findall('%s\\s*>(.*?)<'%aa[0],contentVideo)
                aa = aa[0] if aa else ''
            if join and el_id and aa:
                video_url = join + el_id + aa +'|User-Agent='+UA+'&Referer='+url_main
    return video_url
def _playercloudwowza(data,url):
    video_url=''
    href=re.findall('video_id=(http.+m3u[8])',data)
    if href:
        video_url=href[0]+'|Referer=%s&User-Agent=%s'%(url,UA)+'X-Requested-With=ShockwaveFlash/28.0.0.126'
    return video_url
def _tvpPlayer(query,data,url):
    data=getUrl(query)
    
    if six.PY3:
        data = data.decode(encoding='utf-8', errors='strict')

    src_vid = re.compile('0:{src:["\'](.*?)[\'"]', re.DOTALL).findall(data)
    if src_vid: video_url = src_vid[0]
    else: video_url=''
    return video_url
def _byetv(query,data,url):
    contentbye= getUrl(query)
    
    
    if six.PY3:
        contentbye = contentbye.decode(encoding='utf-8', errors='strict')

    
    ref_url = re.findall('url\\s*=\\s*["\'](http.+?)["\']',contentbye)
    if ref_url:
        contentVideo= getUrl(ref_url[0])
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        try:
            hlsUrl=re.findall('var hlsURL\\s*=\\s*(.*?);',contentVideo)
            name=re.findall('var\\s+name\\s*=\\s*["\'](.+?)["\']\\s*;',contentVideo)[0]
            ipserver=re.findall('var\\s+edgeserverip\\s*=\\s*["\'](.+?)["\']\\s*;',contentVideo)[0]
            appname=re.findall('var\\s+appName\\s*=\\s*["\'](.+?)["\']\\s*;',contentVideo)[0]
            width=re.findall('var\\s+width\\s*=\\s*["\'](.+?)["\']\\s*;',contentVideo)[0]
            height=re.findall('var\\s+height\\s*=\\s*["\'](.+?)["\']\\s*;',contentVideo)[0]
            video_url = eval(hlsUrl[0]) +'|User-Agent='+UA+'&Referer='+ref_url[0]
        except:
            video_url=''
    return video_url
def _veecast(query,data,url):
    video_url=''
    header = {'User-Agent':UA,
            'Referer': url}
    contentVideo = getUrl(query,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    if contentVideo:
        f1   = re.compile('source\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
        f2   = re.compile('file\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
        src_vid   = re.compile('<source src=["\'](.*?)[\'"]').findall(contentVideo)
        if   f1:  video_url = f1[0]
        elif f2:  video_url = f2[0]
        elif src_vid:  video_url = src_vid[0]
        if video_url:
            video_url += '|User-Agent='+UA+'&Referer='+url
    return video_url
def _srkcast(query,data,url):
    video_url=''
    feed = re.compile('fid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='http://www.srkcast.com/embed.php?sid=default&live=%s&vw=%s&vh=%s'%feed[0]
        header = {'User-Agent':UA,
                'Referer': url}
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        if contentVideo:
            f1   = re.compile('source\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
            f2   = re.compile('file\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
            src_vid   = re.compile('<source src=["\'](.*?)[\'"]').findall(contentVideo)
            if   f1:  video_url = f1[0]
            elif f2:  video_url = f2[0]
            elif src_vid:  video_url = src_vid[0]
            if video_url:
                video_url += '|User-Agent='+UA+'&Referer='+url_main
    return video_url
def _sharecast(query,data,url):
    video_url=''
    header={'Referer':url,'User-Agent':UA}
    contentVideo = getUrl(query,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    if contentVideo:
        f1   = re.compile('source\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
        f2   = re.compile('file\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
        src_vid   = re.compile('<source src=["\'](.*?)[\'"]').findall(contentVideo)
        if   f1:  video_url = f1[0]
        elif f2:  video_url = f2[0]
        elif src_vid:  video_url = src_vid[0]
        if video_url:
            video_url += '|User-Agent='+UA+'&Referer='+query
    return video_url
def _limacity(query,data,url):
    video_url=''
    contentVideo = getUrl(query)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    if contentVideo:
        file   = re.compile('source\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
        if file:
            video_url = file[-1]
        file   = re.compile('file\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
        if file:
            video_url = file[-1]
        file   = re.compile('<source src=["\'](.*?)[\'"]').findall(contentVideo)
        if file:
            video_url = file[-1]
        if video_url:
            hlsNumb=re.findall('hls(\\d+)',video_url)
            if hlsNumb:
               video_url = video_url.replace('masterlist.m3u8','%sp/list.m3u8'%hlsNumb[0])
            else:
               video_url = video_url.replace('masterlist.m3u8','720p/list.m3u8')
            video_url += '|User-Agent='+UA+'&Referer='+query
    return video_url
def _ustream(query,data,url):
    video_url=''
    return video_url
def _ustreamix(query,data,url):
    video_url=''
    if 'cr.php' in query:
        content = getUrl(query)
        if six.PY3:
            content = content.decode(encoding='utf-8', errors='strict') 

        
        href = re.compile('<a href="(.*?)" target="_blank">').findall(content)
        if href:
            stream_url='stream='+href[0].split('id=')[-1]
    else:
        if 'id=' in url:
            stream_url='stream='+url.split('id=')[-1]
        else:
            stream_url='stream='+query.split('id=')[-1]
    content = getUrl(query,header = {'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:44.0) Gecko/20100101 Firefox/44.0 Iceweasel/44.0', 'Accept': '*/*'})
    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')

    firstIp = re.findall("x_first_ip.+?'(.*?)'", content)
    if not firstIp:
        query = 'https://ustreamix.com/'+stream_url.replace('=','.php?id=')
        content = getUrl(query,header = {'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:44.0) Gecko/20100101 Firefox/44.0 Iceweasel/44.0', 'Accept': '*/*'})
        if six.PY3:
            content = content.decode(encoding='utf-8', errors='strict')


    firstIp = re.findall("x_first_ip.+?'(.*?)'", content)
    firstIp = firstIp[0]
    ustreamyxBase = ['http://ustreamyx.com/']
    varjdtk=''
    hosttmg=''
    for item in ustreamyxBase:
        url_main_str = item + 'stats.php?p=' + firstIp
        source = getUrl(url_main_str, header = {'Referer': query, 'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:44.0) Gecko/20100101 Firefox/44.0 Iceweasel/44.0', 'Accept': '*/*'})

        if six.PY3:
            source = source.decode(encoding='utf-8', errors='strict')

        varjdtk = re.findall('var jdtk="(.*?)"', source)
        hosttmg = re.findall('host_tmg="(.*?)"', source)
        if varjdtk: varjdtk=varjdtk[0]
        if hosttmg: hosttmg =hosttmg[0]
    if varjdtk:
        stream_host = hosttmg if hosttmg else item
        video_url= 'http://%s/tmg.m3u8?stream=%s&token=%s'%(stream_host,stream_url.replace('.php?id',''), varjdtk) +'|User-Agent=Mozilla/5.0 (X11; Linux i686; rv:44.0) Gecko/20100101 Firefox/44.0 Iceweasel/44.0&Referer='+url
    return video_url
def _dailymotion(query,data,url):
    video_id=query.split('?')[0].split('/')[-1]
    content = getUrl('http://www.dailymotion.com/embed/video/%s' % video_id)

    if six.PY3:
        content = content.decode(encoding='utf-8', errors='strict')
    srcs=re.compile('"(auto)":\\[{"type":"(.*?)","url":"(.*?)"}\\]',re.DOTALL).findall(content)
    for quality,type,url in srcs:
        url = url.replace('\\','')
        contentDM = getUrl(url + '&redirect=0')
        extm3u='I0VYVE0zVQ=='.decode('base64')
        if not contentDM:
            contentDM = getUrl(url + '&redirect=0')
        if extm3u in contentDM:
            names=re.compile('NAME="(.*?)"\n(.*?)\n').findall(contentDM)
            for label,url in names:
                video_url=url
        else:
            if contentDM and not contentDM.startswith('http:'):
                contentDM = re.findall('(http://.*?)$', contentDM)[0]
            live_url = contentDM.split('live.isml')[0]+'live.isml/'
            contentDM2 = getUrl(url)
            if extm3u in contentDM2:
                names=re.compile('RESOLUTION=(.*?)\n(.*?)\n').findall(contentDM2)
                for label,added in names:
                    video_url=live_url+added
    return video_url
def _jazztv(query,data,url):
    video_url=''
    feed = re.compile('fid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='http://www.jazztv.co/embedo.php?live=%s&vw=%s&vh=%s'%feed[0]
        header = {'User-Agent':UA,
                'Referer': url,
                'Host':'www.jazztv.co',
                }
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        file   = re.compile('file[: ]*(.*?)}',re.DOTALL).findall(contentVideo)
        for f in file:
            video_url = f.strip().split('"')[1]
            if video_url.startswith('rtmp'):
                video_url += ' swfVfy=1 live=1 timeout=13  swfUrl=http://ssl.p.jwpcdn.com/player/v/7.9.3/jwplayer.flash.swf pageUrl='+url_main
                break
    return video_url
def _urhdtv(query,data,url):
    video_url=''
    data = getUrl(query)

    if six.PY3:
        data = data.decode(encoding='utf-8', errors='strict')
    file = re.compile('file:\\s*[\'"](.*?)[\'"]').findall(data)
    if file:
        video_url = file[0]
    return video_url
def _jardello(query,data,url):
    video_url=''
    data = getUrl(query)
    if six.PY3:
        data = data.decode(encoding='utf-8', errors='strict')
    

    
    file = re.compile('file:\\s*[\'"](.*?)[\'"]').findall(data)
    if file:
        video_url = file[0]
    return video_url
def _cricfree(query,data,url):
    data = getUrl(query)
    if six.PY3:
        data = data.decode(encoding='utf-8', errors='strict')
    video_url=''
    feed = re.compile('id=[\'"](.*?)[\'"]; width=[\'"](.*?)[\'"]; height=[\'"](.*?)[\'"];').findall(data)
    if feed:
        url_main='http://soccerschedule.online/livegamecrnope.php?id=%s&width=%s&height=%s&stretching='%feed[0]
        header = {'User-Agent':UA,
                 'Referer': query,}
        contentDec = getUrl(url_main,header=header)
        if six.PY3:
            contentDec = contentDec.decode(encoding='utf-8', errors='strict')

        idcric=re.compile('id=[\'"](.*?)[\'"]; width=[\'"](.*?)[\'"]; height=[\'"](.*?)[\'"];').findall(contentDec)
        if idcric:
            url_cric='http://playlive.pw/streamt.php?id=%s&width=%s&height=%s'%idcric[0]
            header = {'User-Agent':UA,'Referer': url_main,}
            contentCric = getUrl(url_cric,header=header)
            
            if six.PY3:
                contentCric = contentCric.decode(encoding='utf-8', errors='strict')

            
            file = re.compile('source:\\s*[\'"](.*?)[\'"]').findall(contentCric)
            if file:
                video_url = file[0]
    return video_url
def _staticnowliveclub(query,data,url):
    video_url=''
    feed = re.compile('id=[\'"](.*?)[\'"]; width=[\'"](.*?)[\'"]; height=[\'"](.*?)[\'"];').findall(data)
    if feed:
        url_main='http://nowlive.club/stream.php?id=%s&width=%s&height=%s&stretching=uniform&p=1'%feed[0]
        header = {'User-Agent':UA,
                 'Referer': url,}
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        stream = re.compile('curl = "(.*?)"').findall(contentVideo)
        h = '|Cookie=%s' % urllib_parse.quote('PHPSESSID=1')
        header={'User-Agent':UA,'Referer': url_main,'Host':'nowlive.club',
            'X-Requested-With':'XMLHttpRequest',
            'Cookie':'c_ref_3504694=%s'%urllib_parse.quote_plus(url)}
        url_swf='http://nowlive.club/jwplayer.flash.swf'
        contentSTCL = getUrl('http://nowlive.club/getToken.php',header=header)
        if six.PY3:
            contentSTCL = contentSTCL.decode(encoding='utf-8', errors='strict')

        token = re.compile('"token":"(.*?)"').findall(contentSTCL)
        if token and stream:
            video_url = base64.b64decode(stream[0])

            if six.PY3:
                video_url = video_url.decode(encoding='utf-8', errors='strict')
            video_url= video_url + token[0] +'|Referer=%s&User-Agent=%s&X-Requested-With=ShockwaveFlash/23.0.0.185'%(url_swf,UA)
    return video_url
def _abcastnet(query,data,url):
    video_url =''
    feed = re.compile('file=["\'](.*?)["\']; width=(.*?); height=(.*?);').findall(data)
    if feed:
        url_main='http://abcast.net/embed.php?file=%s&width=640&height=430'%feed[0][0]
        contentDec = getUrl(url_main)
        if six.PY3:
            contentDec = contentDec.decode(encoding='utf-8', errors='strict')

        
        param_val = re.compile('<param value="(.*?)"\\s*name="flashvars">').findall(contentDec)
        link = re.compile('player.src\\((.*?)\\)',re.DOTALL).findall(contentDec)
        if param_val:
            url_swf='http://abcast.net/ob.swf'
            streamer=re.compile('streamer=(.*?)&').findall(param_val[0])
            file=re.compile('file=(.*?)&').findall(param_val[0])
            if streamer and file:
                video_url =streamer[0]+ ' playpath='+file[0].split('.')[0] +' swfUrl='+url_swf + ' swfVfy=1 live=1 timeout=13 pageUrl='+url_main
                video_url =streamer[0].replace('redirect','live') + ' playpath='+file[0].split('.')[0] +' swfUrl='+url_swf + ' pageUrl='+url_main
        elif link:
            url_abcast=re.compile('["\'](http.*?)["\']').findall(link[0])
            video_url = url_abcast[0] if url_abcast else ''
        else:
            source = re.compile('(?:src|source)(?:\\:|=)\\s*[\'"](http.+m3u.*?)[\'"]').findall(contentDec)
            if source:
                video_url = source[0]
    else:
        contentDec = getUrl(query)
        if six.PY3:
            contentDec = contentDec.decode(encoding='utf-8', errors='strict')

        
        
        source = re.compile('(?:src|source)(?:\\:|=)\\s*[\'"](http.+m3u.*?)[\'"]').findall(contentDec)
        if source:
            video_url = source[0]
    return video_url
def _freelive365(query,data,url):
    video_url =''
    contentVideo = getUrl(query)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    hlsUrl=re.search('var hlsURL\\s*=\\s*(.*?);',contentVideo)
    if hlsUrl:
       hlsUrl = hlsUrl.group(1)
    else:
        url_main=re.compile('url\\s*=\\s*["\'](http://freelive365.com/.*?)["\']').findall(contentVideo)
        if url_main:
            contentVideo = getUrl(url_main[0])
            if six.PY3:
                contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
            hlsUrl=re.search('var hlsURL\\s*=\\s*(.*?);',contentVideo)
            hlsUrl = hlsUrl.group(1) if hlsUrl else ''
    if hlsUrl:
        xxx=re.compile('\\+(\\w+)\\+').findall(hlsUrl)
        l111l1lll1l11l111_tv_={}
        for w in xxx:
            vars=re.compile('var %s\\s*=\\s*(.*?);'%w).search(contentVideo)
            if vars: hlsUrl = hlsUrl.replace('%s'%w,vars.group(1))
        try:
            video_url =eval(hlsUrl)
        except:pass
    return video_url
def _cast4utv(query,data,url):
    video_url =''
    feed = re.compile('fid=["\'](.*?)["\']; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='http://www.cast4u.tv/embed.php?v=%s&vw=%s&vh=%s'%feed[0]
        header = {'User-Agent':UA,
                'Referer': url,
                'Host':'www.cast4u.tv',
                }
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        file   = re.compile('file[: ]*(.*?)}').findall(contentVideo)
        token = re.compile('securetoken: (\\w+)').findall(contentVideo)
        file = file[0].strip() if file else ''
        if file and token:
            xxx = re.compile('(\\w+)\\(\\)').findall(file)
            f = xxx[0]
            fd = re.compile('function\\s+%s\\(\\)\\s*{(.*?)}'%f,re.DOTALL).findall(contentVideo)
            if fd:
                stream = re.compile('(\\[[^\\]]*\\])').findall(fd[0])
                stream = ''.join(eval(stream[0]))
                join = re.compile(' (\\w+).join\\(""\\)').findall(fd[0])
                if join:
                    dd = re.compile('%s = (\\[[^\\]]*\\])'%join[0]).findall(contentVideo)
                    join = ''.join(eval(dd[0]))
                el_id = re.compile('getElementById\\("(.*?)"\\)').findall(fd[0])
                if el_id:
                    id_get = re.compile('id=%s>(.*?)<'%el_id[0]).findall(contentVideo)
                    el_id =id_get[0]
            fd = re.compile('function\\s+%s\\(\\)\\s*{(.*?)}'%xxx[1],re.DOTALL).findall(contentVideo)
            if fd:
                aa = re.compile('(\\[[^\\]]*\\])').findall(fd[0])
                aa = ''.join(eval(aa[0]))
            url_cast4u = stream+join+el_id+'/'+aa
            token='JVhCMDAobktIQCMu'
            video_url = url_cast4u.replace('\\','') +' swfUrl=http://cast4u.tv/jwplayer/jwplayer.flash.swf token='+token.decode('base64')+' live=1 timeout=15 pageUrl=' + query
    return video_url
def _osgchmura(query,data,url):
    video_url=''
    header = {'User-Agent':UA,
             'Referer': url,}
    contentVideo = getUrl(query,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    source = re.compile('src=["\'](http.*?)["\']').findall(contentVideo)
    for src in source:
        if src.endswith('m3u8'):
            video_url = src
            break
    return video_url
def _staticu_profr(query,data,url):
    video_url=''
    source = re.compile('src=["\'](http.*?)["\']').findall(data)
    if source:
        source = re.compile('source=(rtmp.*?[^&]*)').findall(source[0])
        if source:
            video_url = source[0]
    return video_url
def _widestream(query,data,url):
    video_url=''
    header = {'User-Agent':UA,
             'Referer': url,}
    contentVideo = getUrl(query,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    file = re.compile('file\\s*:\\s*["\'](.*?)["\']').search(contentVideo)
    if file:
        video_url=file.group(1)
    return video_url
def _staticnowlive(query,data,url):
    video_url=''
    feed = re.compile('id=[\'"](.*?)[\'"]; width=[\'"](.*?)[\'"]; height=[\'"](.*?)[\'"];').findall(data)
    if feed:
        url_main='http://nowlive.pw/stream.php?id=%s&width=%s&height=%s&stretching=uniform&p=1'%feed[0]
        header = {'User-Agent':UA,
                 'Referer': url,}
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        stream = re.compile('curl = "(.*?)"').findall(contentVideo)
        h = '|Cookie=%s' % urllib_parse.quote('PHPSESSID=1')
        header={'User-Agent':UA,'Referer': url_main,'Host':'nowlive.pw',
            'X-Requested-With':'XMLHttpRequest',
            'Cookie':'c_ref_3504694=%s'%urllib_parse.quote_plus(url)}
        url_swf='http://nowlive.pw/jwplayer.flash.swf'
        contentSTCL = getUrl('http://nowlive.pw/getToken.php',header=header)
        
        if six.PY3:
            contentSTCL = contentSTCL.decode(encoding='utf-8', errors='strict')
        

        token = re.compile('"token":"(.*?)"').findall(contentSTCL)
        if token and stream:
            video_url = base64.b64decode(stream[0]) 
            if six.PY3:
                video_url = video_url.decode(encoding='utf-8', errors='strict')
            
            
            video_url = video_url + token[0] +'|Referer=%s&User-Agent=%s&X-Requested-With=ShockwaveFlash/23.0.0.185'%(url_swf,UA)
    return video_url
def _deltalivepro(query,data,url):
    video_url=''
    file = re.compile("url: '(.*?)'").search(data)
    netCon = re.compile("netConnectionUrl: '(.*?)'").search(data)
    url_swf = re.search('"player", "(.*?.swf)"',data)
    if file and netCon and url_swf:
        video_url = netCon.group(1) + ' playpath='+file.group(1).strip() +' swfUrl='+url_swf.group(1) + ' swfVfy=1 live=1 timeout=13  pageUrl='+url
    return video_url
def _openliveorg(query,data,url):
    video_url=''
    feed = re.compile('file=[\'"](.*?)[\'"]; width=[\'"](.*?)[\'"]; height=[\'"](.*?)[\'"];').findall(data)
    if feed:
        url_main='http://openlive.org/embed.php?file=%s&width=%s&height=%s'%feed[0]
        header = {'User-Agent':UA,
                    'Referer': url,}
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        url_swf = ['http://p.jwpcdn.com/6/12/jwplayer.flash.swf']
        stream = re.compile("'streamer'[:, ]+'(.*?)'").findall(contentVideo)
        file   = re.compile("'file'[:, ]+'(.*?)'").findall(contentVideo)
        if url_swf and stream and file:
            urlbase_openlive=urllib_parse.urlparse(stream[0])
            request = urllib_request.Request('http://'+urlbase_openlive.netloc+urlbase_openlive.path, None, header)
            data =  urllib_request.urlopen(request)
            aa,port=data.fp._sock.fp._sock.getpeername()
            netCon = 'rtmp://94.176.148.234/live?'+urlbase_openlive.query
            video_url = netCon +' playpath='+file[0] + ' swfUrl='+url_swf[0] + ' swfVfy=1 live=1  timeout=10 pageUrl='+url_main
    return video_url
#def _sawlivetv(query,data,url):
#    video_url=''
#    source = getUrl(query)
#    unpacked = ''
#    packed = source.split('\n')
#    for i in packed:
#        try:
#            if 'unescape' in i:
#                a=i
#            if 'rtmp://' in i:
#                rtm=i
#            unpacked += jsunpack.unpack(i)
#        except:
#            pass
#    try:
#        contentVideo = jsunpack.unpack(source.decode('string_escape'))
#    except:
#        contentVideo =''
#    src=re.compile('src=["\'](http:.*?)["\']').findall(contentVideo)
#    if src:
#        header = {'Referer':  src[0], 'User-Agent': UA}
#        contentVideo = getUrl(src[0].replace('/view/','/watch/'),header=header)
#        url_swf = re.compile("SWFObject\\('(.*?)'").findall(contentVideo)
#        match = re.compile('(eval\\(function\\(p,a,c,k,e,d\\).*?)\n').findall(contentVideo)
#        if match:
#            contentVideo = jsunpack.unpack(match[0].decode('string_escape'))
#            dec_saw = lambda x: x.group(0).replace('%','').decode('hex')
#            contentVideo = re.sub('%.{2}',dec_saw,contentVideo)
#            code = contentVideo.replace("so.addVariable('file',",'file=')
#            code = code.replace("so.addVariable('streamer',",'streamer=')
#            code = code.replace('));',');')
#            code = code.replace('unescape','')
#            context = js2py.EvalJs()
#            context.execute(code)
#            streamer= getattr(context,'streamer')
#            file= getattr(context,'file')
#            if url_swf and streamer and file:
#                video_url = streamer +' playpath='+file + ' swfUrl='+url_swf[0] + ' swfVfy=1 live=1 timeout=13   pageUrl='+src[0]
#    return video_url
#
#def _sawlivetv2(query,data,url):
#    video_url=''
#    source = getUrl(url)
#    try:
#        contentVideo = jsunpack.unpack(source.decode('string_escape'))
#    except:
#        contentVideo =''
#    src=re.compile('src=["\'](http:.*?)["\']').findall(contentVideo)
#    if src:
#        header = {'Referer':  src[0], 'User-Agent': UA}
#        contentVideo = getUrl(src[0].replace('/view/','/watch/'),header=header)
#        url_swf = re.compile("SWFObject\\('(.*?)'").findall(contentVideo)
#        match = re.compile('(eval\\(function\\(p,a,c,k,e,d\\).*?)\n').findall(contentVideo)
#        if match:
#            contentVideo = jsunpack.unpack(match[0].decode('string_escape'))
#            dec_saw = lambda x: x.group(0).replace('%','').decode('hex')
#            contentVideo = re.sub('%.{2}',dec_saw,contentVideo)
#            code = contentVideo.replace("so.addVariable('file',",'file=')
#            code = code.replace("so.addVariable('streamer',",'streamer=')
#            code = code.replace('));',');')
#            code = code.replace('unescape','')
#            context = js2py.EvalJs()
#            context.execute(code)
#            streamer= getattr(context,'streamer')
#            file= getattr(context,'file')
#            if url_swf and streamer and file:
#                video_url = streamer +' playpath='+file + ' swfUrl='+url_swf[0] + ' swfVfy=1 live=1 timeout=13   pageUrl='+src[0]
#    return video_url

class reqaa(urllib_error.HTTPError):
    def http_response(self, request, response):
        return response
def _pxstream(query,data,url='http://tele-wizja.com/tvp-1/'):
    video_url=''
    header = {'User-Agent':UA,
                'Referer': url,
                'Host':'pxstream.tv',
                'Upgrade-Insecure-Requests':1}
    cj = http_cookiejar.LWPCookieJar()
    contentVideo = get_url_(query,cj,header=header)
    decaa=';'.join(['%s=%s'%(c.name,c.value) for c in cj])
    source = re.compile('(?:src|source)(?:\\:|=)\\s*[\'"](http.*?m3u.)[\'"]').findall(contentVideo)
    if not source:
        source = re.compile('(?:src|source|file)(?:\\:|=)\\s*[\'"](http.+stream.+?m3u.*)[\'"]').findall(contentVideo)
    if source:
        header={'Origin':'http://pxstream.tv',
                'Pragma':'no-cache',
                'Referer':query,
                'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
                'Accept':'*/*',
                'Accept-Encoding':'gzip, deflate',
                'Accept-Language':'en-US,en;q=0.8',
                'Cache-Control':'no-cache',
                }
        cj = http_cookiejar.LWPCookieJar()
        opener = urllib_request.build_opener(reqaa, urllib_request.HTTPCookieProcessor(cj))
        opener.addheaders = header.items()
        response = opener.open(source[0])
        locat = response.headers.get('Location','')
        response.close()
        if locat:
            video_url = locat+'|Referer='+query+'&User-Agent='+UA
    return video_url
#def _myfreshinfo(query,data,url):
#    video_url=''
#    contentDec=getUrl(query)
#    unesc = re.compile('unescape\\(["\'](.*?)["\']\\)').findall(contentDec)
#    unesc2 = unesc[0].replace('%','').decode('hex')
#    funct = re.compile('function (.*?)\\(').findall(unesc2)[0]
#    funct2 = unesc[1].replace('%','').decode('hex')
#    jscript = re.compile('<SCRIPT LANGUAGE="JavaScript">%s\\("(.*?)"\\);</SCRIPT>'%funct,re.DOTALL).findall(contentDec)
#    if jscript:
#        code = jscript[0]
#        code =''+code.strip('\\n')+''
#        try:
#            fun = unesc2.replace('document.write(tttmmm)','return tttmmm')
#            ctx = execjs.compile(fun)
#            contentVideo = ctx.call(funct, code)
#        except:
#            context = js2py.EvalJs()
#            context.execute(fun)
#            contentVideo = getattr(context,funct)(code)
#    return video_url
def _flowplayer(query,data,url):
    video_url=''
    netCon = re.compile("'(rtmp://.*?)'").findall(data)
    url_swf = re.compile("src:'(http://.*?swf)'").findall(data)
    if netCon and url_swf:
        video_url = netCon[0] + ' swfUrl='+url_swf[0] + ' swfVfy=1 live=1 timeout=13  pageUrl='+url
    return video_url
def _cinematvxyz(query,data,url):
    video_url=''
    file = re.compile("url: '(.*?)'").findall(data)
    netCon = re.compile("'(rtmp://.*?)'").findall(data)
    url_swf = re.search('"player", "(.*?.swf)"',data)
    if file and netCon and url_swf:
        video_url = netCon[0] + ' playpath='+file[0].strip() +' swfUrl='+url_swf.group(1) + ' swfVfy=1 live=1 timeout=13  pageUrl='+url
    return video_url
def _shidurlive(query,data,url):
    video_url='TODO'
    return video_url
def _freedocast(query,data,url):
    video_url=''
    link = re.compile('"streamer=(.*?)"').findall(data)
    if link:
        contentDec=link[0].split('&amp;')
        video_url = contentDec[0] +' playpath='+contentDec[1].split('=')[-1] +' swfUrl='+query+ ' swfVfy=1 live=1 timeout=13  pageUrl='+url
    return video_url
def _tvope(query,data,url):
    video_url=''
    feed = re.compile('c="(.*?)"; w=(.*?); h=(.*?);').findall(data)
    query = 'http://tvope.com/emb/player.php?c=%s&w=%s&h=%s&jw&d='%feed[0]
    query +=query+urllib_parse.urlparse(url).hostname
    header = {'User-Agent':UA,
                'Referer': url,
                'Host':'tvope.com'}
    contentVideo = getUrl(query,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    url_swf = re.compile("SWFObject\\('(.*?)'").findall(contentVideo)
    stream = re.compile("'streamer','(.*?)'\\);").findall(contentVideo)
    file   = re.compile("'file','(.*?)'\\);").findall(contentVideo)
    if url_swf and stream and file:
        video_url = stream[0] +' playpath='+file[0] + ' swfUrl='+url_swf[0] + ' swfVfy=1 live=1 timeout=13  pageUrl='+query
    return video_url
def _dotstream(query,data,urlref):
    video_url=''
    query = query.replace('/pl?','/player.php?')
    query = 'http:'+query if query.startswith('//') else query
    header = {'User-Agent':UA,
            'Referer': urlref}
    contentVideo = getUrl(query,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    if contentVideo:
        url_swf = re.compile('swfPath: "(.*?)"').findall(contentVideo)
        url_swf = url_swf[-1] if url_swf else 'http://dotstream.tv/jwp/jwplayer.flash.swf'
        if url_swf.startswith('//'):
            url_swf = 'http:'+url_swf
        vpartm = re.search("v_part_m = '(.*?)';",contentVideo)
        addrpart = re.search("addr_part = '(.*?)';",contentVideo)
        if re.search('a = ([0-9]+)',contentVideo):
            a=int(re.search('a = ([0-9]+)',contentVideo).group(1))
            b=int(re.search('b = ([0-9]+)',contentVideo).group(1))
            c=int(re.search('c = ([0-9]+)',contentVideo).group(1))
            d=int(re.search('d = ([0-9]+)',contentVideo).group(1))
            f=int(re.search('f = ([0-9]+)',contentVideo).group(1))
            v_part = re.search("v_part = '(.*?)';",contentVideo).group(1)
            if a and b and c and d :
                link = 'rtmp://%d.%d.%d.%d/'%(a/f,b/f,c/f,d/f)
            else:
                link = 'rtmp://'+ re.search("addr_part = '(.*?)';",contentVideo).group(1)+'/'
            link = link + v_part.split('/')[1]+'/'+' playpath='+v_part.split('/')[-1]
            video_url = link + ' swfUrl='+url_swf + ' swfVfy=1 live=1 timeout=13 pageUrl='+query
    return video_url
def get_Cookies(url,params=None,header={}):
    try:
        req = urllib_request.Request(url,params,headers=header)
        sock=urllib_request.urlopen(req)
        cookies=sock.info()['Set-Cookie']
        sock.close()
    except:
        cookies=''
    return cookies
def l11l1l1ll1l11l111_tv_(url,params=None,header={}):
    cj = http_cookiejar.LWPCookieJar()
    opener = urllib_request.build_opener( urllib_request.HTTPCookieProcessor(cj))
    urllib_request.install_opener(opener)
    if not header: header = {'User-Agent':UA}
    req = urllib_request.Request(url,params,headers=header)
    try:
        response = urllib_request.urlopen(req,timeout=5)
        response.close()
    except:
        pass
    cookies=''.join(['%s=%s;'%(c.name, c.value) for c in cj])
    return cookies
def get_cookie_value(cookies='',value='sesssid'):
    idx1=cookies.find(value+'=')
    if idx1==-1:
        return ''
    else:
        idx2=cookies.find(';',idx1+1)
    return cookies[idx1:idx2]
    
def _bankaistream(query,data,url):    
    header = {'User-Agent':UA,
            'Referer': url}
    contentVideo = getUrl(query,header=header)    
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    vido_url=re.findall("""source:\s*['"](.+?)['"]""",contentVideo,re.DOTALL)    
    vido_url = vido_url[0] if vido_url else ''
    return vido_url
def _broadcast(query,data,url):
    video_url=''
    if 'st/stream.php' in query:
        url_main = query
    else:
        feed = re.compile('id=[\'"](.*?)[\'"]; width=[\'"](.*?)[\'"]; height=[\'"](.*?)[\'"];').findall(data)
        if feed: url_main='http://bro.adca.st/stream.php?id=%s&p=1&c=0&stretching=uniform&old=0'%feed[0][0]
        else: url_main=''
    if url_main:
        header = {'User-Agent':UA,
                'Referer': url}
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        host ='bro.adca.st'
        url_bro='http://bro.adca.st/aloha.php'
        header = {'User-Agent':UA,
                'Referer': url_main,
                'Host':host,
                'X-Requested-With':'XMLHttpRequest'}
        contentBro = getUrl(url_bro,header=header)
        
        if six.PY3:
            contentBro = contentBro.decode(encoding='utf-8', errors='strict')

        token = re.findall('"rumba":"(.*?)"',contentBro)
        main_url_bro = re.findall('\\w+\\s*=\\s*"(.+?token=)"',contentVideo)
        if main_url_bro and token:
            video_url = main_url_bro[0] + token[0] +'|User-Agent='+urllib_parse.quote(UA)+'&Referer='+url_main
    return video_url
def _111lll1lll11l111_tv_(query,data,url):
    video_url=''
    feed = re.compile('id=[\'"](.*?)[\'"]; width=[\'"](.*?)[\'"]; height=[\'"](.*?)[\'"];').findall(data)
    if feed:
        url_main='http://bro.adca.st/stream.php?id=%s&cache=4&width=%s&height=%s&stretching=uniform&p=1&c=0'%feed[0]
        host ='bro.adca.st'
        header = {'User-Agent':UA,
                'Referer': url,
                'Host':host,
                 }
        cookies=''
        contentVideo = getUrl(url_main,header=header)
        if six.PY3:
            contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        main_url_bro = re.search('curl = "(.*?)"',contentVideo)
        header = {'User-Agent':UA,
                'Referer': url_main,
                'Host':host,
                'X-Requested-With':'XMLHttpRequest'}
        url_bro='http://'+host+'/getToken.php'
        contentBro = getUrl(url_bro,header=header)
        
        if six.PY3:
            contentBro = contentBro.decode(encoding='utf-8', errors='strict')

        token = re.search('"token":"(.*?)"',contentBro)
        if main_url_bro and token:
            cookies= get_Cookies(url_main,header=header)
            h = '|Cookie=%s' % get_cookie_value(cookies,'PHPSESSID')
            l1111ll11ll11l111_tv_='http://cdn.allofme.site/jw/jwplayer.flash.swf'
            link = base64.b64decode(main_url_bro.group(1))
            if six.PY3:
                link = link.decode(encoding='utf-8', errors='strict')
            video_url = link + token.group(1) + h+'&User-Agent='+UA+'&Referer='+l1111ll11ll11l111_tv_
    return video_url
def _jwpcdn(query,data,url):
    video_url=''
    file   = re.compile('[\']*file[\']*[:, ]*[\'"](.*?)[\'"]').findall(data)
    if file:
        file = file[0]
        if file.endswith('m3u8'):
            video_url = file
        else:
            url_swf='http://p.jwpcdn.com/6/12/jwplayer.flash.swf'
            video_url = file + ' swfUrl='+url_swf + ' live=1 timeout=13  pageUrl='+url
    return video_url
def _jwpsrv(query,data):
    video_url=''
    file   = re.compile('[\']*file[\']*[:, ]*[\'"](.*?)[\'"]').findall(data)
    if file:
        file = file[0]
        if file.endswith('m3u8'):
            video_url = file
        else:
            url_swf='http://p.jwpcdn.com/6/12/jwplayer.flash.swf'
            video_url = file + ' swfUrl='+url_swf + ' live=1 timeout=13  pageUrl='+query
    return video_url
def _aliezme(query,data,url):
    video_url=''
    header = {'User-Agent':UA,'Referer': url}
    contentVideo=getUrl(query,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
    video_url   = re.compile("""['"]*(http[^'^"]+?\.m3u8[^'^"]*?)['"]""").findall(contentVideo)
    video_url=video_url[0] +'|User-Agent='+UA+'&Referer='+url  # '|User-Agent='+UA+'&Referer='+next_url[0] #' live=true swfVfy=1 swfUrl=http://i.aliez.me/swf/playernew.swf flashver=WIN\2024,0,0,221 pageUrl=' +next_url[0]
    return video_url
def _ustream(query,data):
    video_url=''
    cid = re.search('cid=(.*?)"',data)
    HLS_PLAYLIST_URL = 'http://iphone-streaming.ustream.tv/uhls/%s/streams/live/iphone/playlist.m3u8'
    if cid:
        cid=cid.group(1)
        data = getUrl(HLS_PLAYLIST_URL%cid)
        if six.PY3:
            data = data.decode(encoding='utf-8', errors='strict')

        if data:
            links = re.compile('\n(http.*?)\n').findall(data)
            if links:
                video_url = links[0]
    return video_url
def _privatestream(query,data):
    video_url=''
    query = 'http:'+query if query.startswith('//') else query
    if 'js?' in query:
        tmp = getUrl(query)
        src2 = re.compile('src=["\'](.*?)["\']',re.IGNORECASE).findall(tmp)
        if src2:
            src2 = src2[0]
            query = 'http:'+src2 if src2.startswith('//') else src2
    contentVideo = getUrl(query)
    url_main=[]
    if url_main:
        url_swf = re.compile('swfPath: "(http.*?)"').findall(contentVideo)
        url_swf = url_swf[-1] if url_swf else 'http://privatestream.tv/clappr/RTMP.swf?inline=1'
        url_swf='http://privatestream.tv/clappr/RTMP.swf'
        a=int(re.search('a = ([0-9]+)',contentVideo).group(1))
        b=int(re.search('b = ([0-9]+)',contentVideo).group(1))
        c=int(re.search('c = ([0-9]+)',contentVideo).group(1))
        d=int(re.search('d = ([0-9]+)',contentVideo).group(1))
        f=int(re.search('f = ([0-9]+)',contentVideo).group(1))
        v_part = re.search("v_part = '(.*?)';",contentVideo).group(1)
        link = 'rtmp://%d.%d.%d.%d/'%(a/f,b/f,c/f,d/f) + v_part.split('/')[1]+'/'+' playpath='+v_part.split('/')[-1]
        video_url = link + ' swfUrl='+url_swf + ' live=1 timeout=13 pageUrl='+query
    elif contentVideo:
        vpartm = re.search("v_part_m = '(.*?)';",contentVideo)
        addrpart = re.search("addr_part = '(.*?)';",contentVideo)
        url_swf='http://privatestream.tv/clappr/RTMP.swf'
        if re.search('a = ([0-9]+)',contentVideo):
            a=int(re.search('a = ([0-9]+)',contentVideo).group(1))
            b=int(re.search('b = ([0-9]+)',contentVideo).group(1))
            c=int(re.search('c = ([0-9]+)',contentVideo).group(1))
            d=int(re.search('d = ([0-9]+)',contentVideo).group(1))
            f=int(re.search('f = ([0-9]+)',contentVideo).group(1))
            v_part = re.search("v_part = '(.*?)';",contentVideo).group(1)
            if a and b and c and d :
                link = 'rtmp://%d.%d.%d.%d/'%(a/f,b/f,c/f,d/f)
            else:
                link = 'rtmp://'+ re.search("addr_part = '(.*?)';",contentVideo).group(1)+'/'
            link = link + v_part.split('/')[1]+'/'+' playpath='+v_part.split('/')[-1]
            video_url = link + ' swfUrl='+url_swf + ' swfVfy=1 live=1 timeout=13 pageUrl='+query
    return video_url
def _casttome(query,url,data):
    video_url =''
    feed = re.compile('fid="(.*?)"; v_width=(.*?); v_height=(.*?);').findall(data)
    if feed:
        url_main='http://static.castto.me/embedlivesrclappr.php?channel=%s&vw=%s&vh=%s'%feed[0]
    else:
        url_main=query
    header = {'User-Agent':UA,
            'Referer': url,
            'Host':'static.castto.me',
            }
    contentVideo = getUrl(url_main,header=header)
    if six.PY3:
        contentVideo = contentVideo.decode(encoding='utf-8', errors='strict')
        
    file   = re.compile('file\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
    if file:
        video_url = file[-1]
    file   = re.compile('source\\s*:\\s*["\'](.*?)[\'"]').findall(contentVideo)
    if file:
        video_url = file[-1]
    file   = re.compile('<source src=["\'](.*?)[\'"]').findall(contentVideo)
    if file:
        video_url = file[-1]
    if video_url:
        video_url += '|User-Agent='+urllib_parse.quote(UA)+'&Referer='+url_main+'&Cookie='+urllib_parse.quote('userid=264414038;')
    return video_url
