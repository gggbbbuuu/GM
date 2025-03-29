import requests, re, json, time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..models import *
from .plytv import PlyTv
from concurrent.futures import ThreadPoolExecutor
import xbmc
import base64

class Strikeout(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["strikeout.im"]
        self.name = "Strikeout"
        self.timeout = 10
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    def _log(self, msg: str, level: int = xbmc.LOGINFO) -> None:
        xbmc.log(f"[Strikeout] {msg}", level)

    def __get_items(self, sport_href: Tuple[str, str], slugs: List[str], progress: Optional[JetExtractorProgress] = None):
        items = []
        if self.progress_update(progress):
            return items

        sport = sport_href[1]
        sport_href = sport_href[0]
        r_sport = requests.get(f"https://{self.domains[0]}{sport_href}", timeout=self.timeout).text
        soup_sport = BeautifulSoup(r_sport, "html.parser")
        site_config = json.loads(re.findall(r"const siteConfig = (.+?);", r_sport)[0])
        if "scheduleData" not in site_config:
            return items
        schedule_data = requests.get(f"https://{self.domains[0]}/schedule/{site_config['scheduleData']}/", timeout=self.timeout).json()
        for game in soup_sport.select("a.btn-primary"):
            try:
                game_id = game.get("aria-controls")
                game_slug = schedule_data["slugs"][game_id]
                if game_slug in slugs:
                    continue

                slugs.append(game_slug)
                game_title = game.get("title")
                game_links = [JetLink(address=f"https://{self.domains[0]}/{sport_href[1:]}/{i+1}/{game_slug}-stream", name=f"{link['player']} - Link {i+1}") for i, link in enumerate(schedule_data["links"][game_id])]
                game_spans = game.find_all("span")
                if len(game_spans) > 1:
                    game_time = datetime(*(time.strptime(game_spans[-1].get("content"), "%Y-%m-%dT%H:%M")[:6])) - timedelta(hours=1)
                else:
                    game_time = None
                items.append(JetItem(title=game_title, links=game_links, league=sport, starttime=game_time))
            except:
                continue
        return items
    

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        hrefs = []
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for sport_page in soup.select("div.col-xxl-2"):
            sport = sport_page.text
            sport_href = sport_page.select_one("a").get("href")
            if not sport_href.startswith("/"):
                continue
            hrefs.append((sport_href, sport))
        
        slugs = []
        with ThreadPoolExecutor() as executor:
            threads = [(href, executor.submit(self.__get_items, sport_href=href, slugs=slugs, progress=progress)) for href in hrefs]
            for href, t in threads:
                result = t.result()
                items.extend(result)
                self.progress_update(progress, href[1])
            
        return items
    
    def get_link(self, url: JetLink) -> Optional[JetLink]:
        try:
            if not isinstance(url, JetLink):
                self._log("Input is not a JetLink object", xbmc.LOGWARNING)
                if isinstance(url, str):
                    url = JetLink(address=url)
                else:
                    return None

            if not url or not url.address:
                self._log("Invalid URL or empty address", xbmc.LOGWARNING)
                return None

            self._log(f"Processing URL: {url.address}")
            
            # Try to get the page content
            try:
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "DNT": "1"
                }
                
                r = requests.get(url.address, headers=headers, timeout=self.timeout)
                r.raise_for_status()
                content = r.text
                self._log("Successfully fetched page content")

                # Try to find iframe with stream source
                soup = BeautifulSoup(content, 'html.parser')
                iframes = soup.find_all('iframe')
                
                for iframe in iframes:
                    if not iframe.get('src'):
                        continue
                        
                    iframe_url = iframe['src']
                    if iframe_url.startswith('//'):
                        iframe_url = 'https:' + iframe_url
                    elif not iframe_url.startswith('http'):
                        iframe_url = 'https://' + iframe_url

                    self._log(f"Found iframe URL: {iframe_url}")
                    
                    # Try PlyTv extractor for known domains
                    if any(domain in iframe_url.lower() for domain in ['reliabletv.me', 'plytv.me', 'kenitv.me', 'embedstream.me']):
                        self._log(f"Trying PlyTv extractor for: {iframe_url}")
                        result = PlyTv().get_link(JetLink(
                            address=iframe_url,
                            headers={
                                "Origin": f"https://{self.domains[0]}",
                                "Referer": url.address,
                                "User-Agent": self.user_agent
                            }
                        ))
                        if result and result.address:
                            self._log(f"Successfully extracted stream URL via PlyTv")
                            return result
                    
                    # Try direct stream URL extraction
                    try:
                        iframe_content = requests.get(
                            iframe_url,
                            headers={
                                "User-Agent": self.user_agent,
                                "Referer": url.address,
                                "Origin": f"https://{self.domains[0]}"
                            },
                            timeout=self.timeout
                        ).text
                        
                        # Look for various stream URL patterns
                        stream_patterns = [
                            r'source:\s*["\'](.+?)["\']',
                            r'file:\s*["\'](.+?)["\']',
                            r'src:\s*["\'](.+?)["\']',
                            r'var\s+url\s*=\s*["\'](.+?)["\']',
                            r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)'
                        ]
                        
                        for pattern in stream_patterns:
                            matches = re.findall(pattern, iframe_content, re.IGNORECASE)
                            if matches:
                                stream_url = matches[0]
                                if isinstance(stream_url, tuple):
                                    stream_url = stream_url[0]
                                
                                if stream_url.startswith('//'):
                                    stream_url = 'https:' + stream_url
                                elif not stream_url.startswith('http'):
                                    stream_url = 'https://' + stream_url
                                
                                self._log(f"Found stream URL: {stream_url}")
                                
                                return JetLink(
                                    address=stream_url,
                                    headers={
                                        "Referer": iframe_url,
                                        "User-Agent": self.user_agent,
                                        "Origin": f"https://{self.domains[0]}",
                                        "Connection": "keep-alive",
                                        "Accept": "*/*",
                                        "Accept-Language": "en-US,en;q=0.5"
                                    },
                                    inputstream=JetInputstreamAdaptive(
                                        manifest_type="hls",
                                        stream_headers={
                                            "Referer": iframe_url,
                                            "User-Agent": self.user_agent,
                                            "Origin": f"https://{self.domains[0]}"
                                        }
                                    ) if stream_url.endswith('.m3u8') else None
                                )
                                
                    except Exception as e:
                        self._log(f"Error processing iframe {iframe_url}: {str(e)}", xbmc.LOGWARNING)
                        continue

                self._log("No stream URL found", xbmc.LOGWARNING)
                return None

            except Exception as e:
                self._log(f"Failed to get page content: {str(e)}", xbmc.LOGERROR)
                return None

        except Exception as e:
            self._log(f"Error in get_link: {str(e)}", xbmc.LOGERROR)
            return None