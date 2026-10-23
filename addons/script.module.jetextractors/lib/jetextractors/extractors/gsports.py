import base64
import re
import zlib
from typing import List, Optional
from urllib.parse import urljoin

import xbmc

from .._core import fetch_page, fetch_json, find_m3u8, get_session
from ..models import (
    JetExtractor,
    JetExtractorProgress,
    JetInputstreamFFmpegDirect,
    JetItem,
    JetLink,
)
from ..tools import debug_log
from ..util.stream_proxy import get_stream_proxy

# Event pages ship a two-layer obfuscated Clappr player:
#   1. Inline IIFE: !function(d,k){new Function(Array.from(atob(d),
#      c=>String.fromCharCode(c.charCodeAt(0)^k)).join(''))()}("<b64>",23);
#      The blob is base64, then each byte XORed with the IIFE's numeric key.
#      The decoded JS fetches a relative binary path (e.g. '?v=font.woff2').
#   2. The fetched bytes are XORed with a repeating string key (e.g. 'gs99'),
#      then raw-deflate (DecompressionStream 'deflate-raw') compressed. After
#      inflate, the player JS carries `source: 'https://.../folderN/M'` (m3u8).
_IIFE_BLOB = re.compile(
    r'function\s*\(\s*d\s*,\s*k\s*\)\s*\{\s*new Function\(\s*Array\.from\(\s*atob\(\s*d\s*\)'
    r'.*?\}\s*\(\s*"([A-Za-z0-9+/=]+)"\s*,\s*(\d+)\s*\)',
    re.S,
)
_INNER_FETCH = re.compile(r"fetch\(\s*['\"]([^'\"]+)['\"]")
_INNER_XOR_KEY = re.compile(r"[,\s;{(]k\s*=\s*['\"]([^'\"]+)['\"]")
_PLAYER_SOURCE = re.compile(r"source\s*:\s*['\"](https?://[^'\"]+)['\"]")


def _xor_bytes(data: bytes, key) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _decode_outer_blob(html: str) -> Optional[str]:
    """Decode the inline IIFE payload (base64 + numeric XOR) to inner JS."""
    m = _IIFE_BLOB.search(html)
    if not m:
        return None
    try:
        raw = base64.b64decode(m.group(1))
        key = int(m.group(2))
        return bytes(b ^ key for b in raw).decode("utf-8", "replace")
    except Exception as e:
        debug_log(f"[GSports] Outer blob decode failed: {e}", xbmc.LOGWARNING)
        return None


def _decode_layer2(content: bytes, xor_key: str) -> Optional[str]:
    """XOR with the repeating string key, then raw-deflate inflate."""
    if not xor_key or not content:
        return None
    data = _xor_bytes(content, xor_key.encode("utf-8"))
    for wbits in (-zlib.MAX_WBITS, zlib.MAX_WBITS):
        try:
            return zlib.decompress(data, wbits).decode("utf-8", "replace")
        except zlib.error:
            continue
    return None


def _extract_player_source(js: str) -> Optional[str]:
    m = _PLAYER_SOURCE.search(js)
    return m.group(1) if m else None


class GSports(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["gsports.lat", "www.gsports.lat"]
        self.name = "GSports"
        self.short_name = "GS"
        self.base_url = "https://gsports.lat"
        self.api_url = f"{self.base_url}/?api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}/",
        }
        self._proxy = None

    def _get_proxy(self):
        if self._proxy is None:
            self._proxy = get_stream_proxy(
                "gsports",
                self.headers,
                options={
                    "strip_png": False,
                    "prefetch_segments": True,
                    "upstream_keep_alive": True,
                    "keep_alive": False,
                },
            )
        return self._proxy

    def _make_proxy_link(self, stream: str) -> JetLink:
        try:
            proxy_url = self._get_proxy().get_proxy_url(stream, self.headers)
            return JetLink(
                proxy_url,
                headers=self.headers,
                inputstream=JetInputstreamFFmpegDirect.default(),
            )
        except Exception as e:
            debug_log(f"[GSports] Proxy build failed for {stream}: {e}", xbmc.LOGWARNING)
            return JetLink(stream, headers=self.headers, inputstream=JetInputstreamFFmpegDirect.default())

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        if progress:
            self.progress_update(progress, "Fetching schedule...")

        data = fetch_json(self.api_url, referer=self.base_url)
        if not isinstance(data, dict):
            debug_log("[GSports] No API response", xbmc.LOGWARNING)
            return items

        seen = set()
        for event in data.get("events") or []:
            if not isinstance(event, dict):
                continue
            title = (event.get("title") or "").strip()
            url = (event.get("url") or "").strip()
            if not title or not url or url in seen:
                continue
            seen.add(url)
            items.append(
                JetItem(
                    title=title,
                    links=[JetLink(url, links=True)],
                    league=(event.get("category") or "").strip() or None,
                )
            )

        debug_log(f"[GSports] Returning {len(items)} events", xbmc.LOGINFO)
        return items

    def _resolve_stream(self, html: str, page_url: str) -> Optional[str]:
        """Two-layer decode chain; falls back to a plain m3u8 in the page."""
        inner_js = _decode_outer_blob(html)
        if inner_js:
            path_m = _INNER_FETCH.search(inner_js)
            key_m = _INNER_XOR_KEY.search(inner_js)
            if path_m and key_m:
                payload_url = urljoin(page_url, path_m.group(1))
                try:
                    session = get_session(referer=page_url)
                    r = session.get(payload_url, timeout=10)
                    if r.status_code == 200:
                        player_js = _decode_layer2(r.content, key_m.group(1))
                        if player_js:
                            source = _extract_player_source(player_js)
                            if source:
                                return source
                    else:
                        debug_log(
                            f"[GSports] Layer2 HTTP {r.status_code}: {payload_url}",
                            xbmc.LOGWARNING,
                        )
                except Exception as e:
                    debug_log(f"[GSports] Layer2 fetch failed {payload_url}: {e}", xbmc.LOGWARNING)
            else:
                debug_log("[GSports] Inner fetch path/key not found", xbmc.LOGWARNING)

        return find_m3u8(html, page_url)

    def get_links(self, url: JetLink) -> List[JetLink]:
        links: List[JetLink] = []
        try:
            html = fetch_page(url.address, referer=self.base_url)
            if not html:
                return links
            stream = self._resolve_stream(html, url.address)
            if stream:
                links.append(self._make_proxy_link(stream))
            else:
                debug_log(f"[GSports] No stream found on {url.address}", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[GSports] Error getting links for {url.address}: {e}", xbmc.LOGERROR)
        return links
