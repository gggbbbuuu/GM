import requests, re, json, time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..models import *
from .plytv import PlyTv
from concurrent.futures import ThreadPoolExecutor

class Strikeout(JetExtractor):
    domains = ["strikeout.im"]
    name = "Strikeout"

    def __get_items(self, sport_href: Tuple[str, str], slugs: List[str], progress: Optional[JetExtractorProgress] = None):
        items = []
        if self.progress_update(progress):
            return items

        sport = sport_href[1]
        sport_href = sport_href[0]
        r_sport = requests.get(f"https://{self.domains[0]}{sport_href}", timeout=self.timeout).text
        if not r_sport:
            return items
        soup_sport = BeautifulSoup(r_sport, "html.parser")
        site_config = json.loads(re.findall(r"const siteConfig = (.+?);", r_sport)[0])
        if "scheduleData" not in site_config:
            return items
        schedule_data = requests.get(f"https://{self.domains[0]}/schedule/{site_config['scheduleData']}/", timeout=self.timeout).json()
        for game in soup_sport.select("a.btn-primary"):
            try:
                game_id = game.get("aria-controls")
                game_slug = schedule_data["slugs"][game_id]
                if game_slug in slugs:
                    continue

                slugs.append(game_slug)
                game_title = game.get("title")
                game_links = [JetLink(address=f"https://{self.domains[0]}/{schedule_data['linkAppends'][game_id]}/{i+1}/{game_slug}-stream", name=f"{link['player']} - Link {i+1}") for i, link in enumerate(schedule_data["links"][game_id])]
                game_spans = game.find_all("span")
                if len(game_spans) > 1:
                    game_time = datetime(*(time.strptime(game_spans[-1].get("content"), "%Y-%m-%dT%H:%M")[:6])) - timedelta(hours=1)
                else:
                    game_time = None
                items.append(JetItem(title=game_title, links=game_links, league=sport, starttime=game_time))
            except:
                continue
        return items
    

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        hrefs = []
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for sport_page in soup.select("div.col-xxl-2"):
            sport = sport_page.text
            sport_href = sport_page.select_one("a").get("href")
            if not sport_href.startswith("/"):
                continue
            hrefs.append((sport_href, sport))
        
        slugs = []
        with ThreadPoolExecutor() as executor:
            threads = [(href, executor.submit(self.__get_items, sport_href=href, slugs=slugs, progress=progress)) for href in hrefs]
            for href, t in threads:
                result = t.result()
                items.extend(result)
                self.progress_update(progress, href[1])
            
        return items
    
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        zmid = re.findall(r'zmid = "(.+?)"', r)[0]
        game_cat = re.findall(r'gameCat="(.+?)"', r)[0]
        return PlyTv().plytv_sdembed(game_cat, zmid, url.address)