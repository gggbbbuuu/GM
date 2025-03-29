from ..models import *

class Template(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["example.com"]
        self.name = "Template"
        self.short_name = "TP"
        self.resolve_only = True


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        return items


    def get_links(self, url: JetLink) -> List[JetLink]:
        return []
    

    def get_link(self, url: JetLink) -> JetLink:
        return JetLink(url.address)
    