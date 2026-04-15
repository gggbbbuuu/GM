from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
from typing import Optional, List
import requests
import re
from bs4 import BeautifulSoup
try:
    import xbmc
    def log(msg):
        xbmc.log(f"[StreamEastGL] {msg}", level=xbmc.LOGINFO)
except ImportError:
    def log(msg):
        print(f"[StreamEastGL] {msg}")

class StreamEastGL(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streameast.gl"]
        self.name = "StreamEast GL"
        self.base_url = "https://streameast.gl"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        sports = [
            ("NBA", "/nba"),
            ("NFL", "/nfl"),
            ("NHL", "/nhl"),
            ("MLB", "/mlb"),
            ("MMA", "/mma"),
            ("BOXING", "/boxing"),
            ("F1", "/f1"),
            ("SOCCER", "/"),
        ]
        
        headers = {
            'User-Agent': self.user_agent
        }
        
        for league, path in sports:
            try:
                url = f"{self.base_url}{path}"
                r = requests.get(url, headers=headers, timeout=10, verify=False)
                soup = BeautifulSoup(r.text, 'html.parser')
                
                # Find game elements - look for links with class="matches"
                # Pattern: /nba/401811026/team-vs-team
                links = soup.find_all('a', class_='matches')
                
                for link in links:
                    href = link.get('href', '')
                    # Get title from aria-label or team names
                    title = link.get('aria-label', '')
                    if not title:
                        team_names = link.find_all('span', class_='team-name')
                        if team_names:
                            title = ' vs '.join([t.get_text(strip=True) for t in team_names])
                    
                    if not title or not href:
                        continue
                    
                    # Clean up title
                    title = re.sub(r'\s+', ' ', title).strip()
                    if len(title) < 3:
                        continue
                    
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    
                    items.append(JetItem(
                        title=title,
                        links=[JetLink(full_url, links=False)],
                        league=league
                    ))
                    
            except Exception as e:
                log(f"Error fetching {path}: {e}")
                continue
        
        log(f"Total items found: {len(items)}")
        return items
    
    def _guess_team(self, team_str: str) -> str:
        # Map common team names
        team_map = {
            "atlanta hawks": "hawks", "hawks": "hawks",
            "boston celtics": "celtics", "celtics": "celtics",
            "brooklyn nets": "nets", "nets": "nets",
            "charlotte hornets": "hornets", "hornets": "hornets",
            "chicago bulls": "bulls", "bulls": "bulls",
            "cleveland cavaliers": "cavaliers", "cavaliers": "cavaliers",
            "dallas mavericks": "mavericks", "mavericks": "mavericks",
            "denver nuggets": "nuggets", "nuggets": "nuggets",
            "detroit pistons": "pistons", "pistons": "pistons",
            "golden state warriors": "warriors", "warriors": "warriors",
            "houston rockets": "rockets", "rockets": "rockets",
            "indiana pacers": "pacers", "pacers": "pacers",
            "la clippers": "clippers", "clippers": "clippers",
            "los angeles lakers": "lakers", "lakers": "lakers",
            "memphis grizzlies": "grizzlies", "grizzlies": "grizzlies",
            "miami heat": "heat", "heat": "heat",
            "milwaukee bucks": "bucks", "bucks": "bucks",
            "minnesota timberwolves": "timberwolves", "timberwolves": "timberwolves",
            "new orleans pelicans": "pelicans", "pelicans": "pelicans",
            "new york knicks": "knicks", "knicks": "knicks",
            "oklahoma city thunder": "thunder", "thunder": "thunder",
            "orlando magic": "magic", "magic": "magic",
            "philadelphia 76ers": "76ers", "76ers": "76ers",
            "phoenix suns": "suns", "suns": "suns",
            "portland trail blazers": "blazers", "blazers": "blazers",
            "sacramento kings": "kings", "kings": "kings",
            "san antonio spurs": "spurs", "spurs": "spurs",
            "toronto raptors": "raptors", "raptors": "raptors",
            "utah jazz": "jazz", "jazz": "jazz",
            "washington wizards": "wizards", "wizards": "wizards",
        }
        team_str = team_str.strip().lower()
        return team_map.get(team_str, "")
    
    def get_links(self, url: JetLink):
        log("get_links ENTRY CALLED")
        url_str = url.address if hasattr(url, 'address') else str(url)
        
        log(f"get_links called with: {url_str}")
        
        if not url_str:
            return []
        
        headers = {
            'User-Agent': self.user_agent
        }
        
        try:
            r = requests.get(url_str, headers=headers, timeout=10, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
        except Exception as e:
            log(f"Error fetching page: {e}")
            return []
        
        links = []
        
        # Look for iframes that might contain streams
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            data_src = iframe.get('data-src', '')
            
            iframe_url = src or data_src
            if iframe_url:
                links.append(JetLink(iframe_url, name="Stream"))
        
        # Also look for video players
        for video in soup.find_all('video'):
            src = video.get('src', '')
            if src:
                links.append(JetLink(src, name="Video"))
        
        # Look for stream URLs in script tags
        for script in soup.find_all('script'):
            script_text = script.get_text('')
            # Look for m3u8 URLs
            matches = re.findall(r'["\']([^"\']*\.m3u8[^"\']*)["\']', script_text)
            for match in matches:
                if match.startswith('http'):
                    links.append(JetLink(match, name="HLS"))
        
        # Look for data attributes with stream URLs
        for elem in soup.find_all(attrs={'data-stream': True}):
            stream_url = elem.get('data-stream')
            if stream_url:
                links.append(JetLink(stream_url, name="Stream"))
        
        if not links:
            # Return the original URL as it might redirect to stream
            links.append(JetLink(url_str, name="Page"))
        
        log(f"Found {len(links)} links")
        return links
    
    def get_link(self, url: JetLink):
        url_str = url.address if hasattr(url, 'address') else str(url)
        
        log(f"Resolving stream for: {url_str}")
        
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://streameast.gl/'
        }
        
        log(f"Fetching URL: {url_str}")
        
        try:
            r = requests.get(url_str, headers=headers, timeout=10, verify=False, allow_redirects=True)
            log(f"Response status: {r.status_code}, content-type: {r.headers.get('content-type', 'unknown')}")
            
            # Check if response is HLS stream
            if '.m3u8' in url_str or r.text.startswith('#EXTM3U'):
                return JetLink(
                    r.url,
                    headers=headers,
                    inputstream=JetInputstreamFFmpegDirect.default()
                )
            
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Try to extract team from URL path - pattern is like /nba/401811026/team1-vs-team2
            path_parts = url_str.rstrip('/').split('/')
            log(f"Path parts: {path_parts}")
            if len(path_parts) >= 4:
                url_title = path_parts[-1].lower()  # e.g., "pistons-vs-hornets"
                log(f"URL title: {url_title}")
                # Extract second team (after "vs-")
                if '-vs-' in url_title:
                    team_part = url_title.split('-vs-')[-1]
                    team = team_part.replace('-', ' ')
                    log(f"Extracted team string: '{team}'")
                    # Try to find team name from available teams
                    team = self._guess_team(team)
                    log(f"Mapped team: '{team}'")
                    if team:
                        m3u8_url = f"https://s3.us-east-1.amazonaws.com/emre.gundap/{team}_480p30.m3u8"
                        log(f"Trying m3u8: {m3u8_url}")
                        # Verify it exists
                        try:
                            check = requests.head(m3u8_url, timeout=5, verify=False)
                            log(f"HEAD response: {check.status_code}")
                            if check.status_code == 200:
                                log(f"Found valid stream!")
                                return JetLink(
                                    m3u8_url,
                                    headers={
                                        "Origin": "https://streamspass.net",
                                        "Referer": "https://streamspass.net/",
                                        "User-Agent": self.user_agent
                                    },
                                    inputstream=JetInputstreamFFmpegDirect.default()
                                )
                        except:
                            pass
            
            # Fallback: try iframe
            iframe = soup.select_one('iframe#iframe') or soup.select_one('iframe') or soup.select_one('iframe.embed-responsive-item')
            if iframe:
                src = iframe.get('src', '')
                if src:
                    log(f"Found iframe: {src}")
                    if 'streamspass' in src:
                        team = src.split('/')[-1].replace('.html', '')
                        m3u8_url = f"https://s3.us-east-1.amazonaws.com/emre.gundap/{team}_480p30.m3u8"
                        return JetLink(
                            m3u8_url,
                            headers={
                                "Origin": "https://streamspass.net",
                                "Referer": "https://streamspass.net/",
                                "User-Agent": self.user_agent
                            },
                            inputstream=JetInputstreamFFmpegDirect.default()
                        )
            
            # Look for video source
            video = soup.select_one('video source') or soup.select_one('video')
            if video:
                src = video.get('src') or video.get('src')
                if src:
                    return JetLink(
                        src,
                        headers={
                            "Referer": url_str,
                            "User-Agent": self.user_agent
                        },
                        inputstream=JetInputstreamFFmpegDirect.default()
                    )
            
            # Check for direct m3u8 in response
            if '.m3u8' in r.url:
                return JetLink(
                    r.url,
                    headers=headers,
                    inputstream=JetInputstreamFFmpegDirect.default()
                )
            
            # If still no stream found, return the URL with appropriate headers
            return JetLink(
                url_str,
                headers={
                    "Referer": "https://streameast.gl/",
                    "User-Agent": self.user_agent
                },
                inputstream=JetInputstreamFFmpegDirect.default()
            )
            
        except Exception as e:
            log(f"Error resolving stream: {e}")
            return JetLink(url_str, name="Error")