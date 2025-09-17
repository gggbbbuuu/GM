from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
from typing import Optional, List
import time
from datetime import datetime, timedelta
import requests
import re
from ..util import m3u8_src
from urllib3.util import SKIP_HEADER

BASE_URL = 'https://ppv.to'
API_URL = f'{BASE_URL}/api/streams'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
HEADERS = {
    'User-Agent': USER_AGENT,
    'Referer': f'{BASE_URL}/',
    'Origin': f'{BASE_URL}/'
}


class PPVLand(JetExtractor):
    domains = ["ppv.to", "ppvs.su"]
    name = "PPV Land"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        response = requests.get(API_URL, headers=HEADERS, timeout=self.timeout)
        if response.status_code != 200:
            return items
        result = response.json()
        if result.get('success') is not True:
            return items
        for cat in result.get('streams', []):
            category = cat.get('category')
            for stream in cat.get('streams', []):
                start_time = stream['starts_at']
                end_time = stream['ends_at'] + 3600
                if self.is_today(start_time) is False and self.is_today(end_time) is False and self.is_tomorrow(start_time) is False and stream['always_live'] == 0:
                    continue
                title = stream['name']
                _id = stream['id']
                link = f'{API_URL}/{_id}'
                thumbnail = stream['poster']
                if stream['always_live'] == 0:
                    #title += f' - {self.structure_date(start_time)}'
                    items.append(JetItem(title, links=[JetLink(link, links=True)], icon=thumbnail, league=category, starttime=datetime.fromtimestamp(start_time+18000)))
                else:
                    items.append(JetItem(title, links=[JetLink(link, links=True)], icon=thumbnail, league=category))
        return items
    
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        if '/api/' not in url.address:
            response = requests.get(url.address, headers=HEADERS, timeout=self.timeout)
            match = re.search(r'var FS_STREAM_ID = (\d+);', response.text)
            if match:
                stream_id = match.group(1)
                url.address = f'{API_URL}/{stream_id}'
        response = requests.get(url.address, headers=HEADERS, timeout=self.timeout)
        if response.status_code != 200:
            return links
        result = response.json()
        if result.get('success') is not True:
            return links
        
        link = result['data']['m3u8']
        if link:
            links.append(JetLink(link, headers=HEADERS,  inputstream=JetInputstreamFFmpegDirect.default()))
        for source in result["data"]["sources"]:
            links.append(JetLink(source["data"], name=f'{source["name"]} [{source["type"]}]'))
        return links
    
    def get_link(self, url: JetLink) -> JetLink:
        return m3u8_src.scan_page(url.address, headers={"Accept-Encoding": SKIP_HEADER})
    
    def is_today(self, timestamp: int) -> bool:
        date = datetime.fromtimestamp(timestamp)
        today = datetime.today()
        return date.year == today.year and date.month == today.month and date.day == today.day
    
    def is_tomorrow(self, timestamp:int) -> bool:
        date = datetime.fromtimestamp(timestamp)
        tomorrow =  datetime.today() + timedelta(days=1)
        return date.year == tomorrow.year and date.month == tomorrow.month and date.day == tomorrow.day
    
    def structure_date(self, timestamp: int) -> str:
        local = time.localtime(timestamp)
        return time.strftime('%b %d, %Y - %I:%M %p', local)