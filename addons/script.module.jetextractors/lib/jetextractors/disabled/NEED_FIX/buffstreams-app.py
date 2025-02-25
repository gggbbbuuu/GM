import requests, re, base64
from bs4 import BeautifulSoup
from ..util import find_iframes

from ..models import *

#######  NEED FIXING  ########

class Buffstreamsapp(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["buffstreams.app"]
        self.name = "Buffstreams-app"
        self.short_name = "BSA"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        
        for competition in soup.select("div.top-tournament"):
            sport = " ".join(competition.find("h2").text.split(" ")[1:-2])
            for game in competition.select("li"):
                block = game.find("a")
                href = block.get("href")
                if "d-block" in block.attrs["class"]:
                    name = "-".join(game.find("div").text.replace("\n", "").strip().split("-")[:-1])
                else:
                    name = " ".join(block.get("title").split(" ")[1:])
                score_elem = block.find("span", class_="competition-cell-score")
                if score_elem != None:
                    try:
                        score_info = score_elem.text.strip().split("\n")
                        score = score_info[0].strip()
                        quarter = score_info[1].strip()
                        name += f" ({score}, {quarter})"
                    except:
                        pass
                    game.previous
                    if self.progress_update(progress, name):
                        return items
                xbmc.sleep(200)
                items.append(JetItem(name, links=[JetLink(href)], league=sport))
        return items


    # def get_link(self, url: JetLink) -> JetLink:
    #     r = requests.get(url.address).text
    #     atob = base64.b64decode(re.findall(r"window.atob\('(.+?)'\)", r)[0]).decode("ascii")
    #     return JetLink(atob, headers={"Referer": url})
    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        return iframes[0] 
