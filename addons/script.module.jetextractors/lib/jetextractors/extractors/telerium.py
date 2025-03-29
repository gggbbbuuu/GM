import requests, re
from ..models import *
from datetime import datetime, timedelta


class Telerium(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["telerium.tv", "teleriumtv.net", "teleriumtv.com"]
        self.resolve_only = True

    
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address, headers={"User-Agent": self.user_agent}).text
        re_cid = re.findall(r"var cid = \"(.+?)\";", r)[0]
        now = int((datetime.now().replace(second=0, microsecond=0) + timedelta(days=1)).timestamp()) * 1000
        telerium_url = f"https://teleriumtv.com/streams/{re_cid}/{now}.json"
        headers = {"User-Agent": self.user_agent, "Referer": url.address, "Origin": "https://teleriumtv.com", "Accept": "*/*"}
        r_streams = requests.get(telerium_url, headers=headers, cookies={"volume": "0"}).json()
        m3u8 = "https:" + r_streams["url"]
        if "tokenurl" in r_streams:
            r_token = requests.get("https://teleriumtv.com" + r_streams["tokenurl"], headers=headers).json()
            token = r_token[10][::-1]
            m3u8 += token
        return JetLink(address=m3u8, headers={"Referer": url.address, "User-Agent": self.user_agent})
        

# def get_m3u8(url):
#     r_embed = requests.get(url, headers={"Referer": "https://live-golf.stream/", "User-Agent": user_agent, "Cookie": "__ga=100"}).text
#     js_obfus = "eval" + re.compile(r"eval(.+?)\.split").findall(r_embed)[0] + ".split('|'),0,{}))"
#     js_unpacked = jsunpack.unpack(js_obfus)
#     js_variables = re.compile(r"url:window\.atob\((.+?)\)\.slice\((.+?)\)\+window\.atob\((.+?)\)").findall(js_unpacked)[0]
#     json_url_start_var = re.compile(r'function changlasmuy\(.+?,(.+?),.+?\)').findall(js_unpacked)[0]
#     json_url_start = "https:" + base64.b64decode(re.compile(r'%s="(.+?)"' % (json_url_start_var)).findall(js_unpacked)[0].encode("ascii")).decode("utf-8")
#     json_url_args = base64.b64decode(re.compile(r'%s="(.+?)"' % (js_variables[2])).findall(js_unpacked)[0].encode("ascii")).decode("utf-8")
#     json_url = (json_url_start + json_url_args).replace(re.compile(r"https:\/\/(.+?)\/").findall(json_url_start)[0], "telerium.tv")
    
#     r_json = requests.get(json_url, headers={"Referer": url, "User-Agent": user_agent, "Cookie": "__ga=100"}).text
#     url_args_idx_variable = re.compile(r"=dameVuelta\(.+?\[(.+?)\]").findall(js_unpacked)[0]
#     url_args_idx = __solveIdx(js_unpacked, url_args_idx_variable)
#     url_args = json.loads(r_json)[url_args_idx][::-1]
#     url = json_url_start + url_args + ("|Referer=%s&User-Agent=%s" % (url, user_agent))

#     return url

# def __solveIdx(js, url_args_idx_variable):
#     if len(re.compile(r"%s=([a-zA-Z]{10})([+-])([a-zA-Z]{10});" % (url_args_idx_variable)).findall(js)) > 0:
#         re_vars = re.compile(r"%s=([a-zA-Z]{10})([+-])([a-zA-Z]{10});" % (url_args_idx_variable)).findall(js)[0]
#         return (__solveIdx(js, re_vars[0]) + __solveIdx(js, re_vars[2]) * (1 if re_vars[1] == "+" else -1))
#     elif len(re.compile(r"%s=(\d+);" % (url_args_idx_variable)).findall(js)) > 0:
#         return int(re.compile(r"%s=(\d+);" % (url_args_idx_variable)).findall(js)[0])
