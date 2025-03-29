import requests, re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..models import *
from .sportybite import SportyBite

class SportyBitev2(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["matchpulse.io"]
        self.name = "SportyBitev2"
        # Map league names based on logo filenames
        self.league_dict = {
            "nhl": "NHL",
            "nba": "NBA",
            "mlb": "MLB",
            "nfl": "NFL",
            "ncaam": "NCAAM",
            "uefa": "UEFA Champions League",
            "premier": "Premier League",
            "laliga": "La Liga",
            "boxing": "Boxing",
            "boxing-1": "Boxing",
            "boxing-stream": "Boxing",
            "mma": "MMA",
            "19": "MLS",
            "soccer/19": "MLS",
            "f1": "Formula 1",
            "bundesliga": "Bundesliga"
        }

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        events_by_league = {}
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        current_date = None

        for block in soup.select("div.event-blocks-wrapper > div"):
            try:
                if "March" in block.text or "April" in block.text:
                    date_str = block.text.strip()
                    try:
                        current_date = datetime.strptime(date_str, "%B %d, %Y").date()
                    except ValueError:
                        continue
                    continue
                if not block.select_one("div.event-row") or current_date not in (today, tomorrow):
                    continue
                time_div = block.select_one("div[style*='flex-basis: 10%']")
                if not time_div:
                    continue
                time_str = time_div.text.strip()
                try:
                    time_obj = datetime.strptime(time_str, "%I:%M %p").time()
                    event_time = datetime.combine(current_date, time_obj)
                except ValueError:
                    continue
                league_img = block.select_one("div[style*='flex-basis: 5%'] img")
                if not league_img:
                    continue
                league = "Other"
                img_src = league_img.get('src', '').lower()
                if 'espncdn.com' in img_src:
                    parts = img_src.split('/')
                    league_id = parts[-1].split('.')[0]
                    if league_id in self.league_dict:
                        league = self.league_dict[league_id]
                    elif f"soccer/{league_id}" in self.league_dict:
                        league = self.league_dict[f"soccer/{league_id}"]
                else:
                    for league_key in self.league_dict:
                        if league_key in img_src:
                            league = self.league_dict[league_key]
                            break
                single_title = block.select_one("div[style*='flex-basis: 70%']")
                if single_title:
                    title = single_title.text.strip()
                else:
                    teams = block.select("div[style*='flex-basis: 25%']")
                    if len(teams) < 2:
                        continue
                    team1 = teams[0].select_one("span").text.strip()
                    team2 = teams[1].select_one("span").text.strip()
                    title = f"{team1} VS {team2}"

                team1_icon = teams[0].select_one("img").get("src") if teams[0].select_one("img") else None
                team2_icon = teams[1].select_one("img").get("src") if teams[1].select_one("img") else None
                href = block.select_one("a").get("href")
                if not href:
                    continue

                event_item = JetItem(
                    title,
                    league=league,
                    icon=league_img.get("src"),
                    links=[JetLink(href)],
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
        r = requests.get(url.address).text
        hd = re.findall(r'\?hd=(.+?)"', r)[0]
        sportybite = SportyBite()
        return sportybite.get_link(JetLink(f"https://{sportybite.domains[0]}/tvon.php?hd={hd}"))
