from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from ..util import m3u8_src
from urllib3.util import SKIP_HEADER

class RoxieStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["roxiestreams.live","roxiestreams.cc"]
        self.name = "RoxieStreams"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for nav_link in soup.select("a.nav-link")[:-1]:
            league = nav_link.text
            r = requests.get(nav_link.get("href"), timeout=self.timeout).text
            soup = BeautifulSoup(r, "html.parser")
            for event in soup.select("table#eventsTable > tbody > tr, tr > tr"):
                a = event.select_one("a")
                if not a:
                    continue
                href = a.get("href")
                title = a.text.strip()
                items.append(JetItem(title=title, links=[JetLink(href)], league=league))
            if self.progress_update(progress, league):
                break
        return items
    

    def get_link(self, url: JetLink) -> JetLink:
        return m3u8_src.scan_page(url.address, headers={"Accept-Encoding": SKIP_HEADER})
    