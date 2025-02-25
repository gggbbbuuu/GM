import requests, re
from ..models import *

class Streamtape(JetExtractor):
    domains = ["streamtape.com"]
    name = "Streamtape"
    resolve_only = True

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address, headers={"User-Agent": self.user_agent, "Referer": url.address}).text
        script = re.findall(r"getElementById\('norobotlink'\)\.innerHTML = (.+?);<", r)[0]
        substrs = re.findall(r"\.substring\((.+?)\)", script)
        script = script[:script.index(".", 36)]
        for s in substrs:
            script = script + f"[{s}:]"
        link = "https:" + eval(script)
        return JetLink(link, headers={"User-Agent": self.user_agent})

