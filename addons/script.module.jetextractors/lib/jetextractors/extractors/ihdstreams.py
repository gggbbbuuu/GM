import re
import base64
from datetime import datetime
from ..models import *
from .._core import fetch_page
from ..icons import icons
from ..util.resolver import UniversalResolver

SPORTS = ["NFL", "NBA", "UFC", "Boxing", "NHL", "MLB", "WWE", "F1", "NCAAB", "CFB", "WNBA", "Soccer"]
LEAGUE_ICONS = {
    "NFL": "nfl", "NBA": "nba", "UFC": "mma", "Boxing": "boxing", "NHL": "nhl",
    "MLB": "mlb", "WWE": "wwe", "F1": "f1", "NCAAB": "ncaa men", "CFB": "cfb",
    "WNBA": "wnba", "Soccer": "soccer",
}


class IHDStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["ihdstreams.top", "www.ihdstreams.top"]
        self.name = "iHDStreams"
        self.short_name = "IHD"
        self.resolver = UniversalResolver(self.user_agent, "[iHDStreams]")

    def _decode_url(self, raw: str, key: str) -> str:
        d = base64.b64decode(raw + "=" * (-len(raw) % 4))
        xd = bytes(b ^ ord(key[i % len(key)]) for i, b in enumerate(d))
        half = len(xd) // 2
        p1 = base64.b64encode(xd[:half])
        p2 = base64.b64encode(xd[half:])
        j = base64.b64decode(p1 + b"==") + base64.b64decode(p2 + b"==")
        u = bytes(b ^ ord(key[i % len(key)]) for i, b in enumerate(j))
        return u.decode()

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        params = params or {}
        sports = [params["league"]] if params.get("league") else SPORTS
        for idx, sport in enumerate(sports):
            if progress is not None and self.progress_update(progress, f"Fetching {sport} ({idx + 1}/{len(sports)})..."):
                return items
            try:
                html = fetch_page(f"https://{self.domains[0]}/index.php?sport={sport}", referer=f"https://{self.domains[0]}/")
            except Exception:
                continue
            if not html:
                continue
            league = sport.upper()
            for block in re.findall(r'<article class="game-card[^"]*"(.*?)</article>', html, re.S):
                href_m = re.search(r'href="(?:https?://[^"/]+)?/?watch/([^"]+)"', block)
                name_m = re.search(r'itemprop="name" content="([^"]+)"', block)
                if not href_m or not name_m:
                    continue
                title = " ".join(name_m.group(1).split())
                live = 'class="game-card is-live"' in block or "LIVE NOW" in block
                starttime = None
                ts_m = re.search(r'data-event-time="(\d+)"', block)
                if ts_m:
                    try:
                        starttime = datetime.fromtimestamp(int(ts_m.group(1)) / 1000.0)
                    except Exception:
                        starttime = None
                icon_key = LEAGUE_ICONS.get(league, "")
                items.append(JetItem(
                    title,
                    [JetLink(f"https://{self.domains[0]}/watch/{href_m.group(1)}", links=True)],
                    starttime,
                    status="LIVE" if live else None,
                    league=league,
                    icon=icons[icon_key] if icon_key in icons else None,
                ))
        return items

    def get_links(self, event_url) -> List[JetLink]:
        if isinstance(event_url, JetLink):
            event_url = event_url.address
        if "ihdstreams.top" not in event_url:
            return []
        return [JetLink(event_url, name="Stream", headers={"Referer": f"https://{self.domains[0]}/"}, resolveurl=True, extractor=self.name)]

    def get_link(self, url: JetLink) -> JetLink:
        target = url.address if isinstance(url, JetLink) else url
        referer = f"https://{self.domains[0]}/"
        if "ihdstreams.top" not in urlparse(target).netloc:
            return None
        try:
            html = fetch_page(target, referer=referer)
        except Exception:
            return None
        if not html:
            return None
        key_m = re.search(r'_k\s*=\s*"([^"]+)"', html)
        raw_m = re.search(r'_e1\s*=\s*"([^"]+)"', html)
        if not (key_m and raw_m):
            return None
        try:
            embed_path = self._decode_url(raw_m.group(1), key_m.group(1))
        except Exception:
            return None
        if not embed_path:
            return None
        embed_url = embed_path if embed_path.startswith("http") else f"https://{self.domains[0]}{embed_path}"
        try:
            inner = fetch_page(embed_url, referer=target)
        except Exception:
            return None
        if not inner:
            return None
        frame_m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', inner)
        if not frame_m:
            return None
        frame_url = frame_m.group(1)
        if frame_url.startswith("//"):
            frame_url = "https:" + frame_url
        elif frame_url.startswith("/"):
            frame_url = f"https://{self.domains[0]}{frame_url}"
        from ..util.resolver import UniversalResolver
        try:
            stream = self.resolver.resolve_url(frame_url, embed_url)
        except Exception:
            return None
        if not stream:
            return None
        stream_referer = getattr(self.resolver, "stream_referer", None) or embed_url
        headers = {"User-Agent": self.user_agent, "Referer": stream_referer}
        origin = getattr(self.resolver, "stream_origin", None)
        if origin:
            headers["Origin"] = origin
        return JetLink(stream, headers=headers, inputstream=JetInputstreamFFmpegDirect.default())
