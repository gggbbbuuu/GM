import requests, time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ..models import *

class V2Sportsurge(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["v2.sportsurge.net"]
        self.name = "V2 Sportsurge"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get("https://" + self.domains[0], timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for game in soup.select(".MaclariListele"):
            teams = game.select("h4")
            try:
                title = teams[0].text.strip() + " vs. " + teams[1].text.strip()
            except:
                title = teams[0].text.strip()
            category = game.select_one(".col-1").text.strip()
            date = game.select_one(".col-4").text.strip()
            utc_time = datetime(*(time.strptime(date, "%m/%d/%Y %I:%M %p ET")[:6])) + timedelta(hours=4)
            try:
                icon = f'https://{self.domains[0]}/{game.select_one("img").get("src")}'
            except:
                icon = ""
            href = f'https://{self.domains[0]}/{game.get("href")}'
            items.append(JetItem(title=title, icon=icon, starttime=utc_time, league=category, links=[JetLink(href, links=True)]))
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        r = requests.get(url.address).text
        soup = BeautifulSoup(r, "html.parser")
        exclude = self.get_config().get("sportscentral_exclude", [])
        for stream in soup.select(".game-forecast-link.MobildeGizle"):
            name = stream.select_one("h4").text
            if name in exclude:
                continue
            href = stream.select_one("td").get("data-href")
            links.append(JetLink(address=href, name=name))
        return links

    