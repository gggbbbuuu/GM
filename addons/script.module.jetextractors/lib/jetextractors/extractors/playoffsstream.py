import re
from datetime import datetime, timedelta, timezone
from ..models import *
from .._core import fetch_page
from ..icons import icons

CATEGORIES = {
    "nfl-streams": "NFL",
    "nba-streams": "NBA",
    "nhl-streams": "NHL",
    "mlb-streams": "MLB",
    "ncaaf-streams": "CFB",
    "ncaam-streams": "CBB",
    "ncaah-streams": "CBB",
    "ufc-streams": "MMA",
    "boxing-streams": "BOXING",
    "tv-streams": "TV",
}


class PlayoffsStream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["playoffsstream.com", "www.playoffsstream.com"]
        self.name = "PlayoffsStream"
        self.short_name = "PS"

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
            for m in re.finditer(
                r'<a class="btn btn-info btn-block"([^>]*)>(.*?)</a>',
                html,
                re.S,
            ):
                attrs, inner = m.group(1), m.group(2)
                href_m = re.search(r'href="([^"]+)"', attrs)
                title_m = re.search(r'title="([^"]+)"', attrs)
                if not href_m or not href_m.group(1).startswith("/"):
                    continue
                href = href_m.group(1)
                title = " ".join((title_m.group(1) if title_m else "").split())
                title = re.sub(r"\s*Live Stream\s*$", "", title)
                time_m = re.search(r'<div class="text-center">([^<]+)</div>', inner)
                time_text = " ".join(time_m.group(1).split()) if time_m else ""
                starttime = None
                if time_text:
                    try:
                        naive = datetime.strptime(time_text, "%Y-%m-%d %H:%M ET")
                        starttime = naive.replace(tzinfo=timezone(timedelta(hours=-4))).astimezone().replace(tzinfo=None)
                    except Exception:
                        starttime = None
                if not title:
                    continue
                status = None
                if not starttime:
                    status = "24/7" if "tv" in href.split("/")[1] else None
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
        if "playoffsstream.com" in urlparse(target).netloc:
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
