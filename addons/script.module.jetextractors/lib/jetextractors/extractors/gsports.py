import re
import xbmc
from typing import List, Optional

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


def _ffmpegdirect_live() -> JetInputstreamFFmpegDirect:
    return JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live")


class GSports(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["gstream24.fun", "www.gstream24.fun"]
        self.name = "GSports"
        self.short_name = "GS"
        self.base_url = "https://gstream24.fun"
        self.headers = {
            "User-Agent": _STREAMED_TV_UA,
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }
        self._proxy = None

    def _get_proxy(self):
        if self._proxy is None:
            self._proxy = get_stream_proxy(
                "gsports",
                self.headers,
                options={
                    # strmd.st (lbN secure ingest playlists) rejects Chrome desktop UA
                    # and close-per-request segment fetches — mirror embedhd_api/streamed:
                    # Samsung TV UA + reused upstream connections + segment prefetch.
                    "user_agent": _STREAMED_TV_UA,
                    "upstream_keep_alive": True,
                    "prefetch_segments": True,
                    "keep_alive": False,
                    "proxy_absolute_urls": True,
                },
            )
        return self._proxy

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        if progress:
            self.progress_update(progress, "Fetching schedule...")

        html = fetch_page(f"{self.base_url}/all-matches/", referer=f"{self.base_url}/")
        if not html:
            debug_log("[GSports] No schedule page", xbmc.LOGWARNING)
            return items

        for block in re.findall(r"<tr>(.*?)</tr>", html, re.S):
            href_m = re.search(r'href="(https?://gstream24\.fun/games/[^"]+/)"', block)
            if not href_m:
                continue
            cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", block, re.S)]
            if len(cells) < 6:
                continue
            status_cell = next((c for c in cells if c.lower() in ("live", "ended", "upcoming", "in progress")), "")
            if status_cell.lower() == "ended":
                continue
            title = next(
                (c for c in cells if c and " " in c and not re.match(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$", c)
                 and not re.match(r"^\d{1,2}:\d{2}\s*[ap]m$", c, re.I) and len(c.split()) >= 2 and c not in ("Live", "Upcoming")),
                None,
            )
            if not title:
                continue
            league_m = re.search(r'alt="([^"]+)"', block)
            league = league_m.group(1).strip() if league_m else None
            status = "LIVE" if status_cell.lower() == "live" else (status_cell or None)
            items.append(
                JetItem(
                    title=title,
                    links=[JetLink(href_m.group(1), links=True)],
                    status=status,
                    league=league.upper() if league else None,
                )
            )

        debug_log(f"[GSports] Returning {len(items)} events", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        address = url.address if isinstance(url, JetLink) else url
        if "gstream24.fun" not in address:
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
            return None, None
        m = re.search(r'<iframe[^>]+src=["\'](https://embed\.st/[^"\']+)["\']', html)
        if not m:
            debug_log(f"[GSports] No embed.st iframe on {page_url}", xbmc.LOGWARNING)
            return None, None
        embed_url = m.group(1)
        stream = embedsportstop.get_embedsportstop_stream(embed_url)
        if not stream:
            return None, None
        return stream, embed_url

    def get_link(self, url: JetLink) -> JetLink:
        page_url = url.address if isinstance(url, JetLink) else url
        if "gstream24.fun" not in page_url:
            return None

        def _refresh_callback():
            try:
                stream, embed_url = self._resolve_embed(page_url)
            except Exception:
                stream, embed_url = None, None
            if not stream:
                return None
            return {"url": stream, "headers": dict(self.headers)}

        try:
            stream, embed_url = self._resolve_embed(page_url)
        except Exception as e:
            debug_log(f"[GSports] embedsportstop failed: {e}", xbmc.LOGWARNING)
            return None
        if not stream:
            return None
        debug_log(f"[GSports] Resolved: {stream[:110]}", xbmc.LOGINFO)
        try:
            proxy_url = self._get_proxy().get_proxy_url(stream, self.headers, refresh_callback=_refresh_callback)
            return JetLink(proxy_url, headers=dict(self.headers), inputstream=_ffmpegdirect_live())
        except Exception as e:
            debug_log(f"[GSports] Proxy build failed: {e}", xbmc.LOGWARNING)
            return None
