from ..models import *
from ..util import find_iframes

class MixSports1(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["methstreams.me/","streameast.top","bestsolaris.com","topstreams.me","givemeredditstreams.me","nbastreams.org","thesportsurge.net","rojadirecta.io","rnbastreams.net","vipboxs.net/","thebuffstreams.com","streameast.stream","hesgoals.to","rainostream4u.online","worldstreams.watch"]
        self.name = "MixSports1"
        self.resolve_only = True


    def get_link(self, url: JetLink) -> JetLink:
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
        return iframes[0]


