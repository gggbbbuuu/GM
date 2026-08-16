import requests
import re
import json
import base64
import random
import time
import traceback
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse, quote

from ..models import *
from .._core import get_headers, decode_stream, find_m3u8

try:
    import xbmc
except ImportError:
    xbmc = None

try:
    import cloudscraper as _cloudscraper
    _scraper = _cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )
except Exception:
    _scraper = None

try:
    import ssl
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context

    _ctx = ssl.create_default_context()
    _ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE

    class _LowSecAdapter(HTTPAdapter):
        def init_poolmanager(self, *a, **kw):
            kw["ssl_context"] = _ctx
            super().init_poolmanager(*a, **kw)

    _tls_session = requests.Session()
    _tls_session.mount("https://", _LowSecAdapter())
    _tls_session.mount("http://", _LowSecAdapter())
except Exception:
    _tls_session = None


CATEGORY_SLUGS = {
    "mlbbox.me": ["/mlb-2024-live-streams", "/japan-npb-streams", "/baseball-streams"],
    "nhlbox.me": ["/nhl-2024-live-streams"],
    "mmabox.me": ["/ufc-streams", "/mma-streams", "/bkfc-streams", "/bellator-streams", "/wwe-streams"],
    "soccerbox.me": ["/soccer-streams"],
    "rugbybox.me": ["/rugby-streams"],
    "f1box.cc": ["/f1-streams"],
    "boxingbox.me": ["/boxing-streams"],
    "tennisonline.im": ["/tennis-streams"],
    "cricwatch.io": ["/cricket-streams"],
    "dartsstreams.me": ["/darts-streams"],
    "nflbox.sx": ["/football/nflbite", "/football/college-football"],
    "nbabox.co": ["/watch-nbabite-online", "/watch-college-basketball-online"],
}

_AD_IFRAME_PATTERNS = ("getbanner", "ad.html", "doubleclick", "googlesyndication", "adskeeper", "ad4.")
_IFRAME_BLACKLIST = (
    "chatango", "adserv", "live_chat", "ad4", "cloudfront", "image/svg",
    "getbanner.php", "/ads", "ads.", "min.js", ".jpg", ".png", "mail.ru",
    "googleusercontent",
)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _log(msg, level=2):
    if xbmc:
        xbmc.log(f"[SportsBox] {msg}", level)


class SportsBox(JetExtractor):
    def __init__(self) -> None:
        self.domains = list(CATEGORY_SLUGS.keys())
        self.name = "SportsBox"
        self.short_name = "SB"
        self.timeout = 10

    def _do_request(self, url, headers=None, timeout=None):
        if timeout is None:
            timeout = self.timeout
        if _scraper is not None:
            try:
                return _scraper.get(url, headers=headers, timeout=timeout, verify=False)
            except Exception:
                pass
        if _tls_session is not None:
            try:
                return _tls_session.get(url, headers=headers, timeout=timeout, verify=False)
            except Exception:
                pass
        return requests.get(url, headers=headers, timeout=timeout, verify=False)

    def _session_headers(self, referer=None, origin=None):
        h = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            h["Referer"] = referer
        if origin:
            h["Origin"] = origin
        return h

    def _parse_site_config(self, html):
        match = re.search(r"const\s+siteConfig\s*=\s*\{", html)
        if not match:
            return None
        start = match.end() - 1
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(html, start)
            return obj
        except (json.JSONDecodeError, ValueError):
            return None

    def _find_iframe(self, html, base_url):
        for match in re.finditer(r'<iframe\b[^>]*\bsrc=["\']([^"\']+)["\']', html, re.IGNORECASE):
            src = match.group(1)
            if any(p in src.lower() for p in _AD_IFRAME_PATTERNS):
                continue
            if any(b in src.lower() for b in _IFRAME_BLACKLIST):
                continue
            if not src.startswith("http"):
                src = urljoin(base_url, src)
            return src
        return None

    def _scan_m3u8(self, html, url):
        patterns = [
            r'source\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'source src="([^"]+\.m3u8[^"]*)"',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r"(https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                if "<" not in candidate and "%3c" not in candidate.lower():
                    if not candidate.startswith("http"):
                        candidate = urljoin(url, candidate)
                    return candidate

        b64_matches = re.findall(r'atob\(["\']((?:aHR|Ly)[^"\']+)["\']', html)
        for b64 in b64_matches:
            try:
                decoded = base64.b64decode(b64).decode("ascii", errors="ignore")
                if ".m3u8" in decoded:
                    url_match = re.search(r"(https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*)", decoded)
                    if url_match:
                        return url_match.group(1)
                    if decoded.startswith("http") and ".m3u8" in decoded:
                        return decoded
            except Exception:
                continue
        return None

    def _decode_array(self, html, url):
        match = re.search(
            r'(\["h","t","t","p",.+?\])\.\s*join\s*\(\s*["\']["\']\s*\)',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None
        try:
            char_array = json.loads(match.group(1))
            decoded = "".join(char_array)
            if decoded.startswith("//"):
                decoded = "https:" + decoded
            elif not decoded.startswith("http"):
                decoded = urljoin(url, decoded)
            return decoded
        except Exception:
            return None

    def _decode_hex_source(self, html):
        match = re.search(r'hexEncoded\s*=\s*"([0-9a-fA-F]{16,})"', html)
        if not match:
            return None
        try:
            decoded = bytes.fromhex(match.group(1)).decode("utf-8", "ignore")
            if "://" in decoded:
                return decoded
        except Exception:
            pass
        return None

    def _decode_atob(self, html):
        atob_matches = re.findall(
            r"(?:window\.)?atob\(\s*[\'\"]([A-Za-z0-9+/=]+)[\'\"]\s*\)", html
        )
        for match in atob_matches:
            try:
                decoded = base64.b64decode(match).decode("ascii", errors="ignore")
                if ".m3u8" in decoded or ".ts" in decoded:
                    url_match = re.search(
                        r"(https?://[^\s\"'<>]+(?:\.m3u8|\.ts)[^\s\"'<>]*)", decoded
                    )
                    if url_match:
                        return url_match.group(1)
                    if decoded.startswith("http"):
                        return decoded
            except Exception:
                continue
        return None

    def _follow_iframes_to_stream(self, url, base_headers, max_depth=8):
        headers = dict(base_headers)
        current_url = url
        _log(f"_follow_iframes_to_stream starting: {url}")

        for depth in range(max_depth):
            try:
                _log(f"Fetching depth {depth}: {current_url[:120]}")
                r = self._do_request(current_url, headers=headers, timeout=self.timeout)
                _log(f"Got response: status={r.status_code} final_url={r.url[:120]} html_len={len(r.text)}")
            except Exception as e:
                _log(f"iframe fetch failed at depth {depth}: {type(e).__name__}: {e}")
                break

            if r.status_code != 200:
                _log(f"iframe page returned {r.status_code} at depth {depth}")
                break

            final_url = r.url
            text = r.text

            m3u8 = self._scan_m3u8(text, final_url)
            if m3u8:
                _log(f"Found m3u8 at depth {depth}: {m3u8[:100]}")
                return m3u8, final_url, headers

            arr = self._decode_array(text, final_url)
            if arr:
                _log(f"Found char array stream at depth {depth}: {arr[:100]}")
                return arr, final_url, headers

            hex_src = self._decode_hex_source(text)
            if hex_src:
                _log(f"Found hex stream at depth {depth}: {hex_src[:100]}")
                return hex_src, final_url, headers

            atob = self._decode_atob(text)
            if atob:
                _log(f"Found atob stream at depth {depth}: {atob[:100]}")
                return atob, final_url, headers

            iframe_src = self._find_iframe(text, final_url)
            if not iframe_src or iframe_src == current_url:
                _log(f"No iframe found at depth {depth}, stopping. HTML first 300: {text[:300]}")
                break

            _log(f"Following iframe depth {depth}: {iframe_src[:120]}")
            parsed = urlparse(final_url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            headers = {
                "Referer": f"{domain}/",
                "Origin": domain,
                "User-Agent": base_headers.get("User-Agent", _USER_AGENTS[0]),
            }
            current_url = iframe_src

        return None, url, headers

    def _extract_game_vars(self, html):
        zmid_m = re.search(r'const\s+zmid\s*=\s*"([^"]+)"', html)
        pid_m = re.search(r"const\s+pid\s*=\s*(\d+)", html)
        edm_m = re.search(r'const\s+edm\s*=\s*"([^"]+)"', html)

        game_cat_m = re.search(r'gameCat\s*=\s*"([^"]+)"', html)
        game_text_m = re.search(r'gameText\s*=\s*"([^"]+)"', html)

        return {
            "zmid": zmid_m.group(1) if zmid_m else None,
            "pid": pid_m.group(1) if pid_m else None,
            "edm": edm_m.group(1) if edm_m else None,
            "gameCat": game_cat_m.group(1) if game_cat_m else None,
            "gameText": game_text_m.group(1) if game_text_m else None,
        }

    def _b64_decode(self, s):
        try:
            return base64.b64decode(s).decode("utf-8", errors="replace")
        except Exception:
            return s

    def _extract_textarea_iframe(self, html):
        encoded_iframes = re.findall(
            r"<textarea[^>]*>&lt;iframe[^>]*src=['\"]([^'\"]+)['\"]", html, re.IGNORECASE
        )
        if encoded_iframes:
            return encoded_iframes[0]
        textarea_contents = re.findall(r"<textarea[^>]*>(.*?)</textarea>", html, re.DOTALL | re.IGNORECASE)
        for tc in textarea_contents:
            decoded = tc.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"')
            m = re.search(r"<iframe[^>]*src=['\"]([^'\"]+)['\"]", decoded, re.IGNORECASE)
            if m:
                src = m.group(1)
                if "embedsports" in src or "embed" in src:
                    return src
        return None

    def _decode_embed_url_source(self, embed_html):
        byte_matches = list(re.finditer(
            r"decodeSr\(\s*\[\s*([0-9\s,]+?)\s*\]\s*\)", embed_html, re.DOTALL
        ))
        if not byte_matches:
            _log("No decodeSr byte array found in embed")
            return None

        best_url = None
        for m in byte_matches:
            try:
                raw = m.group(1)
                nums = [int(x.strip()) for x in raw.split(",") if x.strip()]
                if len(nums) < 100:
                    continue
                ascii_str = "".join(chr(b) for b in nums)
                layer1 = base64.b64decode(ascii_str).decode("ascii", errors="ignore")
                url_source = base64.b64decode(layer1).decode("utf-8", errors="replace")
                if url_source.startswith("http") and ("owledge" in url_source or "manifest" in url_source):
                    _log(f"Decoded videoSource ({len(nums)} bytes): {url_source[:120]}")
                    best_url = url_source
            except Exception as e:
                continue

        if best_url:
            return best_url

        _log("Could not decode urlSource from any byte array")
        return None

    def _decode_scode(self, embed_html):
        m = re.search(r"const\s+sCode\s*=\s*decodeSr\(\s*\[\s*([0-9\s,]+?)\s*\]\s*\)", embed_html)
        if not m:
            return ""
        try:
            nums = [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
            return "".join(chr(b) for b in nums)
        except Exception:
            return ""

    def _try_ninguno_stream(self, zmid, game_cat, game_text, pid, edm, page_url, config, embedsports_url=None):
        s = _scraper if _scraper is not None else requests.Session()
        if not _scraper:
            s.verify = False

        csrf = config.get("csrf", "") if config else ""
        csrf_ip = config.get("csrf_ip", "") if config else ""
        sec_hash = config.get("sec_hash", "") if config else ""
        sec_expires = config.get("sec_expires", "") if config else ""

        embed_html = None

        base_url = f"https://{edm}/sd0embed/{game_cat}"
        params = {
            "pid": pid or "0",
            "gacat": game_text or game_cat,
            "gatxt": game_cat,
            "v": zmid,
            "csrf": csrf,
            "csrf_ip": csrf_ip,
            "expires": sec_expires,
            "sec_hash": sec_hash,
        }

        page_domain = "/".join(page_url.split("/")[:3])
        for attempt in range(3):
            try:
                s.headers.update(self._session_headers(referer=page_url, origin=page_domain))
                _log(f"Fetching ninguno.cc embed (attempt {attempt + 1}): {base_url}")
                r = s.get(base_url, params=params, timeout=self.timeout)
                _log(f"ninguno.cc status={r.status_code} len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 1000:
                    embed_html = r.text
                    break
                if r.status_code == 403 and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
            except Exception as e:
                _log(f"ninguno.cc fetch error: {e}")
                if attempt < 2:
                    time.sleep(1)
                    continue

        if not embed_html and embedsports_url:
            _log(f"ninguno.cc unavailable, trying embedsports.me: {embedsports_url}")
            try:
                s.headers.update(self._session_headers(referer=page_url, origin=page_domain))
                r = s.get(embedsports_url, timeout=self.timeout)
                _log(f"embedsports.me status={r.status_code} len={len(r.text)}")
                if r.status_code == 200 and len(r.text) > 1000:
                    embed_html = r.text
            except Exception as e:
                _log(f"embedsports.me fetch error: {e}")

        if not embed_html:
            _log("No embed page obtained from ninguno.cc or embedsports.me")
            return None

        url_source = self._decode_embed_url_source(embed_html)
        if not url_source:
            _log("Could not decode urlSource from embed")
            return None

        strUnqId_m = re.search(r"const\s+strUnqId\s*=\s*['\"]([^'\"]+)['\"]", embed_html)
        session_id_m = re.search(r"const\s+session_id\s*=\s*['\"]([^'\"]+)['\"]", embed_html)
        playerId_m = re.search(r"const\s+playerId\s*=\s*['\"]([^'\"]+)['\"]", embed_html)
        edgeHostId_m = re.search(r"const\s+edgeHostId\s*=\s*['\"]([^'\"]+)['\"]", embed_html)
        secTokenUrl_m = re.search(r"const\s+secTokenUrl\s*=\s*bota\(['\"]([^'\"]+)['\"]\)", embed_html)
        expireTs_m = re.search(r'const\s+expireTs\s*=\s*parseInt\(["\'](\d+)["\']', embed_html)

        strUnqId = strUnqId_m.group(1) if strUnqId_m else ""
        session_id_val = session_id_m.group(1) if session_id_m else ""
        playerId = playerId_m.group(1) if playerId_m else ""
        edgeHostId = edgeHostId_m.group(1) if edgeHostId_m else ""
        secTokenUrl = self._b64_decode(secTokenUrl_m.group(1)) if secTokenUrl_m else ""
        expireTs = expireTs_m.group(1) if expireTs_m else ""

        csrfToken = ""
        csrftoken_m = re.search(r'const\s+csrftoken\s*=\s*["\']([^"\']+)["\']', embed_html)
        if csrftoken_m:
            try:
                layer1 = base64.b64decode(csrftoken_m.group(1)).decode("ascii", errors="ignore")
                csrfToken = base64.b64decode(layer1).decode("ascii", errors="ignore")
            except Exception:
                pass
        sCode = self._decode_scode(embed_html)

        _log(f"strUnqId={strUnqId[:40]} edgeHostId={edgeHostId} playerId={playerId[:20]}")
        _log(f"sCode={sCode[:20]} expireTs={expireTs} secTokenUrl={secTokenUrl}")

        device_id = playerId

        if secTokenUrl and sCode:
            auth_url = (
                f"{secTokenUrl}?scode={sCode}"
                f"&stream={strUnqId}"
                f"&expires={expireTs}"
                f"&u_id={playerId}"
                f"&session_id={session_id_val}"
                f"&host_id={edgeHostId}"
            )
            try:
                auth_headers = {
                    "User-Agent": _USER_AGENTS[0],
                    "Accept": "application/json",
                    "X-CSRF-Auth": csrfToken,
                    "Origin": f"https://{edm}",
                    "Referer": f"https://{edm}/sd0embed/{game_cat}",
                }
                _log(f"Calling auth endpoint: {secTokenUrl}")
                r_auth = s.get(auth_url, headers=auth_headers, timeout=self.timeout)
                _log(f"Auth response: status={r_auth.status_code} len={len(r_auth.text)}")

                if r_auth.status_code == 200:
                    try:
                        auth_data = r_auth.json()
                        device_id = auth_data.get("device_id", playerId)
                        _log(f"Got device_id: {device_id}")
                    except Exception as e:
                        _log(f"Auth JSON parse error: {e}, using playerId as device_id")
                else:
                    _log(f"Auth failed with {r_auth.status_code}: {r_auth.text[:300]}")
            except Exception as e:
                _log(f"Auth endpoint failed: {e}, using playerId as device_id")

        stream_url = f"{url_source}?u_id={device_id}"
        _log(f"Stream URL: {stream_url[:120]}")

        parsed = urlparse(stream_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return JetLink(
            address=stream_url,
            headers={
                "Referer": f"https://{edm}/sd0embed/{game_cat}",
                "User-Agent": _USER_AGENTS[0],
                "Origin": origin,
            },
            inputstream=JetInputstreamFFmpegDirect.default(),
        )

    def _resolve_stream_from_page(self, page_html, page_url, parent_game_cat=None):
        try:
            _log(f"_resolve_stream_from_page called for {page_url}, html len={len(page_html)}")
            base_origin = "/".join(page_url.split("/")[:3])
            domain = base_origin
            base_headers = self._session_headers(referer=f"{domain}/", origin=domain)

            _log("Trying iframe following...")
            stream_url, final_url, final_headers = self._follow_iframes_to_stream(
                page_url, base_headers
            )
            if stream_url:
                parsed = urlparse(final_url)
                origin = f"{parsed.scheme}://{parsed.netloc}"
                _log(f"Resolved via iframe following: {stream_url[:120]}")
                return JetLink(
                    address=stream_url,
                    headers={
                        "Referer": final_url,
                        "User-Agent": base_headers.get("User-Agent", _USER_AGENTS[0]),
                        "Origin": origin,
                    },
                    inputstream=JetInputstreamFFmpegDirect.default(),
                )
            _log("Iframe following returned no stream")

            vars = self._extract_game_vars(page_html)
            _log(f"vars from page: zmid={vars['zmid']} gameCat={vars['gameCat']} edm={vars['edm']} pid={vars['pid']}")

            zmid = vars["zmid"]
            game_cat = vars["gameCat"] or parent_game_cat
            game_text = vars["gameText"] or ""
            pid = vars["pid"] or "0"
            edm = vars["edm"] or "ninguno.cc"

            if not zmid:
                _log("No zmid found in page HTML")
                _log(f"Page HTML first 500 chars: {page_html[:500]}")
                return None

            if not game_cat:
                _log("No gameCat found in page or parent, trying URL path extraction")
                path_parts = page_url.rstrip("/").split("/")
                for part in reversed(path_parts):
                    if part in ("stream-1", "stream-2", "stream-3", "stream-4", "stream-5"):
                        continue
                    if len(part) <= 5 and part.isalpha():
                        game_cat = part.upper()
                        _log(f"Extracted gameCat from URL: {game_cat}")
                        break

            if game_cat:
                _log(f"Trying zmid={zmid} game_cat={game_cat} edm={edm}")

                embedsports_url = self._extract_textarea_iframe(page_html)
                if embedsports_url:
                    _log(f"Found textarea iframe: {embedsports_url}")

                config = self._parse_site_config(page_html)
                result = self._try_ninguno_stream(zmid, game_cat, game_text, pid, edm, page_url, config, embedsports_url=embedsports_url)
                if result:
                    return result
            else:
                _log("Could not determine gameCat, cannot build embed URL")

            _log(f"Page HTML first 500 chars: {page_html[:500]}")
            return None
        except Exception as e:
            _log(f"_resolve_stream_from_page EXCEPTION: {e}")
            _log(traceback.format_exc())
            return None

    def _extract_stream_from_embed(self, embed_html, embed_domain):
        if not embed_html:
            return None

        b64_match = re.search(r"const\s+videoUrl\s*=\s*'([^']+)'", embed_html)
        if b64_match:
            decoded = decode_stream(b64_match.group(1))
            if decoded and decoded != b64_match.group(1) and decoded.startswith("http"):
                return JetLink(
                    address=decoded,
                    headers={
                        "Referer": f"https://{embed_domain}/sd0embed",
                        "User-Agent": _USER_AGENTS[0],
                        "Origin": f"https://{embed_domain}",
                    },
                )

        m3u8 = find_m3u8(embed_html, f"https://{embed_domain}/sd0embed")
        if m3u8:
            return JetLink(
                address=m3u8,
                headers={
                    "Referer": f"https://{embed_domain}/sd0embed",
                    "User-Agent": _USER_AGENTS[0],
                    "Origin": f"https://{embed_domain}",
                },
            )

        return None

    def _fetch_category_games(self, domain, cat_path, progress):
        items = []
        cat_url = f"https://{domain}{cat_path}"
        try:
            headers = self._session_headers(referer=f"https://{domain}/")
            r = self._do_request(cat_url, headers=headers, timeout=self.timeout).text
        except Exception as e:
            _log(f"Failed to fetch {cat_url}: {e}")
            return items

        if self.progress_update(progress, f"{domain}: {cat_path}"):
            return items

        config = self._parse_site_config(r)
        list_id = config.get("listId") if config else None
        time_cls = config.get("timeCls") if config else None
        date_attr = config.get("dateAttr") if config else None

        soup = BeautifulSoup(r, "html.parser")
        container = None
        if list_id:
            container = soup.find("div", id=list_id)
        if not container:
            container = soup

        game_links = container.select("a.btn-secondary")
        seen_hrefs = set()

        for game in game_links:
            href = game.get("href", "")
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            title = game.get("title", "").strip()
            if not title:
                title = game.get_text(strip=True)
                for span in game.find_all("span"):
                    title = title.replace(span.get_text(strip=True), "")
                title = title.strip()
            if not title:
                continue

            game_time = None
            time_span = None
            if time_cls:
                time_span = game.find("span", class_=time_cls)
            if not time_span and date_attr:
                time_span = game.find("span", attrs={f"data-{date_attr}": True})
            if not time_span:
                time_span = game.find("span", attrs={"content": True})
            if time_span:
                content_val = time_span.get("content", "")
                if content_val:
                    try:
                        game_time = datetime.strptime(content_val, "%Y-%m-%dT%H:%M")
                    except (ValueError, TypeError):
                        pass

            full_url = f"https://{domain}{href}"
            item = JetItem(
                title=title,
                links=[JetLink(address=full_url, links=True)],
                starttime=game_time,
                league=cat_path.strip("/"),
            )
            items.append(item)

        return items

    def _get_items_for_domain(self, domain, progress):
        items = []

        cat_slugs = CATEGORY_SLUGS.get(domain)
        if not cat_slugs:
            try:
                headers = self._session_headers()
                r = self._do_request(f"https://{domain}", headers=headers, timeout=self.timeout).text
                soup = BeautifulSoup(r, "html.parser")
                cat_slugs = []
                for a in soup.select("a.btn-lg"):
                    href = a.get("href", "")
                    if href and href.startswith("/") and href not in cat_slugs:
                        cat_slugs.append(href)
            except Exception:
                cat_slugs = []

        for cat_path in cat_slugs:
            if self.progress_update(progress, f"{domain}: scanning"):
                return items
            cat_items = self._fetch_category_games(domain, cat_path, progress)
            items.extend(cat_items)

        return items

    def get_items(self, params=None, progress=None):
        items = []
        if self.progress_init(progress, items):
            return items

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                domain: executor.submit(self._get_items_for_domain, domain, progress)
                for domain in self.domains
            }
            for domain, future in futures.items():
                try:
                    result = future.result(timeout=30)
                    items.extend(result)
                except Exception:
                    pass
                self.progress_update(progress, domain)

        return items

    def get_links(self, url):
        _log(f"get_links called: {url.address}")
        links = []
        base_origin = "/".join(url.address.split("/")[:3])

        try:
            headers = self._session_headers(referer=f"{base_origin}/")
            s = requests.Session()
            s.verify = False
            r = s.get(url.address, headers=headers, timeout=self.timeout)
            page_html = r.text
        except Exception as e:
            _log(f"Failed to fetch stream page: {e}")
            return links

        soup = BeautifulSoup(page_html, "html.parser")
        config = self._parse_site_config(page_html)
        links_id = config.get("linksId") if config else None

        container = None
        if links_id:
            container = soup.find("div", id=links_id)
        if not container:
            container = soup

        btns = container.select("button[data-uri]")
        if not btns:
            btns = container.select("a[data-uri]")

        if btns:
            _log(f"Found {len(btns)} link buttons")
            parent_vars = self._extract_game_vars(page_html)
            parent_game_cat = parent_vars.get("gameCat")
            _log(f"Parent page gameCat={parent_game_cat}")
            for btn_idx, btn in enumerate(btns):
                if btn_idx > 0:
                    time.sleep(1.0)
                data_uri = btn.get("data-uri", "")
                if not data_uri:
                    continue
                link_text = btn.get_text(strip=True)
                full_url = urljoin(base_origin + "/", data_uri.lstrip("/"))
                _log(f"Resolving link: {full_url}")

                try:
                    h = self._session_headers(referer=f"{base_origin}/")
                    sub_html = s.get(full_url, headers=h, timeout=self.timeout).text
                except Exception as e:
                    _log(f"Failed to fetch sub-page: {e}")
                    links.append(JetLink(address=full_url, name=link_text or None, resolveurl=True))
                    continue

                resolved = self._resolve_stream_from_page(sub_html, full_url, parent_game_cat=parent_game_cat)
                if resolved:
                    resolved.name = link_text or None
                    links.append(resolved)
                    _log(f"Resolved link: {link_text}")
                else:
                    _log(f"Resolution failed for {link_text}, using resolveurl=True")
                    links.append(JetLink(address=full_url, name=link_text or None, resolveurl=True))

        if not links:
            _log("No link buttons found, trying direct resolve")
            resolved = self._resolve_stream_from_page(page_html, url.address)
            if resolved:
                resolved.name = "Default"
                links.append(resolved)
            else:
                links.append(JetLink(address=url.address, name="Default", resolveurl=True))

        _log(f"get_links returning {len(links)} links")
        return links

    def get_link(self, url):
        _log(f"get_link called: {url.address}")
        try:
            origin = "/".join(url.address.split("/")[:3])
            headers = self._session_headers(referer=f"{origin}/", origin=origin)
            s = requests.Session()
            s.verify = False
            r = s.get(url.address, headers=headers, timeout=self.timeout).text
        except Exception as e:
            _log(f"Failed to fetch page in get_link: {e}")
            return JetLink(url.address, inputstream=JetInputstreamFFmpegDirect.default())

        vars = self._extract_game_vars(r)
        parent_game_cat = vars.get("gameCat")

        resolved = self._resolve_stream_from_page(r, url.address, parent_game_cat=parent_game_cat)
        if resolved:
            _log("get_link resolved successfully")
            return resolved

        _log("get_link falling back to raw URL")
        return JetLink(url.address, inputstream=JetInputstreamFFmpegDirect.default())
