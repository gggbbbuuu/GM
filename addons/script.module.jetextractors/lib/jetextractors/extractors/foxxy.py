import re
import json
import threading
from urllib.parse import urlparse
from ..models import *
from ..tools import debug_log
from .._core import fetch_page, get_session
from ..util.stream_proxy import get_stream_proxy
from ..util import foxxy_store
import xbmc

SCRAPE_INTERVAL = 3600
_scrape_lock = threading.Lock()
_last_scrape_ts = None
_cached_channels = []

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"

IFRAME_SRC_RE = re.compile(r'<iframe[^>]+id=["\']streamIframe["\'][^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
M3U8_URL_RE = re.compile(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*')


def _background_scrape():
    global _last_scrape_ts, _cached_channels
    if not _scrape_lock.acquire(blocking=False):
        return
    try:
        import time
        _last_scrape_ts = time.time()
        debug_log("[Foxxy] Background scrape starting")
        channels = _fetch_channel_list()
        _cached_channels = channels
        if channels:
            foxxy_store.clear_channels()
            foxxy_store.add_channels(channels)
            foxxy_store.set_last_refresh_ts(time.time())
        debug_log(f"[Foxxy] Background scrape complete, {len(channels)} channels")
    except Exception as e:
        debug_log(f"[Foxxy] Background scrape error: {e}")
    finally:
        _scrape_lock.release()


def _fetch_channel_list() -> list:
    """Fetch channel list from JSON API."""
    url = "https://foxxy.st/live-tv?feed=json"
    headers = {"User-Agent": BROWSER_UA}
    try:
        resp = get_session().get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            debug_log(f"[Foxxy] Failed to fetch channel list: {resp.status_code}")
            return []
        data = resp.json()
        channels = data.get("channels", [])
        debug_log(f"[Foxxy] Fetched {len(channels)} channels from API")
        return channels
    except Exception as e:
        debug_log(f"[Foxxy] Error fetching channel list: {e}")
        return []


def _get_embed_url(channel_slug: str) -> str:
    """Fetch channel page and extract embed iframe URL."""
    url = f"https://foxxy.st/live-tv/{channel_slug}"
    headers = {"User-Agent": BROWSER_UA, "Referer": "https://foxxy.st/"}
    try:
        resp = get_session().get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            debug_log(f"[Foxxy] Failed to fetch channel page: {resp.status_code}")
            return None
        html = resp.text
        match = IFRAME_SRC_RE.search(html)
        if match:
            return match.group(1)
        debug_log(f"[Foxxy] No iframe found in {url}")
        return None
    except Exception as e:
        debug_log(f"[Foxxy] Error fetching channel page: {e}")
        return None


def _decode_obfuscated_js(html: str) -> str:
    """Decode the obfuscated JavaScript that contains the stream URL."""
    # Pattern: var _xxx=[...],_yyy=NN,_zzz=NN (variable names may vary)
    match = re.search(r'var\s+_\w+=\[([^\]]+)\],_\w+=(\d+),_\w+=(\d+)', html)
    if not match:
        debug_log("[Foxxy] No obfuscated JS pattern found", xbmc.LOGDEBUG)
        return None
    
    try:
        # Parse the array
        array_str = match.group(1)
        arr = [int(x.strip()) for x in array_str.split(',')]
        xor_key = int(match.group(2))
        sub_val = int(match.group(3))
        
        debug_log(f"[Foxxy] Decoding obfuscated JS: array_len={len(arr)}, xor={xor_key}, sub={sub_val}", xbmc.LOGINFO)
        
        # Decode
        decoded = ""
        for byte in arr:
            char_code = ((byte ^ xor_key) - sub_val + 256) % 256
            decoded += chr(char_code)
        
        return decoded
    except Exception as e:
        debug_log(f"[Foxxy] Error decoding obfuscated JS: {e}", xbmc.LOGERROR)
        return None


def _extract_stream_from_embed(embed_url: str, referer: str) -> str:
    """Extract m3u8 stream URL from embed page."""
    parsed_embed = urlparse(embed_url)
    embed_origin = f"{parsed_embed.scheme}://{parsed_embed.netloc}"
    
    headers = {
        "User-Agent": BROWSER_UA,
        "Referer": referer,
        "Origin": "https://foxxy.st",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        resp = get_session().get(embed_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            debug_log(f"[Foxxy] Embed page returned {resp.status_code}", xbmc.LOGWARNING)
            return None
        
        html = resp.text
        
        patterns = [
            r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
            r'source["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                url = match.group(1) if match.lastindex else match.group(0)
                return url
        
        iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if iframe_match:
            nested_url = iframe_match.group(1)
            if nested_url.startswith("//"):
                nested_url = "https:" + nested_url
            elif nested_url.startswith("/"):
                nested_url = embed_origin + nested_url
            
            nested_headers = {
                "User-Agent": BROWSER_UA,
                "Referer": embed_url,
                "Origin": embed_origin,
            }
            try:
                nested_resp = get_session().get(nested_url, headers=nested_headers, timeout=15)
                if nested_resp.status_code == 200:
                    nested_html = nested_resp.text
                    
                    for pattern in patterns:
                        match = re.search(pattern, nested_html)
                        if match:
                            url = match.group(1) if match.lastindex else match.group(0)
                            return url
                    
                    jw_match = re.search(r'file["\']?\s*:\s*["\']([^"\']+)["\']', nested_html)
                    if jw_match:
                        return jw_match.group(1)
                    
                    decoded_js = _decode_obfuscated_js(nested_html)
                    if decoded_js:
                        for pattern in patterns:
                            match = re.search(pattern, decoded_js)
                            if match:
                                url = match.group(1) if match.lastindex else match.group(0)
                                debug_log(f"[Foxxy] Found stream URL from decoded JS", xbmc.LOGINFO)
                                return url
                        
                        jw_match = re.search(r'file["\']?\s*:\s*["\']([^"\']+)["\']', decoded_js)
                        if jw_match:
                            debug_log(f"[Foxxy] Found JWPlayer file in decoded JS", xbmc.LOGINFO)
                            return jw_match.group(1)
            except Exception as e:
                debug_log(f"[Foxxy] Error fetching nested iframe: {e}", xbmc.LOGWARNING)
        
        debug_log(f"[Foxxy] No m3u8 URL found in embed page", xbmc.LOGWARNING)
        return None
    except Exception as e:
        debug_log(f"[Foxxy] Error fetching embed page: {e}", xbmc.LOGERROR)
        return None


class Foxxy(JetExtractor):
    domains = ["foxxy.st", "foxxtrend.com"]
    name = "Foxxy"
    short_name = "Foxxy"

    def __init__(self) -> None:
        self.base_url = "https://foxxy.st"
        self.stream_headers = {
            "User-Agent": BROWSER_UA,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
        }

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        try:
            if self.progress_init(progress, items):
                return items

            global _cached_channels
            if foxxy_store.is_stale() or not _cached_channels:
                debug_log("[Foxxy] Channels stale, performing synchronous refresh")
                from ..tools import is_store_notifications_enabled
                if is_store_notifications_enabled():
                    import xbmcgui
                    xbmcgui.Dialog().notification(
                        "Foxxy",
                        "Refreshing channels...",
                        xbmcgui.NOTIFICATION_INFO,
                        5000,
                    )
                _background_scrape()
                if not _cached_channels:
                    stored = foxxy_store.load_channels()
                    if stored:
                        _cached_channels = stored
                    else:
                        _cached_channels = _fetch_channel_list()

            channels = _cached_channels
            if not channels:
                debug_log("[Foxxy] No channels available")
                return items

            category_filter = params.get("category") if params else None
            country_filter = params.get("country") if params else None

            if params is None:
                categories = sorted(set(ch.get("category", "Other") for ch in channels if ch.get("category")))
                for cat in categories:
                    items.append(JetItem(
                        title=f"[COLOR yellow]{cat}[/COLOR]",
                        links=[],
                        params={"category": cat}
                    ))
                items.append(JetItem(
                    title="[COLOR green]All Channels[/COLOR]",
                    links=[],
                    params={"category": "__all__"}
                ))
            else:
                filtered = channels
                if category_filter and category_filter != "__all__":
                    filtered = [ch for ch in filtered if ch.get("category") == category_filter]
                if country_filter:
                    filtered = [ch for ch in filtered if ch.get("country") == country_filter]

                for ch in filtered:
                    try:
                        slug = ch.get("slug", "")
                        if not slug:
                            ch_id = ch.get("id", "")
                            slug = ch_id.replace("ch-", "") if ch_id.startswith("ch-") else ch_id
                        name = ch.get("name", "Unknown")
                        logo = ch.get("logo", "")
                        country = ch.get("country", "")
                        category = ch.get("category", "")

                        title = f"{name}"
                        if country:
                            title += f" [COLOR gray]({country})[/COLOR]"

                        channel_url = f"{self.base_url}/live-tv/{slug}"
                        
                        league_text = ""
                        if category and country:
                            league_text = f"{category} - {country}"
                        elif category:
                            league_text = category
                        elif country:
                            league_text = country

                        items.append(JetItem(
                            title=title,
                            icon=logo,
                            league=league_text if league_text else None,
                            links=[JetLink(
                                address=channel_url,
                                name=name,
                                resolveurl=True,
                            )],
                        ))
                    except Exception as e:
                        debug_log(f"[Foxxy] Error building item: {e}", xbmc.LOGERROR)
                        continue

            self.progress_update(progress, f"Loaded {len(items)} channels")
            debug_log(f"[Foxxy] Returning {len(items)} items")
            return items
        except Exception as e:
            import traceback
            debug_log(f"[Foxxy] get_items error: {e}\n{traceback.format_exc()}", xbmc.LOGERROR)
            return []

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        try:
            channel_url = url.address if hasattr(url, 'address') else str(url)
            
            parsed = urlparse(channel_url)
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2 or path_parts[0] != "live-tv":
                debug_log(f"[Foxxy] Invalid channel URL: {channel_url}", xbmc.LOGWARNING)
                return links

            slug = path_parts[1]

            embed_url = _get_embed_url(slug)
            if not embed_url:
                debug_log(f"[Foxxy] Could not find embed URL for {slug}", xbmc.LOGWARNING)
                return links

            stream_url = _extract_stream_from_embed(embed_url, f"{self.base_url}/live-tv/{slug}")
            if not stream_url:
                debug_log(f"[Foxxy] Could not extract stream for {slug}", xbmc.LOGWARNING)
                return links

            debug_log(f"[Foxxy] Stream URL: {stream_url[:80]}...", xbmc.LOGINFO)

            proxy = get_stream_proxy(
                "foxxy",
                self.stream_headers,
                options={
                    "cache_manifest": False,
                    "strip_png": True,
                    "upstream_keep_alive": True,
                    "browser_tls": True,
                },
            )
            proxy_url = proxy.get_proxy_url(stream_url, self.stream_headers)

            links.append(JetLink(
                address=proxy_url,
                name=slug,
                headers=self.stream_headers,
                inputstream=JetInputstreamFFmpegDirect.default(),
            ))

            return links
        except Exception as e:
            import traceback
            debug_log(f"[Foxxy] get_links error: {e}\n{traceback.format_exc()}", xbmc.LOGERROR)
            return []

    def get_link(self, url: JetLink) -> Optional[JetLink]:
        links = self.get_links(url)
        return links[0] if links else None
