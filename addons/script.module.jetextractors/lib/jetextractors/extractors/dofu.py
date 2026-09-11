import re
from bs4 import BeautifulSoup
from ..models import JetExtractor, JetItem, JetLink
from typing import List
from .._core import get_session
from .embedsports import Embedsports


class Dofu(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["dofusports.xyz"]
        self.name = "Dofu"
    

    def get_items(self, params = None, progress = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        page = int(params["page"]) if params is not None else 1
        while page < 20:
            if self.progress_update(progress, f"Page {page}"):
                break
            r = get_session().get(f"http://{self.domains[0]}/games/page/{page}/", headers={"Accept-Encoding": "identity"}, timeout=self.timeout).text
            soup = BeautifulSoup(r, "html.parser")
            for article in soup.select("article"):
                a = article.select_one("a")
                title = a.text
                href = a.get("href")
                items.append(JetItem(title, links=[JetLink(href)]))
            if next := soup.select_one("main#content > a"):
                if next.text[0] == "«":
                    break
            else:
                break
            page += 1
        return items

    def get_link(self, url: JetLink) -> JetLink:
        r = get_session().get(url.address, headers={"Accept-Encoding": "identity"}, timeout=self.timeout).text
        iframe = re.findall(r"iframe.+?src='(.+?)'", r)[0]
        if "embedsports.top" in iframe:
            es = Embedsports()
            return es.get_link(JetLink(iframe))
        else:
            r = get_session(referer=url.address).get(iframe, headers={"Accept-Encoding": "identity"}, timeout=self.timeout).text
            if fid_regex := re.findall(r'fid="(.+?)";.+?src="\/\/(.+?)\.js"', r):
                fid, src = fid_regex[0]
                player_url = f"https://{src}.php?player=desktop&live=" + fid
                r_iframe = get_session(referer=iframe).get(player_url, timeout=self.timeout).text
                eval_url = ("".join(eval(re.findall(r"return\((\[.+?\])", r_iframe)[0]))).replace("\\", "").replace("////", "//")
                return JetLink(eval_url, headers={"User-Agent": self.user_agent, "Referer": player_url})
            else:
                m3u8 = re.findall(r'source: "(.+?)"', r)[0]
                return JetLink(m3u8, headers={"Referer": iframe})
