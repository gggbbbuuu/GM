import requests
from ..models import *


class ABC(JetExtractor):
    def __init__(self) -> None:
        self.domains = [".+us-abc.symphony.edgedatg.go.com"]
        self.domains_regex = True
        self.resolve_only = True
    
    def get_link(self, url: JetLink) -> JetLink:
        payload = "=&video_type=live&uplynk_ct=c&device=001&brand=001&zipcode=94925&app_name=webplayer-abc&hdcp_level=1.4&video_id=VDKA0_sg8t9sdo&video_player=html5&resource_id=%253Crss%2Bversion%253D%25222.0%2522%2Bxmlns%253Amedia%253D%2522http%253A%252F%252Fsearch.yahoo.com%252Fmrss%252F%2522%253E%253Cchannel%253E%253Ctitle%253EABC%253C%252Ftitle%253E%253Citem%253E%253Ctitle%253EDATG%253C%252Ftitle%253E%253Cguid%253EVDKA0_sg8t9sdo%253C%252Fguid%253E%253Cmedia%253Arating%2Bscheme%253D%2522urn%253Ampaa%2522%253ENR%253C%252Fmedia%253Arating%253E%253C%252Fitem%253E%253C%252Fchannel%253E%253C%252Frss%253E&token=Bad%2520request.&auth_flag=1&token_type=ap&adobe_requestor_id=ABC&mvpd=DTV&user_id=1F4AE26E-77E5-4DD4-CDBE-16B90DC7429F"
        response = requests.request("POST", url.address, data=payload, headers={"content-type": "application/x-www-form-urlencoded", "Cookie": "VP2UID=1F4AE26E-77E5-4DD4-CDBE-16B90DC7429F_013_1_001_live_01-06-00_1.2.1.25; SWID=880ADD07-3408-42D0-A8BD-1C39FA2F9673"}).json()
        link = response["channels"]["channel"][0]["assets"]["asset"][0]["value"]
        return JetLink(address=link)