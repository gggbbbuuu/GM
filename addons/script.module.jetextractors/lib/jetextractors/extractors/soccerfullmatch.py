from bs4 import BeautifulSoup as bs
import requests
from ..models import *

class SoccerFullMatch(JetExtractor):
    domains = ["soccerfull.net"]
    name = "SoccerFullMatch"
    
    def __init__(self):
        self.base_url = f"https://{self.domains[0]}"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
        self.headers = {
            'User-Agent': self.user_agent,
            'Referer': self.base_url
        }
        
        
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        page = 1 if params is None else int(params['page'])
        url = f'{self.base_url}/new/{page}'
        response = requests.get(url, headers=self.headers, timeout=10).text
        soup = bs(response, 'html.parser')
        
        matches = soup.find_all(class_='item-movie')
        for match in matches:
            title = match.a['title']
            if self.progress_update(progress, title):
                return items
            link = f"{self.base_url}{match.a['href']}"
            icon = match.find('img')['src']
            league = match.find(class_='code').text
            items.append(JetItem(title, links=[JetLink(link, links=True)], icon=icon, league=league))
        items.append(JetItem("[COLORyellow]Next Page[/COLOR]", links=[], params={"page": page+1}))
        return items
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        response = requests.get(url.address, headers=self.headers, timeout=10).text
        soup = bs(response, 'html.parser')
        for iframe in soup.find_all('iframe'):
           links.append(JetLink(iframe['src'], resolveurl=True))
        test = 'https://dsvplay.com/e/q9rfpn1pl74m'
        links.append(JetLink(test, name='test', resolveurl=True))
        return links
        