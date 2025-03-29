from concurrent.futures import ThreadPoolExecutor
from ..models import *
from ..util import m3u8_src
import requests, re
from bs4 import BeautifulSoup

class TotalSportek(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["www.totalsportek.futbol"]
        self.name = "TotalSportek"


    def __get_items(self, href: str, progress: Optional[JetExtractorProgress] = None):
        items = []
        if self.progress_update(progress):
            return items
        
        r = requests.get(href).text
        soup = BeautifulSoup(r, "html.parser")
        for row in soup.select("div.row")[1:]:
            title = row.select_one("p.font-weight-bold").text.strip()
            row_date = row.select_one("p.font-weight-bolder").text
            href = row.select_one("a").get("href")
            items.append(JetItem(f"{row_date} | {title}", links=[JetLink(href)]))
        return items
    
    def __get_schedule(self, d: Optional[str] = None, progress: Optional[JetExtractorProgress] = None):
        items = []
        if self.progress_update(progress):
            return items
        r = requests.get(f"https://{self.domains[0]}/date/{d}" if d is not None else f"https://{self.domains[0]}").text
        soup = BeautifulSoup(r, "html.parser")
        for row in soup.select("div.div-main-box > a"):
            href = row.get("href")
            if "hufoot" in href:
                continue
            teams = row.select("span.txt-team")
            title = f"{teams[0].text.strip()} vs {teams[1].text.strip()}"
            items.append(JetItem(title, links=[JetLink(f"https://{self.domains[0]}{href}")]))
        return items


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}").text
        soup = BeautifulSoup(r, "html.parser")
        with ThreadPoolExecutor() as executor:
            threads = [("Today", executor.submit(self.__get_schedule, progress=progress))] + [(a.text.strip(), executor.submit(self.__get_items, href=a.get("href"), progress=progress)) for a in soup.select("ul > li > a")[1:-1]]
            for href, t in threads:
                result = t.result()
                items.extend(result)
                self.progress_update(progress, href)
        return items
    

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        re_embed = re.findall(r'iframe.+?src="(.+?)"', r)[0]
        r = requests.get(re_embed).text
        m3u8 = m3u8_src.scan(r)
        return JetLink(m3u8)
    