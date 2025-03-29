import requests, re, time
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from ..models import *
from ..util import sportscentral_streams
from ..config import get_config

class NBABite(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["index.nbabite.com", "reddit1.nflbite.com", "reddit.nhlbite.com", "mlbbite.net", "reddit.formula1stream.cc", "mmabite.net", "tonight.boxingstreams.cc", "wwestreams.cc"]
        self.name = "NBAbite"
        self.short_name = "NBAB"

#######  NEED FIXING  ########
    def __get_items(self, site: str, progress: Optional[JetExtractorProgress] = None) -> List[JetLink]:
        items = []
        if self.progress_update(progress):
            return items

        try:
            r = requests.get("https://" + site, timeout=self.timeout).text
            soup = BeautifulSoup(r, "html.parser")
            if soup.select_one("div.justify-between > strong"):
                date = datetime(*(time.strptime(soup.select_one("div.justify-between > strong").text.strip(), "%a %d %b %Y")[:6]))
            else:
                date = datetime.now()
            other_sites = soup.select("a.other-site") + soup.select("a.rounded-xl")
            league = ""
            for other_site in other_sites:
                if urlparse(other_site.get("href")).netloc.replace("www.", "") == site:
                    league = (other_site.select_one("div.site-name") or other_site).text.strip().replace(" Streams", "").replace("Bite", "")
            if "mlb" in site:
                for competition in soup.select("div.competition"):
                    team_names = [team.text.strip() for team in competition.select("span.name")]
                    title = f"{team_names[0]} vs. {team_names[1]}"
                    href = competition.select_one("a").get("href")
                    items.append(JetItem(title=title, league=f"MLB", links=[JetLink(address=href, links=True)]))
            else:
                for game in soup.select("div.col-md-6"):
                    team_names = [team.text for team in game.select("div.team-name")]
                    title = "%s vs %s" % (team_names[0], team_names[1])
                    status = game.select_one("div.status")
                    game_time = None
                    score = game.select("div.score")
                    if len(score) > 0 and score[0].text:
                        scores = [i.text for i in score]
                        title =  "%s [COLORyellow](%s-%s)[/COLOR]" % (title, scores[0], scores[1])
                    icon = game.select_one("img").get("src")
                    href = game.select_one("a").get("href")
                    items.append(JetItem(title=title, icon=icon, starttime=game_time, league=league, links=[JetLink(address=href, links=True)]))
                for game in soup.select("div.grid-cols-1.gap-3 > div.col-span-1"):
                    team_names = [team.text for team in game.select("strong")]
                    if len(team_names) > 1:
                        title = "%s vs %s" % (team_names[0], team_names[1])
                        score = game.select("b")
                    else:
                        title = game.select_one("h5").text
                        score = []
                    
                    if len(score) > 0 and score[0].text:
                        scores = [i.text for i in score]
                        title =  "%s [COLORyellow](%s-%s)[/COLOR]" % (title, scores[0], scores[1])
                    icon = game.select_one("img").get("src")
                    href = "https://" + site + game.select_one("a").get("href")
                    items.append(JetItem(title=title, icon=icon, league=league, links=[JetLink(address=href, links=True)]))
        except:
            pass

        return items


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        with ThreadPoolExecutor() as executor:
            threads = [(domain, executor.submit(self.__get_items, site=domain, progress=progress)) for domain in self.domains]
            for domain, t in threads:
                result = t.result()
                items.extend(result)
                self.progress_update(progress, domain)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        r = requests.get(url.address).text
        soup = BeautifulSoup(r, "html.parser")
        table = soup.select_one("table.streams-table-new")
        exclude = get_config().get("sportscentral_exclude", [])
        links = []
        for stream in table.select("tbody > tr"):
            href = stream.get("data-stream-link")
            channel = stream.select_one("span.label").text.strip()
            name = stream.select_one("a").text.strip()
            site = urlparse(href).netloc
            if site in exclude:
                continue
            links.append(JetLink(address=href, name=f"{name} - {channel}"))
        return links
