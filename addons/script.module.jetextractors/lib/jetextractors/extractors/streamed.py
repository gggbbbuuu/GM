from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamAdaptive, JetInputstreamFFmpegDirect
from typing import Optional, List
import requests
from datetime import datetime
from urllib3.util import SKIP_HEADER
from urllib.parse import urlparse, urljoin, quote, parse_qs
import xbmc
import re
from ..util.stream_proxy import get_stream_proxy
from ..util import embedsportstop


class Streamed(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamed.pk"]
        self.name = "Streamed"
        self.short_name = "STR"
        self.timeout = 10
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        )
        self.IFRAME = re.compile(r'<iframe\b[^>]*\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
        self.M3U8 = re.compile(r"['\"]([^'\"]*\.m3u8[^'\"]*)['\"]", re.IGNORECASE)

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": f"https://{self.domains[0]}",
            "Referer": f"https://{self.domains[0]}/"
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
            xbmc.log(f"[Streamed] Master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
            if "#EXTM3U" not in text:
                xbmc.log("[Streamed] Master fetch failed, retrying with Chrome/143 UA", xbmc.LOGWARNING)
                fetch_headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
                r = session.get(master_url, headers=fetch_headers, timeout=self.timeout)
                text = r.text
                xbmc.log(f"[Streamed] Retry master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
                if "#EXTM3U" not in text:
                    xbmc.log("[Streamed] Upstream did not return a valid M3U8", xbmc.LOGERROR)
                    return ""

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            variants = []
            for i, line in enumerate(lines):
                if line.upper().startswith("#EXT-X-STREAM-INF"):
                    for j in range(i + 1, len(lines)):
                        if not lines[j].startswith("#"):
                            variants.append(lines[j])
                            break
            if not variants:
                xbmc.log("[Streamed] No variants found, using master URL", xbmc.LOGINFO)
                return master_url

            xbmc.log(f"[Streamed] Found {len(variants)} variant(s): {variants}", xbmc.LOGINFO)
            if len(variants) == 1:
                return urljoin(master_url, variants[0])

            # Prefer highest quality: tiktokcdn PNG-wrapped segments are high-quality
            # real video; plain .ts segments are lower-quality fallback.
            for variant in variants:
                variant_url = urljoin(master_url, variant)
                try:
                    vr = session.get(variant_url, headers=fetch_headers, timeout=self.timeout)
                    vtext = vr.text
                    vtext_lower = vtext.lower()
                    has_tiktok = "tiktokcdn.com" in vtext_lower
                    has_ts = ".ts" in vtext_lower
                    has_png = ".png" in vtext_lower
                    xbmc.log(
                        f"[Streamed] Variant {variant_url} -> tiktok={has_tiktok}, ts={has_ts}, png={has_png}",
                        xbmc.LOGINFO,
                    )
                    if has_tiktok or (has_ts and not has_png):
                        return variant_url
                except Exception as e:
                    xbmc.log(f"[Streamed] Failed to inspect variant {variant_url}: {e}", xbmc.LOGERROR)
                    continue

            return urljoin(master_url, variants[-1])
        except Exception as e:
            xbmc.log(f"[Streamed] _select_variant error: {e}", xbmc.LOGERROR)
            return master_url

    def _resolve_url(self, session: requests.Session, real_url: str):
        """Resolve a Streamed API stream URL or external embed URL to a playable HLS URL."""
        domain = f"https://{urlparse(real_url).netloc}"
        headers = {
            "User-Agent": self.user_agent,
            "Referer": f"{domain}/",
            "Origin": domain
        }

        # embed.st / embedsports.top style embeds use a protobuf /fetch endpoint.
        if "embed.st" in real_url or "embedsports.top" in real_url or any(h in real_url for h in ("pooembed", "embedindia")):
            xbmc.log(f"[Streamed] Resolving embed via embedsportstop: {real_url}", xbmc.LOGINFO)
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
                xbmc.log(f"[Streamed] embedsportstop failed: {e}", xbmc.LOGERROR)

        # Direct Streamed API playlist endpoint (some sources return a playlist).
        if f"/api/stream/" in real_url and self.domains[0] in real_url:
            xbmc.log(f"[Streamed] Fetching API stream: {real_url}", xbmc.LOGINFO)
            try:
                response = session.get(real_url, headers=headers, timeout=self.timeout, verify=False)
                response.raise_for_status()
                text = response.text
                final_url = response.url

                if "#EXTM3U" in text:
                    xbmc.log("[Streamed] API returned direct playlist", xbmc.LOGINFO)
                    return final_url, headers

                stream_url = self._find_m3u8(text, final_url)
                if stream_url:
                    xbmc.log(f"[Streamed] Found m3u8 in API response: {stream_url}", xbmc.LOGINFO)
                    return stream_url, headers
            except Exception as e:
                xbmc.log(f"[Streamed] API stream fetch failed: {e}", xbmc.LOGERROR)

        # Generic embed page fallback.
        xbmc.log(f"[Streamed] Resolving embed page: {real_url}", xbmc.LOGINFO)
        try:
            r = session.get(real_url, headers=headers, timeout=self.timeout, verify=False)
            final_url = r.url
            text = r.text

            if "#EXTM3U" in text:
                return final_url, headers

            stream_url = self._find_m3u8(text, final_url)
            if stream_url:
                return stream_url, headers

            iframe = self._find_iframe(text, final_url)
            if iframe:
                r = session.get(iframe, headers=headers, timeout=self.timeout, verify=False)
                stream_url = self._find_m3u8(r.text, r.url)
                if stream_url:
                    return stream_url, headers
        except Exception as e:
            xbmc.log(f"[Streamed] Embed resolution failed: {e}", xbmc.LOGERROR)

        xbmc.log("[Streamed] Could not resolve stream URL", xbmc.LOGERROR)
        return "", {}

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        try:
            session = self._session()
            sports = session.get(f"https://{self.domains[0]}/api/sports", timeout=self.timeout).json()
            sports_map = {sport["id"]: sport["name"] for sport in sports}

            matches = session.get(f"https://{self.domains[0]}/api/matches/all-today/popular", timeout=self.timeout).json()
        except Exception as e:
            xbmc.log(f"[Streamed] get_items error: {e}", xbmc.LOGERROR)
            return items

        for match in matches:
            title = match["title"]
            if match["date"] != 0:
                match_time = datetime.fromtimestamp(match["date"] / 1000)
            else:
                match_time = None
            sport = sports_map.get(match["category"], "Unknown")

            # Skip Basketball matches until codec extradata issues are resolved
            # if sport.lower() in ['basketball', 'nba']:
            #     xbmc.log(f"[Streamed] Skipping Basketball match: {title}", xbmc.LOGINFO)
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
                xbmc.log(f"[Streamed] get_links error: {e}", xbmc.LOGERROR)
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
                xbmc.log(f"[Streamed] get_links watch error: {e}", xbmc.LOGERROR)
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
        xbmc.log(f"[Streamed] get_link called for: {url.address}", xbmc.LOGINFO)
        try:
            session = self._session()
            real_url = self._decode_proxy(url.address)
            if not real_url:
                xbmc.log("[Streamed] Empty real_url from proxy, aborting", xbmc.LOGERROR)
                return JetLink(url.address, inputstream=JetInputstreamFFmpegDirect.default())

            xbmc.log(f"[Streamed] Resolved proxy to: {real_url}", xbmc.LOGINFO)

            stream_url, headers = self._resolve_url(session, real_url)
            if not stream_url:
                xbmc.log("[Streamed] Could not resolve stream URL", xbmc.LOGERROR)
                return JetLink(real_url, inputstream=JetInputstreamFFmpegDirect.default())

            xbmc.log(f"[Streamed] Resolved stream URL: {stream_url}", xbmc.LOGINFO)
            xbmc.log(
                f"[Streamed] Stream path hints: rtmp={'/rtmp/' in stream_url}, "
                f"tiktok={'tiktokcdn' in stream_url.lower()}, "
                f"png_ext={stream_url.lower().endswith('.png')}",
                xbmc.LOGINFO,
            )

            stream_url = self._select_variant(session, stream_url, headers)
            if not stream_url:
                xbmc.log("[Streamed] Could not select a valid variant", xbmc.LOGERROR)
                return JetLink(real_url, inputstream=JetInputstreamFFmpegDirect.default())
            xbmc.log(f"[Streamed] Selected variant URL: {stream_url}", xbmc.LOGINFO)

            proxy = get_stream_proxy(
                "streamed",
                headers,
                options={"strip_png": True, "manifest_png_to_ts": True},
            )
            proxy_url = proxy.get_proxy_url(stream_url, headers)
            xbmc.log(f"[Streamed] Proxy URL: {proxy_url}", xbmc.LOGINFO)

            return JetLink(
                proxy_url,
                headers=headers,
                inputstream=JetInputstreamFFmpegDirect.default()
            )
        except Exception as e:
            xbmc.log(f"[Streamed] get_link error: {e}", xbmc.LOGERROR)
            import traceback
            xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
            try:
                return JetLink(url.address, inputstream=JetInputstreamFFmpegDirect.default())
            except Exception:
                return None
