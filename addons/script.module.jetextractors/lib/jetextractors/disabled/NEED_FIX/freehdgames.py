import requests
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes
from ..icons import icons

class Freehdgames(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["gamehdlive.online"]
        self.name = "Freehdgames"
        self.short_name = "HG"

#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for game in soup.select("a"):
            href = game.get("href")
            if "ch" not in href or not href.endswith(".php"):
                continue
            league = game.previous.previous.text
            sport = league.replace(" —","")
            link_name = game.text
            game_time = game.previous.previous.previous.previous.text
            name = (game_time + " " + game.previous.text).strip()
            if not name or "Watch Free Games" in name:
                continue
            if self.progress_update(progress, name):
                        return items
            xbmc.sleep(200)
            items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None,
                  title=name, league=sport, links=[JetLink(href, name=link_name)]))
        return items
    

    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        return iframes[0]









    
