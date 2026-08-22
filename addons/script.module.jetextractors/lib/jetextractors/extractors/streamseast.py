from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress
from .._core import get_headers, find_m3u8, find_iframes, make_link, fetch_page
from ..tools import debug_log
from bs4 import BeautifulSoup
import requests
import re
import xbmc
from typing import Optional, List


SKIP_IFRAME_PATTERNS = ["javascript:", "adsco", "youtube.com/live_chat", "streameast.gl"]


def _decode_sportspass_js(html: str) -> Optional[str]:
    eval_match = re.search(r'eval\(function\(h,u,n,t,e,r\)\{(.+?)\}\("(.+?)",(\d+),"(.+?)",(\d+),(\d+),(\d+)\)', html, re.S)
    if not eval_match:
        return None
    try:
        encoded = eval_match.group(2)
        alphabet = eval_match.group(4)
        sep_idx = int(eval_match.group(6))

        separator = alphabet[sep_idx]
        result = ""
        i = 0
        while i < len(encoded):
            seg = ""
            while i < len(encoded) and encoded[i] != separator:
                seg += encoded[i]
                i += 1
            i += 1
            if not seg:
                continue
            for j, ch in enumerate(alphabet):
                if ch != separator:
                    seg = seg.replace(ch, str(j))
            decimal = 0
            for k, digit in enumerate(reversed(seg)):
                decimal += int(digit) * (sep_idx ** k)
            result += chr(decimal - int(eval_match.group(5)))
        return result
    except Exception:
        return None


def _extract_m3u8_from_html(html: str, base_url: str = "") -> Optional[str]:
    direct = find_m3u8(html, base_url)
    if direct:
        return direct
    decoded_js = _decode_sportspass_js(html)
    if decoded_js:
        m = re.search(r'["\']?(https?://[^"\'\s]+\.m3u8(?:\?[^"\'\s]*)?)["\']?', decoded_js)
        if m:
            return m.group(1)
    return None


class StreamsEast(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamseast.ws", "www.streamseast.ws"]
        self.domains_regex = False
        self.name = "StreamsEast"
        self.short_name = "SES"

    SPORTS = ["soccer", "nba", "nfl", "nhl", "mlb", "mma", "boxing", "f1"]

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        for sport in self.SPORTS:
            if self.progress_init(progress, items):
                return items
            
            try:
                if progress:
                    self.progress_update(progress, f"Fetching {sport.title()}...")
                
                url = f"https://{self.domains[0]}/{sport}"
                html = fetch_page(url, referer=f"https://{self.domains[0]}")
                soup = BeautifulSoup(html, "html.parser")

                for match_link in soup.select(f"a[href^='/{sport}/']"):
                    href = match_link.get("href")
                    if not href:
                        continue

                    title = match_link.get("aria-label") or match_link.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue

                    full_url = f"https://{self.domains[0]}{href}"

                    league = sport.upper() if sport in ["nfl", "nba", "nhl", "mlb", "mma", "f1"] else sport.title()
                    parent_heading = match_link.find_previous("h2")
                    if parent_heading:
                        league_text = parent_heading.get_text(strip=True)
                        if league_text and "See All" not in league_text and "News" not in league_text:
                            league = league_text

                    items.append(JetItem(title, [JetLink(full_url, links=True)], league=league))

            except Exception as e:
                debug_log(f"[StreamsEast] Error fetching {sport}: {e}", xbmc.LOGERROR)

        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        try:
            html = fetch_page(url.address, referer=url.address)

            is_live_match = re.search(r'let\s+isLive\s*=\s*["\'](\w+)["\']', html)
            if is_live_match:
                debug_log(f"[StreamsEast] Match status: {is_live_match.group(1)}", xbmc.LOGINFO)

            m3u8_url = _extract_m3u8_from_html(html, url.address)
            if m3u8_url:
                links.append(make_link(m3u8_url, referer=url.address))

            iframes = find_iframes(html, url.address)
            for iframe_url in iframes:
                if any(skip in iframe_url.lower() for skip in SKIP_IFRAME_PATTERNS):
                    continue
                result = self._resolve_iframe(iframe_url, url.address)
                if result:
                    links.append(result)

        except Exception as e:
            debug_log(f"[StreamsEast] Error getting links: {e}", xbmc.LOGERROR)

        return links

    def _resolve_iframe(self, iframe_url: str, referer: str, depth: int = 0) -> Optional[JetLink]:
        if depth > 5:
            return None
        try:
            iframe_html = fetch_page(iframe_url, referer=referer)
            if not iframe_html:
                return None

            m3u8_url = _extract_m3u8_from_html(iframe_html, iframe_url)
            if m3u8_url:
                return make_link(m3u8_url, referer=iframe_url)

            nested_iframes = find_iframes(iframe_html, iframe_url)
            for nested_url in nested_iframes:
                if any(skip in nested_url.lower() for skip in SKIP_IFRAME_PATTERNS):
                    continue
                result = self._resolve_iframe(nested_url, iframe_url, depth + 1)
                if result:
                    return result

        except Exception as e:
            debug_log(f"[StreamsEast] _resolve_iframe error: {e}", xbmc.LOGERROR)

        return None

    def get_link(self, url: JetLink) -> JetLink:
        try:
            html = fetch_page(url.address, referer=url.address)

            m3u8_url = _extract_m3u8_from_html(html, url.address)
            if m3u8_url:
                return make_link(m3u8_url, referer=url.address)

            iframes = find_iframes(html, url.address)
            for iframe_url in iframes:
                if any(skip in iframe_url.lower() for skip in SKIP_IFRAME_PATTERNS):
                    continue
                result = self._resolve_iframe(iframe_url, url.address)
                if result:
                    return result

        except Exception as e:
            debug_log(f"[StreamsEast] Error resolving link: {e}", xbmc.LOGERROR)

        return JetLink(url.address, headers=get_headers(referer=url.address))
