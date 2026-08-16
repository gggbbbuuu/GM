import requests, re
from bs4 import BeautifulSoup
from ..models import *
from .embedstream import Embedstream
from .embedsports import Embedsports

VARIANT = re.compile(r'<a class="btn btn-primary btn-xs[^"]*"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>')

class Stream720p(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["720pstream.cx", "720pstream.nu"]
        self.name = "720pStream"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = f"https://{self.domains[0]}"
        r = requests.get(base_url, timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for nav in soup.select("a.nav-link"):
            if not nav.get("href"):
                continue
            league = nav.text.strip()
            if self.progress_update(progress, league):
                return items
            
            href = nav.get("href")
            r_league = requests.get(f"{base_url}{href}", timeout=self.timeout).text
            soup_league = BeautifulSoup(r_league, "html.parser")
            for game in soup_league.select("a.btn.btn-secondary"):
                game_title = game.get("title", "")
                game_href = game.get("href")
                if game_title and game_href:
                    if game_title.startswith("Live "):
                        game_title = game_title[5:]
                    if game_title.endswith(" Channel"):
                        game_title = game_title[:-8]
                    items.append(JetItem(title=game_title, links=[JetLink(f"{base_url}{game_href}", links=True)], league=league))
        return items


    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        r = requests.get(url.address).text
        for href, label in VARIANT.findall(r):
            links.append(JetLink(f"https://{self.domains[0]}" + href, name=label.strip()))
        if not links:
            links.append(JetLink(url.address, name=self.name))
        return links


    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        iframe = re.findall(r'iframe.+?src="(.+?)"', r)
        if iframe:
            iframe_url = iframe[0]
            if "embedsports.top" in iframe_url:
                return Embedsports().get_link(JetLink(iframe_url))
            else:
                return Embedstream().get_link(JetLink(iframe_url, headers={"Referer": url.address}))
        return JetLink(url.address)