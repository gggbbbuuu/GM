import json
from urllib.parse import urlparse, parse_qs
from ..models import *
from .._core import fetch_json, get_session

class Sofascore(JetExtractor):
    def __init__(self) -> None:
        self.disabled = True
        self.domains = ["redditsport.live"]
        self.proxy_dict = {
            "http": "http://3.211.65.185:80",
            "https": "http://3.211.65.185:80",
            "ftp": "10.10.1.10:3128"
        }


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        session = get_session(proxies=self.proxy_dict)
        event_count = session.get("https://api.sofascore.com/api/v1/sport/-28800/event-count", timeout=self.timeout)
        return items
       
    def get_links(self, url):
        r = fetch_json(url.address)
        if r is None:
            return []
        game_id = parse_qs(urlparse(url.address).query)["id"]
        streams = filter(lambda x: x["event"] == game_id, r)
        links = [JetLink(address=stream["link"]) for stream in streams]
        return links