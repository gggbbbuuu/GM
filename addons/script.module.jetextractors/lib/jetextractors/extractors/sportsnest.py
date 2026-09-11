
import re, base64
from bs4 import BeautifulSoup
from ..models import *
from .._core import fetch_page, get_session

class SportsNest(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["news.sportsnest.co"]
        self.name = "SportsNest"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        page = int(params["page"]) if params is not None else 1
        r = fetch_page(f"https://{self.domains[0]}/page/{page}/?s=soccer")
        soup = BeautifulSoup(r, "html.parser")
        for game in soup.find_all("a", class_="link"):
            name = game.text
            if not name:
                continue
            href = game.get("href")
            items.append(JetItem(name,links=[JetLink(href)]))
        items.append(JetItem(f"Page {page + 1}", links=[], params={"page": page + 1}))
        return items

    
    def get_link(self, url: JetLink) -> JetLink:
        s = get_session()
        s.post(f"https://{self.domains[0]}/wp-content/plugins/litespeed-cache/guest.vary.php")
        r = s.get(url.address).text
        b64 = re.findall(r"src=\"data:text/javascript;base64,(.+?)\"", r)
        for b in b64:
            decoded = base64.b64decode(b).decode("utf-8")
            re_css = re.findall(r"src:'(.+?)'", decoded)
            if re_css:
                return JetLink(re_css[0], headers={"Referer": url.address})


