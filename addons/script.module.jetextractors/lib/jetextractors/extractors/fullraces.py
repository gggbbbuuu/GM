from bs4 import BeautifulSoup as bs

from ..models import *
from .._core import fetch_page, _BROWSER_UA
from ..tools import debug_log
from ..util.stream_proxy import get_stream_proxy
from .basketballreplays import get_dailymotion_proxy


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
            
            r = fetch_page(base_url)
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
            
            r = fetch_page(category_url, referer=category_url)
            
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
        base_url = f"https://{self.domains[0]}"
        r = fetch_page(url.address, referer=base_url)
        soup = bs(r, 'html.parser')

        for iframe in soup.find_all('iframe'):
            link = iframe.get('src', '')
            if not link:
                continue
            if link.startswith('//'):
                link = f'https:{link}'
            title = ''
            title_element = iframe.find_previous()
            while title_element and not title:
                if title_element.name in ['strong', 'h2', 'h1']:
                    title = title_element.text.strip()
                title_element = title_element.find_previous()

            if 'youtube' in link:
                yt_id = link.split('/')[-1]
                link = f'plugin://plugin.video.youtube/play/?video_id={yt_id}'
                title = title or 'Highlights'
                links.append(JetLink(link, name=title, resolveurl=True))
            elif 'dailymotion' in link:
                dm_link = self._resolve_dailymotion(link, title or 'No Title')
                if dm_link:
                    links.append(dm_link)
                else:
                    links.append(JetLink(link, name=title or 'No Title', resolveurl=True))
            else:
                links.append(JetLink(link, name=title or 'No Title', resolveurl=True))

        for button in soup.find_all(class_='su-button'):
            link = button.get('href', '')
            if not link:
                continue
            if link.startswith('//'):
                link = f'https:{link}'
            title = link.split('/')[2]

            if 'youtube' in link:
                yt_id = link.split('/')[-1]
                link = f'plugin://plugin.video.youtube/play/?video_id={yt_id}'
                links.append(JetLink(link, name='Highlights', resolveurl=True))
            elif 'dailymotion' in link:
                dm_link = self._resolve_dailymotion(link, title)
                if dm_link:
                    links.append(dm_link)
                else:
                    links.append(JetLink(link, name=title, resolveurl=True))
            else:
                links.append(JetLink(link, name=title, resolveurl=True))

        return links

    def _resolve_dailymotion(self, dm_url: str, title: str) -> Optional[JetLink]:
        """Resolve a DailyMotion embed/player URL to a proxied HLS stream URL.

        Uses a cookie-based approach: warmup geo.dailymotion.com, visit embed
        page for cookies, call metadata API, then use the StreamProxy with
        use_urllib=True to fetch the CDN manifest (avoids CDN 403 by using
        urllib's TLS fingerprint and skipping Icy-MetaData header).
        """
        try:
            import requests
            import re
            import time
            import uuid

            match = re.search(r'[/.]video/([a-z0-9]+)|video=([a-z0-9]+)', dm_url)
            if not match:
                debug_log(f"[DM] No video ID match in: {dm_url}", xbmc.LOGWARNING)
                return None
            vid = match.group(1) or match.group(2)
            debug_log(f"[DM] Extracted video ID: {vid}", xbmc.LOGINFO)

            session = requests.Session()
            browser_headers = {
                'User-Agent': _BROWSER_UA,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
                'Origin': 'https://geo.dailymotion.com',
                'Referer': 'https://geo.dailymotion.com/',
            }
            session.headers.update(browser_headers)
            session.cookies.set('ff', 'on')

            try:
                session.get('https://geo.dailymotion.com/', timeout=10)
            except Exception as e:
                debug_log(f"[DM] Warmup geo.dailymotion.com network error: {type(e).__name__}: {e}", xbmc.LOGWARNING)

            try:
                session.get(f'https://www.dailymotion.com/embed/video/{vid}', timeout=10)
            except Exception as e:
                debug_log(f"[DM] Embed page network error: {type(e).__name__}: {e}", xbmc.LOGWARNING)

            dm_ts = str(int(time.time()))
            v1st_cookie = session.cookies.get('v1st', '')
            params = {
                'embedder': 'https://www.dailymotion.com',
                'locale': 'en-GB',
                'dmV1st': v1st_cookie,
                'dmTs': dm_ts,
                'is_native_app': '0',
                'geo': '1',
                'player-id': 'web',
                'client_type': 'website',
                'dmViewId': str(uuid.uuid4()),
                'video': vid,
            }
            meta_url = f'https://www.dailymotion.com/player/metadata/video/{vid}'
            r = session.get(meta_url, params=params, timeout=10)
            if r.status_code != 200:
                debug_log(f"[DM] Metadata API failed: {r.status_code}", xbmc.LOGWARNING)
                return None
            data = r.json()

            qualities = data.get("qualities", {})
            auto = qualities.get("auto", [])
            if not auto or "url" not in auto[0] or ".m3u8" not in auto[0]["url"]:
                debug_log(f"[DM] No valid auto m3u8 URL. auto[0] = {auto[0] if auto else 'EMPTY'}", xbmc.LOGWARNING)
                return None
            master_url = auto[0]["url"]
            debug_log(f"[DM] Master URL: {master_url[:200]}", xbmc.LOGINFO)

            cookies = session.cookies.get_dict()
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            dm_headers = {
                'User-Agent': _BROWSER_UA,
                'Referer': 'https://www.dailymotion.com/',
                'Origin': 'https://www.dailymotion.com',
                'Cookie': cookie_str,
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'x-cache-internal': 'true',
                'x-cache-max-age': '-1',
            }
            debug_log(f"[DM] Fetching manifest bytes with urllib: {len(cookies)} cookies", xbmc.LOGINFO)
            import urllib.request as urllib_request
            import ssl
            req = urllib_request.Request(master_url)
            for k, v in dm_headers.items():
                req.add_header(k, v)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            opener = urllib_request.build_opener(urllib_request.HTTPSHandler(context=ctx))
            try:
                with opener.open(req, timeout=10) as resp:
                    manifest_bytes = resp.read()
                debug_log(f"[DM] Manifest bytes length: {len(manifest_bytes)}", xbmc.LOG_INFO)
                debug_log(f"[DM] Manifest content preview: {manifest_bytes[:500]}", xbmc.LOGDEBUG)
            except Exception as e:
                debug_log(f"[DM] Manifest fetch failed with urllib: {type(e).__name__}: {e}", xbmc.LOGWARNING)
                return None

            debug_log(f"[DM] Caching manifest bytes with URL rewrite", xbmc.LOG_INFO)
            proxy_url, _ = get_dailymotion_proxy(manifest_bytes, dm_headers, master_url=master_url)
            debug_log(f"[FullRaces] DailyMotion proxied: {dm_url} -> {proxy_url}", xbmc.LOGINFO)
            return JetLink(proxy_url, name=title, headers=dm_headers, inputstream=JetInputstreamFFmpegDirect.default())
        except Exception as e:
            debug_log(f"[DM] _resolve_dailymotion error: {type(e).__name__}: {e}", xbmc.LOGWARNING)
            return None
