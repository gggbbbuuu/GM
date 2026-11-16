import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import xbmc

from .._core import fetch_page
from ..models import (
    JetExtractor,
    JetExtractorProgress,
    JetInputstreamFFmpegDirect,
    JetItem,
    JetLink,
)
from ..tools import debug_log
from ..util.stream_proxy import get_stream_proxy
from ..util import embedsportstop
from ..util import taifood_mint

_STREAMED_TV_UA = (
    "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) SamsungBrowser/16.0 TV Safari/537.36"
)

SPORTS = {
    "boxing": "BOXING",
    "college-football": "CFB",
    "live_tv": "TV",
    "mlb": "MLB",
    "mls": "MLS",
    "mens-college-basketball": "CBB",
    "nba": "NBA",
    "nfl": "NFL",
    "nhl": "NHL",
    "race": "RACING",
    "ufc": "UFC",
    "wnba": "WNBA",
}


def _ffmpegdirect_live() -> JetInputstreamFFmpegDirect:
    return JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live")


class Volokit(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["volokit2.fun", "www.volokit2.fun"]
        self.name = "VoloKit"
        self.short_name = "VK"
        self.base_url = "http://volokit2.fun"
        self.headers = {
            "User-Agent": _STREAMED_TV_UA,
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }
        self._proxy = None

    def _get_proxy(self):
        if self._proxy is None:
            self._proxy = get_stream_proxy(
                "volokit",
                self.headers,
                options={
                    "user_agent": _STREAMED_TV_UA,
                    "upstream_keep_alive": True,
                    "prefetch_segments": True,
                    # indianservers segments (taifood mint) are WebP-wrapped
                    # MPEG-TS; without strip_png ffmpeg probes `Video: webp`
                    # and hits instant EOF (same as embedsport2/embedhd).
                    "strip_png": True,
                    "prefetch_depth": 3,
                    "keep_alive": False,
                    "proxy_absolute_urls": True,
                },
            )
        return self._proxy

    def _gmt_time_to_local(self, hhmm: str):
        m = re.match(r"^(\d{1,2}):(\d{2})$", hhmm.strip())
        if not m:
            return None
        try:
            now = datetime.now(timezone.utc)
            cand = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
            if cand + timedelta(hours=2) < now:
                cand += timedelta(days=1)
            return cand.astimezone().replace(tzinfo=None)
        except Exception:
            return None

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        params = params or {}
        slugs = [params["league"]] if params.get("league") else list(SPORTS.keys())
        for idx, slug in enumerate(slugs):
            if progress is not None and self.progress_update(progress, f"Fetching {slug} ({idx + 1}/{len(slugs)})..."):
                return items
            try:
                html = fetch_page(f"{self.base_url}/sport/{slug}/", referer=f"{self.base_url}/schedule/")
            except Exception:
                continue
            if not html:
                continue
            league = SPORTS.get(slug, slug.upper())
            for block in re.findall(r'<tr class="vevent theevent">(.*?)</tr>', html, re.S):
                href_m = re.search(r'href="(http://volokit2\.fun/lives/[^"]+)"', block)
                title_m = re.search(r'<a class="url[^"]*"[^>]*>([^<]+)</a>', block)
                if not href_m or not title_m:
                    continue
                title = " ".join(title_m.group(1).split()).title()
                time_m = re.search(r'<span class="timegmt dtstart">\s*(\d{1,2}:\d{2})', block)
                starttime = self._gmt_time_to_local(time_m.group(1)) if time_m else None
                items.append(
                    JetItem(
                        title=title,
                        links=[JetLink(href_m.group(1), links=True)],
                        starttime=starttime,
                        league=league,
                    )
                )
        debug_log(f"[Volokit] Returning {len(items)} events", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        address = url.address if isinstance(url, JetLink) else url
        if "volokit2.fun" not in address:
            return []
        return [
            JetLink(
                address=address,
                name="Stream",
                headers={"Referer": f"{self.base_url}/"},
                resolveurl=True,
                extractor=self.name,
            )
        ]

    _IFRAME_RE = re.compile(
        r'<iframe[^>]+src=["\'](https://(?:taifood-blog\.asia/embed/|embedsports\.me/|embed\.st/)[^"\']+)["\']'
    )

    def _find_iframe(self, page_url: str) -> Optional[str]:
        html = fetch_page(page_url, referer=f"{self.base_url}/")
        if not html:
            return None
        m = self._IFRAME_RE.search(html)
        if not m:
            debug_log(f"[Volokit] No player iframe on {page_url}", xbmc.LOGWARNING)
            return None
        return m.group(1)

    def _resolve_embed(self, page_url: str, iframe: Optional[str] = None):
        """Return (stream_url, headers) for the game page's player iframe.

        2026-11: volokit iframes come in three flavours:
        - taifood-blog.asia/embed/<league>/<date>/<slug> (NBA etc.) - the
          embedsports/indianservers issuer used by Embedsport2/EmbedHDApi;
          mint key = path after /embed/ (taifood_mint.uri_name_from_iframe).
        - embedsports.me/... (CFB/CBB etc.) - resolved by Embedstream
          (handled in get_link, never reaches here).
        - embed.st/... - legacy, via embedsportstop.
        """
        if iframe is None:
            iframe = self._find_iframe(page_url)
        if not iframe:
            return None

        if "taifood-blog.asia" in iframe:
            uri_name = taifood_mint.uri_name_from_iframe(iframe)
            if not uri_name:
                debug_log(f"[Volokit] No /embed/ path in taifood URL: {iframe}", xbmc.LOGWARNING)
                return None
            stream = taifood_mint.mint(uri_name)
            if stream and not taifood_mint.verify_m3u8(stream):
                # CDN occasionally 404s a fresh token; one re-mint absorbs it
                debug_log(f"[Volokit] Mint verify failed for {uri_name}, re-minting once", xbmc.LOGWARNING)
                stream = taifood_mint.mint(uri_name)
            if stream and taifood_mint.verify_m3u8(stream):
                return stream, taifood_mint.stream_headers()
            debug_log(f"[Volokit] taifood mint failed for {uri_name}", xbmc.LOGWARNING)
            return None

        stream = embedsportstop.get_embedsportstop_stream(iframe)
        if not stream:
            return None
        return stream, dict(self.headers)

    def get_link(self, url: JetLink) -> JetLink:
        page_url = url.address if isinstance(url, JetLink) else url
        if "volokit2.fun" not in page_url:
            return None

        try:
            iframe = self._find_iframe(page_url)
        except Exception as e:
            debug_log(f"[Volokit] iframe lookup failed: {e}", xbmc.LOGWARNING)
            return None
        if not iframe:
            return None

        # embedsports.me carries its own player/auth chain + proxy registration
        if "embedsports.me" in iframe:
            from .embedstream import Embedstream
            try:
                return Embedstream().get_link(
                    JetLink(iframe, headers={"Referer": f"{self.base_url}/"})
                )
            except Exception as e:
                debug_log(f"[Volokit] embedstream failed: {e}", xbmc.LOGWARNING)
                return None

        def _refresh_callback():
            try:
                fresh = self._resolve_embed(page_url, iframe)
            except Exception:
                fresh = None
            if not fresh:
                return None
            stream, headers = fresh
            return {"url": stream, "headers": headers}

        try:
            resolved = self._resolve_embed(page_url, iframe)
        except Exception as e:
            debug_log(f"[Volokit] embed resolve failed: {e}", xbmc.LOGWARNING)
            return None
        if not resolved:
            return None
        stream, headers = resolved
        debug_log(f"[Volokit] Resolved: {stream[:110]}", xbmc.LOGINFO)
        try:
            proxy_url = self._get_proxy().get_proxy_url(stream, headers, refresh_callback=_refresh_callback)
            return JetLink(proxy_url, headers=headers, inputstream=_ffmpegdirect_live())
        except Exception as e:
            debug_log(f"[Volokit] Proxy build failed: {e}", xbmc.LOGWARNING)
            return None
