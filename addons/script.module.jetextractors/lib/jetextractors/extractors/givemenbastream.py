import re
from ..models import *
from .._core import fetch_page, get_headers
from ..util.hunter import hunter
from ..util import m3u8_src

class GiveMeNBAStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["givemereddit.eu", "official.givemeredditstream.cc", "givemenbastreams.com", "givemenflstreams.com"]
        self.resolve_only = True


    def get_link(self, url: JetLink) -> JetLink:
        r = fetch_page(url.address)
        re_iframe = re.findall(r'iframe class=\"embed-responsive-item\" src=\"(.+?)\"', r)
        if len(re_iframe) != 0:
            r = fetch_page(re_iframe[0], referer=url.address)
        re_hunter = re.findall(r'decodeURIComponent\(escape\(r\)\)}\("(.+?)",(.+?),"(.+?)",(.+?),(.+?),(.+?)\)', r)[0]
        deobfus = hunter(re_hunter[0], int(re_hunter[1]), re_hunter[2], int(re_hunter[3]), int(re_hunter[4]), int(re_hunter[5]))
        m3u8 = m3u8_src.scan_page(url.address, deobfus)
        m3u8.headers["User-Agent"] = get_headers()["User-Agent"]
        return m3u8