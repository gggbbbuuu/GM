import requests, re, time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..models import *
from .embedstream import Embedstream

class Stream720p(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["720pstream.nu"]
        self.name = "720pStream"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = f"http://{self.domains[0]}"
        r = requests.get(base_url, timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for li in soup.select("li.nav-item"):
            league = li.text.strip()
            if self.progress_update(progress, league):
                return items
            
            icon = li.find("img").get("src")
            href = base_url + li.find("a").get("href")
            r_league = requests.get(href, timeout=self.timeout).text
            soup_league = BeautifulSoup(r_league, "html.parser")
            for game in soup_league.select("a.btn"):
                game_title = game.select_one("span.text-success").text
                game_icon = game.select_one("img").get("src")
                game_href = base_url + game.get("href")
                game_time = game.select_one("div.text-warning")
                if game_time.text != "24/7":
                    time_str = game_time.find("time").get("datetime")
                    utc_time = datetime(*(time.strptime(time_str, "%Y-%m-%dT%H:%M:%S-04:00" if "-04" in time_str else "%Y-%m-%dT%H:%M:%S-05:00")[:6])) + timedelta(hours=5)
                else:
                    utc_time = None
                items.append(JetItem(title=game_title, links=[JetLink(game_href, links=True)], league=league, icon=game_icon, starttime=utc_time))
        return items


    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        r = requests.get(url.address).text
        soup = BeautifulSoup(r, "html.parser")
        for feed in soup.select("a.btn-xs"):
            links.append(JetLink(f"http://{self.domains[0]}" + feed.get("href"), name=feed.text))
        return links


    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        iframe = re.findall(f'iframe.+?src="(.+?)"', r)[0]
        return Embedstream().get_link(JetLink(iframe))