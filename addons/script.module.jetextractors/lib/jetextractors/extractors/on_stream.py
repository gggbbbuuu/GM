import re
from urllib.parse import urlparse, parse_qs
from ..models import *
from .._core import fetch_page

class Onstream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["on-stream.xyz"]
        self.resolve_only = True
    

    def get_link(self, url: JetLink) -> JetLink:
        qs = parse_qs(urlparse(url.address).query)
        if "id" in qs:
            url.address = f"https://{self.domains[0]}/ch/ch{qs['id'][0]}.php"
        r = fetch_page(url.address)
        fid = re.findall(r'\?ch=(.+?)"', r)[0]
        iframe = f"https://speci4leagle.com/spstream3.php?player=desktop&live=" + fid
        r_iframe = fetch_page(iframe)
        eval_url = ("".join(eval(re.findall(r"return\((\[.+?\])", r_iframe)[0]))).replace("\\", "").replace("////", "//")
        return JetLink(eval_url, headers=get_headers(referer=iframe))