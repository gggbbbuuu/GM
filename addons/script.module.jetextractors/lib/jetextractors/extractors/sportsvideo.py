import requests, re
from bs4 import BeautifulSoup as bs
from ..models import *


class SportsVideo(JetExtractor):
    domains = ["nfl-replays.com", "mlblive.net", "rugby24.net", "fullfightreplays.com"]
    name = "SportsVideo"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        if params is None:
            items.append(JetItem(title="NFL", links=[], params={"league": "0"}))
            items.append(JetItem(title="MLB", links=[], params={"league": "1"}))
            items.append(JetItem(title="Rugby", links=[], params={"league": "2"}))
            items.append(JetItem(title="MMA", links=[], params={"league": "3"}))            
        else:
            league = int(params["league"])
            domain = self.domains[league]
            base_url = f"https://{domain}"

            if "href" not in params:
                r = requests.get(base_url, timeout=self.timeout).text
                soup = bs(r, "html.parser")
                for li in soup.select_one("ul#list_cat").select("li"):
                    if li.get("class") != None:
                        continue
                    cat_name = li.text.strip()
                    if self.progress_update(progress, cat_name):
                        return items
                    xbmc.sleep(50)
                    cat_a = li.next
                    if cat_a.get("rel") != None:
                        continue
                    cat_href = cat_a.get("href")
                    if cat_href == None:
                        continue
                    href = "/" + "/".join(cat_href.split("/")[3:])
                    items.append(JetItem(title=cat_name, links=[], params={"league": league, "href": href}))
            else:
                url = base_url + params["href"]
                headers = {"User-Agent": self.user_agent, "Referer": base_url}
                r = requests.get(url, headers=headers, verify="basketball" not in domain, timeout=self.timeout).text
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
                next_page_btn = soup.select("a.swchItem")
                if len(next_page_btn) > 0 and next_page_btn[-1].text == "»":
                    href = next_page_btn[-1].get('href')
                    if not href.startswith("/"):
                        href = params["href"] + href
                    page = int(re.findall(r"spages\('(.+?)'", next_page_btn[-1].get('onclick'))[0])
                    items.append(JetItem(f"[COLORyellow]Page {page}[/COLOR]", links=[], params={"league": league, "page": page, "href": href}))
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
        