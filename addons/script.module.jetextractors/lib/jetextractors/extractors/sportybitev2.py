import requests, re
from bs4 import BeautifulSoup
from ..models import *
from .sportybite import SportyBite

class SportyBitev2(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["backlinkhd.com"]
        self.name = "SportyBitev2"
    

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for game in soup.select("tbody > tr"):
            if "class" in game.attrs and "date-separator" in game.attrs["class"]:
                continue
            league = game.select_one("td.hidden-xs").text
            hours = game.select_one("td.dt").text
            name = game.select_one("td.event-title").text
            
            if not name:
                continue
            href = game.find("a").get("href")
            icon = game.find("img").get("src")
            items.append(JetItem(name, league=league, icon=icon, links=[JetLink(href)]))

        for channel in soup.select("div.channels"):
            name = channel.text.strip()
            href = channel.find("a").get("href")
            items.append(JetItem(name, links=[JetLink(href)]))

        return items
    

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        hd = re.findall(r'\?hd=(.+?)"', r)[0]
        sportybite = SportyBite()
        return sportybite.get_link(JetLink(f"https://{sportybite.domains[0]}/tvon.php?hd={hd}"))
