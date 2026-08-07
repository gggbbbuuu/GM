from ..models import *
import requests
import re
import json
import base64
from typing import Optional, List, Union, Tuple
import xbmc
import time
import random
import traceback
from urllib.parse import urlparse, urljoin, unquote
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from ..tools import debug_log

_tls_session = None
try:
    import ssl
    from requests.adapters import HTTPAdapter
    _ctx = ssl.create_default_context()
    _ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE
    class _LowSecAdapter(HTTPAdapter):
        def init_poolmanager(self, *a, **kw):
            kw['ssl_context'] = _ctx
            super().init_poolmanager(*a, **kw)
    _tls_session = requests.Session()
    _tls_session.mount("https://", _LowSecAdapter())
    _tls_session.mount("http://", _LowSecAdapter())
except Exception:
    _tls_session = None

_module_last_request_time = 0
_events_cache = None
_events_cache_time = 0
_EVENTS_CACHE_TTL = 300

_AD_IFRAME_PATTERNS = ("getbanner", "ad.html", "doubleclick", "googlesyndication", "adskeeper", "ad4.")
_IFRAME_BLACKLIST = ('chatango', 'adserv', 'live_chat', 'ad4', 'cloudfront', 'image/svg',
                     'getbanner.php', '/ads', 'ads.', 'min.js', '.jpg', '.png', 'mail.ru', 'googleusercontent')


class BckDr2(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["dlhd.pk", "dlhd.st"]
        self.name = "BckDr2"
        

        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]

        self.ott_agents = [
            "VLC/3.0.18 LibVLC/3.0.18",
            "TiviMate/4.7.0 (Android)",
            "iMPlayer/3.9.5 (Linux;Android 14) AndroidXMedia3/1.8.0",
            "OTT-IPTV/1.0 (Linux, Android 10; BR) XtreamPlayer/5.0"
        ]

        self.min_request_interval = 5

    def _do_request(self, method: str, url: str, headers=None, timeout: Union[int, Tuple[int, int]] = 15, **kwargs):
        if _tls_session is not None:
            try:
                return _tls_session.request(
                    method, url, headers=headers, timeout=timeout,
                    verify=False, **kwargs,
                )
            except Exception:
                pass
        return requests.request(
            method, url, headers=headers, timeout=timeout,
            verify=False, **kwargs,
        )

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        events = self._fetch_events()
        items.extend(events)

        debug_log(f"[Backdr2] Total items: {len(items)}", xbmc.LOGINFO)
        return items

    def _fetch_events(self) -> List[JetItem]:
        global _events_cache, _events_cache_time

        if _events_cache is not None and (time.time() - _events_cache_time) < _EVENTS_CACHE_TTL:
            debug_log(f"[Backdr2] Returning {len(_events_cache)} cached events", xbmc.LOGINFO)
            return list(_events_cache)

        items = []
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()

                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Origin': 'https://dlhd.pk',
                    'Referer': 'https://dlhd.pk/',
                }

                debug_log(f"[Backdr2] Fetching events from dlhd.pk (attempt {attempt + 1}/{max_retries + 1})", xbmc.LOGINFO)

                try:
                    r = self._do_request('get', "https://dlhd.pk", headers=headers, timeout=(8, 20))
                    body = r.content[:2 * 1024 * 1024]
                except Exception as e:
                    debug_log(f"[Backdr2] Events request failed: {type(e).__name__}: {str(e)[:60]}", xbmc.LOGWARNING)
                    self._update_last_request_time()
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(1, 2)
                        time.sleep(backoff)
                        continue
                    break

                self._update_last_request_time()

                if r.status_code != 200:
                    debug_log(f"[Backdr2] HTTP Error {r.status_code}", xbmc.LOGWARNING)
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(1, 2)
                        time.sleep(backoff)
                        continue
                    break

                html = body.decode('utf-8', errors='replace')
                soup = BeautifulSoup(html, 'html.parser')

                for schedule in soup.select("div#schedule > div.schedule__day"):
                    header_el = schedule.select_one("div.schedule__dayTitle")
                    header = header_el.text.strip() if header_el else "Unknown"

                    for category in schedule.select("div.schedule__category"):
                        category_el = category.select_one("div.card__meta")
                        category_name = category_el.text.strip() if category_el else header

                        for event in category.select("div.schedule__event"):
                            title_el = event.select_one("span.schedule__eventTitle")
                            title = title_el.text.strip() if title_el else ""

                            starttime_el = event.select_one("span.schedule__time")
                            starttime = starttime_el.get("data-time", "") if starttime_el else ""

                            display_title = title
                            if starttime:
                                display_title = f"{title} ({starttime})"

                            channels = event.select("div.schedule__channels > a")
                            links = []
                            for a in channels:
                                href = a.get("href", "")
                                if href:
                                    ch_name = a.get("title", "").strip()
                                    if not ch_name:
                                        ch_id = href.split("=")[-1] if "=" in href else ""
                                        ch_name = f"CH-{ch_id}" if ch_id else "Player"
                                    link = "https://dlhd.pk" + href
                                    links.append(JetLink(link, name=ch_name, links=True))

                            if links:
                                items.append(JetItem(display_title, links, league=category_name))

                debug_log(f"[BkDr2] Found {len(items)} events from dlhd.pk", xbmc.LOGINFO)

                try:
                    self._rate_limit()
                    channels_r = self._do_request('get', "https://dlhd.pk/24-7-channels.php", headers=headers, timeout=(8, 20))
                    self._update_last_request_time()
                    if channels_r.status_code == 200:
                        soup_channels = BeautifulSoup(channels_r.text, 'html.parser')
                        for channel in soup_channels.select("div.grid > a.card"):
                            href = channel.get("href", "")
                            if not href:
                                continue
                            ch_url = "https://dlhd.pk" + href if not href.startswith("http") else href
                            title_el = channel.select_one("div.card__title")
                            title = title_el.text.strip() if title_el else ""
                            if not title or "18+" in title:
                                continue
                            channel_id = ch_url.split("=")[-1] if "=" in ch_url else ""
                            items.append(JetItem(title, links=[JetLink(ch_url, name=f"{title} [CH-{channel_id}]", links=True)], league="24/7 Channels"))
                        debug_log(f"[BkDr2] Found 24/7 channels", xbmc.LOGINFO)
                except Exception as e:
                    debug_log(f"[BkDr2] Failed to fetch 24/7 channels: {e}", xbmc.LOGWARNING)

                _events_cache = list(items)
                _events_cache_time = time.time()
                break

            except Exception as e:
                debug_log(f"[BkDr2] Error fetching events: {str(e)}", xbmc.LOGERROR)
                debug_log(f"[BkDr2] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
                if attempt < max_retries:
                    backoff = (2 ** attempt) + random.uniform(1, 2)
                    time.sleep(backoff)
                else:
                    break

        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        debug_log(f"[BkDr2] get_links START: {url.address}", xbmc.LOGINFO)

        try:
            self._rate_limit()

            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://dlhd.pk',
                'Referer': 'https://dlhd.pk/',
            }

            r = self._do_request('get', url.address, headers=headers, timeout=15)
            if r.status_code != 200:
                debug_log(f"[BkDr2] Page returned status {r.status_code}", xbmc.LOGWARNING)
                return []

            soup = BeautifulSoup(r.text, 'html.parser')
            links = []

            for btn in soup.select("button.player-btn"):
                btn_url = btn.get("data-url", "")
                btn_title = btn.get_text(strip=True)
                if btn_url:
                    if btn_url.startswith('//'):
                        btn_url = 'https:' + btn_url
                    links.append(JetLink(btn_url, name=btn_title, headers={"Referer": r.url}))

            if not links:
                for a in soup.select("center > a"):
                    href = a.get("href", "")
                    if href:
                        full_url = "https://dlhd.pk" + href if not href.startswith("http") else href
                        ch_name = f"Player {len(links) + 1}"
                        links.append(JetLink(full_url, name=ch_name, headers={"Referer": r.url}))

            if not links:
                debug_log(f"[BkDr2] No player buttons found", xbmc.LOGWARNING)
                return []

            debug_log(f"[BkDr2] Found {len(links)} player links (returning for get_link)", xbmc.LOGINFO)
            return links

        except Exception as e:
            debug_log(f"[BkDr2] get_links EXCEPTION: {type(e).__name__}: {str(e)}", xbmc.LOGERROR)
            debug_log(f"[BkDr2] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
            return []

    def _resolve_stream(self, stream_url: str, base_headers: dict) -> List[JetLink]:
        """Try multiple methods to resolve a stream URL to an m3u8."""
        r, final_url, final_headers = self._follow_iframes(stream_url, base_headers)

        if r and r.status_code == 200:
            result = self._extract_stream(r.text, final_url, final_headers)
            if result:
                return result

        return []

    def _extract_stream(self, html: str, url: str, headers: dict) -> List[JetLink]:
        """Try multiple extraction methods on a page's HTML."""
        parsed = urlparse(url)
        domain = f"https://{parsed.netloc}"

        stream_url = self._scan_m3u8(html, url)
        if stream_url:
            debug_log(f"[BkDr2] Found m3u8 via scan: {stream_url[:120]}", xbmc.LOGINFO)
            return [JetLink(
                address=stream_url,
                headers={"Referer": url, "User-Agent": headers.get('User-Agent', self.user_agents[0]), "Origin": domain},
                inputstream=JetInputstreamFFmpegDirect.default(),
            )]

        stream_url = self._decode_array(html, url)
        if stream_url:
            debug_log(f"[BkDr2] Found stream via char array: {stream_url[:120]}", xbmc.LOGINFO)
            return [JetLink(
                address=stream_url,
                headers={"Referer": url, "User-Agent": headers.get('User-Agent', self.user_agents[0]), "Origin": domain},
                inputstream=JetInputstreamFFmpegDirect.default(),
            )]

        stream_url = self._decode_hex_source(html)
        if stream_url:
            debug_log(f"[BkDr2] Found stream via hex decode: {stream_url[:120]}", xbmc.LOGINFO)
            return [JetLink(
                address=stream_url,
                headers={"Referer": url, "User-Agent": headers.get('User-Agent', self.user_agents[0]), "Origin": domain},
                inputstream=JetInputstreamFFmpegDirect.default(),
            )]

        stream_url = self._decode_atob(html)
        if stream_url:
            debug_log(f"[BkDr2] Found stream via atob: {stream_url[:120]}", xbmc.LOGINFO)
            return [JetLink(
                address=stream_url,
                headers={"Referer": url, "User-Agent": headers.get('User-Agent', self.user_agents[0]), "Origin": domain},
                inputstream=JetInputstreamFFmpegDirect.default(),
            )]

        token_result = self._dl_token(html, headers, domain)
        if token_result:
            return token_result

        return []

    def _follow_iframes(self, url: str, base_headers: dict, max_depth: int = 8):
        """Follow iframes from a URL, skipping ads, returning the final page response."""
        headers = dict(base_headers)
        r = None
        current_url = url

        for depth in range(max_depth):
            try:
                r = self._do_request('get', current_url, headers=headers, timeout=15)
            except Exception as e:
                debug_log(f"[BkDr2] Failed to fetch iframe {current_url}: {e}", xbmc.LOGWARNING)
                break

            if r.status_code != 200:
                break

            m3u8 = self._scan_m3u8(r.text, current_url)
            if m3u8:
                break

            iframe_src = self._find_iframe(r.text, current_url)
            if not iframe_src or iframe_src == current_url:
                break

            debug_log(f"[BkDr2] Following iframe depth {depth}: {iframe_src[:120]}", xbmc.LOGINFO)
            parsed_current = urlparse(current_url)
            domain = f"https://{parsed_current.netloc}"
            headers = {
                "Referer": f"{domain}/",
                "Origin": domain,
                "User-Agent": base_headers.get('User-Agent', self.user_agents[0]),
            }
            current_url = iframe_src

        return r, current_url, headers

    def _find_iframe(self, html: str, base_url: str) -> Optional[str]:
        """Find the first non-ad iframe URL in the HTML."""
        for match in re.finditer(r'<iframe\b[^>]*\bsrc=["\']([^"\']+)["\']', html, re.IGNORECASE):
            src = match.group(1)
            if any(p in src.lower() for p in _AD_IFRAME_PATTERNS):
                continue
            if any(b in src.lower() for b in _IFRAME_BLACKLIST):
                continue
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            return src
        return None

    def _scan_m3u8(self, html: str, url: str) -> Optional[str]:
        """Scan HTML for m3u8 URLs using multiple patterns."""
        patterns = [
            r'source\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'source src="([^"]+\.m3u8[^"]*)"',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                if '<' not in candidate and '%3c' not in candidate.lower():
                    if not candidate.startswith('http'):
                        candidate = urljoin(url, candidate)
                    return candidate

        b64_match = re.findall(r'atob\(["\']((?:aHR|Ly)[^"\']+)["\']', html)
        for match in b64_match:
            try:
                decoded = base64.b64decode(match).decode('ascii', errors='ignore')
                if '.m3u8' in decoded:
                    url_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', decoded)
                    if url_match:
                        return url_match.group(1)
                    if decoded.startswith('http') and '.m3u8' in decoded:
                        return decoded
            except Exception:
                continue

        return None

    def _decode_array(self, html: str, url: str) -> Optional[str]:
        """Decode char array pattern like ['h','t','t','p',...].join('')"""
        match = re.search(r'(\["h","t","t","p",.+?\])\.\s*join\s*\(\s*["\']["\']\s*\)', html, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        try:
            char_array = json.loads(match.group(1))
            decoded = "".join(char_array)
            if decoded.startswith('//'):
                decoded = 'https:' + decoded
            elif not decoded.startswith('http'):
                decoded = urljoin(url, decoded)
            return decoded
        except Exception:
            return None

    def _decode_hex_source(self, html: str) -> Optional[str]:
        """Decode hexEncoded variable."""
        match = re.search(r'hexEncoded\s*=\s*"([0-9a-fA-F]{16,})"', html)
        if not match:
            return None
        try:
            decoded = bytes.fromhex(match.group(1)).decode('utf-8', 'ignore')
            if '://' in decoded:
                return decoded
        except Exception:
            pass
        return None

    def _decode_atob(self, html: str) -> Optional[str]:
        """Decode base64-encoded URLs from atob() calls."""
        atob_matches = re.findall(r'(?:window\.)?atob\(\s*[\'"]([A-Za-z0-9+/=]+)[\'"]\s*\)', html)
        for match in atob_matches:
            try:
                decoded = base64.b64decode(match).decode('ascii', errors='ignore')
                if '.m3u8' in decoded or '.ts' in decoded or 'load-playlist' in decoded:
                    url_match = re.search(r'(https?://[^\s"\'<>]+(?:\.m3u8|\.ts|\.css|\.js)[^\s"\'<>]*)', decoded)
                    if url_match:
                        return url_match.group(1)
                    if decoded.startswith('http'):
                        return decoded
            except Exception:
                continue
        return None

    def _dl_token(self, html: str, headers: dict, domain: str) -> List[JetLink]:
        """Extract stream via CHANNEL_KEY / M3U8_SERVER token method."""
        str_pattern = r'const\s+([A-Z0-9_]+)\s*=\s*([\'"])(.*?)\2'
        array_pattern = r'const\s+([A-Z0-9_]+)\s*=\s*\[(.*?)\]'
        str_matches = re.findall(str_pattern, html, re.DOTALL)
        strs = {name: value for name, _, value in str_matches}
        array_matches = re.findall(array_pattern, html, re.DOTALL)
        arrays = {name: re.findall(r'[\'"]([^\'"]+)[\'"]', value) for name, value in array_matches}

        channel_key = strs.get("CHANNEL_KEY")
        m3u8_server = strs.get("M3U8_SERVER")
        auth_token = strs.get("AUTH_TOKEN")

        if not m3u8_server:
            m3u8_servers = arrays.get("M3U8_SERVERS", [])
            if m3u8_servers:
                m3u8_server = m3u8_servers[0]

        if not channel_key or not m3u8_server:
            debug_log(f"[BkDr2] _dl_token: missing CHANNEL_KEY or M3U8_SERVER (found keys: {list(strs.keys())}, arrays: {list(arrays.keys())})", xbmc.LOGWARNING)
            return []

        req_headers = dict(headers)
        req_headers.update({
            "Connection": "Keep-Alive",
            "X-Channel-Key": channel_key,
            "Accept": "application/json"
        })
        if auth_token:
            req_headers["Authorization"] = f"Bearer {auth_token}"

        try:
            server_lookup = f"https://{m3u8_server}/server_lookup?channel_id={channel_key}"
            r = self._do_request('get', server_lookup, headers=req_headers, timeout=15)
            data = r.json()
            server_key = data["server_key"]
        except Exception as e:
            debug_log(f"[BkDr2] Server lookup failed: {e}", xbmc.LOGWARNING)
            return []

        url = f"https://{m3u8_server}/proxy/{server_key}/{channel_key}/mono.css"
        stream_headers = {
            "User-Agent": headers.get('User-Agent', self.user_agents[0]),
            "Referer": domain + "/",
            "Origin": domain
        }

        return [JetLink(
            address=url,
            headers=stream_headers,
            inputstream=JetInputstreamFFmpegDirect.default(),
        )]

    def get_link(self, url: JetLink) -> JetLink:
        debug_log(f"[BkDr2] get_link START: {url.address}", xbmc.LOGINFO)

        try:
            self._rate_limit()

            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://dlhd.pk',
                'Referer': 'https://dlhd.pk/',
            }

            stream_url = url.address
            if stream_url.startswith('//'):
                stream_url = 'https:' + stream_url

            r, final_url, final_headers = self._follow_iframes(stream_url, headers)
            if r and r.status_code == 200:
                parsed = urlparse(final_url)
                domain = f"https://{parsed.netloc}"

                stream_url_found = self._scan_m3u8(r.text, final_url)
                if stream_url_found:
                    debug_log(f"[BkDr2] Found m3u8: {stream_url_found[:120]}", xbmc.LOGINFO)
                    return JetLink(
                        address=stream_url_found,
                        headers={"Referer": final_url, "User-Agent": headers['User-Agent'], "Origin": domain},
                        inputstream=JetInputstreamFFmpegDirect.default(),
                    )

                stream_url_found = self._decode_array(r.text, final_url)
                if stream_url_found:
                    debug_log(f"[BkDr2] Found char array stream: {stream_url_found[:120]}", xbmc.LOGINFO)
                    return JetLink(
                        address=stream_url_found,
                        headers={"Referer": final_url, "User-Agent": headers['User-Agent'], "Origin": domain},
                        inputstream=JetInputstreamFFmpegDirect.default(),
                    )

                stream_url_found = self._decode_hex_source(r.text)
                if stream_url_found:
                    debug_log(f"[BkDr2] Found hex stream: {stream_url_found[:120]}", xbmc.LOGINFO)
                    return JetLink(
                        address=stream_url_found,
                        headers={"Referer": final_url, "User-Agent": headers['User-Agent'], "Origin": domain},
                        inputstream=JetInputstreamFFmpegDirect.default(),
                    )

                stream_url_found = self._decode_atob(r.text)
                if stream_url_found:
                    debug_log(f"[BkDr2] Found atob stream: {stream_url_found[:120]}", xbmc.LOGINFO)
                    return JetLink(
                        address=stream_url_found,
                        headers={"Referer": final_url, "User-Agent": headers['User-Agent'], "Origin": domain},
                        inputstream=JetInputstreamFFmpegDirect.default(),
                    )

                result = self._dl_token(r.text, headers, domain)
                if result:
                    return result[0]

            return url

        except Exception as e:
            debug_log(f"[BkDr2] Error in get_link: {str(e)}", xbmc.LOGERROR)
            debug_log(f"[BkDr2] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
            return url

    def _rate_limit(self):
        global _module_last_request_time
        elapsed = time.time() - _module_last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed + random.uniform(1.0, 3.0)
            debug_log(f"[BkDr2] Rate limiting: waiting {wait_time:.1f}s", xbmc.LOGINFO)
            time.sleep(wait_time)

    def _update_last_request_time(self):
        global _module_last_request_time
        _module_last_request_time = time.time()
