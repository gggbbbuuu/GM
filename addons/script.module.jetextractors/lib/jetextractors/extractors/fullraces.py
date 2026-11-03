import xbmc
from bs4 import BeautifulSoup as bs

from ..models import *
from .._core import fetch_page, _BROWSER_UA
from ..tools import debug_log
from ..util.stream_proxy import get_stream_proxy
from .basketballreplays import (
    get_dailymotion_manifest, fetch_dailymotion_master_bytes,
    get_dailymotion_proxy, dailymotion_audio_links,
)


# FullRaces import trace independent of JetExtractors debug preferences.
xbmc.log("[FullRacesProbe JET 3.3.31] active module: {}".format(__file__), xbmc.LOGWARNING)


def _fetch_fullraces_html(url, referer=None):
    """FullRaces-only fetch with visible HTTP diagnostics and native fallback.

    Do not use the shared fetch_page() here: it converts HTTP errors into an
    empty response, hiding why categories and race links are missing.
    """
    from urllib.parse import urlparse
    import requests

    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('fullraces.com', 'www.fullraces.com'):
        xbmc.log('[FullRacesHTTP] Refused unexpected destination', xbmc.LOGERROR)
        return ''
    path = (parsed.path or '/')[:100]
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
    }
    if referer:
        headers['Referer'] = referer

    def _blocked(text, extra=''):
        sample = (text or '')[:5000].lower()
        return ('just a moment' in sample and 'cloudflare' in sample or
                'cf-chl-' in sample or 'challenge-platform' in sample or
                'challenge' in extra.lower())

    try:
        result = requests.get(url, headers=headers, timeout=(4, 9), allow_redirects=True)
        html = result.text or ''
        blocked = _blocked(html, result.headers.get('cf-mitigated', ''))
        xbmc.log('[FullRacesHTTP] requests path={} status={} chars={} blocked={} host={}'.format(
            path, result.status_code, len(html), blocked, urlparse(result.url).hostname), xbmc.LOGWARNING)
        if result.status_code == 200 and html and not blocked:
            return html
    except Exception as exc:
        xbmc.log('[FullRacesHTTP] requests path={} error={}: {}'.format(
            path, type(exc).__name__, str(exc)[:180]), xbmc.LOGWARNING)

    # The native Go client uses a different TLS/browser profile. Only try it
    # when ordinary requests cannot return a valid page; it is optional.
    try:
        from goclient import get as go_get
        response = go_get(url, profile='chrome133', timeout=10, headers=headers)
        status = getattr(response, 'status_code', 0)
        html = getattr(response, 'text', '') or ''
        error = getattr(response, 'error', '') or ''
        mitigated = getattr(response, 'cf_mitigated', '') or ''
        blocked = _blocked(html, mitigated)
        xbmc.log('[FullRacesHTTP] Go chrome133 path={} status={} chars={} blocked={} error={}'.format(
            path, status, len(html), blocked, str(error)[:150]), xbmc.LOGWARNING)
        if status == 200 and html and not blocked and not error:
            return html
    except (ImportError, AttributeError) as exc:
        xbmc.log('[FullRacesHTTP] Go unavailable: {}'.format(type(exc).__name__), xbmc.LOGWARNING)
    except Exception as exc:
        xbmc.log('[FullRacesHTTP] Go path={} error={}: {}'.format(
            path, type(exc).__name__, str(exc)[:160]), xbmc.LOGWARNING)

    xbmc.log('[FullRacesHTTP] No usable HTML for path={}'.format(path), xbmc.LOGERROR)
    return ''

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
        """Fetch FullRaces categories or posts, tolerating changed site markup.

        Category names/paths are first read from the website's original menu.
        When the menu is missing (or its fetch fails), use confirmed category
        URLs rather than raising AttributeError on a missing ``ul#list_cat``.
        Link resolution remains in get_links and is not modified here.
        """
        from urllib.parse import urljoin, urlparse
        xbmc.log("[FullRacesProbe JET 3.3.31] get_items entered params={!r}".format(params), xbmc.LOGWARNING)
        items = []
        if self.progress_init(progress, items):
            xbmc.log("[FullRacesDiag 3.3.33] cancelled before fetch", xbmc.LOGWARNING)
            return items

        base_url = "https://fullraces.com"
        # Fallback paths checked against FullRaces on 25 October 2026.
        category_fallback = (
            ("Formula 1 2026", "/2026"),
            ("Formula 1 2025", "/2025"),
            ("Formula 1 2024", "/watch/formula_1/formula_1_2024/21"),
            ("Formula 1 2023", "/f1-2023"),
            ("Formula 1 2022", "/formula1-2022"),
            ("Formula 1 2021", "/formula1-2021"),
            ("Formula 1 2020", "/f1-2020"),
            ("Formula 1 2019", "/f1-2019"),
            ("F1 Archive Races", "/f1-archive-races"),
            ("NASCAR", "/nascar"),
            ("IndyCar", "/indycar"),
            ("WSBK", "/wsbk"),
            ("WRC", "/wrc"),
            ("Formula 2", "/f2-full-races"),
            ("Formula 3", "/f3-full-races"),
            ("Formula E", "/formula-e"),
            ("F1 Academy", "/f1-academy"),
        )

        if not params:
            try:
                response = _fetch_fullraces_html(base_url)
                xbmc.log("[FullRacesDiag 3.3.33] homepage fetch returned {} chars".format(len(response or '')), xbmc.LOGWARNING)
                soup = bs(response or '', 'html.parser')
                menu = soup.select_one('ul#list_cat')
                # The old menu selector may be removed; avoid a None.select crash.
                if menu is not None:
                    for li in menu.select('li'):
                        if li.get('class'):
                            continue  # preserve original exclusion of section headers
                        a = li.find('a', href=True)
                        if a is None:
                            continue
                        name = a.get_text(' ', strip=True)
                        destination = urlparse(urljoin(base_url + '/', a['href']))
                        if (not name or destination.hostname not in
                                ('fullraces.com', 'www.fullraces.com')):
                            continue
                        href = destination.path or '/'
                        if not any(item.params['href'] == href for item in items):
                            items.append(JetItem(title=name, links=[], params={'href': href}))
            except Exception as exc:
                xbmc.log('[FullRacesDiag 3.3.33] Category fetch failed ({}: {}); using fallback'.format(
                    type(exc).__name__, exc), xbmc.LOGERROR)

            if not items:
                xbmc.log('[FullRacesDiag 3.3.33] Category menu absent; using fallback list', xbmc.LOGWARNING)
                for name, path in category_fallback:
                    items.append(JetItem(title=name, links=[], params={'href': path}))
            xbmc.log('[FullRacesDiag 3.3.33] returning {} categories'.format(len(items)), xbmc.LOGWARNING)
            return items

        href = params.get('href', '')
        category = urlparse(urljoin(base_url + '/', href))
        if category.hostname not in ('fullraces.com', 'www.fullraces.com'):
            raise ValueError('FullRaces invalid category path')
        category_url = base_url + (category.path or '/')
        try:
            page = max(1, int(params.get('page', 1)))
        except (TypeError, ValueError):
            page = 1
        # uCoz pagination uses '?page2=', '?page3=', ... (not '?page=2').
        if page > 1:
            category_url += '?page{}='.format(page)

        response = _fetch_fullraces_html(category_url, referer=base_url)
        xbmc.log('[FullRacesDiag 3.3.33] category fetch {}: {} chars'.format(category.path, len(response or '')), xbmc.LOGWARNING)
        soup = bs(response or '', 'html.parser')
        matches = soup.select('.short_item.block_elem')
        if not matches:
            # Be defensive if the site's card markup changed.
            matches = soup.select('.short_item')
        if not matches:
            matches = soup.select('article')

        seen = set()
        for match in matches:
            title_anchor = match.select_one('h3 a[href], h2 a[href], h4 a[href]')
            if title_anchor is None:
                continue
            title = title_anchor.get_text(' ', strip=True).replace('Full Game Replay ', '').strip()
            link_url = urljoin(base_url + '/', title_anchor['href'])
            if not title or urlparse(link_url).hostname not in ('fullraces.com', 'www.fullraces.com'):
                continue
            if link_url in seen:
                continue
            seen.add(link_url)
            image = match.select_one('img')
            image_path = (image.get('data-src') or image.get('src') or '') if image else ''
            icon = urljoin(base_url + '/', image_path) if image_path else ''
            items.append(JetItem(title, links=[JetLink(link_url, links=True)], icon=icon))

        if items:
            items.append(JetItem('[COLORyellow]Page {}[/COLOR]'.format(page + 1),
                                 links=[], params={'page': page + 1, 'href': category.path or '/'}))
        else:
            debug_log('[FullRaces] No race cards found on {}'.format(category_url))
        xbmc.log('[FullRacesDiag 3.3.33] returning {} category-page items'.format(len(items)), xbmc.LOGWARNING)
        return items
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        base_url = f"https://{self.domains[0]}"
        r = _fetch_fullraces_html(url.address, referer=base_url)
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
                    links.extend(dailymotion_audio_links(
                        dm_link.address, dm_link.headers, label=title or "Dailymotion"))
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
                    links.extend(dailymotion_audio_links(
                        dm_link.address, dm_link.headers, label=title or "Dailymotion"))
                else:
                    links.append(JetLink(link, name=title, resolveurl=True))
            else:
                links.append(JetLink(link, name=title, resolveurl=True))

        return links

    def _resolve_dailymotion(self, dm_url: str, title: str) -> Optional[JetLink]:
        """Retrieve a Go-verified master playlist and retain external audio."""
        try:
            result = get_dailymotion_manifest(dm_url, self.user_agent)
            if not result:
                return None
            master_url, headers = result
            fetched = fetch_dailymotion_master_bytes(master_url, headers)
            if not fetched:
                return None
            master_bytes, resolved_url = fetched
            proxy_url, headers = get_dailymotion_proxy(
                master_bytes, headers, master_url=resolved_url)
            if not proxy_url:
                return None
            return JetLink(proxy_url, name=title, headers=headers, resolveurl=False,
                           inputstream=JetInputstreamFFmpegDirect(
                               manifest_type='hls', open_mode='ffmpeg'))
        except Exception as exc:
            import xbmc
            xbmc.log('[FullRaces] Dailymotion Go/FFmpeg: {}'.format(
                type(exc).__name__), xbmc.LOGWARNING)
            return None
