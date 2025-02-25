
import requests
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes
from ..icons import icons


class Pawa(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["pawastreams.info", "ww2.pawastreams.top"]
        self.name = "Pawa"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}/", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for category in soup.select("h2.elementor-heading-title"): # TODO: might need to be fixed
            sport = category.text.replace(" Streams", "")
            if self.progress_update(progress, sport):
                return items
            sport_href = category.select_one("a")
            if sport_href == None:
                continue
            sport_href = sport_href.get("href")
            r_sport = requests.get(sport_href, timeout=self.timeout).text
            soup_sport = BeautifulSoup(r_sport, "html.parser")
            for game in soup_sport.select("h3.elementor-post__title"):
                name = game.select_one("a").text
                if not name:
                    continue
                href = game.find("a").get("href")
                items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None,
                  title="[COLORyellow] | [/COLOR]"+name + "   "+"[COLORred][/COLOR]",links=[JetLink(href)], league=sport))
        
        return items
    

    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], []) if self.domains[0] not in str(u)]
        return iframes[0]


