from ..models import *
from typing import Optional, List
from datetime import datetime, timezone
import requests
import xbmc

def fix_league(s: str) -> str:
    return " ".join(x.capitalize() for x in s.split()) if len(s) > 5 else s.upper()

class EmbedHD(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["embedhd.org"]
        self.name = "EmbedHD"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Referer": "https://embedhd.org/"
            }
            api_response = requests.get("https://embedhd.org/api-event.php", timeout=10, verify=False, headers=headers).json()
        except Exception as e:
            xbmc.log(f"[EmbedHD] Error fetching API: {str(e)}", xbmc.LOGERROR)
            return items
        
        now = datetime.now(timezone.utc)
        for day in api_response.get("days", []):
            for match in day.get("items", []):
                title = match["title"]
                league_raw = match["league"]
                league = fix_league(league_raw)
                
                ts_et = match.get("ts_et")
                if ts_et:
                    match_time = datetime.fromtimestamp(ts_et, tz=timezone.utc)
                    if (match_time - now).total_seconds() > 86400:
                        continue
                else:
                    match_time = None
                
                # xbmc.log(f"[EmbedHD] Found match: {title} ({league}) at {match_time}", xbmc.LOGINFO)
                
                streams = match.get("streams", [])
                links = [JetLink(stream["link"], links=False, name=f"HD{stream['hd']}") for stream in streams if stream.get("link")]
                
                items.append(JetItem(title, links, match_time, league=league))
        
        return items

    def get_links(self, url):
        return []

    def get_link(self, url):
        xbmc.log(f"[EmbedHD] Looking up stream from JSON for: {url.address}", xbmc.LOGINFO)
        
        try:
            json_url = "https://magnetic.website/Jetextractor/EmbedHD/embedhd_scrape1.json"
            response = requests.get(json_url, timeout=10, verify=False)
            response.raise_for_status()
            json_data = response.json()
            
            # xbmc.log(f"[EmbedHD] Loaded JSON with {len(json_data)} entries", xbmc.LOGINFO)
            
            # Search for matching URL in the JSON data
            for entry in json_data:
                if entry.get("url") == url.address:
                    # xbmc.log(f"[EmbedHD] Found match: {entry.get('title', 'Unknown')}", xbmc.LOGINFO)
                    
                    # Get the links array
                    links = entry.get("links", [])
                    if not links:
                        xbmc.log(f"[EmbedHD] No links found in JSON entry", xbmc.LOGWARNING)
                        return JetLink("", name="No links available")
                    
                    link_data = links[0]
                    stream_address = link_data.get("address")
                    
                    if not stream_address:
                        xbmc.log(f"[EmbedHD] No address found in link data", xbmc.LOGWARNING)
                        return JetLink("", name="No stream address")
                    headers = link_data.get("headers", {})
                    # Remove empty header values
                    headers = {k: v for k, v in headers.items() if v}
                    
                    if not headers:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
                        }
                    
                    xbmc.log(f"[EmbedHD] Returning stream: {stream_address[:80]}...", xbmc.LOGINFO)
                    # xbmc.log(f"[EmbedHD] Headers (filtered): {headers}", xbmc.LOGDEBUG)
                    
                    return JetLink(
                        stream_address,
                        headers=headers,
                        inputstream=JetInputstreamFFmpegDirect.default()
                    )
            
            # No match found
            xbmc.log(f"[EmbedHD] No matching URL found in JSON for: {url.address}", xbmc.LOGWARNING)
            return JetLink("", name="Stream not found in database")
            
        except Exception as e:
            xbmc.log(f"[EmbedHD] Error fetching JSON or parsing: {str(e)}", xbmc.LOGERROR)
            return JetLink("", name=f"Error: {str(e)}")