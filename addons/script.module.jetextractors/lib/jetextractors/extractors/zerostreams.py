from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
from .._core import get_headers, get_session, find_m3u8, find_iframes, make_link, fetch_page
from ..util.stream_proxy import get_stream_proxy
import json
import re
import xbmc
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse

# Player pages hide the signed m3u8 behind an eval'd char-code array:
#   var _ov6=[231,201,...],_bm6=186,_vf8=83,_bn5="",_wh1;
#   ... String.fromCharCode(((_ov6[_wh1]^_bm6)-_vf8+256)%256) ...
# The parameters must be read from that same statement: scanning the whole page
# for "%<n>" or "_(...)" picks up CSS like "width: 100% !important".
_OBF_ARRAY = re.compile(
    r'var\s+(\w+)\s*=\s*\[([\d,\s]+)\]\s*,\s*(\w+)\s*=\s*(\d+)\s*,\s*(\w+)\s*=\s*(\d+)'
)
_OBF_FROMCHARCODE = re.compile(
    r'String\.fromCharCode\(\s*\(?\s*\(?\s*\w+\s*\[\s*\w+\s*\]\s*\^\s*(\w+)\s*\)\s*-\s*(\w+)'
    r'(?:\s*\+\s*(\d+)\s*\)?)?\s*%\s*(\d+)'
)

_AD_IFRAME = re.compile(
    r'(getbanner|ad\.html|doubleclick|googlesyndication|adskeeper|ad4|live_chat|ads\.'
    r'|histats|plausible|wiveophis|disable-devtool|googletagmanager|cloudfront\.net/.*\.html)',
    re.IGNORECASE,
)


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    good = sum(1 for c in text if c in "\t\r\n" or 32 <= ord(c) < 127)
    return good / len(text)


def _decode_obfuscated_arrays(html: str) -> List[str]:
    """Decode every `window.eval(String.fromCharCode((c^key)-sub+add)%mod)` payload.

    Pages can carry more than one array, so all plausible results are returned
    (most-printable first) instead of only the first one that decodes cleanly.
    """
    results: List[Tuple[str, float]] = []

    for arr in _OBF_ARRAY.finditer(html):
        try:
            values = [int(v) for v in arr.group(2).split(',') if v.strip()]
        except ValueError:
            continue
        if not values:
            continue

        key_name, sub_name = arr.group(3), arr.group(5)
        try:
            key = int(arr.group(4))
            sub = int(arr.group(6))
        except ValueError:
            continue
        add, mod = 256, 256

        fc = _OBF_FROMCHARCODE.search(html)
        if fc and fc.group(1) == key_name and fc.group(2) == sub_name:
            if fc.group(3):
                add = int(fc.group(3))
            mod = int(fc.group(4)) or 256

        if mod <= 0:
            continue

        try:
            decoded = ''.join(chr(((v ^ key) - sub + add) % mod) for v in values)
        except Exception as e:
            xbmc.log(f"[ZeroStreams] _decode exception: {e}", xbmc.LOGERROR)
            continue

        ratio = _printable_ratio(decoded)
        if ratio > 0.8:
            results.append((decoded, ratio))

    results.sort(key=lambda item: item[1], reverse=True)
    return [text for text, _ in results]


def _decode_obfuscated_array(html: str) -> Optional[str]:
    decoded = _decode_obfuscated_arrays(html)
    return decoded[0] if decoded else None


def _extract_signed_url(html: str) -> Optional[str]:
    def scan(text: str) -> Optional[str]:
        url_match = re.search(r'(?:SIGNED_URL|signed_url)\s*=\s*["\']([^"\']+)["\']', text, re.I)
        if url_match and url_match.group(1).startswith('http'):
            return url_match.group(1)
        m3u8_match = re.search(r'["\']([^"\']*\.m3u8[^"\']*)["\']', text, re.I)
        if m3u8_match and m3u8_match.group(1).startswith('http'):
            return m3u8_match.group(1)
        return None

    found = scan(html)
    if found:
        return found

    for decoded_js in _decode_obfuscated_arrays(html):
        found = scan(decoded_js)
        if found:
            return found
    return None


class ZeroStreams(JetExtractor):
    site_url = "https://flyembed.click"

    def __init__(self) -> None:
        self.domains = ["flyembed.click", "www.flyembed.click", "epiembeds.online", "www.epiembeds.online", "zero-streams.online", "www.zero-streams.online"]
        self.domains_regex = False
        self.name = "ZeroStreams"
        self.short_name = "ZS"
        # flyembed2.json is what flyembed.click actually renders today; the older
        # flyembed.json is kept as a fallback but it can serve stale dates.
        self.api_urls = [
            "https://ovogoal.cyou/api/v2/flyembed2.json",
            "https://ovogoal.cyou/api/v2/flyembed.json",
        ]
        self.api_url = self.api_urls[0]

    def _make_proxy_link(self, url: str, origin: str) -> JetLink:
        headers = {
            "User-Agent": self.user_agent,
            "Referer": origin,
            "Origin": origin,
        }
        proxy = get_stream_proxy(
            "zerostreams",
            headers,
            options={
                "strip_png": True,
                "manifest_png_to_ts": True,
                "fetch_png_segments": True,
                "segment_strip_origin": True,
                "keep_alive": False,
            },
        )
        proxy_url = proxy.get_proxy_url(url, headers)
        return JetLink(
            proxy_url,
            headers=headers,
            inputstream=JetInputstreamFFmpegDirect.default(),
        )

    def _fetch_schedule(self) -> List[dict]:
        for api_url in self.api_urls:
            try:
                raw = fetch_page(api_url, referer=self.site_url)
                if not raw:
                    xbmc.log(f"[ZeroStreams] Empty response from {api_url}", xbmc.LOGWARNING)
                    continue
                data = json.loads(raw)
                if isinstance(data, list) and data:
                    xbmc.log(f"[ZeroStreams] Schedule from {api_url}: {len(data)} events", xbmc.LOGINFO)
                    return data
                xbmc.log(f"[ZeroStreams] Unexpected payload from {api_url}", xbmc.LOGWARNING)
            except Exception as e:
                xbmc.log(f"[ZeroStreams] Error fetching {api_url}: {e}", xbmc.LOGERROR)
        return []

    @staticmethod
    def _clean(value) -> str:
        if not isinstance(value, str):
            return ""
        return re.sub(r'\s+', ' ', value).strip()

    def _event_fields(self, event: dict) -> dict:
        """Normalize both schedule schemas (flyembed2.json and the old flyembed.json)."""
        team1 = self._clean(event.get("Team1") or event.get("Team 1 ") or event.get("Team1Name"))
        team2 = self._clean(event.get("Team2") or event.get("Team 2") or event.get("Team2Name"))
        league = self._clean(event.get("League"))
        sport = self._clean(event.get("Sport"))
        iframe_url = self._clean(event.get("IframeURL") or event.get("iframeURL"))
        date_str = self._clean(event.get("MatchDate") or event.get("Date"))
        time_str = self._clean(event.get("MatchStartTime") or event.get("Time"))
        end_str = self._clean(event.get("MatchEndTime"))
        return {
            "team1": team1,
            "team2": team2,
            "league": league or sport,
            "sport": sport,
            "iframe": iframe_url,
            "date": date_str,
            "time": time_str,
            "end": end_str,
            "icon": self._clean(event.get("Team1Logo") or event.get("Leaguelogo") or event.get("LeagueLogo")),
        }

    def _event_times(self, fields: dict) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Return naive (start, end) datetimes; times are as shown on the site."""
        start = None
        date_str = fields.get("date") or ""
        time_str = (fields.get("time") or "").split()[0] if fields.get("time") else ""

        candidates = []
        if date_str and time_str:
            candidates.append(("%Y-%m-%d %H:%M", f"{date_str} {time_str}"))
            candidates.append(("%d %B,%Y %H:%M", f"{date_str} {time_str}"))
            candidates.append(("%B %d, %Y %H:%M", f"{date_str} {time_str}"))
        elif time_str:
            candidates.append(("%H:%M", time_str))

        for fmt, value in candidates:
            try:
                start = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue

        if start is None:
            return None, None

        end = None
        end_str = (fields.get("end") or "").split()[0] if fields.get("end") else ""
        if end_str:
            for fmt, value in (
                ("%Y-%m-%d %H:%M", f"{start.strftime('%Y-%m-%d')} {end_str}"),
                ("%H:%M", end_str),
            ):
                try:
                    end = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue

        if end is None:
            end = start + timedelta(hours=2)
        elif end <= start:
            end += timedelta(days=1)
        return start, end

    def _build_item(self, fields: dict) -> Optional[JetItem]:
        team1, team2, iframe_url = fields["team1"], fields["team2"], fields["iframe"]
        if not team1 or not team2 or not iframe_url:
            return None

        start, end = self._event_times(fields)
        status = "Upcoming"
        if start and end:
            now = datetime.now()
            if now >= end:
                return None
            if now >= start - timedelta(minutes=5):
                status = "LIVE"

        title = f"{team1} vs {team2}"
        if start:
            title = f"{title} ({start.strftime('%m-%d %H:%M')})"
        if status == "LIVE":
            title = f"[LIVE] {title}"

        return JetItem(
            title=title,
            links=[JetLink(iframe_url, links=True)],
            starttime=start,
            status=status,
            league=fields.get("league") or None,
            icon=fields.get("icon") or None,
        )

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        try:
            if progress:
                self.progress_update(progress, "Fetching schedule...")

            events = self._fetch_schedule()
            if not events:
                xbmc.log("[ZeroStreams] No schedule data available", xbmc.LOGERROR)
                return items

            seen = set()
            ended = 0
            for event in events:
                try:
                    item = self._build_item(self._event_fields(event))
                except Exception as e:
                    xbmc.log(f"[ZeroStreams] Error parsing event: {e}", xbmc.LOGERROR)
                    continue
                if item is None:
                    ended += 1
                    continue
                key = item.links[0].address
                if key in seen:
                    continue
                seen.add(key)
                items.append(item)

            # live and upcoming first, earliest start first
            items.sort(key=lambda i: (i.status != "LIVE", i.starttime or datetime.max))

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error building items: {e}", xbmc.LOGERROR)

        live = sum(1 for i in items if i.status == "LIVE")
        xbmc.log(
            f"[ZeroStreams] Returning {len(items)} items ({live} live, {ended} ended dropped)",
            xbmc.LOGINFO,
        )
        return items

    def _player_iframes(self, html: str, base_url: str) -> List[str]:
        results = []
        for candidate in find_iframes(html, base_url):
            if not candidate or _AD_IFRAME.search(candidate):
                continue
            if candidate == base_url:
                continue
            if candidate not in results:
                results.append(candidate)
        return results

    def _resolve_iframe(self, iframe_url: str, referer: str, depth: int = 0) -> Optional[JetLink]:
        if depth > 4:
            return None
        try:
            # Referer must be the page we came from: hosts like exmxbxe.cfd answer
            # 403 "Access Denied (Domain Not Allowed)" on a self-referring request.
            iframe_html = fetch_page(iframe_url, referer=referer)
            if not iframe_html:
                xbmc.log(f"[ZeroStreams] _resolve_iframe: empty html from {iframe_url}", xbmc.LOGWARNING)
                return None

            parsed = urlparse(iframe_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"

            signed_url = _extract_signed_url(iframe_html)
            if signed_url and signed_url.startswith("http"):
                return self._make_proxy_link(signed_url, origin)

            m3u8_url = find_m3u8(iframe_html, iframe_url)
            if m3u8_url:
                return self._make_proxy_link(m3u8_url, origin)

            for nested_url in self._player_iframes(iframe_html, iframe_url):
                result = self._resolve_iframe(nested_url, iframe_url, depth + 1)
                if result:
                    return result

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error resolving iframe {iframe_url}: {e}", xbmc.LOGERROR)

        return None

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        seen = set()
        try:
            html = fetch_page(url.address, referer=url.headers.get("Referer") if url.headers else None)

            parsed = urlparse(url.address)
            origin = f"{parsed.scheme}://{parsed.netloc}"

            candidates: List[str] = []
            for candidate in (find_m3u8(html, url.address), _extract_signed_url(html)):
                if candidate and candidate.startswith("http") and candidate not in candidates:
                    candidates.append(candidate)
            for candidate in candidates:
                links.append(self._make_proxy_link(candidate, origin))
                seen.add(candidate)

            for iframe_url in self._player_iframes(html, url.address):
                if "javascript:" in iframe_url:
                    continue
                result = self._resolve_iframe(iframe_url, url.address)
                if result and result.address not in seen:
                    links.append(result)
                    seen.add(result.address)

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error getting links: {e}", xbmc.LOGERROR)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        try:
            if url.address.startswith("http://127.0.0.1") or url.address.startswith("http://localhost"):
                return url

            parsed = urlparse(url.address)
            origin = f"{parsed.scheme}://{parsed.netloc}"

            referrer = url.headers.get("Referer", origin) if url.headers else origin
            session = get_session(referer=referrer, origin=origin)
            r = session.get(url.address, timeout=10)
            if r.status_code != 200:
                xbmc.log(f"[ZeroStreams] HTTP {r.status_code} for {url.address} (Referer: {referrer})", xbmc.LOGWARNING)
            r.raise_for_status()
            html = r.text

            signed_url = _extract_signed_url(html)
            if signed_url and signed_url.startswith("http"):
                return self._make_proxy_link(signed_url, origin)

            m3u8_url = find_m3u8(html, url.address)
            if m3u8_url:
                return self._make_proxy_link(m3u8_url, origin)

            iframes = self._player_iframes(html, url.address)
            if iframes:
                for nested_url in iframes:
                    result = self._resolve_iframe(nested_url, url.address)
                    if result:
                        return result

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error getting link: {e}", xbmc.LOGERROR)

        return None
