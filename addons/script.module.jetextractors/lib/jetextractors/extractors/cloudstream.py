from ..models import *
from .._core import fetch_page
from ..util import jsunpack
import re

class CloudStream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["cloudstream.to"]
        self.resolve_only = True
    
    def get_link(self, url: JetLink) -> JetLink:
        r = fetch_page(url.address, referer=url.address)
        re_js = jsunpack.unpack(re.compile(r"(eval\(function\(p,a,c,k,e,d\).+?{}\)\))").findall(r)[0])
        m3u8 = re.findall(r'var src.?=.?"(.+?)"', re_js)[0]
        return JetLink(address=m3u8, headers={"Referer": url.address})
    