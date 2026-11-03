import re
from bs4 import BeautifulSoup as bs
from ..models import *
from .._core import fetch_page
from urllib.parse import urljoin, urlparse

class NflVideo(JetExtractor):
    domains = ["nfl-video.com", "nfl-replays.com"]
    name = "NflVideo"

    def is_available(self, url: JetLink) -> bool:
        parsed = urlparse(url.address)
        if parsed.hostname in ("nfl-video.com", "www.nfl-video.com") and (parsed.path.rstrip("/") == "/cfb" or parsed.path.startswith("/cfb/")):
            return False
        return super().is_available(url)

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = f"https://{self.domains[0]}"
        url =  f"{base_url}?page{params['page']}" if params is not None else base_url
        r = fetch_page(url, referer=base_url)
        soup = (bs(r, 'html.parser'))
        matches = soup.find_all(class_='short_item block_elem')
        for match in matches:
            name = match.h3.a.text.replace('Full Game Replay ', '').rstrip(' NHL')
            if self.progress_update(progress, name):
                return items
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
        r = fetch_page(url.address, referer=base_url)
        soup = bs(r, 'html.parser')
        for button in soup.find_all(class_='su-button'):
            link = button['href']
            if link.startswith('//'):
                link = f'https:{link}'
                
            if any(x in link for x in ['nhlgamestoday', 'guidedesgemmes', 'guideanimaux', 'nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors', 'collegegamestoday']):
                r = fetch_page(link, referer=base_url)
                _soup = bs(r, 'html.parser')
                for iframe in _soup.find_all('iframe'):
                    if link := iframe.get('src'):
                        title = link.split('/')[2]
                        links.append(JetLink(link, name=title, resolveurl=True))
            else:
                title = link.split('/')[2]
                links.append(JetLink(link, name=title, resolveurl=True))
        
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            link = iframe['src']
            if link.startswith('//'):
                link = f'https:{link}'
            
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors', 'collegegamestoday']):
                r = fetch_page(link, referer=base_url)
                _soup = bs(r, 'html.parser')
                for iframe in _soup.find_all('iframe'):
                    if link := iframe.get('src'):
                        title = link.split('/')[2]
                        links.append(JetLink(link, name=title, resolveurl=True))
            else:
                title = link.split('/')[2]
                links.append(JetLink(link, name=title, resolveurl=True))
        return links


class CollegeVideo(NflVideo):
    """College football replays on nfl-video.com/cfb/.

    Keep the class here rather than duplicating it in nhlvideo.py. The parent
    NflVideo supplies existing replay-link extraction; this class handles the
    different listing URL, page links and extractor selection.
    """
    domains = ["nfl-video.com"]
    name = "CollegeVideo"
    base_url = "https://nfl-video.com/cfb/"

    def is_available(self, url: JetLink) -> bool:
        """Avoid claiming every NFL page just because CFB shares its host."""
        parsed = urlparse(url.address)
        return (parsed.hostname in ("nfl-video.com", "www.nfl-video.com")
                and (parsed.path.rstrip("/") == "/cfb" or parsed.path.startswith("/cfb/")))

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        try:
            page = max(1, int((params or {}).get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        # The site uses ?page2= (not ?page=2).
        page_url = self.base_url if page == 1 else f"{self.base_url}?page{page}="
        html = fetch_page(page_url, referer=self.base_url)
        if not html:
            return items
        soup = bs(html, "html.parser")
        seen = set()
        for card in soup.select(".short_item.block_elem"):
            anchor = card.select_one("h3 a[href]")
            if not anchor:
                continue
            address = urljoin(page_url, anchor["href"])
            if urlparse(address).hostname not in ("nfl-video.com", "www.nfl-video.com") or address in seen:
                continue
            title = anchor.get_text(" ", strip=True)
            title = re.sub(r"^Full Game Replay\s*[-:]?\s*", "", title, flags=re.I).strip()
            if not title:
                continue
            if self.progress_update(progress, title):
                return items
            seen.add(address)
            image = card.select_one("img")
            image_url = (image.get("data-src") or image.get("data-lazy-src") or image.get("src")) if image else None
            items.append(JetItem(title, links=[JetLink(address, links=True, extractor=self.name)],
                                 icon=urljoin(page_url, image_url) if image_url else ""))

        # Only display another page if the site actually links to it.
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            next_url = urljoin(page_url, href)
            if (urlparse(next_url).hostname in ("nfl-video.com", "www.nfl-video.com")
                    and re.search(r"(?:\?|&)page{}(?:=|&|$)".format(page + 1), urlparse(next_url).query and "?" + urlparse(next_url).query or "")):
                items.append(JetItem(f"[COLORyellow]Page {page + 1}[/COLOR]", links=[],
                                     params={"page": page + 1}))
                break
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        """Resolve replay page buttons/iframes without brittle URL indexing."""
        page_url = url.address
        html = fetch_page(page_url, referer=self.base_url)
        if not html:
            return []
        soup = bs(html, "html.parser")
        links, seen = [], set()

        def add(raw, base=page_url):
            if not raw:
                return
            address = urljoin(base, raw.strip())
            parsed = urlparse(address)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or address in seen:
                return
            seen.add(address)
            links.append(JetLink(address, name=parsed.hostname, resolveurl=True))

        for button in soup.select("a.su-button[href]"):
            target = urljoin(page_url, button["href"])
            if any(host in (urlparse(target).hostname or "") for host in
                   ("nfl-replays", "nfl-video", "basketball-video", "nbaontv", "gamesontvtoday")):
                wrapper_html = fetch_page(target, referer=page_url)
                if wrapper_html:
                    wrapper = bs(wrapper_html, "html.parser")
                    iframe = wrapper.select_one("iframe[src],iframe[data-src]")
                    if iframe:
                        add(iframe.get("data-src") or iframe.get("src"), target)
                        continue
            add(target)

        for iframe in soup.select("iframe[src],iframe[data-src]"):
            add(iframe.get("data-src") or iframe.get("src"))
        return links
