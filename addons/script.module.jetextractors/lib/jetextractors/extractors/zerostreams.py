from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
from .._core import get_headers, get_session, find_m3u8, find_iframes, make_link, fetch_page
from ..util.stream_proxy import get_stream_proxy
import requests
import re
import xbmc
from typing import Optional, List
from urllib.parse import urlparse


def _decode_obfuscated_array(html: str) -> Optional[str]:
    num_list_match = re.search(r'var\s+_(?:\w|\d)+=\[(.*)\],', html, re.S)
    if not num_list_match:
        return None
    index_match = re.search(r'\],(.*)(_.*="")', html, re.S)
    z_match = re.search(r'%(\d+)', html)
    if not index_match or not z_match:
        return None
    try:
        values = [int(i) for i in num_list_match[1].split(',') if i.strip()]
        if not values:
            return None
        parts = [i.strip() for i in index_match[1].split(',') if i.strip()]
        nums = [int(i.split('=')[-1]) for i in parts]
        if len(nums) < 2:
            return None
        x, y = nums[0], nums[1]
        z = int(z_match[1])
        if z == 0:
            return None
        decoded = ''.join(chr(((v ^ x) - y + z) % z) for v in values)
        return decoded
    except Exception as e:
        xbmc.log(f"[ZeroStreams] _decode exception: {e}", xbmc.LOGERROR)
        return None


def _extract_signed_url(html: str) -> Optional[str]:
    url_match = re.search(r'(?:SIGNED_URL|signed_url)\s*=\s*["\']([^"\']+)["\']', html, re.I)
    if url_match:
        url = url_match.group(1)
        if url.startswith('http'):
            return url
    decoded_js = _decode_obfuscated_array(html)
    if decoded_js:
        url_match = re.search(r'(?:SIGNED_URL|signed_url)\s*=\s*["\']([^"\']+)["\']', decoded_js, re.I)
        if url_match:
            url = url_match.group(1)
            if url.startswith('http'):
                return url
    return None


class ZeroStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["flyembed.click/", "www.zero-streams.online", "flyembed.click", "www.flyembed.click", "epiembeds.online", "www.epiembeds.online"]
        self.domains_regex = False
        self.name = "ZeroStreams"
        self.short_name = "ZS"
        self.api_url = "https://ovogoal.cyou/api/v2/flyembed.json"

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

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        try:
            if progress:
                self.progress_update(progress, "Fetching streams from API...")

            headers = get_headers(referer="https://flyembed.click")
            response = requests.get(self.api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                xbmc.log("[ZeroStreams] API returned unexpected format", xbmc.LOGERROR)
                return items

            for event in data:
                try:
                    team1 = event.get("Team 1 ", "").strip()
                    team2 = event.get("Team2", "").strip()
                    league = event.get("League", "").strip()
                    date_str = event.get("Date", "").strip()
                    time_str = event.get("Time", "").strip()
                    iframe_url = event.get("iframeURL", "").strip()
                    league_logo = event.get("Leaguelogo", "")
                    team1_logo = event.get("Team1Logo", "")
                    team2_logo = event.get("Team2Logo", "")

                    if not team1 or not team2 or not iframe_url:
                        continue

                    title = f"{team1} vs {team2}"
                    if date_str and time_str:
                        title = f"{title} ({date_str} {time_str})"
                    elif date_str:
                        title = f"{title} ({date_str})"

                    icon = team1_logo or league_logo

                    items.append(JetItem(
                        title=title,
                        links=[JetLink(iframe_url, links=True)],
                        league=league,
                        icon=icon
                    ))

                except Exception as e:
                    xbmc.log(f"[ZeroStreams] Error parsing event: {e}", xbmc.LOGERROR)
                    continue

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error fetching API: {e}", xbmc.LOGERROR)

        return items

    def _resolve_iframe(self, iframe_url: str, referer: str) -> Optional[JetLink]:
        try:
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

            nested_iframes = find_iframes(iframe_html, iframe_url)
            for nested_url in nested_iframes:
                result = self._resolve_iframe(nested_url, iframe_url)
                if result:
                    return result

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error resolving iframe {iframe_url}: {e}", xbmc.LOGERROR)

        return None

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        try:
            html = fetch_page(url.address, referer=url.address)

            m3u8_url = find_m3u8(html, url.address)
            if m3u8_url:
                parsed = urlparse(url.address)
                origin = f"{parsed.scheme}://{parsed.netloc}"
                links.append(self._make_proxy_link(m3u8_url, origin))

            iframes = find_iframes(html, url.address)
            for iframe_url in iframes:
                if "javascript:" in iframe_url:
                    continue
                result = self._resolve_iframe(iframe_url, url.address)
                if result:
                    links.append(result)

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

            iframes = find_iframes(html, url.address)
            if iframes:
                for nested_url in iframes:
                    result = self._resolve_iframe(nested_url, url.address)
                    if result:
                        return result

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error getting link: {e}", xbmc.LOGERROR)

        return None
