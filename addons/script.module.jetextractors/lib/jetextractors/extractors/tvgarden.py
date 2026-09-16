from ..models import *
from .._core import fetch_json

class TVGarden(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["tv.garden"]
        self.name = "TVGarden"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        if params is None:
            r = fetch_json("https://raw.githubusercontent.com/TVGarden/tv-garden-channel-list/refs/heads/main/channels/raw/countries_metadata.json")
            if r is None:
                return items
            for code, data in r.items():
                items.append(JetItem(data["country"], links=[], params={"code": code.lower()}))
        else:
            r = fetch_json(f"https://raw.githubusercontent.com/TVGarden/tv-garden-channel-list/refs/heads/main/channels/raw/countries/{params['code']}.json")
            if r is None:
                return items
            for channel in r:
                links = [JetLink(url) for url in channel["iptv_urls"] + channel["youtube_urls"]]
                items.append(JetItem(channel["name"], links))

        return items
    