from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
from .._core import find_m3u8, find_iframes, decode_stream, get_headers
from ..endpoints import BACKDOOR_PREFERRED
import requests
import re
import json
from typing import Optional, List, Union, Tuple
import xbmc
import time
import random
import traceback
import urllib3
from ..tools import debug_log
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_tls_session = None
try:
    import ssl
    from requests.adapters import HTTPAdapter
    _ctx = ssl.create_default_context()
    _ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE
    class _LowSecAdapter(HTTPAdapter):
        def init_poolmanager(self, *a, **kw):
            kw['ssl_context'] = _ctx
            super().init_poolmanager(*a, **kw)
    _tls_session = requests.Session()
    _tls_session.mount("https://", _LowSecAdapter())
    _tls_session.mount("http://", _LowSecAdapter())
except Exception:
    _tls_session = None

_module_last_request_time = 0
_events_cache = None
_events_cache_time = 0
_EVENTS_CACHE_TTL = 300  # 5 minutes

class Backdoor1(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["daddylive.mov"]
        self.name = "Backdoor1"

        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self.ott_agents = [       
            "VLC/3.0.18 LibVLC/3.0.18",
            "TiviMate/4.7.0 (Android)",
            "iMPlayer/3.9.5 (Linux;Android 14) AndroidXMedia3/1.8.0",
            "OTT-IPTV/1.0 (Linux; Android 10; BR) XtreamPlayer/5.0"
        ]

        self.min_request_interval = 5
        self.preferred_domains = ["vomos", "zalis"]
        self.dead_domains = ["pontos"]
        self._domains_fetched = False

    def _do_request(self, method: str, url: str, headers=None, timeout: Union[int, Tuple[int, int]] = 15, **kwargs):
        """HTTP request helper for Android boxes/Firestick.
        Uses a pre-built TLS session to avoid import overhead on each call.
        Falls back to plain requests if TLS session is unavailable.
        """
        if _tls_session is not None:
            try:
                return _tls_session.request(
                    method, url, headers=headers, timeout=timeout,
                    verify=False, **kwargs,
                )
            except Exception:
                pass
        return requests.request(
            method, url, headers=headers, timeout=timeout,
            verify=False, **kwargs,
        )

    def _ensure_domains(self):
        if not self._domains_fetched:
            self._fetch_preferred_domains()
            self._domains_fetched = True

    def _fetch_preferred_domains(self) -> None:
        urls = [
            BACKDOOR_PREFERRED,
        ]

        for url in urls:
            try:
                debug_log(f"[Backdoor] Fetching preferred domains from: server", xbmc.LOGINFO)
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                }
                r = self._do_request('get', url, headers=headers, timeout=15)

                if r.status_code == 200:
                    domains = []
                    for line in r.text.splitlines():
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        domains.append(line.lower())

                    if domains:
                        self.preferred_domains = domains
                        debug_log(f"[Backdoor] Loaded {len(domains)} preferred domains: {domains}", xbmc.LOGINFO)
                        return
                else:
                    debug_log(f"[Backdoor] Preferred domains fetch returned status {r.status_code}", xbmc.LOGWARNING)
            except Exception as e:
                debug_log(f"[Backdoor] Failed to fetch preferred domains from {url}: {str(e)}", xbmc.LOGWARNING)

        debug_log(f"[Backdoor] Using default preferred domains: {self.preferred_domains}", xbmc.LOGINFO)

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        self._ensure_domains()

        events = self._fetch_events()
        items.extend(events)

        channels = self._fetch_channels()
        items.extend(channels)

        for item in items:
            if item.links:
                link = item.links[0]
                debug_log(f"[Backdoor] ITEM '{item.title}' -> address={link.address} links={link.links}", xbmc.LOGINFO)

        debug_log(f"[Backdoor] Total items: {len(items)} ({len(events)} events, {len(channels)} channels)", xbmc.LOGINFO)
        return items

    def _fetch_events(self) -> List[JetItem]:
        global _events_cache, _events_cache_time

        # Return cached events if still valid
        if _events_cache is not None and (time.time() - _events_cache_time) < _EVENTS_CACHE_TTL:
            debug_log(f"[Backdoor] Returning {len(_events_cache)} cached events", xbmc.LOGINFO)
            return list(_events_cache)

        items = []
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()

                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Origin': 'https://daddylive.mov',
                    'Referer': 'https://daddylive.mov/',
                }
                
                # Replace the Agent
                headers['User-Agent'] = random.choice(self.ott_agents)

                debug_log(f"[Backdoor] Fetching events from API (attempt {attempt + 1}/{max_retries + 1})", xbmc.LOGINFO)

                try:
                    r = self._do_request('get', "https://daddylive.mov/api/events", headers=headers, timeout=(8, 20))
                    body = r.content[:2 * 1024 * 1024]
                except Exception as e:
                    debug_log(f"[Backdoor] Events API request failed: {type(e).__name__}: {str(e)[:60]}", xbmc.LOGWARNING)
                    self._update_last_request_time()
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(1, 2)
                        debug_log(f"[Backdoor] Retrying events fetch in {backoff:.1f}s...", xbmc.LOGWARNING)
                        time.sleep(backoff)
                        continue
                    break

                self._update_last_request_time()

                if r.status_code != 200:
                    debug_log(f"[Backdoor] API HTTP Error {r.status_code}", xbmc.LOGWARNING)
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(1, 2)
                        time.sleep(backoff)
                        continue
                    break

                try:
                    api_data = json.loads(body)
                except Exception as e:
                    debug_log(f"[Backdoor] Failed to parse API JSON: {str(e)}", xbmc.LOGWARNING)
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(1, 2)
                        time.sleep(backoff)
                        continue
                    break

                categories = None
                popular_events = None
                if isinstance(api_data, list):
                    if len(api_data) == 0:
                        break
                    first_item = api_data[0]
                    if isinstance(first_item, dict) and 'categories' in first_item:
                        categories = first_item.get('categories', {})
                elif isinstance(api_data, dict):
                    if 'categories' in api_data:
                        categories = api_data.get('categories', {})
                    else:
                        categories = api_data
                    popular_events = api_data.get('popular_events', [])

                if not categories or not isinstance(categories, dict):
                    break

                debug_log(f"[Backdoor] Found {len(categories)} categories", xbmc.LOGINFO)

                for category, category_info in categories.items():
                    if not isinstance(category_info, list):
                        continue

                    if category.lower() == 'tv shows':
                        continue

                    for event_info in category_info:
                        if not isinstance(event_info, dict):
                            continue

                        event_name = event_info.get('event', '').strip()
                        if not event_name:
                            continue

                        channels = event_info.get('channels', [])
                        if not channels or not isinstance(channels, list):
                            continue

                        channel_id = None
                        for ch in channels:
                            if isinstance(ch, dict):
                                if ch.get('channel_id'):
                                    channel_id = str(ch.get('channel_id'))
                                    break
                                if ch.get('url'):
                                    channel_id = self._extract_channel_id_from_url(ch.get('url'))
                                    if channel_id:
                                        break

                        if not channel_id:
                            continue

                        stream_url = f"https://daddylive.mov/live/stream={channel_id}"
                        time_str = event_info.get('time', '')
                        if time_str:
                            event_name = f"{event_name} ({time_str})"

                        items.append(JetItem(event_name, [JetLink(stream_url, links=True)], league=category, extractor="Backdoor1"))

                if popular_events and isinstance(popular_events, list):
                    for event_info in popular_events:
                        if not isinstance(event_info, dict):
                            continue
                        event_name = event_info.get('event', '').strip()
                        if not event_name:
                            continue
                        channels = event_info.get('channels', [])
                        if not channels or not isinstance(channels, list):
                            continue
                        time_str = event_info.get('time', '')
                        if time_str:
                            event_name = f"{event_name} ({time_str})"
                        for ch in channels:
                            if not isinstance(ch, dict):
                                continue
                            channel_id = None
                            if ch.get('channel_id'):
                                channel_id = str(ch.get('channel_id'))
                            elif ch.get('url'):
                                channel_id = self._extract_channel_id_from_url(ch.get('url'))
                            if not channel_id:
                                continue
                            stream_url = f"https://daddylive.mov/live/stream={channel_id}"
                            event_category = event_info.get('category', 'Popular Events')
                            items.append(JetItem(event_name, [JetLink(stream_url, links=True)], league=event_category, extractor="Backdoor1"))

                debug_log(f"[Backdoor] Found {len(items)} events from API", xbmc.LOGINFO)

                # Cache successful results
                _events_cache = list(items)
                _events_cache_time = time.time()
                break

            except Exception as e:
                debug_log(f"[Backdoor] Error fetching events: {str(e)}", xbmc.LOGERROR)
                debug_log(f"[Backdoor] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
                if attempt < max_retries:
                    backoff = (2 ** attempt) + random.uniform(1, 2)
                    debug_log(f"[Backdoor] Retrying events fetch in {backoff:.1f}s...", xbmc.LOGWARNING)
                    time.sleep(backoff)
                else:
                    break

        return items

    def _fetch_channels(self) -> List[JetItem]:
        items = []
        try:
            self._rate_limit()

            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://daddylive.mov',
                'Referer': 'https://daddylive.mov/',
            }
            
            # Replace the Agent
            headers['User-Agent'] = random.choice(self.ott_agents)

            debug_log(f"[Backdoor] Fetching channels from API", xbmc.LOGINFO)

            try:
                r = self._do_request('get', "https://daddylive.mov/api/channels", headers=headers, timeout=(8, 20))
                body = r.content[:4 * 1024 * 1024]
            except Exception as e:
                debug_log(f"[Backdoor] Channels API request failed (skipping): {type(e).__name__}: {str(e)[:60]}", xbmc.LOGWARNING)
                self._update_last_request_time()
                return items
            self._update_last_request_time()

            if r.status_code != 200:
                debug_log(f"[Backdoor] Channels API HTTP Error {r.status_code}", xbmc.LOGWARNING)
                return items

            try:
                channels_data = json.loads(body)
            except Exception as e:
                debug_log(f"[Backdoor] Failed to parse channels JSON: {str(e)}", xbmc.LOGWARNING)
                return items

            if not isinstance(channels_data, list):
                debug_log(f"[Backdoor] Channels data is not a list", xbmc.LOGWARNING)
                return items

            debug_log(f"[Backdoor] Found {len(channels_data)} channels", xbmc.LOGINFO)

            for channel in channels_data:
                if not isinstance(channel, dict):
                    continue

                channel_name = channel.get('channel_name', '').strip()
                channel_id = channel.get('channel_id', '')
                if not channel_id and channel.get('url'):
                    channel_id = self._extract_channel_id_from_url(channel.get('url'))

                if not channel_name or not channel_id:
                    continue

                stream_url = f"https://daddylive.mov/live/stream={channel_id}"
                items.append(JetItem(channel_name, [JetLink(stream_url, links=True)], league="Channels", extractor="Backdoor1"))

            debug_log(f"[Backdoor] Added {len(items)} channels to items list", xbmc.LOGINFO)

        except Exception as e:
            debug_log(f"[Backdoor] Error fetching channels: {str(e)}", xbmc.LOGERROR)
            debug_log(f"[Backdoor] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)

        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        debug_log(f"[Backdoor] ========== get_links START ==========", xbmc.LOGINFO)
        debug_log(f"[Backdoor] Input URL: {url.address}", xbmc.LOGINFO)

        self._ensure_domains()

        try:
            self._rate_limit()

            channel_id = None
            match = re.search(r'stream=([^&]+)', url.address)
            if match:
                channel_id = match.group(1)

            debug_log(f"[Backdoor] Extracted channel_id: {channel_id}", xbmc.LOGINFO)

            if not channel_id:
                return []

            stream_url = f"https://daddylive.mov/live/stream={channel_id}"
            result = self._resolve_stream(channel_id, ref_url=stream_url)
            self._update_last_request_time()

            if result is not None:
                debug_log(f"[Backdoor] Found stream: {result.address[:100]}", xbmc.LOGINFO)
                debug_log(f"[Backdoor] ========== get_links END (SUCCESS) ==========", xbmc.LOGINFO)
                return [result]

            debug_log(f"[Backdoor] No valid stream found, returning empty list", xbmc.LOGWARNING)
            return []

        except Exception as e:
            debug_log(f"[Backdoor] get_links EXCEPTION: {type(e).__name__}: {str(e)}", xbmc.LOGERROR)
            debug_log(f"[Backdoor] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
            raise

    def _resolve_stream(self, channel_id: str, ref_url: str) -> Optional[JetLink]:
        ua = random.choice(self.user_agents)

        # Step 1: Fetch the intermediate player page from cricsfree.cfd
        player_url = f"https://cricsfree.cfd/live/stream-{channel_id}.php"
        step1_headers = get_headers(referer="https://daddylive.mov/", origin="https://daddylive.mov")
        step1_headers['Accept-Encoding'] = 'gzip, deflate'

        try:
            r1 = self._do_request('get', player_url, headers=step1_headers, timeout=15)
            if r1.status_code != 200:
                debug_log(f"[Backdoor] Player page returned status {r1.status_code}", xbmc.LOGWARNING)
                return None
            page_html = r1.content.decode('utf-8', errors='ignore').replace('\x00', '')
        except Exception as e:
            debug_log(f"[Backdoor] Player page fetch failed: {str(e)[:80]}", xbmc.LOGWARNING)
            return None

        # Step 2: Extract the iframe src pointing to hamis.romponalis.st
        iframe_src = None
        iframes = find_iframes(page_html, "https://cricsfree.cfd")
        for u in iframes:
            if 'romponalis' in u or 'cricsfree' in u:
                iframe_src = u
                break
        if not iframe_src and iframes:
            iframe_src = iframes[0]

        if not iframe_src:
            debug_log(f"[Backdoor] No iframe found in player page", xbmc.LOGWARNING)
            return None

        if iframe_src.startswith('//'):
            iframe_src = 'https:' + iframe_src

        debug_log(f"[Backdoor] Found iframe: {iframe_src[:120]}", xbmc.LOGINFO)

        # Step 3: Fetch the final page (hamis.romponalis.st) with correct Referer
        step2_headers = get_headers(referer=player_url, origin="https://cricsfree.cfd")
        step2_headers['Accept-Encoding'] = 'gzip, deflate'

        for attempt in range(2):
            try:
                r2 = self._do_request('get', iframe_src, headers=step2_headers, timeout=15)
                if r2.status_code != 200:
                    debug_log(f"[Backdoor] Final page returned status {r2.status_code}", xbmc.LOGWARNING)
                    if attempt == 0 and r2.status_code == 403:
                        time.sleep(1)
                        continue
                    return None
                html = r2.content.decode('utf-8', errors='ignore').replace('\x00', '')
                break
            except Exception as e:
                debug_log(f"[Backdoor] Final page fetch failed: {str(e)[:80]}", xbmc.LOGWARNING)
                return None
        else:
            return None

        stream_url = self._extract_m3u8_from_html(html)
        if not stream_url:
            debug_log(f"[Backdoor] No m3u8 URL found in page HTML", xbmc.LOGWARNING)
            return None

        if stream_url.startswith('//'):
            stream_url = 'https:' + stream_url

        self._discover_domains(stream_url)
        if 'jmp2.uk/plu-' in stream_url or 'pluto' in stream_url.lower():
            debug_log(f"[Backdoor] Skipping unsupported host: {stream_url[:80]}", xbmc.LOGWARNING)
            return None

        stream_url = self._swap_dead_domain(stream_url)

        link = JetLink(
            address=stream_url,
            headers={'Referer': iframe_src, 'User-Agent': ua},
            inputstream=JetInputstreamFFmpegDirect.default(),
        )
        return link

    def _extract_m3u8_from_html(self, html: str) -> Optional[str]:
        atob_matches = re.findall(r'(?:window\.)?atob\(\s*[\'\"]([A-Za-z0-9+/=]+)[\'\"]\s*\)', html)
        for match in atob_matches:
            decoded = decode_stream(match)
            if '.m3u8' in decoded:
                url_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', decoded)
                if url_match:
                    return url_match.group(1)

        return find_m3u8(html, "https://daddylive.mov")

    def _swap_dead_domain(self, url: str) -> str:
        if not any(dead in url for dead in self.dead_domains):
            return url

        self._ensure_domains()

        for preferred in self.preferred_domains:
            test_url = url
            for dead in self.dead_domains:
                if dead in test_url:
                    test_url = test_url.replace(dead, preferred)
                    break
            if self._test_stream_url(test_url):
                debug_log(f"[Backdoor] Working domain found: {preferred}", xbmc.LOGINFO)
                return test_url

        debug_log(f"[Backdoor] No working preferred domain, returning original URL", xbmc.LOGWARNING)
        return url

    def _get_working_stream(self, url: str) -> str:
        needs_replacement = any(dead in url for dead in self.dead_domains)

        if not needs_replacement:
            return url

        for preferred in self.preferred_domains:
            test_url = url
            for dead in self.dead_domains:
                if dead in test_url:
                    test_url = test_url.replace(dead, preferred)
                    break

            if self._test_stream_url(test_url):
                debug_log(f"[Backdoor] Working domain found: {preferred}", xbmc.LOGINFO)
                return test_url

        debug_log(f"[Backdoor] None of preferred domains worked, using original URL", xbmc.LOGWARNING)
        return url

    def _test_stream_url(self, url: str) -> bool:
        try:
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://hamis.romponalis.st/',
            }
            r = self._do_request('head', url, headers=headers, timeout=10)
            if r.status_code in (200, 302, 303):
                return True
            r2 = self._do_request('get', url, headers=headers, timeout=10)
            if r2.status_code == 200:
                content = r2.content[:500]
                if b'#EXTM3U' in content or b'#EXT-X' in content or b'm3u8' in content.lower():
                    return True
        except Exception as e:
            debug_log(f"[Backdoor] Test failed for {url[:80]}: {str(e)[:50]}", xbmc.LOGDEBUG)
        return False

    def _discover_domains(self, url: str) -> None:
        m3u8_match = re.search(r'https?://([a-z0-9.-]+)/', url, re.I)
        if m3u8_match:
            domain = m3u8_match.group(1)
            if 'phantemlis' in domain or 'jmp2' not in domain:
                debug_log(f"[Backdoor] DISCOVERED DOMAIN: {domain} (full URL: {url[:120]})", xbmc.LOGINFO)

    def _extract_channel_id_from_url(self, url: str) -> Optional[str]:
        match = re.search(r'/player/embed\.php\?id=([^&\s]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'stream=([^&]+)', url)
        if match:
            return match.group(1)
        return None

    def _rate_limit(self):
        global _module_last_request_time
        elapsed = time.time() - _module_last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed + random.uniform(1.0, 3.0)
            debug_log(f"[Backdoor] Rate limiting: waiting {wait_time:.1f}s", xbmc.LOGINFO)
            time.sleep(wait_time)

    def _update_last_request_time(self):
        global _module_last_request_time
        _module_last_request_time = time.time()

    def get_link(self, url: JetLink) -> JetLink:
        debug_log(f"[Backdoor] ========== get_link START ==========", xbmc.LOGINFO)
        debug_log(f"[Backdoor] Input URL: {url.address}", xbmc.LOGINFO)

        self._ensure_domains()

        try:
            self._rate_limit()

            channel_id = None
            match = re.search(r'stream=([^&]+)', url.address)
            if match:
                channel_id = match.group(1)

            debug_log(f"[Backdoor] Extracted channel_id: {channel_id}", xbmc.LOGINFO)

            if not channel_id:
                debug_log(f"[Backdoor] No channel_id found, returning original URL", xbmc.LOGWARNING)
                return url

            stream_url = f"https://daddylive.mov/live/stream={channel_id}"
            result = self._resolve_stream(channel_id, ref_url=stream_url)
            self._update_last_request_time()

            if result is not None:
                debug_log(f"[Backdoor] Found resportz stream: {result.address[:100]}", xbmc.LOGINFO)
                debug_log(f"[Backdoor] ========== get_link END (SUCCESS) ==========", xbmc.LOGINFO)
                return result

            debug_log(f"[Backdoor] No valid stream found, returning original URL", xbmc.LOGWARNING)
            return url

        except Exception as e:
            debug_log(f"[Backdoor] Error in get_link: {str(e)}", xbmc.LOGERROR)
            debug_log(f"[Backdoor] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
            return url
