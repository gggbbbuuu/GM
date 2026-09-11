from ..models import *
from .._core import fetch_page

class Streamtape(JetExtractor):
    domains = ["streamtape.com"]
    name = "Streamtape"
    resolve_only = True

    def get_link(self, url: JetLink) -> JetLink:
        r = fetch_page(url.address, referer=url.address)
        script = re.findall(r"getElementById\('norobotlink'\)\.innerHTML = (.+?);<", r)[0]
        substrs = re.findall(r"\.substring\((.+?)\)", script)
        script = script[:script.index(".", 36)]
        for s in substrs:
            script = script + f"[{s}:]"
        link = "https:" + eval(script)
        return JetLink(link, headers=get_headers())

