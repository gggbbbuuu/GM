
import requests, re, time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..models import *

class SportyBite(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["castwebsport.com"]
        self.name = "SportyBite"
        self.league_dict = {
            7: "UEFA Champions League",
            8: "Europa League",
            9: "F1",
            10: "NBA",
            13: "Premier League",
            20: "WWE",
            29: "NFL",
            31: "Boxing",
            34: "MLB",
            46: "NHL",
            78: "Bundesliga",
            79: "La Liga",
            83: "NCAAM"
        }

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        # try:
        session.headers.update(headers)
        r = session.get(
            f"https://{self.domains[0]}",
            timeout=self.timeout
        ).text
        soup = BeautifulSoup(r, "html.parser")
        # except Exception as e:
        #     return []
        events_by_league = {}

        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        for game in soup.select("div.event-card"):
            try:
                time_div = game.select_one("div.event-time")
                if not time_div:
                    continue
                time_str = time_div.text.strip().replace("Watch", "").replace("i", "").strip()
                try:
                    time_obj = datetime(*(time.strptime(time_str, "%I:%M %p")[:6])).time()
                    now = datetime.now()
                    event_time = datetime.combine(today, time_obj)
                    if event_time < now:
                        event_time = datetime.combine(tomorrow, time_obj)
                except (ValueError, IndexError):
                    continue
                icon = game.select_one("div.left-section img")
                if icon and icon.get("src"):
                    try:
                        league_id = int(icon["src"].split("/")[-1].split(".")[0])
                        league = self.league_dict.get(league_id, "Other")
                    except (ValueError, IndexError):
                        league = "Other"
                else:
                    league = "Other"
                title_div = game.select_one("div.event-title")
                if not title_div:
                    continue
                title = title_div.text.strip()
                links = []
                buttons = game.select("button.watch-btn")
                for button in buttons:
                    onclick = button.get("onclick", "")
                    if "window.open" in onclick and "hd=" in onclick:
                        stream_id = button.text.replace("Watch", "").replace("i", "").strip()
                        if stream_id:
                            links.append(JetLink(f"https://{self.domains[0]}/tvon.php?hd={stream_id}"))

                event_date = event_time.date()
                if event_date in (today, tomorrow) and links:
                    event_item = JetItem(
                        title,
                        league=league,
                        icon=icon.get("src") if icon else None,
                        links=links,
                        starttime=event_time
                    )
                    if league not in events_by_league:
                        events_by_league[league] = []
                    events_by_league[league].append(event_item)
                    
            except Exception as e:
                continue

        for league in sorted(events_by_league.keys()):
            league_events = sorted(events_by_league[league], key=lambda x: x.starttime)
            items.extend(league_events)

        return items


    def get_link(self, url: JetLink) -> JetLink:
        try:
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            session.headers.update(headers)
            if "watch.php" in url.address:
                stream_id = re.findall(r"stream_id=(.+?)", url.address)[0]
                url.address = f"https://{self.domains[0]}/tvon.php?hd={stream_id}"

            r = session.get(url.address, timeout=self.timeout).text
            fid = re.findall(r'fid="(.+?)"', r)[0]

            embed_url = "https://processbigger.com/maestrohd1.php?player=desktop&live=" + fid
            session.headers.update({
                "Referer": url.address
            })
            
            r_embed = session.get(embed_url, timeout=self.timeout).text
            m3u8 = "".join(eval(re.findall(r"return\((\[.+?\])", r_embed)[0])).replace("\\", "").replace("////", "//")

            return JetLink(m3u8, headers={
                "Referer": embed_url,
                "User-Agent": headers["User-Agent"]
            })

        except Exception as e:
            return None
