import re
from urllib.parse import urlparse
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from ..models import *

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'


class WebcastGrouped(JetExtractor):
    domains = ["nbawebcast.app", "mlbwebcast.com", "nhlwebcast.com", "nflwebcast.com"]
    name = "Webcast Grouped"
    
    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        if params is None:
            items.append(JetItem(title="NBA", links=[], params={"league": "NBA", "index": "0"}))
            items.append(JetItem(title="MLB", links=[], params={"league": "MLB", "index": "1"}))
            items.append(JetItem(title="NHL", links=[], params={"league": "NHL", "index": "2"}))
            items.append(JetItem(title="NFL", links=[], params={"league": "NFL", "index": "3"}))
        
        else:
            league = params["league"]
            index = int(params["index"])
            domain = self.domains[index]
            base_url = f"https://{domain}"
            headers = {
                'User-Agent': USER_AGENT,
                'Referer': base_url,
                'Origin': base_url
            }
            response = requests.get(base_url, headers=headers, timeout=self.timeout)
            soup = BeautifulSoup(response.text, "html.parser")
            for game in soup.select("tr.singele_match_date "):
                
                if "mdatetitle" in game.attrs["class"]:
                    continue
                    
                try:
                    teamvs = game.select_one("td.teamvs")
                    name = teamvs.text
                    mtdate = teamvs.find(class_="mtdate").text
                    name = name.replace(mtdate, '').replace('  ', ' ').strip()
                except:
                    name = " ".join(game.select_one("td.teamvs").text.strip().replace("  ", " ").split(" ")[:3])
                    
                if self.progress_update(progress, name):
                    return items
                    
                icon = game.select_one("img").get("src")
                game_time = game.select_one("td.matchtime").text.strip().split(":")
                hour = int(game_time[0])
                if hour < 12:
                    hour = hour + 12 #assume PM game
                minute = int(game_time[1])
                local_dt = datetime.now().replace(hour=hour, minute=minute)
                offset = datetime.now().astimezone().utcoffset()
                utc_time = local_dt - offset
                link = game.find(class_="btn btn-info").get("href")
                if link:
                    items.append(JetItem(name, links=[JetLink(link, links=True)], icon=icon, starttime=utc_time, league=league))
        return items
        
        
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        parsed = urlparse(url.address)
        referer = f'https://{parsed.netloc}'
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': referer,
            'Origin': referer
        }
        response = requests.get(url.address, headers=headers, timeout=self.timeout)
        soup = BeautifulSoup(response.text, "html.parser")
        container = soup.find("div", id="multistmb")
        if container:
            for _, a_tag in enumerate(container.find_all("a")[:2]):
                link = a_tag.get("href")
                name = a_tag.get_text(strip=True)
                links.append(JetLink(name=name, address=link))
        return links
    
    def get_link(self, url: JetLink) -> JetLink:
        parsed = urlparse(url.address)
        referer = f'https://{parsed.netloc}'
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': referer,
            'Origin': referer
        }
        response = requests.get(url.address, headers=headers, timeout=self.timeout)
        match = re.search(r"source:\s*'([^']+)'", response.text)
        if not match:
            return None
        m3u8 = match.group(1)
        link = JetLink(m3u8, headers=headers, inputstream = JetInputstreamFFmpegDirect.default())
        return link


class Webcast(WebcastGrouped):
    domains = ["nbawebcast.app", "mlbwebcast.com", "nhlwebcast.com", "nflwebcast.com"]
    name = "Webcast"
    
    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        for domain in self.domains:
            if self.progress_update(progress, domain):
                return items

            r = requests.get(f"https://{domain}", timeout=self.timeout).text
            soup = BeautifulSoup(r, "html.parser")
            for game in soup.select("tr.singele_match_date "):
                if "mdatetitle" in game.attrs["class"]:
                    continue
                
                try:
                    teamvs = game.select_one("td.teamvs")
                    name = teamvs.text
                    mtdate = teamvs.find(class_="mtdate").text
                    name = name.replace(mtdate, '').replace('  ', ' ').strip()
                except:
                    name = " ".join(game.select_one("td.teamvs").text.strip().replace("  ", " ").split(" ")[:3])
                    
                if domain == self.domains[0]:
                    sport = "NBA"
                    name = f"[COLORaqua]{sport}: [/COLOR]" + name
                elif domain == self.domains[1]:
                    sport = "MLB"
                    name = f"[COLORorange]{sport}: [/COLOR]" + name
                elif domain == self.domains[2]:
                    sport = "NHL"
                    name = f"[COLORyellow]{sport}: [/COLOR]" + name
                elif domain == self.domains[3]:
                    sport = "NFL"
                    name = f"[COLORlime]{sport}: [/COLOR]" + name    
                game_time = game.select_one("td.matchtime").text.strip().split(":")
                game_icon = game.select_one("img").get("src")
                hour = int(game_time[0])
                minute = int(game_time[1])
                utc_time = datetime.now().replace(hour=hour, minute=minute) + timedelta(hours=17)
                href = game.find("a").get("href")
                items.append(JetItem(title=name, starttime=utc_time, icon=game_icon, links=[JetLink(href, links=True)]))
                
        return items
