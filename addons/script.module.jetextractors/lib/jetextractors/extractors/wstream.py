import requests, re

from ..models import *
from ..util import jsunpack
from ..util import m3u8_src

class Wstream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["wstream.to", "wigistream.to"]
        self.resolve_only = True

    def get_link(self, url: JetLink) -> JetLink:
        if "Referer" not in url.headers:
            raise Exception("Must have referer in headers")
        r = requests.get(url.address, headers={"Referer": url.headers["Referer"]}).text
        if len(re.findall(r'source\s+?:\s+?"(.+?)"', r)) > 0:
            m3u8 = JetLink(re.compile(r'source\s+?:\s+?"(.+?)"').findall(r)[0])
        elif len(re.findall(r'src\s+?:\s+?"(.+?)"', r)) > 0:
            m3u8 = JetLink(re.findall(r'src\s+?:\s+?"(.+?)"', r)[0])
        else:
            re_js = jsunpack.unpack(re.compile(r"(eval\(function\(p,a,c,k,e,d\).+?{}\)\))").findall(r)[0])
            m3u8 = m3u8_src.scan_page(url.address, re_js)
        m3u8.inputstream = JetInputstreamFFmpegDirect.default()
        return m3u8