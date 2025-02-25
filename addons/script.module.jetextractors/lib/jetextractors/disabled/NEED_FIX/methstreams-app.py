import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from datetime import timedelta, datetime
from ..models import *
from ..util import find_iframes
from ..icons import icons

class Methstreamsapp(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["v.methstreams.app"]
        self.name = "Methstreamsapp"
    
#######  NEED FIXING  ########    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        categories = soup.select("ul.navbar-nav > li > a")
        for category in categories:
            if self.progress_update(progress, category.text):
                return items
            league = category.text.replace(" Streams", "")
            league_href = category.get('href')
            r_league = requests.get(league_href).text
            soup_league = BeautifulSoup(r_league, "html.parser")
            league_games = soup_league.find_all("a", {"class": "btn-block"})
            for body in league_games:
                href = body.get("href")
                if href.startswith("/"):
                    href = f"https://{self.domains[0]}{href}"
                title = body.find("h4").text.strip()
                time = body.find("p").text
                utc_time = None
                if time != "":
                    try:
                        utc_time = parse(time) + timedelta(hours=4)
                    except:
                        try:
                            utc_time = datetime.strptime(time, "%H:%M %p ET - %m/%d/%Y") + timedelta(hours=4)
                        except:
                            pass
                items.append(JetItem(icon=icons[league.lower()] if league.lower() in icons else None,
                  title=title, links=[JetLink(address=href, links=True)],  league=league, starttime=utc_time))
        return items
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        r = requests.get(url).text
        soup = BeautifulSoup(r, "html.parser")
        links = [JetLink(link.get("datatype"), name=link.text) for link in soup.select("button.embed-link")]
        if len(links) == 0:
            url.links = False
            links = [url]
        return links


    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        return iframes[0]
