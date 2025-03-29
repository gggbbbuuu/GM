import requests, re, dateutil.parser
from bs4 import BeautifulSoup
from datetime import timedelta
from ..models import *

class Sixstream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["v.markkystreams.com", "6streams.tv"]
        self.name = "6stream"
        self.short_name = "6S"
    

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get("https://" + self.domains[0], timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        categories = soup.select("ul.nav > li.menu-item > a")
        categories = categories[:int(len(categories) / 2)] # Remove bottom nav buttons
        for category in categories:
            if "Streams" not in category.text:
                continue
            if self.progress_update(progress, category.text):
                return items
            
            try:
                league = category.text.replace(" Streams", "")
                href = category.get("href")
                r_league = requests.get(href, timeout=self.timeout).text
                soup_league = BeautifulSoup(r_league, "html.parser")
                for game in soup_league.find_all("figure"):
                    try:
                        icon = game.get("data-original")
                        sibling = game.next_sibling
                        title = sibling.select_one("h2.entry-title > a").get("title")
                        game_href = game.find("a").get("href")
                        utc_time = None
                        if title.lower().endswith("et"): # this is dumb
                            time = " ".join(title.split(" ")[::-1][:3][::-1])
                            utc_time = dateutil.parser.parse(time.upper()) + timedelta(hours=4)
                            title = title.replace(time, "").strip()

                        items.append(JetItem(title=title, icon=icon, league=league, starttime=utc_time, links=[JetLink(address=game_href)]))
                    except:
                        continue
            except:
                continue
        return items
    
    
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        m3u8 = JetLink(address=re.compile(r'source: "(.+?)"').findall(r)[0].replace(".m3u8", ".m3u8?&Connection=keep-alive"), headers={"Referer": url.address, "User-Agent": self.user_agent}, inputstream=JetInputstreamAdaptive.hls())
        return m3u8
    