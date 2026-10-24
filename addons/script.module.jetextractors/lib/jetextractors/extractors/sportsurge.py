import re
from ..models import *
from .._core import fetch_page
from ..icons import icons


class Sportsurge(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["isportsurge.ws", "www.isportsurge.ws"]
        self.name = "Sportsurge"
        self.short_name = "SS"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        try:
            html = fetch_page(f"https://{self.domains[0]}")
        except Exception:
            return items
        rows = re.findall(
            r'<a class="row MaclariListele[^"]*"[^>]*href="(https://isportsurge\.ws/watch/[^"]+)"[^>]*>(.*?)</a>',
            html,
            re.S,
        )
        for href, block in rows:
            alt_m = re.search(r'alt="Watch\s+([A-Za-z0-9]+):\s*([^"]+)"', block)
            if not alt_m:
                continue
            league = alt_m.group(1).upper()
            title = " ".join(alt_m.group(2).split())
            status = None
            time_m = re.search(r'<span class="time-badge[^"]*"[^>]*>\s*([^<]+?)\s*<', block)
            if time_m:
                text = " ".join(time_m.group(1).split())
                status = "LIVE" if "live" in text.lower() else text
            items.append(JetItem(
                title,
                [JetLink(href)],
                status=status,
                league=league,
                icon=icons[league.lower()] if league.lower() in icons else None,
            ))
        return items

    def _first_stream(self, watch_url: str) -> Optional[str]:
        try:
            html = fetch_page(watch_url)
        except Exception:
            return None
        m = re.search(r'<iframe[^>]+id="cx-iframe"[^>]+src="([^"]+)"', html, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'<(?:button|div|a|span)[^>]*id="stream-btn-(\d+)"', html)
        if m:
            return f"https://gooz.aapmains.net/new-stream-embed/{m.group(1)}"
        m = re.search(r'src=["\'](https://gooz\.aapmains\.net/new-stream-embed/\d+)', html)
        return m.group(1) if m else None

    def get_links(self, event_url) -> List[JetLink]:
        if isinstance(event_url, JetLink):
            event_url = event_url.address
        links = []
        try:
            html = fetch_page(event_url)
        except Exception:
            return links
        buttons = re.findall(
            r'<(?:button|div|a|span)[^>]*id="stream-btn-(\d+)"[^>]*>(.*?)</(?:button|div|a|span)>',
            html,
            re.S,
        )
        seen = set()
        for stream_id, inner in buttons:
            if stream_id in seen:
                continue
            seen.add(stream_id)
            name = " ".join(re.sub(r"<[^>]+>", " ", inner).split()) or "Stream"
            links.append(JetLink(
                f"https://gooz.aapmains.net/new-stream-embed/{stream_id}",
                name=name,
                resolveurl=True,
                extractor=self.name,
            ))
        if not links:
            m = re.search(r'<iframe[^>]+id="cx-iframe"[^>]+src="([^"]+)"', html, re.IGNORECASE)
            if m:
                links.append(JetLink(m.group(1), name="Stream", resolveurl=True, extractor=self.name))
        return links

    def get_link(self, url: JetLink) -> JetLink:
        target = url.address if isinstance(url, JetLink) else url
        if "isportsurge.ws" in urlparse(target).netloc:
            target = self._first_stream(target)
            if not target:
                return None
        if target and ("gooz.aapmains.net" in target or "new-stream-embed" in target):
            from .istream import IStreamEast
            resolved = IStreamEast().get_link(JetLink(target))
            if resolved and resolved.address and resolved.address != target:
                return resolved
            return None
        return None
