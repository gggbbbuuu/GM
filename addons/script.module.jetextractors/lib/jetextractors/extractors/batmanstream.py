import requests, re, json, time
from datetime import datetime, timedelta
from ..models import *

class BatmanStream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["batmanstream.org"]
        self.name = "Batmanstream"
        self.short_name = "BMS"

    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get("https://live.batstream.live/list.php", timeout=self.timeout).text
        ev_arr = re.findall(r"var ev_arr = (\[.+?\]);", r)[0]
        events = json.loads(ev_arr)
        chan_arr = re.findall(r"var chan_arr = (.+?);", r)[0]
        channels = json.loads(chan_arr)
        for event in events:
            try:
                title = event["match"]
                icon = "https://live.batstream.live/img/countries/" + event["country"]
                sport = event["sport"]
                date = datetime(*(time.strptime(event["date"], "%Y-%m-%d %H:%M:%S")[:6])) - timedelta(hours=1)
                links = [JetLink(address=("https:" + link) if link.startswith("//") else link) for link in filter(lambda x: "advsmedia" not in x, [link["link"] for link in channels[event["id"]]])]
                items.append(JetItem(title=title, icon=icon, league=sport, starttime=date, links=links))
            except:
                continue
        return items