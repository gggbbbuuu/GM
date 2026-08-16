import requests, re, json, base64
from urllib.parse import urlencode, parse_qsl, urlparse, urlunparse
from ..models import *

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def _b64x2(value):
    if isinstance(value, str):
        value = (value + "=" * (-len(value) % 4)).encode()
    return base64.b64decode(base64.b64decode(value)).decode()

def _with_query(url, **params):
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query))
    query.update(params)
    return urlunparse(parts._replace(query=urlencode(query)))

def _find(pattern, text):
    m = re.findall(pattern, text)
    return m[0] if m else None


class Embedstream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["embedsports.me"]
        self.name = "Embedstream"
        self.resolve_only = True


    def embedstream(self, id: str, referer: str = ""):
        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT

        page_headers = {"Referer": referer, "Origin": "https://720pstream.cx"}
        r = s.get(f"https://{self.domains[0]}/" + id, headers=page_headers)
        text = r.text

        zmid = _find(r'zmid\s*=\s*"([^"]+)"', text)
        pid = _find(r'pid\s*=\s*(\d+)', text)
        edm = _find(r'edm\s*=\s*"([^"]+)"', text)
        gameText = _find(r'gameText\s*=\s*"([^"]+)"', text)
        gameCat = _find(r'gameCat\s*=\s*"([^"]+)"', text)

        site = re.search(r'siteConfig\s*=\s*(\{.*?\})\s*[,;]', text, re.DOTALL)
        if not site:
            raise Exception("siteConfig not found on embedsports.me page")
        config = json.loads(site.group(1))

        edm_host = edm.replace(".cc", ".cc").replace(".com", ".com")
        player_params = {
            "pid": pid, "gacat": gameText, "gatxt": gameCat, "v": zmid,
            "csrf": config["csrf"], "csrf_ip": config["csrf_ip"],
            "expires": config["sec_expires"], "sec_hash": config["sec_hash"],
        }
        player_url = f"https://{edm}/sd0embed/{gameCat}?{urlencode(player_params)}"

        s.headers.update({"Referer": f"https://{self.domains[0]}/", "Origin": f"https://{self.domains[0]}"})
        r2 = s.get(player_url)
        ptext = r2.text

        csrftoken_b64 = _find(r'const\s*csrftoken\s*=\s*"([^"]+)"', ptext)
        playerId = _find(r'const\s*playerId\s*=\s*"([^"]+)"', ptext)
        sCode_raw = _find(r'const\s*sCode\s*=\s*decodeSr\s*\(\s*\[([\d,\s]+)\]', ptext)
        strUnqId = _find(r'const\s*strUnqId\s*=\s*"([^"]+)"', ptext)
        session_id = _find(r'const\s*session_id\s*=\s*"([^"]+)"', ptext)
        expireTs = _find(r'const\s*expireTs\s*=\s*parseInt\s*\("([^"]+)"', ptext)
        edgeHostId = _find(r'const\s*edgeHostId\s*=\s*"([^"]+)"', ptext)
        videoSource_raw = _find(r'const\s*videoSource\s*=\s*bota\s*\(\s*decodeSr\s*\(\s*\[([\d,\s]+)\]', ptext)
        secTokenB64 = _find(r'const\s*secTokenUrl\s*=\s*bota\("([^"]+)"\)', ptext)

        csrf = _b64x2(csrftoken_b64)
        s_code = "".join(chr(int(n)) for n in sCode_raw.split(",") if n.strip())
        video_source = _b64x2(bytes(int(n) for n in videoSource_raw.split(",")))
        sec_token_url = base64.b64decode(secTokenB64).decode()

        auth_url = _with_query(f"{sec_token_url}/", scode=s_code, stream=strUnqId,
                               expires=expireTs, u_id=playerId, session_id=session_id, host_id=edgeHostId)
        auth = s.get(auth_url, headers={"X-CSRF-Auth": csrf, "Accept": "application/json"})

        device_id = playerId
        try:
            device_id = auth.json().get("device_id") or device_id
        except Exception:
            pass

        stream_url = _with_query(video_source, u_id=device_id)
        edm_origin = f"https://{edm}"
        return JetLink(
            address=stream_url,
            headers={"Referer": f"{edm_origin}/", "Origin": edm_origin, "User-Agent": USER_AGENT},
        )


    def get_link(self, url: JetLink) -> JetLink:
        referer = url.headers.get("Referer", url.address) if url.headers else url.address
        return self.embedstream(url.address.replace(f"https://{self.domains[0]}/", ""), referer)
