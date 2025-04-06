from ..models import *
import requests
from datetime import datetime

class PixelSport(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["pixelsport.tv"]
        self.name = "PixelSports"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        events = requests.get("https://pixelsport.tv/backend/liveTV/events").json()["events"]
        for event in events:
            items.append(JetItem(
                title=event["match_name"],
                # starttime=datetime.fromisoformat(event["date"]),
                links=[JetLink(link, direct=True) for link in map(lambda x: event["channel"][f"server{x}URL"], range(1, 4)) if link != "null"],
                icon=event["competitors1_logo"],
                league=event["competitors1_logo"].split("/")[-4].upper()
            ))
        sliders = requests.get("https://pixelsport.tv/backend/slider/getSliders").json()["data"]
        for slider in sliders:
            items.append(JetItem(
                title=slider["title"],
                links=[JetLink(link, direct=True) for link in map(lambda x: slider["liveTV"][f"server{x}URL"], range(1, 4)) if link != "null"],
                # icon=f"https://{self.domains[0]}/{slider["image"].replace("uploads", "backend")}",
            ))
        return items
    