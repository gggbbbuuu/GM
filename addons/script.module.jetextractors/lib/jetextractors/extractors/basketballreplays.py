from ..models import *
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class BasketballReplays(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["basketballreplays.net"]
        self.name = "BasketballReplays"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}?page{params['page'] if params is not None else 1}").text
        soup = BeautifulSoup(r, "html.parser")
        for item in soup.select("div.h_post"):
            a = item.select_one("div.h_post_title > a")
            title = a.text
            href = f"https://{self.domains[0]}" + a.get("href")
            xbmc.log(href, xbmc.LOGINFO)
            icon = f"https://{self.domains[0]}" + item.select_one("img").get("src")
            items.append(JetItem(title, links=[JetLink(href, links=True)], icon=icon))
        if (next_page := soup.select_one("a.swchItem-next")) is not None:
            page = next_page.get("href").split("/?page")[-1]
            items.append(JetItem(f"Page {page}", links=[], params={"page": page}))
        return items


    def get_links(self, url: JetLink) -> List[JetLink]:
        r = requests.get(url.address).text
        soup = BeautifulSoup(r, "html.parser")
        links = [JetLink(iframe.get("src"), resolveurl=True, name=urlparse(iframe.get("src")).netloc) for iframe in soup.select("iframe")]
        return links
    
    