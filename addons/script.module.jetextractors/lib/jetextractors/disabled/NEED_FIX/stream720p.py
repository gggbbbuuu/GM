import requests, re, base64, xbmc
from bs4 import BeautifulSoup
from datetime import datetime
from ..models import *
from datetime import timedelta

class Stream720p(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["720pstream.nu", "embedsports.me"]
        self.name = "Stream720p"
        self.timeout = 10
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
#######  NEED FIXING  ########
    def _log(self, msg: str, level: int = xbmc.LOGINFO) -> None:
        xbmc.log(f"[Stream720p] {msg}", level)

    def _get_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def _get_stream_url(self, html_content: str) -> Optional[str]:
        try:
            if not html_content:
                self._log("No HTML content provided")
                return None
                
            # First check for any eval or encoded content
            encoded_pattern = r'eval\(function\(.*?\)\s*{.*?}\((.*?)\)\)'
            encoded_match = re.search(encoded_pattern, html_content, re.DOTALL)
            if encoded_match:
                self._log("Found encoded content, attempting to decode")
                # TODO: Add decoder if needed
                
            patterns = [
                r'source:\s*["\'](.+?\.m3u8.*?)["\']',
                r'file:\s*["\'](.+?\.m3u8.*?)["\']',
                r'src=[\'"](.*?\.m3u8.*?)[\'"]',
                r'source:\s*["\'](.+?\.php.*?)["\']',  # PHP stream endpoints
                r'iframe.+?src=[\'"](.*?)[\'"]'  # Iframe source as fallback
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content)
                if matches and matches[0]:
                    stream_url = matches[0].strip()
                    
                    # Basic URL validation
                    if not stream_url.startswith('http'):
                        if stream_url.startswith('//'):
                            stream_url = 'https:' + stream_url
                        elif not stream_url.startswith('/'):
                            stream_url = '/' + stream_url
                            
                    # Validate stream URL format
                    if '.m3u8' in stream_url or '.php' in stream_url:
                        self._log(f"Found stream URL using pattern: {pattern}")
                        return stream_url
                    elif 'iframe' in pattern:
                        # Handle iframe source differently
                        return self._resolve_iframe(stream_url)
                        
            return None
            
        except Exception as e:
            self._log(f"Error in _get_stream_url: {str(e)}", xbmc.LOGERROR)
            return None
            
    def _resolve_iframe(self, iframe_url: str) -> Optional[str]:
        try:
            if not iframe_url.startswith('http'):
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                else:
                    base_url = 'https://720pstream.nu'
                    iframe_url = base_url + iframe_url
                    
            self._log(f"Resolving iframe: {iframe_url}")
            
            r = requests.get(
                iframe_url,
                headers=self._get_headers(iframe_url),
                timeout=self.timeout
            )
            
            if not r.ok:
                self._log(f"Failed to get iframe content: {r.status_code}")
                return None
                
            # Look for direct stream URL in iframe
            stream_url = self._get_stream_url(r.text)
            if stream_url:
                return stream_url
                
            return None
            
        except Exception as e:
            self._log(f"Error in _resolve_iframe: {str(e)}", xbmc.LOGERROR)
            return None

    def _resolve_embedsports(self, path: str) -> Optional[JetLink]:
        try:
            url = f"https://embedsports.me/{path}"
            r = requests.get(url, headers=self._get_headers("https://embedsports.me/"), timeout=self.timeout)
            
            if not r.ok:
                return None
                
            stream_url = self._get_stream_url(r.text)
            if stream_url:
                return JetLink(
                    address=stream_url,
                    headers=self._get_headers(url)
                )
                
            return None
            
        except Exception as e:
            self._log(f"Error resolving embedsports: {str(e)}", xbmc.LOGERROR)
            return None

    def _resolve_plytv(self, url: str) -> Optional[JetLink]:
        try:
            r = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            if not r.ok:
                return None

            # Try to find authentication URL
            auth_url = re.search(r'auth_url\s*=\s*["\']([^"\']+)["\']', r.text)
            if auth_url:
                auth_url = auth_url.group(1)
                if not auth_url.startswith('http'):
                    auth_url = 'https:' + auth_url if auth_url.startswith('//') else auth_url
                    
                # Get stream URL from auth endpoint
                r = requests.get(auth_url, headers=self._get_headers(url), timeout=self.timeout)
                if r.ok:
                    try:
                        data = r.json()
                        if 'url' in data:
                            return JetLink(
                                address=data['url'],
                                headers=self._get_headers(auth_url)
                            )
                    except:
                        pass
                        
            # Try direct stream URL
            stream_url = self._get_stream_url(r.text)
            if stream_url:
                return JetLink(
                    address=stream_url,
                    headers=self._get_headers(url)
                )
                
            return None
            
        except Exception as e:
            self._log(f"Error resolving plytv: {str(e)}", xbmc.LOGERROR)
            return None

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        try:
            items = []
            if self.progress_init(progress, items):
                return items
                
            self._log("Getting items from 720pstream")
            base_url = f"https://{self.domains[0]}"
            
            try:
                r = requests.get(base_url, headers=self._get_headers(), timeout=self.timeout)
                r.raise_for_status()
                
                soup = BeautifulSoup(r.text, 'html.parser')
                
                # Find all league containers
                for li in soup.select("li.nav-item"):
                    try:
                        league = li.text.strip()
                        if self.progress_update(progress, league):
                            return items
                            
                        self._log(f"Processing league: {league}")
                        
                        # Get league icon
                        icon = li.find("img")
                        icon = icon.get("src") if icon else None
                        
                        # Get league URL
                        league_link = li.find("a")
                        if not league_link:
                            continue
                            
                        href = league_link.get("href")
                        if not href:
                            continue
                            
                        if not href.startswith('http'):
                            href = base_url + ('' if href.startswith('/') else '/') + href
                            
                        # Get games in league
                        try:
                            r_league = requests.get(href, headers=self._get_headers(base_url), timeout=self.timeout)
                            r_league.raise_for_status()
                            
                            soup_league = BeautifulSoup(r_league.text, "html.parser")
                            
                            for game in soup_league.select("a.btn"):
                                try:
                                    # Get game title
                                    game_title_elem = game.select_one("span.text-success")
                                    if not game_title_elem:
                                        continue
                                        
                                    game_title = game_title_elem.text.strip()
                                    
                                    # Get game icon
                                    game_icon = game.select_one("img")
                                    game_icon = game_icon.get("src") if game_icon else icon  # Fallback to league icon
                                    
                                    # Get game URL
                                    game_href = game.get("href")
                                    if not game_href:
                                        continue
                                        
                                    if not game_href.startswith('http'):
                                        game_href = base_url + ('' if game_href.startswith('/') else '/') + game_href
                                    
                                    # Get game time
                                    game_time = game.select_one("div.text-warning")
                                    utc_time = None
                                    
                                    if game_time and game_time.text != "24/7":
                                        time_elem = game_time.find("time")
                                        if time_elem:
                                            time_str = time_elem.get("datetime")
                                            if time_str:
                                                try:
                                                    if "-04" in time_str:
                                                        time_format = "%Y-%m-%dT%H:%M:%S-04:00"
                                                    else:
                                                        time_format = "%Y-%m-%dT%H:%M:%S-05:00"
                                                    parsed_time = datetime.strptime(time_str, time_format)
                                                    utc_time = parsed_time + timedelta(hours=5)
                                                except Exception as e:
                                                    self._log(f"Error parsing time {time_str}: {str(e)}", xbmc.LOGWARNING)
                                    
                                    # Create game item
                                    items.append(JetItem(
                                        title=game_title,
                                        links=[JetLink(game_href, headers=self._get_headers(href))],
                                        league=league,
                                        icon=game_icon,
                                        starttime=utc_time
                                    ))
                                    
                                    self._log(f"Added game: {game_title} in {league}")
                                    
                                except Exception as e:
                                    self._log(f"Error processing game in {league}: {str(e)}", xbmc.LOGERROR)
                                    continue
                                    
                        except requests.exceptions.RequestException as e:
                            self._log(f"Error getting league {league} games: {str(e)}", xbmc.LOGERROR)
                            continue
                            
                    except Exception as e:
                        self._log(f"Error processing league: {str(e)}", xbmc.LOGERROR)
                        continue
                
            except requests.exceptions.RequestException as e:
                self._log(f"Error accessing {base_url}: {str(e)}", xbmc.LOGERROR)
                # Try alternate domain
                base_url = f"https://{self.domains[1]}"
                try:
                    r = requests.get(base_url, timeout=self.timeout, headers=self._get_headers())
                    r.raise_for_status()
                except requests.exceptions.RequestException as e:
                    self._log(f"Error accessing alternate domain {base_url}: {str(e)}", xbmc.LOGERROR)
                    return items
            
            if not items:
                self._log("No items found")
            else:
                self._log(f"Found {len(items)} items")
                
            return items
            
        except Exception as e:
            self._log(f"Error in get_items: {str(e)}", xbmc.LOGERROR)
            return []

    def get_link(self, url: JetLink) -> Optional[JetLink]:
        try:
            if not url or not url.address:
                self._log("Invalid URL object or empty address", xbmc.LOGERROR)
                return None

            self._log(f"Processing URL: {url.address}")
            
            # Handle direct m3u8 URLs
            if '.m3u8' in url.address:
                self._log("Direct m3u8 URL found")
                return JetLink(
                    address=url.address,
                    headers=self._get_headers(url.address)
                )
                
            # Handle special domains
            if "embedsports.me" in url.address:
                self._log("Resolving embedsports.me URL")
                path = url.address.split("embedsports.me/")[-1].split("|")[0]
                result = self._resolve_embedsports(path)
                if not result:
                    self._log("Failed to resolve embedsports.me URL", xbmc.LOGWARNING)
                return result
            elif "plytv.me" in url.address:
                self._log("Resolving plytv.me URL")
                result = self._resolve_plytv(url.address)
                if not result:
                    self._log("Failed to resolve plytv.me URL", xbmc.LOGWARNING)
                return result
                
            # Get initial page
            try:
                r = requests.get(
                    url.address,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                self._log(f"Failed to get page: {str(e)}", xbmc.LOGERROR)
                return None
                
            # Try to find stream URL
            stream_url = self._get_stream_url(r.text)
            if not stream_url:
                self._log("No stream URL found in page content", xbmc.LOGWARNING)
                return None

            # Handle relative URLs
            if stream_url.startswith('/'):
                base_url = 'https://720pstream.nu'
                stream_url = base_url + stream_url
                self._log(f"Converted relative URL to: {stream_url}")
                    
            # Validate the stream URL
            try:
                validate_r = requests.head(
                    stream_url,
                    headers=self._get_headers(url.address),
                    timeout=self.timeout,
                    allow_redirects=True
                )
                validate_r.raise_for_status()
                    
                # Check content type
                content_type = validate_r.headers.get('content-type', '').lower()
                if 'text/html' in content_type:
                    self._log("Stream URL returned HTML instead of video content", xbmc.LOGWARNING)
                    return None
                elif not any(t in content_type for t in ['video', 'application/x-mpegurl', 'application/vnd.apple.mpegurl']):
                    self._log(f"Unexpected content type: {content_type}", xbmc.LOGWARNING)
                    # Continue anyway as some servers might not report correct content type
                        
                self._log("Stream URL validated successfully")
                return JetLink(
                    address=stream_url,
                    headers=self._get_headers(url.address)
                )
                        
            except requests.exceptions.RequestException as e:
                self._log(f"Error validating stream URL: {str(e)}", xbmc.LOGERROR)
                # Try returning the stream URL anyway as some servers block HEAD requests
                self._log("Returning unvalidated stream URL as fallback")
                return JetLink(
                    address=stream_url,
                    headers=self._get_headers(url.address)
                )
            
            self._log("No valid stream found")
            return None
            
        except Exception as e:
            self._log(f"Error in get_link: {str(e)}", xbmc.LOGERROR)
            return None