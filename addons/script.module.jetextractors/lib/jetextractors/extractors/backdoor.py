from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
import requests
import re
import json
from typing import Optional, List
import xbmc
import time
import random
import traceback
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_module_last_request_time = 0
_events_cache = None
_events_cache_time = 0
_EVENTS_CACHE_TTL = 300  # 5 minutes

class Backdoor(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streameast.mov"]
        self.name = "Backdoor"
        self.session = requests.Session()

        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self.ott_agents = [       
            "VLC/3.0.18 LibVLC/3.0.18",
            "TiviMate/4.7.0 (Android)",
            "iMPlayer/3.9.5 (Linux;Android 14) AndroidXMedia3/1.8.0",
            "OTT-IPTV/1.0 (Linux; Android 10; BR) XtreamPlayer/5.0"
        ]

        self.min_request_interval = 5  # Increased from 2 to 5 seconds
        self.preferred_domains = ["vomos", "zalis"]
        self.dead_domains = ["pontos"]
        self._fetch_preferred_domains()

    def _fetch_preferred_domains(self) -> None:
        urls = [
            "https://magnetic.website/Jetextractor/preferred/backdoor.txt",
        ]

        for url in urls:
            try:
                xbmc.log(f"[Backdoor] Fetching preferred domains from: server", xbmc.LOGINFO)
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                }
                r = self.session.get(url, headers=headers, timeout=10, verify=False)

                if r.status_code == 200:
                    domains = []
                    for line in r.text.splitlines():
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        domains.append(line.lower())

                    if domains:
                        self.preferred_domains = domains
                        xbmc.log(f"[Backdoor] Loaded {len(domains)} preferred domains: {domains}", xbmc.LOGINFO)
                        return
                else:
                    xbmc.log(f"[Backdoor] Preferred domains fetch returned status {r.status_code}", xbmc.LOGWARNING)
            except Exception as e:
                xbmc.log(f"[Backdoor] Failed to fetch preferred domains from {url}: {str(e)}", xbmc.LOGWARNING)

        xbmc.log(f"[Backdoor] Using default preferred domains: {self.preferred_domains}", xbmc.LOGINFO)

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        events = self._fetch_events()
        items.extend(events)

        channels = self._fetch_channels()
        items.extend(channels)

        xbmc.log(f"[Backdoor] Total items: {len(items)} ({len(events)} events, {len(channels)} channels)", xbmc.LOGINFO)
        return items

    def _fetch_events(self) -> List[JetItem]:
        global _events_cache, _events_cache_time

        # Return cached events if still valid
        if _events_cache is not None and (time.time() - _events_cache_time) < _EVENTS_CACHE_TTL:
            xbmc.log(f"[Backdoor] Returning {len(_events_cache)} cached events", xbmc.LOGINFO)
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
                    'Origin': 'https://streameast.mov',
                    'Referer': 'https://streameast.mov/',
                }
                
                # Replace the Agent
                headers['User-Agent'] = random.choice(self.ott_agents)

                xbmc.log(f"[Backdoor] Fetching events from API (attempt {attempt + 1}/{max_retries + 1})", xbmc.LOGINFO)

                try:
                    r = self.session.get("https://streameast.mov/api/events", headers=headers, timeout=(3, 5), verify=False, stream=True)
                    try:
                        r.raw.decode_content = True
                        body = b""
                        for chunk in r.raw.stream(64 * 1024, decode_content=True):
                            body += chunk
                            if len(body) > 2 * 1024 * 1024:
                                break
                    finally:
                        r.close()
                except Exception as e:
                    xbmc.log(f"[Backdoor] Events API request failed: {type(e).__name__}: {str(e)[:60]}", xbmc.LOGWARNING)
                    self._update_last_request_time()
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(1, 2)
                        xbmc.log(f"[Backdoor] Retrying events fetch in {backoff:.1f}s...", xbmc.LOGWARNING)
                        time.sleep(backoff)
                        continue
                    break

                self._update_last_request_time()

                if r.status_code != 200:
                    xbmc.log(f"[Backdoor] API HTTP Error {r.status_code}", xbmc.LOGWARNING)
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(1, 2)
                        time.sleep(backoff)
                        continue
                    break

                try:
                    api_data = json.loads(body)
                except Exception as e:
                    xbmc.log(f"[Backdoor] Failed to parse API JSON: {str(e)}", xbmc.LOGWARNING)
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(1, 2)
                        time.sleep(backoff)
                        continue
                    break

                if not isinstance(api_data, list) or len(api_data) == 0:
                    break

                first_item = api_data[0]
                if not isinstance(first_item, dict) or 'categories' not in first_item:
                    break

                categories = first_item.get('categories', {})
                if not isinstance(categories, dict):
                    break

                xbmc.log(f"[Backdoor] Found {len(categories)} categories", xbmc.LOGINFO)

                for category, category_info in categories.items():
                    if not isinstance(category_info, list):
                        continue

                    if category.lower() in ['popular live events', 'tv shows']:
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
                            if isinstance(ch, dict) and ch.get('channel_id'):
                                channel_id = str(ch.get('channel_id'))
                                break

                        if not channel_id:
                            continue

                        stream_url = f"https://streameast.mov/live/stream={channel_id}"
                        title = event_name
                        time_str = event_info.get('time', '')
                        if time_str:
                            title = f"{event_name} ({time_str})"

                        items.append(JetItem(title, [JetLink(stream_url, links=True)], league=category))

                xbmc.log(f"[Backdoor] Found {len(items)} events from API", xbmc.LOGINFO)

                # Cache successful results
                _events_cache = list(items)
                _events_cache_time = time.time()
                break

            except Exception as e:
                xbmc.log(f"[Backdoor] Error fetching events: {str(e)}", xbmc.LOGERROR)
                xbmc.log(f"[Backdoor] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
                if attempt < max_retries:
                    backoff = (2 ** attempt) + random.uniform(1, 2)
                    xbmc.log(f"[Backdoor] Retrying events fetch in {backoff:.1f}s...", xbmc.LOGWARNING)
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
                'Origin': 'https://streameast.mov',
                'Referer': 'https://streameast.mov/',
            }
            
            # Replace the Agent
            headers['User-Agent'] = random.choice(self.ott_agents)

            xbmc.log(f"[Backdoor] Fetching channels from API", xbmc.LOGINFO)

            try:
                r = self.session.get("https://streameast.mov/api/channels", headers=headers, timeout=(4, 8), verify=False, stream=True)
                try:
                    r.raw.decode_content = True
                    body = b""
                    for chunk in r.raw.stream(64 * 1024, decode_content=True):
                        body += chunk
                        if len(body) > 4 * 1024 * 1024:
                            break
                finally:
                    r.close()
            except Exception as e:
                xbmc.log(f"[Backdoor] Channels API request failed (skipping): {type(e).__name__}: {str(e)[:60]}", xbmc.LOGWARNING)
                self._update_last_request_time()
                return items
            self._update_last_request_time()

            if r.status_code != 200:
                xbmc.log(f"[Backdoor] Channels API HTTP Error {r.status_code}", xbmc.LOGWARNING)
                return items

            try:
                channels_data = json.loads(body)
            except Exception as e:
                xbmc.log(f"[Backdoor] Failed to parse channels JSON: {str(e)}", xbmc.LOGWARNING)
                return items

            if not isinstance(channels_data, list):
                xbmc.log(f"[Backdoor] Channels data is not a list", xbmc.LOGWARNING)
                return items

            xbmc.log(f"[Backdoor] Found {len(channels_data)} channels", xbmc.LOGINFO)

            for channel in channels_data:
                if not isinstance(channel, dict):
                    continue

                channel_name = channel.get('channel_name', '').strip()
                channel_id = channel.get('channel_id', '')

                if not channel_name or not channel_id:
                    continue

                stream_url = f"https://streameast.mov/live/stream={channel_id}"
                items.append(JetItem(channel_name, [JetLink(stream_url, links=True)], league="Channels"))

            xbmc.log(f"[Backdoor] Added {len(items)} channels to items list", xbmc.LOGINFO)

        except Exception as e:
            xbmc.log(f"[Backdoor] Error fetching channels: {str(e)}", xbmc.LOGERROR)
            xbmc.log(f"[Backdoor] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)

        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        xbmc.log(f"[Backdoor] ========== get_links START ==========", xbmc.LOGINFO)
        xbmc.log(f"[Backdoor] Input URL: {url.address}", xbmc.LOGINFO)

        try:
            self._rate_limit()

            channel_id = None
            match = re.search(r'stream=([^&]+)', url.address)
            if match:
                channel_id = match.group(1)

            xbmc.log(f"[Backdoor] Extracted channel_id: {channel_id}", xbmc.LOGINFO)

            if not channel_id:
                return []

            result = self._resolve_stream(channel_id, ref_url=f"https://resportz.cfd/live/stream-{channel_id}.php")
            self._update_last_request_time()

            if result is not None:
                xbmc.log(f"[Backdoor] Found stream: {result.address[:100]}", xbmc.LOGINFO)
                xbmc.log(f"[Backdoor] ========== get_links END (SUCCESS) ==========", xbmc.LOGINFO)
                return [result]

            xbmc.log(f"[Backdoor] No valid stream found, returning empty list", xbmc.LOGWARNING)
            return []

        except Exception as e:
            xbmc.log(f"[Backdoor] Error in get_links: {str(e)}", xbmc.LOGERROR)
            xbmc.log(f"[Backdoor] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
            return []

    def _resolve_stream(self, channel_id: str, ref_url: str) -> Optional[JetLink]:
        ifr_url = f"https://hamis.romponalis.st/premiumtv/resportz.php?id={channel_id}"
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Referer': ref_url,
        }

        try:
            r = self.session.get(ifr_url, headers=headers, timeout=8, verify=False)
            if r.status_code != 200:
                xbmc.log(f"[Backdoor] Page returned status {r.status_code}", xbmc.LOGWARNING)
                return None
            html = r.text
        except Exception as e:
            xbmc.log(f"[Backdoor] Page fetch failed: {str(e)[:80]}", xbmc.LOGWARNING)
            return None

        stream_url = self._extract_m3u8_from_html(html)
        if not stream_url:
            xbmc.log(f"[Backdoor] No m3u8 URL found in page HTML", xbmc.LOGWARNING)
            return None

        if stream_url.startswith('//'):
            stream_url = 'https:' + stream_url

        self._discover_domains(stream_url)
        if 'jmp2.uk/plu-' in stream_url or 'pluto' in stream_url.lower():
            xbmc.log(f"[Backdoor] Skipping unsupported host: {stream_url[:80]}", xbmc.LOGWARNING)
            return None

        stream_url = self._swap_dead_domain(stream_url)

        link = JetLink(
            address=stream_url,
            headers={'Referer': ifr_url, 'User-Agent': headers['User-Agent']},
            inputstream=JetInputstreamFFmpegDirect.default(),
        )
        return link

    def _extract_m3u8_from_html(self, html: str) -> Optional[str]:
        import base64
        atob_matches = re.findall(r'(?:window\.)?atob\(\s*[\'\"]([A-Za-z0-9+/=]+)[\'\"]\s*\)', html)
        for match in atob_matches:
            try:
                decoded = base64.b64decode(match).decode('ascii', errors='ignore')
                if '.m3u8' in decoded:
                    url_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', decoded)
                    if url_match:
                        return url_match.group(1)
            except Exception:
                continue

        for pattern in [
            r'source\s*[:=]\s*[\'\"](https?://[^\'\"]+\.m3u8[^\'\"]*)[\'\"]',
            r'file\s*[:=]\s*[\'\"](https?://[^\'\"]+\.m3u8[^\'\"]*)[\'\"]',
            r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
        ]:
            match = re.search(pattern, html, re.I)
            if match:
                return match.group(1)

        return None

    def _swap_dead_domain(self, url: str) -> str:
        if not any(dead in url for dead in self.dead_domains):
            return url

        for preferred in self.preferred_domains:
            test_url = url
            for dead in self.dead_domains:
                if dead in test_url:
                    test_url = test_url.replace(dead, preferred)
                    break
            if self._test_stream_url(test_url):
                xbmc.log(f"[Backdoor] Working domain found: {preferred}", xbmc.LOGINFO)
                return test_url

        xbmc.log(f"[Backdoor] No working preferred domain, returning original URL", xbmc.LOGWARNING)
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
                xbmc.log(f"[Backdoor] Working domain found: {preferred}", xbmc.LOGINFO)
                return test_url

        xbmc.log(f"[Backdoor] None of preferred domains worked, using original URL", xbmc.LOGWARNING)
        return url

    def _test_stream_url(self, url: str) -> bool:
        try:
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://hamis.romponalis.st/',
            }
            r = self.session.head(url, headers=headers, timeout=5, verify=False, allow_redirects=True)
            if r.status_code in (200, 302, 303):
                return True
            r2 = self.session.get(url, headers=headers, timeout=5, verify=False, stream=True)
            if r2.status_code == 200:
                content = r2.raw.read(500)
                r2.close()
                if b'#EXTM3U' in content or b'#EXT-X' in content or b'm3u8' in content.lower():
                    return True
        except Exception as e:
            xbmc.log(f"[Backdoor] Test failed for {url[:80]}: {str(e)[:50]}", xbmc.LOGDEBUG)
        return False

    def _discover_domains(self, url: str) -> None:
        m3u8_match = re.search(r'https?://([a-z0-9.-]+)/', url, re.I)
        if m3u8_match:
            domain = m3u8_match.group(1)
            if 'phantemlis' in domain or 'jmp2' not in domain:
                xbmc.log(f"[Backdoor] DISCOVERED DOMAIN: {domain} (full URL: {url[:120]})", xbmc.LOGINFO)

    def _rate_limit(self):
        global _module_last_request_time
        elapsed = time.time() - _module_last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed + random.uniform(1.0, 3.0)
            xbmc.log(f"[Backdoor] Rate limiting: waiting {wait_time:.1f}s", xbmc.LOGINFO)
            time.sleep(wait_time)

    def _update_last_request_time(self):
        global _module_last_request_time
        _module_last_request_time = time.time()

    def get_link(self, url: JetLink) -> JetLink:
        xbmc.log(f"[Backdoor] ========== get_link START ==========", xbmc.LOGINFO)
        xbmc.log(f"[Backdoor] Input URL: {url.address}", xbmc.LOGINFO)

        try:
            self._rate_limit()

            channel_id = None
            match = re.search(r'stream=([^&]+)', url.address)
            if match:
                channel_id = match.group(1)

            xbmc.log(f"[Backdoor] Extracted channel_id: {channel_id}", xbmc.LOGINFO)

            if not channel_id:
                xbmc.log(f"[Backdoor] No channel_id found, returning original URL", xbmc.LOGWARNING)
                return url

            result = self._resolve_stream(channel_id, ref_url=f"https://resportz.cfd/live/stream-{channel_id}.php")
            self._update_last_request_time()

            if result is not None:
                xbmc.log(f"[Backdoor] Found resportz stream: {result.address[:100]}", xbmc.LOGINFO)
                xbmc.log(f"[Backdoor] ========== get_link END (SUCCESS) ==========", xbmc.LOGINFO)
                return result

            xbmc.log(f"[Backdoor] No valid stream found, returning original URL", xbmc.LOGWARNING)
            return url

        except Exception as e:
            xbmc.log(f"[Backdoor] Error in get_link: {str(e)}", xbmc.LOGERROR)
            xbmc.log(f"[Backdoor] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
            return url
