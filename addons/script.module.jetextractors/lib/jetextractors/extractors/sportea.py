from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress
from .embedsports import Embedsports
from .streamed import Streamed
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from ..util import m3u8_src

class Sportea(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamex.cc","us-east.sportea.link", "cdn.snapinstadownload.xyz", "taxifrankfurt.click", "api.chinamarket.bond"]
        self.name = "Sportea"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []

        r = requests.get(f"https://{self.domains[0]}/api/schedule", timeout=self.timeout).json()
        for d in r:
            for sport in d["schedule"]:
                for event in sport["league_schedule"]:
                    links = [JetLink(link["stream_link"], name=link["stream_name"]) for link in event["streams"]]
                    icon = event["strThumb"]
                    title = f'{event["teams"]} - {event["event_date"]}, {event["event_time"]} ({"Live" if event["live_status"] == 1 else "Not Started"})'
                    league = event["sch_sport"]
                    status = event["tsdb_status"]
                    items.append(JetItem(title, links, icon=icon, league=league, status=status))
        return items
    
    def get_link(self, url):
        if "/live/embed" in url.address:
            url.address = url.address.replace("/live/embed/", "/live/channel.php?ch=")
        elif any(a for a in {"/live/alpha", "/live/bravo", "/live/charlie", "/live/delta", "/live/echo"} if a in url.address):
            url.address += "/embed"
        referer = urlparse(url.address).netloc
        r = requests.get(url.address, verify=False, headers={"Referer": f"https://{referer}/"})
        if m3u8 := m3u8_src.scan(r.text):
            if m3u8.startswith("//"):
                m3u8 = "https:" + m3u8
            return JetLink(m3u8, headers={"Referer": url.address})
        else:
            soup = BeautifulSoup(r.text, "html.parser")
            iframe = soup.find("iframe").get("src")
            streamed = Streamed()
            url = f"https://{streamed.domains[0]}/api/stream{urlparse(iframe).path.replace('/embed', '')}"
            if url.endswith("/1"):
                url = url[:-2]
            links = streamed.get_links(JetLink(url))
            # links = streamed.get_links(links[0])
            es = Embedsports()
            link = es.get_link(links[0])
            return link

        