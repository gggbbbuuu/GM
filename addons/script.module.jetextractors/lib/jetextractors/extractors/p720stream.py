import re
from datetime import datetime, timezone
from ..models import *
from .._core import fetch_page
from ..icons import icons

CATEGORIES = {
    "nfl-online": "NFL",
    "nhl-online": "NHL",
    "nba-online": "NBA",
    "mlb-online": "MLB",
    "ncaaf-online": "CFB",
    "ncaam-online": "CBB",
    "mma-online": "MMA",
    "boxing-online": "BOXING",
    "soccer-online": "SOCCER",
}


class P720Stream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["720pstream.cx", "www.720pstream.cx"]
        self.name = "720pStream"
        self.short_name = "720"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        params = params or {}
        if params.get("league"):
            slugs = [params["league"]]
        else:
            slugs = list(CATEGORIES.keys())
        for idx, slug in enumerate(slugs):
            if progress is not None and self.progress_update(progress, f"Fetching {slug} ({idx + 1}/{len(slugs)})..."):
                return items
            try:
                html = fetch_page(f"https://{self.domains[0]}/{slug}")
            except Exception:
                continue
            if not html:
                continue
            league = CATEGORIES.get(slug, slug.upper())
            for block in re.findall(r'<a class="match-card" href="([^"]+)">(.*?)</a>', html, re.S):
                href, inner = block
                if not href.startswith("/"):
                    continue
                time_m = re.search(r'<div class="match-time">\s*<span>([^<]+)</span>', inner)
                time_text = " ".join(time_m.group(1).split()) if time_m else ""
                live = 'class="live-badge"' in inner
                teams_m = re.search(r'<div class="match-teams">(.*?)</div>', inner, re.S)
                title = ""
                if teams_m:
                    title = " ".join(re.sub(r"<[^>]+>", " ", teams_m.group(1)).split())
                if not title:
                    title = time_text
                if "24/7" in time_text:
                    title = f"{title} (24/7)"
                starttime = None
                if time_text and re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC$", time_text):
                    try:
                        starttime = datetime.strptime(time_text, "%Y-%m-%d %H:%M:%S UTC") \
                            .replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                    except Exception:
                        starttime = None
                status = "LIVE" if live else None
                if not live and not starttime:
                    status = time_text or None
                items.append(JetItem(
                    title,
                    [JetLink(f"https://{self.domains[0]}{href}", links=True)],
                    starttime,
                    status=status,
                    league=league,
                    icon=icons[league.lower()] if league.lower() in icons else None,
                ))
        return items

    def get_links(self, event_url) -> List[JetLink]:
        if isinstance(event_url, JetLink):
            event_url = event_url.address
        try:
            html = fetch_page(event_url, referer=f"https://{self.domains[0]}/")
        except Exception:
            return []
        links = []
        for frame in re.findall(r'<iframe[^>]+src=["\'](https://embedsports\.me/[^"\']+)["\']', html):
            if frame in [l.address for l in links]:
                continue
            links.append(JetLink(
                frame,
                name=f"Stream {len(links) + 1}",
                headers={"Referer": event_url},
                resolveurl=True,
                extractor=self.name,
            ))
        return links

    def get_link(self, url: JetLink) -> JetLink:
        target = url.address if isinstance(url, JetLink) else url
        referer = f"https://{self.domains[0]}/"
        if "720pstream.cx" in urlparse(target).netloc:
            referer = target
            try:
                html = fetch_page(target, referer=f"https://{self.domains[0]}/")
            except Exception:
                return None
            m = re.search(r'<iframe[^>]+src=["\'](https://embedsports\.me/[^"\']+)["\']', html)
            if not m:
                return None
            target = m.group(1)
        if "embedsports.me" not in urlparse(target).netloc:
            return None
        from .embedstream import Embedstream
        try:
            return Embedstream().get_link(JetLink(target, headers={"Referer": referer}))
        except Exception:
            return None
