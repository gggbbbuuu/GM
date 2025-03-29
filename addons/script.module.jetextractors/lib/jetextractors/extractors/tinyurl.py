import requests, re
from ..models import *


class Tinyurl(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamcheck.link"]
        self.shortener = True
        self.resolve_only = True
    
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        link = re.findall(r"window.location.href = '(.+?)'", r)[0]
        return JetLink(link)
    