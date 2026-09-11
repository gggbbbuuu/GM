import re
import time
import uuid
import xbmc
import requests
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

from ..models import *
from ..tools import debug_log
from .._core import get_session
from ..util.xyz_helpers import _parse_iso_duration
from ..util.xyz_proxy import _ensure_xyz_proxy, _XYZ_PROXY, _parse_variant_qualities


class ESPN(JetExtractor):
    domains = ["espn.dlhd.net"]
    name = "ESPN+"
    short_name = "ESPN+"

    def __init__(self) -> None:
        self.base_url = "https://espn.fancy-shark151.workers.dev"
        self.stream_headers = {
            "Origin": "https://xyzstreams.st",
            "Referer": "https://xyzstreams.st/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            )
        }
        self.stream_headers2 = {
            "Referer": "https://xyzstreams.st/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            )}

    def _guess_league(self, name: str) -> str:
        t = name.lower()
        if any(x in t for x in ["mlb", "baseball", "brewers", "padres", "rangers", "angels", "yankees", "mariners", "cardinals", "cubs", "tigers", "pirates"]):
            return "MLB"
        if any(x in t for x in ["nfl", "football", "preseason", "colts", "patriots", "broncos", "falcons", "packers", "steelers"]):
            return "NFL"
        if any(x in t for x in ["wnba", "liberty", "fever", "dream", "mercury", "spirit"]):
            return "WNBA"
        if any(x in t for x in ["pga", "golf", "championship"]):
            return "Golf"
        if any(x in t for x in ["wsl", "surfing"]):
            return "Surfing"
        if any(x in t for x in ["little league"]):
            return "Baseball"
        if any(x in t for x in ["soccer", "futbol", "angel city"]):
            return "Soccer"
        if any(x in t for x in ["wrestling", "summerslam"]):
            return "Wrestling"
        return "ESPN+"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        try:
            headers = {
                "Accept": "application/json",
                "User-Agent": self.stream_headers["User-Agent"],
            }
            resp = get_session().get(self.base_url, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                debug_log(f"[ESPN] API returned {resp.status_code}", xbmc.LOGWARNING)
                return items
            data = resp.json()
            if not isinstance(data, dict):
                return items
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
                start_ts = self._parse_iso(start_time)
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
                league = self._guess_league(name)
                icon = entry.get("thumbnailUrl", "")
                items.append(
                    JetItem(
                        title=title,
                        league=f"ESPN+{league}",
                        links=[JetLink(content_url, links=True)],
                        icon=icon if icon else None,
                    )
                )
                debug_log(f"[ESPN] Item: {title} -> {content_url}", xbmc.LOGDEBUG)
            debug_log(f"[ESPN] Fetched {len(items)} events from API", xbmc.LOGINFO)
        except Exception as e:
            debug_log(f"[ESPN] API fetch failed: {e}", xbmc.LOGWARNING)
        return items

    def _parse_iso(self, ts: str) -> Optional[float]:
        try:
            ts = ts.replace("Z", "+00:00")
            from datetime import datetime
            dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception:
            return None

    def get_links(self, url: JetLink) -> List[JetLink]:
        links: List[JetLink] = []
        parsed = urlparse(url.address)
        stream_id = parse_qs(parsed.query).get("id", [None])[0]
        if not stream_id:
            stream_id_match = re.search(r"[?&]id=([^&]+)", url.address)
            if stream_id_match:
                stream_id = stream_id_match.group(1)
        if stream_id:
            stream_url = f"https://xyzstreams.blog/2/stream/espn/{stream_id}/stream_0.m3u8"
            qualities = _parse_variant_qualities(stream_url, dict(self.stream_headers))
            if qualities:
                for name, variant_url, bw in qualities:
                    proxy_url = _build_espn_proxy(variant_url, self.stream_headers)
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=f"{stream_id} - {name}",
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                            resolveurl=False,
                        )
                    )
                return links
            proxy_url = _build_espn_proxy(stream_url, self.stream_headers)
            links.append(
                JetLink(
                    address=proxy_url,
                    name=stream_id,
                    headers=dict(self.stream_headers),
                    inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                    resolveurl=False,
                )
            )
            return links
        try:
            resp = get_session().get(url.address, timeout=self.timeout, headers=dict(self.stream_headers))
            if resp.status_code != 200:
                return links
            html = resp.text
            iframe_match = re.search(r'iframe[^>]+src="([^"]+247[^"]+)"', html)
            if iframe_match:
                iframe_src = iframe_match.group(1)
                if iframe_src.startswith("//"):
                    iframe_src = "https:" + iframe_src
                sid = re.search(r"streamid=([^&]+)", iframe_src)
                pid = re.search(r"proid=([^&]+)", iframe_src)
                if sid:
                    stream_id = sid.group(1)
                    pro_id = pid.group(1) if pid else "espn"
                    stream_url = f"https://xyzstreams.blog/2/stream/{pro_id}/{stream_id}/stream_0.m3u8"
                    proxy_url = _build_espn_proxy(stream_url, self.stream_headers)
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=stream_id,
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                            resolveurl=False,
                        )
                    )
        except Exception as e:
            debug_log(f"[ESPN] get_links failed: {e}", xbmc.LOGWARNING)
        return links


def _build_espn_proxy(upstream_url: str, headers: dict) -> str:
    port = _ensure_xyz_proxy()
    token = uuid.uuid4().hex
    _XYZ_PROXY["upstream"][token] = {
        "url": upstream_url,
        "headers": headers or {},
        "cache": None,
        "cache_time": 0.0,
        "session": requests.Session(),
        "license_key": None,
    }
    return f"http://127.0.0.1:{port}/xyz/{token}.m3u8"
