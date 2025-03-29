import requests, re
from bs4 import BeautifulSoup
from ..models import *
from ..util import hunter, m3u8_src

class GiveMeReddit(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["givemeredditstreams.xyz", "givemereddit.eu","official.givemeredditstream.cc","givemenbastreams.com", "givemenflstreams.com"]
        self.name = "Give Me"

#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        for league in soup.select("a.nav-link")[1:]:
            if self.progress_update(progress):
                return items
            
            league_name = league.text
            r_league = requests.get(f"https://{self.domains[0]}{league.get('href')}").text
            soup_league = BeautifulSoup(r_league, "html.parser")
            for game in soup_league.select("a.matches"):
                href = game.get("href")
                if href.startswith("/"):
                    href = f"https://{self.domains[0]}" + href
                title = game.get("aria-label")
                if title == None:
                    if league_name == "MLB":
                        teams = game.select("span.team-name")
                        title = f"{teams[0].text} vs {teams[1].text}"
                    else:
                        title = game.text.strip()
                        print(title)
                icon = game.select_one("img")
                if icon != None:
                    icon = icon.get("src")
                if self.progress_update(progress, title):
                        return items
                xbmc.sleep(50)
                
                items.append(JetItem(title, links=[JetLink(href)], league=league_name, icon=icon))
        return items


    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        re_iframe = re.findall(r'iframe class=\"embed-responsive-item\" src=\"(.+?)\"', r)
        if len(re_iframe) != 0:
            r = requests.get(re_iframe[0], headers={"User-Agent": self.user_agent, "Referer": url.address}).text
        re_hunter = re.findall(r'decodeURIComponent\(escape\(r\)\)}\("(.+?)",(.+?),"(.+?)",(.+?),(.+?),(.+?)\)', r)[0]
        deobfus = hunter.hunter(re_hunter[0], int(re_hunter[1]), re_hunter[2], int(re_hunter[3]), int(re_hunter[4]), int(re_hunter[5]))
        m3u8 = m3u8_src.scan_page(url.address, deobfus)
        m3u8.headers["User-Agent"] = self.user_agent
        if len(re_iframe) != 0:
            m3u8.headers["Referer"] = re_iframe[0]
        return m3u8