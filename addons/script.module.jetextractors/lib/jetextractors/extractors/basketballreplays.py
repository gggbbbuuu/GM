from ..models import *
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class BasketballReplays(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["basketballreplays.net"]
        self.name = "BasketballReplays"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}?page{params['page'] if params is not None else 1}").text
        soup = BeautifulSoup(r, "html.parser")
        for item in soup.select("div.h_post"):
            a = item.select_one("div.h_post_title > a")
            title = a.text
            href = f"https://{self.domains[0]}" + a.get("href")
            icon = f"https://{self.domains[0]}" + item.select_one("img").get("src")
            items.append(JetItem(title, links=[JetLink(href, links=True)], icon=icon))
        if (next_page := soup.select_one("a.swchItem-next")) is not None:
            page = next_page.get("href").split("/?page")[-1]
            items.append(JetItem(f"Page {page}", links=[], params={"page": page}))
        return items


    def get_links(self, url: JetLink) -> List[JetLink]:
        r = requests.get(url.address).text
        soup = BeautifulSoup(r, "html.parser")
        links = [JetLink(iframe.get("src"), resolveurl=True, name=urlparse(iframe.get("src")).netloc) for iframe in soup.select("iframe")]
        return links
    

class WNBAReplays(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["basketball-video.com/wnba-video"]
        self.name = "WNBA Replays"
    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        page = int(params['page'] if params is not None else 1)
        r = requests.get(f"https://{self.domains[0]}?page{page}").text
        soup = BeautifulSoup(r, "html.parser")
        games = soup.find_all(class_='short_item block_elem')
        for game in games:
            title = game.h3.a.text.replace('Full Game Replay ', '')
            if self.progress_update(progress, title):
                return items
            link = f"https://basketball-video.com{game.a['href']}"
            thumbnail = f"https://basketball-video.com{game.a.img['src']}"
            items.append(JetItem(title, links=[JetLink(link, links=True)], icon=thumbnail))
        items.append(JetItem(f"Page {page+1}", links=[], params={"page": page+1}))
        return items
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        headers = {"User-Agent": self.user_agent, "Referer": url.address}
        r = requests.get(url.address, headers=headers, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        buttons = soup.find_all(class_='su-button')
        for button in buttons:
            link = button['href']
            if link.startswith('//'):
                link = f'https:{link}'
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday']):
                r = requests.get(link, headers=headers, timeout=self.timeout).text
                _soup = BeautifulSoup(r, 'html.parser')
                iframe = _soup.find('iframe')
                if iframe:
                    link = iframe['src']
                else:
                    continue
            link = link.replace('luluvid.com', 'luluvdo.com')
            title = link.split('/')[2]
            links.append(JetLink(link, resolveurl=True, name=title))
        
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            link = iframe['src']
            if link.startswith('//'):
                link = f'https:{link}'
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday']):
                r = requests.get(link, headers=headers, timeout=self.timeout).text
                _soup = BeautifulSoup(r, 'html.parser')
                iframe = _soup.find('iframe')
                if iframe:
                    link = iframe['src']
                else:
                    continue
            link = link.replace('luluvid.com', 'luluvdo.com')
            title = link.split('/')[2]
            links.append(JetLink(link, resolveurl=True, name=title))
        return links
        