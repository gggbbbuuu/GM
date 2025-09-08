from ..models import JetExtractor, JetExtractorProgress, JetItem, JetLink
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs

class FSTV(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["fstv.zip"]
        self.name = "FSTV"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", headers={"User-Agent": self.user_agent})
        soup = BeautifulSoup(r.text, "html.parser")
        for league in soup.select("div.common-table-league > div.match-table-item"):
            league_name = league.select_one("a").text.strip()
            league_icon = league.select_one("img.ui-icon").get("src")
            for event in league.select("div.table-row"):
                if event.select_one("div.club-item"):
                    clubs = " vs. ".join(map(lambda x: x.text.strip(), event.select("div.club-name")))
                    scores = " - ".join(map(lambda x: x.text.strip(), event.select("div.club-item > span.b-text-success")))
                    title = f"{clubs} ({scores})"
                else:
                    title = event.select_one("div.list-club-wrapper").text.strip()
                match_time = datetime.fromtimestamp(int(event.select_one("span.match-time").get("data-timestamp")))
                href = "https://" + self.domains[0] + event.select_one("a").get("href")
                items.append(JetItem(title, links=[JetLink(href, links=True)], starttime=match_time, league=league_name, icon=league_icon))

        live_tv_url = f"https://{self.domains[0]}/live-tv.html"
        r = requests.get(live_tv_url, headers={"User-Agent": self.user_agent})
        soup = BeautifulSoup(r.text, "html.parser")
        for channel in soup.select("div.item-channel"):
            title = channel.get("title")
            icon = channel.get("data-logo")
            link = channel.get("data-link")
            items.append(JetItem(title, [JetLink(live_tv_url, headers={"User-Agent": self.user_agent}, params={"linkSource": link})], icon=icon, league="Live TV"))

        return items
    
    def get_links(self, url):
        r = requests.get(url.address, headers={"User-Agent": self.user_agent})
        soup = BeautifulSoup(r.text, "html.parser")
        return [JetLink(
            url.address,
            params={
                "linkSource": link.get("data-link"),
                "type": link.get("data-link-type"),
                "isLive": link.get("data-link-live")
            },
            name=link.text
        ) for link in soup.select("button.btn-server")]
    
    def get_link(self, url):
        s = requests.Session()
        r = s.get(url.address, headers={"User-Agent": self.user_agent, "Referer": f"https://{self.domains[0]}/"})
        csrf = re.findall(r'input name="__RequestVerificationToken".+?value="(.+?)"', r.text)[0]
        r_player = s.post(
            url.address,
            params={"handler": "ChangeLink"},
            data=url.params,
            headers={
                "User-Agent": self.user_agent,
                "Referer": url.address,
                "Requestverificationtoken": csrf,
                "X-Requested-With": "XMLHttpRequest"
            }
        )
        soup = BeautifulSoup(r_player.text, "html.parser")
        query = parse_qs(urlparse(soup.select_one("iframe").get("src")).query)
        return JetLink(query["link"][0], headers={"User-Agent": self.user_agent, "Referer": f"https://{self.domains[0]}/"})