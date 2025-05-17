import requests
import re
from datetime import datetime, timedelta
import xbmc
from bs4 import BeautifulSoup
import pytz
from ..models import *

class SportyBite(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["piratcast.tv", "castwebsport.com", "sons-stream.com"]
        self.name = "SportyBite"
        self.league_dict = {
            "NBA": "NBA",
            "WNBA": "WNBA",
            "NHL": "NHL",
            "MLB": "MLB",
            "NFL": "NFL",
            "Boxing": "Boxing",
            "Premier League": "Premier League",
            "Bundesliga": "Bundesliga",
            "La Liga": "La Liga",
            "UEFA Champions League": "UEFA Champions League",
            "Europa League": "Europa League",
            "F1": "F1",
            "WWE": "WWE",
            "NCAAM": "NCAAM",
            "IIHF World Championship 2025": "IIHF"
        }

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            }

        api_paths = ["/api-panel.php"]
        data = None
        utc_tz = pytz.UTC
        # Use system's local timezone
        try:
            local_tz = datetime.now().astimezone().tzinfo
        except Exception:
            local_tz = pytz.timezone("America/Los_Angeles")
        
        now_utc = datetime.now(utc_tz)
        now_local = now_utc.astimezone(local_tz)
        offset_hours = int((now_local.utcoffset().total_seconds() / 3600))
        correction_hours = abs(offset_hours)
        

        for domain in self.domains:
            headers['Referer'] = f'https://{domain}/'
            for path in api_paths:
                api_url = f"https://{domain}{path}"
                try:
                    session.headers.update(headers)
                    r = session.get(api_url, timeout=self.timeout)
                    r.raise_for_status()
                    data = r.json()
                    break
                except Exception as e:
                    continue
            if data:
                break

        if data:
            events_by_league = {}
            today = datetime.now(local_tz).date()
            tomorrow = today + timedelta(days=1)
            
            for category in data:
                category_name = category.get("category", "Unknown")
                for stream in category.get("streams", []):
                    try:
                        title = stream["name"]
                        league = self.league_dict.get(stream["tag"], "Other")
                        start_time_utc = datetime.fromtimestamp(stream["starts_at"], tz=utc_tz)
                        start_time_local = start_time_utc.astimezone(local_tz)
                        start_time = start_time_local.replace(tzinfo=None) + timedelta(hours=correction_hours)
                        iframe_url = stream["iframe"]
                        event_date = start_time.date()
                        
                        if event_date not in (today, tomorrow):
                            continue

                        event_item = JetItem(
                            title=title,
                            league=league,
                            icon="https://piratcast.tv/favicon.ico",
                            links=[JetLink(iframe_url, direct=False)],
                            starttime=start_time,
                            status="Live" if start_time <= datetime.now(local_tz).replace(tzinfo=None) <= datetime.fromtimestamp(stream["ends_at"], tz=utc_tz).astimezone(local_tz).replace(tzinfo=None) else "Upcoming"
                        )

                        if league not in events_by_league:
                            events_by_league[league] = []
                        events_by_league[league].append(event_item)

                    except Exception as e:
                        continue

            for league in sorted(events_by_league.keys()):
                league_events = sorted(events_by_league[league], key=lambda x: x.starttime)
                items.extend(league_events)
                
        if not data:
            # try:
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            r = session.get(f"https://{self.domains[0]}/", timeout=self.timeout)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for game in soup.select("div.event-card"):
                try:
                    title_elem = game.select_one("div.event-title")
                    time_elem = game.select_one("div.event-time")
                    button = game.select_one("button.watch-btn")
                    if not (title_elem and time_elem and button):
                        continue
                    title = title_elem.text.strip()
                    time_str = time_elem.text.strip().replace("Watch", "").replace("i", "").strip()
                    onclick = button.get("onclick", "")
                    stream_id = re.findall(r"hd=(\d+)", onclick)
                    if not stream_id:
                        continue
                    iframe_url = f"https://{self.domains[0]}/papa.php?hd={stream_id[0]}"
                    try:
                        start_time = datetime.strptime(time_str, "%I:%M %p")
                        start_time = datetime.combine(today, start_time.time())
                        start_time = pytz.timezone(str(local_tz)).localize(start_time).replace(tzinfo=None) + timedelta(hours=correction_hours)
                        if start_time < datetime.now(local_tz).replace(tzinfo=None):
                            start_time += timedelta(days=1)
                    except ValueError:
                        start_time = datetime.now(local_tz).replace(tzinfo=None)
                    league = "Other"
                    event_item = JetItem(
                        title=title,
                        league=league,
                        icon="https://piratcast.tv/favicon.ico",
                        links=[JetLink(iframe_url, direct=False)],
                        starttime=start_time,
                        status="Upcoming"
                    )
                    items.append(event_item)
                except Exception as e:
                    continue
            
        return items

    def get_link(self, url: JetLink) -> JetLink:
        try:
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                
            }
            session.headers.update(headers)

            if "watch.php" in url.address:
                stream_id = re.findall(r"stream_id=(.+?)", url.address)[0]
                url.address = f"https://{self.domains[0]}/papa.php?hd={stream_id}"

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
            }, inputstream=JetInputstreamAdaptive.hls())

        except Exception as e:
            xbmc.log(f"[SportyBite] Error resolving link {url.address}: {str(e)}", xbmc.LOGERROR)
            return None