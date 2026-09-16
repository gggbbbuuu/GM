from ..models import *
from ..util import m3u8_src
from ..util.stream_proxy import get_stream_proxy
from .._core import fetch_page, get_session, _BROWSER_UA
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode, parse_qs
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

def get_dailymotion_proxy(manifest, dm_headers=None, master_url=None):
    if dm_headers is None:
        dm_headers = {"User-Agent": _BROWSER_UA, "Referer": "https://www.dailymotion.com/", "Origin": "https://www.dailymotion.com"}
    proxy = get_stream_proxy("dailymotion", dm_headers, options={"cache_manifest": True, "manifest_ttl": 3600, "browser_tls": True, "prefetch_segments": True, "upstream_keep_alive": True, "use_urllib": True, "add_icy_metadata": False})
    if isinstance(manifest, bytes):
        proxy_url = proxy.cache_manifest_bytes(manifest, master_url or "http://prepopulated.local", dm_headers)
        debug_log(f"[DM] Proxy URL (cached manifest): {proxy_url}", xbmc.LOGINFO)
        return proxy_url, dm_headers
    proxy_url = proxy.get_proxy_url(manifest, dm_headers)
    debug_log(f"[DM] Proxy URL (upstream: {manifest[:200]}): {proxy_url}", xbmc.LOGINFO)
    return proxy_url, dm_headers

def get_dailymotion_manifest(dailymotion_url, user_agent):
    """Returns (master_url_or_bytes, dm_headers) or None on failure.

    Uses the mlblive.py cookie-based approach: warmup geo.dailymotion.com,
    visit embed page for cookies, call metadata API, then fetch the master
    URL WITH session cookies — DailyMotion's CDN validates the signed URL
    against visitor cookies (dmV1st).
    """
    try:
        match = re.search(r'[/.]video/([a-z0-9]+)|video=([a-z0-9]+)', dailymotion_url)
        if not match:
            debug_log(f"[DM] No video ID match in: {dailymotion_url}", xbmc.LOGWARNING)
            return None
        vid = match.group(1) or match.group(2)
        debug_log(f"[DM] Extracted video ID: {vid}", xbmc.LOGINFO)

        # Use a fresh requests session (not JetHttpClient) to avoid stale cookies
        import requests
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
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Origin': 'https://geo.dailymotion.com',
            'Referer': 'https://geo.dailymotion.com/',
        }
        session.headers.update(browser_headers)
        session.cookies.set('ff', 'on')

        # Warmup request to geo.dailymotion.com to get cookies
        try:
            session.get('https://geo.dailymotion.com/', timeout=10)
        except Exception as e:
            debug_log(f"[DM] Warmup geo.dailymotion.com network error: {type(e).__name__}: {e}", xbmc.LOGWARNING)
        debug_log(f"[DM] Warmup cookies: {session.cookies.get_dict()}", xbmc.LOGINFO)

        # Visit embed page to get more cookies
        try:
            embed_resp = session.get(f'https://www.dailymotion.com/embed/video/{vid}', timeout=10)
        except Exception as e:
            debug_log(f"[DM] Embed page network error: {type(e).__name__}: {e}", xbmc.LOGWARNING)
        debug_log(f"[DM] After embed page cookies: {session.cookies.get_dict()}", xbmc.LOGINFO)

        # Call metadata API with query parameters (like the browser does)
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
        try:
            r = session.get(meta_url, params=params, timeout=10)
        except Exception as e:
            debug_log(f"[DM] Metadata API network error: {type(e).__name__}: {e}", xbmc.LOGWARNING)
            return None
        debug_log(f"[DM] Metadata API status: {r.status_code}", xbmc.LOGINFO)
        if r.status_code != 200:
            debug_log(f"[DM] Metadata API failed, body: {r.text[:300]}", xbmc.LOGWARNING)
            return None
        data = r.json()
        debug_log(f"[DM] Metadata response: {json.dumps(data, indent=2)[:2000]}", xbmc.LOGINFO)

        qualities = data.get("qualities", {})
        auto = qualities.get("auto", [])
        debug_log(f"[DM] qualities keys: {list(qualities.keys())}, auto count: {len(auto)}", xbmc.LOGINFO)
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
        debug_log(f"[DM] Returning master URL for stream proxy fetch: {len(cookies)} cookies", xbmc.LOGINFO)
        return (master_url, dm_headers)
    except Exception as e:
        debug_log(f"[DM] get_dailymotion_manifest error: {type(e).__name__}: {e}", xbmc.LOGWARNING)
        return None

def decrypt_bysesukior(video_code, referer):
    try:
        api_url = f"https://bysesukior.com/api/videos/{video_code}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": referer}
        r = get_session().get(api_url, headers=headers, timeout=10)
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
        except Exception as e:
            debug_log(f"[decrypt_bysesukior] cryptography module import/decode failed, trying Cryptodome: {type(e).__name__}: {e}", xbmc.LOGDEBUG)
            # Fallback to Cryptodome (available in Kodi)
            try:
                from Cryptodome.Cipher import AES
                # AES-GCM: last 16 bytes are the auth tag
                ciphertext = payload[:-16]
                auth_tag = payload[-16:]
                cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                plaintext = cipher.decrypt_and_verify(ciphertext, auth_tag)
            except Exception as e:
                debug_log(f"[decrypt_bysesukior] inner decrypt error: {type(e).__name__}: {e}", xbmc.LOGWARNING)
                return None
        
        result = plaintext.decode("utf-8")
        j = json.loads(result)
        sources = j.get("sources", [])
        for source in sources:
            if ".m3u8" in source.get("url", ""):
                return source["url"]
        return None
    except Exception as e:
        debug_log(f"[decrypt_bysesukior] outer error: {type(e).__name__}: {e}", xbmc.LOGWARNING)
        return None

class BasketballReplays(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["basketballreplays.net"]
        self.name = "BasketballReplays"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = fetch_page(f"https://{self.domains[0]}/?page={params['page'] if params is not None else 1}")
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
        r = fetch_page(url.address)
        soup = BeautifulSoup(r, "html.parser")
        
        watch_btn = soup.select_one("a.su-button[href*='nhlgamestoday']")
        if watch_btn:
            redirect_url = watch_btn.get("href")
            if redirect_url:
                r = fetch_page(redirect_url)
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
                    result = get_dailymotion_manifest(src, self.user_agent)
                    if result:
                        manifest_bytes, dm_headers = result
                        proxy_url, _ = get_dailymotion_proxy(manifest_bytes, dm_headers)
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
        r = fetch_page(f"https://{self.domains[0]}?page{page}")
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
                r2 = fetch_page(link, referer=url.address)
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
        r = fetch_page(url.address, referer=url.address)
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
                    r2 = fetch_page(link, referer=url.address)
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
                    result = get_dailymotion_manifest(link, self.user_agent)
                    if result:
                        manifest_bytes, dm_headers = result
                        proxy_url, _ = get_dailymotion_proxy(manifest_bytes, dm_headers)
                        links.append(JetLink(proxy_url, resolveurl=False, name="dailymotion.com", headers=dm_headers, inputstream=JetInputstreamFFmpegDirect.default()))
                    else:
                        links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))
                else:
                    links.append(JetLink(link, resolveurl=True, name=event_title or 'Unknown Event'))

        # Second pass: process su-buttons


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
                    r2 = fetch_page(raw_src, referer=url.address)
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
                result = get_dailymotion_manifest(link, self.user_agent)
                if result:
                    manifest_bytes, dm_headers = result
                    proxy = get_stream_proxy("dailymotion", dm_headers, options={"cache_manifest": True, "manifest_ttl": 3600, "browser_tls": True, "prefetch_segments": True, "upstream_keep_alive": True, "use_urllib": True, "add_icy_metadata": False})
                    proxy_url = proxy.get_proxy_url(manifest_bytes, dm_headers)
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
        r = fetch_page(f"https://{self.domains[0]}?page{page}")
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
        r = fetch_page(url.address, referer=url.address)
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
                r2 = fetch_page(link, referer=url.address)
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
                result = get_dailymotion_manifest(link, self.user_agent)
                if result:
                    manifest_bytes, dm_headers = result
                    proxy = get_stream_proxy("dailymotion", dm_headers, options={"cache_manifest": True, "manifest_ttl": 3600, "browser_tls": True, "prefetch_segments": True, "upstream_keep_alive": True, "use_urllib": True, "add_icy_metadata": False})
                    proxy_url = proxy.get_proxy_url(manifest_bytes, dm_headers)
                    links.append(JetLink(proxy_url, resolveurl=False, name="dailymotion.com", headers=dm_headers, inputstream=JetInputstreamFFmpegDirect.default()))
                else:
                    links.append(JetLink(link, resolveurl=True, name=name))
            else:
                links.append(JetLink(link, resolveurl=True, name=name))
        return links
        