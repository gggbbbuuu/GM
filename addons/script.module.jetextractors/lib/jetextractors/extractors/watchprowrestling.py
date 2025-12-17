import json
from urllib.parse import urlparse, parse_qsl
from base64 import b64decode
import requests
from bs4 import BeautifulSoup as bs
from ..models import *


DEBRID = ['1fichier.com', 'drop.download']
FILTERED = ['Gofile', 'NetU', 'Live', 'PVP']

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
            title = card.img['alt'].lstrip('Watch ')
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
        response = requests.get(url.address, headers=headers, timeout=10)
        soup = bs(response.text, 'html.parser')
        
        for p in soup.find_all('p'):
            hoster = ''
            title = ''
            button = p.find(class_='custom-button')
            if button:
                if p.span:
                    hoster = p.span.strong.text
                    for a in p.find_all('a'):
                        desc = a.text
                        link = a['href']
                        title = f'{hoster} - {desc}'.replace('Other Hosts - ', '')
                        if any(x in title for x in FILTERED) or any(x in link for x in FILTERED):
                            continue
                            
                        items.append(JetLink(f'https://{self.domains[0]}', name=title, params={'link': link}))
                else:
                    for a in p.find_all('a'):
                        link = a['href']
                        title = a.text.replace('Other Hosts - ', '')
                        if any(x in title for x in FILTERED) or any(x in link for x in FILTERED):
                            continue
                            
                        if title in ('1fichier', 'Dropapk'):
                            title += ' - Debrid'
                        
                        items.append(JetLink(f'https://{self.domains[0]}', name=title, params={'link': link}))
        
        return items
        
        
    def get_link(self, url: JetLink) -> JetLink:
        headers = {"User-Agent": self.user_agent, "Referer": f'https://{self.domains[0]}'}
        link = url.params['link']
        parsed = urlparse(link)
        query = dict(parse_qsl(parsed.query))
        if not query:
            return JetLink(link, resolveurl=True)
        
        _type = query.get('type')
        _id = query.get('id')
        ids = query.get('ids')
        main_id = query.get('mainid')
        print(_type)
        url2 = f'https://www.m2list.com/2023update/db/{main_id}_cache.php'
        
        if _type == 'voe':
            return JetLink(f'https://voe.sx/e/{_id}', resolveurl=True)
        
        elif _type == 'pvp':
            dm_id = ''
            headers['Referer'] = headers['Origin'] = 'https://www.m2list.com'
            response = requests.get(url2, headers=headers, timeout=10)
            match = re.search(r'var\s+json="([^"]+)"', response.text)
            if not match:
                return
            value = match.group(1)
            dm_id = json.loads(b64decode(value).decode())[_id]
            if _id.startswith('dm'):
                return JetLink(f'https://www.dailymotion.com/video/{dm_id}', resolveurl=True)
            elif _id.startswith('tube'):
                return JetLink(f'https://android-database1.firebase-api.com/dvr1/{dm_id}.m3u8|Referer=https://www.linux-developers.top/&Origin=https://www.linux-developers.top/&User-Agent={self.user_agent}', direct=True)
                
        elif _type == 'go':
            return JetLink(f'{b64decode(ids).decode()}|Referer=https://{self.domains[0]}')
        
        elif _type == 'dh':
            return JetLink(f'https://dood.watch/e/{_id}', resolveurl=True)
        
        elif _type == 'ok':
            return JetLink(f'https://ok.ru/videoembed/{_id}', resolveurl=True)
