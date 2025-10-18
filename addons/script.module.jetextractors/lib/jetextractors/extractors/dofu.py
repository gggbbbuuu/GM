import requests
import re
from bs4 import BeautifulSoup
from ..models import JetExtractor, JetItem, JetLink
from typing import List
from urllib3.util import SKIP_HEADER
from .embedsports import Embedsports


class Dofu(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["dofusports.xyz"]
        self.name = "Dofu"
    

    def get_items(self, params = None, progress = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        page = int(params["page"]) if params is not None else 1
        while page < 20:
            if self.progress_update(progress, f"Page {page}"):
                break
            r = requests.get(f"http://{self.domains[0]}/games/page/{page}/", timeout=self.timeout).text
            soup = BeautifulSoup(r, "html.parser")
            for article in soup.select("article"):
                a = article.select_one("a")
                title = a.text
                href = a.get("href")
                items.append(JetItem(title, links=[JetLink(href)]))
            if next := soup.select_one("main#content > a"):
                if next.text[0] == "«":
                    break
            else:
                break
            page += 1
        return items

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address, headers={"Accept-Encoding": SKIP_HEADER}).text
        iframe = re.findall(r"iframe.+?src='(.+?)'", r)[0]
        if "embedsports.top" in iframe:
            es = Embedsports()
            return es.get_link(JetLink(iframe))
        else:
            r = requests.get(iframe, headers={"Referer": url.address, "Accept-Encoding": SKIP_HEADER}).text
            m3u8 = re.findall(r'source: "(.+?)"', r)[0]
            return JetLink(m3u8, headers={"Referer": iframe})
