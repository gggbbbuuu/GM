from ..models import *
from typing import Optional, List, Tuple, Dict
import re
import json
import time
import uuid
import requests
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, quote

from ..tools import debug_log
from .._core import get_session
import xbmc
from ..util import embedsportstop
from ..util.stream_proxy import get_stream_proxy
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
        self.alt_streams_api = "https://api.ppv.st/api/streams"

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

    def _build_proxy_link(self, upstream_url: str, headers: dict) -> str:
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
            "session": requests.Session(),
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
                        embed_url = f"{self.base_url}/247.html?streamid={stream_id}&proid=sling"
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
                    embed_url_abs = f"{self.base_url}/247.html?streamid={stream_id}&proid=sling"
                    debug_log(f"[XYZ] Constructed embed URL for {name}: {embed_url_abs}", xbmc.LOGDEBUG)
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
                            qs = parse_qs(urlparse(embed_url).query)
                            stream_id = qs.get("stream_id", [""])[0]
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

    def _fetch_alt_streams(self) -> List[JetItem]:
        items: List[JetItem] = []
        try:
            headers = dict(self.stream_headers)
            headers.update({
                "Accept": "application/json",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/alt",
            })
            resp = get_session().get(
                self.alt_streams_api,
                timeout=self.timeout,
                headers=headers,
            )
            if resp.status_code != 200:
                debug_log(f"[XYZ] Alt streams API returned {resp.status_code}", xbmc.LOGWARNING)
                return items
            data = resp.json()
            if not isinstance(data, dict) or not data.get("success"):
                return items
            categories = data.get("streams", [])
            if not isinstance(categories, list):
                return items
            now = time.time()
            for category in categories:
                if not isinstance(category, dict):
                    continue
                category_name = str(category.get("category") or "Sports").strip()
                streams = category.get("streams", [])
                if not isinstance(streams, list):
                    continue
                for stream in streams:
                    if not isinstance(stream, dict):
                        continue
                    title = str(stream.get("name") or "Stream").strip()
                    iframe = stream.get("iframe")
                    if not title or not isinstance(iframe, str) or not iframe.startswith(("http://", "https://")):
                        continue
                    resolver_url = f"{self.base_url}/jetextractor/alt?url={quote(iframe, safe='')}"
                    links = [JetLink(resolver_url, name=str(stream.get("tag") or "Main"), links=True)]
                    substreams = stream.get("substreams", [])
                    if isinstance(substreams, list):
                        for substream in substreams:
                            if not isinstance(substream, dict):
                                continue
                            sub_iframe = substream.get("iframe")
                            if isinstance(sub_iframe, str) and sub_iframe.startswith(("http://", "https://")):
                                links.append(
                                    JetLink(
                                        f"{self.base_url}/jetextractor/alt?url={quote(sub_iframe, safe='')}",
                                        name=str(substream.get("tag") or substream.get("name") or "Alternate"),
                                        links=True,
                                    )
                                )
                    starts_at = stream.get("starts_at")
                    ends_at = stream.get("ends_at")
                    always_live = bool(stream.get("always_live") or category.get("always_live"))
                    status = "LIVE" if always_live else None
                    if not always_live and isinstance(starts_at, (int, float)):
                        if now < starts_at:
                            status = "Upcoming"
                        elif isinstance(ends_at, (int, float)) and now > ends_at:
                            status = "Ended"
                        else:
                            status = "LIVE"
                    items.append(
                        JetItem(
                            title=title,
                            league=self._guess_league(title, category_name),
                            links=links,
                            status=status,
                            icon=stream.get("poster"),
                        )
                    )
        except Exception as e:
            debug_log(f"[XYZ] Alt streams fetch failed: {e}", xbmc.LOGWARNING)
        return items

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
        
        if any(x in t for x in ["espn+", "espn plus"]):
            return "ESPN+"
        return "Sports"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        homepage_items, channel_items = self._fetch_homepage_data()
        alt_items = self._fetch_alt_streams()
        espn_items = self._fetch_espn_items()
        mlb_items = self._fetch_mlb_games()
        wnba_items = self._fetch_wnba_games()
        fubo_items = self._build_fubo_items()
        items.extend(homepage_items)
        items.extend(channel_items)
        items.extend(alt_items)
        items.extend(espn_items)
        items.extend(mlb_items)
        items.extend(wnba_items)
        items.extend(fubo_items)

        for alt in alt_items:
            alt_title_clean = re.sub(r'\[.*?\]\s*', '', alt.title).strip().lower()
            for event in homepage_items:
                event_title_clean = re.sub(r'\[.*?\]\s*', '', event.title).strip().lower()
                if alt_title_clean and event_title_clean and alt_title_clean == event_title_clean:
                    existing_addrs = {l.address for l in alt.links if hasattr(l, 'address')}
                    for link in event.links:
                        if hasattr(link, 'address') and link.links and link.address not in existing_addrs:
                            alt.links.append(JetLink(
                                address=link.address,
                                name="Event Page",
                                links=True,
                            ))
                            debug_log(f"[XYZ] Added event page link to alt item: {alt.title} -> {link.address}", xbmc.LOGINFO)
                    break

        for ch in channel_items:
            link_addrs = [l.address for l in ch.links if hasattr(l, "address")]
            debug_log(f"[XYZ] Channel: {ch.title} -> {link_addrs}", xbmc.LOGINFO)
        for alt in alt_items:
            link_addrs = [l.address for l in alt.links if hasattr(l, "address")]
            debug_log(f"[XYZ] Alt: {alt.title} -> {link_addrs}", xbmc.LOGINFO)
        debug_log(f"[XYZ] Total items: {len(items)} (Events={len(homepage_items)}, Channels={len(channel_items)}, Alt={len(alt_items)}, ESPN={len(espn_items)}, MLB={len(mlb_items)}, WNBA={len(wnba_items)}, Fubo={len(fubo_items)})", xbmc.LOGINFO)
        return items

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
            iframe_urls = parse_qs(parsed_url.query).get("url", [])
            if not iframe_urls:
                return links
            embed_url = iframe_urls[0]
        else:
            embed_url = url.address

        if "embedindia" in urlparse(embed_url).netloc:
            try:
                stream_url = embedsportstop.get_embedsportstop_stream(embed_url)
                if stream_url:
                    embed_origin = f"{urlparse(embed_url).scheme}://{urlparse(embed_url).netloc}"
                    headers = {
                        "Origin": embed_origin,
                        "Referer": f"{embed_origin}/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
                        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": '"Windows"',
                        "Accept": "*/*",
                    }
                    debug_log(f"[XYZ] Resolved embedindia stream URL: {stream_url}", xbmc.LOGINFO)
                    proxy = get_stream_proxy(
                        "xyz_alt",
                        headers,
                        options={
                            "strip_png": True,
                            "manifest_png_to_ts": True,
                            "proxy_absolute_urls": True,
                            "cache_manifest": False,
                            "add_icy_metadata": False,
                            "browser_tls": True,
                        },
                    )
                    proxy_url = proxy.get_proxy_url(stream_url, headers)
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=url.name or "Stream",
                            inputstream=JetInputstreamAdaptive(
                                manifest_type="hls",
                                manifest_headers=headers,
                            ),
                            resolveurl=False,
                        )
                    )
            except Exception as e:
                debug_log(f"[XYZ] EmbedIndia resolution failed: {e}", xbmc.LOGWARNING)
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

        parsed_embed = urlparse(url.address)
        if parsed_embed.path in ("/embed", "/embedjw") and parsed_embed.query:
            stream_name = parsed_embed.query
            iptv_url = f"https://iptvstream.dlhd.net/{stream_name}/mono.ts.m3u8"
            debug_log(f"[XYZ] Constructed direct URL: {iptv_url}", xbmc.LOGINFO)
            proxy_url = self._build_proxy_link(iptv_url, dict(self.stream_headers))
            links.append(
                JetLink(
                    address=proxy_url,
                    name=stream_name,
                    headers=dict(self.stream_headers),
                    inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                    resolveurl=False,
                )
            )
            return links

        if parsed_embed.path == "/embedserver2" and parsed_embed.query:
            stream_name = parsed_embed.query
            iptv_url = f"https://iptvstream2.xyzstreams.space/{stream_name}/mono.ts.m3u8"
            debug_log(f"[XYZ] Constructed embedserver2 URL: {iptv_url}", xbmc.LOGINFO)
            proxy_url = self._build_proxy_link(iptv_url, dict(self.stream_headers))
            links.append(
                JetLink(
                    address=proxy_url,
                    name=stream_name,
                    headers=dict(self.stream_headers),
                    inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                    resolveurl=False,
                )
            )
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
            headers = dict(self.stream_headers)
            resp = get_session().get(url.address, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                debug_log(f"[XYZ] Embed page returned {resp.status_code}", xbmc.LOGWARNING)
                return links

            html = resp.text

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
            stream_urls.extend(re.findall(r'source\s*[:=]\s*"(https?://[^"]+)"', html))
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
                name_match = re.search(r'[?&](\w+)=', url.address)
                if name_match and ("/embed" in url.address or "/embedjw" in url.address):
                    stream_name = name_match.group(1)
                    valid_urls.append(f"https://iptvstream.dlhd.net/{stream_name}/mono.ts.m3u8")
                elif name_match and "/embedserver2" in url.address:
                    stream_name = name_match.group(1)
                    valid_urls.append(f"https://iptvstream2.xyzstreams.space/{stream_name}/mono.ts.m3u8")
                else:
                    stream_id_match = re.search(r'[?&]streamid=([^&]+)', url.address)
                    pro_id_match = re.search(r'[?&]proid=([^&]+)', url.address)
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
                            alt_name_match = re.search(r'[?&](\w+)=', url.address)
                            if alt_name_match:
                                valid_urls.append(f"https://iptvstream.dlhd.net/{alt_name_match.group(1)}/mono.ts.m3u8")

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
                    slug = path_match.group(1) if path_match else slug

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
                sub_page_links = re.findall(
                    r'<a\s+href="(/[^"]+\.html)"[^>]*>\s*<li[^>]*class="text247"[^>]*>(.*?)</li>',
                    html,
                    re.DOTALL,
                )
                if not sub_page_links:
                    sub_page_links = re.findall(
                        r'<a\s+href="(/[^"]+\.html)"[^>]*>',
                        html,
                    )
                    sub_page_links = [(href, "") for href in sub_page_links]

                if sub_page_links:
                    seen_sub = set()
                    for match in sub_page_links:
                        if isinstance(match, tuple):
                            href, inner_html = match
                        else:
                            href, inner_html = match, ""
                        if href in seen_sub:
                            continue
                        seen_sub.add(href)
                        href_abs = self.base_url + href if href.startswith("/") else href
                        title_match = re.search(r'class="game-title"[^>]*>(.*?)</div>', inner_html, re.DOTALL)
                        if title_match:
                            game_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                        else:
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

                        if game_badge and " / " in game_badge:
                            network_key = game_badge.split(" / ")[0].strip()
                        elif game_badge:
                            network_key = game_badge.strip()
                        else:
                            network_key = ""

                        if network_key:
                            embed_url = f"{self.base_url}/embed?{network_key}"
                            debug_log(f"[XYZ] Schedule direct stream: {display_name} -> {embed_url}", xbmc.LOGINFO)
                            links.append(JetLink(embed_url, name=display_name, links=True))
                        else:
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
