import requests, time
from datetime import datetime, timedelta
from ..models import *
from ..util.sportscentral_streams import get_streams_table

class SportsCentral(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["sportscentral.io", "scdn.dev"]
        self.name = "SportsCentral"
        self.short_name = "SC"
#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        current_date = datetime.now()
        today = current_date.replace(hour=3, minute=0, second=0)
        date_format = current_date.strftime("%Y-%m-%d")

        leagues = ["nba", "nfl", "mlb", "nhl", "mma", "motorsport", "cricket"]
        for league in leagues:
            if self.progress_update(progress, league):
                return items
            r = requests.get("https://sportscentral.io/api/%s-tournaments?date=%s" % (league, date_format), headers={"Referer": "https://reddit1.nbabite.com", "User_Agent": self.user_agent}, timeout=self.timeout).json()
            for game_league in r:
                for event in game_league["events"]:
                    home_team = event["homeTeam"]["name"]
                    away_team = event["awayTeam"]["name"]
                    status = event["status"]["description"]
                    if status is None:
                        status = "N/A"
                    if league != "mma":
                        home_score = event["homeScore"]["current"]
                        if home_score == "":
                            home_score = "0"
                        away_score = event["awayScore"]["current"]
                        if away_score == "":
                            away_score = "0"
                        title = "[COLORorange]%s %s-%s[/COLOR]: %s vs %s" % (status, home_score, away_score, home_team, away_team)
                    else:
                        title = "[COLORorange]%s[/COLOR]: %s vs %s" % (status, home_team, away_team)
                    icon = event["homeTeam"]["logo"]
                    game_id = event["id"]
                    game_time_str = "%sT%s" % (event["formatedStartDate"], event["startTime"])
                    game_time = datetime(*(time.strptime(game_time_str, "%Y-%m-%dT%H:%M")[:6]))
                    if game_time < today:
                        continue
                    sport = event["sport"]
                    # links_url = "https://sportscentral.io/streams-table/%s/%s?new-ui=1&origin=reddit1.nbabite.com" % (str(game_id), sport)
                    links_url = f"https://scdn.dev/main-assets/{game_id}/{sport}?origin=reddit1.nbabite.com"
                    items.append(JetItem(title=title, icon=icon, starttime=game_time, league=game_league["uniqueName"], links=[JetLink(links_url, links=True)]))
        
        if self.progress_update(progress, "soccer"):
            return items

        # Soccer
        r = requests.get("https://sportscentral.io/new-api/matches?date=" + date_format, headers={"Referer": "https://redditmlbstreams.live", "User_Agent": self.user_agent}, timeout=self.timeout).json()
        for league in r:
            events = league["events"]
            logo = league["logo"]
            league_name = league["name"]
            for event in events:
                status = event["status"]["type"]
                if status != "inprogress": continue
                home_team = event["homeTeam"]["name"]
                home_score = event["homeScore"]["current"]
                away_team = event["awayTeam"]["name"]
                away_score = event["awayScore"]["current"]
                title = "[COLORorange]%s %s-%s[/COLOR]: %s vs %s" % (status.capitalize(), home_score, away_score, home_team, away_team)
                game_id = event["id"]
                game_time = datetime.fromtimestamp(event["startTimestamp"]) + timedelta(hours=7)
                # links_url = "https://sportscentral.io/streams-table/%s/soccer?new-ui=1&origin=mlbstreams.to" % (str(game_id))
                links_url = f"https://scdn.dev/main-assets/{game_id}/soccer?origin=reddit1.nbabite.com"
                items.append(JetItem(title=title, icon=logo, starttime=game_time, league=league_name, links=[JetLink(links_url, links=True)]))
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        return get_streams_table(url.address)
