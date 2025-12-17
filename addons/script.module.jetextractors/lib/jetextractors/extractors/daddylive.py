import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode
import base64
from dateutil import parser
from datetime import datetime, timedelta
import re
import json
from binascii import unhexlify
from urllib3.util import SKIP_HEADER
import ast
import time

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import unpad
except Exception as _:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad
    except Exception as _:
        pass

from ..models import JetExtractor, JetExtractorProgress, JetItem, JetLink, JetInputstreamFFmpegDirect, JetInputstreamAdaptive
from ..util import find_iframes
from typing import Optional, List

STD_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'

class Daddylive(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["dlhd.dad"]
        self.name = "Daddylive"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        sched_headers = {
            "Origin": f'https://{self.domains[0]}', 
            "Referer": f'https://{self.domains[0]}/', 
            "User-Agent": STD_AGENT
        }

        r_schedule = requests.get(f"https://{self.domains[0]}", headers=sched_headers, timeout=self.timeout, verify=False)
        soup_schedule = BeautifulSoup(r_schedule.text, "html.parser")
        for schedule in soup_schedule.select("div#schedule > div.schedule__day"):
            header = schedule.select_one("div.schedule__dayTitle").text
            for category in schedule.select("div.schedule__category"):
                category_name = category.select_one("div.card__meta").text
                for event in category.select("div.schedule__event"):
                    title = event.select_one("span.schedule__eventTitle").text
                    starttime = event.select_one("span.schedule__time").get("data-time")
                    channels = event.select("div.schedule__channels > a")
                    links = [JetLink("https://" + self.domains[0] + a.get("href"), name=f'{a.get("title")} [CH-{a.get("href").split("=")[-1]}]', links=True) for a in channels]
                    try:
                        utc_time = self.parse_header(header, starttime) - timedelta(hours=1)
                    except Exception as _:
                        try:
                            utc_time = datetime.now().replace(hour=int(starttime.split(":")[0]), minute=int(starttime.split(":")[1])) - timedelta(hours=1)
                        except Exception as _:
                            utc_time = datetime.now()
                    items.append(JetItem(title, links, starttime=utc_time, league=category_name))
        
        if self.progress_update(progress):
            return items

        r_channels = requests.get(f"https://{self.domains[0]}/24-7-channels.php", headers=sched_headers, timeout=self.timeout, verify=False)
        soup_channels = BeautifulSoup(r_channels.text, "html.parser")
        for channel in soup_channels.select("div.grid > a.card"):
            href = "https://" + self.domains[0] + channel.get("href")
            title = channel.select_one("div.card__title").text
            if "18+" in title:
                continue
            channel_id = href.split("=")[-1]
            items.append(JetItem(title, links=[JetLink(href, name=f"{title} [CH-{channel_id}]", links=True)], league="[COLORorange]24/7[/COLOR]"))
        
        return items
    
    def get_links(self, url):
        r = requests.get(url.address, headers={"Accept-Encoding": SKIP_HEADER}, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")
        
        if links := soup.select("center > a"):
            return [JetLink(f"https://{self.domains[0]}{link.get('href')}", name=f"Player {i + 1} [{link.get('href').split('/')[-2].capitalize()}]") for i, link in enumerate(links)]
        elif links := soup.select("button.player-btn"):
            return [JetLink(link.get("data-url"), name=link.get("title"), headers={"Referer": r.request.url}) for link in links]
        else:
            return [JetLink(r.request.url)]

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(
            url.address,
            verify=False,
            headers={
                'User-Agent': self.user_agent,
                "Referer": f'https://{self.domains[0]}'
            },
        )
        soup = BeautifulSoup(r.text, 'html.parser')
        iframe = soup.select_one("iframe#thatframe, iframe.video").get("src")
        r_iframe = requests.get(iframe, headers= {'User-Agent': self.user_agent, "Referer": f'https://{self.domains[0]}'})
        if "wikisport" in iframe or "lovecdn" in iframe:
            new_iframe = re.findall(r'iframe.*src="(.+?)"', r_iframe.text)[0]
            r_iframe = requests.get(new_iframe, headers={"Referer": iframe})
            iframe = new_iframe
        
        if channel_key := re.findall(r'const CHANNEL_KEY\s*=\s*"(.+?)"', r_iframe.text):
            channel_key = channel_key[0]
            
            pattern = r'const\s+([A-Z_]+)\s*=\s*"([^"]+)"'
            matches = re.findall(pattern, r_iframe.text)
            result = {name: value for name, value in matches}
            referer = f'https://{urlparse(iframe).netloc}'
            channel_key = result.get('CHANNEL_KEY')
            auth_token = result.get('AUTH_TOKEN')
            session_token = auth_token
            
            headers = {
                "User-Agent": self.user_agent,
                "Referer": referer,
                "Origin": referer,
                "Connection": "Keep-Alive",
                "Authorization": f"Bearer {session_token}",
                "X-Channel-Key": channel_key,
            }
                    
            auth_url = 'https://chevy.giokko.ru/heartbeat'
            requests.get(auth_url, headers=headers, timeout=self.timeout)
            
            server_lookup_url = f"{referer}/server_lookup.js?channel_id={channel_key}"
            response = requests.get(server_lookup_url, headers=headers, timeout=self.timeout).json()
            server_key = response['server_key']
            if server_key == "top1/cdn":
                m3u8 = f"https://top1.giokko.ru/top1/cdn/{channel_key}/mono.m3u8"
            else:
                m3u8 = f"https://{server_key}new.giokko.ru/{server_key}/{channel_key}/mono.m3u8"
            return JetLink(m3u8, headers=headers, inputstream=JetInputstreamFFmpegDirect.default())
            
        elif re_eval := re.findall(r"eval\('(\\x0a.+)'\)", r_iframe.text):
            origin = f"https://{urlparse(iframe).netloc}"
            info = unhexlify(re_eval[0].replace("\\x", "")).decode("utf-8")
            stream_url = re.findall(r'(?:let|const) streamURL = "(.*)"', info)[0]
            if not stream_url:
                init_url = re.findall(r'(?:let|const) initURL = "(.*)"', info)[0]
                r_m3u8 = requests.get(init_url)
                stream_url = base64.b64decode(r_m3u8.text).decode("utf-8")
            link = JetLink(stream_url)
        elif re_init := re.findall(r"atob\('(Y29uc3.+?)'", r_iframe.text):
            player_info = base64.b64decode(re_init[0]).decode("utf-8")
            init_url = re.findall(r'const initUrl.*=.*"(.+?)";', player_info)[0]
            r_init_url = requests.get(init_url)
            stream_url = base64.b64decode(r_init_url.text).decode("utf-8")
            origin = f"https://{urlparse(iframe).netloc}"
            link = JetLink(stream_url)
        elif "vidembed" in iframe:
            soup_iframe = BeautifulSoup(r_iframe.text, "html.parser")
            aes_iv = soup_iframe.select_one("body").get("class")[0].replace("container-", "")
            parsed = urlparse(iframe)
            origin = f"https://www.{parsed.netloc}"
            stream_id = parsed.path.split("/")[-1]
            r_source = requests.post(
                f"{origin}/api/source/{stream_id}",
                params={"type": "live"},
                json={"d": f"www.{parsed.netloc}", "r": f"{origin}/stream/{stream_id}"},
                headers={"Referer": origin + "/", "Origin": origin}
            ).json()
            aes = AES.new(base64.b64decode("W8o/hbp+p0s/jftdRQXDyQ=="), AES.MODE_CBC, iv=base64.b64decode(aes_iv))
            decrypted = aes.decrypt(base64.b64decode(r_source["player"]))
            info = json.loads(unpad(decrypted, 16).decode("utf-8"))
            link = JetLink(info["source_file"])
        elif "zhdcdn" in iframe:
            iframe = re.findall(r'iframe src="(.+?)"', r_iframe.text)[0]
            iframe = iframe.replace("'+encodeURIComponent(document.referrer)+'", f"https://{self.domains[0]}/")
            r_embed = requests.get(iframe, headers={"Referer": iframe})
            auth = re.findall(r'"auth":"(.+?)"', r_embed.text)[0]
            crf = re.findall(r'id="crf__" value=\'(.+?)\'', r_embed.text)[0]
            m3u8 = base64.b64decode(crf).decode("utf-8")
            origin = f"https://{urlparse(iframe).netloc}"
            link = JetLink(m3u8, headers={"Xauth": auth, "Referer": iframe}, inputstream=JetInputstreamAdaptive.hls("|" + urlencode({"Xauth": auth, "Referer": iframe})))
        elif mo := re.findall(r'(..=\[(?:\[\d+,".+?"\],?)+])', r_iframe.text):
            origin = f"https://{urlparse(r_iframe.url).netloc}"
            var = re.findall(r"var .=(.+?)\(\)\+(.+?)\(\);", r_iframe.text)[0]
            # num = sum(map(lambda x: int(re.findall(r"function " + x + r"\(\)\{return (\d+);\}", r_iframe.text)[0]), var))
            num1 = int(re.findall(r"function " + var[0] + r"\(\)\{return (\d+);\}", r_iframe.text)[0])
            num2 = int(re.findall(r"function " + var[1] + r"\(\)\{return (\d+);\}", r_iframe.text)[0])
            num = num1 + num2
            vals = list(sorted(re.findall(r'\[(\d+),"(.+?)"\],?', mo[0]), key=lambda x: int(x[0])))
            m3u8_bytes = bytes(map(lambda x: int(re.sub(r"\D", "", base64.b64decode(x[1]).decode("utf-8"))) - num, vals))
            link = JetLink(m3u8_bytes.decode("utf-8"))
        elif f := re.findall(r'fid="(.+?)".+src=\"(.+?)\/embed\.js"', r_iframe.text):
            fid = f[0][0]
            origin = f[0][1]
            if origin.startswith("//"):
                origin = "https:" + origin
            r_iframe = requests.get(f"{origin}/embed.php", params={"player": "desktop", "live": fid}, headers={"Referer": iframe})
            arr = ast.literal_eval(re.findall(r'return\((\["h","t".+?\])', r_iframe.text)[0])
            m3u8 = "".join(arr).replace("\\", "").replace("////", "//")
            link = JetLink(m3u8)
        elif "embed.html?token=" in iframe:
            origin = f"https://{urlparse(iframe).netloc}"
            link = JetLink(iframe.replace("/embed.html", "/index.fmp4.m3u8"), headers={"Referer": iframe})
        else:
            iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(url.address, "", [], [])]
            origin = f"https://{self.domains[0]}"
            link = iframes[0]
        
        if link.headers is None:
            link.headers = dict()
        
        if "Connection" not in link.headers:
            link.headers["Connection"] = "Keep-Alive"
        if "Origin" not in link.headers:
            link.headers["Origin"] = origin
        if "Referer" not in link.headers:
            link.headers["Referer"] = origin + "/"
        link.headers["User-Agent"] = self.user_agent

        if link.inputstream is None:
            link.inputstream = JetInputstreamFFmpegDirect.default()
        
        return link
               
    def parse_header(self, header: str, time: str):
        timestamp = parser.parse(header[:header.index("-")] + " " + time)
        timestamp = timestamp.replace(year=2025)  # daddylive is dumb
        return timestamp
    
