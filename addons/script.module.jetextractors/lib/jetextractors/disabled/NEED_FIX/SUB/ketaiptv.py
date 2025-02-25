import requests
from bs4 import BeautifulSoup
from ..models import *
from ..util import m3u8_src

class KetaIPTV(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["ketaiptv.me"]
        self.name = "KetaIPTV"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}/search.php?search=+", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for item in soup.select("li.channel-item"):
            title = item.text.strip()
            if "PORN" in title.upper() or "XXX" in title.upper() or "18+" in title.upper():
                continue
            link = item.select("a")[-1].get("href")
            items.append(JetItem(title, [JetLink(link)]))
        return items


    def get_link(self, url: JetLink) -> JetLink:
        return m3u8_src.scan_page(url)