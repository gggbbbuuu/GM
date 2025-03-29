# Whoever wrote this: do NOT call xbmc or resolveurl functions in Jetextractors
from bs4 import BeautifulSoup as bs
from requests.sessions import Session
from ..models import *

class FullReplays(JetExtractor):
    domains = ["www.fullreplays.com"]
    name = "FullReplays"
    
    def __init__(self):
        self.base_url = f"https://{self.domains[0]}"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
        self.headers = {
            'User-Agent': self.user_agent,
            'Referer': self.base_url
        }
        self.session = Session()
        self.session.headers = self.headers

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        if params is None:
            page = self.base_url
        else:
            page = params["page"]
        response = self.session.get(page).text
        soup = bs(response, 'html.parser')
        
        matches = soup.find_all(class_='row')
        for match in matches:
            articles = match.find_all('article')
            for article in articles:
                if article is None:
                    continue
                title = article.h2.text
                if self.progress_update(progress, title):
                    return items
                link = article.a['href']
                thumbnail = article.a.img['src']
                items.append(JetItem(title, links=[JetLink(link, links=True)], icon=thumbnail))
            
        pagination = soup.find(class_='next page-numbers')
        if pagination:
            next_page = pagination['href']
            items.append(JetItem("[COLORyellow]Next Page[/COLOR]", links=[], params={"page": next_page}))
        return items
    
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        response = self.session.get(url.address).text
        soup = bs(response, 'html.parser')
        for source in soup.find_all(class_='frc-vid-sources-list'):
            buttons = source.find_all(class_='vlog-button')
            for button in buttons:
                if button.get('data-sc') is not None:
                    link = button['data-sc']
                else:
                    print(button.text)
                    link = button['href']
                host = urlparse(link).netloc
                title = f'{button.text.strip()} - {host}'
                links.append(JetLink(link, name=title, resolveurl=True))
        return links
        