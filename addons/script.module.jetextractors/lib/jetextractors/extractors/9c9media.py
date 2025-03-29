from ..models import *

class NineC9Media(JetExtractor):
    def __init__(self) -> None:
        self.domains = [".+9c9media.com", ".+9c9media.akamaized.net"]
        self.domains_regex = True
        self.resolve_only = True
    
    def get_link(self, url: JetLink):
        return JetLink(address=url.address, inputstream=JetInputstreamAdaptive(manifest_type="mpd", license_key="https://mvplicense.9c9media.ca/widevine||R{SSM}|"))