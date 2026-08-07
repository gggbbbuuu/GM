from ..models import *
from ..util import m3u8_src
from ..util.stream_proxy import get_stream_proxy
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import base64
import json
import re
import time
import uuid
import xbmc

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

def get_dailymotion_proxy(manifest, user_agent):
    dm_headers = {"User-Agent": user_agent, "Referer": "https://www.dailymotion.com/", "Origin": "https://www.dailymotion.com"}
    proxy = get_stream_proxy("dailymotion", dm_headers, options={"cache_manifest": True, "manifest_ttl": 3600})
    if isinstance(manifest, bytes):
        port = proxy._ensure_server()
        token = uuid.uuid4().hex
        proxy._upstream[token] = {
            "url": "http://prepopulated.local",
            "headers": dm_headers,
            "fallback_urls": [],
            "cache": manifest,
            "cache_time": time.time(),
        }
        return f"http://127.0.0.1:{port}/dailymotion/{token}.m3u8", dm_headers
    return proxy.get_proxy_url(manifest, dm_headers), dm_headers

def get_dailymotion_manifest(dailymotion_url, user_agent):
    try:
        match = re.search(r'[/.]video/([a-z0-9]+)|video=([a-z0-9]+)', dailymotion_url)
        if not match:
            return None
        vid = match.group(1) or match.group(2)
        headers = {"User-Agent": user_agent, "Referer": "https://www.dailymotion.com/", "Origin": "https://www.dailymotion.com"}
        r = requests.get(f"https://www.dailymotion.com/player/metadata/video/{vid}", headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        qualities = data.get("qualities", {})
        auto = qualities.get("auto", [])
        if not auto or "url" not in auto[0] or ".m3u8" not in auto[0]["url"]:
            return None
        master_url = auto[0]["url"]
        r2 = requests.get(master_url, headers=headers, timeout=10)
        if r2.status_code != 200:
            return None
        master_text = r2.text
        variants = []
        current_inf = None
        for line in master_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#EXT-X-STREAM-INF"):
                current_inf = line
            elif not line.startswith("#"):
                if current_inf:
                    bw = 0
                    bw_match = re.search(r'BANDWIDTH=(\d+)', current_inf)
                    if bw_match:
                        bw = int(bw_match.group(1))
                    if not line.startswith("http"):
                        if line.startswith("//"):
                            line = "https:" + line
                        else:
                            base = master_url.rsplit("/", 1)[0]
                            line = base + "/" + line
                    variants.append((bw, line, current_inf))
                    current_inf = None
        if not variants:
            return None
        audio_group_id = "aud"
        has_audio = False
        master_lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
        for bw, url, inf in variants:
            codecs_match = re.search(r'CODECS="([^"]+)"', inf)
            codecs = codecs_match.group(1) if codecs_match else ""
            res_match = re.search(r'RESOLUTION=(\d+x\d+)', inf)
            res = res_match.group(1) if res_match else ""
            if codecs.startswith("mp4a") or (not codecs and "audio" in inf.lower()):
                has_audio = True
                master_lines.append('#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="' + audio_group_id + '",CODECS="' + codecs + '",DEFAULT=YES,AUTOSELECT=YES,NAME="audio",URI="' + url + '"')
            else:
                new_inf = "#EXT-X-STREAM-INF:BANDWIDTH=" + str(bw)
                if codecs:
                    new_inf += ',CODECS="' + codecs + '"'
                if res:
                    new_inf += ',RESOLUTION=' + res
                if has_audio:
                    new_inf += ',AUDIO="' + audio_group_id + '"'
                master_lines.append(new_inf)
                master_lines.append(url)
        if not has_audio:
            for bw, url, inf in variants:
                if "aac" in url.lower() or "audio" in url.lower():
                    codecs_match = re.search(r'CODECS="([^"]+)"', inf)
                    codecs = codecs_match.group(1) if codecs_match else "mp4a.40.2"
                    master_lines.append('#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="' + audio_group_id + '",CODECS="' + codecs + '",DEFAULT=YES,AUTOSELECT=YES,NAME="audio",URI="' + url + '"')
                    has_audio = True
                    break
            if has_audio:
                for ln_idx, ln in enumerate(master_lines):
                    if ln.startswith("#EXT-X-STREAM-INF:") and 'AUDIO=' not in ln:
                        master_lines[ln_idx] = ln + ',AUDIO="' + audio_group_id + '"'
        return ("\n".join(master_lines) + "\n").encode("utf-8")
    except:
        return None

def decrypt_bysesukior(video_code, referer):
    try:
        api_url = f"https://bysesukior.com/api/videos/{video_code}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": referer}
        r = requests.get(api_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        playback = data.get("playback", {})
        
        key_parts = playback.get("key_parts", [])
        if len(key_parts) < 2:
            return None
            
        def fix_b64(s):
            s = s.replace("-", "+").replace("_", "/")
            return s + "=" * (4 - len(s) % 4) if len(s) % 4 else s
        
        k1 = base64.b64decode(fix_b64(key_parts[0]))
        k2 = base64.b64decode(fix_b64(key_parts[1]))
        key = k1 + k2
        iv = base64.b64decode(fix_b64(playback.get("iv", "")))
        payload = base64.b64decode(fix_b64(playback.get("payload", "")))
        
        try:
            # Try cryptography module first
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(iv, payload, None)
        except:
            # Fallback to Cryptodome (available in Kodi)
            try:
                from Cryptodome.Cipher import AES
                # AES-GCM: last 16 bytes are the auth tag
                ciphertext = payload[:-16]
                auth_tag = payload[-16:]
                cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                plaintext = cipher.decrypt_and_verify(ciphertext, auth_tag)
            except:
                return None
        
        result = plaintext.decode("utf-8")
        j = json.loads(result)
        sources = j.get("sources", [])
        for source in sources:
            if ".m3u8" in source.get("url", ""):
                return source["url"]
        return None
    except:
        return None

class BasketballReplays(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["basketballreplays.net"]
        self.name = "BasketballReplays"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}/?page={params['page'] if params is not None else 1}").text
        soup = BeautifulSoup(r, "html.parser")
        for item in soup.select("div.h_post"):
            a = item.select_one("div.h_post_title > a")
            if a is None:
                continue
            title = a.text
            href = f"https://{self.domains[0]}" + a.get("href")
            img = item.select_one("img")
            icon = f"https://{self.domains[0]}" + img.get("src") if img else None
            items.append(JetItem(title, links=[JetLink(href, links=True)], icon=icon))
        if (next_page := soup.select_one("a.swchItem-next")) is not None:
            page = next_page.get("href", "").split("/?page")[-1]
            if page:
                items.append(JetItem(f"Page {page}", links=[], params={"page": page}))
        return items


    def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        seen = set()
        r = requests.get(url.address, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        
        watch_btn = soup.select_one("a.su-button[href*='nhlgamestoday']")
        if watch_btn:
            redirect_url = watch_btn.get("href")
            if redirect_url:
                r = requests.get(redirect_url, timeout=10).text
                soup = BeautifulSoup(r, "html.parser")
        
        for iframe in soup.select("iframe"):
            src = iframe.get("src")
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                if src in seen:
                    continue
                seen.add(src)
                name = urlparse(src).netloc
                if "ok.ru" in src:
                    name = "ok.ru"
                
                if "bysesukior.com" in src:
                    video_code = src.split("/e/")[-1].split("/")[0].split("?")[0]
                    decrypted_url = decrypt_bysesukior(video_code, src)
                    if decrypted_url and ".m3u8" in decrypted_url:
                        link = JetLink(decrypted_url, resolveurl=False, name="bysesukior.com")
                        link.headers = {"Referer": src, "Origin": "https://bysesukior.com", "User-Agent": self.user_agent}
                        link.inputstream = JetInputstreamFFmpegDirect.default()
                        links.append(link)
                    else:
                        links.append(JetLink(src, resolveurl=True, name=name))
                elif any(x in src for x in ["vidara.so", "vidara.to"]):
                    m3u8_link = m3u8_src.scan_page(src, headers={"User-Agent": self.user_agent, "Referer": src})
                    if m3u8_link:
                        m3u8_link.resolveurl = True
                        m3u8_link.name = "vidara.so"
                        links.append(m3u8_link)
                    else:
                        links.append(JetLink(src, resolveurl=True, name=name))
                elif "dailymotion.com" in src:
                    manifest = get_dailymotion_manifest(src, self.user_agent)
                    if manifest:
                        dm_headers = {"User-Agent": self.user_agent, "Referer": "https://www.dailymotion.com/", "Origin": "https://www.dailymotion.com"}
                        proxy_url, dm_headers = get_dailymotion_proxy(manifest, self.user_agent)
                        link = JetLink(proxy_url, resolveurl=False, name="dailymotion.com")
                        link.headers = dm_headers
                        link.inputstream = JetInputstreamFFmpegDirect.default()
                        links.append(link)
                    else:
                        links.append(JetLink(src, resolveurl=True, name=name))
                else:
                    links.append(JetLink(src, resolveurl=True, name=name))
        
        return links
        
class CollegeReplays(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["basketball-video.com/college-basketball"]
        self.name = "CollegeBasketball Replays"
    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        page = int(params['page'] if params is not None else 1)
        r = requests.get(f"https://{self.domains[0]}?page{page}").text
        soup = BeautifulSoup(r, "html.parser")
        games = soup.find_all(class_='short_item block_elem')
        for game in games:
            title = game.h3.a.text.replace('Full Game Replay ', '')
            if self.progress_update(progress, title):
                return items
            link = f"https://basketball-video.com{game.a['href']}"
            thumbnail = f"https://basketball-video.com{game.a.img['src']}"
            items.append(JetItem(title, links=[JetLink(link, links=True)], icon=thumbnail))
        if (next_page := soup.select_one("a.swchItem-next")) is not None:
            href = next_page.get("href", "")
            pages = re.findall(r'page[=]?(\d+)', href)
            if pages:
                page_num = pages[-1]
                items.append(JetItem(f"Page {page_num}", links=[], params={"page": page_num}))
        return items
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        ad_domains = ['doubleclick.net', 'adservice.google.com', 'googlesyndication.com',
                      'popads.net', 'popcash.net', 'adsterra.com', 'exoclick.com', 'juicyads.com',
                      'trafficjunky.net', 'mgid.com', 'taboola.com', 'outbrain.com', 'clkmon.com',
                      's.click', 'bit.ly', 'goo.gl', 'tinyurl.com', 't.co']
        video_hosts = ['dailymotion.com', 'ok.ru', 'bysesukior.com', 'vidara.so', 'vidara.to',
                       'youtube.com', 'youtu.be', 'vk.com', 'vkuser.net', 'luluvdo.com', 'luluvid.com',
                       'streamabc.com', 'vidlo.com', 'vidsrc', 'geo.dailymotion.com']

        def get_host(link):
            try:
                return urlparse(link).netloc.lower().split(':')[0]
            except:
                return ''

        def host_matches(link, hosts):
            host = get_host(link)
            if not host:
                return False
            for h in hosts:
                if host == h or host.endswith('.' + h):
                    return True
            return False

        def is_video_link(link):
            if host_matches(link, ad_domains):
                return False
            if host_matches(link, video_hosts):
                return True
            if '.m3u8' in link or '.mp4' in link:
                return True
            return False

        def follow_redirects(raw_link, depth=0):
            if depth > 5:
                return None
            link = raw_link
            if link.startswith('//'):
                link = f'https:{link}'
            link = link.replace('luluvid.com', 'luluvdo.com')
            if host_matches(link, ad_domains):
                return None
            if is_video_link(link):
                return link
            try:
                r2 = requests.get(link, headers=headers, timeout=self.timeout, allow_redirects=True).text
                _soup = BeautifulSoup(r2, 'html.parser')
                iframes = _soup.find_all('iframe')
                for iframe in iframes:
                    src = iframe.get('src', '')
                    if not src or host_matches(src, ad_domains):
                        continue
                    if src.startswith('//'):
                        src = 'https:' + src
                    if is_video_link(src):
                        return follow_redirects(src, depth + 1)
                for iframe in iframes:
                    src = iframe.get('src', '')
                    if not src or host_matches(src, ad_domains):
                        continue
                    if src.startswith('//'):
                        src = 'https:' + src
                    result = follow_redirects(src, depth + 1)
                    if result:
                        return result
            except:
                pass
            return None

        links = []
        headers = {"User-Agent": self.user_agent, "Referer": url.address}
        r = requests.get(url.address, headers=headers, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        paragraphs = soup.find_all('p')
        event_title = None
        for p in paragraphs:
            if p.find('a') is None and p.get_text(strip=True):
                event_title = p.get_text(strip=True)
            watch_link = p.find('a')
            if watch_link and watch_link.has_attr('href'):
                link = watch_link['href']
                if link.startswith('//'):
                    link = f'https:{link}'
                if host_matches(link, ad_domains):
                    continue
                if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors', 'guideanimaux.com']):
                    r2 = requests.get(link, headers=headers, timeout=10).text
                    _soup = BeautifulSoup(r2, 'html.parser')
                    iframes = _soup.find_all('iframe')
                    found = False
                    for iframe in iframes:
                        src = iframe.get('src', '')
                        if not src or host_matches(src, ad_domains):
                            continue
                        if src.startswith('//'):
                            src = 'https:' + src
                        if is_video_link(src):
                            link = src
                            found = True
                            break
                    if not found:
                        for iframe in iframes:
                            src = iframe.get('src', '')
                            if not src:
                                continue
                            if src.startswith('//'):
                                src = 'https:' + src
                            result = follow_redirects(src, 1)
                            if result:
                                link = result
                                found = True
                                break
                    if not found:
                        continue
                link = link.replace('luluvid.com', 'luluvdo.com')

                if host_matches(link, ad_domains):
                    continue

                if "bysesukior.com" in link:
                    video_code = link.split("/e/")[-1].split("/")[0].split("?")[0]
                    decrypted_url = decrypt_bysesukior(video_code, link)
                    if decrypted_url and ".m3u8" in decrypted_url:
                        links.append(JetLink(decrypted_url, resolveurl=True, name="bysesukior.com", headers={"Referer": link, "Origin": "https://bysesukior.com", "User-Agent": self.user_agent}, inputstream=JetInputstreamFFmpegDirect.default()))
                    else:
                        links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
                elif any(x in link for x in ["vidara.so", "vidara.to"]):
                    m3u8_link = m3u8_src.scan_page(link, headers={"User-Agent": self.user_agent, "Referer": link})
                    if m3u8_link:
                        m3u8_link.resolveurl = True
                        m3u8_link.name = "vidara.so"
                        links.append(m3u8_link)
                    else:
                        links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
                elif "dailymotion.com" in link:
                    manifest = get_dailymotion_manifest(link, self.user_agent)
                    if manifest:
                        dm_headers = {"User-Agent": self.user_agent, "Referer": "https://www.dailymotion.com/", "Origin": "https://www.dailymotion.com"}
                        proxy_url, dm_headers = get_dailymotion_proxy(manifest, self.user_agent)
                        links.append(JetLink(proxy_url, resolveurl=False, name="dailymotion.com", headers=dm_headers, inputstream=JetInputstreamFFmpegDirect.default()))
                    else:
                        links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
                else:
                    links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))

        all_srcs = []
        for button in soup.find_all(class_='su-button'):
            href = button.get('href', '')
            if href:
                all_srcs.append(('su-button', href))
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if src:
                all_srcs.append(('iframe', src))

        seen_hrefs = set()
        p_hrefs = set()
        for p in paragraphs:
            a = p.find('a')
            if a and a.has_attr('href'):
                p_hrefs.add(a['href'])
        for t in soup.find_all('a'):
            href = t.get('href', '')
            if not href or href in p_hrefs or href in seen_hrefs:
                continue
            if href.startswith('#') or href.startswith('javascript'):
                continue
            if href.startswith('/'):
                href = 'https://basketball-video.com' + href
            elif href.startswith('//'):
                href = 'https:' + href
            elif not href.startswith('http'):
                continue
            text = t.get_text(strip=True).lower()
            href_lower = href.lower()
            if host_matches(href, ad_domains):
                continue
            if any(x in href_lower for x in ['nbaontv', 'gamesontvtoday', 'nbatraderumors']):
                seen_hrefs.add(href)
                all_srcs.append(('a-tag', href))
            elif any(w in text for w in ['watch', 'stream', 'play', 'live', 'replay', 'full game']):
                if 'basketball-video.com' in href_lower:
                    parts = href.rstrip('/').split('/')
                    if len(parts) >= 4 and any(kw in parts[-1].lower() for kw in ['full-game', 'replay', 'playoffs', 'finals']):
                        seen_hrefs.add(href)
                        all_srcs.append(('a-tag', href))

        for src_type, raw_src in all_srcs:
            if not raw_src or host_matches(raw_src, ad_domains):
                continue
            if raw_src.startswith('//'):
                raw_src = 'https:' + raw_src
            raw_src = raw_src.replace('luluvid.com', 'luluvdo.com')

            resolved = None
            if is_video_link(raw_src):
                resolved = raw_src
            elif any(x in raw_src for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors', 'guideanimaux.com']):
                try:
                    r2 = requests.get(raw_src, headers=headers, timeout=10).text
                    _soup = BeautifulSoup(r2, 'html.parser')
                    iframes = _soup.find_all('iframe')
                    for iframe in iframes:
                        src = iframe.get('src', '')
                        if not src or host_matches(src, ad_domains):
                            continue
                        if src.startswith('//'):
                            src = 'https:' + src
                        if is_video_link(src):
                            resolved = src
                            break
                    if not resolved:
                        for iframe in iframes:
                            src = iframe.get('src', '')
                            if not src:
                                continue
                            if src.startswith('//'):
                                src = 'https:' + src
                            result = follow_redirects(src, 1)
                            if result:
                                resolved = result
                                break
                except:
                    pass
            else:
                resolved = follow_redirects(raw_src, 1)

            if not resolved or host_matches(resolved, ad_domains):
                continue

            link = resolved
            if "bysesukior.com" in link:
                video_code = link.split("/e/")[-1].split("/")[0].split("?")[0]
                decrypted_url = decrypt_bysesukior(video_code, link)
                if decrypted_url and ".m3u8" in decrypted_url:
                    links.append(JetLink(decrypted_url, resolveurl=True, name="bysesukior.com", headers={"Referer": link, "Origin": "https://bysesukior.com", "User-Agent": self.user_agent}, inputstream=JetInputstreamFFmpegDirect.default()))
                else:
                    links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
            elif any(x in link for x in ["vidara.so", "vidara.to"]):
                m3u8_link = m3u8_src.scan_page(link, headers={"User-Agent": self.user_agent, "Referer": link})
                if m3u8_link:
                    m3u8_link.resolveurl = True
                    m3u8_link.name = "vidara.so"
                    links.append(m3u8_link)
                else:
                    links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
            elif "dailymotion.com" in link:
                manifest = get_dailymotion_manifest(link, self.user_agent)
                if manifest:
                    dm_headers = {"User-Agent": self.user_agent, "Referer": "https://www.dailymotion.com/", "Origin": "https://www.dailymotion.com"}
                    proxy = get_stream_proxy("dailymotion", dm_headers, options={"cache_manifest": True, "manifest_ttl": 3600})
                    proxy_url = proxy.get_proxy_url(manifest, dm_headers)
                    links.append(JetLink(proxy_url, resolveurl=False, name="dailymotion.com", headers=dm_headers, inputstream=JetInputstreamFFmpegDirect.default()))
                else:
                    links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
            else:
                links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
        return links
    

class WNBAReplays(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["basketball-video.com/wnba-full-games"]
        self.name = "WNBA Replays"
    
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        page = int(params['page'] if params is not None else 1)
        r = requests.get(f"https://{self.domains[0]}?page{page}").text
        soup = BeautifulSoup(r, "html.parser")
        games = soup.find_all(class_='short_item block_elem')
        for game in games:
            if not game.h3 or not game.h3.a:
                continue
            title = game.h3.a.text.replace('Full Game Replay ', '')
            if self.progress_update(progress, title):
                return items
            if not game.a:
                continue
            link = f"https://basketball-video.com{game.a['href']}"
            thumbnail = f"https://basketball-video.com{game.a.img['src']}" if game.a.img else None
            items.append(JetItem(title, links=[JetLink(link, links=True)], icon=thumbnail))
        if (next_page := soup.select_one("a.swchItem-next")) is not None:
            href = next_page.get("href", "")
            pages = re.findall(r'page[=]?(\d+)', href)
            if pages:
                page_num = pages[-1]
                items.append(JetItem(f"Page {page_num}", links=[], params={"page": page_num}))
        return items
    
def get_links(self, url: JetLink) -> List[JetLink]:
        links = []
        seen = set()
        headers = {"User-Agent": self.user_agent, "Referer": url.address}
        r = requests.get(url.address, headers=headers, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")

        video_hosts = ['dailymotion.com', 'ok.ru', 'bysesukior.com', 'vidara.so', 'vidara.to', 'youtube.com', 'youtu.be', 'vk.com', 'vkuser.net', 'luluvdo.com', 'luluvid.com', 'streamabc.com', 'vidlo.com', 'vidsrc', 'geo.dailymotion.com']
        ad_domains = ['google.com', 'doubleclick.net', 'adservice.google.com', 'googlesyndication.com', 'popads.net', 'popcash.net', 'adsterra.com', 'exoclick.com', 'juicyads.com', 'trafficjunky.net', 'mgid.com', 'taboola.com', 'outbrain.com', 'clkmon.com', 's.click', 'bit.ly', 'goo.gl', 'tinyurl.com', 't.co']

        def get_host(link):
            try:
                return urlparse(link).netloc.lower().split(':')[0]
            except:
                return ''

        def host_matches(link, hosts):
            host = get_host(link)
            if not host:
                return False
            for h in hosts:
                if host == h or host.endswith('.' + h):
                    return True
            return False

        def is_video_link(link):
            if host_matches(link, ad_domains):
                return False
            if host_matches(link, video_hosts):
                return True
            if '.m3u8' in link or '.mp4' in link:
                return True
            return False

        def follow_redirects(raw_link, depth=0):
            if depth > 5:
                return None
            link = raw_link
            if link.startswith('//'):
                link = f'https:{link}'
            link = link.replace('luluvid.com', 'luluvdo.com')
            if host_matches(link, ad_domains):
                return None
            if is_video_link(link):
                return link
            try:
                r2 = requests.get(link, headers=headers, timeout=self.timeout, allow_redirects=True).text
                _soup = BeautifulSoup(r2, "html.parser")
                iframes = _soup.find_all("iframe")
                for iframe in iframes:
                    src = iframe.get('src', '')
                    if not src:
                        continue
                    if src.startswith('//'):
                        src = 'https:' + src
                    if host_matches(src, ad_domains):
                        continue
                    if is_video_link(src):
                        return follow_redirects(src, depth + 1)
                for iframe in iframes:
                    src = iframe.get('src', '')
                    if not src:
                        continue
                    if src.startswith('//'):
                        src = 'https:' + src
                    if host_matches(src, ad_domains):
                        continue
                    result = follow_redirects(src, depth + 1)
                    if result:
                        return result
            except:
                pass
            return None

        all_srcs = []
        for button in soup.find_all(class_='su-button'):
            href = button.get('href', '')
            all_srcs.append(href)
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            all_srcs.append(src)

        for raw_src in all_srcs:
            if not raw_src:
                continue
            link = follow_redirects(raw_src)
            if not link:
                continue
            if link in seen:
                continue
            seen.add(link)
            host = urlparse(link).netloc
            name = host.split('.')[0] if host else 'unknown'

            if "bysesukior.com" in link:
                video_code = link.split("/e/")[-1].split("/")[0].split("?")[0]
                decrypted_url = decrypt_bysesukior(video_code, link)
                if decrypted_url and ".m3u8" in decrypted_url:
                    links.append(JetLink(decrypted_url, resolveurl=True, name="bysesukior.com", headers={"Referer": link, "Origin": "https://bysesukior.com", "User-Agent": self.user_agent}, inputstream=JetInputstreamFFmpegDirect.default()))
                else:
                    links.append(JetLink(link, resolveurl=True, name=name))
            elif any(x in link for x in ["vidara.so", "vidara.to"]):
                m3u8_link = m3u8_src.scan_page(link, headers={"User-Agent": self.user_agent, "Referer": link})
                if m3u8_link:
                    m3u8_link.resolveurl = True
                    m3u8_link.name = "vidara.so"
                    links.append(m3u8_link)
                else:
                    links.append(JetLink(link, resolveurl=True, name=name))
            elif "dailymotion.com" in link:
                manifest = get_dailymotion_manifest(link, self.user_agent)
                if manifest:
                    dm_headers = {"User-Agent": self.user_agent, "Referer": "https://www.dailymotion.com/", "Origin": "https://www.dailymotion.com"}
                    proxy = get_stream_proxy("dailymotion", dm_headers, options={"cache_manifest": True, "manifest_ttl": 3600})
                    proxy_url = proxy.get_proxy_url(manifest, dm_headers)
                    links.append(JetLink(proxy_url, resolveurl=False, name="dailymotion.com", headers=dm_headers, inputstream=JetInputstreamFFmpegDirect.default()))
                else:
                    links.append(JetLink(link, resolveurl=True, name=name))
            else:
                links.append(JetLink(link, resolveurl=True, name=name))
        return links
        