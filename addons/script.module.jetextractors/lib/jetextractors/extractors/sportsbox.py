import requests, re, json, time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from ..models import *
from .plytv import PlyTv

class SportsBox(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["nflbox.me", "www.nbabox.me", "mlbbox.me", "nhlbox.me", "mmastreams.me", "socceronline.me", "rugbystreams.me", "f1box.me", "boxingstream.me", "tennisonline.me", "watch.cricstream.me", "dartsstreams.com"]
        self.name = "SportsBox(non-PC)"
        self.short_name = "SB"
#######  NEED FIXING  ########
    def __get_items(self, domain: str, progress: Optional[JetExtractorProgress] = None):
        items = []
        if self.progress_update(progress):
            return items
        
        try:
            slugs = []
            r = requests.get(f"https://{domain}", timeout=self.timeout).text
            soup = BeautifulSoup(r, "html.parser")
            categories = soup.select("a.btn-lg")
            for cat in categories:
                cat_name = cat.text.split(" - ")[0].strip()
                if self.progress_update(progress, f"{domain}: {cat_name}"):
                    return items
                
                cat_href = "https://" + domain + cat.get("href")
                r_cat = requests.get(cat_href, headers={"Referer": f"https://{domain}"}, timeout=self.timeout).text
                soup_cat = BeautifulSoup(r_cat, "html.parser")
                site_config = json.loads(re.findall(r"const siteConfig = (.+?);", r_cat)[0])
                schedule_data = requests.get(f"https://{domain}/schedule/{site_config['scheduleData']}/", timeout=self.timeout).json()

                for game in soup_cat.select("a.btn-secondary"):
                    game_id = game.get("aria-controls")
                    game_slug = schedule_data["slugs"][game_id]
                    if game_slug in slugs:
                        continue

                    slugs.append(game_slug)
                    link_append = schedule_data["linkAppends"][game_id]
                    game_title = game.get("title")
                    game_links = [JetLink(address=f"https://{domain}/{game_slug}-live/{link_append}/stream-{i+1}", name=f"{link['player'][1:]} - Link {i+1}") for i, link in enumerate(schedule_data["links"][game_id])]
                    game_spans = game.find_all("span")
                    if len(game_spans) > 1:
                        game_time = datetime(*(time.strptime(game_spans[-1].get("content"), "%Y-%m-%dT%H:%M")[:6])) - timedelta(hours=1)
                    else:
                        game_time = None
                    items.append(JetItem(title=game_title, links=game_links, league=cat_name, starttime=game_time))
        except:
            pass
        return items
    

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        with ThreadPoolExecutor() as executor:
            threads = [(domain, executor.submit(self.__get_items, domain=domain, progress=progress)) for domain in self.domains]
            for domain, t in threads:
                result = t.result()
                items.extend(result)
                self.progress_update(progress, domain)
        return items
        

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        zmid = re.findall(r'zmid = "(.+?)"', r)[0]
        game_cat = re.findall(r'gameCat="(.+?)"', r)[0]
        return PlyTv().plytv_sdembed(game_cat, zmid, url.address)