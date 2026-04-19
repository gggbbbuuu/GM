from ..models import *
from ..util import m3u8_src
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
        r = requests.get(f"https://{self.domains[0]}/?page={params['page'] if params is not None else 1}").text
        soup = BeautifulSoup(r, "html.parser")
        for item in soup.select("div.h_post"):
            a = item.select_one("div.h_post_title > a")
            if a is None:
                continue
            title = a.text
            href = f"https://{self.domains[0]}" + a.get("href")
            img = item.select_one("img")
            icon = f"https://{self.domains[0]}" + img.get("src") if img else None
            items.append(JetItem(title, links=[JetLink(href, links=True)], icon=icon))
        if (next_page := soup.select_one("a.swchItem-next")) is not None:
            page = next_page.get("href", "").split("/?page")[-1]
            if page:
                items.append(JetItem(f"Page {page}", links=[], params={"page": page}))
        return items


    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        seen = set()
        r = requests.get(url.address, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        
        watch_btn = soup.select_one("a.su-button[href*='nhlgamestoday']")
        if watch_btn:
            redirect_url = watch_btn.get("href")
            if redirect_url:
                r = requests.get(redirect_url, timeout=10).text
                soup = BeautifulSoup(r, "html.parser")
        
        for iframe in soup.select("iframe"):
            src = iframe.get("src")
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                if src in seen:
                    continue
                seen.add(src)
                name = urlparse(src).netloc
                if "ok.ru" in src:
                    name = "ok.ru"
                
                if "vidara.so" in src or "vidara.to" in src:
                    m3u8_link = m3u8_src.scan_page(src, headers={"User-Agent": self.user_agent, "Referer": src})
                    if m3u8_link:
                        m3u8_link.resolveurl = True
                        m3u8_link.name = "vidara.so"
                        links.append(m3u8_link)
                    else:
                        links.append(JetLink(src, resolveurl=True, name=name))
                else:
                    links.append(JetLink(src, resolveurl=True, name=name))
        
        return links
        
class CollegeReplays(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["basketball-video.com/college-basketball"]
        self.name = "CollegeBasketball Replays"
    
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
        paragraphs = soup.find_all('p')
        event_title = None
        for p in paragraphs:
            # If paragraph contains only text, treat as event title
            if p.find('a') is None and p.get_text(strip=True):
                event_title = p.get_text(strip=True)
            # Watch link
            watch_link = p.find('a')
            if watch_link and watch_link.has_attr('href'):
                link = watch_link['href']
                if link.startswith('//'):
                    link = f'https:{link}'
                if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors']):
                    r2 = requests.get(link, headers=headers, timeout=10).text
                    _soup = BeautifulSoup(r2, 'html.parser')
                    iframe = _soup.find('iframe')
                    if iframe:
                        link = iframe['src']
                    else:
                        continue
                link = link.replace('luluvid.com', 'luluvdo.com')
                
                if "vidara.so" in link or "vidara.to" in link:
                    m3u8_link = m3u8_src.scan_page(link, headers={"User-Agent": self.user_agent, "Referer": link})
                    if m3u8_link:
                        m3u8_link.resolveurl = True
                        m3u8_link.name = "vidara.so"
                        links.append(m3u8_link)
                    else:
                        links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
                else:
                    links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
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
        r = requests.get(f"https://{self.domains[0]}/?page={page}").text
        soup = BeautifulSoup(r, "html.parser")
        games = soup.find_all(class_='short_item block_elem')
        for game in games:
            if not game.h3 or not game.h3.a:
                continue
            title = game.h3.a.text.replace('Full Game Replay ', '')
            if self.progress_update(progress, title):
                return items
            if not game.a:
                continue
            link = f"https://basketball-video.com{game.a['href']}"
            thumbnail = f"https://basketball-video.com{game.a.img['src']}" if game.a.img else None
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
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors']):
                r = requests.get(link, headers=headers, timeout=self.timeout).text
                _soup = BeautifulSoup(r, 'html.parser')
                iframe = _soup.find('iframe')
                if iframe:
                    link = iframe['src']
                else:
                    continue
            link = link.replace('luluvid.com', 'luluvdo.com')
            title = link.split('/')[2]
            
            if "vidara.so" in link or "vidara.to" in link:
                m3u8_link = m3u8_src.scan_page(link, headers={"User-Agent": self.user_agent, "Referer": link})
                if m3u8_link:
                    m3u8_link.resolveurl = True
                    m3u8_link.name = "vidara.so"
                    links.append(m3u8_link)
                else:
                    links.append(JetLink(link, resolveurl=True, name=title))
            else:
                links.append(JetLink(link, resolveurl=True, name=title))
        
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            link = iframe['src']
            if link.startswith('//'):
                link = f'https:{link}'
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors']):
                r = requests.get(link, headers=headers, timeout=self.timeout).text
                _soup = BeautifulSoup(r, 'html.parser')
                iframe = _soup.find('iframe')
                if iframe:
                    link = iframe['src']
                else:
                    continue
            link = link.replace('luluvid.com', 'luluvdo.com')
            title = link.split('/')[2]
            
            if "vidara.so" in link or "vidara.to" in link:
                m3u8_link = m3u8_src.scan_page(link, headers={"User-Agent": self.user_agent, "Referer": link})
                if m3u8_link:
                    m3u8_link.resolveurl = True
                    m3u8_link.name = "vidara.so"
                    links.append(m3u8_link)
                else:
                    links.append(JetLink(link, resolveurl=True, name=title))
            else:
                links.append(JetLink(link, resolveurl=True, name=title))
        return links
        