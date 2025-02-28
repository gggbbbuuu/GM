import sys
import re
import json
from urllib.parse import quote_plus, unquote_plus, urljoin, urlencode
from typing import List, Optional, Dict
from base64 import b64decode
from dateutil.tz import tzlocal
from datetime import datetime
import xbmc
import xbmcgui
import requests
from bs4 import BeautifulSoup
from ..plugin import Plugin
from ..DI import DI
from ..util.common import ownAddon

KODI_VER = float(xbmc.getInfoLabel("System.BuildVersion")[:4])

def get_timezone_offset():
    current_time = datetime.now(tzlocal())
    t_offset = current_time.utcoffset().total_seconds()/3600
    return t_offset

timefixset = ownAddon.getSetting('timefix_')
if not timefixset or timefixset == "":
    timefix = int(get_timezone_offset())
    ownAddon.setSetting('timefix_', 'Auto')
    # ownAddon.setSetting('timefix_', '{0:+d}'.format(timefix))
else:
    if not timefixset == "Auto":
        timefix = int(timefixset)
    else:
        timefix = int(get_timezone_offset())

class Ddlv(Plugin):
    name = "Daddy"
    priority = 10
    
    def __init__(self):
        self.session = DI.session
        self.base_url = 'https://dlhd.so'
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        self.session.headers = {"User-Agent": self.user_agent, "Referer": self.base_url}
        self.schedule_url = urljoin(self.base_url, '/schedule/schedule-generated.json')
        self.extra_url = urljoin(self.base_url, '/schedule/schedule-extra-generated.json')
        self.channels_url = f'{self.base_url}/24-7-channels.php'
        self.addon_icon = 'https://raw.githubusercontent.com/thecrewwh/zips/master/matrix/_zip/plugin.video.daddylive/icon.png' or ownAddon.getAddonInfo('icon')
        self.addon_fanart = 'https://raw.githubusercontent.com/thecrewwh/zips/master/matrix/_zip/plugin.video.daddylive/fanart.jpg' or ownAddon.getAddonInfo('fanart')
    

    def get_list(self, url: str) -> Optional[Dict]:
        if not url.startswith('ddlv'):
            return
            
        if url.startswith('ddlv/channels'):
            return self.session.get(self.channels_url, timeout=10).text
            
        if url == 'ddlv': 
            schedule = self.session.get(self.schedule_url, timeout=10).json()
            extra = self.session.get(self.extra_url, timeout=10).json()
            schedule.update(extra)
            return json.dumps(schedule)
        elif url.startswith('ddlv/cats/'):
            return unquote_plus(url.replace('ddlv/cats/', ''))
        elif url.startswith('ddlv/events/'):
            return unquote_plus(url.replace('ddlv/events/', ''))
    
    
    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith('ddlv'):
            return
            
        itemlist = []
        title = ''
        link = ''
        
        if url == 'ddlv/channels':
            soup = BeautifulSoup(response, 'html.parser')
            channels = []
            for a in soup.find_all('a')[7:]:
                title = a.text
                link = json.dumps([[title, f"{self.base_url}{a['href']}"]])
                if not link in channels:
                    channels.append(link)
                    itemlist.append(
                        {
                            'type': 'item',
                            'title': title,
                            'link': link,
                            "thumbnail": self.addon_icon, 
                            "fanart": self.addon_fanart,
                            'summary': title
                        }
                    )
            return itemlist
            
        response = json.loads(response)
        
        if url.startswith('ddlv/events/'):
            for event in response:
                time_ = event.get('time','00:00')
                hour = int(time_.split(':')[0])
                dt = timefix
                new_hour = (hour + dt) % 24
                new_hour = str(new_hour).zfill(2)+ ':' + time_.split(':')[1]
                channels_ = event.get('channels', [])
                title = event.get('event', '')
                title = '[COLOR orange]'+new_hour+'[/COLOR]'+' '+title
                title = '[B]'+title+'[/B]'
                if len(channels_)>1:
                    title = title+'[CR][I][COLOR grey]Multilink ('+str(len(channels_))+' Channels)[/COLOR][/I]'
                link = json.dumps([[channel.get('channel_name'), urljoin(self.base_url, f"/stream/stream-{channel.get('channel_id')}.php")] for channel in channels_])
                itemlist.append(
                    {
                        'type': 'item',
                        'title': title,
                        'link': link,
                        "thumbnail": self.addon_icon, 
                        "fanart": self.addon_fanart,
                        'summary': title
                    }
                )
            return itemlist
        
        itemlist.append(
            {
                'type': 'dir',
                'title': 'Channels',
                'link': 'ddlv/channels',
                "thumbnail": self.addon_icon, 
                "fanart": self.addon_fanart,
                'summary': title
            }
        )
        
        for key in response.keys():
            if url == 'ddlv':
                title = key.split(' -')[0]
                link = f'ddlv/cats/{quote_plus(json.dumps(response[key]))}'
            elif url.startswith('ddlv/cats/'):
                title = key
                link = f'ddlv/events/{quote_plus(json.dumps(response[key]))}'
                
            itemlist.append(
                {
                    'type': 'dir',
                    'title': title,
                    'link': link,
                    "thumbnail": self.addon_icon, 
                    "fanart": self.addon_fanart,
                    'summary': title
                }
            )
        return itemlist


    def play_video(self, item: str) -> Optional[bool]:
        if self.base_url in str(item):
            item = json.loads(item)
            url = json.loads(item['link'])
            if isinstance(url, list):
                if len(url) > 1:
                    url = self.get_multilink(url)
                    if not url:
                        sys.exit()
                else:
                    url = url[0][1]
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            iframe = soup.find('iframe', attrs={'id': 'thatframe'})
            if iframe:
                url2 = iframe.get('src')
                if url2:
                    headers = {
                        'User-Agent': self.user_agent,
                        'Referer': url
                    }
                    response2 = requests.get(url2, headers=headers, timeout=10).text
                    try:
                        link=re.compile("\"file\":\s*'(.+?)'").findall(response2)[-1]
                        try:
                            link = b64decode(link).decode('utf-8')
                        except:
                            pass
                        # xbmcgui.Dialog().textviewer('url_b_def',url_b)
                    except:
                        try:
                            link = re.compile('"(aHR0.+?)"').findall(response2)[-1]
                            try:
                                link = b64decode(link).decode('utf-8')
                            except:
                                pass
                        except:
                            try:
                                link = re.compile('encryptedSource\s*=\s*"(.+?)"').findall(response2)[-1]
                                try:
                                    link = b64decode(link).decode('utf-8')
                                except:
                                    pass
                            except:
                                try:
                                    link = re.compile("source:\s*'(.+?)'").findall(response2)[-1]
                                    try:
                                        link = b64decode(link).decode('utf-8')
                                    except:
                                        pass
                                except:
                                    link = decode_url(response2)
                                    try:
                                        link = b64decode(link).decode('utf-8')
                                    except:
                                        pass
                    if link:
                        referer = quote_plus(url2)
                        user_agent = quote_plus(self.user_agent)
                        headers_ = f'Referer={referer}&Origin={referer}&User-Agent={user_agent}'
                        link = f'{link}|{headers_}'
                        liz = xbmcgui.ListItem(item['title'], path=link)
                        liz.setInfo(
                        "video", {"plot": item['summary'], "plotoutline": item['summary']}
                        )
                        liz.setArt({'thumb': self.addon_icon, 'icon': self.addon_icon, 'poster': self.addon_icon})
                        liz.setMimeType('application/xml+dash')
                        liz.setContentLookup(False)
                        liz.setProperty('inputstream', 'inputstream.adaptive')
                        liz.setProperty('inputstream.adaptive.manifest_headers', headers_)
                        liz.setProperty('inputstream.adaptive.stream_headers', headers_)
                        if KODI_VER < 21:
                            liz.setProperty('inputstream.adaptive.manifest_type', 'hls') # Deprecated on Kodi 21
                        # liz.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                        license_headers = {
                            'User-Agent': self.user_agent,
                            'Referer': 'https://weblivehdplay.ru',
                            'Origin': 'https://weblivehdplay.ru'
                        }
                        license_config = {
                            'headers': urlencode(license_headers)
                        }
                        license_key = f"|{'|'.join(license_config.values())}||"
                        #license_key = '|Referer=https://weblivehdplay.ru&Origin=https://weblivehdplay.ru'
                        liz.setProperty('inputstream.adaptive.license_key', license_key)
                        liz.setProperty('IsPlayable', 'true')
                        xbmc.Player().play(link, listitem=liz)
                        return True
    
    
    def get_multilink(self, lists, lists2=None, trailers=None):
        labels = []
        links = []
        counter = 1
        if lists2 is not None:
            for _list in lists2:
                lists.append(_list)
        for _list in lists:
            if isinstance(_list, list) and len(_list) == 2:
                if len(lists) == 1:
                    return _list[1]
                labels.append(_list[0])
                links.append(_list[1])
            elif isinstance(_list, str):
                if len(lists) == 1:
                    return _list
                if _list.strip().endswith(')'):
                    labels.append(_list.split('(')[-1].replace(')', ''))
                    links.append(_list.rsplit('(')[0].strip())
                else:
                    labels.append('Link ' + str(counter))
                    links.append(_list)
            else:
                return
            counter += 1
        if trailers is not None:
            for name, link in trailers:
                labels.append(name)
                links.append(link)
        dialog = xbmcgui.Dialog()
        ret = dialog.select('Choose a Link', labels)
        if ret == -1:
            return
        if isinstance(lists[ret], str) and lists[ret].endswith(')'):
            link = lists[ret].split('(')[0].strip()
            return link
        elif isinstance(lists[ret], list):
            return lists[ret][1]
        return lists[ret]

def __duf(d,e,f):
    _0xce1e="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
    g = list(_0xce1e)
    h = g[0:e]
    i = g[0:f]
    d = list(d)[::-1]
    j = 0
    for c,b in enumerate(d):
        if b in h:
            j = j + h.index(b)*e**c
 
    k = ""
    while j > 0:
        k = i[j%f] + k
        j = (j - (j%f))//f
 
    return int(k) or 0

def hunter(h,u,n,t,e,r):
    r = ""
    i = 0
    while i < len(h):
        j = 0
        s = ""
        while h[i] is not n[e]:
            s = ''.join([s,h[i]])
            i = i + 1
 
        while j < len(n):
            s = s.replace(n[j],str(j))
            j = j + 1
 
        r = ''.join([r,''.join(map(chr, [__duf(s,e,10) - t]))])
        i = i + 1
 
    return r

def decode_url(text: str) -> str:
    pattern =  'decodeURIComponent\(.+?"(.+?)",(.+?),"(.+?)",(.+?),(.+?),(.+?)\)'
    x = re.findall(pattern, text)[0]
    y = hunter(x[0], int(x[1]), x[2], int(x[3]), int(x[4]), int(x[5]))
    z = re.findall("'(.+?)';", y)[0]
    link = b64decode(z).decode()
    return link