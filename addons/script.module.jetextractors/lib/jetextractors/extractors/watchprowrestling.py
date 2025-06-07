import json
from urllib.parse import urlparse, parse_qsl
from base64 import b64decode
import requests
from bs4 import BeautifulSoup as bs
from ..models import *


DEBRID = ['1fichier.com', 'drop.download']
FILTERED = ['Gofile', 'NetU', 'Live']

# TODO: I am dumb
class WatchProWrestling(JetExtractor):
    domains = ["watchprowrestlings.live"]
    name = "WatchProWrestling"
    
    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        ajax = f'https://{self.domains[0]}/wp-admin/admin-ajax.php'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        page = 1 if params is None else int(params['page'])
        text = ''
        for _ in range(0, 4):
            category = 'tonight'
            data = {
                'action': 'load_more_posts',
                'paged': page,
                'category': category
            }
            r = requests.post(ajax, headers=headers, data=data, timeout=10)
            text += r.text
            page += 1
            
        soup = bs(text, 'html.parser')
        for card in soup.find_all(class_='post-card'):
            title = card.img['alt']
            link = card.a['href']
            thumbnail = card.img['src']
            if self.progress_update(progress, title):
                return items
            items.append(JetItem(title=title, links=[JetLink(link, links=True)], icon=thumbnail, params=params))
        
        params = {'page': page}
        items.append(JetItem('[COLOR yellow]Next Page[/COLOR]', links=[], params=params))
        return items
        
        
    def get_links(self, url: JetLink) -> List[JetLink]:
        items = []
        non_debrid = []
        headers = {"User-Agent": self.user_agent, "Referer": f'https://{self.domains[0]}'}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        soup = bs(response.text, 'html.parser')
        matches = soup.find_all(class_='custom-button')
        for match in matches:
            headers['Referer'] = f'https://{self.domains[0]}'
            title = match.text
            link = match['href']
            
            if any(x in title for x in FILTERED) or any(x in link for x in FILTERED):
                continue
                
            if any(x in link for x in DEBRID):
                title = f"{title} - Debrid"
                items.append(JetLink(link, name=title, resolveurl=True))
            
            else:
                if 'fast.store' in link:
                    link = f'{link}|Referer=https://{self.domains[0]}'
                    title = f'{title} - Valid for 3 days from post date.'
                    non_debrid.append(JetLink(link, name=title, direct=True))
                    
                elif 'voe.php' in link:
                    id_ = link.split('=')[-1]
                    link = f'https://voe.sx/e/{id_}'
                    title = f'Voe - {title}'
                    non_debrid.append(JetLink(link, name=title, resolveurl=True))
                
                elif 'dh.php' in link:
                    r = requests.get(link, headers=headers, timeout=self.timeout).text
                    soup = bs(r, 'html.parser')
                    iframe = soup.find('iframe')
                    if iframe:
                        link = iframe.get('src')
                        title = f'Dood - {title}'
                        non_debrid.append(JetLink(link, name=title, resolveurl=True))
                        
                elif 'ok.php' in link:
                    parsed = urlparse(link)
                    variables = dict(parse_qsl(parsed.query))
                    video_id = variables.get('id')
                    link = f'https://ok.ru/videoembed/{video_id}'
                    title = f'OK HD - {title}'
                    non_debrid.append(JetLink(link, name=title, resolveurl=True))
                    
                elif 'dm2.php' in link or 'dm_rep' in link:
                    headers['Referer'] = 'https://www.m2list.com/'
                    parsed = urlparse(link)
                    variables = dict(parse_qsl(parsed.query))
                    mirror = variables.get('id')
                    mainid = variables.get('mainid')
                    if mainid is not None:
                        video_id = ''
                        response = requests.get(f'https://www.m2list.com/2023update/db/{mainid}_cache.php', headers=headers, timeout=10).text
                        match = re.search(r'var\s+json\s*=\s*"([^"]+)"', response)
                        if match:
                            json_encoded = match.group(1)
                            json_decoded = b64decode(json_encoded).decode('utf-8')
                            video_id = json.loads(json_decoded)[mirror]
                            link = f'https://www.dailymotion.com/video/{video_id}'
                            title = f'Daily Motion - {title}'
                            non_debrid.append(JetLink(link, name=title, resolveurl=True))
                            
        items.extend(non_debrid)
        return items
