from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamAdaptive
from .._core import get_headers, find_m3u8, find_iframes, make_link
from ..tools import debug_log
import re
import time
import requests
import xbmc
from urllib.parse import urlparse, parse_qs, quote, unquote
from typing import Optional, List


def _is_valid_m3u8_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    if any(c in url for c in " \t\n\r(){}[];"):
        return False
    if url.count("://") != 1:
        return False
    parsed = urlparse(url)
    if not parsed.netloc or "." not in parsed.netloc:
        return False
    return ".m3u8" in url

class OnDemand(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["ondemand.st", "damitv.st", "messi.damitv.st"]
        self.name = "OnDemand"
        self.short_name = "OD"
        self.api_url = "https://ondemand.st/papi/api/streams"
        self.extract_url_api = "https://ondemand.st/papi/extract-url"
        self.base_url = "https://ondemand.st"
        self._cache: List[dict] = []
        self._cache_time: float = 0.0
        self._cache_duration: int = 120

    def _normalize_iframe_url(self, iframe: str) -> str:
        if not iframe:
            return iframe
        if iframe.startswith("//"):
            return "https:" + iframe
        if not iframe.startswith("http"):
            if iframe.startswith("/"):
                return f"https://messi.damitv.st{iframe}"
            return f"https://messi.damitv.st/{iframe}"
        if "damitv.st" in iframe and "messi.damitv.st" not in iframe:
            iframe = iframe.replace("damitv.st", "messi.damitv.st")
        return iframe

    def _build_resolver_url(self, iframe_url: str) -> str:
        return f"{self.base_url}/jetextractor/embed?url={quote(iframe_url, safe='')}"

    def _fetch_streams(self) -> List[dict]:
        now = time.time()
        if self._cache and (now - self._cache_time) < self._cache_duration:
            debug_log(f"[OnDemand] Using cached data", xbmc.LOGINFO)
            return self._cache

        try:
            headers = get_headers()
            resp = requests.get(self.api_url, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                debug_log(f"[OnDemand] API returned {resp.status_code}", xbmc.LOGWARNING)
                return []
            data = resp.json()
            if not data.get("success"):
                debug_log("[OnDemand] API indicated failure", xbmc.LOGWARNING)
                return []
            streams = data.get("streams", [])
            self._cache = streams
            self._cache_time = now
            debug_log(f"[OnDemand] Fetched {len(streams)} categories", xbmc.LOGINFO)
            return streams
        except Exception as e:
            debug_log(f"[OnDemand] Fetch failed: {e}", xbmc.LOGWARNING)
            return []

    def _get_category_label(self, category: str) -> str:
        category_map = {
            "football": "Soccer",
            "basketball": "NBA",
            "american-football": "NFL",
            "baseball": "MLB",
            "hockey": "NHL",
            "combat": "MMA / Boxing",
            "golf": "Golf",
            "tennis": "Tennis",
        }
        return category_map.get(category.lower(), category.upper())

    def _get_status(self, starts_at: int, ends_at: int) -> Optional[str]:
        now = time.time()
        if starts_at:
            if now < starts_at:
                return "Upcoming"
            elif ends_at and now > ends_at:
                return "Ended"
        return "LIVE"

    def _extract_stream_id(self, iframe_url: str) -> Optional[str]:
        parsed = urlparse(iframe_url)
        params = parse_qs(parsed.query)
        stream_id = params.get("id", [None])[0]
        if stream_id:
            return unquote(stream_id)
        if parsed.path.startswith("/embed/"):
            parts = parsed.path.replace("/embed/", "").split("/")
            return "/".join(parts) if parts[0] else None
        return None

    def _is_dlhd(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        sid = params.get("id", [""])[0]
        return unquote(sid).startswith("dlhd-")

    def _try_extract_api(self, stream_id: str) -> Optional[str]:
        api_endpoint = f"{self.extract_url_api}/{stream_id}"
        
        try:
            headers = get_headers(referer="https://ondemand.st/", origin="https://ondemand.st/")
            resp = requests.get(api_endpoint, headers=headers, timeout=self.timeout)
            
            if resp.status_code == 200:
                data = resp.json()
                hls_url = data.get("hlsUrl") or data.get("url") or data.get("stream")
                if hls_url and hls_url.startswith(("http://", "https://")):
                    if ".m3u8" in hls_url:
                        return hls_url
            
            elif resp.status_code == 404 or "no sources" in resp.text.lower():
                debug_log(f"[OnDemand] No sources for stream: {stream_id}", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[OnDemand] Extract API failed: {e}", xbmc.LOGWARNING)
        
        return None

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        categories = self._fetch_streams()
        if not categories:
            return items

        for category in categories:
            if not isinstance(category, dict):
                continue
            category_name = str(category.get("category", "Events")).strip()
            streams = category.get("streams", [])
            if not isinstance(streams, list):
                continue

            for stream in streams:
                if not isinstance(stream, dict):
                    continue
                name = stream.get("name", "Stream").strip()
                poster = stream.get("poster")
                iframe_url = self._normalize_iframe_url(stream.get("iframe"))
                if not iframe_url:
                    continue

                sources = stream.get("sources", [])
                if isinstance(sources, list):
                    sources = [s for s in sources if isinstance(s, dict) and not self._is_dlhd(s.get("embed", ""))]

                starts_at = stream.get("starts_at", 0)
                ends_at = stream.get("ends_at", 0)
                if not isinstance(starts_at, (int, float)):
                    starts_at = 0
                if not isinstance(ends_at, (int, float)):
                    ends_at = 0

                status = self._get_status(starts_at, ends_at)
                league = stream.get("league") or category_name
                if league:
                    league = self._get_category_label(str(league))

                title = name
                if status:
                    title = f"[{status}] {name}"

                resolver_url = self._build_resolver_url(iframe_url)
                links = [JetLink(resolver_url, links=True, name=f"Main")]

                if isinstance(sources, list):
                    for source in sources:
                        if isinstance(source, dict):
                            source_embed = self._normalize_iframe_url(source.get("embed"))
                            source_name = source.get("name", "Source")
                            if source_embed and source_embed != iframe_url:
                                source_resolver = self._build_resolver_url(source_embed)
                                links.append(
                                    JetLink(source_resolver, links=True, name=source_name)
                                )

                item = JetItem(
                    title=title,
                    league=league,
                    links=links,
                    icon=poster if poster else None,
                )
                items.append(item)

        debug_log(f"[OnDemand] Total items: {len(items)}", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        links: List[JetLink] = []
        url_address = url.address

        parsed = urlparse(url_address)
        is_resolver = "/jetextractor/embed" in url_address
        is_embed = ("damitv.st" in parsed.netloc or "messi.damitv.st" in parsed.netloc or "embedindia.st" in parsed.netloc) and ("/embed/" in parsed.path or parsed.path == "/embed")
        is_watch_page = "ondemand.st" in parsed.netloc and "/watch/" in parsed.path

        if not (is_resolver or is_embed or is_watch_page):
            return links

        if is_resolver:
            params = parse_qs(parsed.query)
            iframe_url = params.get("url", [None])[0]
        else:
            iframe_url = url_address

        if not iframe_url:
            return links

        iframe_url = self._normalize_iframe_url(iframe_url)

        try:
            stream_id = self._extract_stream_id(iframe_url)
            
            if stream_id:
                hls_url = self._try_extract_api(stream_id)
                if hls_url:
                    debug_log(f"[OnDemand] Found m3u8 via API: {hls_url[:80]}", xbmc.LOGINFO)
                    links.append(JetLink(
                        hls_url,
                        inputstream=JetInputstreamAdaptive.hls(),
                    ))
                    return links

                debug_log(f"[OnDemand] No m3u8 for stream_id={stream_id}, skipping", xbmc.LOGINFO)
                return links

            html = ""
            resp = requests.get(iframe_url, headers=get_headers(referer=iframe_url, origin=iframe_url), timeout=self.timeout, allow_redirects=True)
            if resp.status_code != 200:
                debug_log(f"[OnDemand] Embed page returned {resp.status_code}", xbmc.LOGWARNING)
                return links

            html = resp.text
            final_url = resp.url
            if ".m3u8" in final_url and _is_valid_m3u8_url(final_url):
                debug_log(f"[OnDemand] Found m3u8 via redirect: {final_url[:80]}", xbmc.LOGINFO)
                links.append(JetLink(
                    final_url,
                    inputstream=JetInputstreamAdaptive.hls(),
                ))
                return links

            m3u8_url = find_m3u8(html, final_url)
            if m3u8_url and _is_valid_m3u8_url(m3u8_url):
                debug_log(f"[OnDemand] Found m3u8 in HTML: {m3u8_url[:80]}", xbmc.LOGINFO)
                links.append(JetLink(
                    m3u8_url,
                    headers=get_headers(referer=final_url, origin=final_url),
                    inputstream=JetInputstreamAdaptive.hls(),
                ))
                return links

            iframes = find_iframes(html, final_url)
            for iframe_src in iframes[:2]:
                if "javascript:" not in iframe_src:
                    links.append(JetLink(iframe_src, resolveurl=True))

        except Exception as e:
            debug_log(f"[OnDemand] get_links failed: {e}", xbmc.LOGWARNING)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        links = self.get_links(url)
        if links:
            return links[0]
        return JetLink(url.address)