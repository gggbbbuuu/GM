import re
from urllib.parse import urlparse, unquote, quote, parse_qs
from ..models import *
from .._core import fetch_page
from ..util.resolver import UniversalResolver
from bs4 import BeautifulSoup

SCHEDULE_URL = "https://onhockey.tv/schedule_table.php"
SITE_REFERER = "https://onhockey.tv/"


class OnHockey(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["onhockey.tv", "www.onhockey.tv"]
        self.name = "OnHockey"
        self.short_name = "OHK"
        self.resolver = UniversalResolver(self.user_agent, "[OnHockey]")

    def _fetch_schedule(self) -> str:
        try:
            return fetch_page(SCHEDULE_URL, referer=SITE_REFERER) or ""
        except Exception:
            return ""

    def _source_url(self, href: str) -> str:
        if href.startswith("np_stream400.php"):
            m = re.search(r"channel=([^&]+)", href)
            if not m:
                return None
            channel = unquote(m.group(1))
            if channel.startswith("//"):
                return "https:" + channel
            if channel.startswith("http"):
                return channel
            return None
        if href.startswith("np_vk.php"):
            m = re.search(r"channel=([^&]+)", href)
            if not m:
                return None
            value = unquote(m.group(1))
            parts = dict(p.split("=", 1) for p in value.split("&") if "=" in p)
            if "oid" in parts and "id" in parts:
                return f"https://vkvideo.ru/video_ext.php?oid={parts['oid']}&id={parts['id']}"
            return None
        return None

    def _parse_rows(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        league = None
        for tr in soup.find_all("tr"):
            classes = tr.get("class") or []
            if "game" in classes:
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                title_td = tds[1]
                sources = []
                for a in title_td.select(".gamelinks a[href]"):
                    src = self._source_url(a["href"])
                    if not src:
                        continue
                    if "embed.st/" in src:
                        continue
                    if any(src == s["url"] for s in sources):
                        continue
                    label = " ".join(a.get_text(" ").split())
                    channel = (a.get("title") or "").strip()
                    name = " - ".join(x for x in (channel, label) if x)
                    sources.append({"url": src, "name": name or "Stream"})
                for gl in title_td.find_all(class_="gamelinks"):
                    gl.extract()
                title = " ".join(title_td.get_text(" ").split())
                if not title:
                    continue
                yield league, title, sources
            else:
                b = tr.find("b")
                if b:
                    text = b.get_text(strip=True)
                    if text and len(text) <= 30:
                        league = text

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        html = self._fetch_schedule()
        if not html:
            return items
        for league, title, sources in self._parse_rows(html):
            status = f"{len(sources)} links" if sources else "SCHEDULED"
            items.append(JetItem(
                title,
                [JetLink(f"https://onhockey.tv/schedule_table.php#{quote(title, safe='')}", links=True)],
                status=status,
                league=league,
            ))
        return items

    def _find_sources(self, wanted_title: str, html: str) -> list:
        wanted = " ".join(wanted_title.split())
        first = []
        contains = []
        for league, title, sources in self._parse_rows(html):
            if not sources:
                continue
            if not first:
                first = sources
            if not wanted:
                continue
            if title == wanted:
                return sources
            if wanted in title or title in wanted:
                contains = sources
        if wanted:
            return contains
        return first

    def get_links(self, event_url) -> List[JetLink]:
        if isinstance(event_url, JetLink):
            event_url = event_url.address
        fragment = unquote(urlparse(event_url).fragment or "")
        html = self._fetch_schedule()
        if not html:
            return []
        sources = self._find_sources(fragment, html)
        return [
            JetLink(
                s["url"],
                name=s["name"],
                headers={"Referer": SITE_REFERER},
                resolveurl=True,
                extractor=self.name,
            )
            for s in sources
        ]

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

    def get_link(self, url: JetLink) -> JetLink:
        target = url.address if isinstance(url, JetLink) else url
        referer = SITE_REFERER
        if "onhockey.tv" in urlparse(target).netloc:
            fragment = unquote(urlparse(target).fragment or "")
            html = self._fetch_schedule()
            if not html:
                return None
            sources = self._find_sources(fragment, html)
            if not sources:
                return None
            target = sources[0]["url"]

        stream = self.resolver.resolve_url(target, referer)
        if not stream:
            return None
        return self._pack_link(stream, target)
