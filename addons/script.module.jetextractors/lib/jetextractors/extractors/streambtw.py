import requests, re
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes, m3u8_src
from ..icons import icons
import time  
import base64

class StreamBTW(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streambtw.com","hiteasport.info","streameast.asia","streambtw.live"]
        self.name = "StreamBTW"
        self.short_name = "CS"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        try:
            r = requests.get(f"https://{self.domains[0]}/public/api.php?action=get", timeout=self.timeout, headers={"User-Agent": self.user_agent}).json()
        except requests.exceptions.RequestException:
            try:
                r = requests.get(f"https://{self.domains[1]}/public/api.php?action=get", timeout=self.timeout, headers={"User-Agent": self.user_agent}).json()
            except requests.exceptions.RequestException:
                return items
        
        groups = r.get("groups", [])
        for group in groups:
            league = group.get("title", "")
            for item in group.get("items", []):
                title = item.get("title", "")
                url = item.get("url", "")
                
                if title and url:
                    items.append(JetItem(
                        icon=icons[league.lower()] if league.lower() in icons else None,
                        league=league.upper(),
                        title=title,
                        links=[JetLink(url)]
                    ))
        return items

    def get_link(self, url: JetLink) -> JetLink:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        base_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        def try_stream_url(stream_candidate: str, headers: dict) -> bool:
            """Quick HEAD check if a URL is a valid stream."""
            try:
                resp = requests.head(stream_candidate, timeout=5, headers=headers)
                ct = resp.headers.get('content-type', '').lower()
                return resp.status_code == 200 and ('m3u8' in ct or 'video' in ct or 'application' in ct)
            except:
                return False

        def extract_via_regex(html: str, base_url: str) -> str:
            patterns = [
                r'(?:https?://[^\'\"\s]+/playlist/stream_nba2\.m3u8[^\'\"\s]*)',
                r'stream_nba2[^\'\"\s]+m3u8',
                r'md5=([^&\'\"]+)',
                r'expires=([^&\'\"]+)',
                r'streameast[^\'\"\s]+playlist/stream_nba2\.m3u8',
                r'playlist/stream[^\'\"\s]+nba2[^\'\"\s]+m3u8',
            ]
            md5_match = re.search(r'md5=([^&\'\"]+)', html)
            expires_match = re.search(r'expires=([^&\'\"]+)', html)
            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if 'md5=' in match and md5_match and expires_match:
                        candidate = f"https://streameast.asia/playlist/stream_nba2.m3u8?md5={md5_match.group(1)}&expires={expires_match.group(1)}"
                    else:
                        candidate = match if match.startswith('http') else f"https://{base_url.split('/')[2]}{match}" if match.startswith('/') else base_url.rsplit('/', 1)[0] + '/' + match
                    if try_stream_url(candidate, stream_headers):
                        return candidate
            return None

        def extract_obfuscated_base64(html: str) -> str:
            """Extract and decode the base64 obfuscated stream URL."""
            match = re.search(r'var encoded\s*=\s*"([^"]+)";', html, re.IGNORECASE | re.DOTALL)
            if match:
                encoded_str = match.group(1)
                try:
                    stream_url = base64.b64decode(encoded_str).decode('utf-8')
                    return stream_url
                except Exception:
                    pass
            return None

        def extract_channel_key(html: str) -> str:
            """Extract channelKey from EPlayerAuth.init config."""
            match = re.search(r"channelKey:\s*'([^']+)'", html)
            if match:
                return match.group(1)
            return None

        def get_stream_from_channel_key(channel_key: str, headers: dict) -> Optional[str]:
            """Get stream URL from channel key via server_lookup API."""
            try:
                resp = requests.get(
                    f"https://chevy.soyspace.cyou/server_lookup?channel_id={channel_key}",
                    timeout=10,
                    headers=headers
                )
                data = resp.json()
                server_key = data.get("server_key", "")
                if not server_key:
                    return None
                
                if server_key == "top1/cdn":
                    m3u8_url = f"https://top1.soyspace.cyou/top1/cdn/{channel_key}/mono.css"
                else:
                    m3u8_url = f"https://{server_key}new.soyspace.cyou/{server_key}/{channel_key}/mono.css"
                
                if try_stream_url(m3u8_url, headers):
                    return m3u8_url
            except Exception:
                pass
            return None

        primary_domain = self.domains[0]
        alternate_domain = self.domains[1]
        original_url = url.address
        stream_id = original_url.split('/')[-1].replace('.php', '')  # 'nba2'

        session = requests.Session()
        session.headers.update(base_headers)
        stream_headers = base_headers.copy()
        stream_headers.update({
            "Referer": f"https://{primary_domain}/",
            "Origin": f"https://{primary_domain}/"
        })
        try:
            main_url = f"https://{primary_domain}/"
            session.get(main_url, timeout=self.timeout)
            headers = base_headers.copy()
            headers["Referer"] = main_url
            r = session.get(original_url, timeout=self.timeout, headers=headers)
            
            channel_key = extract_channel_key(r.text)
            if channel_key:
                stream_url = get_stream_from_channel_key(channel_key, stream_headers)
                if stream_url:
                    return JetLink(stream_url, headers=stream_headers)
            
            base64_stream = extract_obfuscated_base64(r.text)
            if base64_stream and try_stream_url(base64_stream, stream_headers):
                return JetLink(base64_stream, headers=stream_headers)
        
            regex_stream = extract_via_regex(r.text, original_url)
            if regex_stream:
                return JetLink(regex_stream, headers=stream_headers)
            
            m3u8_link = m3u8_src.scan_page(original_url, html=r.text)
            if m3u8_link:
                return m3u8_link
            
            guessed_stream = f"https://{primary_domain}/playlist/stream_{stream_id}.m3u8"
            if try_stream_url(guessed_stream, stream_headers):
                return JetLink(guessed_stream, headers=stream_headers, inputstream=JetInputstreamFFmpegDirect.default())
                
        except Exception:
            pass

        session = requests.Session()
        session.headers.update(base_headers)
        alt_stream_headers = base_headers.copy()
        alt_stream_headers.update({
            "Referer": f"https://{alternate_domain}/",
            "Origin": f"https://{alternate_domain}/"
        })
        try:
            main_url = f"https://{alternate_domain}/"
            session.get(main_url, timeout=self.timeout)
            alt_url = original_url.replace(primary_domain, alternate_domain)
            headers = base_headers.copy()
            headers["Referer"] = main_url
            r = session.get(alt_url, timeout=self.timeout, headers=headers)
            # Obfuscated base64 extract
            base64_stream = extract_obfuscated_base64(r.text)
            if base64_stream and try_stream_url(base64_stream, alt_stream_headers):
                return JetLink(base64_stream, headers=alt_stream_headers)
            # Regex extract
            regex_stream = extract_via_regex(r.text, alt_url)
            if regex_stream:
                return JetLink(regex_stream, headers=alt_stream_headers)
            # Standard m3u8 scan
            m3u8_link = m3u8_src.scan_page(alt_url, html=r.text)
            if m3u8_link:
                return m3u8_link
            # Guessed stream
            guessed_stream = f"https://{alternate_domain}/playlist/stream_{stream_id}.m3u8"
            if try_stream_url(guessed_stream, alt_stream_headers):
                return JetLink(guessed_stream, headers=alt_stream_headers, inputstream=JetInputstreamFFmpegDirect.default())
                
        except Exception:
            pass

        
        try:
            resolved = find_iframes.find_iframes(original_url, "", [], [], stream_headers)
            if resolved:
                first = resolved[0]
                return JetLink(first, headers=stream_headers, inputstream=JetInputstreamFFmpegDirect.default()) if isinstance(first, str) else first
        except Exception:
            pass

        return url