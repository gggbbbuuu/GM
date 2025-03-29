import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from datetime import timedelta, datetime

from ..models import *
from ..util import find_iframes
from ..icons import icons


class Meth_com(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["methstreams.com"]
        self.name = "Meth_com"
        self.short_name = "MS"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}/", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for league in soup.select("ul.nav > li > a"):
            if self.progress_update(progress):
                return items
            r_league = requests.get(f"https://{self.domains[0]}/" + league.get("href"), timeout=self.timeout).text
            soup_league = BeautifulSoup(r_league, "html.parser")
            leagues1 = league.text
            for game in soup_league.find_all("a", {"class": "btn-block"}):
                href = game.get("href")
                if href.startswith("/"):
                    href = f"https://{self.domains[0]}{href}"
                title = game.find("h4").text.strip()
                time = game.find("p").text
                utc_time = None
                if time != "":
                    try:
                        utc_time = parse(time) + timedelta(hours=17)
                    except:
                        try:
                            utc_time = datetime.strptime(time, "%H:%M %p ET - %m/%d/%Y") + timedelta(hours=17)
                        except:
                            pass
                items.append(JetItem(icon=icons[leagues1.lower()] if leagues1.lower() in icons else None,league=leagues1.upper(),title=title, links=[JetLink(address=href)], starttime=utc_time))
        return items


    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        return iframes[0]