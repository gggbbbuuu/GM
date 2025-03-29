from ..models import *
from ..util import find_iframes
from .voodc import Voodc
# from .givemereddit import GiveMeReddit

class Mix2(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["yyyyy.xyz"]
        self.resolve_only = True


    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        link = iframes[0]
        # if "giveme" in link.address:
        #     return GiveMeReddit().get_link(link.address)
        if "voodc" in link.address:
            return Voodc().get_link(link.address)
        if "freesportstime" in link.address:
            del link.headers["Referer"]
        return iframes[0]
