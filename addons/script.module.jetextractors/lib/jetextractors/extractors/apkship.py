import requests
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes
from .daddylive import Daddylive
from .voodc import Voodc


class Apkship(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["apkship.xyz"]
        self.name = "Apkship"
        self.short_name = "APK"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        page = 1 if params is None else int(params["page"])
        r = requests.get(f"https://{self.domains[0]}/page/{page}/", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for game in soup.select("div.inside-article"):
            a = game.find("a")
            href = a.get("href")
            title = a.text.strip()
            items.append(JetItem(title=title, links=[JetLink(address=href)]))
            if self.progress_update(progress, title):
                        return items
            xbmc.sleep(200)
        if (next_page := soup.select_one("a.next")) is not None:
            page = next_page.get("href").split("/")[-2]
            items.append(JetItem(f"Page {page}", links=[], params={"page": page}))
        return items
    

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        soup = BeautifulSoup(r, "html.parser")
        iframe = soup.find("iframe").get("src")
        return Daddylive().get_link(JetLink(iframe.replace("https://apkship.shop/live/", "https://thedaddy.to/stream/")))

