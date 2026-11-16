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

        # 2026-11 player redesign: SecKeyPlayerConfig carries urlSource +
        # a seckyes.cc auth handshake (old fromCharCode template chain is gone).
        if "SecKeyPlayerConfig" in ptext:
            return self._resolve_seckey(ptext, player_url, pldm, s)

        # Playlist template: new pages use f=s(String.fromCharCode(...[...]))
        # (s=atob); old pages F=d(...). Decode char codes as base64 -> URL.        playlist_template = None
        for nums in re.findall(
            r'=\s*[ds]\(String\.fromCharCode\(\.\.\.\[([\d,]+)\]\)\)', ptext
        ):
            try:
                cand = _b64d("".join(chr(int(n)) for n in nums.split(",")))
            except Exception:
                continue
            if cand.startswith("http"):
                playlist_template = cand
                break
        if not playlist_template:
            raise Exception("stream template (F) not found in player page")

        # Auth object: {scode:"...",ts:<var>,session_id:"...",device_id:<var>}
        # new: c({scode:...}); old: l=_({scode:...}).
        blk = re.search(
            r'\{scode:"([^"]+)",ts:(\w+),session_id:"([^"]+)",device_id:(\w+)\}', ptext
        )
        if not blk:
            raise Exception("player auth constants missing in player page")
        scode, ts_var, session_id, dev_var = blk.group(1), blk.group(2), blk.group(3), blk.group(4)

        # expires: <ts_var>=parseInt(<digits>)
        ts_m = re.search(
            rf'\b{re.escape(ts_var)}\s*=\s*parseInt\(\s*["\']?(\d+)', ptext
        )
        if not ts_m:
            raise Exception("player expires (ts) missing in player page")
        expires = int(ts_m.group(1))

        # device init (u_id): new config anchors v=parseInt(0,10)||0,y="stl...";
        # old style let R="...". Device ids look like stl<xxx>-<hex>.
        device_init = None
        m = re.search(
            r'v=parseInt\(\s*\d+\s*,\s*10\s*\)\s*\|\|\s*0\s*,\s*([A-Za-z_$][\w$]*)="([^"]+)"',
            ptext,
        )
        if m and m.group(1) == dev_var:
            device_init = m.group(2)
        if not device_init:
            m = re.search(rf'\blet\s+{re.escape(dev_var)}\s*=\s*"([^"]+)"', ptext)
            if m:
                device_init = m.group(1)
        if not device_init:
            cands = re.findall(
                rf'(?<![A-Za-z0-9_$]){re.escape(dev_var)}\s*=\s*"([^"]*)"', ptext
            )
            device_init = next(
                (c for c in cands if re.match(r"stl[a-z]*-[A-Za-z0-9]+", c)),
                cands[-1] if cands else None,
            )
        if not device_init:
            raise Exception("player device id (u_id) missing in player page")

        # Auth base URL: new r=s("<b64>"); old v=d("<b64>").
        auth_base = None
        for pat in (
            r'\br\s*=\s*[ds]\("([A-Za-z0-9+/=]+)"\)',
            r'\bv\s*=\s*[ds]\("([A-Za-z0-9+/=]+)"\)',
        ):
            m = re.search(pat, ptext)
            if not m:
                continue
            try:
                cand = _b64d(m.group(1))
            except Exception:
                continue
            if cand.startswith("http"):
                auth_base = cand
                break
        if not auth_base:
            raise Exception("player auth endpoint missing in player page")

        # stream key: new uses var referenced by stream=${encodeURIComponent(<var>)};
        # old k="<...>".
        stream_id = None
        m = re.search(r'stream=\$\{encodeURIComponent\((\w+)\)\}', ptext)
        if m:
            vm = re.search(
                rf'(?<![A-Za-z0-9_$]){re.escape(m.group(1))}\s*=\s*"([^"]+)"', ptext
            )
            if vm:
                stream_id = vm.group(1)
        if not stream_id:
            stream_id = _find(r'\bk\s*=\s*"([^"]+)"', ptext)
        if not stream_id:
            raise Exception("player stream id missing in player page")

        # X-CSRF-Auth: new "X-CSRF-Auth":s("<b64>"); old [m]:d("<b64>").
        csrf_raw = None
        for pat in (
            r'"X-CSRF-Auth"\s*:\s*[ds]\("([A-Za-z0-9+/=]+)"\)',
            r'\[m\]\s*:\s*[ds]\("([A-Za-z0-9+/=]+)"\)',
        ):
            m = re.search(pat, ptext)
            if m:
                csrf_raw = m.group(1)
                break
        if not csrf_raw:
            raise Exception("player CSRF token missing in player page")
        csrf_blob = _b64d(csrf_raw)

        host_id = urlparse(playlist_template).hostname.split(".")[0]

        auth_url = "{}?{}".format(
            auth_base,
            urlencode({
                "scode": scode,
                "stream": stream_id,
                "expires": expires,
                "u_id": device_init,
                "session_id": session_id,
                "host_id": host_id,
            }),
        )
        auth = s.get(
            auth_url,
            headers={
                "Accept": "application/json",
                "X-CSRF-Auth": csrf_blob,
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
        device_id = data.get("device_id") or device_init
        if not device_id:
            raise Exception("auth endpoint reported failure")

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


    def _resolve_seckey(self, ptext: str, player_url: str, pldm: str, s):
        """2026-11 embedsports.me player: SecKeyPlayerConfig + seckyes.cc auth.

        The player page embeds window.SecKeyPlayerConfig[<id>]={urlSource,
        csrf_token(b64), secTokenUrl(b64 -> auth base), sCode, strUnqId,
        expireTs, session_id, device_id, edgeHostId}. Playback requires:
        1. GET <auth_base>/?scode&stream&expires&u_id&session_id&host_id with
           headers Accept: application/json, X-CSRF-Auth: b64decode(csrf_token),
           Origin: https://<pldm>, Referer: <player_url> (Origin/Referer are
           mandatory - nginx 400s without them). Response carries a fresh
           device_id.
        2. urlSource with u_id replaced by that device_id -> master playlist.
        Manifest/variant/segments/AES key all require Origin+Referer (412/400
        bare); X-CSRF-Auth only gates the auth call itself.
        """
        m = re.search(r'window\.SecKeyPlayerConfig\["[^"]+"\]\s*=\s*(\{.*?\})\s*;', ptext, re.DOTALL)
        if not m:
            raise Exception("SecKeyPlayerConfig missing in player page")
        cfg = json.loads(m.group(1))
        url_source = cfg.get("urlSource")
        csrf_token = cfg.get("csrf_token")
        sec_token_url = cfg.get("secTokenUrl")
        if not url_source or not csrf_token or not sec_token_url:
            raise Exception("SecKeyPlayerConfig incomplete (urlSource/csrf/secTokenUrl)")

        origin = f"https://{pldm}"
        csrf_auth = _b64d(csrf_token)
        auth_base = _b64d(sec_token_url).rstrip("/")
        auth_qs = urlencode({
            "scode": cfg.get("sCode", ""),
            "stream": cfg.get("strUnqId", ""),
            "expires": cfg.get("expireTs", ""),
            "u_id": cfg.get("device_id", ""),
            "session_id": cfg.get("session_id", ""),
            "host_id": cfg.get("edgeHostId", ""),
        })
        auth_headers = {
            "Accept": "application/json",
            "X-CSRF-Auth": csrf_auth,
            "Origin": origin,
            "Referer": player_url,
        }
        auth = s.get(f"{auth_base}/?{auth_qs}", headers=auth_headers, timeout=10)
        if auth.status_code != 200:
            raise Exception(f"seckey auth returned {auth.status_code}")
        try:
            data = auth.json()
        except Exception:
            raise Exception("seckey auth returned invalid json")
        device_id = data.get("device_id") or cfg.get("device_id")
        if not device_id:
            raise Exception("seckey auth reported no device_id")

        parsed = urlparse(url_source.replace("\\/", "/"))
        query = dict(parse_qsl(parsed.query))
        query["u_id"] = device_id
        stream_url = urlunparse(parsed._replace(query=urlencode(query)))

        return JetLink(
            address=stream_url,
            headers={
                "Referer": player_url,
                "Origin": origin,
                "User-Agent": USER_AGENT,
            },
        )

    def get_link(self, url: JetLink) -> JetLink:
        referer = url.headers.get("Referer", url.address) if url.headers else url.address
        try:
            return self.embedstream(url.address.replace(f"https://{self.domains[0]}/", ""), referer)
        except Exception:
            return None
