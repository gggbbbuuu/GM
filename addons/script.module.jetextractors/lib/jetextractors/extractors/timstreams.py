from ..models import JetExtractor, JetExtractorProgress, JetItem, JetLink, JetInputstreamFFmpegDirect
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs

import base64
import pytz
from dateutil.parser import parse

default_zone = pytz.timezone('GMT') 
utc_zone = pytz.timezone('UTC')
uk_zone = pytz.timezone('Europe/London')
usa_zone = pytz.timezone('US/Eastern')         
usa_zone2 = pytz.timezone('US/Central')

############
import xbmcvfs 
from dateutil import parser
from datetime import datetime, timedelta
import os

LOGPATH = xbmcvfs.translatePath('special://logpath/')
FILENAME = 'tim.log'
LOG_FILE = os.path.join(LOGPATH, FILENAME)

#-----------------------------
def log_debug(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now()}: {msg}\n")
    except Exception as e:
        f.write(f"{datetime.now()}: Logging failed: {str(e)}\n")
        
#-----------------------------
class TimStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["timstreams.xyz","kleanpro.cfd"]
        self.name = "TimStreams"
        self.user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.headers = {
            "User-Agent": self.user_agent,
            "Referer": f"https://{self.domains[0]}/"
             }
             
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
                    
        base_html = requests.get(f"https://{self.domains[0]}", headers=self.headers, timeout=10)                
        API_URL = re.search(r'API_ENDPOINT\s*=\s*[\'"]([^\'"]+)[\'"]', base_html.text).group(1)        
        api_data = requests.get(API_URL, headers=self.headers, timeout=10).json()
        
        # --- Extract genre arrays from base_html  ---
        def extract_categories(array_name):
            match = re.search(rf'{array_name}\s*=\s*\[(.*?)\];', base_html.text, re.DOTALL)
            if not match:
                return []          
            return [{"id": int(id_), "name": name} for id_, name in re.findall(r'\{\s*id:\s*(\d+),\s*name:\s*"([^"]+)"\s*\}', match.group(1))]

        sports_categories = extract_categories("sports_categories")
        channel_categories = extract_categories("channel_categories")
               
        # Build lookup dicts for genre mapping
        sports_dict = {c["id"]: c["name"] for c in sports_categories}
        channel_dict = {c["id"]: c["name"] for c in channel_categories}
            
        for item in api_data:          
            cat = item.get("category")
            
            if cat not in ("Events", "24/7"):
                continue  
                
            genre_map = sports_dict if cat == "Events" else channel_dict
            
            for ev in item.get("events", []):            
                title = ev.get("name")
                if 'big brother' in title.lower() : continue
                
                # link_list = [stream.get("url") for stream in ev.get("streams", [])]                 
                link = next((stream.get("url") for stream in ev.get("streams", [])), None)
                
                start_time = ev.get("time", None)
                if start_time : 
                    start_time = parse(start_time)
                                
                if isinstance(start_time, datetime):               
                    try:
                        sched_dt = start_time
                        # Ensure datetime is timezone-aware
                        if sched_dt and sched_dt.tzinfo is None:
                            # Set base timezone 
                            sched_dt = uk_zone.localize(sched_dt)
                            # offset to UTC
                            utc_dt = sched_dt.astimezone(pytz.UTC)
                    except Exception:
                        sched_dt = utc_dt = None
                                                                        
                if cat.lower() == '24/7' : 
                    league = 'Channel' 
                else : 
                    league = genre_map.get(ev.get("genre"), "unknown")       
     
                if link : 
                    items.append(JetItem(title,[JetLink(link, headers=self.headers)] , league=league, starttime=utc_dt ))
                    
        return items
        
    def get_link(self, url):                                       
        if not url : return None   
   
        html = requests.get(url.address, headers={"User-Agent": self.user_agent, "Referer": f"https://{self.domains[0]}/"}).text    
        match = re.search(r"eval\(atob\('([^']+)'\)\)", html)
        
        if not match:
            return None 

        b64_data = match.group(1)
        decoded_js = base64.b64decode(b64_data).decode("utf-8")
            
        url_match = re.search(r'const initUrl\s*=\s*"([^"]+)"', decoded_js)
        
        if not url_match:
            return None

        stream_url = url_match.group(1)
        parsed_url = urlparse(stream_url)
        
        stream_headers = {
            "Referer": "{parsed_url.scheme}://{parsed_url.netloc}/",
            "User-Agent": "Mozilla/5.0"
            }
    
        playlist_b64 = requests.get(stream_url, headers=stream_headers).text    
        decoded_playlist = base64.b64decode(playlist_b64).decode("utf-8")    
                                   
        return JetLink(decoded_playlist, headers={"User-Agent": self.user_agent, "Referer": f"https://{self.domains[0]}/"})
        # return JetLink(decoded_playlist, headers={"User-Agent": self.user_agent, "Referer": f"https://{self.domains[0]}/"}, inputstream=JetInputstreamFFmpegDirect.default())  
        
      
      