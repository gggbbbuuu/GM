from ..models import *
from .embedsports import Embedsports
from .streamscenter import StreamsCenter
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ..util import find_iframes

class StreamEast(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["the.streameast.xyz", "^(?:the)?streameast\....?"]
        self.domains_regex = True
        self.name = "TheStreamEast"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}")
        soup = BeautifulSoup(r.text, "html.parser")
        for category in soup.select("div.category-block"):
            category_name = category.select_one("h2").text
            for match in category.select("div.match-item"):
                a = match.select_one("a")
                title = a.text
                href = a.get("href")
                if time_badge := match.select_one("span.today-badge"):
                    match_time = datetime.fromtimestamp(int(time_badge.get("data-starttime"))) + timedelta(hours=7)
                else:
                    match_time = None
                items.append(JetItem(title, [JetLink(href, links=True)], starttime=match_time, league=category_name))
        return items

    def get_links(self, url):
        r = requests.get(url.address, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")
        if chooser := soup.select_one("div#Alternatifler"):
            servers = len(list(chooser.children))
        else:
            servers = 1
        links = [JetLink(url.address + str(i + 1)) for i in range(servers)]
        return links

    def get_link(self, url):
        r = requests.get(url.address, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")
        iframe = soup.select_one("iframe#iframe").get("src")
        return self.__get_link(iframe, url.address)
    
    def __get_link(self, iframe: str, url: str) -> JetLink:
        if "streamscenter" in iframe:
            return StreamsCenter().get_link(JetLink(iframe))
        elif "embedsports" in iframe:
            return Embedsports().get_link(JetLink(iframe))
        else:
            iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(iframe, "", [], [])]
            return iframes[0]
