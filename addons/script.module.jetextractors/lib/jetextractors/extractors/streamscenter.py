from ..models import *
import requests
import re

class StreamsCenter(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamscenter.live", "streamscenter.online"]
        self.name = "StreamsCenter"
        self.resolve_only = True

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address, headers={"Referer": "https://streameast.ph/"})
        re_iframe = "https:" + re.findall(r'iframe.+?src="(.+?)"', r.text)[0]
        r = requests.get(re_iframe, headers={"Referer": url.address})
        payload = re.findall(r'input: "(.+?)"', r.text)[0]
        r = requests.post(f"https://{self.domains[0]}/embed/decrypt.php", data={"input": payload})
        return JetLink(r.text, headers={"User-Agent": self.user_agent, "Referer": url.address})
    