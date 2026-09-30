from ..models import *
from typing import Optional, List
import re
import json
import requests
from urllib.parse import urlparse, parse_qs, unquote, quote, urljoin
from ..tools import debug_log
from .._core import get_session
from ..util import embedsportstop
from ..util.stream_proxy import get_stream_proxy
import xbmc


def _ffmpegdirect_live() -> JetInputstreamFFmpegDirect:
    """inputstream.ffmpegdirect in stream_mode='live' (NOT the 'timeshift' default)."""
    return JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live")


class ReedStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["reedstreams.to", "api.reedstreams.link"]
        self.name = "ReedStreams"
        self.short_name = "REED"
        self.timeout = 15
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        self.player_ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        self.smart_tv_ua = "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/16.0 TV Safari/537.36"

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.verify = False
        s.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        return s

    def _proxy_url(self, embed_url: str, name: str) -> str:
        """Create a proxy URL that points back to this extractor for resolution."""
        return f"https://{self.domains[0]}/jetextractor/reedstreams?url={quote(embed_url, safe='')}&name={quote(name, safe='')}"

    def _decode_proxy(self, address: str) -> str:
        """Extract the original embed URL from a proxy URL."""
        parsed = urlparse(address)
        if parsed.path == "/jetextractor/reedstreams" and parsed.netloc in self.domains:
            return parse_qs(parsed.query).get("url", [""])[0]
        return address

    def _select_variant(self, session: requests.Session, master_url: str, headers: dict) -> str:
        """Fetch master playlist and pick a real HLS variant, preferring highest quality."""
        try:
            fetch_headers = dict(headers)
            fetch_headers.setdefault("Accept", "*/*")
            fetch_headers.setdefault("Connection", "close")
            fetch_headers.setdefault("Icy-MetaData", "1")

            r = session.get(master_url, headers=fetch_headers, timeout=self.timeout, verify=False)
            text = r.text
            debug_log(f"[ReedStreams] Master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
            if "#EXTM3U" not in text:
                debug_log("[ReedStreams] Master fetch failed, retrying with Chrome/143 UA", xbmc.LOGWARNING)
                fetch_headers["User-Agent"] = self.player_ua
                r = session.get(master_url, headers=fetch_headers, timeout=self.timeout, verify=False)
                text = r.text
                debug_log(f"[ReedStreams] Retry master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
                if "#EXTM3U" not in text:
                    debug_log("[ReedStreams] Upstream did not return a valid M3U8", xbmc.LOGERROR)
                    return ""

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            variants = []
            for i, line in enumerate(lines):
                if line.upper().startswith("#EXT-X-STREAM-INF"):
                    bw = 0
                    m = re.search(r'BANDWIDTH=(\d+)', line)
                    if m:
                        bw = int(m.group(1))
                    for j in range(i + 1, len(lines)):
                        if not lines[j].startswith("#"):
                            variants.append((bw, lines[j]))
                            break
            if not variants:
                debug_log("[ReedStreams] No variants found, using master URL", xbmc.LOGINFO)
                return master_url

            debug_log(f"[ReedStreams] Found {len(variants)} variant(s): {variants}", xbmc.LOGINFO)
            if len(variants) == 1:
                return urljoin(master_url, variants[0][1])

            # Always prefer the highest bandwidth variant
            variants.sort(key=lambda x: x[0], reverse=True)
            return urljoin(master_url, variants[0][1])
        except Exception as e:
            debug_log(f"[ReedStreams] _select_variant error: {e}", xbmc.LOGERROR)
            return master_url

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        session = self._session()
        api_url = "https://api.reedstreams.link/api/matches/all"
        
        try:
            debug_log(f"[ReedStreams] Fetching matches from {api_url}", xbmc.LOGINFO)
            resp = session.get(api_url, timeout=self.timeout)
            if resp.status_code != 200:
                debug_log(f"[ReedStreams] API returned status {resp.status_code}", xbmc.LOGWARNING)
                return items
            
            matches = resp.json()
            debug_log(f"[ReedStreams] Got {len(matches)} matches", xbmc.LOGINFO)
            
            for match in matches:
                match_id = match.get("id", "")
                title = match.get("title", "Unknown Match")
                category = match.get("category", "Sports")
                date_ts = match.get("date", 0)
                
                # Build match page URL
                match_url = f"https://reedstreams.to/match/{match_id}"
                
                # Create JetLink to match page (will be resolved in get_links)
                link = JetLink(
                    address=match_url,
                    name=title,
                    links=True,  # This will trigger get_links()
                )
                
                item = JetItem(
                    title=title,
                    links=[link],
                    league=category,
                )
                
                if date_ts:
                    from datetime import datetime
                    item.starttime = datetime.fromtimestamp(date_ts / 1000)
                
                items.append(item)
                
        except Exception as e:
            debug_log(f"[ReedStreams] Error fetching matches: {e}", xbmc.LOGERROR)
            import traceback
            debug_log(traceback.format_exc(), xbmc.LOGERROR)
        
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        match_url = url.address
        
        debug_log(f"[ReedStreams] get_links called for: {match_url}", xbmc.LOGINFO)
        
        # Extract match ID from URL
        match_id_match = re.search(r'/match/([^/?]+)', match_url)
        if not match_id_match:
            debug_log(f"[ReedStreams] Could not extract match ID from {match_url}", xbmc.LOGWARNING)
            return links
        
        match_id = match_id_match.group(1)
        
        # Fetch match page JSON with retry logic
        session = self._session()
        max_retries = 3
        sources = []
        for attempt in range(max_retries):
            try:
                debug_log(f"[ReedStreams] Fetching match data for {match_id} (attempt {attempt+1}/{max_retries})", xbmc.LOGINFO)
                resp = session.get(match_url, timeout=self.timeout)
                if resp.status_code != 200:
                    debug_log(f"[ReedStreams] Match page returned status {resp.status_code}", xbmc.LOGWARNING)
                    return links
                
                match_data = resp.json()
                sources = match_data.get("sources", [])
                debug_log(f"[ReedStreams] Got {len(sources)} sources", xbmc.LOGINFO)
                break  # Success, exit retry loop
                
            except requests.exceptions.Timeout:
                debug_log(f"[ReedStreams] Timeout on attempt {attempt+1}/{max_retries}", xbmc.LOGWARNING)
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    debug_log(f"[ReedStreams] All {max_retries} attempts timed out", xbmc.LOGERROR)
                    return links
            except Exception as e:
                debug_log(f"[ReedStreams] Error fetching match data: {e}", xbmc.LOGERROR)
                import traceback
                debug_log(traceback.format_exc(), xbmc.LOGERROR)
                return links
        
        # Process sources
        try:
            for source in sources:
                source_name = source.get("sourceName", source.get("source", "Unknown"))
                embed_url = source.get("embedUrl", "")
                provider = source.get("provider", "")
                quality = source.get("quality", "")
                language = source.get("language", "")
                hd = source.get("hd", False)
                
                if not embed_url:
                    continue
                
                # Build display name
                display_name = source_name
                if quality:
                    display_name += f" [{quality}]"
                if language:
                    display_name += f" ({language})"
                
                # Create JetLink with proxy URL that points back to this extractor
                proxy_url = self._proxy_url(embed_url, display_name)
                link = JetLink(
                    address=proxy_url,
                    name=display_name,
                )
                links.append(link)
                
                debug_log(f"[ReedStreams] Added source: {display_name} -> {embed_url}", xbmc.LOGDEBUG)
                
        except Exception as e:
            debug_log(f"[ReedStreams] Error processing sources: {e}", xbmc.LOGERROR)
            import traceback
            debug_log(traceback.format_exc(), xbmc.LOGERROR)
        
        return links

    def get_link(self, url: JetLink) -> JetLink:
        # Decode proxy URL to get the original embed URL
        embed_url = self._decode_proxy(url.address)
        if not embed_url:
            embed_url = url.address
        
        debug_log(f"[ReedStreams] get_link called for: {embed_url}", xbmc.LOGINFO)
        
        stream_url = None
        headers = {"User-Agent": self.user_agent}
        
        try:
            parsed = urlparse(embed_url)
            host = parsed.netloc.lower()
            
            # Handle embed.st sources (admin, delta, echo, golf)
            if "embed.st" in host:
                debug_log(f"[ReedStreams] Resolving embed.st URL via embedsportstop", xbmc.LOGINFO)
                stream_url = embedsportstop.get_embedsportstop_stream(embed_url)
                headers["Referer"] = f"https://{host}/"
                headers["Origin"] = f"https://{host}"
            
            # Handle embedsports.top sources (foxtrot, etc.)
            elif "embedsports.top" in host:
                debug_log(f"[ReedStreams] Resolving embedsports.top URL via embedsportstop", xbmc.LOGINFO)
                try:
                    stream_url = embedsportstop.get_embedsportstop_stream(embed_url)
                    headers["Referer"] = f"https://{host}/"
                    headers["Origin"] = f"https://{host}"
                except Exception as e:
                    debug_log(f"[ReedStreams] Error resolving embedsports.top: {e}", xbmc.LOGWARNING)
                    return None
            
            # Handle watchthematch.online (krishna provider)
            elif "watchthematch.online" in host:
                debug_log(f"[ReedStreams] Resolving watchthematch.online URL", xbmc.LOGINFO)
                # Extract ID from path: /embed/{id} -> {id}
                path_match = re.search(r'/embed/([^/?]+)', embed_url)
                if path_match:
                    channel_id = path_match.group(1)
                    stream_url = f"https://watchthematch.online/v1/channel/{channel_id}/index.m3u8"
                    debug_log(f"[ReedStreams] Constructed stream URL: {stream_url}", xbmc.LOGINFO)
                    headers["Referer"] = "https://watchthematch.online/"
                    headers["Origin"] = "https://watchthematch.online"
                else:
                    debug_log(f"[ReedStreams] Could not extract channel ID from {embed_url}", xbmc.LOGWARNING)
                    return None
            
            # Handle sportsembed.su (iframes to embedindia.st)
            elif "sportsembed.su" in host:
                debug_log(f"[ReedStreams] Resolving sportsembed.su (following iframe)", xbmc.LOGINFO)
                session = self._session()
                try:
                    resp = session.get(embed_url, timeout=20)  # Increased timeout
                    if resp.status_code == 200:
                        # Find iframe to embedindia.st
                        iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.I)
                        if iframe_match:
                            iframe_url = iframe_match.group(1)
                            if iframe_url.startswith("//"):
                                iframe_url = "https:" + iframe_url
                            debug_log(f"[ReedStreams] Found iframe: {iframe_url}", xbmc.LOGINFO)
                            
                            if "embedindia" in iframe_url:
                                stream_url = embedsportstop.get_embedsportstop_stream(iframe_url)
                                iframe_host = urlparse(iframe_url).netloc
                                headers["Referer"] = f"https://{iframe_host}/"
                                headers["Origin"] = f"https://{iframe_host}"
                        else:
                            debug_log(f"[ReedStreams] No iframe found in sportsembed.su page", xbmc.LOGWARNING)
                    else:
                        debug_log(f"[ReedStreams] sportsembed.su returned status {resp.status_code}", xbmc.LOGWARNING)
                except requests.exceptions.Timeout:
                    debug_log(f"[ReedStreams] Timeout fetching sportsembed.su", xbmc.LOGWARNING)
                    return None
                except Exception as e:
                    debug_log(f"[ReedStreams] Error resolving sportsembed.su: {e}", xbmc.LOGWARNING)
                    return None
            
            # Handle viloud.tv (m3u8 in URL parameter)
            elif "viloud.tv" in host:
                debug_log(f"[ReedStreams] Resolving viloud.tv (extracting URL param)", xbmc.LOGINFO)
                qs = parse_qs(parsed.query)
                url_param = qs.get("url", [None])[0]
                if url_param:
                    stream_url = unquote(url_param)
                    debug_log(f"[ReedStreams] Extracted m3u8 from URL param: {stream_url}", xbmc.LOGINFO)
                    headers["Referer"] = "https://player.viloud.tv/"
                    headers["Origin"] = "https://player.viloud.tv"
            
            # Handle embedindia.st directly
            elif "embedindia" in host:
                debug_log(f"[ReedStreams] Resolving embedindia URL via embedsportstop", xbmc.LOGINFO)
                stream_url = embedsportstop.get_embedsportstop_stream(embed_url)
                headers["Referer"] = f"https://{host}/"
                headers["Origin"] = f"https://{host}"
            
            # Handle edgesport.cfd (complex obfuscation - best effort)
            elif "edgesport.cfd" in host:
                debug_log(f"[ReedStreams] edgesport.cfd requires complex deobfuscation - skipping", xbmc.LOGWARNING)
                # This source type has multi-layer obfuscation that's difficult to decode
                # Return None to skip this source
                return None
            
            else:
                debug_log(f"[ReedStreams] Unknown host: {host} - attempting generic resolution", xbmc.LOGWARNING)
                # Try generic iframe/m3u8 scanning
                from .._core import find_iframes, find_m3u8
                session = self._session()
                resp = session.get(embed_url, timeout=self.timeout)
                if resp.status_code == 200:
                    # Try to find m3u8 directly
                    m3u8 = find_m3u8(resp.text, embed_url)
                    if m3u8:
                        stream_url = m3u8
                    else:
                        # Try iframes
                        iframes = find_iframes(resp.text, embed_url)
                        if iframes:
                            debug_log(f"[ReedStreams] Found iframes: {iframes}", xbmc.LOGDEBUG)
                            # Try to resolve first iframe
                            for iframe_url in iframes:
                                if "embedindia" in iframe_url or "embed.st" in iframe_url:
                                    stream_url = embedsportstop.get_embedsportstop_stream(iframe_url)
                                    break
            
            if not stream_url:
                debug_log(f"[ReedStreams] Could not resolve stream URL from {embed_url}", xbmc.LOGWARNING)
                return None
            
            debug_log(f"[ReedStreams] Resolved stream URL: {stream_url}", xbmc.LOGINFO)
            
            # Select best variant from master playlist
            session = self._session()
            stream_url = self._select_variant(session, stream_url, headers)
            if not stream_url:
                debug_log("[ReedStreams] Could not select a valid variant", xbmc.LOGERROR)
                return None
            debug_log(f"[ReedStreams] Selected variant URL: {stream_url}", xbmc.LOGINFO)
            
            # Route through stream proxy with Smart TV User-Agent
            proxy = get_stream_proxy(
                "reedstreams",
                headers,
                options={
                    "strip_png": True,
                    "manifest_png_to_ts": True,
                    "upstream_keep_alive": True,
                    "prefetch_segments": True,
                    "keep_alive": False,
                    "user_agent": self.smart_tv_ua,
                },
            )
            proxy_url = proxy.get_proxy_url(stream_url, headers)
            debug_log(f"[ReedStreams] Proxy URL: {proxy_url}", xbmc.LOGINFO)
            
            return JetLink(
                proxy_url,
                headers=headers,
                inputstream=_ffmpegdirect_live()
            )
            
        except Exception as e:
            debug_log(f"[ReedStreams] Error resolving {embed_url}: {e}", xbmc.LOGERROR)
            import traceback
            debug_log(traceback.format_exc(), xbmc.LOGERROR)
            return None
