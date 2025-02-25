
import requests, re, base64
from bs4 import BeautifulSoup
from ..models import *
from ..icons import icons
from ..util import find_iframes

#######  NEED FIXING  ########
class Thestreameastai(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["thestreameast.ai"]
        self.name = "Thestreameastai"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for game in soup.select("li.f1-podium--item"):
            name = game.select_one("span.d-md-inline").text
            live = game.select("span",style_="color: #e10600;font-weight:bold;")[-1].text
            sport = game.select_one("span",class_="f1-podium--rank f1-bold--xs",stlyle_="min-width: 35px;width: unset;").text 
            if not name:
                continue
            href = game.find("a").get("href")
            items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None, title=sport+ "[COLORyellow] | [/COLOR]"+name + "   "+"[COLORred]"+ live+"[/COLOR]",links=[JetLink(href)]))
        return items

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        re_iframe = re.findall(r'iframe.+?src="(.+?)"',r)[0]
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(re_iframe)]
        link = iframes[0]
        
        # if "hutg54" in link.address:
        #     link.headers["Referer"] = f"https://{self.domains[2]}"
        # else:
        #     link.headers["Referer"] = f"https://{self.domains[1]}"
        link.inputstream = JetInputstreamFFmpegDirect.default()
        return link
    # def get_link(self, url: JetLink) -> JetLink:
    #     r = requests.get(url.address).text
    #     atob = base64.b64decode(re.findall(r"window.atob\('(.+?)'\)", r)[0]).decode("ascii")
    #     return JetLink(atob, headers={"Referer": url.address})


