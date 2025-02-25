import requests, re, base64
from bs4 import BeautifulSoup
from ..models import *
from ..icons import icons
from ..util import find_iframes

class Sportshub(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["sportshub.ai"]
        self.name = "Sportshub"
        self.short_name = "SH"
        
#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}").text
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
                items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None,
                  title=name, links=[JetLink(href)], league=sport))
        return items


    # def get_link(self, url: JetLink) -> JetLink:
    #     r = requests.get(url.address).text
    #     atob_match = re.findall(r"window.atob\('(.+?)'\)", r)
    #     if atob_match:
    #         atob = base64.b64decode(atob_match[0]).decode("ascii")
    #         return JetLink(atob, headers={"Referer": url.address})
    #     else:
    #         raise ValueError("Encoded URL not found in the response.")
    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        return iframes[0]









    
