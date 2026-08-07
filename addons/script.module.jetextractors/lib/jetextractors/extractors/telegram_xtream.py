import re
import time
import base64
import requests
import threading
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import *
from ..tools import debug_log, is_telegramxtream_enabled
from ..util.xtream import validate_xtream_credentials, get_xtream_channels, build_xtream_stream_url
from ..util.mac import validate_mac_credentials, get_mac_channels, MacServer
from ..util.TelegramStore import (
    load_channels, add_portal_credentials, add_channels,
    search_channels, get_portal_credentials, filter_channels,
    get_telegram_sources, get_telegram_pointer, set_telegram_pointer,
    is_portal_excluded, add_excluded_portal, remove_excluded_portal, get_excluded_portals,
    add_mac_portal_credentials, get_mac_portal_credentials, get_all_mac_portals,
    get_all_cached_portals, remove_portal_channels, remove_portal_credentials,
    remove_mac_portal_credentials,
    get_last_scrape_ts, set_last_scrape_ts,
    MAX_POSTS_PER_SYNC,
)
from ..util.stream_proxy import get_stream_proxy

SCRAPE_INTERVAL = 6 * 3600
_scrape_lock = threading.Lock()
_last_scrape_ts = None

TELEGRAM_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/77.0.3865.90 Safari/537.36 TelegramBot (like TwitterBot)"
)

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

URL_LINE = re.compile(r'(?i)^\W*(?:[\w ]{0,20}?[:=]\s*)?(https?://\S+)')
INLINE_PAIR = re.compile(r'(?i)\buser(?:name)?\s*(?::\s*|=\s+)(\S+).*?\bpass(?:word)?\s*(?::\s*|=\s+)(\S+)')
EMOJI_PAIR = re.compile(r"[\U0001F464\U0001F468]\s+(.+?)\s*[\U0001F510\U0001F511]\s*(.+)")
USER_LABEL = re.compile(r'(?i)\buser(?:name)?\s*[:=]\s*(\S+)')
PASS_LABEL = re.compile(r'(?i)\bpass(?:word)?\s*[:=]\s*(\S+)')
MAC_ADDRESS = re.compile(r'([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}')
MAC_LINE = re.compile(r'(?i)\b(?:mac|stb)\s*[:=]\s*([0-9A-Fa-f]{2}[:\-]{1}[0-9A-Fa-f]{2}[:\-]{1}[0-9A-Fa-f]{2}[:\-]{1}[0-9A-Fa-f]{2}[:\-]{1}[0-9A-Fa-f]{2}[:\-]{1}[0-9A-Fa-f]{2})')


def _looks_like_credential(token: str) -> bool:
    return bool(token) and " " not in token and 2 <= len(token) <= 64


def _clean_address(raw_url: str) -> str:
    try:
        parsed = urlparse(raw_url)
        host = parsed.hostname
        if not host:
            return ""
        scheme = parsed.scheme or "http"
        return f"{scheme}://{host}:{parsed.port}" if parsed.port else f"{scheme}://{host}"
    except Exception:
        return ""


def parse_telegram_mac_credentials(text: str) -> list:
    """Parse Telegram post text for Mac Codes credentials.

    Returns list of (address, mac, username, password) tuples.
    username/password may be None if not found.
    Handles formats like:
        Portal  :  http://server:port/c/MAC Addr:  00:1A:2B:3C:4D:5EExp date:  ...
    Note: Telegram often strips newlines, so all fields may be on one line.
    """
    results = []

    # Pattern: Split by "Portal" and extract URL + MAC from each block
    # Example block: "  http://vpn.tvrhino.world:80/c/MAC Addr:  00:1A:79:C4:E7:ECExp date:  ..."
    blocks = re.split(r'(?i)portal\s*[:=]', text)
    for block in blocks[1:]:  # Skip first empty part
        # Extract URL - stop at "MAC" or end of URL-like characters
        # The URL ends with a path like /c/ or /c
        url_match = re.search(r'(https?://[^\s<>]+?)(?:\s*(?:MAC|Exp|Channel|Status|\Z))', block, re.IGNORECASE)
        if not url_match:
            # Try simpler pattern - just http(s) until whitespace or MAC
            url_match = re.search(r'(https?://\S+?)(?:MAC)', block, re.IGNORECASE)
        if not url_match:
            url_match = re.search(r'(https?://[^\s<>]+)', block)

        if not url_match:
            continue
        addr = _clean_address(url_match.group(1))
        if not addr:
            continue

        # Extract MAC address
        mac_match = re.search(r'([0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2}[:\-][0-9A-Fa-f]{2})', block)
        if mac_match:
            mac = mac_match.group(1).upper().replace("-", ":")
            debug_log(f"[TelegramXtream] Mac parser: found pair - {addr}, {mac}")
            results.append((addr, mac, None, None))

    debug_log(f"[TelegramXtream] Mac parser: returning {len(results)} credential sets")
    return results


def parse_telegram_credentials(text: str) -> list:
    address = ""
    creds = []
    pending_user = None

    for raw_url in re.findall(r'https?://[^\s<>"\']+', text):
        raw_url = raw_url.replace('&amp;', '&').rstrip('.,;)]}')
        parsed = urlparse(raw_url)
        q = parse_qs(parsed.query)
        un, pw = q.get("username"), q.get("password")
        if un and pw:
            creds.append((_clean_address(raw_url), un[0], pw[0]))

    for line in text.splitlines():
        line = line.strip()
        if not line:
            pending_user = None
            continue
        if "t.me/" in line or "kodi.tv/" in line:
            continue

        low = line.lower()

        if "user" in low and "pass" in low:
            m = INLINE_PAIR.search(line)
            if m:
                u, p = m.group(1), m.group(2)
                if _looks_like_credential(u) and _looks_like_credential(p):
                    creds.append((address, u, p))
            pending_user = None
            continue

        if "://" in line:
            m = URL_LINE.match(line)
            if m:
                parsed = urlparse(m.group(1))
                q = parse_qs(parsed.query)
                un, pw = q.get("username"), q.get("password")
                if un and pw:
                    creds.append((_clean_address(m.group(1)), un[0], pw[0]))
                else:
                    addr = _clean_address(m.group(1))
                    if addr:
                        address = addr
            pending_user = None
            continue

        em = EMOJI_PAIR.findall(line)
        if em:
            u, p = em[0][0].strip(), em[0][1].strip()
            if _looks_like_credential(u) and _looks_like_credential(p):
                creds.append((address, u, p))
            pending_user = None
            continue

        um, pm = USER_LABEL.search(line), PASS_LABEL.search(line)
        if um and not pm:
            v = um.group(1)
            pending_user = v if _looks_like_credential(v) else None
            continue
        if pm and not um:
            v = pm.group(1)
            if pending_user and _looks_like_credential(v):
                creds.append((address, pending_user, v))
            pending_user = None
            continue

    return [(a, u, p) for (a, u, p) in creds if a]


def _get_latest_post(channel: str):
    """Get newest post ID from a Telegram channel. Returns None on failure."""
    try:
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        resp = requests.get(f"https://t.me/s/{channel}", headers={"User-Agent": ua}, timeout=10)
        ids = re.findall(rf'data-post="{re.escape(channel)}/(\d+)"', resp.text)
        return max((int(i) for i in ids), default=None)
    except Exception as e:
        debug_log(f"[TelegramXtream] Could not get latest post for {channel}: {e}")
        return None

def _fetch_telegram_text(source: str) -> str:
    urls = [source]
    if "?" not in source:
        urls.insert(0, f"{source}?embed=1")

    for fetch_url in urls:
        resp = requests.get(fetch_url, headers={"User-Agent": TELEGRAM_UA}, timeout=10)
        if 'Please open Telegram' in resp.text or 'tgme_widget_message_error' in resp.text:
            continue
        soup = BeautifulSoup(resp.text, 'html.parser')
        divs = soup.find_all('div', class_=lambda c: c and 'tgme_widget_message_text' in c)
        if divs:
            return "\n".join(div.get_text("\n") for div in divs)
        desc = soup.find('meta', {'property': 'og:description'})
        if desc and desc.get('content'):
            return desc.get('content')

    match = re.search(r't\.me/([a-zA-Z0-9_]+)/(\d+)', source)
    if match:
        channel = match.group(1)
        latest = _get_latest_post(channel)
        if latest:
            return _fetch_telegram_text(f"https://t.me/{channel}/{latest}")

    return ""


def scrape_telegram_sources(progress=None) -> int:
    """Scrape configured Telegram sources and cache channels.

    Phase 1: Parse all posts, collect unique portals (fast - no API calls).
    Phase 2: Validate each portal once, fetch channels from valid ones only.
    Supports both Xtream Codes and Mac Codes credentials.
    """
    new_count = 0
    sources = get_telegram_sources()

    debug_log(f"[TelegramXtream] Scraping {len(sources)} sources: {sources}")

    xtream_portals_to_check = {}
    mac_portals_to_check = {}

    for source in sources:
        try:
            match = re.search(r"t\.me/([^/]+)/(\d+)", source)
            if not match:
                debug_log(f"[TelegramXtream] Skipping invalid source URL: {source}")
                continue

            channel = match.group(1)
            start_post = int(match.group(2))

            latest = _get_latest_post(channel)
            if latest is None:
                debug_log(f"[TelegramXtream] Could not get latest post for {channel}, skipping")
                continue

            pointer = get_telegram_pointer(channel)
            if pointer is not None:
                begin = pointer + 1
            else:
                begin = start_post

            if begin > latest:
                debug_log(f"[TelegramXtream] Channel {channel} already up to date (pointer={pointer}, latest={latest})")
                continue

            end = min(begin + MAX_POSTS_PER_SYNC - 1, latest)
            debug_log(f"[TelegramXtream] Channel {channel}: scanning posts {begin}..{end} (latest={latest})")

            for post_id in range(begin, end + 1):
                post_url = f"https://t.me/{channel}/{post_id}"
                try:
                    text = _fetch_telegram_text(post_url)
                    if not text:
                        debug_log(f"[TelegramXtream] Post {post_id}: no message content")
                        continue

                    # Parse Mac credentials
                    mac_creds = parse_telegram_mac_credentials(text)
                    if mac_creds:
                        debug_log(f"[TelegramXtream] Post {post_id}: found {len(mac_creds)} Mac credentials")
                    else:
                        debug_log(f"[TelegramXtream] Post {post_id}: no Mac credentials found")

                    for addr, mac, user, pwd in mac_creds:
                        if addr not in mac_portals_to_check:
                            mac_portals_to_check[addr] = []
                        mac_entry = (mac, user, pwd)
                        if mac_entry not in mac_portals_to_check[addr]:
                            mac_portals_to_check[addr].append(mac_entry)

                    # Parse Xtream credentials
                    creds = parse_telegram_credentials(text)
                    if creds:
                        debug_log(f"[TelegramXtream] Post {post_id}: found {len(creds)} Xtream credentials")

                    for addr, user, pwd in creds:
                        if addr not in xtream_portals_to_check:
                            xtream_portals_to_check[addr] = []
                        pair = (user, pwd)
                        if pair not in xtream_portals_to_check[addr]:
                            xtream_portals_to_check[addr].append(pair)

                except Exception as e:
                    debug_log(f"[TelegramXtream] Error parsing post {post_id}: {e}")

            set_telegram_pointer(channel, end)
            debug_log(f"[TelegramXtream] Channel {channel} pointer updated to {end}")

        except Exception as e:
            debug_log(f"[TelegramXtream] Source scrape error: {e}")

    debug_log(f"[TelegramXtream] Phase 1 done: {len(xtream_portals_to_check)} Xtream portals, {len(mac_portals_to_check)} Mac portals")

    # Phase 1.5: Re-validate existing cached portals (remove dead ones)
    cached_portals = get_all_cached_portals()
    debug_log(f"[TelegramXtream] Re-validating {len(cached_portals)} cached portals")
    dead_portals = []
    for cached in cached_portals:
        portal = cached.get("portal", "")
        channel_type = cached.get("channel_type", "xtream")
        user = cached.get("username", "")
        pwd = cached.get("password", "")
        mac = cached.get("mac", "")

        if not portal or is_portal_excluded(portal):
            continue

        try:
            if channel_type == "mac" and mac:
                valid, _ = validate_mac_credentials(portal, mac)
            else:
                valid, _ = validate_xtream_credentials(portal, user, pwd)

            if not valid:
                debug_log(f"[TelegramXtream] Cached portal DEAD: {portal} ({channel_type})")
                dead_portals.append((portal, channel_type, mac))
            else:
                debug_log(f"[TelegramXtream] Cached portal OK: {portal}")
        except Exception as e:
            debug_log(f"[TelegramXtream] Error re-validating {portal}: {e}")
            dead_portals.append((portal, channel_type, mac))

    # Remove dead portals from cache
    for portal, channel_type, mac in dead_portals:
        remove_portal_channels(portal, channel_type)
        if channel_type == "mac":
            remove_mac_portal_credentials(portal)
        else:
            remove_portal_credentials(portal)
        debug_log(f"[TelegramXtream] Removed dead portal: {portal}")

    if dead_portals:
        debug_log(f"[TelegramXtream] Removed {len(dead_portals)} dead portals from cache")
    else:
        debug_log(f"[TelegramXtream] All cached portals still alive")

    # Phase 2a: Validate Xtream portals and fetch channels (threaded)
    def _process_xtream_portal(addr, user, pwd):
        try:
            debug_log(f"[TelegramXtream] Validating Xtream: {addr}")
            valid, result = validate_xtream_credentials(addr, user, pwd)
            debug_log(f"[TelegramXtream] Xtream validation result: valid={valid}")
            if valid:
                debug_log(f"[TelegramXtream] Valid Xtream credentials for {addr}")
                add_portal_credentials(addr, user, pwd)
                channels = get_xtream_channels(addr, user, pwd)
                debug_log(f"[TelegramXtream] Got {len(channels)} Xtream channels from {addr}")
                kept = filter_channels(channels)
                debug_log(f"[TelegramXtream] Kept {len(kept)} after filter from {addr}")
                for ch in kept:
                    ch["username"] = user
                    ch["password"] = pwd
                add_channels(kept, addr, channel_type="xtream")
                return len(kept)
            else:
                debug_log(f"[TelegramXtream] Invalid Xtream credentials for {addr}")
        except Exception as e:
            debug_log(f"[TelegramXtream] Xtream validation error for {addr}: {e}")
        return 0

    xtream_tasks = []
    for addr, cred_pairs in xtream_portals_to_check.items():
        if is_portal_excluded(addr):
            debug_log(f"[TelegramXtream] Skipping excluded portal: {addr}")
            continue
        for user, pwd in cred_pairs:
            xtream_tasks.append((addr, user, pwd))

    max_workers = min(4, len(xtream_tasks)) if xtream_tasks else 1
    debug_log(f"[TelegramXtream] Scraping {len(xtream_tasks)} Xtream portals with {max_workers} threads")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_xtream_portal, addr, user, pwd): addr for addr, user, pwd in xtream_tasks}
        for future in as_completed(futures):
            try:
                new_count += future.result()
            except Exception as e:
                debug_log(f"[TelegramXtream] Xtream portal error: {e}")

    # Phase 2b: Validate Mac portals and fetch channels (threaded)
    def _process_mac_portal(addr, mac, user, pwd):
        try:
            debug_log(f"[TelegramXtream] Validating Mac: {addr}")
            valid, result = validate_mac_credentials(addr, mac)
            debug_log(f"[TelegramXtream] Mac validation result: valid={valid}")
            if valid:
                debug_log(f"[TelegramXtream] Valid Mac credentials for {addr}")
                add_mac_portal_credentials(addr, mac, user, pwd)
                channels = get_mac_channels(addr, mac, user, pwd)
                debug_log(f"[TelegramXtream] Got {len(channels)} Mac channels from {addr}")
                for ch in channels:
                    ch["mac"] = mac
                    ch["username"] = user or ""
                    ch["password"] = pwd or ""
                kept = filter_channels(channels)
                debug_log(f"[TelegramXtream] Kept {len(kept)} after filter from {addr}")
                add_channels(kept, addr, channel_type="mac")
                return len(kept)
            else:
                debug_log(f"[TelegramXtream] Invalid Mac credentials for {addr}")
        except Exception as e:
            debug_log(f"[TelegramXtream] Mac validation error for {addr}: {e}")
        return 0

    mac_tasks = []
    for addr, mac_entries in mac_portals_to_check.items():
        if is_portal_excluded(addr):
            debug_log(f"[TelegramXtream] Skipping excluded Mac portal: {addr}")
            continue
        mac, user, pwd = mac_entries[0]
        mac_tasks.append((addr, mac, user, pwd))

    max_workers = min(4, len(mac_tasks)) if mac_tasks else 1
    debug_log(f"[TelegramXtream] Scraping {len(mac_tasks)} Mac portals (1 MAC per portal) with {max_workers} threads")
    debug_log(f"[TelegramXtream] Scraping {len(mac_tasks)} Mac portals with {max_workers} threads")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_mac_portal, addr, mac, user, pwd): addr for addr, mac, user, pwd in mac_tasks}
        for future in as_completed(futures):
            try:
                new_count += future.result()
            except Exception as e:
                debug_log(f"[TelegramXtream] Mac portal error: {e}")

    debug_log(f"[TelegramXtream] Scrape complete, {new_count} new channels")
    return new_count


def _background_scrape():
    global _last_scrape_ts
    if not _scrape_lock.acquire(blocking=False):
        return
    try:
        debug_log("[TelegramXtream] Background scrape starting")
        count = scrape_telegram_sources()
        _last_scrape_ts = time.time()
        set_last_scrape_ts(_last_scrape_ts)
        debug_log(f"[TelegramXtream] Background scrape complete, {count} new channels")
        import xbmcgui
        xbmcgui.Dialog().notification(
            "TelegramXtream",
            f"Scrape complete: {count:,} channels",
            xbmcgui.NOTIFICATION_INFO,
            5000,
        )
    except Exception as e:
        debug_log(f"[TelegramXtream] Background scrape error: {e}")
    finally:
        _scrape_lock.release()


def _needs_scrape() -> bool:
    global _last_scrape_ts
    if _last_scrape_ts is None:
        _last_scrape_ts = get_last_scrape_ts()
    if _last_scrape_ts == 0.0:
        return True
    return (time.time() - _last_scrape_ts) >= SCRAPE_INTERVAL


class TelegramXtream(JetExtractor):
    def __init__(self):
        self.domains = ["t.me", "telegram.me", "xtream://"]
        self.name = "TelegramXtream"
        self.short_name = "TGX"
        self.resolve_only = False
        self._proxy = None

    def _get_proxy(self):
        if self._proxy is None:
            self._proxy = get_stream_proxy(
                "TelegramXtream",
                {"User-Agent": BROWSER_UA},
                options={"cache_manifest": True, "manifest_ttl": 5.0}
            )
        return self._proxy

    def _proxy_url(self, stream_url: str, portal: str = "") -> str:
        headers = {"User-Agent": BROWSER_UA, "Referer": portal, "Origin": portal}
        return self._get_proxy().get_proxy_url(stream_url, headers)

    def is_available(self, url: JetLink) -> bool:
        if not is_telegramxtream_enabled():
            return False
        url_domain = urlparse(url.address).netloc
        if url_domain in ("t.me", "telegram.me"):
            return True
        if url.address.startswith("xtream://"):
            return True
        if url.address.startswith("mac://"):
            return True
        return False

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        if not is_telegramxtream_enabled():
            debug_log("[TelegramXtream] Extractor disabled in settings")
            return items

        data = load_channels()
        if not data.get("channels"):
            debug_log("[TelegramXtream] No cached channels, spawning background scrape")
            import xbmcgui
            xbmcgui.Dialog().notification(
                "TelegramXtream",
                "Fetching channels in background...",
                xbmcgui.NOTIFICATION_INFO,
                5000,
            )
            t = threading.Thread(target=_background_scrape, daemon=True)
            t.start()
            return items
        elif _needs_scrape():
            debug_log("[TelegramXtream] Channels exist but stale, spawning background scrape")
            t = threading.Thread(target=_background_scrape, daemon=True)
            t.start()

        if not data.get("channels"):
            debug_log("[TelegramXtream] Still no channels, returning empty")
            return items

        channels = filter_channels(data.get("channels", []))
        debug_log(f"[TelegramXtream] {len(channels)} channels after filter")

        self.progress_update(progress, "Returning cached channels")

        mac_by_portal_genre = {}
        for ch in channels:
            if ch.get("channel_type") != "mac":
                continue
            portal = ch.get("portal", "")
            genre = ch.get("category_name", "") or "Other"
            key = (portal, genre)
            if key not in mac_by_portal_genre:
                mac_by_portal_genre[key] = []
            mac_by_portal_genre[key].append(ch)

        for (portal, genre), genre_channels in sorted(mac_by_portal_genre.items()):
            encoded_portal = base64.urlsafe_b64encode(portal.encode()).decode()
            encoded_genre = base64.urlsafe_b64encode(genre.encode()).decode()
            folder_url = f"mac://genre?portal={encoded_portal}&genre={encoded_genre}"
            items.append(JetItem(
                title=f"{genre}  ({portal})  [{len(genre_channels)} ch]",
                links=[JetLink(folder_url, links=True)],
            ))

        for ch in channels:
            portal = ch.get("portal", "")
            channel_type = ch.get("channel_type", "xtream")
            name = ch.get("name", "Unknown")

            if channel_type == "mac":
                mac = ch.get("mac", "")
                cmd = ch.get("cmd", "")
                user = ch.get("username", "")
                pwd = ch.get("password", "")
                if not cmd:
                    continue
                creds = f"{portal}|{mac}|{user}|{pwd}"
                encoded_creds = base64.urlsafe_b64encode(creds.encode()).decode()
                encoded_cmd = base64.urlsafe_b64encode(cmd.encode()).decode()
                stream_url = f"mac://channels?creds={encoded_creds}&cmd={encoded_cmd}"
                items.append(JetItem(
                    title=f"{name}  ({portal}) [COLORaqua][MAC][/COLOR]",
                    links=[JetLink(stream_url, links=True)],
                    icon=self._get_icon(name),
                ))
            else:
                stream_id = ch.get("stream_id")
                user = ch.get("username", "")
                pwd = ch.get("password", "")
                if not stream_id:
                    continue
                stream_url = f"jetproxy://{portal}/live/{user}/{pwd}/{stream_id}.m3u8"
                items.append(JetItem(
                    title=f"{name}  ({portal})",
                    links=[JetLink(stream_url, direct=True, inputstream=JetInputstreamAdaptive.hls())],
                    icon=self._get_icon(name),
                ))
        return items

    def get_link(self, url: JetLink) -> JetLink:
        if not is_telegramxtream_enabled():
            return JetLink(url.address)

        if url.address.startswith("xtream://"):
            return url

        if url.address.startswith("mac://"):
            return url

        if "t.me" not in url.address and "telegram.me" not in url.address:
            return JetLink(url.address)

        debug_log(f"[TelegramXtream] Scraping: {url.address}")

        try:
            text = _fetch_telegram_text(url.address)
            if not text:
                raise Exception("Could not find message content")

            # Try Mac credentials first
            mac_creds = parse_telegram_mac_credentials(text)
            if mac_creds:
                for address, mac, username, password in mac_creds:
                    valid, _ = validate_mac_credentials(address, mac)
                    if valid:
                        creds = f"{address}|{mac}|{username or ''}|{password or ''}"
                        encoded_creds = base64.b64encode(creds.encode()).decode()
                        encoded_cmd = base64.b64encode(b"").decode()
                        virtual_url = f"mac://channels?creds={encoded_creds}&cmd={encoded_cmd}"
                        return JetLink(virtual_url, links=True)

            # Try Xtream credentials
            creds = parse_telegram_credentials(text)
            if creds:
                for address, username, password in creds:
                    valid, _ = validate_xtream_credentials(address, username, password)
                    if valid:
                        encoded_addr = base64.b64encode(address.encode()).decode()
                        encoded = base64.b64encode(f"{username}|{password}".encode()).decode()
                        virtual_url = f"xtream://channels?addr={encoded_addr}&creds={encoded}"
                        return JetLink(virtual_url, links=True)

            raise Exception("No valid credentials found")

        except Exception as e:
            debug_log(f"[TelegramXtream] Error: {e}")
            raise

    def get_links(self, url: JetLink) -> List[JetLink]:
        if not is_telegramxtream_enabled():
            return []
        if url.address.startswith("xtream://"):
            return self._get_xtream_links(url)
        elif url.address.startswith("mac://genre"):
            return self._get_genre_links(url)
        elif url.address.startswith("mac://"):
            return self._get_mac_links(url)
        return []

    def _get_genre_links(self, url: JetLink) -> List[JetLink]:
        """Handle mac://genre?portal=XXX&genre=YYY - return channels in a genre."""
        parsed = urlparse(url.address)
        query = parse_qs(parsed.query)
        encoded_portal = query.get("portal", [None])[0]
        encoded_genre = query.get("genre", [None])[0]

        if not encoded_portal or not encoded_genre:
            debug_log("[TelegramXtream] Genre links: missing portal or genre param")
            return []

        try:
            portal = base64.urlsafe_b64decode(encoded_portal).decode()
            genre = base64.urlsafe_b64decode(encoded_genre).decode()
        except Exception as e:
            debug_log(f"[TelegramXtream] Genre links: failed to decode params: {e}")
            return []

        debug_log(f"[TelegramXtream] Genre links: looking for portal={portal}, genre={genre}")

        data = load_channels()
        channels = filter_channels(data.get("channels", []))

        debug_log(f"[TelegramXtream] Genre links: total channels={len(channels)}")

        # Debug: show genre names for this portal
        portal_genres = set()
        for ch in channels:
            if ch.get("portal") == portal:
                portal_genres.add(ch.get("category_name") or "Other")
        debug_log(f"[TelegramXtream] Genre links: genres for portal={portal}: {sorted(portal_genres)[:20]}")

        results = []
        for ch in channels:
            ch_portal = ch.get("portal", "")
            ch_genre = ch.get("category_name") or "Other"

            if ch_portal != portal:
                continue
            if ch_genre != genre:
                continue

            channel_type = ch.get("channel_type", "xtream")
            name = ch.get("name", "Unknown")

            if channel_type == "mac":
                mac = ch.get("mac", "")
                cmd = ch.get("cmd", "")
                user = ch.get("username", "")
                pwd = ch.get("password", "")
                if not cmd:
                    continue
                creds = f"{portal}|{mac}|{user}|{pwd}"
                encoded_creds = base64.urlsafe_b64encode(creds.encode()).decode()
                encoded_cmd = base64.urlsafe_b64encode(cmd.encode()).decode()
                stream_url = f"mac://channels?creds={encoded_creds}&cmd={encoded_cmd}"
                results.append(JetLink(stream_url, links=True, name=name))
            else:
                stream_id = ch.get("stream_id")
                user = ch.get("username", "")
                pwd = ch.get("password", "")
                if not stream_id:
                    continue
                stream_url = f"jetproxy://{portal}/live/{user}/{pwd}/{stream_id}.m3u8"
                results.append(JetLink(stream_url, direct=True, name=name, inputstream=JetInputstreamAdaptive.hls()))

        debug_log(f"[TelegramXtream] Genre links: found {len(results)} links for {genre}")
        return results

    def _get_xtream_links(self, url: JetLink) -> List[JetLink]:
        virtual_url = url.address[9:]
        parsed = urlparse(virtual_url)
        query = parse_qs(parsed.query)
        encoded_addr = query.get("addr", [None])[0]
        encoded_creds = query.get("creds", [None])[0]

        if not encoded_addr or not encoded_creds:
            return []

        try:
            address = base64.b64decode(encoded_addr).decode()
            decoded = base64.b64decode(encoded_creds).decode()
            username, password = decoded.split("|", 1)
        except Exception:
            return []

        channels = get_xtream_channels(address, username, password)
        return [
            JetLink(
                f"jetproxy://{address}/live/{username}/{password}/{ch['stream_id']}.m3u8",
                direct=True,
                name=ch["name"],
                inputstream=JetInputstreamAdaptive.hls()
            )
            for ch in channels[:100]
        ]

    def _get_mac_links(self, url: JetLink) -> List[JetLink]:
        """Handle Mac:// virtual URLs - resolve via create_link API and return playable URL."""
        parsed = urlparse(url.address)
        query = parse_qs(parsed.query)
        encoded_creds = query.get("creds", [None])[0]
        encoded_cmd = query.get("cmd", [None])[0]

        if not encoded_creds or not encoded_cmd:
            debug_log("[TelegramXtream] Mac links: missing creds or cmd")
            return []

        try:
            creds_str = base64.urlsafe_b64decode(encoded_creds).decode()
            parts = creds_str.split("|", 3)
            if len(parts) < 4:
                debug_log(f"[TelegramXtream] Mac links: invalid creds format ({len(parts)} parts)")
                return []
            address, mac, username, password = parts
        except Exception as e:
            debug_log(f"[TelegramXtream] Mac links: failed to decode creds: {e}")
            return []

        try:
            cmd = base64.urlsafe_b64decode(encoded_cmd).decode()
        except Exception as e:
            debug_log(f"[TelegramXtream] Mac links: failed to decode cmd: {e}")
            return []

        debug_log(f"[TelegramXtream] Mac links: calling create_link for {address}, cmd={cmd[:80]}...")

        try:
            server = MacServer(address, mac, username or None, password or None)
            if server.handshake():
                link = server.create_link(cmd)
                if link:
                    debug_log(f"[TelegramXtream] Mac links: got playable URL: {link[:100]}")
                    return [JetLink(link, direct=True)]
                else:
                    debug_log(f"[TelegramXtream] Mac links: create_link returned empty")
            else:
                debug_log(f"[TelegramXtream] Mac links: handshake failed for {address}")
        except Exception as e:
            debug_log(f"[TelegramXtream] Mac links: error: {e}")

        return []

    def _get_icon(self, title: str) -> Optional[str]:
        from ..icons import icons
        title_lower = (title or "").lower()
        for key, icon in icons.items():
            if key in title_lower:
                return icon
        return None