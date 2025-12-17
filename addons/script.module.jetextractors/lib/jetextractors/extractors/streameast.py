from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress
from .embedsports import Embedsports
from .streamscenter import StreamsCenter
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, List
from ..util import find_iframes

class StreamEast(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["v2.streameast.ga","streameast.ga", "^(?:the)?streameast\....?"]
        self.domains_regex = True
        self.name = "TheStreamEast"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}")
        soup = BeautifulSoup(r.text, "html.parser")
        for category in soup.select("div.se-sport-section"):
            category_name = category.get("data-sport-name")
            for match in category.select("a.uefa-card"):
                title = " vs. ".join([name.text.strip() for name in match.select("span.uefa-name")])
                href = "https://" + self.domains[0] + match.get("href")
                match_time = datetime.fromtimestamp(int(match.get("data-time")))
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
        iframe_elem = soup.select_one("iframe#iframe")
        if not iframe_elem or not iframe_elem.get("src"):
            iframe_elem = soup.select_one("iframe")
        
        if not iframe_elem or not iframe_elem.get("src"):
            return url
            
        iframe = iframe_elem.get("src")
        
        # Handle different iframe sources
        if "streamscenter" in iframe or "streamcenter" in iframe or "streams.center" in iframe:
            result = StreamsCenter().get_link(JetLink(iframe))
            if result:
                return result
            
        
        if "embedsports" in iframe:
            result = Embedsports().get_link(JetLink(iframe))
            if result:
                return result
        
        # Try find_iframes as fallback
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(iframe, url.address, [], [])]
        if iframes:
            return iframes[0]
        
        # return the iframe URL itself with headers
        return JetLink(iframe, headers={"Referer": url.address, "User-Agent": self.user_agent})