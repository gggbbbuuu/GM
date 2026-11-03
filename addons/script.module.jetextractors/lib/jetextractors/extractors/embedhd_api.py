from ..models import *
from .._core import get_session
from ..util.stream_proxy import get_stream_proxy
from ..util import taifood_mint
from typing import Optional, List
import time
import xbmc
import re
from ..tools import debug_log
from datetime import datetime


def _ffmpegdirect_live() -> JetInputstreamFFmpegDirect:
    """inputstream.ffmpegdirect in stream_mode='live' (NOT the 'timeshift' default).

    indianservers.st /secure/ URLs use rotating short-lived tokens and the CDN
    403s segment fetches that stall behind the timeshift read thread (see
    ISSUE_FREEZE.md / streamed.py). Live mode keeps segment requests flowing.
    """
    return taifood_mint.ffmpegdirect_live()


_STREAMED_TV_UA = taifood_mint.STREAMED_TV_UA


class EmbedHDApi(JetExtractor):
    """RockyLive/RockyEmbed (rockylive.st) event scraper.

    Resolution (2026-10-31): the old iframe chain (rockyembed fetch.php ->
    atob taifood wrapper -> JS-computed player URL) mints SINGLE-USE short
    window tokens client-side inside an aggressively obfuscated + wasm-gated
    bundle, so replaying that URL from Kodi always 403s. The same token
    issuer exists server-side: POST https://taifood-blog.asia/fetch with an
    application/octet-stream protobuf payload (field 1 = event id, or the
    slug) and the network's `indians` API-key header returns a ChaCha20-
    Poly1305 encrypted FRESH indianservers.st /secure/ URL - the exact
    embedsports protocol implemented in util/embedsportstop.py. Mint on
    demand + re-mint via the proxy refresh callback.
    """

    def __init__(self) -> None:
        self.domains = ["rockylive.st", "www.rockylive.st", "rockyembed.st", "www.rockyembed.st"]
        self.name = "EmbedHD API"
        self.timeout = 15
        self.api_url = "https://rockylive.st/api/events.php?limit=1000"
        self.events_cache: List[dict] = []
        self.last_refresh: float = 0.0
        self._proxy = None
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    def _get_session_headers(self, referer: str = "https://rockylive.st/", origin: str = "https://rockylive.st") -> dict:
        return {
            "User-Agent": self.user_agent,
            "Referer": referer,
            "Origin": origin,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _get_proxy(self):
        if self._proxy is None:
            manifest_headers = taifood_mint.stream_headers()
            self._proxy = get_stream_proxy(
                "embedhd_api",
                manifest_headers,
                options={
                    "cache_manifest": False,
                    "proxy_absolute_urls": True,
                    # indianservers segments are WebP-wrapped MPEG-TS: ffmpeg
                    # probes the raw payload as a still `Video: webp` image
                    # and hits instant EOF. strip_png routes segments through
                    # segment_processor (_strip_png -> _strip_webp for RIFF)
                    # - the same switch streamed.py uses on this CDN.
                    "strip_png": True,
                    # indianservers.st rejects Chrome desktop UA + close-per-request
                    # segment fetches with 403. Mirror streamed.py: Samsung TV UA and
                    # reuse upstream connections + prefetch so segment requests look
                    # like a real TV player.
                    "user_agent": _STREAMED_TV_UA,
                    "upstream_keep_alive": True,
                    "prefetch_segments": True,
                    # WebP unwrap is CPU-expensive per segment; read-ahead keeps
                    # the decoder fed (same rationale as Backdoor1's tiktok path).
                    "prefetch_depth": 3,
                    "keep_alive": False,
                },
            )
        return self._proxy

    def _fetch_events(self) -> bool:
        now = time.time()
        if self.events_cache and (now - self.last_refresh) < 45:
            return True
        try:
            headers = self._get_session_headers()
            r = get_session().get(
                self.api_url,
                headers=headers,
                timeout=self.timeout,
                verify=False,
            )
            if r.status_code == 200:
                data = r.json()
                # 2026-10 API reshape: {"events":[...]} replaced {"matches":[...]}
                # and per-stream `links` were dropped in favour of `embed_url`.
                matches = data.get("events") or data.get("matches") or []
                if matches:
                    self.events_cache = matches
                    self.last_refresh = now
                    debug_log(f"[EmbedHDApi] Loaded {len(matches)} events from API", xbmc.LOGINFO)
                    return True
        except Exception as e:
            debug_log(f"[EmbedHDApi] Failed to fetch events: {e}", xbmc.LOGWARNING)
        return False

    def _get_category_label(self, category: str) -> str:
        category_map = {
            "baseball": "MLB",
            "american-football": "NFL",
            "football": "Soccer",
            "motor-sports": "Motorsport",
            "fight": "UFC/Fight",
            "combat-sports": "Boxing",
        }
        return category_map.get(category, (category or "").upper())

    def _mint_stream(self, event_ref: str) -> Optional[str]:
        """Ask the network issuer for a fresh indianservers stream URL.

        event_ref: the numeric event id (preferred) or the slug - both are
        accepted by the issuer (field 1 of the protobuf payload).
        Mint/decrypt logic lives in util/taifood_mint.py (shared with
        Embedsport2).
        """
        return taifood_mint.mint(event_ref)

    def _verify_m3u8(self, url: str) -> bool:
        return taifood_mint.verify_m3u8(url)

    def _stream_headers(self) -> dict:
        return taifood_mint.stream_headers()

    def _proxy_link(self, stream_url: str, refresh_callback: Optional[callable] = None) -> JetLink:
        proxy = self._get_proxy()
        proxy_url = proxy.get_proxy_url(stream_url, self._stream_headers(), refresh_callback=refresh_callback)
        debug_log(f"[EmbedHDApi] Proxy URL: {proxy_url}", xbmc.LOGINFO)
        return JetLink(
            address=proxy_url,
            inputstream=_ffmpegdirect_live(),
        )

    @staticmethod
    def _event_ref_from_address(address: str) -> Optional[str]:
        """Item addresses are the API's embed_url (fetch.php?full=<id>) or the
        event page URL (<slug>-<id>/); both carry the numeric id."""
        m = re.search(r'[?&]full=(\d+)', address)
        if m:
            return m.group(1)
        m = re.search(r'-(\d+)/?(?:\?.*)?$', address)
        if m:
            return m.group(1)
        m = re.search(r'/(\d+)(?:\?.*)?$', address)
        if m:
            return m.group(1)
        return None

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        if not self._fetch_events():
            return items

        for event in self.events_cache:
            title = event.get("title", "")
            if not title:
                continue

            category = event.get("league_slug") or event.get("category", "")
            league = event.get("league", "")
            start_timestamp = event.get("start_timestamp") or event.get("ts_et", 0)
            always_live = bool(event.get("always_live"))

            starttime = None
            if start_timestamp and start_timestamp > 0:
                try:
                    starttime = datetime.fromtimestamp(start_timestamp)
                except Exception:
                    pass

            # New API hands one embed_url per event (old shape had a streams
            # array); the id inside it is what the mint endpoint wants.
            address = event.get("embed_url") or event.get("event_url")
            if not address:
                continue

            link = JetLink(address=address, resolveurl=True, extractor=self.name)
            item = JetItem(
                title=title,
                links=[link],
                starttime=starttime,
                status="LIVE" if always_live else "",
                league=league or self._get_category_label(category),
            )
            items.append(item)

        debug_log(f"[EmbedHDApi] Total items: {len(items)}", xbmc.LOGINFO)
        return items

    def get_link(self, url: JetLink) -> Optional[JetLink]:
        event_ref = self._event_ref_from_address(url.address)
        if not event_ref:
            debug_log(f"[EmbedHDApi] No event id in address: {url.address}", xbmc.LOGWARNING)
            return None

        def _refresh_callback():
            # Tokens are short-window; re-mint a brand new one on refresh.
            fresh = self._mint_stream(event_ref)
            if not fresh:
                return None
            return {"url": fresh, "headers": self._stream_headers()}

        stream_url = self._mint_stream(event_ref)
        if not stream_url or not self._verify_m3u8(stream_url):
            debug_log(f"[EmbedHDApi] Failed to mint a playable stream for {event_ref}", xbmc.LOGWARNING)
            return None
        debug_log(f"[EmbedHDApi] Resolved m3u8: {stream_url[:100]}", xbmc.LOGINFO)
        return self._proxy_link(stream_url, refresh_callback=_refresh_callback)
