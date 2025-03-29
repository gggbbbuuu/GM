
import requests, re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes
from ..icons import icons

class Webcast(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["nbawebcast.app", "mlbwebcast.com", "v3.nhlwebcast.com", "nflwebcast.com"]
        self.name = "Webcast"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        for domain in self.domains:
            if self.progress_update(progress, domain):
                return items

            r = requests.get(f"https://{domain}", timeout=self.timeout).text
            soup = BeautifulSoup(r, "html.parser")
            for game in soup.select("tr.singele_match_date "):
                if "mdatetitle" in game.attrs["class"]:
                    continue
                name = " ".join(game.select_one("td.teamvs").text.strip().replace("  ", " ").split(" ")[:3])
                if domain == self.domains[0]:
                    sport = "NBA"
                    name = f"[COLORaqua]{sport}: [/COLOR]" + name
                elif domain == self.domains[1]:
                    sport = "MLB"
                    name = f"[COLORorange]{sport}: [/COLOR]" + name
                elif domain == self.domains[2]:
                    sport = "NHL"
                    name = f"[COLORyellow]{sport}: [/COLOR]" + name
                elif domain == self.domains[3]:
                    sport = "NFL"
                    name = f"[COLORlime]{sport}: [/COLOR]" + name    
                game_time = game.select_one("td.matchtime").text.strip().split(":")
                game_icon = game.select_one("img").get("src")
                hour = int(game_time[0])
                minute = int(game_time[1])
                utc_time = datetime.now().replace(hour=hour, minute=minute) + timedelta(hours=17)
                href = game.find("a").get("href")
                items.append(JetItem(title=name, starttime=utc_time, icon=icons[sport.lower()] if sport.lower() in icons else None, links=[JetLink(href, links=True)]))

        return items


    def get_links(self, url: JetLink) -> List[JetLink]:
        regex_patterns = {
            self.domains[0]: r"<a class=\"btn .+\" href=\"(https://nbacast\.com/live/.+)\" target",
            self.domains[1]: r"<a class=\"btn .+\" href=\"(https://mlbwebcast.com/stream/.+)\" target",
            self.domains[2]: r"<a class=\"btn .+\" href=\"(https://nhlwebcast\.com/live/.+)\" target",
            self.domains[3]: r"<a class=\"btn .+\" href=\"(https://nflwebcast\.com/live/.+)\" target"
        }

        r = requests.get(url.address).text
        re_links = []

        for domain, pattern in regex_patterns.items():
            if domain in url.address:
                re_links += re.findall(pattern, r)
        iframes: list[JetLink] = []
        for link in re_links:
            iframes += [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(link, "", [], [])]
        for iframe in iframes:
            iframe.direct = True
            if "Referer" in iframe.headers and "bdnewszh.com" in iframe.headers["Referer"]:
                iframe.headers["Referer"] = "https://bdnewszh.com/"
        links = [link for link in iframes if "m3u8" in link.address]
        if len(links) >= 2:
            links[1].name = "Home"
            links[0].name = "Away"
        return links


