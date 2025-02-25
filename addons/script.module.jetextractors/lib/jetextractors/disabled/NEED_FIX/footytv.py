
import requests, re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes
from .voodc import Voodc

class FootyBiteTV(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["www.footybite.watch"]
        self.name = "FootyBiteTV"
#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for game in soup.select("tbody > tr"):
            tds = game.select("td")
            name = tds[1].text
            game_time = tds[0].text
            hour = int(game_time[0])
            minute = int(game_time[1])
            utc_time = datetime.now().replace(hour=hour, minute=minute) + timedelta(hours=23)
            
            if not name:
                continue
            href = game.find("a").get("href")
            if self.progress_update(progress, name):
                        return items
            xbmc.sleep(200)
            items.append(JetItem(name, starttime=utc_time, links=[JetLink(href)]))
        return items


    def get_links(self, url):
        r = requests.get(url).text
        soup = BeautifulSoup(r, "html.parser")
        links = [JetLink(link.get("href"), name=link.text) for link in soup.select("center > a")]
        if len(links) == 0:
            links = [JetLink(url)]
        return links


    def get_link(self, url):
        r = requests.get(url).text
        iframe = re.findall("iframe.+src=\"(.+?)\"", r)[0]
        if "voodc" in iframe:
            return Voodc().get_link(iframe)
        else:
            iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(iframe, "", [], [])]
            return iframes[0]
        


