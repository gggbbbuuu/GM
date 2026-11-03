import re
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse, parse_qs
from ..models import *
from .._core import fetch_page
from .basketballreplays import (
    get_dailymotion_manifest, get_dailymotion_proxy, dailymotion_audio_links,
    fetch_dailymotion_master_bytes
)

class FullFightReplays(JetExtractor):
    domains = ["fullfightreplays.com"]
    name = "FullFightReplays"

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
            xbmc.sleep(50)
            link = f"{base_url}{match.a['href']}"
            icon = f"{base_url}{match.a.img['src']}"
            items.append(JetItem(name, links=[JetLink(link, links=True)], icon=icon))

        if params is not None:
            next_page = int(params['page']) + 1
        else:
            next_page = 2
        items.append(JetItem(f"[COLORyellow]Page {next_page}[/COLOR]", links=[], params={"page": next_page}))
        return items
    
    @staticmethod
    def _dailymotion_watch_url(raw_url):
        """Normalise standard/embedded/short Dailymotion URLs for the master resolver."""
        parsed = urlparse(raw_url)
        host = (parsed.hostname or '').lower()
        if host != 'dai.ly' and host != 'dailymotion.com' and not host.endswith('.dailymotion.com'):
            return None
        if host == 'dai.ly':
            video_id = parsed.path.strip('/').split('/')[0]
            return 'https://www.dailymotion.com/video/' + video_id if video_id else None
        # Handle /video/ID, /embed/video/ID and ?video=ID.
        import re
        found = re.search(r'/video/([a-zA-Z0-9]+)', parsed.path)
        if found:
            return 'https://www.dailymotion.com/video/' + found.group(1)
        video_id = parse_qs(parsed.query).get('video', [None])[0]
        return 'https://www.dailymotion.com/video/' + video_id if video_id else None

    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        seen = set()
        dailymotion_count = 0

        def add_link(raw_url):
            nonlocal dailymotion_count
            if not raw_url:
                return
            if raw_url.startswith('//'):
                raw_url = 'https:' + raw_url

            # Buttons and embedded players often expose different URL forms
            # for the same video. Count each Dailymotion video only once.
            dm_watch_url = self._dailymotion_watch_url(raw_url)
            identity = dm_watch_url or raw_url
            if identity in seen:
                return
            seen.add(identity)
            host = urlparse(raw_url).hostname or ''
            if dm_watch_url:
                dailymotion_count += 1
                label = 'Dailymotion {}'.format(dailymotion_count)
                # Keep the entire audio-enabled HLS master. FFmpegDirect is a
                # playback detail, not a separate link/mirror to display.
                try:
                    result = get_dailymotion_manifest(dm_watch_url, self.user_agent)
                    if result:
                        master_url, headers = result
                        fetched = fetch_dailymotion_master_bytes(master_url, headers)
                        if fetched:
                            master_bytes, final_url = fetched
                            proxy_url, headers = get_dailymotion_proxy(
                                master_bytes, headers, master_url=final_url)
                            if proxy_url:
                                prepared = dailymotion_audio_links(proxy_url, headers, label)
                                if prepared:
                                    # Exactly one choice per playable video.
                                    # Preserve its FFmpegDirect inputstream.
                                    prepared[0].name = label
                                    links.append(prepared[0])
                                    return
                except Exception as exc:
                    xbmc.log('[FullFightReplays] Dailymotion master error: {}'.format(exc), xbmc.LOGWARNING)
                # Only show the older resolver if the audio-enabled master
                # failed. It may return a video-only stream.
                links.append(JetLink(raw_url, name=label + ' (backup)', resolveurl=True))
                return
            links.append(JetLink(raw_url, name=host, resolveurl=True))
        base_url = f"https://{urlparse(url.address).netloc}/"
        r = fetch_page(url.address, referer=base_url)
        soup = bs(r, 'html.parser')
        for button in soup.find_all(class_='su-button'):
            link = button['href']
            if link.startswith('//'):
                link = f'https:{link}'
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video']):
                r = fetch_page(link, referer=base_url)
                _soup = bs(r, 'html.parser')
                iframe = _soup.find('iframe')
                if iframe:
                    link = iframe['src']
                else:
                    continue
            if link.startswith('//'):
                link = f'https:{link}'
            add_link(link)
        
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            link = iframe['src']
            if link.startswith('//'):
                link = f'https:{link}'
            add_link(link)
        return links
        