import re
import time
import base64
import requests
import threading
from urllib.parse import urlparse, parse_qs
from ..models import *
from ..tools import debug_log, is_homeiptv_enabled
from ..util.xtream import validate_xtream_credentials, get_xtream_channels
from ..util.mac import validate_mac_credentials, get_mac_channels, MacServer
from ..util.homeiptv_store import (
    load_channels, add_portal_credentials, add_channels,
    get_portal_credentials, filter_channels,
    get_sources, is_portal_excluded,
    get_all_cached_portals, remove_portal_channels, remove_portal_credentials,
    add_excluded_portal, remove_excluded_portal, get_excluded_portals,
    add_mac_portal_credentials, get_mac_portal_credentials, get_all_mac_portals,
    remove_mac_portal_channels, remove_mac_portal_credentials,
    get_last_scrape_ts, set_last_scrape_ts,
)
from ..util.stream_proxy import get_stream_proxy

SCRAPE_INTERVAL = 6 * 3600
_scrape_lock = threading.Lock()
_last_scrape_ts = None

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


MAC_ADDRESS = re.compile(r'([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}')


def _clean_address(raw_url: str) -> str:
    """Extract base URL (scheme + host + port) from a full URL."""
    try:
        parsed = urlparse(raw_url)
        host = parsed.hostname
        if not host:
            return ""
        scheme = parsed.scheme or "http"
        return f"{scheme}://{host}:{parsed.port}" if parsed.port else f"{scheme}://{host}"
    except Exception:
        return ""


def parse_text_file_credentials(text: str) -> tuple:
    """Parse text file content for Xtream and Mac credentials.

    Supports two formats:
    1. Xtream: http://server:port/get.php?username=XXX&password=YYY&type=m3u
    2. Mac (single line): http://server:port/c/ 00:1A:2B:3C:4D:5E
    3. Mac (multi-line):
       http://server:port/c/
       00:1A:2B:3C:4D:5E

    Returns (xtream_creds, mac_creds) where:
    - xtream_creds: list of (address, username, password) tuples
    - mac_creds: list of (address, mac) tuples
    """
    xtream_results = []
    mac_results = []
    seen_xtream = set()
    seen_mac = set()

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue

        try:
            parsed = urlparse(line)
            if parsed.scheme not in ("http", "https"):
                i += 1
                continue

            # Check if this line has a MAC address (single-line format)
            mac_match = MAC_ADDRESS.search(line)
            if mac_match:
                mac = mac_match.group(0).upper().replace("-", ":")
                # Get the URL part (before the MAC)
                url_part = line[:mac_match.start()].strip()
                if url_part:
                    address = _clean_address(url_part)
                    if address:
                        key = (address, mac)
                        if key not in seen_mac:
                            seen_mac.add(key)
                            mac_results.append((address, mac))
                            debug_log(f"[HomeIPTV] Parsed MAC (single-line): {address}, {mac}")
                i += 1
                continue

            # Check for Xtream credentials in URL
            q = parse_qs(parsed.query)
            username = q.get("username", [None])[0]
            password = q.get("password", [None])[0]

            if username and password:
                address = _clean_address(line)
                if address:
                    key = (address, username, password)
                    if key not in seen_xtream:
                        seen_xtream.add(key)
                        xtream_results.append((address, username, password))
                        debug_log(f"[HomeIPTV] Parsed Xtream: {address}, user={username}")
                i += 1
                continue

            # Check for multi-line MAC format: URL on this line, MAC on next
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                mac_match = MAC_ADDRESS.search(next_line)
                if mac_match:
                    mac = mac_match.group(0).upper().replace("-", ":")
                    address = _clean_address(line)
                    if address:
                        key = (address, mac)
                        if key not in seen_mac:
                            seen_mac.add(key)
                            mac_results.append((address, mac))
                            debug_log(f"[HomeIPTV] Parsed MAC (multi-line): {address}, {mac}")
                    i += 2
                    continue

            i += 1

        except Exception as e:
            debug_log(f"[HomeIPTV] Error parsing line: {e}")
            i += 1
            continue

    debug_log(f"[HomeIPTV] Parsed {len(xtream_results)} Xtream, {len(mac_results)} MAC credentials")
    return xtream_results, mac_results


def fetch_text_file(url: str) -> str:
    """Fetch content from a text file URL."""
    try:
        resp = requests.get(url, headers={"User-Agent": BROWSER_UA}, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        debug_log(f"[HomeIPTV] Failed to fetch text file {url}: {e}")
        return ""


def scrape_homeiptv_sources(progress=None) -> int:
    """Scrape configured text file sources and cache channels.

    Phase 1: Fetch all text files, parse credentials (fast - no API calls).
    Phase 1.5: Re-validate existing cached portals (remove dead ones).
    Phase 2: Validate each portal, fetch channels from valid ones.
    Supports both Xtream Codes and Mac Codes credentials.
    """
    new_count = 0
    sources = get_sources()

    debug_log(f"[HomeIPTV] Scraping {len(sources)} text file sources")

    xtream_portals_to_check = {}  # address -> [(username, password)]
    mac_portals_to_check = {}     # address -> [mac]

    # Phase 1: Parse all text files
    for source_url in sources:
        try:
            debug_log(f"[HomeIPTV] Fetching text file: {source_url}")
            text = fetch_text_file(source_url)
            if not text:
                debug_log(f"[HomeIPTV] Empty response from {source_url}")
                continue

            xtream_creds, mac_creds = parse_text_file_credentials(text)

            for addr, user, pwd in xtream_creds:
                if addr not in xtream_portals_to_check:
                    xtream_portals_to_check[addr] = []
                pair = (user, pwd)
                if pair not in xtream_portals_to_check[addr]:
                    xtream_portals_to_check[addr].append(pair)

            for addr, mac in mac_creds:
                if addr not in mac_portals_to_check:
                    mac_portals_to_check[addr] = []
                if mac not in mac_portals_to_check[addr]:
                    mac_portals_to_check[addr].append(mac)

        except Exception as e:
            debug_log(f"[HomeIPTV] Error processing source {source_url}: {e}")

    debug_log(f"[HomeIPTV] Phase 1 done: {len(xtream_portals_to_check)} Xtream, {len(mac_portals_to_check)} MAC portals")

    # Phase 1.5: Re-validate existing cached portals (remove dead ones)
    # Re-validate Xtream portals
    cached_portals = get_all_cached_portals()
    debug_log(f"[HomeIPTV] Re-validating {len(cached_portals)} cached Xtream portals")
    dead_portals = []
    for cached in cached_portals:
        portal = cached.get("portal", "")
        user = cached.get("username", "")
        pwd = cached.get("password", "")

        if not portal or is_portal_excluded(portal):
            continue

        try:
            valid, _ = validate_xtream_credentials(portal, user, pwd)
            if not valid:
                debug_log(f"[HomeIPTV] Cached Xtream portal DEAD: {portal}")
                dead_portals.append((portal, user, pwd))
            else:
                debug_log(f"[HomeIPTV] Cached Xtream portal OK: {portal}")
        except Exception as e:
            debug_log(f"[HomeIPTV] Error re-validating {portal}: {e}")
            dead_portals.append((portal, user, pwd))

    for portal, user, pwd in dead_portals:
        remove_portal_channels(portal)
        remove_portal_credentials(portal, user, pwd)
        debug_log(f"[HomeIPTV] Removed dead Xtream portal: {portal}")

    # Re-validate MAC portals
    cached_mac_portals = get_all_mac_portals()
    debug_log(f"[HomeIPTV] Re-validating {len(cached_mac_portals)} cached MAC portals")
    dead_mac_portals = []
    for cached in cached_mac_portals:
        portal = cached.get("portal", "")
        mac = cached.get("mac", "")

        if not portal or is_portal_excluded(portal):
            continue

        try:
            valid, _ = validate_mac_credentials(portal, mac)
            if not valid:
                debug_log(f"[HomeIPTV] Cached MAC portal DEAD: {portal}")
                dead_mac_portals.append((portal, mac))
            else:
                debug_log(f"[HomeIPTV] Cached MAC portal OK: {portal}")
        except Exception as e:
            debug_log(f"[HomeIPTV] Error re-validating MAC {portal}: {e}")
            dead_mac_portals.append((portal, mac))

    for portal, mac in dead_mac_portals:
        remove_mac_portal_channels(portal)
        remove_mac_portal_credentials(portal, mac)
        debug_log(f"[HomeIPTV] Removed dead MAC portal: {portal}")

    total_dead = len(dead_portals) + len(dead_mac_portals)
    if total_dead:
        debug_log(f"[HomeIPTV] Removed {total_dead} dead portals from cache")
    else:
        debug_log(f"[HomeIPTV] All cached portals still alive")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _process_xtream_portal(addr, user, pwd):
        try:
            debug_log(f"[HomeIPTV] Validating Xtream: {addr}")
            valid, result = validate_xtream_credentials(addr, user, pwd)
            debug_log(f"[HomeIPTV] Validation result: valid={valid}")

            if valid:
                debug_log(f"[HomeIPTV] Valid Xtream credentials for {addr}")
                add_portal_credentials(addr, user, pwd)
                channels = get_xtream_channels(addr, user, pwd)
                debug_log(f"[HomeIPTV] Got {len(channels)} Xtream channels from {addr}")

                for ch in channels:
                    ch["username"] = user
                    ch["password"] = pwd

                kept = filter_channels(channels)
                debug_log(f"[HomeIPTV] Kept {len(kept)} after filter from {addr}")

                add_channels(kept, addr, channel_type="xtream")
                return len(kept)
            else:
                debug_log(f"[HomeIPTV] Invalid Xtream credentials for {addr}")
        except Exception as e:
            debug_log(f"[HomeIPTV] Xtream validation error for {addr}: {e}")
        return 0

    # Phase 2a: Validate Xtream portals and fetch channels (threaded)
    xtream_tasks = []
    for addr, cred_pairs in xtream_portals_to_check.items():
        if is_portal_excluded(addr):
            debug_log(f"[HomeIPTV] Skipping excluded portal: {addr}")
            continue
        for user, pwd in cred_pairs:
            xtream_tasks.append((addr, user, pwd))

    max_workers = min(4, len(xtream_tasks)) if xtream_tasks else 1
    debug_log(f"[HomeIPTV] Scraping {len(xtream_tasks)} Xtream portals with {max_workers} threads")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_xtream_portal, addr, user, pwd): addr for addr, user, pwd in xtream_tasks}
        for future in as_completed(futures):
            try:
                new_count += future.result()
            except Exception as e:
                debug_log(f"[HomeIPTV] Xtream portal error: {e}")

    # Phase 2b: Validate MAC portals and fetch channels (threaded)
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _process_mac_portal(addr, mac):
        try:
            debug_log(f"[HomeIPTV] Validating MAC: {addr}")
            valid, result = validate_mac_credentials(addr, mac)
            debug_log(f"[HomeIPTV] MAC validation result: valid={valid}")

            if valid:
                debug_log(f"[HomeIPTV] Valid MAC credentials for {addr}")
                add_mac_portal_credentials(addr, mac)
                channels = get_mac_channels(addr, mac)
                debug_log(f"[HomeIPTV] Got {len(channels)} MAC channels from {addr}")

                for ch in channels:
                    ch["mac"] = mac

                kept = filter_channels(channels)
                debug_log(f"[HomeIPTV] Kept {len(kept)} after filter from {addr}")

                add_channels(kept, addr, channel_type="mac")
                return len(kept)
            else:
                debug_log(f"[HomeIPTV] Invalid MAC credentials for {addr}")
        except Exception as e:
            debug_log(f"[HomeIPTV] MAC validation error for {addr}: {e}")
        return 0

    mac_tasks = []
    for addr, macs in mac_portals_to_check.items():
        if is_portal_excluded(addr):
            debug_log(f"[HomeIPTV] Skipping excluded MAC portal: {addr}")
            continue
        mac_tasks.append((addr, macs[0]))

    max_workers = min(4, len(mac_tasks)) if mac_tasks else 1
    debug_log(f"[HomeIPTV] Scraping {len(mac_tasks)} MAC portals (1 MAC per portal) with {max_workers} threads")
    debug_log(f"[HomeIPTV] Scraping {len(mac_tasks)} MAC portals with {max_workers} threads")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_mac_portal, addr, mac): addr for addr, mac in mac_tasks}
        for future in as_completed(futures):
            try:
                new_count += future.result()
            except Exception as e:
                debug_log(f"[HomeIPTV] MAC portal error: {e}")

    debug_log(f"[HomeIPTV] Scrape complete, {new_count} new channels")
    return new_count


def _background_scrape():
    global _last_scrape_ts
    if not _scrape_lock.acquire(blocking=False):
        return
    try:
        debug_log("[HomeIPTV] Background scrape starting")
        count = scrape_homeiptv_sources()
        _last_scrape_ts = time.time()
        set_last_scrape_ts(_last_scrape_ts)
        debug_log(f"[HomeIPTV] Background scrape complete, {count} new channels")
        import xbmcgui
        xbmcgui.Dialog().notification(
            "HomeIPTV",
            f"Scrape complete: {count:,} channels",
            xbmcgui.NOTIFICATION_INFO,
            5000,
        )
    except Exception as e:
        debug_log(f"[HomeIPTV] Background scrape error: {e}")
    finally:
        _scrape_lock.release()


def _needs_scrape() -> bool:
    global _last_scrape_ts
    if _last_scrape_ts is None:
        _last_scrape_ts = get_last_scrape_ts()
    if _last_scrape_ts == 0.0:
        return True
    return (time.time() - _last_scrape_ts) >= SCRAPE_INTERVAL


class HomeIPTV(JetExtractor):
    def __init__(self):
        self.domains = ["homeiptv://"]
        self.name = "HomeIPTV"
        self.short_name = "HIPTV"
        self.resolve_only = False
        self._proxy = None

    def _get_proxy(self):
        if self._proxy is None:
            self._proxy = get_stream_proxy(
                "HomeIPTV",
                {"User-Agent": BROWSER_UA},
                options={"cache_manifest": True, "manifest_ttl": 5.0}
            )
        return self._proxy

    def _proxy_url(self, stream_url: str, portal: str = "") -> str:
        headers = {"User-Agent": BROWSER_UA, "Referer": portal, "Origin": portal}
        return self._get_proxy().get_proxy_url(stream_url, headers)

    def is_available(self, url: JetLink) -> bool:
        if not is_homeiptv_enabled():
            return False
        return url.address.startswith("homeiptv://") or url.address.startswith("homeiptvmac://")

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        if not is_homeiptv_enabled():
            debug_log("[HomeIPTV] Extractor disabled in settings")
            return items

        data = load_channels()
        if not data.get("channels"):
            debug_log("[HomeIPTV] No cached channels, spawning background scrape")
            import xbmcgui
            xbmcgui.Dialog().notification(
                "HomeIPTV",
                "Fetching channels in background...",
                xbmcgui.NOTIFICATION_INFO,
                5000,
            )
            t = threading.Thread(target=_background_scrape, daemon=True)
            t.start()
            return items
        elif _needs_scrape():
            debug_log("[HomeIPTV] Channels exist but stale, spawning background scrape")
            t = threading.Thread(target=_background_scrape, daemon=True)
            t.start()

        if not data.get("channels"):
            debug_log("[HomeIPTV] Still no channels, returning empty")
            return items

        channels = filter_channels(data.get("channels", []))
        debug_log(f"[HomeIPTV] {len(channels)} channels after filter")

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
            folder_url = f"homeiptv://genre?portal={encoded_portal}&genre={encoded_genre}"
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
                if not cmd:
                    continue
                creds = f"{portal}|{mac}"
                encoded_creds = base64.urlsafe_b64encode(creds.encode()).decode()
                encoded_cmd = base64.urlsafe_b64encode(cmd.encode()).decode()
                stream_url = f"homeiptvmac://channels?creds={encoded_creds}&cmd={encoded_cmd}"
                items.append(JetItem(
                    title=f"{name}  ({portal}) [MAC]",
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
        if not is_homeiptv_enabled():
            return JetLink(url.address)
        if url.address.startswith("homeiptv://"):
            return url
        return JetLink(url.address)

    def get_links(self, url: JetLink) -> List[JetLink]:
        if not is_homeiptv_enabled():
            return []
        if url.address.startswith("homeiptv://genre"):
            return self._get_genre_links(url)
        elif url.address.startswith("homeiptv://"):
            return self._get_iptv_links(url)
        elif url.address.startswith("homeiptvmac://"):
            return self._get_mac_links(url)
        return []

    def _get_genre_links(self, url: JetLink) -> List[JetLink]:
        """Handle homeiptv://genre?portal=XXX&genre=YYY - return channels in a genre."""
        parsed = urlparse(url.address)
        query = parse_qs(parsed.query)
        encoded_portal = query.get("portal", [None])[0]
        encoded_genre = query.get("genre", [None])[0]

        if not encoded_portal or not encoded_genre:
            return []

        try:
            portal = base64.urlsafe_b64decode(encoded_portal).decode()
            genre = base64.urlsafe_b64decode(encoded_genre).decode()
        except Exception:
            return []

        data = load_channels()
        channels = filter_channels(data.get("channels", []))

        results = []
        for ch in channels:
            if ch.get("portal") != portal:
                continue
            if (ch.get("category_name") or "Other") != genre:
                continue

            channel_type = ch.get("channel_type", "xtream")
            name = ch.get("name", "Unknown")

            if channel_type == "mac":
                mac = ch.get("mac", "")
                cmd = ch.get("cmd", "")
                if not cmd:
                    continue
                creds = f"{portal}|{mac}"
                encoded_creds = base64.urlsafe_b64encode(creds.encode()).decode()
                encoded_cmd = base64.urlsafe_b64encode(cmd.encode()).decode()
                stream_url = f"homeiptvmac://channels?creds={encoded_creds}&cmd={encoded_cmd}"
                results.append(JetLink(stream_url, links=True, name=name))
            else:
                stream_id = ch.get("stream_id")
                user = ch.get("username", "")
                pwd = ch.get("password", "")
                if not stream_id:
                    continue
                stream_url = f"jetproxy://{portal}/live/{user}/{pwd}/{stream_id}.m3u8"
                results.append(JetLink(stream_url, direct=True, name=name, inputstream=JetInputstreamAdaptive.hls()))

        return results

    def _get_iptv_links(self, url: JetLink) -> List[JetLink]:
        """Handle homeiptv:// virtual URLs - return cached channels."""
        data = load_channels()
        channels = filter_channels(data.get("channels", []))

        return [
            JetLink(
                f"jetproxy://{ch['portal']}/live/{ch['username']}/{ch['password']}/{ch['stream_id']}.m3u8",
                direct=True,
                name=ch["name"],
                inputstream=JetInputstreamAdaptive.hls()
            )
            for ch in channels[:100]
        ]

    def _get_mac_links(self, url: JetLink) -> List[JetLink]:
        """Handle homeiptvmac:// virtual URLs - resolve via create_link API and return playable URL."""
        raw = url.address
        if raw.startswith("homeiptvmac://"):
            raw = "mac://" + raw[len("homeiptvmac://"):]
        parsed = urlparse(raw)
        query = parse_qs(parsed.query)
        encoded_creds = query.get("creds", [None])[0]
        encoded_cmd = query.get("cmd", [None])[0]

        if not encoded_creds or not encoded_cmd:
            debug_log("[HomeIPTV] Mac links: missing creds or cmd")
            return []

        try:
            creds_str = base64.urlsafe_b64decode(encoded_creds).decode()
            parts = creds_str.split("|", 1)
            if len(parts) < 2:
                debug_log(f"[HomeIPTV] Mac links: invalid creds format")
                return []
            address, mac = parts
        except Exception as e:
            debug_log(f"[HomeIPTV] Mac links: failed to decode creds: {e}")
            return []

        try:
            cmd = base64.urlsafe_b64decode(encoded_cmd).decode()
        except Exception as e:
            debug_log(f"[HomeIPTV] Mac links: failed to decode cmd: {e}")
            return []

        debug_log(f"[HomeIPTV] Mac links: calling create_link for {address}, cmd={cmd[:80]}...")

        try:
            server = MacServer(address, mac)
            if server.handshake():
                if not server.username:
                    server.get_profile()
                link = server.create_link(cmd)
                if link:
                    debug_log(f"[HomeIPTV] Mac links: got playable URL: {link[:100]}")
                    return [JetLink(link, direct=True)]
                else:
                    debug_log(f"[HomeIPTV] Mac links: create_link returned empty")
            else:
                debug_log(f"[HomeIPTV] Mac links: handshake failed for {address}")
        except Exception as e:
            debug_log(f"[HomeIPTV] Mac links: error: {e}")

        return []

    def _get_icon(self, title: str) -> Optional[str]:
        from ..icons import icons
        title_lower = (title or "").lower()
        for key, icon in icons.items():
            if key in title_lower:
                return icon
        return None
