
import requests, re
from datetime import datetime
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..models import *

class SportyBite(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["sons-stream.com"]
        self.name = "SportyBite"
        self.league_dict = {
            7: "UEFA Champions League",
            8: "Europa League",
            9: "F1",
            10: "NBA",
            13: "Premier League",
            20: "WWE",
            29: "NFL",
            34: "MLB",
            46: "NHL",
            78: "Bundesliga",
            79: "La Liga"
        }

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")

        current_date = datetime.now()
        for game in soup.select("tr.cell-color"):
            
            date_row = game.find_previous_sibling("tr", class_="date-row")
            if date_row:
                date = date_row.get_text(strip=True)
            else:
                continue

            cells = game.select("td")
            time = cells[0].text.strip()
            hour = int(time[0])
            minute = int(time[1])
            utc_time = datetime.now().replace(hour=hour, minute=minute) + timedelta(hours=17)
            icon = cells[1].select_one("img").get("src")
            league_id = int(icon.split("/")[-1].split(".")[0])
            title = cells[2].text.split("Watch")[0].strip()
            
            
            links = []
            for cell in cells[3:6]:
                if cell.text:
                    links.append(JetLink(f"https://{self.domains[0]}/tvon.php?hd={cell.text.strip()}"))
            items.append(JetItem(title, league=self.league_dict.get(league_id, None), icon=icon, links=links))

        for channel in soup.select("div.channels"):
            name = channel.text.strip()
            href = channel.find("a").get("href")
            items.append(JetItem(name, links=[JetLink(href)]))

        return items


    def get_link(self, url: JetLink) -> JetLink:
        if "watch.php" in url.address:
            stream_id = re.findall(r"stream_id=(.+?)", url.address)[0]
            url.headers["Referer"] = url.address
            url.address = f"https://{self.domains[0]}/tvon.php?hd={stream_id}"
        r = requests.get(url.address).text
        fid = re.findall(r'fid="(.+?)"', r)[0]
        # embed_url = "https://anarchy-stream.com/dhonka3.php?player=desktop&live=" + fid
        embed_url = "https://processbigger.com/maestrohd1.php?player=desktop&live=" + fid
        r_embed = requests.get(embed_url, headers={"Referer": url.address}).text
        m3u8 = "".join(eval(re.findall(r"return\((\[.+?\])", r_embed)[0])).replace("\\", "").replace("////", "//")
        
        return JetLink(m3u8, headers={"Referer": embed_url, "User-Agent": self.user_agent})
