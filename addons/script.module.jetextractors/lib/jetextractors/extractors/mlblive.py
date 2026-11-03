import json
import re
from bs4 import BeautifulSoup as bs
from urllib.parse import parse_qs, urlparse
from ..models import *
from .._core import fetch_page, get_session
import xbmc
import uuid
import time
from ..tools import debug_log

def _browser_session_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Origin': 'https://geo.dailymotion.com',
        'Referer': 'https://geo.dailymotion.com/',
    }

def _metadata_params(vid):
    dm_v1st = str(uuid.uuid4())
    dm_ts = str(int(time.time()))
    return {
        'embedder': 'https://www.dailymotion.com',
        'locale': 'en-GB',
        'dmV1st': dm_v1st,
        'dmTs': dm_ts,
        'is_native_app': '0',
        'geo': '1',
        'player-id': 'web',
        'client_type': 'website',
        'dmViewId': str(uuid.uuid4()),
        'video': vid
    }

class MlbLive(JetExtractor):
    domains = ["mlblive.net"]
    name = "MlbLive"

    def _html(self, url, referer=None):
        """MLBLive-only fetch with visible status/Cloudflare/Go diagnostics.

        Do not change JetExtractors' shared HTTP client or playback handling.
        The Go fallback is optional and errors must not disappear silently.
        """
        import requests
        from urllib.parse import urlparse

        host = (urlparse(url).hostname or '').lower()
        path = (urlparse(url).path or '/')[:120]
        headers = {
            'User-Agent': self.user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/133.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
        if referer:
            headers['Referer'] = referer

        def blocked(html, mitigated=''):
            sample = (html or '')[:5000].lower()
            return (bool(mitigated) or 'cf-chl-' in sample or
                    'challenge-platform' in sample or
                    ('just a moment' in sample and 'cloudflare' in sample))

        timeout = max(5, min(30, int(self.timeout or 15)))
        try:
            result = requests.get(url, headers=headers, timeout=(4, timeout),
                                  allow_redirects=True)
            html = result.text or ''
            is_blocked = blocked(html, result.headers.get('cf-mitigated', ''))
            xbmc.log('[MlbLiveHTTP] requests host={} path={} status={} chars={} blocked={}'.format(
                host, path, result.status_code, len(html), is_blocked), xbmc.LOGWARNING)
            if result.status_code == 200 and html.strip() and not is_blocked:
                return html
        except Exception as exc:
            xbmc.log('[MlbLiveHTTP] requests host={} path={} error={}: {}'.format(
                host, path, type(exc).__name__, str(exc)[:150]), xbmc.LOGWARNING)

        try:
            try:
                from goclient import get as go_get
            except ImportError:
                import os
                import sys
                import xbmcaddon
                import xbmcvfs
                root = xbmcvfs.translatePath(
                    xbmcaddon.Addon('script.module.go').getAddonInfo('path'))
                lib_path = os.path.join(root, 'lib')
                if lib_path not in sys.path:
                    sys.path.insert(0, lib_path)
                from goclient import get as go_get
            for profile in ('android', 'chrome133'):
                try:
                    response = go_get(url, profile=profile, headers=headers,
                                      timeout=timeout)
                    html = response.text or ''
                    error = response.error or ''
                    is_blocked = blocked(html, response.cf_mitigated)
                    xbmc.log('[MlbLiveHTTP] Go {} host={} path={} status={} chars={} blocked={} error={}'.format(
                        profile, host, path, response.status_code, len(html),
                        is_blocked, error[:150]), xbmc.LOGWARNING)
                    if (response.status_code == 200 and html.strip()
                            and not is_blocked and not error):
                        return html
                except Exception as exc:
                    xbmc.log('[MlbLiveHTTP] Go {} host={} error={}: {}'.format(
                        profile, host, type(exc).__name__, str(exc)[:150]),
                        xbmc.LOGWARNING)
        except Exception as exc:
            xbmc.log('[MlbLiveHTTP] Go client unavailable: {}: {}'.format(
                type(exc).__name__, str(exc)[:150]), xbmc.LOGWARNING)

        xbmc.log('[MlbLiveHTTP] No usable HTML host={} path={}'.format(host, path),
                 xbmc.LOGERROR)
        return ''

    def _handle_dailymotion(self, link: str) -> Optional[JetLink]:
        """Preserve separate Dailymotion AAC audio via Go + HLS master."""
        parsed = urlparse(link)
        host = (parsed.hostname or '').lower()
        if host not in ('dai.ly', 'dailymotion.com') and not host.endswith('.dailymotion.com'):
            return None
        try:
            from .basketballreplays import (
                get_dailymotion_manifest, fetch_dailymotion_master_bytes,
                get_dailymotion_proxy,
            )
            result = get_dailymotion_manifest(link, self.user_agent)
            if result:
                master_url, headers = result
                fetched = fetch_dailymotion_master_bytes(master_url, headers)
                if fetched:
                    master, resolved_url = fetched
                    proxy_url, headers = get_dailymotion_proxy(
                        master, headers, master_url=resolved_url)
                    if proxy_url:
                        return JetLink(proxy_url, name='Dailymotion (FFmpeg + Audio)',
                                       headers=headers, resolveurl=False,
                                       inputstream=JetInputstreamFFmpegDirect(
                                           manifest_type='hls', open_mode='ffmpeg'))
        except Exception as exc:
            xbmc.log('[MlbLive] Dailymotion Go/FFmpeg: {}'.format(type(exc).__name__),
                     xbmc.LOGWARNING)
        # This fallback remains unchanged in the external ResolveURL add-on.
        return JetLink(link, name='Dailymotion (ResolveURL fallback)',
                       resolveurl=True)

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        """Handle current listings and DLE-style ?page2= pagination safely."""
        from urllib.parse import urljoin, urlparse
        items = []
        if self.progress_init(progress, items):
            return items

        base_url = 'https://mlblive.net'
        try:
            page = int((params or {}).get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, min(page, 10000))
        url = base_url + ('/?page{}='.format(page) if page > 1 else '/')
        xbmc.log('[MlbLiveHTTP] get_items page={} url={}'.format(page, url), xbmc.LOGWARNING)
        html = self._html(url, referer=base_url + '/')
        if not html:
            xbmc.log('[MlbLiveHTTP] EMPTY listing page={} (no phantom next page)'.format(page),
                     xbmc.LOGWARNING)
            return items

        soup = bs(html, 'html.parser')
        cards = soup.select('.short_item.block_elem') or soup.select('.short_item')
        if not cards:
            cards = soup.select('article')
        seen = set()

        def add_post(anchor, image):
            if anchor is None or not anchor.get('href'):
                return
            address = urljoin(base_url + '/', anchor['href'])
            parsed = urlparse(address)
            if parsed.scheme != 'https' or parsed.hostname not in ('mlblive.net', 'www.mlblive.net'):
                return
            # A replay post must have a non-homepage path, not a category/pagination link.
            if not parsed.path or parsed.path == '/' or address in seen:
                return
            title = anchor.get_text(' ', strip=True)
            if not title or 'full game replay' not in title.lower():
                return
            title = re.sub(r'\s+', ' ', title).strip()
            seen.add(address)
            if self.progress_update(progress, title):
                return 'cancelled'
            icon = ''
            if image is not None:
                src = (image.get('data-src') or image.get('data-original') or
                       image.get('src') or '')
                if src:
                    icon = urljoin(base_url + '/', src)
            items.append(JetItem(title, links=[JetLink(address, links=True)], icon=icon))

        for card in cards:
            a = card.select_one('h3 a[href], h2 a[href], h4 a[href]')
            if a is None:
                a = card.select_one('a[href]')
            ret = add_post(a, card.find('img'))
            if ret == 'cancelled':
                return items

        # Some templates put each replay heading outside the legacy cards.
        if not items:
            for heading in soup.select('h3, h2'):
                ret = add_post(heading.find('a', href=True), heading.find('img'))
                if ret == 'cancelled':
                    return items

        xbmc.log('[MlbLiveHTTP] parsed page={} html_chars={} cards={} posts={}'.format(
            page, len(html), len(cards), len(items)), xbmc.LOGWARNING)

        if items:
            next_page = page + 1
            has_next = False
            for a in soup.select('a[href]'):
                href = a.get('href', '')
                if ('?page{}='.format(next_page) in href or
                        '?page{}'.format(next_page) == href or
                        '/page/{}/'.format(next_page) in href):
                    has_next = True
                    break
            if has_next:
                items.append(JetItem('[COLORyellow]Page {}[/COLOR]'.format(next_page),
                                     links=[], params={'page': next_page}))
                xbmc.log('[MlbLiveHTTP] next page={} detected'.format(next_page),
                         xbmc.LOGWARNING)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        seen = set()
        base_url = f"https://{urlparse(url.address).netloc}/"
        r = self._html(url.address, referer=base_url)
        soup = bs(r, 'html.parser')

        def _add_link(raw_link: str) -> None:
            if raw_link.startswith('//'):
                raw_link = f'https:{raw_link}'
            dm = self._handle_dailymotion(raw_link)
            if dm is not None:
                key = dm.address
                if key not in seen:
                    seen.add(key)
                    links.append(dm)
                    # Keep the previous playback engine as an optional route
                    # if inputstream.adaptive is not installed or fails.
                    if dm.name == "Dailymotion (Audio - Adaptive)":
                        links.append(JetLink(
                            dm.address, name="Dailymotion (FFmpeg fallback)",
                            headers=dm.headers,
                            inputstream=JetInputstreamFFmpegDirect.default()))
            else:
                if raw_link not in seen:
                    seen.add(raw_link)
                    title = raw_link.split('/')[2] if len(raw_link.split('/')) > 2 else raw_link
                    links.append(JetLink(raw_link, name=title, resolveurl=True))

        for button in soup.find_all(class_='su-button'):
            link = button.get('href', '')
            if not link:
                continue
            if link.startswith('//'):
                link = f'https:{link}'
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv',
                                        'gamesontvtoday', 'nbatraderumors', 'nhlgamestoday', 'mlblive']):
                r2 = self._html(link, referer=base_url)
                _soup2 = bs(r2, 'html.parser')
                iframe = _soup2.find('iframe')
                if iframe:
                    link = iframe.get('src', '')
                else:
                    continue
            _add_link(link)

        for iframe in soup.find_all('iframe'):
            link = iframe.get('src', '')
            if not link:
                continue
            _add_link(link)

        return links
