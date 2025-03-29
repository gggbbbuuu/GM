import requests, re
from urllib.parse import urlparse
from ..models import *

class Topravideo(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["topravideo.com", "vvtodmat.topravideo.com"]
        self.resolve_only = True

    def get_link(self, url: JetLink) -> JetLink:
        video_id = urlparse(url.address).path.split("/")[-1]
        url.address = f"https://vvtodmat.topravideo.com/embed/{video_id}?autoplay=1&htmlplayer=1"
        r = requests.get(url.address).text
        re_m3u8 = re.findall(r"hls:'(.+?)'", r)
        return JetLink(address="https:" + re_m3u8[0])