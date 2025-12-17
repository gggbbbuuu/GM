from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamAdaptive
from typing import Optional, List
from .embedsports import Embedsports
import requests
from datetime import datetime
from urllib3.util import SKIP_HEADER
import xbmc
import base64

class Streamed(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamed.pk"]
        self.name = "Streamed"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        sports = requests.get(f"https://{self.domains[0]}/api/sports").json()
        sports_map = { sport["id"]: sport["name"] for sport in sports }

        matches = requests.get(f"https://{self.domains[0]}/api/matches/all-today/popular").json()
        for match in matches:
            title = match["title"]
            if match["date"] != 0:
                match_time = datetime.fromtimestamp(match["date"] / 1000)
            else:
                match_time = None
            print(title, match_time)
            sport = sports_map[match["category"]]
            
            # Skip Basketball matches until codec extradata issues are resolved
            if sport.lower() in ['basketball', 'nba']:
                xbmc.log(f"[Streamed] Skipping Basketball match: {title}", xbmc.LOGINFO)
                continue
            
            links = [JetLink(f"https://{self.domains[0]}/api/stream/{source['source']}/{source['id']}", links=True, name=source["source"].capitalize()) for source in match["sources"]]
            items.append(JetItem(title, links, match_time, league=sport))
        return items
    
    def get_links(self, url):
        if "/api/" in url.address:
            streams = requests.get(url.address, headers={"Accept-Encoding": SKIP_HEADER}).json()
            if "/embed/" in url.address:
                links = [JetLink(f"https://{self.domains[0]}/api/stream/{stream['source']}/{stream['id']}", name=stream["source"], links=True) for stream in streams]
            else:
                links = [JetLink(stream["embedUrl"], name=f"Stream {stream['streamNo']} [{stream['language'] or 'N/A'}, {'HD' if stream['hd'] else 'SD'}, {stream['viewers']} viewers]") for stream in streams]
            return links
        elif "/watch/" in url.address:
            match_id = url.address.split("/")[-1]
            matches = requests.get(f"https://{self.domains[0]}/api/matches/all").json()
            for match in matches:
                if match["id"] != match_id:
                    continue
                links = [JetLink(f"https://{self.domains[0]}/api/stream/{source['source']}/{source['id']}", links=True, name=source["source"].capitalize()) for source in match["sources"]]
                return links
    
    def get_link(self, url):
        if "/watch/" not in url.address:
            split = url.address.split("/")
            source = split[-2]
            source_id = split[-1]
            stream_url = f"https://{self.domains[0]}/api/stream/{source}/{source_id}"
            
            xbmc.log(f"[Streamed] Fetching stream from: {stream_url}", xbmc.LOGINFO)
            
            # Fetch the playlist to check for .png disguised segments
            headers = {
                "User-Agent": self.user_agent,
                "Referer": f"https://{self.domains[0]}/"
            }
            
            try:
                response = requests.get(stream_url, headers=headers, timeout=10, verify=False)
                response.raise_for_status()
                playlist_content = response.text
                
                xbmc.log(f"[Streamed] Playlist content preview: {playlist_content[:200]}", xbmc.LOGINFO)
                
                # Check if playlist has .png segments (disguised as images)
                if '.png' in playlist_content:
                    xbmc.log(f"[Streamed] Detected .png disguised segments, patching to .ts", xbmc.LOGINFO)
                    # Replace .png with .ts
                    modified_playlist = playlist_content.replace('.png', '.ts')
                    # Encode as base64 data URL
                    encoded_playlist = base64.b64encode(modified_playlist.encode('utf-8')).decode('utf-8')
                    play_url = f"data:application/vnd.apple.mpegurl;base64,{encoded_playlist}"
                    
                    xbmc.log(f"[Streamed] Using base64 encoded playlist", xbmc.LOGINFO)
                    return JetLink(
                        play_url,
                        headers=headers,
                        inputstream=JetInputstreamAdaptive.hls()
                    )
                else:
                    xbmc.log(f"[Streamed] Normal playlist, using direct URL", xbmc.LOGINFO)
                    return JetLink(
                        stream_url,
                        headers=headers,
                        inputstream=JetInputstreamAdaptive.hls()
                    )
                    
            except Exception as e:
                xbmc.log(f"[Streamed] Error fetching playlist: {str(e)}", xbmc.LOGERROR)
                # Fallback to direct URL
                return JetLink(
                    stream_url,
                    headers=headers,
                    inputstream=JetInputstreamAdaptive.hls()
                )