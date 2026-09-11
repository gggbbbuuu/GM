import re
from ..util import jsunpack

from ..models import *
from .._core import fetch_page, get_session

class Voodc(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["voodc.com"]
        self.name = "Voodc"
        self.short_name = "TP"
        self.user_agent = "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
        self.resolve_only = True


    def get_link(self, url: JetLink) -> JetLink:
        r = get_session().get(url.address, headers={"User-Agent": self.user_agent}, timeout=self.timeout).text
        script = "https:" + re.findall(r'" src="(.+?)"', r)[0]
        split = script.split("/")
        embed_url = f"https://voodc.com/player/d/{split[-1]}/{split[-2]}"
        r = get_session().get(embed_url, headers={"User-Agent": self.user_agent}, timeout=self.timeout).text
        re_m3u8 = re.findall(r'"file": \'(.+?)\'',  r)
        if len(re_m3u8) > 0:
            m3u8 = re_m3u8[0]
        else:
            fid = re.findall(r"fid='(.+?)'", r)[0]
            r_player = fetch_page(f"https://player.mycraft.click/{fid}")
            re_packed = re.findall(r"(}\(.+)", r_player)[0]
            jameiei = jsunpack.unpack(re_packed)
            m3u8 = "".join(map(lambda x: chr(int(x)), re.findall(r"\[(.+)\]", jameiei)[0].split(",")))
        return JetLink(m3u8, headers={"User-Agent": self.user_agent})