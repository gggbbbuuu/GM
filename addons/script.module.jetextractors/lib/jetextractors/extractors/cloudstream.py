from ..models import *
import requests, re
from ..util import jsunpack

class CloudStream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["cloudstream.to"]
        self.resolve_only = True
    
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address, headers={"Referer": url.address}).text
        re_js = jsunpack.unpack(re.compile(r"(eval\(function\(p,a,c,k,e,d\).+?{}\)\))").findall(r)[0])
        m3u8 = re.findall(r'var src.?=.?"(.+?)"', re_js)[0]
        return JetLink(address=m3u8, headers={"Referer": url.address})
    