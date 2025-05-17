import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from urllib.parse import urlencode, quote, unquote, parse_qsl, quote_plus, urlparse, urlunparse
import base64
import traceback
from dateutil import parser
from datetime import datetime, timedelta
import re
import json
import logging
import xbmcvfs
import os
from requests.sessions import Session

from ..models import *
from ..util import m3u8_src, find_iframes

logger = logging.getLogger(__name__)
LOGPATH = xbmcvfs.translatePath('special://logpath/')
FILENAME = 'daddylive.log'
LOG_FILE = os.path.join(LOGPATH, FILENAME)

def log_debug(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now()}: {msg}\n")
        logger.debug(msg)
    except Exception as e:
        logger.error(f"Logging failed: {str(e)}")

# STREAM_DOMAINS = {
#     "windnew": "wind",
#     "zekonew": "zeko",
#     "nfsnew": "nfs",
#     "solarnew": "solar",
#     "lunanew": "luna",
#     "staronew": "staro",
#     "metalnew": "metal"
# }

STD_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'

class Daddylive(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["daddylive.dad","daddylive.mp","thedaddy.to","dlhd.so","1.dlhd.sx","dlhd.sx", "d.daddylivehd.sx", "daddylive.sx", "daddylivehd.com","ddh1new.iosplayer.ru/ddh2","zekonew.iosplayer.ru/zeko"]
        self.name = "Daddylive"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        unique_hrefs = set()
        count = 0
        duplicate_count = 0
        # r: dict = requests.get(f"https://{self.domains[0]}/schedule/schedule-generated.json", timeout=self.timeout).json()
        
        sched_headers = {
                "Origin": f'https://{self.domains[0]}', 
                "Referer": f'https://{self.domains[0]}/', 
                "User-Agent": STD_AGENT
                }
        
        sched_url = f"https://{self.domains[0]}/schedule/schedule-generated.php" 
        r: dict = requests.get(sched_url, headers=sched_headers).json()         
        
        for header, events in r.items():
            for event_type, event_list in events.items():
                for event in event_list:
                    title = event.get("event", "")
                    starttime = event.get("time", "")
                    league = event_type.replace("</span>", "")
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

        session = Session()
        headers = {
            "User-Agent": self.user_agent,
            "Referer": f"https://{urlparse(url.address).netloc}/",
            "Origin": f"https://{urlparse(url.address).netloc}"
        }

        try:
            log_debug(f"Fetching URL: {url.address}")
            current_url = url.address
            if "/stream/" in current_url:
                # Try /cast/ URL if /stream/ fails
                try:
                    response = session.get(current_url, headers=headers, timeout=10).text
                    soup = BeautifulSoup(response, 'html.parser')
                    iframe = soup.find('iframe', attrs={'id': 'thatframe'})
                    if not iframe:
                        current_url = current_url.replace('/stream/', '/cast/')
                        response = session.get(current_url, headers=headers, timeout=10).text
                        soup = BeautifulSoup(response, 'html.parser')
                        iframe = soup.find('iframe', attrs={'id': 'thatframe'})
                except:
                    current_url = current_url.replace('/stream/', '/cast/')
                    response = session.get(current_url, headers=headers, timeout=10).text
                    soup = BeautifulSoup(response, 'html.parser')
                    iframe = soup.find('iframe', attrs={'id': 'thatframe'})
            else:
                response = session.get(current_url, headers=headers, timeout=10).text
                soup = BeautifulSoup(response, 'html.parser')
                iframe = soup.find('iframe', attrs={'id': 'thatframe'})

            if not iframe:
                raise Exception("No iframe found with id='thatframe'")
            iframe_url = iframe['src']
            log_debug(f"Iframe URL: {iframe_url}")

            response = session.get(iframe_url, headers=headers, timeout=10).text
            log_debug(f"Cookies after iframe request: {session.cookies.get_dict()}")
            pattern = r'var\s+(\w+)\s*=\s*"([^"]+)"'
            matches = re.findall(pattern, response)
            variables = dict(matches)
            
            channel_key = variables.get('channelKey')
            auth_ts = variables.get('authTs')
            auth_rnd = variables.get('authRnd')
            auth_sig = quote(variables.get('authSig', ''))
            
            if not all([channel_key, auth_ts, auth_rnd, auth_sig]):
                raise Exception("Missing authentication parameters")
            log_debug(f"Channel Key: {channel_key}")

            # Perform auth request
            auth_url = f'https://top2new.newkso.ru/auth.php?channel_id={channel_key}&ts={auth_ts}&rnd={auth_rnd}&sig={auth_sig}'
            headers['Referer'] = iframe_url
            session.get(auth_url, headers=headers, timeout=10)

            server_lookup_url = f"https://{urlparse(iframe_url).netloc}/server_lookup.php?channel_id={channel_key}"
            headers['Origin'] = f"https://{urlparse(iframe_url).netloc}"
            response = session.get(server_lookup_url, headers=headers, timeout=10).json()
            log_debug(f"Server Lookup Response: {response}")
            server_key = response.get('server_key')
            if not server_key:
                raise Exception("No server_key found")
            log_debug(f"Server Key: {server_key}")

            m3u8 = f'https://{server_key}new.newkso.ru/{server_key}/{channel_key}/mono.m3u8'
            referer = f'https://{urlparse(iframe_url).netloc}'
            m3u8_url = f'{m3u8}|Referer={referer}/&Origin={referer}&Connection=Keep-Alive&User-Agent={self.user_agent}'

            m3u8_link = JetLink(address=m3u8_url)
            m3u8_link.inputstream = JetInputstreamFFmpegDirect.default()
            m3u8_link.inputstream.is_realtime_stream = True
            m3u8_link.inputstream.stream_mode = "timeshift"
            m3u8_link.inputstream.manifest_type = "hls"
            return m3u8_link
        except Exception as e:
            log_debug(f"Error in get_link: {str(e)}\n{traceback.format_exc()}")
            raise
               
    def parse_header(self, header, time):
        timestamp = parser.parse(header[:header.index("-")] + " " + time)
        timestamp = timestamp.replace(year=2024)  # daddylive is dumb
        return timestamp