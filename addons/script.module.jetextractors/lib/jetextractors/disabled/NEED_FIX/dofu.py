import requests, time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ..models import *
from ..util import find_iframes
from ..icons import icons
from .voodc import Voodc
from .givemenbastream import GiveMeNBAStreams
from .sportea import Sportea


class Dofu(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["dofusports.xyz"]
        self.name = "Dofu"
    
#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        leagues=["nfl","nba", "nhl","mlb","ufc"]
        for league in leagues:
            if self.progress_update(progress, league):
                return items
            
            page = 1
            while True:
                url = f"http://{self.domains[0]}/sport/{league}"
                if page > 1:
                    url += f"/page/{page}"
                
                r = requests.get(url, timeout=self.timeout).text
                soup = BeautifulSoup(r, "html.parser")
                main_content = soup.select_one("main#content")
                
                if not main_content:
                    break
                    
                articles = main_content.select("article")
                if not articles:
                    break
                
                for article in articles:
                    link_elem = article.select_one("h2 a")
                    if link_elem:
                        name = link_elem.text.strip()
                        href = link_elem.get("href")
                        sport = league
                        
                        items.append(JetItem(
                            icon=icons[league.lower()] if league.lower() in icons else None,
                            title=name,
                            league=sport.upper(),
                            links=[JetLink(href)]
                        ))
                
                next_page = main_content.select_one('a:-soup-contains("Next Page")')
                if not next_page:
                    break
                    
                page += 1

        return items

    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        link = iframes[0]
        if "giveme" in link.address:
            return GiveMeNBAStreams().get_link(link)
        if "voodc" in link.address:
            return Voodc().get_link(link)
        if "sportea" in link.address:
            return Sportea().get_link(link)
        if "freesportstime" in link.address:
            del link.headers["Referer"]
        return iframes[0]
