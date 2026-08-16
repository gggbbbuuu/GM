from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress
from .._core import get_headers, get_session, find_m3u8, find_iframes, make_link, fetch_page
import requests
import re
import xbmc
from typing import Optional, List
from urllib.parse import urlparse


def _decode_obfuscated_array(html: str) -> Optional[str]:
    script_match = re.search(r'<script[^>]*>\(function\(\)\{var\s+\w+=\[([\d,\s]+)\],(\w+)=(\d+),(\w+)=(\d+)', html)
    if not script_match:
        return None
    try:
        values = [int(x.strip()) for x in script_match.group(1).split(',') if x.strip()]
        xor_key = int(script_match.group(3))
        sub_key = int(script_match.group(5))
        decoded = ''
        for v in values:
            decoded += chr(((v ^ xor_key) - sub_key + 65536) % 65536)
        return decoded
    except Exception:
        return None


def _extract_signed_url(html: str) -> Optional[str]:
    decoded_js = _decode_obfuscated_array(html)
    if decoded_js:
        url_match = re.search(r'SIGNED_URL\s*=\s*["\']([^"\']+)["\']', decoded_js)
        if url_match:
            return url_match.group(1)
    url_match = re.search(r'SIGNED_URL\s*=\s*["\']([^"\']+)["\']', html)
    if url_match:
        return url_match.group(1)
    return None


class ZeroStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["zero-streams.online", "www.zero-streams.online", "flyembed.click", "www.flyembed.click", "epiembeds.online", "www.epiembeds.online"]
        self.domains_regex = False
        self.name = "ZeroStreams"
        self.short_name = "ZS"
        self.api_url = "https://ovogoal.cyou/api/v2/flyembed.json"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        try:
            if progress:
                self.progress_update(progress, "Fetching streams from API...")

            headers = get_headers(referer="https://zero-streams.online")
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

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        try:
            html = fetch_page(url.address, referer=url.address)

            iframes = find_iframes(html, url.address)
            for iframe_url in iframes:
                if "javascript:" in iframe_url:
                    continue
                links.append(JetLink(iframe_url, resolveurl=True, headers=get_headers(referer=url.address)))

            m3u8_url = find_m3u8(html, url.address)
            if m3u8_url:
                links.append(make_link(m3u8_url, referer=url.address))

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error getting links: {e}", xbmc.LOGERROR)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        try:
            parsed = urlparse(url.address)
            origin = f"{parsed.scheme}://{parsed.netloc}"

            referrer = url.headers.get("Referer", origin) if url.headers else origin
            session = get_session(referer=referrer, origin=origin)
            r = session.get(url.address, timeout=10)
            r.raise_for_status()
            html = r.text

            signed_url = _extract_signed_url(html)
            if signed_url:
                return JetLink(
                    signed_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Referer": origin,
                        "Origin": origin,
                    }
                )

            m3u8_url = find_m3u8(html, url.address)
            if m3u8_url:
                return JetLink(
                    m3u8_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Referer": origin,
                        "Origin": origin,
                    }
                )

            iframes = find_iframes(html, url.address)
            if iframes:
                return JetLink(iframes[0], resolveurl=True, headers=get_headers(referer=url.address))

        except Exception as e:
            xbmc.log(f"[ZeroStreams] Error getting link: {e}", xbmc.LOGERROR)

        return JetLink(url.address)
