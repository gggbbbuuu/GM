import requests, re, base64
from bs4 import BeautifulSoup
from pyjsparser import parse

from ..models import *
from ..util.hunter import hunter

class PlyTv(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["reliabletv.me"]
        self.user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.resolve_only = True
    

    def get_auth_url(self, embed: str) -> str:
        auth_url = base64.b64decode(re.findall(r"const secTokenUrl = '(.+?)'", embed)[0]).decode("utf-8")
        scode = re.findall(r"const sCode = '(.+?)'", embed)[0]
        ts = re.findall(r"const expireTs = (.+?);", embed)[0]
        unique_id = re.findall(r"const strUnqId = '(.+?)'", embed)[0]
        return f"{auth_url}/?stream={unique_id}&scode={scode}&expires={ts}"


    def __plytv_sdembed(self, base_url, origin):
        if not base_url.startswith("http"):
            base_url = f"https://{self.domains[0]}/sd0embed?v=" + base_url
        r = requests.post(base_url, headers={"Origin": origin, "Referer": origin, "User-Agent": self.user_agent}).text
        soup = BeautifulSoup(r, "html.parser")
        script = next(s for s in soup.select("script") if s.attrs == {})
        p = parse(script.string)
        for c, cmd in enumerate(p["body"]):
            if cmd["type"] == "VariableDeclaration":
                for declaration in cmd["declarations"]:
                    var_name = declaration['id']['name']
                    if 'name' in declaration['init']:
                        var_declare = declaration['init']['name']
                    else:
                        if declaration['init']['value'] != '':
                            var_declare = f"'{declaration['init']['value']}'"
                        else:
                            var_declare = "''"
                    exec(f"{var_name} = {var_declare}")
            elif cmd["type"] == "ExpressionStatement" and cmd["expression"]["type"] != "CallExpression":
                if cmd["expression"]["type"] == "AssignmentExpression":
                    exps = [cmd["expression"]]
                else:
                    exps = cmd["expression"]["expressions"]
                for exp in exps:
                    exec(f"{exp['left']['name']} = {exp['right']['left']['name']} {exp['right']['operator']} {exp['right']['right']['name']}")
        result = eval(p["body"][-2]["expression"]["arguments"][0]["name"])
        re_hunter = re.compile(r'decodeURIComponent\(escape\(r\)\)}\("(.+?)",(.+?),"(.+?)",(.+?),(.+?),(.+?)\)').findall(result)[0]
        deobfus = hunter(re_hunter[0], int(re_hunter[1]), re_hunter[2], int(re_hunter[3]), int(re_hunter[4]), int(re_hunter[5]))
        re_m3u8 = base64.b64decode(re.findall(r"const playUrl = '(.+?)';", deobfus)[0]).decode("utf-8")
        auth_url = self.get_auth_url(deobfus)
        auth = requests.get(auth_url, headers={"Referer": base_url, "User-Agent": self.user_agent, "Origin": f"https://{self.domains[0]}"})
        return JetLink(address=re_m3u8, headers={"Referer": f"https://{self.domains[0]}/sd0embed", "User-Agent": self.user_agent, "Origin": f"https://www.{self.domains[0]}"}, is_widevine=True, manifest_type="hls", license_url="h")

    
    def plytv_sdembed(self, endpoint, vid, origin):
        # TODO: REMOVE
        # referer = "https://embedstream.me/nfl/nfl-network-stream-1"
        # origin = "https://embedstream.me"
        # endpoint = "NFL"

        base_url = f"https://{self.domains[0]}/sd0embed/{endpoint}"
        r_embed = requests.get(base_url, headers={"Referer": origin, "User-Agent": self.user_agent}, params={"v": vid}).text
        re_b64 = re.findall(r"const videoUrl = '(.+?)';", r_embed)[0]
        url = base64.b64decode(base64.b64decode(re_b64).decode("UTF-8")).decode("UTF-8")
        auth_url = self.get_auth_url(r_embed)
        r = requests.get(auth_url, headers={"Referer": base_url, "User-Agent": self.user_agent}).text
        return JetLink(address=url, headers={"Referer": base_url, "User-Agent": self.user_agent, "Origin": f"https://{self.domains[0]}"})

    def get_link(self, url: JetLink) -> JetLink:
        if "Origin" not in url.headers:
            raise Exception("Origin not in headers")
        return self.plytv_sdembed(url.address, url.headers["Origin"])
