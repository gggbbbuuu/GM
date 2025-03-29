import requests, re, json, html
from ..models import *

class OkRu(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["ok.ru"]
        self.resolve_only = True

    def get_link(self, url: JetLink) -> JetLink:
        r_embed = requests.get(url.address, headers={"User-Agent": self.user_agent}).text
        embed_json = json.loads(html.unescape(re.compile(r'data-options="(.+?)"').findall(r_embed)[0]))
        metadata_json = json.loads(embed_json["flashvars"]["metadata"])
        return JetLink(address=metadata_json["hlsManifestUrl"] if "hlsManifestUrl" in metadata_json else metadata_json["hlsMasterPlaylistUrl"], headers={"User-Agent": self.user_agent})