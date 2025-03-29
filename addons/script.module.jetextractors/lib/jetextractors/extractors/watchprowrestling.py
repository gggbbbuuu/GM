import requests
from bs4 import BeautifulSoup as bs
from ..models import *


DEBRID = ['1fichier.com', 'drop.download']
FILTERED = ['Gofile', 'NetU', 'Full', 'Part', 'Live', 'Prelims', 'Main']


# TODO: whoever made this is dumb
class WatchProWrestling(JetExtractor):
    domains = ["watchprowrestling.co"]
    name = "WatchProWrestling"
    
    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_update(progress):
            return items
        if params is not None:
            url = params['url']
        else:
            url = f'https://{self.domains[0]}'
        headers = {"User-Agent": self.user_agent, "Referer": f'https://{self.domains[0]}'}
        r = requests.get(url, headers=headers, timeout=self.timeout).text
        soup = bs(r, 'html.parser')
        vids = soup.find_all(class_='post-card')
        for vid in vids:
            title = vid.a.img['alt'].replace('Watch ', '')
            link = vid.a['href']
            thumbnail = vid.a.img['src']
            items.append(JetItem(title=title, links=[JetLink(link, links=True)], icon=thumbnail))
        pagination = soup.find(class_='next page-numbers')
        if pagination:
            next_page = pagination['href']
            items.append(JetItem('[COLORyellow]Next Page[/COLOR]', links=[], params={'url': next_page}))
        return items
        
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        items = []
        non_debrid = []
        headers = {"User-Agent": self.user_agent, "Referer": f'https://{self.domains[0]}'}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        soup = bs(response.text, 'html.parser')
        matches = soup.find_all(class_='custom-button')
        for match in matches:
            title = match.text
            link = match['href']
            if any(x in title for x in FILTERED):
                if 'dh.php' not in link and 'voe.php' not in link:
                    continue
            if title in ('Raw Talk', 'Pre Show'):
                if 'dh.php' not in link and 'voe.php' not in link:
                    continue
            if any(x in link for x in DEBRID):
                title = f"{title} [B][COLOR green]***Debrid***[/COLOR][/B]"
                items.append(JetLink(link, name=title, resolveurl=True))
            else:
                if 'mfast.store' in link:
                    link = f'{link}|Referer=https://{self.domains[0]}/'
                    non_debrid.append(JetLink(link, name=title, direct=True))
                elif 'voe.php' in link:
                    id_ = link.split('=')[-1]
                    link = f'https://voe.sx/e/{id_}'
                    non_debrid.append(JetLink(link, name=title, resolveurl=True))
                elif 'dh.php' in link:
                    r = requests.get(link, headers=headers, timeout=self.timeout).text
                    soup = bs(r, 'html.parser')
                    iframe = soup.find('iframe')
                    if iframe:
                        link = iframe.get('src')
                        non_debrid.append(JetLink(link, name=title, resolveurl=True))
        items.extend(non_debrid)
        return items
        