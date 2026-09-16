from bs4 import BeautifulSoup as bs
from ..models import *
from .._core import fetch_page, find_iframes, find_m3u8
from ..util.stream_proxy import get_stream_proxy
import re

class SoccerFullMatch(JetExtractor):
    domains = ["soccerfull.net"]
    name = "SoccerFullMatch"

    def __init__(self):
        self.base_url = f"https://{self.domains[0]}"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        self.headers = {
            'User-Agent': self.user_agent,
            'Referer': self.base_url
        }
        self._proxy = None

    def _get_proxy(self):
        if self._proxy is None:
            self._proxy = get_stream_proxy(
                "soccerfull",
                self.headers,
                options={
                    "strip_png": False,
                    "prefetch_segments": True,
                    "upstream_keep_alive": True,
                    "keep_alive": False,
                },
            )
        return self._proxy

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        page = 1 if params is None else int(params['page'])
        url = f'{self.base_url}/new/{page}'
        response = fetch_page(url, referer=self.base_url)
        soup = bs(response, 'html.parser')

        matches = soup.find_all(class_='item-movie')
        for match in matches:
            title = match.a['title']
            if self.progress_update(progress, title):
                return items
            link = f"{self.base_url}{match.a['href']}"
            icon = match.find('img')['src']
            if icon.startswith('/'):
                icon = f"{self.base_url}{icon}"
            league = match.find(class_='code').text
            items.append(JetItem(title, links=[JetLink(link, links=True)], icon=icon, league=league))
        items.append(JetItem("[COLORyellow]Next Page[/COLOR]", links=[], params={"page": page+1}))
        return items

    def _resolve_play_url(self, play_url: str, name: Optional[str] = None, depth: int = 0) -> Optional[JetLink]:
        try:
            play_response = fetch_page(play_url, referer=self.base_url)
            m3u8 = find_m3u8(play_response, self.base_url)
            if m3u8:
                try:
                    proxy = self._get_proxy()
                    proxy_url = proxy.get_proxy_url(m3u8, self.headers)
                    return JetLink(
                        proxy_url,
                        name=name,
                        headers=self.headers,
                        inputstream=JetInputstreamFFmpegDirect.default()
                    )
                except Exception:
                    pass
                return JetLink(
                    m3u8,
                    name=name,
                    headers=self.headers,
                    inputstream=JetInputstreamAdaptive.hls()
                )
            iframes = find_iframes(play_response, play_url)
            for iframe_url in iframes:
                if self.base_url in iframe_url:
                    if depth < 5:
                        return self._resolve_play_url(iframe_url, name, depth + 1)
                else:
                    return JetLink(iframe_url, resolveurl=True, name=name)
        except Exception:
            pass
        return None

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        response = fetch_page(url.address, referer=self.base_url)
        soup = bs(response, 'html.parser')

        servers = soup.find_all('a', class_='video-server')
        for server in servers:
            href = server.get('href', '')
            name = server.text.strip()
            sid_match = re.search(r'sid=(\d+)', href)
            if sid_match:
                play_url = f'{self.base_url}/play/{sid_match.group(1)}'
                link = self._resolve_play_url(play_url, name)
                if link:
                    links.append(link)

        if not links:
            iframes = find_iframes(response, url.address)
            for iframe_url in iframes:
                if self.base_url in iframe_url:
                    link = self._resolve_play_url(iframe_url)
                    if link:
                        links.append(link)
                else:
                    links.append(JetLink(iframe_url, resolveurl=True))

        return links
