from ..models import *
from .._core import get_headers, find_m3u8
from ..util.stream_proxy import get_stream_proxy
from typing import Optional, List, Tuple
import requests
import time
import xbmc
import re
from ..tools import debug_log
from datetime import datetime
from urllib.parse import urljoin

class EmbedHDApi(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["embedhd.st"]
        self.name = "EmbedHD API"
        self.timeout = 15
        self.api_url = "https://embedhd.st/api-event.php"
        self.events_cache: List[dict] = []
        self.last_refresh: float = 0.0
        self._proxy = None

    def _get_session_headers(self, referer: str = "https://embedhd.st/") -> dict:
        return {
            "User-Agent": self.user_agent,
            "Referer": referer,
            "Origin": "https://embedhd.st",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _get_proxy(self):
        if self._proxy is None:
            manifest_headers = {
                "User-Agent": self.user_agent,
                "Referer": "https://exposestrat.com/",
                "Origin": "https://exposestrat.com",
            }
            self._proxy = get_stream_proxy(
                "embedhd",
                manifest_headers,
                options={"cache_manifest": False, "proxy_absolute_urls": True},
            )
        return self._proxy

    def _fetch_events(self) -> bool:
        now = time.time()
        if self.events_cache and (now - self.last_refresh) < 45:
            return True
        try:
            headers = self._get_session_headers()
            r = requests.get(
                self.api_url,
                headers=headers,
                timeout=self.timeout,
                verify=False,
            )
            if r.status_code == 200:
                data = r.json()
                matches = data.get("matches", [])
                if matches:
                    self.events_cache = matches
                    self.last_refresh = now
                    debug_log(f"[EmbedHDApi] Loaded {len(matches)} events from API", xbmc.LOGINFO)
                    return True
        except Exception as e:
            debug_log(f"[EmbedHDApi] Failed to fetch events: {e}", xbmc.LOGWARNING)
        return False

    def _get_category_label(self, category: str) -> str:
        category_map = {
            "baseball": "MLB",
            "american-football": "NFL",
            "football": "Soccer",
            "motor-sports": "Motorsport",
            "fight": "UFC/Fight",
        }
        return category_map.get(category, category.upper())

    def _follow_iframe_to_m3u8(self, start_url: str) -> Tuple[Optional[str], Optional[str]]:
        session = requests.Session()
        session.headers.update(self._get_session_headers())
        session.verify = False
        current_url = start_url
        visited = set()
        
        for depth in range(5):
            if current_url in visited:
                break
            visited.add(current_url)
            
            try:
                r = session.get(current_url, timeout=self.timeout)
                if r.status_code != 200:
                    debug_log(f"[EmbedHDApi] Chain depth {depth} returned {r.status_code}: {current_url}", xbmc.LOGDEBUG)
                    return None, None
                
                html = r.text
                
                m3u8_match = re.search(r'["\'](https?://[^"\']+\.m3u8(?:\?[^"\']*)?)["\']', html)
                if m3u8_match:
                    cookies = "; ".join(f"{c.name}={c.value}" for c in session.cookies)
                    return m3u8_match.group(1), cookies
                
                return_match = re.search(r'return\(\[([^\]]+)\]', html)
                if return_match:
                    try:
                        m3u8 = "".join(eval("[" + return_match.group(1) + "]")).replace("\\", "").replace("////", "//")
                        if m3u8 and ".m3u8" in m3u8:
                            cookies = "; ".join(f"{c.name}={c.value}" for c in session.cookies)
                            debug_log(f"[EmbedHDApi] Extracted m3u8 from return([...]): {m3u8[:100]}", xbmc.LOGINFO)
                            return m3u8, cookies
                    except Exception:
                        pass
                
                fid_match = re.search(r'window\.fid=["\']([^"\']+)["\']', html)
                if fid_match:
                    fid = fid_match.group(1)
                    embed_url = f"https://exposestrat.com/maestrohd1.php?player=desktop&live={fid}"
                    if embed_url not in visited:
                        session.headers.update({"Referer": current_url})
                        current_url = embed_url
                        debug_log(f"[EmbedHDApi] Found fid={fid}, following to {embed_url}", xbmc.LOGINFO)
                        continue
                
                iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
                if iframe_match:
                    next_url = iframe_match.group(1)
                    if not next_url.startswith("http"):
                        next_url = urljoin(current_url, next_url)
                    session.headers.update({"Referer": current_url})
                    current_url = next_url
                    continue
                
                ref_id_match = re.search(r'window\.[a-zA-Z_]+\.src=[\'"]([^"\']+)[\'"]', html)
                if ref_id_match:
                    cookies = "; ".join(f"{c.name}={c.value}" for c in session.cookies)
                    return ref_id_match.group(1), cookies
                
                break
                
            except Exception as e:
                debug_log(f"[EmbedHDApi] Chain error: {e}", xbmc.LOGDEBUG)
                return None, None
        
        return None, None

    def _proxy_link(self, stream_url: str, cookies: Optional[str] = None) -> JetLink:
        proxy = self._get_proxy()
        headers = {"Referer": "https://exposestrat.com/", "Origin": "https://exposestrat.com"}
        if cookies:
            headers["Cookie"] = cookies
        proxy_url = proxy.get_proxy_url(stream_url, headers)
        debug_log(f"[EmbedHDApi] Proxy URL: {proxy_url}", xbmc.LOGINFO)
        return JetLink(
            address=proxy_url,
            inputstream=JetInputstreamFFmpegDirect.default(),
        )

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        if not self._fetch_events():
            return items

        for event in self.events_cache:
            title = event.get("title", "")
            if not title:
                continue

            status = event.get("status", "")
            category = event.get("category", "")
            league = event.get("league", "")
            ts_et = event.get("ts_et", 0)
            
            starttime = None
            if ts_et and ts_et > 0:
                try:
                    starttime = datetime.fromtimestamp(ts_et)
                except Exception:
                    pass

            streams = event.get("streams", [])
            if not streams:
                continue

            for s in streams:
                if not isinstance(s, dict):
                    continue
                stream_url = s.get("link")
                if not stream_url:
                    continue
                
                link = JetLink(address=stream_url)
                
                item = JetItem(
                    title=title,
                    links=[link],
                    starttime=starttime,
                    status=status,
                    league=league or self._get_category_label(category),
                )
                items.append(item)
                break

        debug_log(f"[EmbedHDApi] Total items: {len(items)}", xbmc.LOGINFO)
        return items

    def get_link(self, url: JetLink) -> JetLink:
        cdn_url, cookies = self._follow_iframe_to_m3u8(url.address)
        if not cdn_url:
            debug_log("[EmbedHDApi] Failed to resolve m3u8 from chain", xbmc.LOGWARNING)
            return JetLink(address=url.address)
        debug_log(f"[EmbedHDApi] Resolved m3u8: {cdn_url[:100]}", xbmc.LOGINFO)
        return self._proxy_link(cdn_url, cookies)