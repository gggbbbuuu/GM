import re, requests, base64

from ..models import *
from ..util import jsunpack
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

import re, requests, base64

from ..models import *
from ..util import jsunpack
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

def scan(html: str) -> str:
    res = None
    r = re.findall(r"source src=\"(.+?\.m3u8)\"", html)
    r_var = re.findall(r"var source.?=.?(?:\"|'|`)(.+?)(?:\"|'|`)", html)
    r2 = re.findall(r"source\s*:\s+?(?:\"|'|`)(.+?)(?:\"|'|`)", html)
    r3 = re.findall(r"(?:\"|')(http.*?\.m3u8.*?)(?:\"|')", html)
    r_b64 = re.findall(r"atob\((?:\"|')((?:aHR|Ly).+?)(?:\"|')", html)
    re_packed = re.findall(r"(eval\(function\(p,a,c,k,e,d\).+?{}\)\))", html)
    r_m3u8_url = re.findall(r'["\']?((?:https?://)?[^\s"\']+\.m3u8[^\s"\']*)["\']?', html)
    r_video_src = re.findall(r'video.*?src\s*[=:]\s*["\']([^"\']+)["\']', html, re.I)
    r_data_src = re.findall(r'data-src\s*[=:]\s*["\']([^"\']+)["\']', html, re.I)
    r_player = re.findall(r'player\.src\s*\([^)]+\{[^}]*src\s*:\s*["\']([^"\']+)["\']', html, re.I)
    r_master = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
    r_src_attr = re.findall(r'src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html, re.I)
    if len(r) > 0: res = r[0]
    elif len(r_var) > 0:
        for match in r_var:
            if ".m3u8" in match: 
                res = match
                break
    elif len(r2) > 0:
        for match in r2:
            if ".m3u8" in match: 
                res = match
                break
    elif len(r3) > 0:
        for match in r3:
            if ".m3u8" in match:
                res = match
                break
    elif len(r_b64) > 0:
        for match in r_b64:
            b64 = base64.b64decode(match).decode("ascii")
            if ".m3u8" in b64 or ".css" in b64 or ".js" in b64 or "load-playlist" in b64:
                res = b64
    elif len(re_packed) > 0:
        packed = jsunpack.unpack(re_packed[0])
        res = scan(packed)
    elif len(r_m3u8_url) > 0:
        for match in r_m3u8_url:
            if ".m3u8" in match:
                res = match
                break
    elif len(r_video_src) > 0:
        for match in r_video_src:
            if ".m3u8" in match:
                res = match
                break
    elif len(r_data_src) > 0:
        for match in r_data_src:
            if ".m3u8" in match:
                res = match
                break
    elif len(r_player) > 0:
        res = r_player[0]
    elif len(r_master) > 0:
        res = r_master[0]
    elif len(r_src_attr) > 0:
        res = r_src_attr[0]
    return res


def scan_page(url: str, html: Optional[str] = None, headers: Optional[dict] = None) -> JetLink:
    if headers is None:
        headers = {"User-Agent": user_agent}
    else:
        headers = dict(headers)
        if "User-Agent" not in headers:
            headers["User-Agent"] = user_agent
    if html is None:
        try:
            html = requests.get(url, headers=headers, timeout=10).text
        except Exception:
            return None
    
    url = url.replace("&", "_")
    res = scan(html)
    if res is None:
        video_id = re.search(r'/e/([A-Za-z0-9]+)', url)
        if video_id:
            vid = video_id.group(1)
            api_base = "https://vidara.so"
            if "vidara.to" in url:
                api_base = "https://vidara.so"
            api_stream_url = f"{api_base}/api/stream"
            try:
                api_resp = requests.post(api_stream_url, headers={**headers, "Content-Type": "application/json"}, json={"filecode": vid, "device": "desktop"}, timeout=10).text
                import json as j
                try:
                    data = j.loads(api_resp)
                    if "streaming_url" in data:
                        res = data["streaming_url"]
                except:
                    res = scan(api_resp)
            except:
                pass
    
    if res is None:
        return None
    
    if res.startswith("//"):
        res = ("https:" if url.startswith("https") else "http:") + res
    
    link = JetLink(address=res, headers={"Referer": url, "Origin": url, "User-Agent": user_agent}, inputstream=JetInputstreamFFmpegDirect.default())
    return link