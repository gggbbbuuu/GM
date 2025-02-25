import requests
from bs4 import BeautifulSoup
# from urllib.parse import urlparse
from urllib.parse import urlparse, quote_plus
from dateutil import parser
from datetime import datetime, timedelta
import re
import xbmc
import json
from requests.sessions import Session
session = Session()

from ..models import *
from ..util import m3u8_src

class Daddylive(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["daddylive.mp","thedaddy.to","dlhd.so","1.dlhd.sx","dlhd.sx", "d.daddylivehd.sx", "daddylive.sx", "daddylivehd.com","ddh1new.iosplayer.ru/ddh2","zekonew.iosplayer.ru/zeko"]
        self.name = "Daddylive"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        unique_hrefs = set()
        count = 0
        duplicate_count = 0
        r: dict = requests.get(f"https://{self.domains[0]}/schedule/schedule-generated.json", timeout=self.timeout).json()

        for header, events in r.items():
            for event_type, event_list in events.items():
                for event in event_list:
                    title = event.get("event", "")
                    starttime = event.get("time", "")
                    league = event_type
                    channels = event.get("channels", [])
                    if isinstance(channels, dict):
                        channels = channels.values()
                    try:
                        utc_time = self.parse_header(header, starttime) - timedelta(hours=1)
                    except:
                        try:
                            utc_time = datetime.now().replace(hour=int(starttime.split(":")[0]), minute=int(starttime.split(":")[1])) - timedelta(hours=1)
                        except:
                            utc_time = datetime.now()
                    
                    items.append(JetItem(
                        title,
                        [JetLink(f"https://{self.domains[0]}/stream/stream-{channel['channel_id']}.php", name=channel["channel_name"]) for channel in channels],
                        league=league,
                        starttime=utc_time
                    ))
        
        if self.progress_update(progress):
            return items

        r_channels = requests.get(f"https://{self.domains[0]}/24-7-channels.php", timeout=self.timeout)
        soup_channels = BeautifulSoup(r_channels.text, "html.parser")
        A_link = soup_channels.find_all('a')[:2]
        b_link = soup_channels.find_all('a')[8:]
        links = A_link + b_link
        for link in links:
            title = link.text
            if '18+' in title:
                del title
                continue
            
            href = f"https://{self.domains[0]}{link['href']}"
            if href in unique_hrefs:
                duplicate_count += 1
                continue
            unique_hrefs.add(href)
            count += 1
            items.append(JetItem(title, links=[JetLink(href)], league="[COLORorange]24/7"))
        
        return items

    def get_link(self, url: JetLink) -> JetLink:
        if "/embed/" not in url.address and "/channels/" not in url.address and "/stream/" not in url.address and "/cast/" not in url.address and "/batman/" not in url.address and "/extra/" not in url.address:
            raise Exception("Invalid URL")
                             
        response = session.get(url.address, timeout=10).text                       
        soup = BeautifulSoup(response, 'html.parser')
        iframe = soup.find('iframe', attrs={'id': 'thatframe'})                                    
        iframe_url = iframe.get('src') 
        m =  m3u8_src.scan_page(iframe_url)
        if m is not None and "Referer" in m.headers:
            referer = m.headers["Referer"]
            origin = f"https://{urlparse(referer).netloc}"
            referer = f"https://{urlparse(referer).netloc}/"   
        iframe_response = session.get(iframe_url, timeout=10).text                                  
        server_info = re.findall(r'var m3u8Url = "(.+?)";', iframe_response)                      
        channel_key = re.findall(r'var channelKey.+?\"(.+?)\"', iframe_response, re.DOTALL)        
        server_info = re.findall(r'var m3u8Url\s*=(.+?);', iframe_response, re.DOTALL)      
        channelKey = channel_key[0]
        server_key_url = f'{origin}/server_lookup.php?channel_id={channelKey}'
        response = session.get(server_key_url, timeout=10) 
        key_data = json.loads(response.text)
        serverKey = key_data["server_key"]
        server_data = server_info[0].splitlines()  
        
        for s in server_data :      
            if 'http' in s.lower() and 'serverkey' in s.lower() :                   
                    server_url = ""                                 
                    if s.endswith(':'): s = s[:-1]  
                    
                    server_url = s.replace(
                        'channelKey', channelKey).replace(
                        'serverKey', serverKey).replace(
                        '"', '').replace(
                        ' ', '') .replace(
                        '+', '') 
                                                                                      
        m3u8_url = server_url
        
        headers = {
                "Origin":origin ,
                "Referer": referer,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            }
        
        m3u8 = JetLink(address=m3u8_url, headers=headers)
        m3u8.inputstream = JetInputstreamFFmpegDirect.default()
        return m3u8
               
    def parse_header(self, header, time):
        timestamp = parser.parse(header[:header.index("-")] + " " + time)
        timestamp = timestamp.replace(year=2024)  # daddylive is dumb
        return timestamp