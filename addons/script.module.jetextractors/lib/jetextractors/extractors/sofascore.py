import requests
from urllib.parse import urlparse, parse_qs
from ..models import *

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
        event_count = requests.get("https://api.sofascore.com/api/v1/sport/-28800/event-count", proxies=self.proxy_dict, timeout=self.timeout)
        return items
        

    def get_links(self, url):
        r = requests.get(url.address).json()
        game_id = parse_qs(urlparse(url.address).query)["id"]
        streams = filter(lambda x: x["event"] == game_id, r)
        links = [JetLink(address=stream["link"]) for stream in streams]
        return links