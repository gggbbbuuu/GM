from ..models import *
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from ..util.m3u8_src import scan_page
from urllib3.util import SKIP_HEADER
import xbmc
import re
import tempfile
import base64

class RoxieStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["roxiestreams.info","roxiestreams.live","roxiestreams.cc"]
        self.name = "RoxieStreams"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        
        # Get all nav-links
        nav_links = soup.select("a.nav-link")
        xbmc.log(f"[RoxieStreams] Found {len(nav_links)} nav-links", xbmc.LOGINFO)
        
        for nav_link in nav_links:
            league = nav_link.text.strip()
            href = nav_link.get("href")
            if not href or href == "#" or "discord" in href.lower() or not href.startswith("http"):
                xbmc.log(f"[RoxieStreams] Skipping nav-link: {league} ({href})", xbmc.LOGINFO)
                continue
            
            xbmc.log(f"[RoxieStreams] Processing league: {league} - {href}", xbmc.LOGINFO)
            
            try:
                r = requests.get(href, timeout=self.timeout).text
                soup_league = BeautifulSoup(r, "html.parser")
                
                # Find all table rows
                all_links = soup_league.find_all("td")
                
                xbmc.log(f"[RoxieStreams] Found {len(all_links)} td elements for {league}", xbmc.LOGINFO)
                
                for td in all_links:
                    a = td.find("a")
                    if not a:
                        continue
                    
                    event_href = a.get("href")
                    title = a.text.strip()
                    # Skip if no valid href or title
                    if not event_href or not title or event_href == "#":
                        continue
                    
                    if "roxiestreams" in event_href and "streams" in event_href:
                        items.append(JetItem(title=title, links=[JetLink(event_href, links=True)], league=league))
                        xbmc.log(f"[RoxieStreams] Added event: {title} -> {event_href}", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"[RoxieStreams] Error processing league {league}: {e}", xbmc.LOGERROR)
                
            if self.progress_update(progress, league):
                break
        
        xbmc.log(f"[RoxieStreams] Total items found: {len(items)}", xbmc.LOGINFO)
        return items
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        xbmc.log(f"[RoxieStreams] get_links called for: {url.address}", xbmc.LOGINFO)
        links = []
        try:
            html = requests.get(url.address, headers={"Accept-Encoding": SKIP_HEADER}).text
            soup = BeautifulSoup(html, "html.parser")
            buttons = soup.select("button.streambutton")
            if buttons:
                xbmc.log(f"[RoxieStreams] Found {len(buttons)} stream buttons", xbmc.LOGINFO)
                subdomain = 'daffodil'# Default subdomain
                # Fetch domains from domains.txt
                domains_list = []
                try:
                    domains_url = f"https://{self.domains[0]}/domains.txt"
                    xbmc.log(f"[RoxieStreams] Fetching domains from: {domains_url}", xbmc.LOGINFO)
                    domains_response = requests.get(domains_url, timeout=self.timeout)
                    if domains_response.status_code == 200:
                        domains_list = [d.strip() for d in domains_response.text.strip().split('\n') if d.strip()]
                        xbmc.log(f"[RoxieStreams] Loaded {len(domains_list)} domains from domains.txt: {domains_list}", xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f"[RoxieStreams] Failed to fetch domains.txt: {e}", xbmc.LOGERROR)
                
                if not domains_list:
                    domains_list = ['shadow-ran.online', 'shadow-network.info', 'shadow-tv.net']
                    xbmc.log(f"[RoxieStreams] Using fallback domains: {domains_list}", xbmc.LOGINFO)
                fallback_domain = domains_list[0]
                scripts = soup.find_all("script")
                for script in scripts:
                    script_content = script.string or script.text or ""
                    if not script_content:
                        continue
                    # Find subdomain variable
                    subdomain_match = re.search(r"var\s+subdomain\s*=\s*['\"]([^'\"]+)['\"]", script_content)
                    if subdomain_match:
                        subdomain = subdomain_match.group(1)
                        xbmc.log(f"[RoxieStreams] Found subdomain: {subdomain}", xbmc.LOGINFO)
                        break
                for idx, button in enumerate(buttons, 1):
                    onclick = button.get("onclick", "")
                    button_text = button.get_text(strip=True) or f"Stream {idx}"
                    
                    # Try new format first: showPlayer('clappr', 'https://601.833577.xyz/daffodil.m3u8')
                    direct_url_match = re.search(r"showPlayer\([^,]+,\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", onclick)
                    if direct_url_match:
                        stream_url = direct_url_match.group(1)
                        xbmc.log(f"[RoxieStreams] Button '{button_text}' (direct URL): {stream_url}", xbmc.LOGINFO)
                        link = JetLink(address=stream_url, name=button_text, resolveurl=False, inputstream=JetInputstreamFFmpegDirect.default())
                        links.append(link)
                    else:
                        # Try old format: getRandomStream('usa.m3u8', 'daffodil')
                        stream_match = re.search(r"getRandomStream\(['\"]([^'\"]+\.m3u8)['\"](?:,\s*['\"]([^'\"]+)['\"])?\)", onclick)
                        if stream_match:
                            stream_path = stream_match.group(1)
                            button_subdomain = stream_match.group(2) if stream_match.group(2) else subdomain
                            stream_url = f"https://{button_subdomain}.{fallback_domain}/{stream_path}"
                            xbmc.log(f"[RoxieStreams] Button '{button_text}' (constructed URL): {stream_url}", xbmc.LOGINFO)
                            link = JetLink(address=stream_url, name=button_text, resolveurl=False, inputstream=JetInputstreamFFmpegDirect.default())
                            links.append(link)
        
        except Exception as e:
            xbmc.log(f"[RoxieStreams] Exception in get_links: {e}", xbmc.LOGERROR)
        
        if links:
            xbmc.log(f"[RoxieStreams] Returning {len(links)} links", xbmc.LOGINFO)
            return links
        # Fallback to single link extraction
        xbmc.log(f"[RoxieStreams] No stream buttons found, falling back to get_link", xbmc.LOGINFO)
        return [self.get_link(url)]
    
    def get_link(self, url: JetLink) -> JetLink:
        xbmc.log(f"[RoxieStreams] get_link called for: {url.address}", xbmc.LOGINFO)
        # 1. Try to extract stream buttons and m3u8 URLs
        try:
            html = requests.get(url.address, headers={"Accept-Encoding": SKIP_HEADER}).text
            xbmc.log(f"[RoxieStreams] HTML fetched for {url.address} (length: {len(html)})", xbmc.LOGINFO)
            soup = BeautifulSoup(html, "html.parser")
            buttons = soup.select("button.streambutton")
            if buttons:
                xbmc.log(f"[RoxieStreams] Found {len(buttons)} stream buttons", xbmc.LOGINFO)
                subdomain = 'daffodil'
                fallback_domain = 'shadow-ran.online'
                scripts = soup.find_all("script")
                for script in scripts:
                    script_content = script.string or script.text or ""
                    if not script_content:
                        continue
                    subdomain_match = re.search(r"var\s+subdomain\s*=\s*['\"]([^'\"]+)['\"]", script_content)
                    if subdomain_match:
                        subdomain = subdomain_match.group(1)
                        xbmc.log(f"[RoxieStreams] Found subdomain: {subdomain}", xbmc.LOGINFO)
                first_button = buttons[0]
                onclick = first_button.get("onclick", "")
                xbmc.log(f"[RoxieStreams] First button onclick: {onclick}", xbmc.LOGINFO)
                
                # Try new format first: showPlayer('clappr', 'https://601.833577.xyz/daffodil.m3u8')
                direct_url_match = re.search(r"showPlayer\([^,]+,\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", onclick)
                if direct_url_match:
                    stream_url = direct_url_match.group(1)
                    xbmc.log(f"[RoxieStreams] Found direct m3u8 URL: {stream_url}", xbmc.LOGINFO)
                    return JetLink(address=stream_url, inputstream=JetInputstreamFFmpegDirect.default(), resolveurl=False)
                stream_match = re.search(r"getRandomStream\(['\"]([^'\"]+\.m3u8)['\"](?:,\s*['\"]([^'\"]+)['\"])?\)", onclick)
                if stream_match:
                    stream_path = stream_match.group(1)
                    button_subdomain = stream_match.group(2) if stream_match.group(2) else subdomain
                    # Construct the stream URL
                    stream_url = f"https://{button_subdomain}.{fallback_domain}/{stream_path}"
                    xbmc.log(f"[RoxieStreams] Constructed stream URL: {stream_url}", xbmc.LOGINFO)
                    return JetLink(address=stream_url, inputstream=JetInputstreamFFmpegDirect.default(), resolveurl=False)
            # 2. Try static extraction as fallback
            link = scan_page(url.address, headers={"Accept-Encoding": SKIP_HEADER})
            if link is not None:
                if hasattr(link, 'resolveurl'):
                    link.resolveurl = False
                xbmc.log(f"[RoxieStreams] scan_page succeeded: {getattr(link, 'address', None)}", xbmc.LOGINFO)
                return link
            # 3. Enhanced script parsing for m3u8 URLs
            scripts = soup.find_all("script")
            for script in scripts:
                script_content = script.string or script.text or ""
                if not script_content:
                    continue
                script_lower = script_content.lower()
                # Existing Clappr
                clappr_match = re.search(r"source\s*:\s*['\"](https?://[^'\"]+\.m3u8[^'\"]*)['\"]", script_lower)
                if clappr_match:
                    xbmc.log(f"[RoxieStreams] Found Clappr m3u8: {clappr_match.group(1)}", xbmc.LOGINFO)
                    return JetLink(address=clappr_match.group(1),inputstream=JetInputstreamFFmpegDirect.default(), resolveurl=False)
                # Existing generic
                found = re.findall(r'(https?://[^\'\"]+\.m3u8[^\'\"]*)', script_lower)
                if found:
                    xbmc.log(f"[RoxieStreams] Found m3u8 in script: {found[0]}", xbmc.LOGINFO)
                    return JetLink(address=found[0],inputstream=JetInputstreamFFmpegDirect.default(), resolveurl=False)
                #patterns for Video.js, JW Player, or obfuscated
                videojs_match = re.search(r"(?:src|file|playlist)\s*[:=]\s*['\"](https?://[^'\"]+\.m3u8[^'\"]*)['\"]", script_lower)
                if videojs_match:
                    xbmc.log(f"[RoxieStreams] Found Video.js/JW m3u8: {videojs_match.group(1)}", xbmc.LOGINFO)
                    return JetLink(address=videojs_match.group(1),inputstream=JetInputstreamFFmpegDirect.default(), resolveurl=False)
                # Base64-decoded URLs
                b64_matches = re.findall(r'([A-Za-z0-9+/]{20,}=*)(?:\.m3u8|\.js)', script_lower)
                for b64_str in b64_matches:
                    try:
                        decoded = base64.b64decode(b64_str).decode('utf-8')
                        if 'm3u8' in decoded:
                            m3u8_url = re.search(r'(https?://[^\'\" ]+\.m3u8)', decoded)
                            if m3u8_url:
                                xbmc.log(f"[RoxieStreams] Decoded b64 m3u8: {m3u8_url.group(1)}", xbmc.LOGINFO)
                                return JetLink(address=m3u8_url.group(1),inputstream=JetInputstreamFFmpegDirect.default(), resolveurl=False)
                    except:
                        pass
            
            # 4. Try iframe src only if not YouTube
            iframe = soup.find("iframe")
            if iframe and iframe.get("src"):
                iframe_url = iframe["src"]
                # Skip YouTube iframes
                if "youtube.com/live_chat" in iframe_url:
                    xbmc.log(f"[RoxieStreams] Skipping YouTube chat iframe: {iframe_url}", xbmc.LOGINFO)
                else:
                    xbmc.log(f"[RoxieStreams] Found iframe src: {iframe_url}", xbmc.LOGINFO)
                    if iframe_url.startswith("//"):
                        iframe_url = "https:" + iframe_url
                    iframe_link = scan_page(iframe_url, headers={"Accept-Encoding": SKIP_HEADER})
                    # If m3u8 uses .js segments, replace with .ts 
                    if iframe_link is not None and hasattr(iframe_link, 'address') and ".m3u8" in iframe_link.address:
                        m3u8_text = requests.get(iframe_link.address).text
                        if re.search(r"\.js", m3u8_text):
                            lines = m3u8_text.splitlines()
                            patched_lines = []
                            for line in lines:
                                if line.strip().endswith('.js') and not line.startswith('#') and '.ts' not in line:  # Assume it's a segment
                                    patched_line = re.sub(r"\.js($|[?#&/])", r".ts\1", line)  # Preserve query/frag
                                    patched_lines.append(patched_line)
                                    xbmc.log(f"[RoxieStreams] Patched segment: {line.strip()} -> {patched_line.strip()}", xbmc.LOGINFO)
                                else:
                                    patched_lines.append(line)
                            patched = '\n'.join(patched_lines)
                            # Save patched m3u8 to temp file
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".m3u8", mode="w", encoding="utf-8") as f:
                                f.write(patched)
                                iframe_link.address = f.name
                            #Check for segments and resolve
                            base_url = iframe_link.address.rsplit('/', 1)[0] + '/'
                            for line in patched.splitlines():
                                if line.strip().endswith('.ts') and not line.startswith('http'):
                                    full_seg = base_url + line.strip()
                                    try:
                                        resp = requests.head(full_seg, timeout=5)
                                        xbmc.log(f"Resolved segment {line.strip()}: {resp.status_code} ({full_seg})", xbmc.LOGINFO)
                                    except Exception as e:
                                        xbmc.log(f"Resolved segment {line.strip()}: ERROR {e}", xbmc.LOGERROR)
                        
                        if hasattr(iframe_link, 'resolveurl'):
                            iframe_link.resolveurl = False
                        # Log playlist
                        with open(iframe_link.address, "r", encoding="utf-8") as logf:
                            xbmc.log("--- M3U8 Playlist Contents ---", xbmc.LOGINFO)
                            xbmc.log(logf.read(), xbmc.LOGINFO)
                        xbmc.log(f"[RoxieStreams] Returning iframe_link: {getattr(iframe_link, 'address', None)}", xbmc.LOGINFO)
                        return iframe_link
        except Exception as e:
            xbmc.log(f"[RoxieStreams] Exception in get_link: {e}", xbmc.LOGERROR)
        
        # 3. Final fallback: Try proxy only if all above fail
        # try:
        #     proxy_url = f"http://localhost:5010/extract_m3u8?url={url.address}&referer=https://{self.domains[0]}"
        #     resp = requests.get(proxy_url, timeout=60)  # Increased timeout for waits/clicks
        #     if resp.status_code == 200 and resp.text.strip().startswith("http"):
        #         xbmc.log(f"[RoxieStreams] Proxy found m3u8: {resp.text.strip()}", xbmc.LOGINFO)
        #         return JetLink(address=resp.text.strip(), resolveurl=False)
        #     else:
        #         xbmc.log(f"[RoxieStreams] Proxy failed: status {resp.status_code}, response: {resp.text}", xbmc.LOGERROR)
        # except Exception as e:
        #     xbmc.log(f"[RoxieStreams] Proxy error: {e}", xbmc.LOGERROR)
        
        xbmc.log(f"[RoxieStreams] All methods failed for {url.address}. Returning original.", xbmc.LOGWARNING)
        return JetLink(address=url.address, inputstream=JetInputstreamFFmpegDirect.default(), resolveurl=False)