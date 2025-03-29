import requests, re
from ..models import *
from ..util.hunter import hunter
from ..util import m3u8_src

class GiveMeNBAStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["givemereddit.eu", "official.givemeredditstream.cc", "givemenbastreams.com", "givemenflstreams.com"]
        self.resolve_only = True


    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        re_iframe = re.findall(r'iframe class=\"embed-responsive-item\" src=\"(.+?)\"', r)
        if len(re_iframe) != 0:
            r = requests.get(re_iframe[0], headers={"User-Agent": self.user_agent, "Referer": url.address}).text
        re_hunter = re.findall(r'decodeURIComponent\(escape\(r\)\)}\("(.+?)",(.+?),"(.+?)",(.+?),(.+?),(.+?)\)', r)[0]
        deobfus = hunter(re_hunter[0], int(re_hunter[1]), re_hunter[2], int(re_hunter[3]), int(re_hunter[4]), int(re_hunter[5]))
        m3u8 = m3u8_src.scan_page(url.address, deobfus)
        m3u8.headers["User-Agent"] = self.user_agent
        return m3u8