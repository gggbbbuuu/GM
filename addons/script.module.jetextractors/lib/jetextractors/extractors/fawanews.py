import re
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup as bs

from ..models import *
from .._core import fetch_page, find_m3u8, find_iframes
from ..tools import debug_log
from ..util.stream_proxy import get_stream_proxy


class FawaNews(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["www.fawanews.sc", "fawanews.sc"]
        self.name = "FawaNews"
        self.short_name = "FW"
        self.base_url = "http://www.fawanews.sc"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}/",
        }
        self._proxy = None

    def _get_proxy(self):
        if self._proxy is None:
            self._proxy = get_stream_proxy(
                "fawanews",
                self.headers,
                options={
                    "strip_png": False,
                    "prefetch_segments": True,
                    "upstream_keep_alive": True,
                    "keep_alive": False,
                },
            )
        return self._proxy

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        html = fetch_page(f"{self.base_url}/", referer=self.base_url)
        if not html:
            return items

        soup = bs(html, "html.parser")
        seen = set()
        for card in soup.select("div.user-item"):
            name_el = card.select_one(".user-item__name")
            if not name_el:
                continue
            title = name_el.get_text(strip=True)
            if not title or title in seen:
                continue

            a_el = card.find("a", href=True)
            if not a_el:
                continue
            href = a_el["href"].strip()
            if not href or href.startswith(("http://", "https://", "//")):
                continue
            href = href.split("#")[0].split("?")[0].strip()
            if not href:
                continue
            seen.add(title)

            icon = ""
            img_el = card.select_one(".user-item__avatar img") or card.find("img")
            if img_el and img_el.get("src"):
                icon = img_el["src"].strip()

            league = None
            status = None
            playing_el = card.select_one(".user-item__playing")
            if playing_el:
                playing = playing_el.get_text(" ", strip=True)
                m = re.match(r"^(.*?)\s+((?:\d{1,2}:\d{2})|--:--)$", playing)
                if m:
                    league = m.group(1).strip() or None
                    status = m.group(2)
                elif playing:
                    league = playing

            # Event pages live at the site root; quote spaces/specials in filename.
            link = f"{self.base_url}/{quote(href)}"
            items.append(JetItem(title=title, links=[JetLink(link, links=True)], icon=icon, league=league, status=status))

        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        html = fetch_page(url.address, referer=self.base_url)
        if not html:
            return links

        # Event pages embed a Clappr player fed by JS vars: d1 + d2 + d3 -> m3u8
        streams = []
        parts = re.findall(r'var\s+d\d+\s*=\s*["\']([^"\']*)["\']', html)
        if len(parts) >= 3:
            streams.append("".join(parts))

        m3u8 = find_m3u8(html, self.base_url)
        if m3u8:
            streams.append(m3u8)

        for stream in streams:
            if not stream.startswith("http"):
                stream = urljoin(self.base_url, stream)
            if stream in [l.address for l in links]:
                continue
            try:
                proxy_url = self._get_proxy().get_proxy_url(stream, self.headers)
                links.append(JetLink(
                    proxy_url,
                    name="Stream",
                    headers=self.headers,
                    inputstream=JetInputstreamFFmpegDirect.default(),
                ))
            except Exception:
                links.append(JetLink(stream, name="Stream", headers=self.headers, inputstream=JetInputstreamAdaptive.hls()))

        if not links:
            for iframe_url in find_iframes(html, url.address):
                links.append(JetLink(iframe_url, resolveurl=True, name="Embed"))

        return links
