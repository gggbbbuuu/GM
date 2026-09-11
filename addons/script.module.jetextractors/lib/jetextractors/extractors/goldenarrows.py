from ..models import *
import re
from .._core import fetch_page, get_headers, make_link
from bs4 import BeautifulSoup
from .wstream import Wstream
from dateutil.parser import parse

class GoldenArrows(JetExtractor):
    def __init__(self) -> None:
        self.name = "GoldenArrows"
        self.domains = ["goldenarrowschannel.info"]

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = fetch_page(f"https://{self.domains[0]}/internal/schedule-int.html")
        soup = BeautifulSoup(r, "html.parser")
        for game in soup.select("tr"):
            game_date = game.contents[1].text.strip()
            if game_date == "Date": continue
            game_time = game.contents[3].text.strip()
            game_name = game.contents[7].text.strip()
            game_href = game.select("a")[-1].get("href")
            game_utc = parse(f"{game_date} {game_time}")
            items.append(JetItem(title=game_name, links=[JetLink(address=game_href)], starttime=game_utc, league="Darts"))
        return items
    

    def get_link(self, url: JetLink) -> JetLink:
        if "internal" not in url.address:
            url.address = url.address.replace("/stream", "/internal/stream")
        r = fetch_page(url.address)
        iframe = re.findall(r'iframe src="(.+?)"', r)[0]
        if iframe.startswith("//"):
            iframe = "https:" + iframe
        return Wstream().get_link(make_link(iframe, referer=url.address))