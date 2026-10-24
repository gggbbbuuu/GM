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

    def _resolve_embed(self, page_url: str):
        html = fetch_page(page_url, referer=f"{self.base_url}/")
        if not html:
            return None
        m = re.search(r'<iframe[^>]+src=["\'](https://embed\.st/[^"\']+)["\']', html)
        if not m:
            debug_log(f"[Volokit] No embed.st iframe on {page_url}", xbmc.LOGWARNING)
            return None
        return embedsportstop.get_embedsportstop_stream(m.group(1))

    def get_link(self, url: JetLink) -> JetLink:
        page_url = url.address if isinstance(url, JetLink) else url
        if "volokit2.fun" not in page_url:
            return None

        def _refresh_callback():
            try:
                fresh = self._resolve_embed(page_url)
            except Exception:
                fresh = None
            if not fresh:
                return None
            return {"url": fresh, "headers": dict(self.headers)}

        try:
            stream = self._resolve_embed(page_url)
        except Exception as e:
            debug_log(f"[Volokit] embedsportstop failed: {e}", xbmc.LOGWARNING)
            return None
        if not stream:
            return None
        debug_log(f"[Volokit] Resolved: {stream[:110]}", xbmc.LOGINFO)
        try:
            proxy_url = self._get_proxy().get_proxy_url(stream, self.headers, refresh_callback=_refresh_callback)
            return JetLink(proxy_url, headers=dict(self.headers), inputstream=_ffmpegdirect_live())
        except Exception as e:
            debug_log(f"[Volokit] Proxy build failed: {e}", xbmc.LOGWARNING)
            return None
