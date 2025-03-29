import requests
from bs4 import BeautifulSoup
from ..models import *
from ..icons import icons
from ..util import find_iframes
from ..util import m3u8_src
import re
from typing import Optional, List
from urllib.parse import urljoin

class HDStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["ww1.ihdstreams.xyz","live.hdstreams.vip"]
        self.name = "HDStreams"
#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        session = requests.Session()
        leagues = ["NFL","NBA","NHL","F1","NCAAB","MLB","CFB","XFL","MLS","UFC","Boxing","WWE"]
        for league in leagues:
            if self.progress_update(progress, league):
                return items
            
            schedule_url = f"https://{self.domains[0]}/Schedule/{league}-Schedule"
            xbmc.log(f"HDStreams fetching schedule: {schedule_url}", level=xbmc.LOGINFO)
            
            try:
                r = session.get(schedule_url, timeout=self.timeout)
                xbmc.log(f"HDStreams schedule response status: {r.status_code}", level=xbmc.LOGINFO)
                
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    game_blocks = soup.find_all("a", class_="block w-full rounded overflow-hidden shadow-md hover:shadow-lg mb-6 bg-white")
                    xbmc.log(f"HDStreams found {len(game_blocks)} games", level=xbmc.LOGINFO)
                    
                    for block in game_blocks:
                        href = block.get("href", "")
                        title_elem = block.find("h3", class_="text-sm sm:text-xl mb-2")
                        date_elem = block.find("p", class_="text-gray-700 text-xs sm:text-sm")
                        
                        if title_elem:
                            title = title_elem.text.strip()
                            date = date_elem.text.strip() if date_elem else ""
                            
                            xbmc.log(f"HDStreams adding game: {title} - {href}", level=xbmc.LOGINFO)
                            items.append(JetItem(
                                title=f"{title} - {date}",
                                icon=icons.get(league.lower(), ""),
                                league=league.upper(),
                                links=[JetLink(address=href)],
                            ))
            
            except Exception as e:
                xbmc.log(f"HDStreams error: {str(e)}", level=xbmc.LOGERROR)
                continue
            
        return items
    
            
        
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        re_iframe = re.findall(r'iframe.+?src="(.+?)"',r)[0]
        iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes.find_iframes(re_iframe)]
        link = iframes[0]
        # if "hutg54" in link.address:
        #     link.headers["Referer"] = f"https://{self.domains[2]}"
        # else:
        link.headers["Referer"] = f"https://{self.domains[1]}"
        link.inputstream = JetInputstreamFFmpegDirect.default()
        return link    