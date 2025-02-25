import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from ..models import *
from ..util import m3u8_src

class Sportea(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["s1.sportea.link", "live.ugreen.autos"]
        self.name = "Sportea"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []

        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for table in soup.select("div.p-4 > div.row"):
            league = table.select_one("h5").text.upper()
            for game in table.select("tbody > tr"):
                data = game.select("td")
                time = data[1].text
                title = data[2].text.split("\n")[0].strip()
                if "college basketball" in title.lower():
                    league_1 = "NCAAB"
                else:
                    league_1 = league
                href = data[-1].select_one("a").get("href")
                items.append(JetItem(title, links=[JetLink(href)], league=league_1))
        return items
    
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address.replace("embed.php", "channel.php")).text
        re_iframe = re.findall(r'<iframe src="(.+?)"', r)[0]
        api_url = re_iframe.replace("/stream/", "/api/source/") + "?type=live"
        r_api = requests.post(api_url, json={"d": urlparse(api_url).netloc, "r": f"https://{self.domains[1]}/"}).json()
        m3u8 = r_api["player"]["source_file"]
        return JetLink(m3u8, headers={"Referer": re_iframe})