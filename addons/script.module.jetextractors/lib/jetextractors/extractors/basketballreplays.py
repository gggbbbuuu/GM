from ..models import *
from ..util import m3u8_src
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import base64
import json
import re

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

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
        links = []
        headers = {"User-Agent": self.user_agent, "Referer": url.address}
        r = requests.get(url.address, headers=headers, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        paragraphs = soup.find_all('p')
        event_title = None
        for p in paragraphs:
            # If paragraph contains only text, treat as event title
            if p.find('a') is None and p.get_text(strip=True):
                event_title = p.get_text(strip=True)
            # Watch link
            watch_link = p.find('a')
            if watch_link and watch_link.has_attr('href'):
                link = watch_link['href']
                if link.startswith('//'):
                    link = f'https:{link}'
                if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors']):
                    r2 = requests.get(link, headers=headers, timeout=10).text
                    _soup = BeautifulSoup(r2, 'html.parser')
                    iframe = _soup.find('iframe')
                    if iframe:
                        link = iframe['src']
                    else:
                        continue
                link = link.replace('luluvid.com', 'luluvdo.com')
                
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
        headers = {"User-Agent": self.user_agent, "Referer": url.address}
        r = requests.get(url.address, headers=headers, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        buttons = soup.find_all(class_='su-button')
        for button in buttons:
            link = button['href']
            if link.startswith('//'):
                link = f'https:{link}'
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors']):
                r = requests.get(link, headers=headers, timeout=self.timeout).text
                _soup = BeautifulSoup(r, 'html.parser')
                iframe = _soup.find('iframe')
                if iframe:
                    link = iframe['src']
                else:
                    continue
            link = link.replace('luluvid.com', 'luluvdo.com')
            title = link.split('/')[2]
            
            if "bysesukior.com" in link:
                    video_code = link.split("/e/")[-1].split("/")[0].split("?")[0]
                    decrypted_url = decrypt_bysesukior(video_code, link)
                    if decrypted_url and ".m3u8" in decrypted_url:
                        links.append(JetLink(decrypted_url, resolveurl=True, name="bysesukior.com", headers={"Referer": link, "Origin": "https://bysesukior.com", "User-Agent": self.user_agent}, inputstream=JetInputstreamFFmpegDirect.default()))
                    else:
                        links.append(JetLink(link, resolveurl=True, name=title))
            elif any(x in link for x in ["vidara.so", "vidara.to"]):
                    m3u8_link = m3u8_src.scan_page(link, headers={"User-Agent": self.user_agent, "Referer": link})
                    if m3u8_link:
                        m3u8_link.resolveurl = True
                        m3u8_link.name = "vidara.so"
                        links.append(m3u8_link)
                    else:
                        links.append(JetLink(link, resolveurl=True, name=title))
            else:
                links.append(JetLink(link, resolveurl=True, name=title))
        
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            link = iframe['src']
            if link.startswith('//'):
                link = f'https:{link}'
            if any(x in link for x in ['nfl-replays', 'nfl-video', 'basketball-video', 'nbaontv', 'gamesontvtoday', 'nbatraderumors']):
                r = requests.get(link, headers=headers, timeout=self.timeout).text
                _soup = BeautifulSoup(r, 'html.parser')
                iframe = _soup.find('iframe')
                if iframe:
                    link = iframe['src']
                else:
                    continue
            link = link.replace('luluvid.com', 'luluvdo.com')
            title = link.split('/')[2]
            
            if "bysesukior.com" in link:
                    video_code = link.split("/e/")[-1].split("/")[0].split("?")[0]
                    decrypted_url = decrypt_bysesukior(video_code, link)
                    if decrypted_url and ".m3u8" in decrypted_url:
                        links.append(JetLink(decrypted_url, resolveurl=True, name="bysesukior.com", headers={"Referer": link, "Origin": "https://bysesukior.com", "User-Agent": self.user_agent}, inputstream=JetInputstreamFFmpegDirect.default()))
                    else:
                        links.append(JetLink(link, resolveurl=True, name=title))
            elif any(x in link for x in ["vidara.so", "vidara.to"]):
                    m3u8_link = m3u8_src.scan_page(link, headers={"User-Agent": self.user_agent, "Referer": link})
                    if m3u8_link:
                        m3u8_link.resolveurl = True
                        m3u8_link.name = "vidara.so"
                        links.append(m3u8_link)
                    else:
                        links.append(JetLink(link, resolveurl=True, name=title))
            else:
                links.append(JetLink(link, resolveurl=True, name=title))
        return links
        