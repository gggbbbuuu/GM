import requests
from bs4 import BeautifulSoup as bs
import xbmc
from ..models import *


class NhlVideo(JetExtractor):
    domains = ["nhlfullgame.com"]
    name = "NhlVideo"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        base_url = f"https://{self.domains[0]}"
        url = base_url if params is None else params['page']
        headers = {"User-Agent": self.user_agent, "Referer": url}
        r = requests.get(url, headers=headers, timeout=self.timeout).text
        soup = (bs(r, 'html.parser'))
        matches = soup.find_all(class_='portfolio-thumb ph-link')
        for match in matches:
            title = match.img['title'].rstrip(' NHL Full Game Replay')
            if self.progress_update(progress, title):
                return items
            xbmc.sleep(100)
            link = f"{base_url}{match.a['href']}"
            thumbnail = f"{base_url}{match.img['src']}"
            items.append(JetItem(title, links=[JetLink(link, links=True)], icon=thumbnail))
        next_page = soup.find(class_='swchItem swchItem-next')
        if next_page:
            params = {"page": f"{base_url}{next_page['href']}"}
        items.append(JetItem("[COLORyellow]Next Page[/COLOR]", links=[], params=params))
        return items
    
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        base_url = f"https://{urlparse(url.address).netloc}/"
        headers = {"User-Agent": self.user_agent, "Referer": base_url}
        r = requests.get(url.address, headers=headers, timeout=self.timeout).text
        soup = bs(r, 'html.parser')
        for button in soup.find_all(class_='su-button'):
            link = button['href']
            if 'nfl-replays' in link:
                r = requests.get(link, headers=headers, timeout=self.timeout).text
                _soup = bs(r, 'html.parser')
                iframe = _soup.find('iframe')
                if iframe:
                    link = iframe['src']
                else:
                    continue
            if link.startswith('//'):
                link = f'https:{link}'
            title = link.split('/')[2]
            links.append(JetLink(link, name=title, resolveurl=True))
        
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            link = iframe['src']
            if link.startswith('//'):
                link = f'https:{link}'
            title = link.split('/')[2]
            links.append(JetLink(link, name=title, resolveurl=True))
        links.reverse()
        return links