import requests, re
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes, m3u8_src
from ..icons import icons
import time  # New: For expires generation if needed

class StreamBTW(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streambtw.com","streambtw.live"]
        self.name = "StreamBTW"
        self.short_name = "CS"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        try:
            r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout, headers={"User-Agent": self.user_agent}).text
        except requests.exceptions.RequestException:
            try:
                r = requests.get(f"https://{self.domains[1]}", timeout=self.timeout, headers={"User-Agent": self.user_agent}).text
            except requests.exceptions.RequestException:
                return items
        soup = BeautifulSoup(r, "html.parser")
        
        for extra in soup.select("div.card"):
            game_titles = [title.text.strip() for title in extra.select("p")]
            hrefs = [link.get("href") for link in extra.select("a")]
            sport = [title.text.strip() for title in extra.select("h5")]
            thumb = [icon.get("src") for icon in extra.select("img")]
            for title,sport, href,thumb in zip(game_titles,sport, hrefs,thumb):
                # Make href absolute if it's relative
                if href and not href.startswith("http"):
                    href = f"https://{self.domains[0]}{href}" if href.startswith("/") else f"https://{self.domains[0]}/{href}"
                items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None, league=sport.upper(), title=title, links=[JetLink(href)]))
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
        stream_headers = base_headers.copy()
        stream_headers.update({
            "Referer": "https://streambtw.com/",
            "Origin": "https://streambtw.com/"
        })

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
                        candidate = f"https://streambtw.com/playlist/stream_nba2.m3u8?md5={md5_match.group(1)}&expires={expires_match.group(1)}"
                    else:
                        candidate = match if match.startswith('http') else f"https://{base_url.split('/')[2]}{match}" if match.startswith('/') else base_url.rsplit('/', 1)[0] + '/' + match
                    if try_stream_url(candidate, stream_headers):
                        return candidate
            return None

        primary_domain = self.domains[0]
        alternate_domain = self.domains[1]
        original_url = url.address
        stream_id = original_url.split('/')[-1].replace('.php', '')  # 'nba2'

        session = requests.Session()
        session.headers.update(base_headers)
        try:
            main_url = f"https://{primary_domain}/"
            session.get(main_url, timeout=self.timeout)  # Set cookies
            headers = base_headers.copy()
            headers["Referer"] = main_url
            r = session.get(original_url, timeout=self.timeout, headers=headers)
            
            # Regex extract
            regex_stream = extract_via_regex(r.text, original_url)
            if regex_stream:
                return JetLink(regex_stream, headers=stream_headers)
            
            # Standard m3u8 scan
            m3u8_link = m3u8_src.scan_page(original_url, html=r.text)
            if m3u8_link:
                return m3u8_link
            
            # BS iframe + resolve (use prior helper if defined)
            soup = BeautifulSoup(r.text, "html.parser")
            iframe = soup.select_one("iframe")
            if iframe and iframe.get("src"):
                iframe_src = iframe.get("src")
                if not iframe_src.startswith("http"):
                    iframe_src = "https:" + iframe_src if iframe_src.startswith("//") else f"https://{primary_domain}{iframe_src}"
                # Fallback to find_iframes with headers
                resolved = find_iframes.find_iframes(iframe_src, original_url, [], [], stream_headers)
                if resolved:
                    first = resolved[0]
                    return JetLink(first, headers=stream_headers) if isinstance(first, str) else first
                return JetLink(iframe_src, headers=stream_headers)
            
            
            guessed_streambtw = f"https://streambtw.com/playlist/stream_{stream_id}.m3u8"
            if try_stream_url(guessed_streambtw, stream_headers):
                return JetLink(guessed_streambtw, headers=stream_headers)
                
        except Exception:
            pass

        # Alternate domain 
        session = requests.Session()
        session.headers.update(base_headers)
        try:
            main_url = f"https://{alternate_domain}/"
            session.get(main_url, timeout=self.timeout)
            alt_url = original_url.replace(primary_domain, alternate_domain)
            headers = base_headers.copy()
            headers["Referer"] = main_url
            r = session.get(alt_url, timeout=self.timeout, headers=headers)
            
            regex_stream = extract_via_regex(r.text, alt_url)
            if regex_stream:
                return JetLink(regex_stream, headers=stream_headers)
            
            m3u8_link = m3u8_src.scan_page(alt_url, html=r.text)
            if m3u8_link:
                return m3u8_link
            
            soup = BeautifulSoup(r.text, "html.parser")
            iframe = soup.select_one("iframe")
            if iframe and iframe.get("src"):
                iframe_src = iframe.get("src")
                if not iframe_src.startswith("http"):
                    iframe_src = "https:" + iframe_src if iframe_src.startswith("//") else f"https://{alternate_domain}{iframe_src}"
                resolved = find_iframes.find_iframes(iframe_src, alt_url, [], [], stream_headers)
                if resolved:
                    first = resolved[0]
                    return JetLink(first, headers=stream_headers) if isinstance(first, str) else first
                return JetLink(iframe_src, headers=stream_headers)
            
            
            guessed_streambtw = f"https://{alternate_domain}/playlist/stream_{stream_id}.m3u8"
            if try_stream_url(guessed_streambtw, stream_headers):
                return JetLink(guessed_streambtw, headers=stream_headers)
                
        except Exception:
            pass

        
        try:
            resolved = find_iframes.find_iframes(original_url, "", [], [], stream_headers)
            if resolved:
                first = resolved[0]
                return JetLink(first, headers=stream_headers) if isinstance(first, str) else first
        except Exception:
            pass

        return url