import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from datetime import timedelta, datetime

from ..models import *
from ..util import find_iframes
from ..icons import icons

class Methstreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["pre.methstreams.me"]
        self.name = "Methstreams"
        self.short_name = "MS"

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
                        utc_time = parse(time) + timedelta(hours=8)
                    except:
                        try:
                            utc_time = datetime.strptime(time, "%H:%M %p ET - %m/%d/%Y") + timedelta(hours=8)
                        except:
                            pass
                items.append(JetItem(icon=icons[league.lower()] if league.lower() in icons else None,
                  title=title, links=[JetLink(address=href, links=True)],  league=league, starttime=utc_time))
        return items
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        r = requests.get(url.address).text
        soup = BeautifulSoup(r, "html.parser")
        links = []
        for button in soup.select("button.embed-link"):
            links.append(JetLink(button.get("datatype"), name=button.text.strip()))
        for stream in soup.select("div.table-streams > table > tbody > tr"):
            th = stream.find("th")
            href = th.find("a").get("href")
            name = th.find("span").text
            links.append(JetLink(href, name=name))
        return links    
