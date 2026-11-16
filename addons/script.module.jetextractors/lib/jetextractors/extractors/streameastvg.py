import re
import json
import html as html_lib
import xbmc
from ..models import *
from .._core import fetch_page, get_session
from ..tools import debug_log
from ..util.resolver import UniversalResolver
from ..util import taifood_mint
from ..util.stream_proxy import get_stream_proxy


class StreamEastVG(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streameast.vg", "www.streameast.vg", "foxiy.st"]
        self.name = "StreamEastVG"
        self.short_name = "SEVG"
        self.resolver = UniversalResolver(self.user_agent, "[StreamEastVG]")

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        try:
            html = fetch_page("https://streameast.vg/")
        except Exception:
            return items
        entries = []
        m = re.search(r'<script[^>]*>\s*(\[{"t":)', html)
        if m:
            try:
                entries, _ = json.JSONDecoder().raw_decode(html[m.start(1):])
            except Exception:
                entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path = entry.get("u") or ""
            title = entry.get("t") or ""
            if not path.startswith("/") or not title:
                continue
            when = (entry.get("d") or "").strip()
            status = "LIVE" if when.upper() == "LIVE" else (when or None)
            items.append(JetItem(
                title,
                [JetLink(f"https://streameast.vg{path}", links=True)],
                status=status,
                league=(entry.get("g") or None),
            ))
        return items

    def _feed_links(self, html: str) -> List[JetLink]:
        links = []
        for href, inner in re.findall(r'<a[^>]+href="(https://foxiy\.st/event/[^"]+)"[^>]*>(.*?)</a>', html, re.S):
            name_parts = []
            n_m = re.search(r'<span class="mbf-n">([^<]+)</span>', inner)
            q_m = re.search(r'<span class="mbf-q[^"]*">([^<]+)</span>', inner)
            x_m = re.search(r'<span class="mbf-x">(.*?)</span>', inner, re.S)
            if n_m:
                name_parts.append(n_m.group(1).strip())
            if q_m:
                name_parts.append(f"[{q_m.group(1).strip()}]")
            if x_m:
                desc = " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", x_m.group(1))).split())
                if desc:
                    name_parts.append(f"- {desc}")
            links.append(JetLink(
                href,
                name=" ".join(name_parts) or "Feed",
                resolveurl=True,
                extractor=self.name,
            ))
        return links

    def get_links(self, event_url) -> List[JetLink]:
        if isinstance(event_url, JetLink):
            event_url = event_url.address
        if "foxiy.st" in event_url:
            return [JetLink(event_url, name="Feed", resolveurl=True, extractor=self.name)]
        try:
            html = fetch_page(event_url)
        except Exception:
            return []
        return self._feed_links(html)

    def _pack_link(self, stream: str, referer_fallback: str) -> JetLink:
        referer = getattr(self.resolver, "stream_referer", None) or referer_fallback
        headers = {
            "User-Agent": self.user_agent,
            "Referer": referer,
        }
        origin = getattr(self.resolver, "stream_origin", None)
        if origin:
            headers["Origin"] = origin
        return JetLink(stream, headers=headers, inputstream=JetInputstreamFFmpegDirect.default())

    def _taifood_minted_link(self, stream_url: str, key: str) -> Optional[JetLink]:
        """Wrap an already-minted indianservers playlist in StreamProxy.

        Segments are WebP-wrapped MPEG-TS (strip_png mandatory) and the CDN
        rejects desktop UA (Samsung TV UA). Tokens are short-window: the
        refresh callback re-mints via taifood_mint.
        """
        try:
            def _refresh_callback():
                fresh = taifood_mint.mint(key)
                if not fresh:
                    return None
                return {"url": fresh, "headers": taifood_mint.stream_headers()}

            headers = taifood_mint.stream_headers()
            proxy = get_stream_proxy(
                "streameastvg",
                headers,
                options={
                    "cache_manifest": False,
                    "proxy_absolute_urls": True,
                    "strip_png": True,
                    "user_agent": taifood_mint.STREAMED_TV_UA,
                    "upstream_keep_alive": True,
                    "prefetch_segments": True,
                    "prefetch_depth": 3,
                    "keep_alive": False,
                },
            )
            proxy_url = proxy.get_proxy_url(stream_url, headers, refresh_callback=_refresh_callback)
            debug_log(f"[StreamEastVG] Taifood mint proxied for {key}: {stream_url[:100]}", xbmc.LOGINFO)
            return JetLink(
                address=proxy_url,
                headers=headers,
                inputstream=taifood_mint.ffmpegdirect_live(),
                resolveurl=False,
            )
        except Exception as e:
            debug_log(f"[StreamEastVG] Taifood proxy wrap failed: {e}", xbmc.LOGERROR)
            return None

    def _looks_like_video(self, stream_url: str, referer: str) -> bool:
        from urllib.parse import urljoin
        try:
            session = get_session()
            headers = {"User-Agent": self.user_agent, "Referer": referer}
            r = session.get(stream_url, headers=headers, timeout=12)
            if r.status_code != 200 or "#EXTM3U" not in r.text[:4000]:
                return True
            segs = [l.strip() for l in r.text.splitlines() if l.strip() and not l.startswith("#")]
            if not segs:
                return True
            base = stream_url.rsplit("/", 1)[0]
            seg = segs[0] if segs[0].startswith("http") else urljoin(base + "/", segs[0])
            head = session.head(seg, headers=headers, timeout=12)
            ctype = (head.headers.get("content-type") or "").lower()
            if ctype.startswith("image/"):
                return False
            return True
        except Exception:
            return True

    def get_link(self, url: JetLink) -> JetLink:
        target = url.address if isinstance(url, JetLink) else url
        if "streameast.vg" in urlparse(target).netloc:
            try:
                html = fetch_page(target)
            except Exception:
                return None
            candidates = []
            for href, _inner in re.findall(r'<a[^>]+href="(https://foxiy\.st/event/[^"]+)"[^>]*>(.*?)</a>', html, re.S):
                if href not in candidates:
                    candidates.append(href)
            if not candidates:
                return None
            first_good = None
            for i, candidate in enumerate(candidates):
                stream = self.resolver.resolve_url(candidate)
                if not stream:
                    continue
                taifood_key = getattr(self.resolver, "taifood_key", None)
                if taifood_key and "indianservers" in stream:
                    link = self._taifood_minted_link(stream, taifood_key)
                    if link:
                        debug_log(f"[StreamEastVG] feed {i + 1} taifood mint: {candidate}", xbmc.LOGINFO)
                        return link
                packed = self._pack_link(stream, candidate)
                if first_good is None:
                    first_good = packed
                if self._looks_like_video(stream, packed.headers.get("Referer", candidate)):
                    debug_log(f"[StreamEastVG] feed {i + 1} has video: {candidate}", xbmc.LOGINFO)
                    return packed
                debug_log(f"[StreamEastVG] feed {i + 1} is image-only slate: {candidate}", xbmc.LOGINFO)
            if first_good is None:
                return None
            debug_log("[StreamEastVG] all feeds are image-only slates (upstream not broadcasting video yet)", xbmc.LOGWARNING)
            return None

        stream = self.resolver.resolve_url(target)
        if not stream:
            return None
        taifood_key = getattr(self.resolver, "taifood_key", None)
        if taifood_key and "indianservers" in stream:
            link = self._taifood_minted_link(stream, taifood_key)
            if link:
                debug_log(f"[StreamEastVG] taifood mint direct: {target}", xbmc.LOGINFO)
                return link
        packed = self._pack_link(stream, target)
        if not self._looks_like_video(stream, packed.headers.get("Referer", target)):
            debug_log("[StreamEastVG] selected feed is image-only slate", xbmc.LOGWARNING)
            return None
        return packed
