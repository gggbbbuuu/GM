from ..models import *
import requests
from bs4 import BeautifulSoup
from ..util import m3u8_src
from ..icons import icons
from datetime import datetime, timedelta

today = datetime.now()
tomorrow = today + timedelta(days=1)
today_str = today.strftime("%A, %B %d, %Y")
tomorrow_str = tomorrow.strftime("%A, %B %d, %Y")

class TopEmbed(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["topembed.pw"]
        self.name = "TopEmbed"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        events_by_league = {}
        if self.progress_init(progress, items):
            return items

        LEAGUE_MAPPING = {
            "NBA": "NBA",
            "NFL": "NFL",
            "NHL": "NHL",
            "MLB": "MLB",
            "NCAA F": "NCAAF",
            "NCAA B": "NCAAB",
            "Soccer": "Soccer",
            "UFC": "UFC",
            "Boxing": "Boxing",
            "WWE": "WWE",
            "MMA": "MMA",
            "Tennis": "Tennis",
            "Golf": "Golf",
            "Rugby": "Rugby",
            "Cricket": "Cricket",
            "NASCAR": "NASCAR",
            "F1": "F1",
            "MotoGP": "MotoGP",
            "IndyCar": "IndyCar",
            "Supercross": "Supercross",
            "Darts": "Darts",
            "Snooker": "Snooker",
            "Table Tennis": "Table Tennis",
            "Volleyball": "Volleyball",
            "Handball": "Handball",
            "Basketball": "Basketball",
            "Hockey": "Hockey",
            "Baseball": "Baseball",
            "Football": "Soccer"
        }

        r = requests.get(f"https://{self.domains[0]}?all").text
        soup = BeautifulSoup(r, "html.parser")
        current_date = None
        
        for element in soup.select("div.bg-gray-800, div.bg-white"):
            if "bg-gray-800" in element.get("class", []):
            
                current_date = element.text.strip()
                continue
            
            if current_date not in [today_str, tomorrow_str]:
                continue
            
            if "bg-white" in element.get("class", []):
                title1 = element.select_one("div.font-bold").text
                title2 = element.select_one("div.mb-2").text.replace("Info: ", "")
                title3 = current_date

                leagues = title2.replace("Info: ", "")
                for key, value in LEAGUE_MAPPING.items():
                    if key in leagues:
                        leagues = value
                        break

                title = f"{title1} - {title2} ({title3})"
                links = []
                for channel in element.select("div.mb-4 > div > input"):
                    l = channel.get("value")
                    if not l.startswith("https"):
                        continue
                    link = JetLink(l)
                    if "/channel/" in l:
                        link.name = l.split("/")[-1]
                    links.append(link)
                
                event_item = JetItem(
                    icon=icons[leagues.lower()] if leagues.lower() in icons else None,
                    league=leagues.upper(),
                    title=title,
                    links=links
                )
                
                if leagues not in events_by_league:
                    events_by_league[leagues] = []
                events_by_league[leagues].append(event_item)
        
        for league in sorted(events_by_league.keys()):
            items.extend(events_by_league[league])

        r = requests.get(f"https://{self.domains[0]}?show_tv=true").text
        soup = BeautifulSoup(r, "html.parser")
        tv_items = []
        for channel in soup.select("tbody > tr"):
            title = channel.select_one("td").text
            l = channel.select_one("input").get("value")
            link = JetLink(l, name=l.split("/")[-1])
            tv_items.append(JetItem(title, [link]))
        
        items.extend(tv_items)
        return items


    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address, headers={"Referer": f"https://{self.domains[0]}/"}).text
        m3u8 = m3u8_src.scan(r)
        return JetLink(m3u8, headers={"Referer": f"https://{self.domains[0]}/", "Origin": f"https://{self.domains[0]}"}, inputstream=JetInputstreamFFmpegDirect.default())
