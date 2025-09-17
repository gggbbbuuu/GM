from ..models import *
import requests
from datetime import datetime

class Streamed(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamed.pk"]
        self.name = "Streamed"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        sports = requests.get(f"https://{self.domains[0]}/api/sports").json()
        sports_map = { sport["id"]: sport["name"] for sport in sports }

        matches = requests.get(f"https://{self.domains[0]}/api/matches/all-today/popular").json()
        for match in matches:
            title = match["title"]
            if match["date"] != 0:
                match_time = datetime.fromtimestamp(match["date"] / 1000)
            else:
                match_time = None
            print(title, match_time)
            sport = sports_map[match["category"]]
            links = [JetLink(f"https://{self.domains[0]}/api/stream/{source['source']}/{source['id']}", links=True, name=source["source"].capitalize()) for source in match["sources"]]
            items.append(JetItem(title, links, match_time, league=sport))
        return items
    
    def get_links(self, url):
        if "/api/" in url.address:
            streams = requests.get(url.address).json()
            links = [JetLink(stream["embedUrl"], name=f"Stream {stream['streamNo']} [{stream['language'] or 'N/A'}, {'HD' if stream['hd'] else 'SD'}, {stream['viewers']} viewers]") for stream in streams]
            return links
        elif "/watch/" in url.address:
            match_id = url.address.split("/")[-1]
            matches = requests.get(f"https://{self.domains[0]}/api/matches/all").json()
            for match in matches:
                if match["id"] != match_id:
                    continue
                links = [JetLink(f"https://{self.domains[0]}/api/stream/{source['source']}/{source['id']}", links=True, name=source["source"].capitalize()) for source in match["sources"]]
                return links
    
    def get_link(self, url):
        if "/watch/" not in url.address:
            split = url.address.split("/")
            source = split[-2]
            source_id = split[-1]
            url.address = f"https://{self.domains[0]}/api/stream/{source}/{source_id}"
            return JetLink(url.address, headers={"User-Agent": self.user_agent, "Referer": f"https://{self.domains[0]}/"}, inputstream=JetInputstreamFFmpegDirect.default())
            
