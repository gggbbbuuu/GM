import requests, re, base64, time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..util import find_iframes
from ..models import *

class Onestream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["1stream.eu"]
        self.name = "1stream"
#######  NEED FIXING  ########

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = f"http://{self.domains[0]}"
        r = requests.get(base_url, timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        categories = soup.select("ul.navbar-nav > li > a")
        for category in categories:
            if self.progress_update(progress, category.text):
                return items
            
            try:
                league = category.text.replace(" streams", "").replace(" Streams", "")
                href = category.get("href")
                r_category = requests.get(base_url + href, timeout=self.timeout).text
                soup = BeautifulSoup(r_category, "html.parser")
                for game in soup.find_all("a", class_="btn-block"):
                    try:
                        url = game.get("href")
                        icon = game.find("img").get("src")
                        title = game.find("h4").text.strip()
                        time_str = game.find("p").text.strip()
                        utc_time = datetime(*(time.strptime(time_str, "%a %d %b %Y %H:%M %p EST")[:6])) + timedelta(hours=5)
                        items.append(JetItem(title=title, links=[JetLink(address=url)], icon=icon, league=league, starttime=utc_time))
                    except:
                        continue

            except:
                continue
        return items
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        re_iframe = re.findall(r'iframe.+?src="(.+?)"',r)[0]
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(re_iframe)]
        link = iframes[0]
        
        link.inputstream = JetInputstreamFFmpegDirect.default()
        return link
    
    # def get_link(self, url: JetLink) -> JetLink:
    #     r = requests.get(url.address).text
    #     link = base64.b64decode(re.findall(r'window.atob\("(.+?)"\)', r)[0]).decode("utf-8")
    #     return JetLink(link, headers={"Referer": f"https://{self.domains[0]}/", "Origin": f"https://{self.domains[0]}"})
    