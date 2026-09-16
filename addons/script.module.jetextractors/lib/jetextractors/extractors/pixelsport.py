from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress
from typing import Optional, List
from .._core import fetch_json

class PixelSport(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["pixelsport.tv"]
        self.name = "PixelSports"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        events_data = fetch_json("https://pixelsport.tv/backend/liveTV/events")
        if events_data is None:
            return items
        events = events_data["events"]
        for event in events:
            items.append(JetItem(
                title=event["match_name"],
                # starttime=datetime.fromisoformat(event["date"]),
                links=[JetLink(link, direct=True, headers={"Referer": f"https://{self.domains[0]}/", "User-Agent": self.user_agent}) for link in map(lambda x: event["channel"][f"server{x}URL"], range(1, 4)) if link != "null"],
                icon=event["competitors1_logo"],
                league=event["competitors1_logo"].split("/")[-4].upper()
            ))
        items.sort(key=lambda x: (x.league or "", x.title))
        sliders_data = fetch_json("https://pixelsport.tv/backend/slider/getSliders")
        if sliders_data is None:
            return items
        sliders = sliders_data["data"]
        for slider in sliders:
            items.append(JetItem(
                title=slider["title"],
                links=[JetLink(link, direct=True, headers={"Referer": f"https://{self.domains[0]}/", "User-Agent": self.user_agent}) for link in map(lambda x: slider["liveTV"][f"server{x}URL"], range(1, 4)) if link != "null"],
                # icon=f"https://{self.domains[0]}/{slider["image"].replace("uploads", "backend")}",
            ))
        
        return items
    