import requests, re, datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from ..models.Extractor import Extractor
from ..models.Game import Game
from ..models.Link import Link
from ..config import get_config

class NBABite2(Extractor):
    def __init__(self) -> None:
        self.domains = ["reddits.footybite.io", "reddit.nflbite.io", "reddit.nbabite.io", "reddit.mlbbite.io", "reddit.nhlbite.io"]
        self.name = "NBABite2"

    def get_games(self):
        games = []
        for domain in self.domains:
            r = requests.get(f"https://{domain}", headers={"User-Agent": self.user_agent}).text
            soup = BeautifulSoup(r, "html.parser")
            for game in soup.select("div.spl-card > div.b_scard > a"):
                href = game.get("href")
                icon = game.select_one("img").get("src")
                teams = [team.text for team in game.select("h3")]
                title = f"{teams[0]} vs. {teams[1]}"
                status = game.select_one("span.b_demoteText").text.strip()
                primary_text = game.select_one("div.spl-primaryText")
                score = primary_text.text.strip().split("\n")
                score = f"{score[0].strip()} - {score[-1].strip()}"
                if "-" in primary_text.text:
                    game_status = f"{status} {score}"
                else:
                    game_status = status
                if ":" in status:
                    try:
                        split = status.split(":")
                        hours = int(split[0])
                        minutes = int(split[1])
                        time = datetime.datetime.now().replace(hour=hours, minute=minutes) - datetime.timedelta(hours=5)
                    except:
                        time = None
                else:
                    time = None
                    if not status and game_status.startswith(" "):
                        game_status = "[COLORred]LIVE[/COLOR]" + game_status
                    title = f"[COLORyellow]{game_status}[/COLOR] {title}"
                league = primary_text.next_sibling.next_sibling.text
                games.append(Game(title, [Link(href, is_links=True)], league=league, icon=icon, starttime=time))
        return games

    def get_links(self, url):
        links = []
        r = requests.get(url, headers={"User-Agent": self.user_agent, "Referer": f"https://{urlparse(url).netloc}"}).text
        soup = BeautifulSoup(r, "html.parser")
        exclude = get_config().get("sportscentral_exclude", [])
        for site in soup.select("tbody > tr"):
            streamer = site.select_one("th").text.strip()
            td = site.select("td")
            channel = td[0].text.strip()
            quality = " ".join([q.strip() for q in td[4].text.split("\n")])
            href = site.select_one("a").get("href")
            if streamer in exclude:
                continue
            links.append(Link(href, name=f"{streamer} [{channel}] - {quality}"))
        return links