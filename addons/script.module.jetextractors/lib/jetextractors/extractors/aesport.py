from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
from ..models import *

class AeSport(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["aesport.tv"]
        self.name = "AeSport"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        # Games
        r = requests.get(f"https://{self.domains[0]}/fixture/all.html", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        max_date = datetime.now() + timedelta(days=2)
        for game in soup.select("div.fixture-page-item"):
            team_left = game.select_one("span.name-team-left").text
            team_right = game.select_one("span.name-team-right").text
            title = f"{team_left} vs {team_right}"
            league = game.select_one("div.tournament").text.strip()
            utc_time = datetime.fromtimestamp(int(game.select_one(".time-format").get("data-time")) // 1000) + timedelta(hours=7)
            if utc_time > max_date:
                break
            href = game.select_one("a").get("href")
            items.append(JetItem(title, links=[JetLink(href, links=True)], league=league, starttime=utc_time))

        if self.progress_update(progress):
            return items

        # Live TV
        r = requests.get(f"https://{self.domains[0]}/live-tv.html", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for section in soup.select("div.live-tv"):
            section_title = section.select_one("div.head-bar > div.left").text.strip()
            for channel in section.select("div.content > a"):
                href = channel.get("href")
                icon = channel.select_one("img.hide").get("src")
                title = channel.select_one("div.channel-name").text.strip()
                items.append(JetItem(title, links=[JetLink(href, links=True)], league=section_title, icon=icon))

        return items
    

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        r = requests.get(url).text
        soup = BeautifulSoup(r, "html.parser")
        for link in soup.select("a.link-channel"):
            l = clean_url(link.get("data-url"))
            user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 13_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148" if "https://liveua.score806.cc" in l else self.user_agent
            links.append(JetLink(l, name=link.text.strip(), headers={"Referer": f"https://{self.domains[0]}/", "User-Agent": user_agent}, inputstream=JetInputstreamFFmpegDirect.default()))
        return links


def clean_url(url: str) -> str:
    return url.replace('https://live-tv.vipcdn.live', 'https://liveua.score806.cc')