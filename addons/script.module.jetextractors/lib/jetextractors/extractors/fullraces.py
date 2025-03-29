import requests
from bs4 import BeautifulSoup as bs

from ..models import *


class FullRaces(JetExtractor):
    domains = ["fullraces.com"]
    name = "Fullraces"

    # def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
    #     items = []
    #     if self.progress_update(progress):
    #         return items
            
    #     base_url = f"https://{self.domains[0]}"
    #     if params:
    #         page = int(params['page'])
    #         url = f'{base_url}/?page{page}'
    #     else:
    #         page = 1
    #         url = base_url
    #     headers = {"User-Agent": self.user_agent, "Referer": base_url}
    #     r = requests.get(url, headers=headers, timeout=10).text
    #     soup = (bs(r, 'html.parser'))
    #     matches = soup.find_all(class_='short_item')
    #     for match in matches:
    #         title = match.h3.a.text
    #         link = f"{base_url}{match.a['href']}"
    #         icon = f"{base_url}{match.a.img['src']}"
    #         items.append(JetItem(title=title, links=[JetLink(link, links=True)], icon=icon))
    #     items.append(JetItem(f'[COLORyellow]Page {page+1}[/COLOR]', links=[], params={'page': page+1}))
    #     return items
    
    # def get_links(self, url: JetLink) -> List[JetLink]:
    #     links = []
    #     title = ''
    #     link = ''
    #     base_url = f"https://{self.domains[0]}"
    #     headers = {"User-Agent": self.user_agent, "Referer": base_url}
    #     r = requests.get(url, headers=headers, timeout=self.timeout).text
    #     soup = bs(r, 'html.parser')
    #     iframes = soup.find_all('iframe')
    #     for iframe in iframes:
    #         link = iframe['src']
    #         if link.startswith('//'):
    #             link = f'https:{link}'
    #         if 'youtube' in link:
    #             yt_id = link.split('/')[-1]
    #             link = f'plugin://plugin.video.youtube/play/?video_id={yt_id}'
    #             title = 'Highlights'
    #         else:
    #             title = link.split('/')[2]
    #         links.append(JetLink(link, name=title, resolveurl=True))
    #     for button in soup.find_all(class_='su-button'):
    #         link = button['href']
    #         if link.startswith('//'):
    #             link = f'https:{link}'
    #         if 'youtube' in link:
    #             yt_id = link.split('/')[-1]
    #             link = f'plugin://plugin.video.youtube/play/?video_id={yt_id}'
    #             title = 'Highlights'
    #         else:
    #             title = link.split('/')[2]
    #         links.append(JetLink(link, name=title, resolveurl=True))
    #     return links
    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        base_url = f"https://{self.domains[0]}"
        
        if params is None:
            
            r = requests.get(base_url, timeout=self.timeout).text
            soup = bs(r, 'html.parser')
            for li in soup.select_one("ul#list_cat").select("li"):
                if li.get("class") is not None:
                    continue
                cat_name = li.text.strip()
                cat_a = li.find('a')
                if cat_a is None or cat_a.get("href") is None:
                    continue
                cat_href = cat_a.get("href")
                href = "/" + "/".join(cat_href.split("/")[3:])
                items.append(JetItem(title=cat_name, links=[], params={"href": href}))
        else:
            category_url = f"{base_url}{params['href']}"
            if 'page' in params:
                category_url += f"?page{params['page']}"
            else:
                category_url += "?page1"
            
            headers = {"User-Agent": self.user_agent, "Referer": category_url}
            r = requests.get(category_url, headers=headers, timeout=self.timeout).text
            
            soup = bs(r, 'html.parser')
            matches = soup.find_all(class_='short_item block_elem')
            
            
            for match in matches:
                name = match.h3.a.text.replace('Full Game Replay ', '').rstrip(' NHL')
                link = f"{base_url}{match.a['href']}"
                icon = f"{base_url}{match.a.img['src']}"
                items.append(JetItem(name, links=[JetLink(link, links=True)], icon=icon))
            current_page = int(params.get("page", 1))
            next_page = current_page + 1
            next_page_url = f"{params['href']}?page={next_page}"
            items.append(JetItem(f"[COLORyellow]Page {next_page}[/COLOR]", links=[], params={"page": next_page, "href": params['href']}))
            
        return items
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        # title = ''
        link = ''
        base_url = f"https://{self.domains[0]}"
        headers = {"User-Agent": self.user_agent, "Referer": base_url}
        r = requests.get(url.address, headers=headers).text
        soup = bs(r, 'html.parser')
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            link = iframe['src']
            if link.startswith('//'):
                link = f'https:{link}'
            title = ''
            title_element = iframe.find_previous()
            while title_element and not title:
                if title_element.name in ['strong', 'h2', 'h1']:
                    title = title_element.text.strip()
                title_element = title_element.find_previous()
            print(f"Extracted title: '{title}' for link: '{link}'")
            if "Condensed" in title:
                title = title.split(';')[-1].strip()+"| "+link.split('/')[2]
            else:
                title = title_element.text.strip()+"  "+link.split('/')[2]
            if 'youtube' in link:
                yt_id = link.split('/')[-1]
                link = f'plugin://plugin.video.youtube/play/?video_id={yt_id}'
                title = title or 'Highlights'
            links.append(JetLink(link, name=title or 'No Title', resolveurl=True))
        button = soup.find(class_='su-button')
        if button:
            link = button['href']
            title = link.split('/')[2]
            links.append(JetLink(link, name=title, resolveurl=True))
        return links
        