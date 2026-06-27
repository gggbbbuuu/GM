from ..models import *
from typing import Optional, List
import requests
import re
import json
import xbmc
from bs4 import BeautifulSoup
from ..util.stream_proxy import get_stream_proxy


class XYZ(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["xyzstreams.shop"]
        self.name = "XYZ"
        self.short_name = "XYZ"
        self.base_url = f"https://{self.domains[0]}"
        self.embed_api = f"{self.base_url}/embedapi.json"
        self.scoreboard_api = "https://api.streamxyz.shop:2053/api/scoreboard"

        self.stream_headers = {
            "Origin": self.base_url,
            "Referer": self.base_url + "/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
        }

        # Hardcoded Sling channel lineup from the site
        self.sling_channels = [
            ("ESPN", "espn"),
            ("ACC Network", "acc_network"),
            ("BBC America", "bbc_america"),
            ("BeIN Sports", "bein_sports"),
            ("Disney XD", "disney_xd"),
            ("Disney", "disney_channel"),
            ("ESPN2", "espn2"),
            ("ESPNU", "espnu"),
            ("ESPNEWS", "espnnews"),
            ("TNT", "tnt"),
            ("TBS", "tbs"),
            ("USA Network", "usa_network"),
            ("FX", "fx"),
            ("FS1", "FS1"),
            ("FS2", "fs2"),
            ("CNN", "cnn"),
            ("Fox News", "fox_news"),
            ("AMC", "amc"),
            ("Discovery", "discovery"),
            ("HGTV", "hgtv"),
            ("Food Network", "food_network"),
            ("Comedy Central", "comedy_central"),
            ("A&E", "ae"),
            ("History Channel", "history_channel"),
            ("Lifetime", "lifetime"),
            ("Disney Channel", "disney_channel"),
            ("Cartoon Network", "cartoon_network"),
            ("Syfy", "syfy"),
            ("National Geographic", "national_geographic"),
            ("Nickelodeon", "nickelodeon"),
            ("E!", "e"),
            ("Bravo", "bravo"),
            ("BET", "bet"),
            ("TLC", "tlc"),
            ("Travel Channel", "travel_channel"),
            ("AXS TV", "axs_tv"),
            ("NFL Network", "nfl_network"),
        ]

        # XYZ serves PNG-wrapped segments; rewrite .ts->.png upstream and strip.
        self._proxy = get_stream_proxy(
            "xyz",
            self.stream_headers,
            options={
                "strip_png": True,
                "manifest_png_to_ts": True,
                "fetch_png_segments": True,
            },
        )

    def _build_proxy_link(self, upstream_url: str, headers: dict) -> str:
        proxy_url = self._proxy.get_proxy_url(upstream_url, headers)
        xbmc.log(f"[XYZ] Proxy registered: {proxy_url}", xbmc.LOGINFO)
        return proxy_url

    def _fetch_scoreboard(self) -> List[JetItem]:
        items: List[JetItem] = []
        try:
            headers = dict(self.stream_headers)
            headers["Accept"] = "application/json"
            resp = requests.get(
                self.scoreboard_api,
                timeout=self.timeout,
                headers=headers,
            )
            if resp.status_code != 200:
                xbmc.log(f"[XYZ] Scoreboard API returned {resp.status_code}", xbmc.LOGDEBUG)
                return items
            data = resp.json()
            if not isinstance(data, list):
                return items
            for game in data:
                if not isinstance(game, dict):
                    continue
                away = game.get("away", {})
                home = game.get("home", {})
                away_name = away.get("name", "Away")
                home_name = home.get("name", "Home")
                title = f"{away_name} @ {home_name}"
                feeds = game.get("feeds", {})
                if not feeds:
                    continue
                links: List[JetLink] = []
                for feed_name, feed_url in feeds.items():
                    if not feed_url or not isinstance(feed_url, str):
                        continue
                    proxy_url = self._build_proxy_link(feed_url, dict(self.stream_headers))
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=feed_name,
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamFFmpegDirect.default(),
                            resolveurl=False,
                        )
                    )
                if links:
                    status = game.get("statusText", "")
                    if status:
                        title = f"[{status}] {title}"
                    items.append(
                        JetItem(
                            title=title,
                            league="MLB",
                            links=links,
                        )
                    )
        except Exception as e:
            xbmc.log(f"[XYZ] Scoreboard fetch failed: {e}", xbmc.LOGDEBUG)
        return items

    def _fetch_homepage_events(self) -> List[JetItem]:
        items: List[JetItem] = []
        try:
            headers = dict(self.stream_headers)
            resp = requests.get(self.base_url, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                return items
            soup = BeautifulSoup(resp.text, "html.parser")
            event_cards = soup.find_all("a", class_="event-card")
            for card in event_cards:
                href = card.get("href", "")
                if not href:
                    continue
                if href.startswith("/"):
                    href = self.base_url + href
                elif not href.startswith("http"):
                    href = f"{self.base_url}/{href}"

                title_tag = card.find("h3")
                title = title_tag.text.strip() if title_tag else "Event"
                league = self._guess_league(title)

                start = card.get("data-start", "")
                end = card.get("data-end", "")
                status = ""
                if start and end:
                    try:
                        import time as _time
                        now = _time.time()
                        start_ts = self._parse_iso_ts(start)
                        end_ts = self._parse_iso_ts(end)
                        if start_ts and end_ts:
                            if now < start_ts:
                                status = "Upcoming"
                            elif now > end_ts:
                                status = "Ended"
                            else:
                                status = "LIVE"
                    except Exception:
                        pass

                if status:
                    title = f"[{status}] {title}"

                items.append(
                    JetItem(
                        title=title,
                        league=league,
                        links=[JetLink(href, links=True)],
                    )
                )
        except Exception as e:
            xbmc.log(f"[XYZ] Homepage scrape failed: {e}", xbmc.LOGDEBUG)
        return items

    def _parse_iso_ts(self, ts: str) -> Optional[float]:
        try:
            ts = ts.replace("Z", "+00:00")
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception:
            return None

    def _guess_league(self, title: str) -> str:
        t = title.lower()
        if any(x in t for x in ["ufc", "boxing", "wwe"]):
            return "MMA / Boxing"
        if any(x in t for x in ["nhl", "golden knights", "hurricanes"]):
            return "NHL"
        if any(x in t for x in ["mlb", "baseball", "yankees", "dodgers"]):
            return "MLB"
        if any(x in t for x in ["nba", "basketball", "lakers", "celtics"]):
            return "NBA"
        if any(x in t for x in ["nfl", "football", "super bowl", "chiefs"]):
            return "NFL"
        if any(x in t for x in ["fifa", "world cup", "epl", "premier league", "la liga", "bundesliga", "serie a", "uefa", "champions league"]):
            return "Soccer"
        return "Sports"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        mlb_items = self._fetch_scoreboard()
        items.extend(mlb_items)
        homepage_items = self._fetch_homepage_events()
        items.extend(homepage_items)

        for name, clean_id in self.sling_channels:
            m3u8_url = f"https://streamxyz.shop/{clean_id}/index.m3u8"
            proxy_url = self._build_proxy_link(m3u8_url, dict(self.stream_headers))
            items.append(
                JetItem(
                    title=name,
                    league="Cable",
                    links=[
                        JetLink(
                            address=proxy_url,
                            name="Server 1",
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamFFmpegDirect.default(),
                            resolveurl=False,
                        )
                    ],
                )
            )

        xbmc.log(f"[XYZ] Total items: {len(items)} (MLB={len(mlb_items)}, Events={len(homepage_items)}, Channels={len(self.sling_channels)})", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        xbmc.log(f"[XYZ] get_links called for: {url.address}", xbmc.LOGINFO)
        links: List[JetLink] = []
        if "127.0.0.1" in url.address and "/xyz/" in url.address:
            links.append(
                JetLink(
                    address=url.address,
                    name=url.name or "Stream",
                    headers=dict(self.stream_headers),
                    inputstream=JetInputstreamFFmpegDirect.default(),
                    resolveurl=False,
                )
            )
            return links

        if ".m3u8" in url.address:
            proxy_url = self._build_proxy_link(url.address, dict(self.stream_headers))
            links.append(
                JetLink(
                    address=proxy_url,
                    name=url.name or "Stream",
                    headers=dict(self.stream_headers),
                    inputstream=JetInputstreamFFmpegDirect.default(),
                    resolveurl=False,
                )
            )
            return links

        try:
            headers = dict(self.stream_headers)
            resp = requests.get(url.address, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                xbmc.log(f"[XYZ] Embed page returned {resp.status_code}", xbmc.LOGWARNING)
                return links

            html = resp.text
            m3u8_urls = []
            m = re.search(r'const\s+streamUrl\s*=\s*"([^"]+\.m3u8[^"]*)"', html)
            if m:
                m3u8_urls.append(m.group(1))
            m3u8_urls.extend(re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html))

            seen = set()
            for m3u8 in m3u8_urls:
                if m3u8 in seen:
                    continue
                seen.add(m3u8)
                xbmc.log(f"[XYZ] Found m3u8: {m3u8}", xbmc.LOGINFO)
                parts = m3u8.rstrip("/").split("/")
                slug = parts[-2] if len(parts) >= 2 else ""
                if not slug:
                    continue
                proxy_url = self._build_proxy_link(m3u8, dict(self.stream_headers))
                links.append(
                    JetLink(
                        address=proxy_url,
                        name=slug,
                        headers=dict(self.stream_headers),
                        inputstream=JetInputstreamFFmpegDirect.default(),
                        resolveurl=False,
                    )
                )
            if not links:
                xbmc.log("[XYZ] No streams found in embed page", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f"[XYZ] Error in get_links: {e}", xbmc.LOGERROR)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        xbmc.log(f"[XYZ] get_link called for: {url.address}", xbmc.LOGINFO)
        if "127.0.0.1" in url.address and "/xyz/" in url.address:
            return JetLink(
                address=url.address,
                headers=dict(self.stream_headers),
                inputstream=JetInputstreamFFmpegDirect.default(),
                resolveurl=False,
            )

        if ".m3u8" in url.address:
            proxy_url = self._build_proxy_link(url.address, dict(self.stream_headers))
            return JetLink(
                address=proxy_url,
                headers=dict(self.stream_headers),
                inputstream=JetInputstreamFFmpegDirect.default(),
                resolveurl=False,
            )

        links = self.get_links(url)
        if links:
            return links[0]
        return JetLink(address=url.address)
