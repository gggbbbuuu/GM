import requests, re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ..models import *
from ..util import m3u8_src


class Dofu(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["dofusports.xyz"]
        self.name = "Dofu"
    

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        page = int(params["page"]) if params is not None else 1
        r = requests.get(f"http://{self.domains[0]}/games/page/{page}/", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for article in soup.select("article"):
            a = article.select_one("a")
            title = a.text
            href = a.get("href")
            items.append(JetItem(title, links=[JetLink(href)]))
        items.append(JetItem(f"Page {page + 1}", links=[], params={"page": page + 1}))
        return items

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        iframe = re.findall(r"iframe.+?src='(.+?)'", r)[0]
        r = requests.get(iframe, headers={"Referer": url.address}).text
        m3u8 = re.findall(r'source: "(.+?)"', r)[0]
        return JetLink(m3u8, headers={"Referer": iframe})
