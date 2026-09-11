import re
from ..models import *
from .._core import fetch_page

class Tinyurl(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamcheck.link"]
        self.shortener = True
        self.resolve_only = True
    
    def get_link(self, url: JetLink) -> JetLink:
        r = fetch_page(url.address)
        link = re.findall(r"window.location.href = '(.+?)'", r)[0]
        return JetLink(link)
    