import re, json, base64
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from ..models import *
from .._core import get_session
from ..util.stream_proxy import build_proxy_url

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def _b64d(value: str) -> str:
    return base64.b64decode(value + "=" * (-len(value) % 4)).decode()

def _find(pattern, text):
    m = re.findall(pattern, text)
    return m[0] if m else None


class Embedstream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["embedsports.me"]
        self.name = "Embedstream"
        self.resolve_only = True


    def embedstream(self, id: str, referer: str = ""):
        link = self._resolve(id, referer)
        if link is None:
            return None
        return self._register_proxy(link, id, referer)

    def _register_proxy(self, link: JetLink, id: str, referer: str) -> JetLink:
        headers = dict(link.headers or {})
        if not link.inputstream:
            link.inputstream = JetInputstreamFFmpegDirect.default()

        def refresh():
            try:
                fresh = self._resolve(id, referer)
            except Exception:
                fresh = None
            if fresh and fresh.address and fresh.address.startswith("http"):
                return {"url": fresh.address, "headers": dict(fresh.headers or headers)}
            return None

        proxy_url = build_proxy_url(
            "embedstream",
            link.address,
            headers,
            options={
                "proxy_absolute_urls": True,
                "keep_alive": False,
                "upstream_keep_alive": True,
                "prefetch_segments": True,
                "prefetch_depth": 3,
            },
            per_request_headers=headers,
            refresh_callback=refresh,
        )
        link.address = proxy_url
        return link

    def _resolve(self, id: str, referer: str = ""):
        s = get_session()
        s.headers["User-Agent"] = USER_AGENT

        page_url = f"https://{self.domains[0]}/{id}"
        page_headers = {"Referer": referer or page_url, "Origin": "https://720pstream.cx"}
        r = s.get(page_url, headers=page_headers)
        text = r.text

        site = re.search(r"const siteConfig = (\{.*?\});", text, re.DOTALL)
        if not site:
            raise Exception("siteConfig not found on embedsports.me page")
        cfg = json.loads(site.group(1))

        loader = re.search(r"<script[^>]+embed\.min\.js[^>]*>", text)
        if not loader:
            raise Exception("player loader script not found on embedsports.me page")
        attrs = dict(re.findall(r'(data-[a-z]+)="([^"]+)"', loader.group(0)))
        pldm = attrs.get("data-pldm")
        gc = attrs.get("data-gc", "sports")
        if not pldm or not attrs.get("data-pid") or not attrs.get("data-play"):
            raise Exception("player data attributes missing on embedsports.me page")

        player_params = {
            "pid": attrs["data-pid"],
            "v": attrs["data-play"],
            "player": attrs.get("data-player", "jw"),
            "csrf": cfg["csrf"],
            "csrf_ip": cfg["csrf_ip"],
            "expires": cfg["sec_expires"],
            "sec_hash": cfg["sec_hash"],
        }
        player_url = f"https://{pldm}/sd0embed/{gc}?{urlencode(player_params)}"
        s.headers.update({"Referer": page_url, "Origin": f"https://{self.domains[0]}"})
        r2 = s.get(player_url)
        ptext = r2.text
        if r2.status_code != 200:
            raise Exception(f"player page returned {r2.status_code}")

        f_nums = _find(r"F=d\(String\.fromCharCode\(\.\.\.\[([\d,]+)\]\)\)", ptext)
        if not f_nums:
            raise Exception("stream template (F) not found in player page")
        playlist_template = _b64d("".join(chr(int(n)) for n in f_nums.split(",")))
        host_id = urlparse(playlist_template).hostname.split(".")[0]

        blk = re.search(r'l=_\(\{scode:"([^"]+)",ts:(\w+),session_id:"([^"]+)",device_id:(\w+)\}', ptext)
        y = _find(r'y=parseInt\((?:")?(\d+)', ptext)
        r_init = _find(r'let R="([^"]+)"', ptext)
        csrf_blob = _find(r'\[m\]:d\("([^"]+)"\)', ptext)
        auth_base = _find(r'v=d\("([A-Za-z0-9+/=]+)"\)', ptext)
        stream_id = _find(r'k="([^"]+)"', ptext)
        if not (blk and y and r_init and csrf_blob and auth_base and stream_id):
            raise Exception("player auth constants missing in player page")

        auth_url = "{}?{}".format(
            _b64d(auth_base),
            urlencode({
                "scode": blk.group(1),
                "stream": stream_id,
                "expires": y,
                "u_id": r_init,
                "session_id": blk.group(3),
                "host_id": host_id,
            }),
        )
        auth = s.get(
            auth_url,
            headers={
                "Accept": "application/json",
                "X-CSRF-Auth": _b64d(csrf_blob),
                "Referer": player_url,
                "Origin": f"https://{pldm}",
            },
        )
        if auth.status_code != 200:
            raise Exception(f"auth endpoint returned {auth.status_code}")
        try:
            data = auth.json()
        except Exception:
            raise Exception("auth endpoint returned invalid json")
        if not data.get("success"):
            raise Exception("auth endpoint reported failure")
        device_id = data.get("device_id") or r_init

        parsed = urlparse(playlist_template)
        query = dict(parse_qsl(parsed.query))
        query["u_id"] = device_id
        stream_url = urlunparse(parsed._replace(query=urlencode(query)))

        return JetLink(
            address=stream_url,
            headers={
                "Referer": player_url,
                "Origin": f"https://{pldm}",
                "User-Agent": USER_AGENT,
            },
        )


    def get_link(self, url: JetLink) -> JetLink:
        referer = url.headers.get("Referer", url.address) if url.headers else url.address
        try:
            return self.embedstream(url.address.replace(f"https://{self.domains[0]}/", ""), referer)
        except Exception:
            return None
