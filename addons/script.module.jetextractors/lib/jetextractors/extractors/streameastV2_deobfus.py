from ..models import *
import requests

class Streameast(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["the.streameast.app"]
        self.name = "StreamEast"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get("https://magnetic.website/Jetextractor/streameast.json").json()
        items = [JetItem.from_dict(item) for item in r]
        for item in items:
            for link in item.links:
                link.inputstream = JetInputstreamFFmpegDirect.default()
                link.direct = True
        return items
    