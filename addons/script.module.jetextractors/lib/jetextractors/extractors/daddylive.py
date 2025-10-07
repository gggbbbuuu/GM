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
        self.domains = ["daddylivestream.com", "dlhd.dad"]
        self.name = "Daddylive"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        unique_hrefs = set()
        count = 0
        duplicate_count = 0
        
        sched_headers = {
            "Origin": f'https://{self.domains[0]}', 
            "Referer": f'https://{self.domains[0]}/', 
            "User-Agent": STD_AGENT
        }
        
        sched_url = f"https://{self.domains[0]}/schedule/schedule-generated.php" 
        r: dict = requests.get(sched_url, headers=sched_headers).json()         
        
        for header, events in r.items():
            for event_type, event_list in events.items():
                for event in event_list:
                    title = event.get("event", "")
                    starttime = event.get("time", "")
                    league = event_type.replace("</span>", "")
                    channels = event.get("channels", [])
                    if isinstance(channels, dict):
                        channels = channels.values()
                    
                    try:
                        utc_time = self.parse_header(header, starttime) - timedelta(hours=1)
                    except Exception as _:
                        try:
                            utc_time = datetime.now().replace(hour=int(starttime.split(":")[0]), minute=int(starttime.split(":")[1])) - timedelta(hours=1)
                        except Exception as _:
                            utc_time = datetime.now()
                    
                    items.append(JetItem(
                        title,
                        [JetLink(f"https://{self.domains[0]}/stream/stream-{channel['channel_id']}.php", name=f'{channel["channel_name"]} [CH-{channel["channel_id"]}]', links=True) for channel in channels],
                        league=league,
                        starttime=utc_time,
                    ))
        
        if self.progress_update(progress):
            return items

        r_channels = requests.get(f"https://{self.domains[0]}/24-7-channels.php", timeout=self.timeout)
        soup_channels = BeautifulSoup(r_channels.text, "html.parser")
        A_link = soup_channels.find_all('a')[:2]
        b_link = soup_channels.find_all('a')[8:]
        links = A_link + b_link
        for link in links:
            title = link.text
            if '18+' in title:
                del title
                continue
            
            href = f"https://{self.domains[0]}{link['href']}"
            if href in unique_hrefs:
                duplicate_count += 1
                continue
            unique_hrefs.add(href)
            count += 1
            items.append(JetItem(title, links=[JetLink(href, links=True)], league="[COLORorange]24/7"))
        
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
                "Accept-Encoding": SKIP_HEADER,
                "Referer": url.headers.get("Referer", SKIP_HEADER) if url.headers is not None else SKIP_HEADER
            },
        )
        soup = BeautifulSoup(r.text, 'html.parser')
        iframe = soup.select_one("iframe#thatframe, iframe.video").get("src")
        r_iframe = requests.get(iframe, headers={"Referer": url.address})
        if "wikisport" in iframe or "lovecdn" in iframe:
            new_iframe = re.findall(r'iframe.*src="(.+?)"', r_iframe.text)[0]
            r_iframe = requests.get(new_iframe, headers={"Referer": iframe})
            iframe = new_iframe
        
        if bundle_b64 := re.findall(r'const XKZK\s*=\s*"(.+?)"', r_iframe.text):
            channel_key = re.findall(r'const CHANNEL_KEY\s*=\s*"(.+?)"', r_iframe.text)[0]
            bundle: dict = json.loads(base64.b64decode(bundle_b64[0]).decode("utf-8"))
            for key, value in bundle.items():
                bundle[key] = base64.b64decode(value).decode("utf-8")
            _r_auth = requests.get(
                f'{bundle["b_host"]}auth.php',
                params={"channel_id": channel_key, "ts": bundle["b_ts"], "rnd": bundle["b_rnd"], "sig": bundle["b_sig"]}, 
                headers={"Referer": iframe, "Accept-Encoding": SKIP_HEADER}
            )

            origin = f'https://{urlparse(iframe).netloc}'
            server_lookup_url = f"{origin}/server_lookup.php?channel_id={channel_key}"
            r_key = requests.get(server_lookup_url, headers={"Origin": origin, "Accept-Encoding": SKIP_HEADER}).json()
            server_key = r_key["server_key"]
            if server_key == "top1/cdn":
                m3u8 = f'https://top1.newkso.ru/{server_key}/{channel_key}/mono.m3u8' 
            else:
                m3u8 = f'https://{server_key}new.newkso.ru/{server_key}/{channel_key}/mono.m3u8'
            link = JetLink(m3u8)
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
               
    def parse_header(self, header, time):
        timestamp = parser.parse(header[:header.index("-")] + " " + time)
        timestamp = timestamp.replace(year=2025)  # daddylive is dumb
        return timestamp