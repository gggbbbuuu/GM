from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress
from typing import Optional, List
import requests
import re
from bs4 import BeautifulSoup
from urllib3.util import SKIP_HEADER

class TotalSportek(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["totalsportek7.com"]
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
            teams = row.select("div.row.my-auto")
            title = ", ".join([team.text.strip() for team in teams])
            items.append(JetItem(title, links=[JetLink(f"https://{self.domains[0]}{href}")]))
        return items


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}")
        soup = BeautifulSoup(r.text, "html.parser")
        # with ThreadPoolExecutor() as executor:
        #     threads = [("Today", executor.submit(self.__get_schedule, progress=progress))] + [(a.text.strip(), executor.submit(self.__get_items, href="https://" + self.domains[0] + a.get("href"), progress=progress)) for a in soup.select("ul > li > a")[1:-1]]
        #     for href, t in threads:
        #         result = t.result()
        #         items.extend(result)
        #         self.progress_update(progress, href)
        for game in soup.select("li.f1-podium--item > a"):
            title_elem = game.select_one("span.f1-podium--rank")
            sport = title_elem.text.upper()
            title = " VS ".join(map(str.strip, game.select_one("span.f1-podium--driver").text.strip().split(" VS ")))
            href = "https://" + self.domains[0] + game.get("href")
            items.append(JetItem(title, links=[JetLink(href, links=True)], league=sport))
        return items
    

    def get_links(self, url):
        links = []
        r = requests.get(url.address, headers={"Accept-Encoding": SKIP_HEADER})
        soup = BeautifulSoup(r.text, "html.parser")
        for link in soup.select("table.table > tr")[1:]:
            href = link.select_one("input").get("value")
            td = link.select("td")
            name = td[1].text.strip()
            channel = td[6].text.strip()
            links.append(JetLink(href, name=f"{name} [{channel}]"))
        return links
    