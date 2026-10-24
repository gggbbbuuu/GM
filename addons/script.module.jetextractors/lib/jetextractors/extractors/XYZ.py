from ..models import *
from typing import Optional, List, Tuple, Dict
import binascii
import hashlib
import re
import json
import time
import uuid
import requests
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, quote

from ..tools import debug_log
from .._core import get_session
import xbmc
from ..util import sling_store
from ..util.xyz_helpers import _hex_to_base64url, _parse_iso_duration
from ..util.xyz_proxy import _extract_clearkey, _ensure_xyz_proxy, _XYZ_PROXY
from .xyz_mappings import MLB_M3U8_MAP, WNBA_M3U8_MAP, WNBA_NATIONAL_MAP, FUBO_NATIONAL_MAP


class XYZ(JetExtractor):
    _MLB_M3U8_MAP = MLB_M3U8_MAP
    _WNBA_M3U8_MAP = WNBA_M3U8_MAP
    _WNBA_NATIONAL_MAP = WNBA_NATIONAL_MAP
    _FUBO_NATIONAL_MAP = FUBO_NATIONAL_MAP

    def _build_fubo_items(self) -> List[JetItem]:
        """Build Fubo national channel items from _FUBO_NATIONAL_MAP."""
        items: List[JetItem] = []
        for name, url in self._FUBO_NATIONAL_MAP.items():
            proxy_url = self._build_proxy_link(url, dict(self.stream_headers))
            items.append(
                JetItem(
                    title=name,
                    league="Fubo",
                    links=[
                        JetLink(
                            address=proxy_url,
                            name=name,
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                            resolveurl=False,
                        )
                    ],
                )
            )
        return items

    def __init__(self) -> None:
        self.domains = ["xyzstreams.st", "player.xyzstreams.space", "player.xyzstreams.st"]
        self.name = "XYZ"
        self.short_name = "XYZ"
        self.base_url = f"https://{self.domains[0]}"
        self.embed_api = f"{self.base_url}/embedapi.json"
        self.mlb_games_api = "https://guide.alexyoung65656.workers.dev/https://stats-api.sportsnet.ca/ticker?league=mlb"
        self.wnba_games_api = "https://guide.alexyoung65656.workers.dev/https://stats-api.sportsnet.ca/ticker?league=wnba"

        self.stream_headers = {
            "Origin": self.base_url,
            "Referer": self.base_url + "/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
        # "Accept": "*/*",
        # "Accept-Language": "en-US,en;q=0.9",
        # "Accept-Encoding": "gzip, deflate, br, zstd",
        # "DNT": "1",
        # "Sec-Ch-Ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        # "Sec-Ch-Ua-mobile": "?0",
        # "Sec-Ch-Ua-Platform": '"Windows"',
        # "Sec-Fetch-Dest": "empty",
        # "Sec-Fetch-Mode": "cors",
        # "Sec-Fetch-Site": "cross-site",
    }

    def _build_proxy_link(self, upstream_url: str, headers: dict, session: Optional[requests.Session] = None) -> str:
        port = _ensure_xyz_proxy()
        token = uuid.uuid4().hex
        
        # Extract ClearKey from upstream URL if present
        license_key = None
        parsed = urlparse(upstream_url)
        qs = parse_qs(parsed.query)
        ck_param = qs.get("ck", [])
        if ck_param:
            ck_value = ck_param[0]
            m = re.match(r"^([a-f0-9]+)[:%3A]([a-f0-9]+)$", ck_value, re.IGNORECASE)
            if m:
                kid_hex, key_hex = m.group(1), m.group(2)
                kid_b64 = _hex_to_base64url(kid_hex)
                key_b64 = _hex_to_base64url(key_hex)
                license_key = f"{kid_b64}:{key_b64}"
                debug_log(f"[XYZ] Extracted ClearKey from upstream URL: kid={kid_hex[:8]}...", xbmc.LOGINFO)
        
        _XYZ_PROXY["upstream"][token] = {
            "url": upstream_url,
            "headers": headers or {},
            "cache": None,
            "cache_time": 0.0,
            "session": session if session is not None else requests.Session(),
            "license_key": license_key,
        }
        proxy_url = f"http://127.0.0.1:{port}/xyz/{token}.m3u8"
        debug_log(f"[XYZ] Proxy registered: {proxy_url}", xbmc.LOGINFO)
        return proxy_url

    def _fetch_mlb_games(self) -> List[JetItem]:
        items: List[JetItem] = []
        try:
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            headers = dict(self.stream_headers)
            headers["Accept"] = "application/json"
            resp = get_session().get(
                self.mlb_games_api,
                timeout=self.timeout,
                headers=headers,
            )
            if resp.status_code != 200:
                debug_log(f"[XYZ] MLB Games API returned {resp.status_code}", xbmc.LOGDEBUG)
                return items
            data = resp.json()
            raw_games = data.get("data", {}).get("games", []) if isinstance(data, dict) else []
            if not isinstance(raw_games, list):
                return items
            now = time.time()
            for game in raw_games:
                if not isinstance(game, dict):
                    continue
                game_dt = game.get("datetime")
                if not game_dt:
                    continue
                game_date = game_dt[:10]
                if game_date != today:
                    continue
                away_info = game.get("visiting_team", {})
                home_info = game.get("home_team", {})
                if not isinstance(away_info, dict) or not isinstance(home_info, dict):
                    continue
                away_abbr = away_info.get("short_name", "")
                home_abbr = home_info.get("short_name", "")
                away_name = away_info.get("name", away_abbr or "Away")
                home_name = home_info.get("name", home_abbr or "Home")
                title = f"{away_name} @ {home_name}"
                api_status = (game.get("game_status") or "").lower()
                clock_info = (game.get("clock") or "").strip()
                is_clock_valid_and_live = clock_info != "" and not clock_info.lower().startswith("0 ")
                status = None
                if (api_status in ("in progress", "live") or game.get("active") is True) and is_clock_valid_and_live:
                    status = "LIVE"
                    if clock_info:
                        title = f"[{clock_info}] {title}"
                elif api_status in ("final", "completed"):
                    status = "Ended"
                elif game_dt:
                    start_ts = self._parse_iso_ts(game_dt)
                    if start_ts:
                        if now < start_ts:
                            status = "Upcoming"
                        else:
                            status = "LIVE"
                if status and status != "LIVE":
                    title = f"[{status}] {title}"
                elif status == "LIVE" and clock_info:
                    pass
                elif status == "LIVE":
                    title = f"[LIVE] {title}"
                links: List[JetLink] = []
                away_m3u8 = self._MLB_M3U8_MAP.get(away_abbr)
                home_m3u8 = self._MLB_M3U8_MAP.get(home_abbr)
                if home_m3u8:
                    proxy_url = self._build_proxy_link(home_m3u8, dict(self.stream_headers))
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=f"Home Feed ({home_abbr})",
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                            resolveurl=False,
                        )
                    )
                if away_m3u8:
                    proxy_url = self._build_proxy_link(away_m3u8, dict(self.stream_headers))
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=f"Away Feed ({away_abbr})",
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                            resolveurl=False,
                        )
                    )
                if links:
                    items.append(
                        JetItem(
                            title=f"Ticket:{title}",
                            league="MLB",
                            links=links,
                        )
                    )
            debug_log(f"[XYZ] MLB Games API: {len(items)} games found", xbmc.LOGINFO)
        except Exception as e:
            debug_log(f"[XYZ] MLB Games API fetch failed: {e}", xbmc.LOGWARNING)
        return items

    def _fetch_wnba_games(self) -> List[JetItem]:
        items: List[JetItem] = []
        try:
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            headers = dict(self.stream_headers)
            headers["Accept"] = "application/json"
            resp = get_session().get(
                self.wnba_games_api,
                timeout=self.timeout,
                headers=headers,
            )
            if resp.status_code != 200:
                debug_log(f"[XYZ] WNBA Games API returned {resp.status_code}", xbmc.LOGDEBUG)
                return items
            data = resp.json()
            raw_games = data.get("data", {}).get("games", []) if isinstance(data, dict) else []
            if not isinstance(raw_games, list):
                return items

            # Fetch ESPN scoreboard for broadcast channel info
            broadcast_map: Dict[str, str] = {}
            try:
                espn_resp = get_session().get(
                    "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
                    timeout=self.timeout,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if espn_resp.status_code == 200:
                    espn_data = espn_resp.json()
                    for evt in espn_data.get("events", []):
                        comps = evt.get("competitions", [])
                        if not comps:
                            continue
                        national = [
                            b for b in comps[0].get("broadcasts", [])
                            if b.get("market") == "national"
                        ]
                        if national:
                            espn_name = (evt.get("shortName") or evt.get("name") or "").upper()
                            chan = national[0].get("names", [""])[0]
                            if chan and espn_name:
                                broadcast_map[espn_name] = chan
            except Exception as e:
                debug_log(f"[XYZ] WNBA ESPN broadcast fetch failed: {e}", xbmc.LOGDEBUG)

            now = time.time()
            for game in raw_games:
                if not isinstance(game, dict):
                    continue
                game_dt = game.get("datetime")
                if not game_dt:
                    continue
                game_date = game_dt[:10]
                if game_date != today:
                    continue
                away_info = game.get("visiting_team", {})
                home_info = game.get("home_team", {})
                if not isinstance(away_info, dict) or not isinstance(home_info, dict):
                    continue
                away_abbr = away_info.get("short_name", "")
                home_abbr = home_info.get("short_name", "")
                away_name = away_info.get("name", away_abbr or "Away")
                home_name = home_info.get("name", home_abbr or "Home")
                title = f"{away_name} @ {home_name}"
                api_status = (game.get("game_status") or "").lower()
                clock_info = (game.get("clock") or "").strip()
                is_clock_valid_and_live = clock_info != "" and not clock_info.lower().startswith("0 ")
                status = None
                if (api_status in ("in progress", "live") or game.get("active") is True) and is_clock_valid_and_live:
                    status = "LIVE"
                    if clock_info:
                        title = f"[{clock_info}] {title}"
                elif api_status in ("final", "completed"):
                    status = "Ended"
                elif game_dt:
                    start_ts = self._parse_iso_ts(game_dt)
                    if start_ts:
                        if now < start_ts:
                            status = "Upcoming"
                        else:
                            status = "LIVE"
                if status and status != "LIVE":
                    title = f"[{status}] {title}"
                elif status == "LIVE" and clock_info:
                    pass
                elif status == "LIVE":
                    title = f"[LIVE] {title}"
                links: List[JetLink] = []
                away_m3u8 = self._WNBA_M3U8_MAP.get(away_abbr)
                home_m3u8 = self._WNBA_M3U8_MAP.get(home_abbr)
                if home_m3u8:
                    proxy_url = self._build_proxy_link(home_m3u8, dict(self.stream_headers))
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=f"Home Feed ({home_abbr})",
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                            resolveurl=False,
                        )
                    )
                if away_m3u8:
                    proxy_url = self._build_proxy_link(away_m3u8, dict(self.stream_headers))
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=f"Away Feed ({away_abbr})",
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                            resolveurl=False,
                        )
                    )
                espn_key = f"{away_abbr} @ {home_abbr}"
                chan_name = broadcast_map.get(espn_key)
                if chan_name:
                    lookup = chan_name.lower().strip()
                    match = self._WNBA_NATIONAL_MAP.get(lookup)
                    if match:
                        display, stream_id = match
                        embed_url = f"{self.base_url}/2472.html?streamid={stream_id}&proid=sling"
                        links.append(
                            JetLink(
                                address=embed_url,
                                name=f"\U0001f4fa {display} ({chan_name})",
                                links=True,
                            )
                        )
                if links:
                    items.append(
                        JetItem(
                            title=f"Ticket: {title}",
                            league="WNBA",
                            links=links,
                        )
                    )
        except Exception as e:
            debug_log(f"[XYZ] WNBA Games API fetch failed: {e}", xbmc.LOGWARNING)
        return items

    def _extract_js_array(self, html: str, var_name: str) -> list:
        try:
            m = re.search(rf"const\s+{re.escape(var_name)}\s*=\s*(\[.*?\])\s*;", html, re.DOTALL)
            if not m:
                return []
            raw = m.group(1)
            raw = re.sub(r"(?<!:)//.*?$", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
            raw = re.sub(
                r"'((?:\\.|[^'\\])*)'",
                lambda match: '"' + match.group(1).replace("\\'", "'") + '"',
                raw,
            )
            raw = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', raw)
            raw = re.sub(r",\s*(?=[}\]])", "", raw)
            return json.loads(raw)
        except Exception as e:
            debug_log(f"[XYZ] Failed to parse {var_name}: {e}", xbmc.LOGDEBUG)
            return []

    def _parse_events(self, html: str) -> List[JetItem]:
        items: List[JetItem] = []
        for event in self._extract_js_array(html, "EVENTS_DATA"):
            if not isinstance(event, dict):
                continue
            title = event.get("title", "Event").strip()
            href = event.get("href", "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = self.base_url + href
            elif not href.startswith("http"):
                href = f"{self.base_url}/{href}"
            if "college football" in title.lower() or "cfb" in title.lower():
                league = "College Football"
            else:
                league = self._guess_league(title, event.get("category"))

            start = event.get("start", "")
            end = event.get("end", "")
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
        return items

    def _parse_sling_map(self, html: str) -> List[JetItem]:
        """Parse SLING_LINEUP_MAP (object/dict with 80+ channels)."""
        items: List[JetItem] = []
        try:
            m = re.search(r"const\s+SLING_LINEUP_MAP\s*=\s*(\{.*?\});", html, re.DOTALL)
            if not m:
                debug_log("[XYZ] SLING_LINEUP_MAP not found in HTML", xbmc.LOGDEBUG)
                return items
            raw = m.group(1)
            raw = re.sub(
                r"'((?:\\.|[^'\\])*)'",
                lambda match: '"' + match.group(1).replace("\\'", "'") + '"',
                raw,
            )
            raw = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', raw)
            raw = re.sub(r",\s*(?=[}\]])", "", raw)
            channels_map = json.loads(raw)
            if not isinstance(channels_map, dict):
                return items
            for key, chan in channels_map.items():
                if not isinstance(chan, dict):
                    continue
                name = chan.get("displayName", "").strip()
                if not name:
                    continue
                embed_url = chan.get("embedUrl", "").strip()
                if embed_url:
                    if embed_url.startswith("http://") or embed_url.startswith("https://"):
                        embed_url_abs = embed_url
                    elif embed_url.startswith("/"):
                        embed_url_abs = self.base_url + embed_url
                    else:
                        embed_url_abs = f"{self.base_url}/{embed_url}"
                    debug_log(f"[XYZ] Embed URL for {name}: {embed_url_abs}", xbmc.LOGDEBUG)
                else:
                    stream_id = chan.get("id", "")
                    if not stream_id:
                        continue
                    embed_url_abs = f"{self.base_url}/2472.html?streamid={stream_id}&proid=sling"
                    debug_log(f"[XYZ] Constructed embed URL for {name}: {embed_url_abs}", xbmc.LOGDEBUG)
                named_id = str(chan.get("id") or "").strip()
                if named_id and not named_id.isdigit() and re.search(r"2472?\.html", embed_url_abs):
                    embed_url_abs = f"{self.base_url}/2472.html?streamid={named_id}&proid=sling"
                items.append(
                    JetItem(
                        title=name,
                        league="Cable",
                        links=[JetLink(embed_url_abs, links=True)],
                    )
                )
        except Exception as e:
            debug_log(f"[XYZ] Failed to parse SLING_LINEUP_MAP: {e}", xbmc.LOGWARNING)
        return items

    def _fetch_homepage_data(self) -> Tuple[List[JetItem], List[JetItem]]:
        events: List[JetItem] = []
        channels: List[JetItem] = []
        try:
            headers = dict(self.stream_headers)
            resp = get_session().get(self.base_url, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                return events, channels
            html = resp.text
            events = self._parse_events(html)
            channels = self._parse_sling_map(html)
            debug_log(f"[XYZ] Fetched homepage: {len(channels)} channels", xbmc.LOGDEBUG)
            for ch in channels:
                link_addrs = [l.address for l in ch.links if hasattr(l, "address")]
                debug_log(f"[XYZ] Channel: {ch.title} -> {link_addrs}", xbmc.LOGDEBUG)

            if channels and sling_store.is_stale():
                try:
                    store_rows = []
                    for ch in channels:
                        embed_url = ch.links[0].address if ch.links and hasattr(ch.links[0], "address") else ""
                        stream_id = ""
                        if embed_url:
                            parsed_eu = urlparse(embed_url)
                            qs = parse_qs(parsed_eu.query)
                            stream_id = qs.get("streamid", [None])[0]
                            if not stream_id:
                                query_val = parsed_eu.query.strip()
                                if query_val and query_val.isdigit():
                                    stream_id = query_val
                            stream_id = stream_id or ""
                        store_rows.append({
                            "name": ch.title,
                            "embed_url": embed_url,
                            "stream_id": stream_id,
                        })
                    sling_store.add_channels(store_rows)
                    sling_store.set_last_refresh_ts(time.time())
                    debug_log(f"[XYZ] Saved {len(store_rows)} sling channels to DB", xbmc.LOGINFO)
                except Exception as e:
                    debug_log(f"[XYZ] Failed to save sling channels to DB: {e}", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[XYZ] Homepage fetch failed: {e}", xbmc.LOGDEBUG)
        return events, channels

    def _fetch_espn_items(self) -> List[JetItem]:
        items: List[JetItem] = []
        espn_api = "https://espn.dlhd.net/"
        try:
            headers = {
                "Accept": "application/json",
                "User-Agent": self.stream_headers["User-Agent"],
            }
            resp = get_session().get(espn_api, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                debug_log(f"[XYZ] ESPN API returned {resp.status_code}", xbmc.LOGDEBUG)
                return items
            data = resp.json()
            item_list = data.get("itemListElement", [])
            if not isinstance(item_list, list):
                return items
            now = time.time()
            for entry in item_list:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name", "").strip()
                content_url = entry.get("contentUrl", "").strip()
                if not name or not content_url:
                    continue
                start_time = entry.get("startTime", "")
                duration_iso = entry.get("duration", "")
                start_ts = self._parse_iso_ts(start_time)
                duration_secs = _parse_iso_duration(duration_iso)
                end_ts = (start_ts + duration_secs) if start_ts and duration_secs else None
                if start_ts and end_ts:
                    if now > end_ts:
                        continue
                    status = "LIVE" if now >= start_ts else "Upcoming"
                elif start_ts:
                    status = "Upcoming" if now < start_ts else "LIVE"
                else:
                    status = None
                title = f"[{status}] {name}" if status else name
                league = self._guess_league(name, "ESPN+")
                icon = entry.get("thumbnailUrl", "")
                links = [JetLink(content_url, links=True)]
                items.append(
                    JetItem(
                        title=title,
                        league=league,
                        links=links,
                        icon=icon if icon else None,
                    )
                )
            debug_log(f"[XYZ] ESPN+ items: {len(items)}", xbmc.LOGINFO)
        except Exception as e:
            debug_log(f"[XYZ] ESPN+ fetch failed: {e}", xbmc.LOGWARNING)
        return items

    def _parse_iso_ts(self, ts: str) -> Optional[float]:
        try:
            ts = ts.replace("Z", "+00:00")
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception:
            return None

    def _guess_league(self, title: str, category: Optional[str] = None) -> str:
        if category:
            cat = category.lower()
            if cat in ("football", "soccer"):
                return "Soccer"
            if cat in ("american football", "football (american)"):
                return "NFL"
            if cat in ("combat sports", "mma", "boxing"):
                return "MMA / Boxing"
            if cat == "basketball":
                return "NBA"
            if cat == "baseball":
                return "MLB"
            if cat == "hockey":
                return "NHL"
            if cat == "football (american)":
                return "NFL"
            if cat == "espn+":
                return "ESPN+"
        t = title.lower()
        if any(x in t for x in ["ufc", "boxing", "wwe"]):
            return "MMA / Boxing"
        if any(x in t for x in ["nhl", "golden knights", "hurricanes"]):
            return "NHL"
        if any(x in t for x in ["mlb", "baseball", "yankees", "dodgers"]):
            return "MLB"
        if any(x in t for x in ["wnba","liberty", "sparks","aces","storm", "sky", "tempo"]):
            return "WNBA"
        if any(x in t for x in ["nba", "basketball", "lakers", "celtics"]):
            return "NBA"
        if any(x in t for x in ["nfl", "football", "super bowl", "chiefs"]):
            return "NFL"
        if any(x in t for x in ["fifa", "world cup", "epl", "premier league", "la liga", "bundesliga", "serie a", "uefa", "champions league"]):
            return "Soccer"
        if any(x in t for x in ["college football", "cfb"]):
            return "College Football"
        
        if any(x in t for x in ["espn+", "espn plus"]):
            return "ESPN+"
        return "Sports"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        homepage_items, channel_items = self._fetch_homepage_data()
        # Expand schedule-type events (CFB weeks etc.) into one item per game
        # so matchups appear directly in the main list.
        expanded_homepage: List[JetItem] = []
        for ev in homepage_items:
            expanded_homepage.extend(self._expand_schedule_event(ev))
        homepage_items = expanded_homepage
        espn_items = self._fetch_espn_items()
        mlb_items = self._fetch_mlb_games()
        wnba_items = self._fetch_wnba_games()
        fubo_items = self._build_fubo_items()
        items.extend(homepage_items)
        items.extend(channel_items)
        items.extend(espn_items)
        items.extend(mlb_items)
        items.extend(wnba_items)
        items.extend(fubo_items)

        for ch in channel_items:
            link_addrs = [l.address for l in ch.links if hasattr(l, "address")]
            debug_log(f"[XYZ] Channel: {ch.title} -> {link_addrs}", xbmc.LOGINFO)
        debug_log(f"[XYZ] Total items: {len(items)} (Events={len(homepage_items)}, Channels={len(channel_items)}, ESPN={len(espn_items)}, MLB={len(mlb_items)}, WNBA={len(wnba_items)}, Fubo={len(fubo_items)})", xbmc.LOGINFO)
        return items

    def _parse_schedule_rows(self, html: str) -> List[Tuple[str, str]]:
        """Parse schedule-list rows into (display_name, href) pairs.

        Team names live in .game-teams (away span, @, home span); older
        pages used .game-title. Time is .game-meta, channel .network-badge.
        Display name reads "Ohio State @ Indiana (12:00 PM ET) [FOX]".
        """
        rows: List[Tuple[str, str]] = []
        matches = re.findall(
            r'<a\s+href="(/[^"]+\.html)"[^>]*>\s*<li[^>]*class="text247"[^>]*>(.*?)</li>',
            html,
            re.DOTALL,
        )
        if not matches:
            matches = [
                (href, "")
                for href in re.findall(r'<a\s+href="(/[^"]+\.html)"[^>]*>', html)
            ]
        seen = set()
        for match in matches:
            if isinstance(match, tuple):
                href, inner_html = match
            else:
                href, inner_html = match, ""
            if href in seen:
                continue
            seen.add(href)
            game_title = ""
            teams_match = re.search(r'class="game-teams"[^>]*>(.*?)</div>', inner_html, re.DOTALL)
            if teams_match:
                spans = re.findall(r"<span[^>]*>(.*?)</span>", teams_match.group(1), re.DOTALL)
                teams = [re.sub(r"<[^>]+>", "", s).strip() for s in spans]
                teams = [t for t in teams if t and t != "@"]
                if len(teams) >= 2:
                    game_title = f"{teams[0]} @ {teams[1]}"
                elif teams:
                    game_title = teams[0]
            if not game_title:
                title_match = re.search(r'class="game-title"[^>]*>(.*?)</div>', inner_html, re.DOTALL)
                if title_match:
                    game_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            if not game_title:
                game_title = href.rsplit("/", 1)[-1].replace(".html", "").replace("-", " ").upper()
            meta_match = re.search(r'class="game-meta"[^>]*>(.*?)</div>', inner_html, re.DOTALL)
            game_meta = re.sub(r'<[^>]+>', '', meta_match.group(1)).strip() if meta_match else ""
            badge_match = re.search(r'class="network-badge"[^>]*>(.*?)</span>', inner_html, re.DOTALL)
            game_badge = re.sub(r'<[^>]+>', '', badge_match.group(1)).strip() if badge_match else ""
            display_name = game_title
            if game_meta:
                display_name = f"{game_title} ({game_meta})"
            if game_badge:
                display_name = f"{display_name} [{game_badge}]"
            rows.append((display_name, href))
        return rows

    def _expand_schedule_event(self, item: JetItem) -> List[JetItem]:
        """Expand a schedule-type homepage event (CFB week, etc.) into
        one JetItem per game, listed directly in the main events view.

        Non-schedule pages (UFC, single events) return the original item.
        """
        if not item.links:
            return [item]
        href = item.links[0].address if hasattr(item.links[0], "address") else ""
        if not href:
            return [item]
        try:
            resp = get_session().get(href, timeout=self.timeout, headers=dict(self.stream_headers))
            if resp.status_code != 200:
                return [item]
            rows = self._parse_schedule_rows(resp.text)
            if not rows:
                return [item]
            status_prefix = ""
            m = re.match(r"^\[([^\]]+)\]\s*", item.title)
            if m:
                status_prefix = f"[{m.group(1)}] "
            expanded: List[JetItem] = []
            for name, sub_href in rows:
                abs_href = self.base_url + sub_href if sub_href.startswith("/") else sub_href
                expanded.append(
                    JetItem(
                        title=f"{status_prefix}{name}",
                        league=item.league,
                        links=[JetLink(abs_href, links=True)],
                        icon=item.icon,
                    )
                )
            debug_log(
                f"[XYZ] Expanded '{item.title}' into {len(expanded)} schedule games",
                xbmc.LOGINFO,
            )
            return expanded
        except Exception as e:
            debug_log(f"[XYZ] Schedule expand failed for {item.title}: {e}", xbmc.LOGDEBUG)
            return [item]

    def _lookup_named_sling_id(self, numeric_id: str) -> Optional[str]:
        cache = getattr(self, "_sling_numeric_ids", None)
        if cache is None:
            cache = {}
            try:
                resp = get_session().get(
                    self.base_url,
                    timeout=self.timeout,
                    headers=dict(self.stream_headers),
                )
                if resp.status_code == 200:
                    m = re.search(r"const\s+SLING_LINEUP_MAP\s*=\s*(\{.*?\});", resp.text, re.DOTALL)
                    if m:
                        raw = m.group(1)
                        raw = re.sub(
                            r"'((?:\\.|[^'\\])*)'",
                            lambda match: '"' + match.group(1).replace("\\'", "'") + '"',
                            raw,
                        )
                        raw = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', raw)
                        raw = re.sub(r",\s*(?=[}\]])", "", raw)
                        channels_map = json.loads(raw)
                        if isinstance(channels_map, dict):
                            for chan in channels_map.values():
                                if not isinstance(chan, dict):
                                    continue
                                sid = str(chan.get("id") or "").strip()
                                embed = str(chan.get("embedUrl") or "")
                                q = urlparse(embed).query.strip()
                                if sid and not sid.isdigit() and q.isdigit():
                                    cache[q] = sid
            except Exception as e:
                debug_log(f"[XYZ] Sling id lookup failed: {e}", xbmc.LOGDEBUG)
            self._sling_numeric_ids = cache
        return cache.get(numeric_id)

    def _workers_jetlink(self, stream_id: str, pro_id: str, name: str) -> Optional[JetLink]:
        api = (
            "https://247.gavyny704.workers.dev/"
            f"?stream_id={quote(stream_id, safe='')}&pro_id={quote(pro_id or 'sling', safe='')}"
        )
        headers = dict(self.stream_headers)
        headers["Accept"] = "application/json"
        try:
            resp = None
            for attempt in (1, 2):
                resp = get_session().get(api, timeout=self.timeout, headers=headers)
                if resp.status_code == 200:
                    break
                debug_log(f"[XYZ] workers.dev returned {resp.status_code} for {stream_id} (try {attempt})", xbmc.LOGWARNING)
            if resp is None or resp.status_code != 200:
                return None
            data = resp.json()
        except Exception as e:
            debug_log(f"[XYZ] workers.dev fetch failed for {stream_id}: {e}", xbmc.LOGWARNING)
            return None
        if not isinstance(data, dict) or not data.get("success") or not data.get("manifest") or not data.get("key"):
            debug_log(f"[XYZ] workers.dev has no playable key for {stream_id}: {data}", xbmc.LOGWARNING)
            return None
        key = str(data["key"]).lower()
        if not re.match(r"^[a-f0-9]{32}:[a-f0-9]{32}$", key):
            debug_log(f"[XYZ] workers.dev key format invalid for {stream_id}", xbmc.LOGWARNING)
            return None
        proxy_url = self._build_proxy_link(api, dict(self.stream_headers))
        token = proxy_url.rstrip("/").rsplit("/", 1)[-1].split(".")[0]
        entry = _XYZ_PROXY["upstream"].get(token)
        if entry is not None:
            entry["license_key"] = key
        debug_log(f"[XYZ] Sling ClearKey stream {stream_id} via workers.dev", xbmc.LOGINFO)
        return JetLink(
            address=proxy_url,
            name=name or stream_id,
            headers=dict(self.stream_headers),
            inputstream=JetInputstreamAdaptive(
                manifest_type="hls",
                license_type="org.w3.clearkey",
                license_key=key,
            ),
            resolveurl=False,
        )

    def _resolve_247_link(self, url: JetLink) -> Optional[JetLink]:
        parsed = urlparse(url.address)
        qs = parse_qs(parsed.query)
        stream_id = (qs.get("streamid") or [None])[0]
        pro_id = (qs.get("proid") or ["sling"])[0] or "sling"
        if not stream_id:
            query_val = parsed.query.strip()
            if query_val.isdigit():
                stream_id = query_val
        if not stream_id:
            return None
        if stream_id.isdigit():
            named = self._lookup_named_sling_id(stream_id)
            if named:
                debug_log(f"[XYZ] Mapped numeric sling id {stream_id} -> {named}", xbmc.LOGINFO)
                stream_id = named
                pro_id = "sling"
        if not stream_id.isdigit():
            resolved = self._workers_jetlink(stream_id, pro_id, url.name or stream_id)
            if resolved:
                return resolved
        debug_log(f"[XYZ] No workers.dev stream for {stream_id}", xbmc.LOGWARNING)
        return None

    _EMBED_SERVERS = (
        # Live servers per the /embed player page (2026-10-17). The old
        # xyzstreams.space / duckdns.org entries are dead; servers 2/3 are
        # now iximiuz nodes. Markers map best-server LB responses (when
        # xyzstreams.blog is reachable) to the matching stream host.
        ("https://hls.fancy-shark151.workers.dev", "https://hls.fancy-shark151.workers.dev/api/token", "b-cdn.net"),
        ("https://6ad384387c9e458d4217b78d-226ffd.node-us-2b7a.iximiuz.com", "https://6ad384387c9e458d4217b78d-226ffd.node-us-2b7a.iximiuz.com/api/token", "node-us-2b7a"),
        ("https://6ad3846f7c9e458d4217bb40-e8ea9b.node-us-1a4e.iximiuz.com", "https://6ad3846f7c9e458d4217bb40-e8ea9b.node-us-1a4e.iximiuz.com/api/token", "node-us-1a4e"),
    )

    def _decrypt_embed_token(self, iv_hex: str, token_hex: str) -> str:
        key = hashlib.sha256(b"MySuperSecretKey123!").digest()
        iv = binascii.unhexlify(iv_hex)
        ct = binascii.unhexlify(token_hex)
        raw = None
        try:
            from Cryptodome.Cipher import AES
            raw = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
        except Exception:
            try:
                from Crypto.Cipher import AES
                raw = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
            except Exception:
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
                raw = decryptor.update(ct) + decryptor.finalize()
        pad = raw[-1]
        if 1 <= pad <= 16 and raw.endswith(bytes([pad]) * pad):
            raw = raw[:-pad]
        return "".join(ch for ch in raw.decode("utf-8", "replace") if 32 <= ord(ch) <= 126)

    def _fetch_embed_token(self, token_api: str, session: Optional[requests.Session] = None) -> Optional[str]:
        try:
            sess = session or get_session()
            resp = sess.get(token_api, timeout=self.timeout, headers=dict(self.stream_headers))
            if resp.status_code != 200:
                debug_log(f"[XYZ] Embed token API returned {resp.status_code}", xbmc.LOGWARNING)
                return None
            data = resp.json()
            token = self._decrypt_embed_token(data["iv"], data["token"])
            return token or None
        except Exception as e:
            debug_log(f"[XYZ] Embed token fetch failed: {e}", xbmc.LOGWARNING)
            return None

    def _embed_header_refresher(self, token_api: str, session: Optional[requests.Session] = None):
        def _prep():
            headers = dict(self.stream_headers)
            token = self._fetch_embed_token(token_api, session=session)
            if token:
                headers["x-token"] = token
            return headers
        return _prep

    def _pick_embed_servers(self):
        ordered = list(self._EMBED_SERVERS)
        try:
            resp = get_session().get(
                "https://xyzstreams.blog/5/best-server",
                timeout=3,
                headers=dict(self.stream_headers),
            )
            if resp.status_code == 200:
                best = str(resp.json().get("best_server") or "")
                for server in self._EMBED_SERVERS:
                    if server[2] in best:
                        ordered = [server] + [s for s in self._EMBED_SERVERS if s[0] != server[0]]
                        break
        except Exception as e:
            debug_log(f"[XYZ] Embed load balancer failed: {e}", xbmc.LOGDEBUG)
        return ordered

    def _resolve_embed_mono(self, stream_name: str) -> Optional[JetLink]:
        stream_name = (stream_name or "").strip()
        if not stream_name or "/" in stream_name:
            return None
        # Embed server slugs are inconsistently cased (fox/ESPN vs ABC/SECN);
        # try the badge text as-is, then lowercase, then uppercase. Channel
        # slugs use ?server=1; event* slugs (ESPN+ games) use ?server=2 —
        # try both params for every slug.
        slug_variants: List[str] = []
        for v in (stream_name, stream_name.lower(), stream_name.upper()):
            if v not in slug_variants:
                slug_variants.append(v)
        server_params = ("1", "2")
        for base, token_api, _marker in self._pick_embed_servers():
            # The workers.dev x-token is bound to the TCP connection/isolate
            # that minted it — mint, validate, and proxy must all share ONE
            # session or the proxy fetch is rejected with 403.
            session = requests.Session()
            token = self._fetch_embed_token(token_api, session=session)
            if not token:
                session.close()
                continue
            matched_slug = None
            stream_url = None
            resp = None
            for sp in server_params:
                for slug in slug_variants:
                    candidate = f"{base}/{slug}/mono.ts.m3u8?server={sp}"
                    headers = dict(self.stream_headers)
                    headers["x-token"] = token
                    try:
                        resp = session.get(candidate, timeout=self.timeout, headers=headers)
                    except Exception as e:
                        debug_log(f"[XYZ] Embed playlist failed {candidate}: {e}", xbmc.LOGWARNING)
                        resp = None
                        continue
                    if resp.status_code == 200 and "#EXTM3U" in resp.text[:300]:
                        matched_slug = slug
                        stream_url = candidate
                        break
                    debug_log(f"[XYZ] Embed playlist {resp.status_code} for {candidate}", xbmc.LOGDEBUG)
                if stream_url:
                    break
            if not stream_url or resp is None:
                session.close()
                continue
            headers = dict(self.stream_headers)
            headers["x-token"] = token
            proxy_url = self._build_proxy_link(stream_url, headers, session=session)
            proxy_token = proxy_url.rstrip("/").rsplit("/", 1)[-1].split(".")[0]
            entry = _XYZ_PROXY["upstream"].get(proxy_token)
            if entry is not None:
                entry["prepare_headers"] = self._embed_header_refresher(token_api, session=session)
            debug_log(
                f"[XYZ] Embed stream {stream_name} (as {matched_slug}) -> {stream_url}",
                xbmc.LOGINFO,
            )
            return JetLink(
                address=proxy_url,
                name=stream_name,
                headers=headers,
                inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                resolveurl=False,
            )
        debug_log(f"[XYZ] No embed playlist for {stream_name}", xbmc.LOGWARNING)
        return None

    def get_links(self, url: JetLink) -> List[JetLink]:
        debug_log(f"[XYZ] get_links called for: {url.address}", xbmc.LOGINFO)
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

        parsed_url = urlparse(url.address)
        if "dlhd.net" in parsed_url.netloc and parsed_url.path.endswith(".m3u8"):
            proxy_url = self._build_proxy_link(url.address, dict(self.stream_headers))
            links.append(
                JetLink(
                    address=proxy_url,
                    name=url.name or "Stream",
                    headers=dict(self.stream_headers),
                    inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                    resolveurl=False,
                )
            )
            return links
        if parsed_url.path == "/jetextractor/alt":
            # Legacy alt wrapper links (old favorites) — delegate to XYZAlt.
            try:
                from .xyz_alt import XYZAlt
                return XYZAlt().get_links(url)
            except Exception as e:
                debug_log(f"[XYZ] Alt delegation failed: {e}", xbmc.LOGWARNING)
                return links

        if "xyzstreams.st/player.html" in url.address:
            stream_id = parse_qs(urlparse(url.address).query).get("id", [None])[0]
            if stream_id:
                stream_url = f"https://xyzstreams.blog/2/stream/espn/{stream_id}/stream_0.m3u8"
                # Proxy the master playlist directly so ISA can select both
                # a video variant AND the audio rendition. Splitting into
                # individual variants drops #EXT-X-MEDIA audio tags -> no audio.
                proxy_url = self._build_proxy_link(stream_url, dict(self.stream_headers))
                license_key = _extract_clearkey(
                    stream_url, dict(self.stream_headers), self.timeout
                )
                if license_key:
                    inputstream = JetInputstreamAdaptive(
                        manifest_type="hls",
                        license_type="org.w3.clearkey",
                        license_key=license_key,
                    )
                else:
                    inputstream = JetInputstreamAdaptive(manifest_type="hls")
                links.append(
                    JetLink(
                        address=proxy_url,
                        name=stream_id,
                        headers=dict(self.stream_headers),
                        inputstream=inputstream,
                        resolveurl=False,
                    )
                )
                return links

        if re.search(r"2472?\.html", urlparse(url.address).path):
            sling_link = self._resolve_247_link(url)
            if sling_link:
                links.append(sling_link)
            return links

        parsed_embed = urlparse(url.address)
        if parsed_embed.path in ("/embed", "/embedjw") and parsed_embed.query:
            embed_link = self._resolve_embed_mono(parsed_embed.query)
            if embed_link:
                links.append(embed_link)
            return links

        if parsed_embed.path == "/embedserver2" and parsed_embed.query:
            # Old host iptvstream2.xyzstreams.space is dead (DNS). Event slugs
            # (event*) live on the mono embed servers with ?server=2.
            embed_link = self._resolve_embed_mono(parsed_embed.query)
            if embed_link:
                links.append(embed_link)
            return links

        if "player.xyzstreams.space" in parsed_url.netloc or "player.xyzstreams.st" in parsed_url.netloc:
            try:
                headers = dict(self.stream_headers)
                resp = get_session().get(url.address, timeout=self.timeout, headers=headers)
                if resp.status_code != 200:
                    debug_log(f"[XYZ] Player page returned {resp.status_code}", xbmc.LOGWARNING)
                    return links
                html = resp.text
                signed_url_match = re.search(r'data-signed-url="([^"]+)"', html)
                if signed_url_match:
                    stream_url = signed_url_match.group(1)
                    debug_log(f"[XYZ] Player signed URL: {stream_url[:200]}", xbmc.LOGINFO)
                    proxy_url = self._build_proxy_link(stream_url, dict(self.stream_headers))
                    stream_id = url.address.rsplit("/", 1)[-1] if "/" in url.address else "Stream"
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=url.name or stream_id,
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                            resolveurl=False,
                        )
                    )
                    return links
                debug_log("[XYZ] Player page missing data-signed-url", xbmc.LOGWARNING)
            except Exception as e:
                debug_log(f"[XYZ] Player page fetch failed: {e}", xbmc.LOGWARNING)
            return links

        if ".m3u8" in url.address or ".mpd" in url.address:
            proxy_url = self._build_proxy_link(url.address, dict(self.stream_headers))
            if "xyzstreams.blog" in urlparse(url.address).netloc:
                license_key = _extract_clearkey(
                    url.address, dict(self.stream_headers), self.timeout
                )
                if license_key:
                    inputstream = JetInputstreamAdaptive(
                        manifest_type="hls",
                        license_type="org.w3.clearkey",
                        license_key=license_key,
                    )
                else:
                    inputstream = JetInputstreamAdaptive(manifest_type="hls")
            else:
                inputstream = JetInputstreamAdaptive(manifest_type="hls")
            links.append(
                JetLink(
                    address=proxy_url,
                    name=url.name or "Stream",
                    headers=dict(self.stream_headers),
                    inputstream=inputstream,
                    resolveurl=False,
                )
            )
            return links

        try:
            return self._resolve_embed_page(url.address, url)
        except Exception as e:
            debug_log(f"[XYZ] Error in get_links: {e}", xbmc.LOGERROR)

        return links

    def _resolve_embed_page(self, embed_url: str, orig_url: Optional[JetLink] = None) -> List[JetLink]:
        """Fetch an embed/event page and extract playable links or further links.

        Shared by XYZ and XYZAlt: parses dynamic streams arrays, stream-switcher
        buttons, iframes, and raw m3u8/mpd URLs from the page HTML.
        """
        links: List[JetLink] = []
        orig = orig_url.address if orig_url is not None else embed_url
        try:
            headers = dict(self.stream_headers)
            resp = get_session().get(embed_url, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                debug_log(f"[XYZ] Embed page returned {resp.status_code}", xbmc.LOGWARNING)
                return links

            html = resp.text

            # New-style event pages (e.g. ufc.html) define their players in a
            # JS `const streams = [{btnName, title, source}, ...]` array.
            if not links:
                for stream in self._extract_js_array(html, "streams"):
                    if not isinstance(stream, dict):
                        continue
                    src = (stream.get("source") or "").strip()
                    if not src or "${" in src:
                        continue
                    if src.startswith("/"):
                        src = self.base_url + src
                    elif not src.startswith("http"):
                        src = f"{self.base_url}/{src}"
                    btn = (stream.get("btnName") or stream.get("title") or "Stream").strip()
                    debug_log(f"[XYZ] Dynamic stream button: {btn} -> {src}", xbmc.LOGINFO)
                    links.append(JetLink(src, name=btn, links=True))
                if links:
                    return links

            stream_switcher_matches = re.findall(
                r'<button[^>]*class="stream-btn[^"]*"[^>]*data-url="([^"]+)"[^>]*>(.*?)</button>',
                html,
                re.DOTALL,
            )
            if stream_switcher_matches:
                debug_log(f"[XYZ] Found {len(stream_switcher_matches)} stream-switcher buttons", xbmc.LOGINFO)
                seen_btn = set()
                for btn_url, btn_name in stream_switcher_matches:
                    btn_url = btn_url.replace("&amp;", "&")
                    btn_name = re.sub(r'<[^>]+>', '', btn_name).strip()
                    if "HEVC" in btn_name.upper():
                        debug_log(f"[XYZ] Skipping HEVC button: {btn_name}", xbmc.LOGINFO)
                        continue
                    if btn_url.startswith("/"):
                        btn_url = self.base_url + btn_url
                    elif not btn_url.startswith("http"):
                        btn_url = f"{self.base_url}/{btn_url}"
                    if btn_url not in seen_btn:
                        seen_btn.add(btn_url)
                        debug_log(f"[XYZ] Stream-switcher button: {btn_name} -> {btn_url}", xbmc.LOGINFO)
                        links.append(JetLink(btn_url, name=btn_name, links=True))
                if links:
                    return links

            if not links:
                iframe_matches = re.findall(
                    r'<iframe[^>]+src="([^"]+)"[^>]*>',
                    html,
                    re.IGNORECASE,
                )
                if iframe_matches:
                    seen_iframe = set()
                    for iframe_src in iframe_matches:
                        iframe_src = iframe_src.replace("&amp;", "&")
                        # Skip JS template placeholders like ${stream.source}
                        # embedded in player source, not real iframe targets.
                        if "${" in iframe_src or "}" in iframe_src:
                            continue
                        if iframe_src.startswith("//"):
                            iframe_src = "https:" + iframe_src
                        elif iframe_src.startswith("/"):
                            iframe_src = self.base_url + iframe_src
                        if not iframe_src.startswith("http"):
                            continue
                        if iframe_src in seen_iframe:
                            continue
                        seen_iframe.add(iframe_src)
                        iframe_name = "Stream"
                        name_match = re.search(r'<iframe[^>]+src="[^"]*"[^>]*>([^<]*)', html)
                        if name_match and name_match.group(1).strip():
                            iframe_name = name_match.group(1).strip()
                        elif "?" in iframe_src:
                            qs_name = parse_qs(urlparse(iframe_src).query)
                            for v in qs_name.values():
                                if v:
                                    iframe_name = v[0]
                                    break
                        elif "/" in iframe_src:
                            iframe_name = iframe_src.rsplit("/", 1)[-1].replace(".html", "").replace("embed?", "")
                        debug_log(f"[XYZ] Found iframe: {iframe_name} -> {iframe_src}", xbmc.LOGINFO)
                        links.append(JetLink(iframe_src, name=iframe_name, links=True))
                    if links:
                        return links

            stream_urls = []
            m = re.search(r'const\s+streamUrl\s*=\s*["\']([^"\']+)["\']', html)
            if m:
                stream_urls.append(m.group(1))
            m2 = re.search(r'const\s+streamUrl\s*=\s*`([^`]+)`', html)
            if m2:
                stream_urls.append(m2.group(1))
            # source:/file: assignments must reference an actual manifest —
            # loose matching picked up script URLs (e.g. the core-js CDN on
            # taifood pages) and offered GitHub HTML as a "stream".
            stream_urls.extend(
                u
                for u in re.findall(r'(?:source|file)\s*[:=]\s*"(https?://[^"]+)"', html)
                if ".m3u8" in u or ".mpd" in u
            )
            stream_urls.extend(re.findall(r'(https?://[^\s"\'<>]+(?:\.m3u8|\.mpd))', html))

            valid_urls = []
            for u in stream_urls:
                if not (u.startswith("http://") or u.startswith("https://")):
                    continue
                if '$' in u or '{' in u or '}' in u:
                    continue
                if '"' in u or "'" in u or '`' in u:
                    continue
                valid_urls.append(u)

            if not valid_urls:
                name_match = re.search(r'[?&](\w+)=', orig)
                if name_match and ("/embed" in orig or "/embedjw" in orig):
                    embed_link = self._resolve_embed_mono(name_match.group(1))
                    if embed_link:
                        links.append(embed_link)
                        return links
                elif name_match and "/embedserver2" in orig:
                    stream_name = name_match.group(1)
                    valid_urls.append(f"https://iptvstream2.xyzstreams.space/{stream_name}/mono.ts.m3u8")
                else:
                    stream_id_match = re.search(r'[?&]streamid=([^&]+)', orig)
                    pro_id_match = re.search(r'[?&]proid=([^&]+)', orig)
                    if stream_id_match:
                        stream_id = stream_id_match.group(1)
                        pro_id = pro_id_match.group(1) if pro_id_match else "sling"
                        valid_urls.append(
                            f"https://xyzstreams.blog/2/stream/{pro_id}/{stream_id}/stream_0.m3u8"
                        )
                    else:
                        iptv_match = re.search(r'iptvstream(?:2)?\.xyzstreams\.space/([^"\'<>`\s]+)', html)
                        if not iptv_match:
                            iptv_match = re.search(r'iptvstream\.dlhd\.net/([^"\'<>`\s]+)', html)
                        if iptv_match:
                            valid_urls.append(f"https://{iptv_match.group(1)}")
                        else:
                            alt_name_match = re.search(r'[?&](\w+)=', orig)
                            if alt_name_match and ("/embed" in orig or "/embedjw" in orig):
                                embed_link = self._resolve_embed_mono(alt_name_match.group(1))
                                if embed_link:
                                    links.append(embed_link)
                                    return links

            seen = set()
            for m3u8 in valid_urls:
                if m3u8 in seen:
                    continue
                seen.add(m3u8)
                debug_log(f"[XYZ] Found stream: {m3u8}", xbmc.LOGINFO)
                slug_match = re.search(r'[?&]stream_id=([^&]+)', m3u8)
                if slug_match:
                    slug = slug_match.group(1)
                else:
                    path_match = re.search(r'/([^/]+)/stream_0\.m3u8', m3u8)
                    slug = path_match.group(1) if path_match else "Stream"

                # For 247 streams, proxy the master playlist directly so ISA
                # can select both a video variant AND the audio rendition.
                # Splitting into individual variants drops #EXT-X-MEDIA audio
                # tags, resulting in video-only playback with no audio.
                if "xyzstreams.blog" in urlparse(m3u8).netloc:
                    proxy_url = self._build_proxy_link(m3u8, dict(self.stream_headers))
                    license_key = _extract_clearkey(
                        m3u8, dict(self.stream_headers), self.timeout
                    )
                    if license_key:
                        debug_log(f"[XYZ] Using ClearKey for {slug}", xbmc.LOGINFO)
                        inputstream = JetInputstreamAdaptive(
                            manifest_type="hls",
                            license_type="org.w3.clearkey",
                            license_key=license_key,
                        )
                    else:
                        inputstream = JetInputstreamAdaptive(manifest_type="hls")
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=slug,
                            headers=dict(self.stream_headers),
                            inputstream=inputstream,
                            resolveurl=False,
                        )
                    )
                    continue

                proxy_url = self._build_proxy_link(m3u8, dict(self.stream_headers))

                # The 247.xyzstreams proxies serve DRM-wrapped HLS/DASH.
                # InputStream Adaptive with the manifest's ClearKey is required.
                if "xyzstreams.blog" in urlparse(m3u8).netloc:
                    license_key = _extract_clearkey(
                        m3u8, dict(self.stream_headers), self.timeout
                    )
                    if license_key:
                        debug_log(f"[XYZ] Using ClearKey for {slug}", xbmc.LOGINFO)
                        inputstream = JetInputstreamAdaptive(
                            manifest_type="hls",
                            license_type="org.w3.clearkey",
                            license_key=license_key,
                        )
                    else:
                        inputstream = JetInputstreamAdaptive(manifest_type="hls")
                else:
                    inputstream = JetInputstreamAdaptive(manifest_type="hls")

                links.append(
                    JetLink(
                        address=proxy_url,
                        name=slug,
                        headers=dict(self.stream_headers),
                        inputstream=inputstream,
                        resolveurl=False,
                    )
                )
            if not links:
                for display_name, sub_href in self._parse_schedule_rows(html):
                    href_abs = self.base_url + sub_href if sub_href.startswith("/") else sub_href
                    # Link the sub-page: it holds the authoritative player
                    # target (iframe /embed?CW, /embedserver2?event*, stream
                    # buttons). The badge text is NOT the server slug.
                    debug_log(f"[XYZ] Schedule sub-page: {display_name} -> {href_abs}", xbmc.LOGINFO)
                    links.append(JetLink(href_abs, name=display_name, links=True))
                if links:
                    return links

                debug_log("[XYZ] No streams found in embed page", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[XYZ] Error in get_links: {e}", xbmc.LOGERROR)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        debug_log(f"[XYZ] get_link called for: {url.address}", xbmc.LOGINFO)
        if "127.0.0.1" in url.address and "/xyz/" in url.address:
            return JetLink(
                address=url.address,
                headers=dict(self.stream_headers),
                inputstream=JetInputstreamFFmpegDirect.default(),
                resolveurl=False,
            )

        parsed_check = urlparse(url.address)
        if parsed_check.path == "/embedserver2" and parsed_check.query:
            mono = self._resolve_embed_mono(parsed_check.query)
            if mono:
                return mono
            referer = url.headers.get("Referer") if url.headers else None
            try:
                from ..util.resolver import UniversalResolver
                resolver = UniversalResolver(self.user_agent, "[XYZ]")
                stream = resolver.resolve_url(url.address, referer)
                if stream:
                    headers = {"User-Agent": self.user_agent, "Referer": resolver.stream_referer or url.address}
                    if resolver.stream_origin:
                        headers["Origin"] = resolver.stream_origin
                    return JetLink(
                        stream,
                        headers=headers,
                        inputstream=JetInputstreamFFmpegDirect.default(),
                    )
            except Exception as e:
                debug_log(f"[XYZ] embedserver2 resolver fallback failed: {e}", xbmc.LOGWARNING)
            return None

        if ".m3u8" in url.address or ".mpd" in url.address:
            proxy_url = self._build_proxy_link(url.address, dict(self.stream_headers))
            if "xyzstreams.blog" in urlparse(url.address).netloc:
                license_key = _extract_clearkey(
                    url.address, dict(self.stream_headers), self.timeout
                )
                if license_key:
                    inputstream = JetInputstreamAdaptive(
                        manifest_type="hls",
                        license_type="org.w3.clearkey",
                        license_key=license_key,
                    )
                else:
                    inputstream = JetInputstreamAdaptive(manifest_type="hls")
            else:
                inputstream = JetInputstreamAdaptive(manifest_type="hls")
            return JetLink(
                address=proxy_url,
                headers=dict(self.stream_headers),
                inputstream=inputstream,
                resolveurl=False,
            )

        links = self.get_links(url)
        if links:
            return links[0]
        return JetLink(address=url.address)
