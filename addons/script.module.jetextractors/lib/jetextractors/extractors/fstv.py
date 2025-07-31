from ..models import *
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

class FSTV(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["fstv.us"]
        self.name = "FSTV"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", headers={"User-Agent": self.user_agent})
        soup = BeautifulSoup(r.text, "html.parser")
        for league in soup.select("div.common-table-league > div.match-table-item"):
            league_name = league.select_one("a").text.strip()
            league_icon = league.select_one("img.ui-icon").get("src")
            for event in league.select("div.table-row"):
                if event.select_one("div.club-item"):
                    clubs = " vs. ".join(map(lambda x: x.text.strip(), event.select("div.club-name")))
                    scores = " - ".join(map(lambda x: x.text.strip(), event.select("div.club-item > span.b-text-success")))
                    title = f"{clubs} ({scores})"
                else:
                    title = event.select_one("div.list-club-wrapper").text.strip()
                match_time = datetime.fromtimestamp(int(event.select_one("span.match-time").get("data-timestamp")))
                href = "https://" + self.domains[0] + event.select_one("a").get("href")
                items.append(JetItem(title, links=[JetLink(href, links=True)], starttime=match_time, league=league_name, icon=league_icon))

        
        r = requests.get(f"https://{self.domains[0]}/live-tv.html", headers={"User-Agent": self.user_agent})
        soup = BeautifulSoup(r.text, "html.parser")
        for channel in soup.select("div.item-channel"):
            title = channel.get("title")
            icon = channel.get("data-logo")
            link = channel.get("data-link")
            items.append(JetItem(title, [JetLink(link, headers={"User-Agent": self.user_agent})], icon=icon, league="Live TV"))

        return items
    
    def get_links(self, url):
        r = requests.get(url.address, headers={"User-Agent": self.user_agent})
        re_links = re.findall(r'data-link="(.+?)"', r.text)
        return [JetLink(link, headers={"User-Agent": self.user_agent}) for link in re_links]
    