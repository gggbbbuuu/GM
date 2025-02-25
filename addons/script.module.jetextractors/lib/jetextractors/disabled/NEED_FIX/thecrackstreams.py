import requests, re, base64
from bs4 import BeautifulSoup
from datetime import timedelta, datetime
from ..models import *
from ..icons import icons

class Thecrackstreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["thecrackstreams.to"]
        self.name = "Thecrackstreams"
        self.short_name = "TC"
#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        categories = soup.select("ul.menu-main-menu > li > a")
        for category in categories:
            if self.progress_update(progress, category.text):
                return items
            
            league = category.text.replace(" streams", "")
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
                items.append(JetItem(icon=icons[league.lower()] if league.lower() in icons else None, title=title, links=[JetLink(address=href)], league=league, starttime=utc_time))
        return items

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        atob = base64.b64decode(re.findall(r"window.atob\('(.+?)'\)", r)[0]).decode("ascii")
        return JetLink(atob, headers={"Referer": url.address})









    
