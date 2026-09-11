import re
from ..models import *
from .._core import fetch_page, get_session

class Techoreels(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["techclips.net", "techoreels.com"]
        self.resolve_only = True

    def __find_link(self, url, servers, serv_eval):
        for serv in servers:
            stream = eval(serv_eval)
            s = get_session(referer=url)
            r_stream = s.get(stream)
            if r_stream.status_code == 200:
                return JetLink(address=stream, headers=get_headers(referer=url))

    def get_link(self, url: JetLink) -> JetLink:
        r = fetch_page(url.address)
        servers = re.findall(r'var servs = (\[.+?\]);', r)
        if len(servers) > 0:
            servers = eval(servers[0])
            serv_eval = re.findall(r"source: (.+?),", r)[0]
            return self.__find_link(url.address, servers, serv_eval)
        else:
            iframe = re.findall(r'iframe src="(.+?)"', r)[0]
            r_iframe = fetch_page(iframe)
            servers = eval(re.findall(r'var servs = (\[.+?\]);', r_iframe)[0])
            serv_eval = re.findall(r"source: (.+?),", r_iframe)[0]
            return self.__find_link(url, servers, serv_eval)