from ..models import *
from ..models import JetInputstreamAdaptive
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from ..util.m3u8_src import scan_page
from urllib3.util import SKIP_HEADER
from ..util.stream_proxy import get_stream_proxy
import xbmc
import re
import tempfile
import base64
import json as _json


#https://mainstreams.pro/hls/zayrtezafgvdv68.m3u8?st=FhrJ8hQM_4PmQoYvIdaav8prg8b1IntgYWMaa8OESgU&e=1770599872|Referer=https://streams.center/embed/ch68.php&Origin=https://streams.center&User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
#https://mainstreams.pro/hls/zayrtezafgvdv68.m3u8?st=FhrJ8hQM_4PmQoYvIdaav8prg8b1IntgYWMaa8OESgU&e=1770599872|User-Agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F107.0.0.0+Safari%2F537.36&Referer=https%3A%2F%2Fstreams.center%2Fembed%2Fch68.php&Origin=https%3A%2F%2Fstreams.center

class RoxieStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["roxiestreams.info","roxiestreams.live","roxiestreams.cc"]
        self.name = "RoxieStreams"

    def _process_stream_url(self, stream_url: str) -> tuple:
        headers = {
            "Origin": "https://roxiestreams.info",
            "Referer": "https://roxiestreams.info/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "DNT": "1",
            "Sec-Ch-Ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
        }
        inputstream = JetInputstreamFFmpegDirect.default()
        # if "heritagebd.shop" in stream_url:
        #     stream_url = stream_url.replace("heritagebd.shop", "teicontools.com.br")
        #     headers = {
        #         "Referer": "https://roxiestreams.info/",
        #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        #     }
        if ".mpd" in stream_url:
            # DRM-protected streams need license URL
            license_url = "https://drm.discovery.com/license-server"
            if "indazn.com" in stream_url or "dazn" in stream_url.lower():
                license_url = "https://drm.discovery.com/license-server"
            inputstream = JetInputstreamAdaptive("mpd", license_key=license_url)
        return stream_url, headers, inputstream

    def _resolve_raw_page(self, raw_url: str, button_text: str = None) -> Optional[JetLink]:
        """Resolve a roxiestreams /raw/<channel> page.

        These pages embed a Shaka Player that loads a DASH (.mpd) manifest and
        often use ClearKey DRM (drm.clearKeys map). ClearKey is supported by
        Kodi's inputstream.adaptive, so we can play these directly rather than
        failing back to the raw (unplayable) page URL.
        """
        try:
            resp = requests.get(
                raw_url,
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
                    "Referer": "https://roxiestreams.info/",
                    "Origin": "https://roxiestreams.info",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            if resp.status_code != 200:
                xbmc.log(f"[RoxieStreams] _resolve_raw_page bad status {resp.status_code} for {raw_url}", xbmc.LOGWARNING)
                return None
            html = resp.text
            xbmc.log(f"[RoxieStreams] _resolve_raw_page fetched {raw_url} (len {len(html)})", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"[RoxieStreams] _resolve_raw_page fetch failed for {raw_url}: {e}", xbmc.LOGWARNING)
            return None

        # Shaka Player manifest load: player.load("https://.../cenc.mpd")
        load_match = re.search(r'player\.load\(\s*[\'"]([^\'"]+\.(?:mpd|m3u8)[^\'"]*)[\'"]', html)
        if not load_match:
            xbmc.log(f"[RoxieStreams] _resolve_raw_page: no player.load() manifest found in {raw_url}", xbmc.LOGWARNING)
            return None
        stream_url = load_match.group(1)
        xbmc.log(f"[RoxieStreams] _resolve_raw_page: found manifest {stream_url}", xbmc.LOGINFO)

        # ClearKey DRM: drm: { clearKeys: { "<kid>": "<key>" } }
        ck_match = re.search(r'clearKeys\s*:\s*\{([^}]*)\}', html, re.DOTALL)
        license_key = None
        license_type = None
        if ck_match:
            body = ck_match.group(1)
            kid_key = re.search(r'["\']([0-9a-fA-F]{32})["\']\s*:\s*["\']([0-9a-fA-F]{32})["\']', body)
            if kid_key:
                kid_hex = kid_key.group(1).lower()
                key_hex = kid_key.group(2).lower()
                # inputstream.adaptive accepts clearkey in "KID:KEY" hex format
                license_key = f"{kid_hex}:{key_hex}"
                license_type = "org.w3.clearkey"
                xbmc.log(f"[RoxieStreams] _resolve_raw_page: ClearKey DRM detected (kid={kid_hex}, key={key_hex})", xbmc.LOGINFO)

        headers = {
            "Origin": "https://roxiestreams.info",
            "Referer": "https://roxiestreams.info/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        }

        if stream_url.endswith(".mpd") or ".mpd?" in stream_url:
            inputstream = JetInputstreamAdaptive(
                "mpd",
                license_type=license_type,
                license_key=license_key,
                manifest_headers=headers,
                stream_headers=headers,
            )
            xbmc.log(f"[RoxieStreams] _resolve_raw_page: inputstream dict = {_json.dumps(inputstream.to_dict())}", xbmc.LOGINFO)
            link = JetLink(
                address=stream_url,
                name=button_text,
                resolveurl=False,
                inputstream=inputstream,
                headers=headers,
                direct=True,
            )
        else:
            # HLS without DRM - patch segments via local proxy
            patched_url, _ = self._patch_m3u8_segments(stream_url, headers)
            inputstream = JetInputstreamFFmpegDirect.default()
            link = JetLink(
                address=patched_url,
                name=button_text,
                resolveurl=False,
                inputstream=inputstream,
                headers=headers,
                direct=True,
            )
        xbmc.log(f"[RoxieStreams] _resolve_raw_page: returning link for {button_text or raw_url}", xbmc.LOGINFO)
        return link

    def _patch_m3u8_segments(self, stream_url: str, headers: dict):
        try:
            # Roxiestreams manifests can expire quickly; don't cache them.
            proxy = get_stream_proxy(
                "roxiestreams",
                headers,
                options={"cache_manifest": False, "proxy_absolute_urls": False},
            )
            proxy_url = proxy.get_proxy_url(stream_url, headers)
            xbmc.log(f"[RoxieStreams] Live manifest proxy: {proxy_url} (rebuilds from upstream on each fetch)", xbmc.LOGINFO)
            return proxy_url, None
        except Exception as e:
            xbmc.log(f"[RoxieStreams] Failed to register proxy: {e}", xbmc.LOGWARNING)
            return stream_url, None

    def _is_working_m3u8(self, stream_url: str) -> bool:
        try:
            resp = requests.get(
                stream_url,
                timeout=8,
                allow_redirects=True,
                stream=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Origin": "https://roxiestreams.info",
                    "Referer": "https://roxiestreams.info/"
                }
            )
            if resp.status_code not in (200, 206):
                return False
            content_type = resp.headers.get("Content-Type", "").lower()
            if "mpegurl" in content_type or "octet-stream" in content_type or "text" in content_type:
                return True
            try:
                head = next(resp.iter_content(chunk_size=2048), b"")
            except Exception:
                head = b""
            try:
                resp.close()
            except Exception:
                pass
            try:
                head_text = head.decode("utf-8", errors="ignore")
            except Exception:
                head_text = ""
            if "#EXTM3U" in head_text:
                return True
            if ".m3u8" in stream_url and head_text and not head_text.lstrip().startswith("<"):
                return True
            return False
        except Exception:
            return False

    def _fetch_preferred_domains(self) -> List[str]:
        preferred = []
        urls = [
            "https://magnetic.website/Jetextractor/preferred/domains.txt",
            "https://magnetic.website/Jetextractor/preferred/roxiestreams.txt",
            # "https://magnetic.website/Jetextractor/preferred/domains.txt"
        ]
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            }
            secret_token = "your-secret-token-here"
            if secret_token:
                headers["Authorization"] = f"Bearer {secret_token}"
            for url in urls:
                try:
                    resp = requests.get(url, timeout=self.timeout, headers=headers)
                    if resp.status_code == 200:
                        for line in resp.text.strip().splitlines():
                            line = line.strip().strip('"').strip("'").strip(",").strip()
                            if line:
                                preferred.append(line)
                        if preferred:
                            # xbmc.log(f"[RoxieStreams] Loaded {len(preferred)} preferred domains from {url}", xbmc.LOGINFO)
                            xbmc.log(f"[RoxieStreams] Loaded {len(preferred)} preferred domains from server", xbmc.LOGINFO)
                            return preferred
                except Exception as e:
                    xbmc.log(f"[RoxieStreams] Failed to fetch from {url}: {e}", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f"[RoxieStreams] Failed to fetch preferred domains: {e}", xbmc.LOGERROR)
        fallback = ["shadow-ran.online"]
        xbmc.log(f"[RoxieStreams] Using fallback preferred domains: {fallback}", xbmc.LOGINFO)
        return fallback

    def _pick_working_stream_url(self, subdomain: str, stream_path: str, domains_list: List[str], button_text: str) -> str:
        for domain in domains_list:
            test_url = f"https://{subdomain}.{domain}/{stream_path}"
            xbmc.log(f"[RoxieStreams] Button '{button_text}' using URL: {test_url}", xbmc.LOGINFO)
            return test_url
        fallback = f"https://{subdomain}.{domains_list[0]}/{stream_path}"
        xbmc.log(f"[RoxieStreams] Button '{button_text}' fallback URL: {fallback}", xbmc.LOGINFO)
        return fallback

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}).text
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
                r = requests.get(href, timeout=self.timeout, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}).text
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
            html = requests.get(url.address, headers={"Accept-Encoding": SKIP_HEADER, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}).text
            soup = BeautifulSoup(html, "html.parser")
            buttons = soup.select("button.streambutton")
            if buttons:
                xbmc.log(f"[RoxieStreams] Found {len(buttons)} stream buttons", xbmc.LOGINFO)
                subdomain = 'daffodil'# Default subdomain
                # Fetch domains from domains.txt
                domains_list = []
                for domains_file in ('domainsz30.txt', 'domainsz25.txt', 'domains.txt'):
                    try:
                        domains_url = f"https://{self.domains[0]}/{domains_file}"
                        xbmc.log(f"[RoxieStreams] Fetching domains from: {domains_url}", xbmc.LOGINFO)
                        domains_response = requests.get(domains_url, timeout=self.timeout, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"})
                        if domains_response.status_code == 200:
                            domains_list = [d.strip() for d in domains_response.text.strip().split('\n') if d.strip()]
                            xbmc.log(f"[RoxieStreams] Loaded {len(domains_list)} domains from {domains_file}: {domains_list}", xbmc.LOGINFO)
                            if domains_list:
                                break
                    except Exception as e:
                        xbmc.log(f"[RoxieStreams] Failed to fetch {domains_file}: {e}", xbmc.LOGERROR)
                
                if not domains_list:
                    domains_list = ['shadow-ran.online']
                    xbmc.log(f"[RoxieStreams] Using fallback domains: {domains_list}", xbmc.LOGINFO)
                
                # Extract current domain from page HTML (use existing html var)
                domain_from_page = re.search(r'https?://\$\{subdomain\}\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html)
                if domain_from_page:
                    extracted_domain = domain_from_page.group(1)
                    if extracted_domain not in domains_list:
                        domains_list.insert(0, extracted_domain)
                        xbmc.log(f"[RoxieStreams] Extracted domain from page: {extracted_domain}", xbmc.LOGINFO)
                
                # Add known fallback domains (append so discovered/current domains stay first)
                for d in ['shadow-ran.online']:
                    if d not in domains_list:
                        domains_list.append(d)
                
                preferred_domains = self._fetch_preferred_domains()
                for preferred in reversed(preferred_domains):
                    if preferred in domains_list:
                        domains_list.remove(preferred)
                    domains_list.insert(0, preferred)

                xbmc.log(f"[RoxieStreams] Final domains list: {domains_list}", xbmc.LOGINFO)
                
                # Keep domains in order - first is tried first
                xbmc.log(f"[RoxieStreams] Using domains: {domains_list}", xbmc.LOGINFO)
                scripts = soup.find_all("script")
                # Find default subdomain from scripts (may be overridden by individual buttons)
                default_subdomain = 'daffodil'
                js_functions = {}
                for script in scripts:
                    script_content = script.string or script.text or ""
                    if not script_content:
                        continue
                    subdomain_match = re.search(r"var\s+subdomain\s*=\s*['\"]([^'\"]+)['\"]", script_content)
                    if subdomain_match:
                        default_subdomain = subdomain_match.group(1)
                        xbmc.log(f"[RoxieStreams] Found default subdomain: {default_subdomain}", xbmc.LOGINFO)
                    # Find JavaScript functions like playStream1(), playStream5()
                    func_matches = re.findall(r"function\s+(playStream\d+)\s*\(\s*\)\s*\{([^}]+(?:\{[^}]*\})*[^}]*)\}", script_content)
                    for func_name, func_body in func_matches:
                        js_functions[func_name] = func_body
                        xbmc.log(f"[RoxieStreams] Found JS function: {func_name}", xbmc.LOGINFO)
                
                for idx, button in enumerate(buttons, 1):
                    onclick = button.get("onclick", "")
                    button_text = button.get_text(strip=True) or f"Stream {idx}"
                    xbmc.log(f"[RoxieStreams] Button '{button_text}' onclick: {onclick}", xbmc.LOGINFO)
                    
                    # Try new format first: showPlayer('clappr', 'https://601.833577.xyz/daffodil.m3u8')
                    direct_url_match = re.search(r"showPlayer\([^,]+,\s*['\"]([^'\"]+\.(?:m3u8|mpd)[^'\"]*)['\"]", onclick)
                    if direct_url_match:
                        stream_url = direct_url_match.group(1)
                        xbmc.log(f"[RoxieStreams] Button '{button_text}' (direct URL): {stream_url}", xbmc.LOGINFO)
                        
                        stream_url, headers, inputstream = self._process_stream_url(stream_url)
                        patched_url, _ = self._patch_m3u8_segments(stream_url, headers)
                        link = JetLink(address=patched_url, name=button_text, resolveurl=False, inputstream=inputstream, headers=headers, direct=True)
                        links.append(link)
                    elif onclick.startswith("playStream"):
                        # Handle JS functions - find actual URL from page scripts
                        func_match = re.match(r"playStream(\d+)\(\)", onclick)
                        if func_match:
                            func_num = func_match.group(1)
                            func_name = f"playStream{func_num}"
                            xbmc.log(f"[RoxieStreams] Button '{button_text}' looking for {func_name} URL", xbmc.LOGINFO)
                            # Search for URL in the specific function body
                            js_url = None
                            if func_name in js_functions:
                                func_body = js_functions[func_name]
                                # Check for getRandomStream call
                                random_match = re.search(r"getRandomStream\(['\"]([^'\"]+\.m3u8)['\"](?:,\s*['\"]([^'\"]+)['\"])?\)", func_body)
                                if random_match:
                                    stream_path = random_match.group(1)
                                    button_subdomain = random_match.group(2) if random_match.group(2) else default_subdomain
                                    chosen_url = self._pick_working_stream_url(button_subdomain, stream_path, domains_list, button_text)
                                    js_url = chosen_url
                                    xbmc.log(f"[RoxieStreams] Button '{button_text}' using getRandomStream: {js_url}", xbmc.LOGINFO)
                                else:
                                    # Check for showPlayer with variable (e.g., dashStream)
                                    var_match = re.search(r"showPlayer\([^,]+,\s*(\w+)", func_body)
                                    if var_match:
                                        var_name = var_match.group(1)
                                        # Search all scripts for variable definition
                                        for script in scripts:
                                            script_content = script.string or script.text or ""
                                            var_def = re.search(rf"(?:var|let|const)\s+{re.escape(var_name)}\s*=\s*['\"]([^'\"]+)['\"]", script_content)
                                            if var_def:
                                                js_url = var_def.group(1)
                                                xbmc.log(f"[RoxieStreams] Button '{button_text}' found variable {var_name}: {js_url}", xbmc.LOGINFO)
                                                break
                                    else:
                                        # Try direct URL patterns as fallback
                                        matches = re.findall(r'["\']([^"\']+\.m3u8[^"\']*?)["\']', func_body)
                                        matches += re.findall(r'["\']([^"\']+\.mpd[^"\']*?)["\']', func_body)
                                        matches += re.findall(r'(https?://[^\s"\'<>]+\.(?:m3u8|mpd)[^\s"\'<>]*)', func_body)
                                        for m in matches:
                                            if m.startswith("http"):
                                                js_url = m
                                                xbmc.log(f"[RoxieStreams] Button '{button_text}' found URL in {func_name}: {js_url}", xbmc.LOGINFO)
                                                break
                            else:
                                xbmc.log(f"[RoxieStreams] Button '{button_text}' function {func_name} not found in js_functions", xbmc.LOGWARNING)
                            if js_url:
                                js_url, headers, inputstream = self._process_stream_url(js_url)
                                patched_url, _ = self._patch_m3u8_segments(js_url, headers)
                                links.append(JetLink(address=patched_url, name=button_text, resolveurl=False, inputstream=inputstream, headers=headers, direct=True))
                            else:
                                xbmc.log(f"[RoxieStreams] Button '{button_text}' using fallback subdomain: {default_subdomain}", xbmc.LOGINFO)
                                stream_path = "main.m3u8" if func_num != "5" else "golazo.m3u8"
                                chosen_url = self._pick_working_stream_url(default_subdomain, stream_path, domains_list, button_text)
                                chosen_url, headers, inputstream = self._process_stream_url(chosen_url)
                                patched_url, _ = self._patch_m3u8_segments(chosen_url, headers)
                                links.append(JetLink(address=patched_url, name=button_text, resolveurl=False, inputstream=inputstream, headers=headers, direct=True))
                    elif "playIframePlayer" in onclick:
                        # Iframe-based player: playIframePlayer('https://roxiestreams.info/raw/fox')
                        iframe_match = re.search(r"playIframePlayer\(['\"]([^'\"]+)['\"]", onclick)
                        if iframe_match:
                            raw_url = iframe_match.group(1)
                            xbmc.log(f"[RoxieStreams] Button '{button_text}' (iframe/raw): {raw_url}", xbmc.LOGINFO)
                            try:
                                raw_link = self._resolve_raw_page(raw_url, button_text)
                                if raw_link is not None and raw_link.address:
                                    links.append(raw_link)
                                else:
                                    xbmc.log(f"[RoxieStreams] Button '{button_text}' raw page yielded no link", xbmc.LOGWARNING)
                            except Exception as e:
                                xbmc.log(f"[RoxieStreams] Button '{button_text}' iframe resolve failed: {e}", xbmc.LOGWARNING)
                    else:
                        # Try old format: getRandomStream('usa.m3u8', 'daffodil')
                        stream_match = re.search(r"getRandomStream\(['\"]([^'\"]+\.m3u8)['\"](?:,\s*['\"]([^'\"]+)['\"])?\)", onclick)
                        if stream_match:
                            stream_path = stream_match.group(1)
                            # Get subdomain from onclick if present, otherwise use default
                            button_subdomain = stream_match.group(2) if stream_match.group(2) else default_subdomain
                            xbmc.log(f"[RoxieStreams] Button '{button_text}' subdomain: {button_subdomain}", xbmc.LOGINFO)
                            
                            chosen_url = self._pick_working_stream_url(button_subdomain, stream_path, domains_list, button_text)
                            chosen_url, headers, inputstream = self._process_stream_url(chosen_url)
                            patched_url, _ = self._patch_m3u8_segments(chosen_url, headers)
                            links.append(JetLink(address=patched_url, name=button_text, resolveurl=False, inputstream=inputstream, headers=headers, direct=True))
        except Exception as e:
            xbmc.log(f"[RoxieStreams] Exception in get_links: {e}", xbmc.LOGERROR)
        
        if links:
            # Filter out unplayable DRM/MPD streams. Keep ClearKey-protected MPD
            # streams since Kodi's inputstream.adaptive supports ClearKey.
            # DAZN streams use Widevine and are skipped.
            filtered = []
            for link in links:
                is_mpd = ".mpd" in link.address
                is_dazn = "dazn" in link.address.lower() and "indazn" in link.address
                if is_mpd or is_dazn:
                    lic_type = getattr(getattr(link, "inputstream", None), "license_type", None)
                    lic_key = getattr(getattr(link, "inputstream", None), "license_key", None)
                    if lic_type == "org.w3.clearkey" and lic_key:
                        filtered.append(link)
                        xbmc.log(f"[RoxieStreams] Keeping ClearKey MPD stream: {link.name} (license_key={lic_key})", xbmc.LOGINFO)
                    else:
                        xbmc.log(f"[RoxieStreams] Skipping DRM stream: {link.name} -> {link.address[:80]}... (license_type={lic_type})", xbmc.LOGINFO)
                    continue
                filtered.append(link)
            
            links = filtered
            
            if not links:
                xbmc.log(f"[RoxieStreams] All links were DRM, returning empty", xbmc.LOGWARNING)
                return []
            
            # Return all available streams, keeping their original button names
            # so the user can pick which one to play. Non-cloudflare first, then
            # cloudflare/customer streams, but nothing is dropped.
            normal = [l for l in links if "cloudflarestream" not in l.address and "customer-" not in l.address]
            cloudflare = [l for l in links if "cloudflarestream" in l.address or "customer-" in l.address]
            ordered = normal + cloudflare
            
            xbmc.log(f"[RoxieStreams] Returning {len(ordered)} links (all streams available)", xbmc.LOGINFO)
            return ordered
        # Fallback to single link extraction
        xbmc.log(f"[RoxieStreams] No stream buttons found, falling back to get_link", xbmc.LOGINFO)
        return [self.get_link(url)]
    
    def get_link(self, url: JetLink) -> JetLink:
        xbmc.log(f"[RoxieStreams] get_link called for: {url.address}", xbmc.LOGINFO)
        # 0. /raw/<channel> pages embed a Shaka Player (DASH .mpd, often ClearKey
        # DRM). Resolve these directly via _resolve_raw_page instead of falling
        # through to the unplayable raw HTML.
        if "/raw/" in url.address:
            raw_link = self._resolve_raw_page(url.address, url.name)
            if raw_link is not None and raw_link.address:
                return raw_link
            xbmc.log(f"[RoxieStreams] _resolve_raw_page failed for {url.address}, continuing with generic flow", xbmc.LOGWARNING)
        # 1. Try to extract stream buttons and m3u8 URLs
        try:
            html = requests.get(url.address, headers={"Accept-Encoding": SKIP_HEADER, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}).text
            xbmc.log(f"[RoxieStreams] HTML fetched for {url.address} (length: {len(html)})", xbmc.LOGINFO)
            soup = BeautifulSoup(html, "html.parser")
            buttons = soup.select("button.streambutton")
            if buttons:
                xbmc.log(f"[RoxieStreams] Found {len(buttons)} stream buttons", xbmc.LOGINFO)
                subdomain = 'daffodil'
                domains_list = []
                for domains_file in ('domainsz30.txt', 'domainsz25.txt', 'domains.txt'):
                    try:
                        domains_url = f"https://{self.domains[0]}/{domains_file}"
                        domains_response = requests.get(domains_url, timeout=self.timeout, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"})
                        if domains_response.status_code == 200:
                            domains_list = [d.strip() for d in domains_response.text.strip().split('\n') if d.strip()]
                            if domains_list:
                                break
                    except:
                        pass
                if not domains_list:
                    domains_list = ['shadow-ran.online']
                
                # Extract current domain from page HTML
                domain_from_page = re.search(r'https?://\$\{subdomain\}\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html)
                if domain_from_page:
                    extracted_domain = domain_from_page.group(1)
                    if extracted_domain not in domains_list:
                        domains_list.insert(0, extracted_domain)
                        xbmc.log(f"[RoxieStreams] Extracted domain from page: {extracted_domain}", xbmc.LOGINFO)
                
                # Add known fallback domains (append so discovered/current domains stay first)
                for d in ['shadow-ran.online']:
                    if d not in domains_list:
                        domains_list.append(d)
                
                preferred_domains = self._fetch_preferred_domains()
                for preferred in reversed(preferred_domains):
                    if preferred in domains_list:
                        domains_list.remove(preferred)
                    domains_list.insert(0, preferred)

                xbmc.log(f"[RoxieStreams] Final domains list: {domains_list}", xbmc.LOGINFO)
                
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
                direct_url_match = re.search(r"showPlayer\([^,]+,\s*['\"]([^'\"]+\.(?:m3u8|mpd)[^'\"]*)['\"]", onclick)
                if direct_url_match:
                    stream_url = direct_url_match.group(1)
                    xbmc.log(f"[RoxieStreams] Found direct m3u8 URL: {stream_url}", xbmc.LOGINFO)
                    
                    stream_url, headers, inputstream = self._process_stream_url(stream_url)
                    patched_url, _ = self._patch_m3u8_segments(stream_url, headers)
                    return JetLink(address=patched_url, inputstream=inputstream, resolveurl=False, headers=headers, direct=True)
                stream_match = re.search(r"getRandomStream\(['\"]([^'\"]+\.m3u8)['\"](?:,\s*['\"]([^'\"]+)['\"])?\)", onclick)
                if stream_match:
                    stream_path = stream_match.group(1)
                    button_subdomain = stream_match.group(2) if stream_match.group(2) else subdomain
                    # Try all domains in order
                    for domain in domains_list:
                        stream_url = f"https://{button_subdomain}.{domain}/{stream_path}"
                        xbmc.log(f"[RoxieStreams] Trying: {stream_url}", xbmc.LOGINFO)
                        stream_url, headers, inputstream = self._process_stream_url(stream_url)
                        patched_url, _ = self._patch_m3u8_segments(stream_url, headers)
                        return JetLink(address=patched_url, inputstream=inputstream, resolveurl=False, headers=headers, direct=True)
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
                clappr_match = re.search(r"source\s*:\s*['\"](https?://[^'\"]+\.(?:m3u8|mpd)[^'\"]*)['\"]", script_lower)
                if clappr_match:
                    stream_url = clappr_match.group(1)
                    xbmc.log(f"[RoxieStreams] Found Clappr m3u8: {stream_url}", xbmc.LOGINFO)
                    stream_url, headers, inputstream = self._process_stream_url(stream_url)
                    return JetLink(address=stream_url, inputstream=inputstream, resolveurl=False, headers=headers, direct=True)
                # Existing generic
                found = re.findall(r'(https?://[^\'\"]+\.(?:m3u8|mpd)[^\'\"]*)', script_lower)
                if found:
                    stream_url = found[0]
                    xbmc.log(f"[RoxieStreams] Found m3u8 in script: {stream_url}", xbmc.LOGINFO)
                    stream_url, headers, inputstream = self._process_stream_url(stream_url)
                    return JetLink(address=stream_url, inputstream=inputstream, resolveurl=False, headers=headers, direct=True)
                #patterns for Video.js, JW Player, or obfuscated
                videojs_match = re.search(r"(?:src|file|playlist)\s*[:=]\s*['\"](https?://[^'\"]+\.(?:m3u8|mpd)[^'\"]*)['\"]", script_lower)
                if videojs_match:
                    stream_url = videojs_match.group(1)
                    xbmc.log(f"[RoxieStreams] Found Video.js/JW m3u8: {stream_url}", xbmc.LOGINFO)
                    stream_url, headers, inputstream = self._process_stream_url(stream_url)
                    return JetLink(address=stream_url, inputstream=inputstream, resolveurl=False, headers=headers, direct=True)
                # Base64-decoded URLs
                b64_matches = re.findall(r'([A-Za-z0-9+/]{20,}=*)(?:\.m3u8|\.mpd|\.js)', script_lower)
                for b64_str in b64_matches:
                    try:
                        decoded = base64.b64decode(b64_str).decode('utf-8')
                        if 'm3u8' in decoded or 'mpd' in decoded:
                            m3u8_url = re.search(r'(https?://[^\'\" ]+\.(?:m3u8|mpd))', decoded)
                            if m3u8_url:
                                stream_url = m3u8_url.group(1)
                                xbmc.log(f"[RoxieStreams] Decoded b64 m3u8: {stream_url}", xbmc.LOGINFO)
                                stream_url, headers, inputstream = self._process_stream_url(stream_url)
                                return JetLink(address=stream_url, inputstream=inputstream, resolveurl=False, headers=headers, direct=True)
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
                        m3u8_text = requests.get(iframe_link.address, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}).text
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
                                        resp = requests.head(full_seg, timeout=5, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"})
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
