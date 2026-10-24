import re
from datetime import datetime, timezone
from ..models import *
from .._core import fetch_page
from ..icons import icons
from ..util.resolver import UniversalResolver

SPORT_PAGES = {
    "footballstreams.php": "NFL",
    "nbastreams.php": "NBA",
    "nhlstreams.php": "NHL",
    "mlbstreams.php": "MLB",
    "mmastreams.php": "MMA",
    "boxingstreams.php": "BOXING",
    "f1streams.php": "F1",
    "motogpstreams.php": "MOTOGP",
}


class FSportsHD(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["fsportshdz.xyz", "www.fsportshdz.xyz"]
        self.name = "FSportsHD"
        self.short_name = "FS"
        self.resolver = UniversalResolver(self.user_agent, "[FSportsHD]")

    def _parse_rows(self, html: str, league: str):
        for href_path, block in re.findall(r'<a href="(channels/[^"]+)">(.*?)</a>', html, re.S):
            title_m = re.search(r"<h4[^>]*>([^<]+)</h4>", block)
            if not title_m:
                continue
            title = " ".join(title_m.group(1).split())
            display_m = re.search(r'<div id="display\d+"([^>]*)>', block)
            live = False
            if display_m and "display:none" not in display_m.group(1):
                live = True
            starttime = None
            date_m = re.search(r"new Date\('([^']+)'\)", block)
            if date_m:
                try:
                    starttime = datetime.strptime(date_m.group(1), "%b %d %Y %H:%M:%S %z").astimezone().replace(tzinfo=None)
                except Exception:
                    starttime = None
            yield {
                "href": f"https://{self.domains[0]}/{href_path}",
                "title": title,
                "live": live,
                "starttime": starttime,
                "league": league,
            }

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        params = params or {}
        if params.get("league"):
            pages = {params["league"]: SPORT_PAGES.get(params["league"], params["league"].upper())}
        else:
            pages = SPORT_PAGES
        for idx, (page, league) in enumerate(pages.items()):
            if progress is not None and self.progress_update(progress, f"Fetching {page} ({idx + 1}/{len(pages)})..."):
                return items
            try:
                html = fetch_page(f"https://{self.domains[0]}/{page}", referer=f"https://{self.domains[0]}/")
            except Exception:
                continue
            if not html:
                continue
            for row in self._parse_rows(html, league):
                items.append(JetItem(
                    row["title"],
                    [JetLink(row["href"], links=True)],
                    row["starttime"],
                    status="LIVE" if row["live"] else None,
                    league=row["league"],
                    icon=icons[row["league"].lower()] if row["league"].lower() in icons else None,
                ))
        return items

    def get_links(self, event_url) -> List[JetLink]:
        if isinstance(event_url, JetLink):
            event_url = event_url.address
        if "fsportshdz.xyz" not in event_url:
            return []
        return [JetLink(event_url, name="Stream", headers={"Referer": f"https://{self.domains[0]}/"}, resolveurl=True, extractor=self.name)]

    def get_link(self, url: JetLink) -> JetLink:
        target = url.address if isinstance(url, JetLink) else url
        referer = f"https://{self.domains[0]}/"
        if "fsportshdz.xyz" in urlparse(target).netloc:
            referer = target
        from ..util.resolver import UniversalResolver
        try:
            stream = self.resolver.resolve_url(target, referer)
        except Exception:
            return None
        if not stream:
            return None
        stream_referer = getattr(self.resolver, "stream_referer", None) or referer
        headers = {"User-Agent": self.user_agent, "Referer": stream_referer}
        origin = getattr(self.resolver, "stream_origin", None)
        if origin:
            headers["Origin"] = origin
        return JetLink(stream, headers=headers, inputstream=JetInputstreamFFmpegDirect.default())
