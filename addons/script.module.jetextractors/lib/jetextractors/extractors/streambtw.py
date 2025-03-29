import requests
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes
from ..icons import icons

class StreamBTW(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streambtw.com"]
        self.name = "StreamBTW"
        self.short_name = "CS"
#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        
        # for game_area in soup.select("div.col-8"):
        #     game_titles = [title.text.strip() for title in game_area.select("p")]
        #     hrefs = [link.get("href") for link in game_area.select("a")]
        #     sport = [title.text.strip() for title in game_area.select("h5")]
        #     for title,sport, href in zip(game_titles,sport, hrefs):
        #         items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None, league=sport.upper(), title=title, links=[JetLink(href)]))
        # return items
        for extra in soup.select("div.card"):
            game_titles = [title.text.strip() for title in extra.select("p")]
            
            
            hrefs = [link.get("href") for link in extra.select("a")]
            sport = [title.text.strip() for title in extra.select("h5")]
            thumb = [icon.get("src") for icon in extra.select("img")]
            for title,sport, href,thumb in zip(game_titles,sport, hrefs,thumb):
                if self.progress_update(progress, title):
                        return items
                xbmc.sleep(200)
                items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None, league=sport.upper(), title=title, links=[JetLink(href)]))
        return items

    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        iframes[0].headers["Origin"] = f"https://{self.domains[0]}"
        iframes[0].headers["User-Agent"] = self.user_agent
        return iframes[0]