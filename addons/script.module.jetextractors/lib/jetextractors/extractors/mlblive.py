import json
import re
import requests
from bs4 import BeautifulSoup as bs
from urllib.parse import parse_qs, urlparse, urlencode
from ..models import *
import xbmc
import uuid
import time

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

    def _handle_dailymotion(self, link: str) -> Optional[JetLink]:
        """Extract video_id from any Dailymotion URL variant, resolve the signed
        m3u8 directly via the player metadata API, and return a playable JetLink.
        Falls back to resolveurl if the API call fails.

        The Dailymotion CDN director validates the signed URL against the v1st
        visitor cookie.  We extract the v1st value from the dmV1st query param
        in the returned manifest URL and echo it back as a Cookie header so the
        CDN can verify the signature.
        """
        parsed = urlparse(link)
        host = parsed.netloc.lower()
        if "dailymotion.com" not in host and "dai.ly" not in host:
            return None

        # --- extract video_id ---
        video_id = parse_qs(parsed.query).get("video", [None])[0]
        path_parts = [p for p in parsed.path.split("/") if p]

        if video_id is None:
            if host == "dai.ly" and path_parts:
                video_id = path_parts[0]
            elif "video" in path_parts:
                idx = path_parts.index("video")
                if idx + 1 < len(path_parts):
                    video_id = path_parts[idx + 1]
            elif path_parts:
                # last path segment (handles /embed/{id} etc.)
                video_id = path_parts[-1]

        if not video_id:
            return None

        video_id = video_id.split(".")[0]

        # --- try direct metadata API ---
        try:
            session = requests.Session()
            
            # Use same UA as official Dailymotion addon
            ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
            session.headers.update(_browser_session_headers())
            
            # Add ff cookie to session
            session.cookies.set('ff', 'on')
            
            # First warmup request to geo.dailymotion.com
            session.get('https://geo.dailymotion.com/', timeout=self.timeout)
            xbmc.log(f"[Dailymotion] Geo warmup cookies: {session.cookies.get_dict()}", xbmc.LOGINFO)
            
            # Also visit the embed page to get more cookies (like official addon does)
            embed_resp = session.get('https://www.dailymotion.com/embed/video/' + video_id, timeout=self.timeout)
            xbmc.log(f"[Dailymotion] After embed page cookies: {session.cookies.get_dict()}", xbmc.LOGINFO)
            
            # Try to extract cookies from embed page HTML/JS
            embed_html = embed_resp.text
            # Look for dmvk in the page - sometimes it's embedded in JS
            dmvk_match = re.search(r'dmvk["\s:=]+([a-f0-9]+)', embed_html)
            if dmvk_match:
                xbmc.log(f"[Dailymotion] Found dmvk in embed page: {dmvk_match.group(1)}", xbmc.LOGINFO)
            
            # Get metadata
            params = _metadata_params(video_id)
            meta_url = f'https://www.dailymotion.com/player/metadata/video/{video_id}'
            r = session.get(meta_url, params=params, timeout=self.timeout)
            data = r.json()
            
            xbmc.log(f"[Dailymotion] Metadata keys: {list(data.keys())}", xbmc.LOGINFO)
            
            auto = data.get("qualities", {}).get("auto", [])
            if auto:
                m3u8_url = auto[0].get("url", "")
                xbmc.log(f"[Dailymotion] m3u8_url (auto): {m3u8_url}", xbmc.LOGINFO)
            
            # Try other quality levels
            if not m3u8_url:
                qualities = data.get("qualities", {})
                for quality_level in ['1080p', '720p', '480p', '360p', '240p']:
                    if quality_level in qualities:
                        for q in qualities[quality_level]:
                            if q.get("url"):
                                m3u8_url = q["url"]
                                xbmc.log(f"[Dailymotion] m3u8_url ({quality_level}): {m3u8_url}", xbmc.LOGINFO)
                                break
                    if m3u8_url:
                        break
            
            if not m3u8_url:
                stream_formats = data.get("stream_formats", [])
                for sf in stream_formats:
                    if sf.get("url"):
                        m3u8_url = sf["url"]
                        xbmc.log(f"[Dailymotion] m3u8_url (stream_formats): {m3u8_url}", xbmc.LOGINFO)
                        break
            
            if m3u8_url:
                cookies = session.cookies.get_dict()
                cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                headers = _browser_session_headers()
                headers['Cookie'] = cookie_str
                xbmc.log(f"[Dailymotion] Fetching m3u8 with cookies: {cookies}", xbmc.LOGDEBUG)
                
                try:
                    mbtext = session.get(m3u8_url, headers=headers, timeout=self.timeout).text
                    xbmc.log(f"[Dailymotion] m3u8 content length: {len(mbtext)}", xbmc.LOGDEBUG)
                    xbmc.log(f"[Dailymotion] m3u8 content start: {mbtext[:500]}", xbmc.LOGDEBUG)
                    
                    # Try various formats
                    mb = re.findall(r'NAME="([^"]+)",PROGRESSIVE-URI="([^"]+)"', mbtext)
                    if not mb:
                        mb = re.findall(r'NAME=([^"\n]+).*?\n([^\n]+)', mbtext)
                    if not mb:
                        mb = re.findall(r'X-CAPI-LINEAR-URI: "([^"]+)"', mbtext)
                    
                    xbmc.log(f"[Dailymotion] Regex matches: {mb}", xbmc.LOGDEBUG)
                    
                    if mb:
                        mb = sorted(mb, key=lambda x: int(x[0].split("@")[0]) if "@" in x[0] and x[0].split("@")[0].isdigit() else 0, reverse=True)
                        for quality, strurl in mb:
                            if "@" in quality:
                                quality_val = int(quality.split("@")[0])
                            else:
                                quality_val = 0
                            xbmc.log(f"[Dailymotion] Quality match: {quality}, url: {strurl[:50]}", xbmc.LOGDEBUG)
                            if quality_val <= 1080:
                                if not strurl.startswith('http'):
                                    strurl = '/'.join(m3u8_url.split('/')[:-1]) + '/' + strurl
                                stream_url = f'{strurl}|{urlencode(headers)}'
                                xbmc.log(f"[Dailymotion] Final stream URL: {stream_url[:80]}...", xbmc.LOGDEBUG)
                                return JetLink(stream_url, name=f"Dailymotion {quality_val}p", inputstream=JetInputstreamFFmpegDirect.default())
                except Exception as e:
                    xbmc.log(f"[Dailymotion] Parse exception: {e}", xbmc.LOGWARNING)
                
                # Last resort: return embed URL with resolveurl
                return JetLink(f"https://www.dailymotion.com/embed/video/{video_id}", name="Dailymotion", resolveurl=True)
        except Exception as e:
            xbmc.log(f"[Dailymotion] Exception: {e}", xbmc.LOGERROR)

        # --- fallback: use embed URL with resolveurl ---
        return JetLink(
            f"https://www.dailymotion.com/embed/video/{video_id}",
            name="Dailymotion",
            resolveurl=True,
        )

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = f"https://{self.domains[0]}"
        url =  f"{base_url}/?page{params['page']}" if params is not None else base_url
        headers = {"User-Agent": self.user_agent, "Referer": base_url}
        r = requests.get(url, headers=headers, timeout=self.timeout).text
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
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        seen = set()
        base_url = f"https://{urlparse(url.address).netloc}/"
        headers = {"User-Agent": self.user_agent, "Referer": base_url}
        r = requests.get(url.address, headers=headers, timeout=self.timeout).text
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
                r2 = requests.get(link, headers=headers, timeout=self.timeout).text
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
