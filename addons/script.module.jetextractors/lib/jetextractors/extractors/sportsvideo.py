# -*- coding: utf-8 -*-
"""SportsVideo JetExtractor: NFL, MLB, Rugby, MMA.

MLB and Rugby use the installed script.module.go HTTP engine. NFL/MMA keep
JetExtractors' existing fetch_page transport.
"""
import os
import re
import sys
from urllib.parse import urljoin, urlparse, urlsplit

import xbmc
from bs4 import BeautifulSoup as bs

from ..models import JetExtractor, JetExtractorProgress, JetItem, JetLink
from .._core import fetch_page, get_session
from typing import Optional, List


class SportsVideo(JetExtractor):
    domains = ['nfl-replays.com', 'mlblive.net', 'rugby24.net', 'fullfightreplays.com']
    name = 'SportsVideo'

    @staticmethod
    def _go_domain(url):
        return (urlparse(url).hostname or '').lower() in ('mlblive.net', 'rugby24.net')

    def _html(self, url, referer=None):
        """Use Go for MLB/Rugby, existing fetch_page for NFL/MMA."""
        if not self._go_domain(url):
            return fetch_page(url, referer=referer) if referer else fetch_page(url)

        # Lazy import: NFL/MMA should still work even without the Go module.
        # Some Kodi builds do not expose a nested module's lib/ on sys.path.
        try:
            from goclient import get as go_get
        except ImportError:
            import xbmcaddon
            import xbmcvfs
            root = xbmcaddon.Addon('script.module.go').getAddonInfo('path')
            root = xbmcvfs.translatePath(root)
            lib_path = os.path.join(root, 'lib')
            if lib_path not in sys.path:
                sys.path.insert(0, lib_path)
            from goclient import get as go_get
        headers = {'Referer': referer} if referer else None
        last_error = 'No response'
        for profile in ('android', 'chrome133'):
            try:
                response = go_get(url, profile=profile, headers=headers,
                                  timeout=int(getattr(self, 'timeout', 25) or 25))
                html = response.text
                blocked = (response.cf_mitigated or
                           'just a moment' in html[:2000].lower())
                if response.status_code == 200 and html.strip() and not blocked:
                    xbmc.log('[SportsVideo] Go {}: HTTP 200 ({} bytes)'.format(
                        urlparse(url).hostname, len(response.content)), xbmc.LOGINFO)
                    return html
                last_error = response.error or 'HTTP {}{}'.format(
                    response.status_code, ' (challenge)' if blocked else '')
            except Exception as exc:
                last_error = str(exc)
        raise RuntimeError('{}: {}'.format(urlparse(url).hostname, last_error))

    def _notice(self, label, league):
        return [JetItem(title=label, links=[],
                        params={'league': league, 'notice': '1'})]

    def get_items(self, params: Optional[dict] = None,
                  progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        if params is None:
            for index, name in enumerate(('NFL', 'MLB', 'Rugby', 'MMA')):
                items.append(JetItem(title=name, links=[],
                                     params={'league': str(index)}))
            return items
        if params.get('notice'):
            return items
        try:
            league = int(params.get('league', 0))
            domain = self.domains[league]
        except (ValueError, TypeError, IndexError):
            return items
        base_url = 'https://' + domain
        path = params.get('href')
        page_url = urljoin(base_url + '/', str(path)) if path else base_url

        try:
            if not path:
                soup = bs(self._html(page_url), 'html.parser')
                nav = soup.select_one('ul#list_cat')
                if nav:
                    seen = set()
                    for li in nav.select('li'):
                        if li.get('class'):
                            continue  # Category group headings aren't links.
                        a = li.find('a', href=True, recursive=False)
                        if not a:
                            continue
                        category_url = urljoin(page_url, a['href'])
                        parsed = urlsplit(category_url)
                        if parsed.hostname != domain or category_url in seen:
                            continue
                        label = a.get_text(' ', strip=True)
                        if not label:
                            continue
                        if self.progress_update(progress, label):
                            return items
                        seen.add(category_url)
                        category_path = parsed.path + (('?' + parsed.query) if parsed.query else '')
                        items.append(JetItem(title=label, links=[],
                                             params={'league': league, 'href': category_path}))
                        xbmc.sleep(50)
                    if items:
                        return items
                # The site may no longer have the old category navigation.
                # If so, show replays from its homepage rather than failing.
            else:
                # Retain the existing session for NFL/MMA; Go handles MLB/Rugby.
                if self._go_domain(page_url):
                    html = self._html(page_url, referer=base_url + '/')
                else:
                    headers = {'User-Agent': self.user_agent, 'Referer': base_url}
                    session = get_session(referer=base_url)
                    html = session.get(page_url, headers=headers, verify=True,
                                       timeout=self.timeout).text
                soup = bs(html, 'html.parser')

            seen = set()
            for match in soup.select('.short_item.block_elem'):
                a = match.select_one('h3 a[href]')
                if not a:
                    continue
                link = urljoin(page_url, a['href'])
                if urlparse(link).hostname != domain or link in seen:
                    continue
                title = re.sub(r'\s+', ' ', a.get_text(' ', strip=True))
                title = re.sub(r'^Full Game Replay\s*[-:]?\s*', '',
                               title, flags=re.IGNORECASE).strip()
                if not title:
                    continue
                if self.progress_update(progress, title):
                    return items
                poster = match.select_one('img')
                image = ''
                if poster:
                    image = poster.get('data-src') or poster.get('data-lazy-src') or poster.get('src') or ''
                seen.add(link)
                items.append(JetItem(title, links=[JetLink(link, links=True)],
                                     icon=urljoin(page_url, image) if image else ''))
                xbmc.sleep(50)

            # Original sites use '/?page2' or category links with a
            # swchItem '»' next-page control.
            for a in soup.select('a.swchItem[href]'):
                if a.get_text(' ', strip=True) != '»':
                    continue
                next_url = urljoin(page_url, a['href'])
                parsed = urlsplit(next_url)
                if parsed.hostname != domain:
                    continue
                next_path = parsed.path + (('?' + parsed.query) if parsed.query else '')
                match = re.search(r"spages\(['\"](\d+)", a.get('onclick', ''))
                if match:
                    page = int(match.group(1))
                else:
                    current = int(params.get('page') or 1)
                    page = current + 1
                items.append(JetItem('[COLOR yellow]Page {}[/COLOR]'.format(page),
                                     links=[], params={'league': league, 'page': page,
                                                       'href': next_path}))
                break
            return items
        except Exception as exc:
            xbmc.log('[SportsVideo] {} listing error: {}'.format(domain, exc), xbmc.LOGERROR)
            return self._notice('{}: {}'.format(domain, exc), league)

    def get_links(self, url: JetLink) -> List[JetLink]:
        address = url.address
        base_url = 'https://{}/'.format(urlparse(address).netloc)
        try:
            soup = bs(self._html(address, referer=base_url), 'html.parser')
        except Exception as exc:
            xbmc.log('[SportsVideo] replay error: {}'.format(exc), xbmc.LOGERROR)
            return []
        links, seen = [], set()

        def add_link(link):
            link = urljoin(address, (link or '').strip())
            parsed = urlparse(link)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc or link in seen:
                return
            seen.add(link)
            links.append(JetLink(link, name=parsed.hostname or 'Server', resolveurl=True))

        content = soup.select_one('.fullstory') or soup
        for button in content.select('a.su-button[href]'):
            target = urljoin(address, button['href'])
            if any(host in (urlparse(target).hostname or '') for host in
                   ('nfl-replays', 'nfl-video', 'basketball-video')):
                try:
                    wrapper = bs(self._html(target, referer=base_url), 'html.parser')
                    iframe = wrapper.select_one('iframe[src]')
                    if iframe:
                        target = urljoin(target, iframe['src'])
                    else:
                        continue
                except Exception:
                    continue
            add_link(target)

        for iframe in content.select('iframe[src],iframe[data-src]'):
            add_link(iframe.get('data-src') or iframe.get('src'))
        return links
