import requests, re
from bs4 import BeautifulSoup
from dateutil.parser import parse
from dateutil.parser import parse
from datetime import timedelta, datetime

from ..models import *
from ..util.m3u8_src import scan_page

class Crackstream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["thecrackstreams.to"]
        self.name = "Crackstreams"
        self.short_name = "CS"

#######  NEED FIXING  ########    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        leagues = ["nba-streams", "nhl-streams","nfl-streams","boxing-streams","cfb-streams","mma-streams","soccerstreams","wwe-streams"]
        for league in leagues:
            r = requests.get(f"https://thecrackstreams.to/crackstreams/{league}/", timeout=self.timeout).text
            soup = BeautifulSoup(r, "html.parser")
            game = soup.select("li.f1-podium--item > a")
            if self.progress_update(progress, league):
                        return items
            
            for stream in game:
                title = stream.select_one(".f1-podium--driver").text.strip()  # Get the title of the stream
                href = stream.get('href')
                # if self.progress_update(progress, title):
                #         return items
                items.append(JetItem(title=title, links=[JetLink(href)]))

        return items
    
    


    def get_link(self, url: JetLink) -> JetLink:
        m3u8 = ""
        video_html = requests.get(url.address).text
        video = BeautifulSoup(video_html, "html.parser")
        if len(video.find_all("iframe")) > 0:
            iframe = video.find("iframe").get("src")
            r_iframe = requests.get(iframe).text
            m3u8 = JetLink(address=re.compile(r"source: ['\"](.+?)['\"]").findall(r_iframe)[0].replace(".m3u8", ".m3u8?&Connection=keep-alive"))
        else:
            m3u8 = scan_page(url.address, video_html)
        return m3u8
