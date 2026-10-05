from ..models import JetExtractor, JetExtractorProgress, JetItem, JetLink, JetInputstreamAdaptive, JetInputstreamFFmpegDirect
from typing import Optional, List, Dict
import re
import uuid
import base64
import time
import xbmc
from .._core import get_session
from ..tools import debug_log
from ..util.xyz_proxy import _ensure_xyz_proxy, _XYZ_PROXY
from ..util.timstreams_store import (
    add_channels,
    load_channels,
    get_channel_count,
    is_stale,
    set_last_refresh_ts,
)


class TimStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["timst.top","timst.cfd", "timstreams.xyz", "epiembeds.online"]
        self.name = "TimStreams"
        self.short_name = "TimStreams"
        self.base_url = f"https://{self.domains[0]}"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/149.0.0.0 Safari/537.36"
        )
        self.stream_headers = {
            "User-Agent": self.user_agent,
            "Referer": f"{self.base_url}/",
        }
        self.timeout = 10

    def _genre_map(self, genres_raw) -> Dict[int, str]:
        result = {}
        if not isinstance(genres_raw, list):
            return result
        for g in genres_raw:
            gid = g.get("id")
            name = g.get("name")
            if gid is not None and name:
                result[gid] = name
            for sc in g.get("sub_categories") or []:
                scid = sc.get("id")
                scname = sc.get("name")
                if gid is not None and scid is not None and scname:
                    result[f"{gid}:{scid}"] = scname
        return result

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        session = get_session()
        headers = dict(self.stream_headers)
        headers["Accept"] = "application/json"

        # --- Live events (sports) ---
        try:
            resp = session.get(f"{self.base_url}/api/live-upcoming", timeout=self.timeout, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                genres = self._genre_map(data.get("genres", []))
                for ev in data.get("events", []):
                    title = ev.get("name", "")
                    genre_id = ev.get("genre")
                    sub_genre = ev.get("sub_genre") or ev.get("sub_category") or ev.get("subCategory")
                    league = "Event"
                    if genre_id is not None:
                        if sub_genre is not None:
                            league = genres.get(f"{genre_id}:{sub_genre}") or genres.get(genre_id) or "Event"
                        else:
                            league = genres.get(genre_id, "Event")
                    streams = ev.get("streams") or []
                    if not streams:
                        continue
                    links = []
                    for s in streams:
                        links.append(JetLink(
                            address=s.get("url", ""),
                            name=s.get("name", "Stream"),
                            headers=dict(self.stream_headers),
                            resolveurl=True,
                            extractor=self.short_name,
                        ))
                    items.append(JetItem(
                        title=title,
                        links=links,
                        league=league,
                        icon=ev.get("logo"),
                        status="LIVE" if ev.get("isevent") else None,
                        starttime=self._parse_event_time(ev),
                    ))
            else:
                debug_log(f"[TimStreams] Live events API returned {resp.status_code}", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[TimStreams] Failed to fetch live events: {e}", xbmc.LOGWARNING)

        # --- 24/7 channels ---
        channels_fetched_live = False
        try:
            resp = session.get(f"{self.base_url}/api/channels", timeout=self.timeout, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                genres = self._genre_map(data.get("genres", []))
                store_rows = []
                for ch in data.get("channels", []):
                    title = ch.get("name", "")
                    genre_id = ch.get("genre")
                    league = genres.get(genre_id, "Channel") if genre_id is not None else "Channel"
                    streams = ch.get("streams") or []
                    if not streams:
                        continue
                    links = []
                    for s in streams:
                        sname = s.get("name", "Stream")
                        links.append(JetLink(
                            address=s.get("url", ""),
                            name=sname,
                            headers=dict(self.stream_headers),
                            resolveurl=True,
                            extractor=self.short_name,
                        ))
                        store_rows.append({
                            "name": title,
                            "stream_url": s.get("url", ""),
                            "stream_name": sname,
                            "league": league,
                            "logo": ch.get("logo"),
                        })
                    items.append(JetItem(
                        title=title,
                        links=links,
                        league=league,
                        icon=ch.get("logo"),
                    ))
                channels_fetched_live = True
                if is_stale():
                    try:
                        add_channels(store_rows)
                        set_last_refresh_ts(time.time())
                        debug_log(f"[TimStreams] Saved {len(store_rows)} 24/7 channels to DB", xbmc.LOGINFO)
                    except Exception as e:
                        debug_log(f"[TimStreams] Failed to save 24/7 channels to DB: {e}", xbmc.LOGWARNING)
            else:
                debug_log(f"[TimStreams] Channels API returned {resp.status_code}", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[TimStreams] Failed to fetch channels: {e}", xbmc.LOGWARNING)

        # --- Fallback: load cached 24/7 channels from DB when live fetch failed ---
        if not channels_fetched_live and get_channel_count() > 0:
            try:
                cached = load_channels()
                for ch in cached.get("channels", []):
                    links = []
                    for s in ch.get("streams", []):
                        links.append(JetLink(
                            address=s.get("url", ""),
                            name=s.get("name", "Stream"),
                            headers=dict(self.stream_headers),
                            resolveurl=True,
                            extractor=self.short_name,
                        ))
                    items.append(JetItem(
                        title=ch.get("name", ""),
                        links=links,
                        league=ch.get("league", "24/7 Channels"),
                        icon=ch.get("logo"),
                    ))
            except Exception as e:
                debug_log(f"[TimStreams] Failed to load cached 24/7 channels: {e}", xbmc.LOGWARNING)

        # --- Replays ---
        try:
            resp = session.get(f"{self.base_url}/api/replays", timeout=self.timeout, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for rep in data.get("replays", []):
                    title = rep.get("name", "")
                    streams = rep.get("streams") or []
                    if not streams:
                        continue
                    links = []
                    for s in streams:
                        links.append(JetLink(
                            address=s.get("url", ""),
                            name=s.get("name", "Stream"),
                            headers=dict(self.stream_headers),
                            resolveurl=True,
                            extractor=self.short_name,
                        ))
                    date_str = rep.get("date", "")
                    items.append(JetItem(
                        title=title,
                        links=links,
                        league="Replays",
                        icon=rep.get("logo"),
                        status=f"Ended ({date_str})" if date_str else "Ended",
                    ))
            else:
                debug_log(f"[TimStreams] Replays API returned {resp.status_code}", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[TimStreams] Failed to fetch replays: {e}", xbmc.LOGWARNING)

        return items

    def _parse_event_time(self, ev: dict):
        time_str = ev.get("time") or ev.get("start_time")
        if not time_str:
            return None
        try:
            from datetime import datetime, timezone, timedelta
            dt = datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
        try:
            from datetime import datetime, timezone
            import re as _re
            t = _re.match(r"(\d{4}-\d{2}-\d{2})", time_str)
            if t:
                return datetime.strptime(t.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            pass
        return None

    @staticmethod
    def _decode_obfuscated_js(html: str) -> Optional[str]:
        """Extract the m3u8 stream URL from the embed page's obfuscated JavaScript.

        Handles the XOR cipher format used by epiembeds.online:
            var <arr>=[<nums>],<xor_key>=<N>,<sub_key>=<N>,...;
            for(...;...) { result += String.fromCharCode(((<arr>[i]^<xor_key>)-<sub_key>+256)&255); }
            window.eval(result);

        Also falls back to the old base64 / atob format.
        """
        # --- XOR cipher format (variable names change per stream) ---
        # Try combined format first: var arr=[nums],xor_key=N,sub_key=N
        match = re.search(
            r'(?:var\s+)?\w+\s*=\s*\[([\d,\s]+)\][,\s]*(?:var\s+)?\w+\s*=\s*(\d+)[,\s]*(?:var\s+)?\w+\s*=\s*(\d+)',
            html,
        )
        if match:
            nums = [int(x.strip()) for x in match.group(1).split(",") if x.strip()]
            xor_key = int(match.group(2))
            sub_key = int(match.group(3))
            decoded = ""
            for byte in nums:
                decoded += chr(((byte ^ xor_key) - sub_key + 256) & 255)
            url_match = re.search(r'file\s*[:=]\s*"([^"]+\.m3u8[^"]*)"', decoded)
            if not url_match:
                url_match = re.search(r'file\s*[:=]\s*"([^"]+)"', decoded)
            if not url_match:
                url_match = re.search(r'(https?://[^\s"\'<>]+)', decoded)
            if url_match:
                return url_match.group(1)

        # --- Separate var statements fallback ---
        # Some pages use: var arr=[...]; var xor_key=N; var sub_key=N;
        arr_match = re.search(r'\w+\s*=\s*\[([\d,\s]+)\]', html)
        if arr_match:
            nums_str = arr_match.group(1)
            nums = [int(x.strip()) for x in nums_str.split(",") if x.strip()]
            if nums and len(nums) > 10:
                key_matches = re.findall(r'\w+\s*=\s*(\d+)\s*;', html)
                if len(key_matches) >= 2:
                    for xor_val in key_matches:
                        for sub_val in key_matches:
                            if xor_val == sub_val:
                                continue
                            decoded = ""
                            for byte in nums:
                                decoded += chr(((byte ^ int(xor_val)) - int(sub_val) + 256) & 255)
                            url_match = re.search(r'(https?://[^\s"\'<>]+)', decoded)
                            if url_match:
                                return url_match.group(1)

        # --- Old base64 / atob format ---
        match = re.search(r"eval\(atob\('([^']+)'\)", html)
        if match:
            try:
                decoded_js = base64.b64decode(match.group(1)).decode("utf-8")
                url_match = re.search(r'const initUrl\s*=\s*"([^"]+)"', decoded_js)
                if url_match:
                    return url_match.group(1)
                url_match = re.search(r'file\s*[:=]\s*"([^"]+)"', decoded_js)
                if url_match:
                    return url_match.group(1)
            except Exception:
                pass

        # --- Direct m3u8 / source fallback ---
        # Some embed pages may have the URL directly in the HTML
        url_match = re.search(r'source\s*:\s*"([^"]+\.m3u8[^"]*)"', html)
        if url_match:
            return url_match.group(1)
        url_match = re.search(r'file\s*[:=]\s*"([^"]+\.m3u8[^"]*)"', html)
        if url_match:
            return url_match.group(1)
        url_match = re.search(r'(https?://[^\s"\'<>)]+\.m3u8[^\s"\'<>)]*)', html)
        if url_match:
            return url_match.group(1)

        return None

    @staticmethod
    def _build_proxy_link(upstream_url: str, headers: dict) -> str:
        """Register an upstream m3u8 with the XYZ proxy and return a local proxy URL.

        The proxy rewrites segment URLs to local endpoints and strips RIFF/WebP
        and PNG wrappers from TikTok CDN segments so ISA can play them as raw TS.
        """
        port = _ensure_xyz_proxy()
        token = uuid.uuid4().hex
        _XYZ_PROXY["upstream"][token] = {
            "url": upstream_url,
            "headers": headers or {},
            "cache": None,
            "cache_time": 0.0,
            "session": get_session(),
            "license_key": None,
        }
        proxy_url = f"http://127.0.0.1:{port}/xyz/{token}.m3u8"
        debug_log(f"[TimStreams] Proxy registered: {proxy_url} -> {upstream_url}", xbmc.LOGINFO)
        return proxy_url

    def get_link(self, url: JetLink) -> Optional[JetLink]:
        if not url or not url.address:
            return None

        # Return proxy URLs directly (player requests resolution of a proxy URL)
        if "127.0.0.1" in url.address and "/xyz/" in url.address:
            return JetLink(
                address=url.address,
                headers=dict(self.stream_headers),
                inputstream=JetInputstreamFFmpegDirect.default(),
                resolveurl=False,
            )

        # Resolve embed page -> m3u8 URL
        address = url.address
        if address.startswith("/"):
            address = f"{self.base_url}{address}"

        try:
            session = get_session()
            html = session.get(address, headers=dict(self.stream_headers), timeout=self.timeout).text
        except Exception as e:
            debug_log(f"[TimStreams] Failed to fetch embed page: {e}", xbmc.LOGWARNING)
            xbmc.log(f"[TimStreams] Failed to fetch embed page: {e}", xbmc.LOGWARNING)
            return None

        try:
            stream_url = self._decode_obfuscated_js(html)
        except Exception as e:
            debug_log(f"[TimStreams] Exception during JS decode: {e}", xbmc.LOGWARNING)
            xbmc.log(f"[TimStreams] Exception during JS decode: {e}", xbmc.LOGWARNING)
            return None

        if not stream_url:
            debug_log("[TimStreams] Could not decode stream URL from embed page", xbmc.LOGWARNING)
            xbmc.log("[TimStreams] Could not decode stream URL from embed page", xbmc.LOGWARNING)
            return None

        debug_log(f"[TimStreams] Resolved m3u8: {stream_url}", xbmc.LOGINFO)
        xbmc.log(f"[TimStreams] Resolved m3u8: {stream_url}", xbmc.LOGINFO)

        # Build upstream headers with correct Referer/Origin for the stream domain
        upstream_headers = dict(self.stream_headers)
        try:
            from urllib.parse import urlparse
            embed_domain = urlparse(address).netloc
            upstream_headers["Referer"] = f"https://{embed_domain}/"
            upstream_headers["Origin"] = f"https://{embed_domain}"
        except Exception:
            pass

        # Proxy through XYZ proxy so RIFF/WebP-wrapped TikTok CDN segments are stripped
        try:
            proxy_url = self._build_proxy_link(stream_url, upstream_headers)
        except Exception as e:
            debug_log(f"[TimStreams] XYZ proxy failed, falling back to direct playback: {e}", xbmc.LOGWARNING)
            xbmc.log(f"[TimStreams] XYZ proxy failed, falling back to direct playback: {e}", xbmc.LOGWARNING)
            return JetLink(
                address=stream_url,
                headers=upstream_headers,
                inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                resolveurl=False,
            )

        return JetLink(
            address=proxy_url,
            headers=upstream_headers,
            inputstream=JetInputstreamAdaptive(manifest_type="hls"),
            resolveurl=False,
        )
