# import requests, re, json, time
# from datetime import datetime, timedelta, timezone
# from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote
# from ..models import *

# class Weakspell(JetExtractor):
#     def __init__(self) -> None:
#         self.name = "Weakspell/LiveOnScore"
#         self.short_name = "WS"
#         self.domains = ["weakspell.to"]

    
#     def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
#         items = []
#         if self.progress_init(progress, items):
#             return items
        
#         r = requests.get(f"http://{self.domains[0]}", timeout=self.timeout).text
#         soup = BeautifulSoup(r, "html.parser")
#         categories = soup.select("ul.navbar-nav > li > a")
#         for category in categories:
#             if self.progress_update(progress, category.text):
#                 return items
            
#             try:
#                 league = category.text.replace(" Streams", "")
#                 href = category.get("href")
#                 r_category = requests.get(href, timeout=self.timeout).text
#                 soup = BeautifulSoup(r_category, "html.parser")
#                 for game in soup.find_all("a", class_="btn-block"):
#                     try:
#                         url = game.get("href")
#                         icon = game.find("img").get("src")
#                         title = game.find("h4").text.strip()
#                         time_str = game.find("p").text.strip()
#                         utc_time = None
#                         if time_str != "":
#                             if "LIVE" in time_str:
#                                 utc_time = datetime.now(timezone.utc)
#                             else:
#                                 utc_time = datetime(*(time.strptime(time_str, "%a %d %b %Y %I:%M %p EST")[:6])) + timedelta(hours=5)
#                         items.append(JetItem(title=title, links=[JetLink(address=url)], icon=icon, league=league, starttime=utc_time))
#                     except Exception as e:
#                         continue
#             except:
#                 continue
#         return items
    
    
#     def get_link(self, url: JetLink) -> JetLink:
#         base_url = "http://" + urlparse(url.address).netloc
#         r_game = requests.get(url.address).text
#         re_vidgstream = re.compile(r'var vidgstream = "(.+?)";').findall(r_game)[0]
#         if base_url == "http://liveonscore.tv":
#             re_gethlsUrl = re.compile(r'gethlsUrl\(vidgstream, (.+?), (.+?)\);').findall(r_game)[0]
#             r_hls = requests.get(base_url + "/gethls.php?idgstream=%s&serverid=%s&cid=%s" % (quote(re_vidgstream, safe=""), re_gethlsUrl[0], re_gethlsUrl[1]), headers={"User-Agent": self.user_agent, "Referer": url.address, "X-Requested-With": "XMLHttpRequest"}).text
#         else:
#             r_hls = requests.get(base_url + "/gethls.php?idgstream=%s" % quote(re_vidgstream, safe=""), headers={"User-Agent": self.user_agent, "Referer": url.address, "X-Requested-With": "XMLHttpRequest"}).text
#         json_hls = json.loads(r_hls)
#         m3u8 = json_hls["rawUrl"]
#         if m3u8 is None:
#             raise "no link found"
#         else:
#             m3u8 = JetLink(address=m3u8.replace(".m3u8", ".m3u8?&Connection=keep-alive"), headers={"Referer": url.address})
#         return m3u8

import requests,json
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes
from ..icons import icons
import xbmc
import os

#######  NEED FIXING  ########
class Weakspell(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["methstreams.to"]
        self.name = "Weakspell/LiveOnScore"
        self.short_name = "CS"
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, "html.parser")
        
        # for game_area in soup.select("div.col-8"):
        #     game_titles = [title.text.strip() for title in game_area.select("p")]
        #     hrefs = [link.get("href") for link in game_area.select("a")]
        #     sport = [title.text.strip() for title in game_area.select("h5")]
        #     for title,sport, href in zip(game_titles,sport, hrefs):
        #         items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None, league=sport.upper(), title=title, links=[JetLink(href)]))
        # return items
        # for extra in soup.select("div.card"):
        #     game_titles = [title.text.strip() for title in extra.select("p")]
        #     hrefs = [link.get("href") for link in extra.select("a")]
        #     sport = [title.text.strip() for title in extra.select("h5")]
        #     thumb = [icon.get("src") for icon in extra.select("img")]
        #     for title,sport, href,thumb in zip(game_titles,sport, hrefs,thumb):
        #         items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None, league=sport.upper(), title=title, links=[JetLink(href)]))
        # return items
    
        for extra in soup.select("div.col-xs-12"):
            game_items = extra.select("li.styled-list-item")
            for item in game_items:
                title = item.select_one("span.title_name").text.strip()
                href = item.find("a")["href"]
                sport = item.select_one("span.cat-name").text.strip()
                items.append(JetItem(icon=icons[sport.lower()] if sport.lower() in icons else None, league=sport.upper(), title=title, links=[JetLink(href)]))
        return items
    
    def get_link(self, url: JetLink) -> JetLink:
        base_url = "http://" + urlparse(url.address).netloc
        r_game = requests.get(url.address).text
        re_vidgstream = re.compile(r'var vidgstream = "(.+?)";').findall(r_game)[0]
        r_hls = requests.get(base_url + "/gethls.php?idgstream=%s" % quote(re_vidgstream, safe=""), headers={"User-Agent": self.user_agent, "Referer": url.address, "X-Requested-With": "XMLHttpRequest"}).text
        json_hls = json.loads(r_hls)
        m3u8 = json_hls["rawUrl"]
        if m3u8 is None:
            raise "no link found"
        else:
            m3u8 = JetLink(address=m3u8.replace(".m3u8", ".m3u8?&Connection=keep-alive"), headers={"Referer": url.address})
        return m3u8

    