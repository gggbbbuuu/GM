import requests
from bs4 import BeautifulSoup as bs
from ..models import *

class FullFightReplays(JetExtractor):
    domains = ["fullfightreplays.com"]
    name = "FullFightReplays"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = f"https://{self.domains[0]}"
        url =  f"{base_url}?page{params['page']}" if params is not None else base_url
        headers = {"User-Agent": self.user_agent, "Referer": base_url}
        r = requests.get(url, headers=headers, timeout=self.timeout).text
        soup = (bs(r, 'html.parser'))
        matches = soup.find_all(class_='short_item block_elem')
        for match in matches:
            name = match.h3.a.text.replace('Full Game Replay ', '').rstrip(' NHL')
            if self.progress_update(progress, name):
                return items
            xbmc.sleep(50)
            link = f"{base_url}{match.a['href']}"
            icon = f"{base_url}{match.a.img['src']}"
            items.append(JetItem(name, links=[JetLink(link, links=True)], icon=icon))

        if params is not None:
            next_page = int(params['page']) + 1
        else:
            next_page = 2
        items.append(JetItem(f"[COLORyellow]Page {next_page}[/COLOR]", links=[], params={"page": next_page}))
        return items
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        base_url = f"https://{urlparse(url.address).netloc}/"
        headers = {"User-Agent": self.user_agent, "Referer": base_url}
        r = requests.get(url.address, headers=headers, timeout=self.timeout).text
        soup = bs(r, 'html.parser')
        for button in soup.find_all(class_='su-button'):
            link = button['href']
            if link.startswith('//'):
                link = f'https:{link}'
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video']):
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
        return links
        