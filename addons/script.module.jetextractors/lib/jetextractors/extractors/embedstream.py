import requests, re
from ..models import *
from .plytv import PlyTv

class Embedstream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["embedsports.me"]
        self.name = "Embedstream"
        self.resolve_only = True


    def embedstream(self, id: str):
        r_embedstream = requests.get(f"https://{self.domains[0]}/" + id).text
        zmid = re.compile(r'zmid = "(.+?)"').findall(r_embedstream)[0]
        game_cat = re.findall(r'gameCat="(.+?)"', r_embedstream)[0]
        return PlyTv().plytv_sdembed(game_cat, zmid, f"https://{self.domains[0]}/")


    def get_link(self, url: JetLink) -> JetLink:
        return self.embedstream(url.address.replace(f"https://{self.domains[0]}/", ""))