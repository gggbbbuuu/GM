from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamAdaptive, JetInputstreamFFmpegDirect
from typing import Optional, List
import requests
from requests.adapters import HTTPAdapter
from datetime import datetime, date, timedelta
from urllib3.util import SKIP_HEADER
from urllib3.util.ssl_ import create_urllib3_context
from urllib.parse import urlparse, urljoin, quote, parse_qs
import ssl
import xbmc
import re
from ..util.stream_proxy import get_stream_proxy
from ..util import embedsportstop
from ..tools import debug_log

try:
    import cloudscraper
    _HAS_CLOUDSCRAPER = True
except Exception:
    _HAS_CLOUDSCRAPER = False


def _ffmpegdirect_live() -> JetInputstreamFFmpegDirect:
    """inputstream.ffmpegdirect in stream_mode='live' (NOT the 'timeshift' default).

    ISSUE_FREEZE.md iteration 6/7: stream_mode='timeshift' (what
    JetInputstreamFFmpegDirect.default() uses) makes the player-close path
    block ~20s inside the addon teardown ("Dll Destroyed - Inputstream FFmpeg
    Direct" exactly 20.0s late on 19:54 and 20:04 logs): the timeshift
    machinery keeps FFmpeg's read thread pulling segments into the disk
    buffer, and close waits for the full network timeout. ULAMA — which does
    NOT freeze — uses the same inputstream.ffmpegdirect but with
    stream_mode='live' (its timeshift setting defaults to off). Trade-off:
    no pause/rewind on live streams.
    """
    return JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live")


class _StreamedAdapter(HTTPAdapter):
    """HTTPAdapter with a browser-like TLS fingerprint."""

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ssl_version=ssl.PROTOCOL_TLS)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = False
        context.set_ciphers(
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256:"
            "ECDHE-ECDSA-AES128-GCM-SHA256:"
            "ECDHE-RSA-AES128-GCM-SHA256:"
            "ECDHE-ECDSA-AES256-GCM-SHA384:"
            "ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-CHACHA20-POLY1305"
        )
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


class Streamed(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamed.pk"]
        self.name = "Streamed"
        self.short_name = "STR"
        self.timeout = 10
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        self.IFRAME = re.compile(r'<iframe\b[^>]*\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
        self.M3U8 = re.compile(r"['\"]([^'\"]*\.m3u8[^'\"]*)['\"]", re.IGNORECASE)

    def _session(self) -> requests.Session:
        if _HAS_CLOUDSCRAPER:
            try:
                s = cloudscraper.create_scraper()
                debug_log("[Streamed] Using cloudscraper session", xbmc.LOGINFO)
                return s
            except Exception as e:
                debug_log(f"[Streamed] cloudscraper init failed: {e}, falling back", xbmc.LOGWARNING)

        s = requests.Session()
        s.verify = False
        s.mount("https://", _StreamedAdapter())
        s.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": f"https://{self.domains[0]}",
            "Referer": f"https://{self.domains[0]}/",
            "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive"
        })
        return s

    def _proxy_url(self, real_url: str, name: str) -> str:
        """Wrap an arbitrary stream/embed URL so JetExtractors routes it back here."""
        return f"https://{self.domains[0]}/jetextractor/streamed?url={quote(real_url, safe='')}&name={quote(name, safe='')}"

    def _decode_proxy(self, address: str) -> str:
        parsed = urlparse(address)
        if parsed.path == "/jetextractor/streamed" and parsed.netloc in self.domains:
            return parse_qs(parsed.query).get("url", [""])[0]
        return address

    def _find_iframe(self, html: str, url: str) -> str:
        for match in self.IFRAME.finditer(html):
            src = match.group(1)
            if any(p in src.lower() for p in ("getbanner", "ad.html", "doubleclick", "googlesyndication")):
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif not src.startswith("http"):
                src = urljoin(url, src)
            return src
        return ""

    def _find_m3u8(self, html: str, url: str) -> str:
        match = self.M3U8.search(html)
        if not match:
            return ""
        src = match.group(1)
        if src.startswith("//"):
            src = "https:" + src
        elif not src.startswith("http"):
            src = urljoin(url, src)
        return src

    def _select_variant(self, session: requests.Session, master_url: str, headers: dict) -> str:
        """Fetch master playlist and pick a real HLS variant, preferring high-quality tiktokcdn."""
        try:
            fetch_headers = dict(headers)
            fetch_headers.setdefault("Accept", "*/*")
            fetch_headers.setdefault("Connection", "close")
            fetch_headers.setdefault("Icy-MetaData", "1")

            r = session.get(master_url, headers=fetch_headers, timeout=self.timeout)
            text = r.text
            debug_log(f"[Streamed] Master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
            if "#EXTM3U" not in text:
                debug_log("[Streamed] Master fetch failed, retrying with Chrome/143 UA", xbmc.LOGWARNING)
                fetch_headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
                r = session.get(master_url, headers=fetch_headers, timeout=self.timeout)
                text = r.text
                debug_log(f"[Streamed] Retry master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
                if "#EXTM3U" not in text:
                    debug_log("[Streamed] Upstream did not return a valid M3U8", xbmc.LOGERROR)
                    return ""

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            variants = []
            for i, line in enumerate(lines):
                if line.upper().startswith("#EXT-X-STREAM-INF"):
                    bw = 0
                    m = re.search(r'BANDWIDTH=(\d+)', line)
                    if m:
                        bw = int(m.group(1))
                    for j in range(i + 1, len(lines)):
                        if not lines[j].startswith("#"):
                            variants.append((bw, lines[j]))
                            break
            if not variants:
                debug_log("[Streamed] No variants found, using master URL", xbmc.LOGINFO)
                return master_url

            debug_log(f"[Streamed] Found {len(variants)} variant(s): {variants}", xbmc.LOGINFO)
            if len(variants) == 1:
                return urljoin(master_url, variants[0][1])

            # Always prefer the highest bandwidth variant
            variants.sort(key=lambda x: x[0], reverse=True)
            return urljoin(master_url, variants[0][1])
        except Exception as e:
            debug_log(f"[Streamed] _select_variant error: {e}", xbmc.LOGERROR)
            return master_url

    def _resolve_url(self, session: requests.Session, real_url: str):
        """Resolve a Streamed API stream URL or external embed URL to a playable HLS URL."""
        domain = f"https://{urlparse(real_url).netloc}"
        headers = {
            "User-Agent": self.user_agent,
            "Referer": f"{domain}/",
            "Origin": domain,
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }

        # embed.st / embedsports.top style embeds use a protobuf /fetch endpoint.
        if "embed.st" in real_url or "embedsports.top" in real_url or any(h in real_url for h in ("pooembed", "embedindia")):
            debug_log(f"[Streamed] Resolving embed via embedsportstop: {real_url}", xbmc.LOGINFO)
            try:
                stream_url = embedsportstop.get_embedsportstop_stream(real_url)
                if stream_url:
                    # Playback must carry the embed domain as Referer/Origin.
                    embed_domain = f"https://{urlparse(real_url).netloc}"
                    playback_headers = {
                        "User-Agent": self.user_agent,
                        "Referer": f"{embed_domain}/",
                        "Origin": embed_domain
                    }
                    return stream_url, playback_headers
            except Exception as e:
                debug_log(f"[Streamed] embedsportstop failed: {e}", xbmc.LOGERROR)

        # Direct Streamed API playlist endpoint (some sources return a playlist).
        if f"/api/stream/" in real_url and self.domains[0] in real_url:
            debug_log(f"[Streamed] Fetching API stream: {real_url}", xbmc.LOGINFO)
            try:
                response = session.get(real_url, headers=headers, timeout=self.timeout, verify=False)
                response.raise_for_status()
                text = response.text
                final_url = response.url

                final_domain = f"https://{urlparse(final_url).netloc}"
                final_headers = dict(headers)
                final_headers["Referer"] = f"{final_domain}/"
                final_headers["Origin"] = final_domain

                if "#EXTM3U" in text:
                    debug_log("[Streamed] API returned direct playlist", xbmc.LOGINFO)
                    return final_url, final_headers

                stream_url = self._find_m3u8(text, final_url)
                if stream_url:
                    debug_log(f"[Streamed] Found m3u8 in API response: {stream_url}", xbmc.LOGINFO)
                    return stream_url, final_headers
            except Exception as e:
                debug_log(f"[Streamed] API stream fetch failed: {e}", xbmc.LOGERROR)

        # Generic embed page fallback.
        debug_log(f"[Streamed] Resolving embed page: {real_url}", xbmc.LOGINFO)
        try:
            r = session.get(real_url, headers=headers, timeout=self.timeout, verify=False)
            final_url = r.url
            text = r.text

            final_domain = f"https://{urlparse(final_url).netloc}"
            final_headers = dict(headers)
            final_headers["Referer"] = f"{final_domain}/"
            final_headers["Origin"] = final_domain

            if "#EXTM3U" in text:
                return final_url, final_headers

            stream_url = self._find_m3u8(text, final_url)
            if stream_url:
                return stream_url, final_headers

            iframe = self._find_iframe(text, final_url)
            if iframe:
                iframe_domain = f"https://{urlparse(iframe).netloc}"
                iframe_headers = dict(headers)
                iframe_headers["Referer"] = f"{iframe_domain}/"
                iframe_headers["Origin"] = iframe_domain
                r = session.get(iframe, headers=iframe_headers, timeout=self.timeout, verify=False)
                stream_url = self._find_m3u8(r.text, r.url)
                if stream_url:
                    return stream_url, iframe_headers
        except Exception as e:
            debug_log(f"[Streamed] Embed resolution failed: {e}", xbmc.LOGERROR)

        debug_log("[Streamed] Could not resolve stream URL", xbmc.LOGERROR)
        return "", {}

    def _safe_json(self, session: requests.Session, url: str) -> Optional[dict]:
        """Fetch URL and parse JSON, logging response details on failure."""
        try:
            r = session.get(url, timeout=self.timeout)
            text = r.text
            debug_log(f"[Streamed] {url} -> status {r.status_code}, len {len(text)}, url {r.url}", xbmc.LOGINFO)
            if not text.strip():
                debug_log("[Streamed] Empty response body", xbmc.LOGWARNING)
                return None
            try:
                return r.json()
            except Exception as e:
                debug_log(f"[Streamed] JSON parse error: {e}", xbmc.LOGERROR)
                debug_log(f"[Streamed] Response body:\n{text[:2000]}", xbmc.LOGERROR)
                return None
        except Exception as e:
            debug_log(f"[Streamed] Request failed for {url}: {e}", xbmc.LOGERROR)
            return None

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        session = self._session()
        sports_url = f"https://{self.domains[0]}/api/sports"
        matches_url = f"https://{self.domains[0]}/api/matches/all-today/popular"

        sports = self._safe_json(session, sports_url)
        if sports is None:
            return items
        sports_map = {sport["id"]: sport["name"] for sport in sports}

        matches = self._safe_json(session, matches_url)
        if matches is None:
            return items

        now = datetime.now()
        cutoff = now + timedelta(hours=12)
        for match in matches:
            title = match["title"]
            if match["date"] != 0:
                match_time = datetime.fromtimestamp(match["date"] / 1000)
                if match_time > cutoff:
                    continue
            else:
                match_time = None
            sport = sports_map.get(match["category"], "Unknown")

            # Skip Basketball matches until codec extradata issues are resolved
            # if sport.lower() in ['basketball', 'nba']:
            #     debug_log(f"[Streamed] Skipping Basketball match: {title}", xbmc.LOGINFO)
            #     continue

            links = [
                JetLink(
                    self._proxy_url(
                        f"https://{self.domains[0]}/api/stream/{source['source']}/{source['id']}",
                        source["source"].capitalize()
                    ),
                    links=True,
                    name=source["source"].capitalize()
                )
                for source in match["sources"]
            ]
            items.append(JetItem(title, links, match_time, league=sport))
        return items

    def get_links(self, url):
        session = self._session()
        real_url = self._decode_proxy(url.address)
        if not real_url:
            return []

        if "/api/" in real_url:
            try:
                streams = session.get(real_url, headers={"Accept-Encoding": SKIP_HEADER}, timeout=self.timeout).json()
            except Exception as e:
                debug_log(f"[Streamed] get_links error: {e}", xbmc.LOGERROR)
                return []

            if "/embed/" in real_url:
                links = [
                    JetLink(
                        self._proxy_url(
                            f"https://{self.domains[0]}/api/stream/{stream['source']}/{stream['id']}",
                            stream["source"]
                        ),
                        links=True,
                        name=stream["source"]
                    )
                    for stream in streams
                ]
            else:
                links = [
                    JetLink(
                        self._proxy_url(
                            stream["embedUrl"],
                            f"Stream {stream['streamNo']} [{stream['language'] or 'N/A'}, {'HD' if stream['hd'] else 'SD'}, {stream['viewers']} viewers]"
                        ),
                        name=f"Stream {stream['streamNo']} [{stream['language'] or 'N/A'}, {'HD' if stream['hd'] else 'SD'}, {stream['viewers']} viewers]"
                    )
                    for stream in streams
                ]
            return links

        elif "/watch/" in real_url:
            match_id = real_url.split("/")[-1]
            try:
                matches = session.get(f"https://{self.domains[0]}/api/matches/all", timeout=self.timeout).json()
            except Exception as e:
                debug_log(f"[Streamed] get_links watch error: {e}", xbmc.LOGERROR)
                return []
            for match in matches:
                if match["id"] != match_id:
                    continue
                links = [
                    JetLink(
                        self._proxy_url(
                            f"https://{self.domains[0]}/api/stream/{source['source']}/{source['id']}",
                            source["source"].capitalize()
                        ),
                        links=True,
                        name=source["source"].capitalize()
                    )
                    for source in match["sources"]
                ]
                return links

        return []

    def get_link(self, url):
        debug_log(f"[Streamed] get_link called for: {url.address}", xbmc.LOGINFO)
        try:
            session = self._session()
            real_url = self._decode_proxy(url.address)
            if not real_url:
                debug_log("[Streamed] Empty real_url from proxy, aborting", xbmc.LOGERROR)
                return JetLink(url.address, inputstream=_ffmpegdirect_live())

            debug_log(f"[Streamed] Resolved proxy to: {real_url}", xbmc.LOGINFO)

            stream_url, headers = self._resolve_url(session, real_url)
            if not stream_url:
                debug_log("[Streamed] Could not resolve stream URL", xbmc.LOGERROR)
                return JetLink(real_url, inputstream=_ffmpegdirect_live())

            debug_log(f"[Streamed] Resolved stream URL: {stream_url}", xbmc.LOGINFO)
            debug_log(
                f"[Streamed] Stream path hints: rtmp={'/rtmp/' in stream_url}, "
                f"tiktok={'tiktokcdn' in stream_url.lower()}, "
                f"png_ext={stream_url.lower().endswith('.png')}",
                xbmc.LOGINFO,
            )

            stream_url = self._select_variant(session, stream_url, headers)
            if not stream_url:
                debug_log("[Streamed] Could not select a valid variant", xbmc.LOGERROR)
                return JetLink(real_url, inputstream=_ffmpegdirect_live())
            debug_log(f"[Streamed] Selected variant URL: {stream_url}", xbmc.LOGINFO)

            proxy = get_stream_proxy(
                "streamed",
                headers,
                options={
                    "strip_png": True,
                    "manifest_png_to_ts": True,
                    "user_agent": "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/16.0 TV Safari/537.36",
                    
                    # ISSUE_BUFFERING.md: reuse upstream CDN connections and
                    # prefetch the next segment in the background to counter
                    # the depth-1 serialized segment pipeline (stalls).
                    
                    "upstream_keep_alive": True,
                    "prefetch_segments": True,
                    
                   # ISSUE_FREEZE.md (ffmpegdirect variant): do NOT keep the
                    # manifest connection alive. With keep-alive, the idle
                    # persistent connection is the one FFmpeg's inputstream.
                    # ffmpegdirect teardown blocks ~20s on at player close
                    # ("Dll Destroyed - Inputstream FFmpeg Direct" 20s late).
                    # With keep_alive=False the connection closes after each
                    # response, so teardown is instant (same as roxiestreams).
                    
                    "keep_alive": False,
                },
            )
            proxy_url = proxy.get_proxy_url(stream_url, headers)
            debug_log(f"[Streamed] Proxy URL: {proxy_url}", xbmc.LOGINFO)

            return JetLink(
                proxy_url,
                headers=headers,
                inputstream=_ffmpegdirect_live()
            )
        except Exception as e:
            debug_log(f"[Streamed] get_link error: {e}", xbmc.LOGERROR)
            import traceback
            debug_log(traceback.format_exc(), xbmc.LOGERROR)
            try:
                return JetLink(url.address, inputstream=_ffmpegdirect_live())
            except Exception:
                return None
