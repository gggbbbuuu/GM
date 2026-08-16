import requests
from ..tools import debug_log

MAC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0"

EXCLUDE_GENRES = [
    "24/7", "AFRICA", "ALBANIAN", "ARAB", "BANGLA", "BULGARIAN", "CAMBODIAN",
    "CROATIAN", "CZECH", "DANISH", "DUTCH", "ESTONIAN", "FINNISH",
    "GEORGIAN", "GREEK", "HEBREW", "HINDI", "HUNGARIAN", "ICELANDIC",
    "INDONESIAN", "IRANIAN", "IRAQI", "IRISH", "KAZAKH", "KOREAN",
    "KURDISH", "LAO", "LATVIAN", "LITHUANIAN", "MACEDONIAN", "MALAY",
    "MONGOLIAN", "NORWEGIAN", "PAKISTANI", "PERSIAN", "POLISH",
    "PORTUGUESE", "ROMANIAN", "RUSSIAN", "SERBIAN", "SINHALA", "SLOVAK",
    "SLOVENIAN", "SOMALI", "SPANISH", "SWEDISH", "TAJIK", "TAMIL",
    "THAI", "TURKISH", "UKRAINIAN", "URDU", "UZBEK", "VIETNAMESE",
]


def _fix_ts_extension(url: str) -> str:
    """Convert .ts extension to .m3u8 for HLS playback."""
    url = url.replace("extension=ts", "extension=m3u8")
    url = url.replace("?ext=.ts", "?ext=m3u8")
    url = url.replace("&ext=.ts", "&ext=m3u8")
    url = url.replace("/extension.ts", "/extension.m3u8")
    return url


class MacServer:
    """Manages communication with Mac Codes (Stalker) portal servers."""

    def __init__(self, host: str, mac: str, username: str = None, password: str = None, timeout: int = 10):
        self.host = host.rstrip("/")
        self.mac = mac
        self.username = username
        self.password = password
        self.timeout = timeout
        self.token = None
        self.session = requests.Session()
        self.session.headers["User-Agent"] = MAC_USER_AGENT
        self.session.headers["Cookie"] = f"mac={mac}; stb_lang=en; timezone=America/Los_Angeles"

    def _api_request(self, action: str, api_type: str = "stb", params: dict = None) -> dict:
        """Make an API request to the portal."""
        api_url = f"{self.host}/c/portal.php"
        request_params = {
            "type": api_type,
            "action": action,
            "JsHttpRequest": "1-xml",
        }
        if params:
            request_params.update(params)

        login_payload = None
        if api_type == "itv" and self.username is not None:
            login_payload = {"login": self.username, "password": self.password}

        try:
            r = self.session.request(
                "POST",
                api_url,
                params=request_params,
                json=login_payload,
                timeout=self.timeout
            )
            if len(r.text) != 0:
                return r.json().get("js", {})
            return {}
        except Exception as e:
            debug_log(f"[Mac] API request failed ({action}): {e}")
            return {}

    def handshake(self) -> bool:
        """Perform handshake to get authentication token."""
        try:
            result = self._api_request("handshake")
            self.token = result.get("token")
            if self.token:
                self.session.headers["Authorization"] = f"Bearer {self.token}"
                debug_log(f"[Mac] Handshake successful for {self.host}")
                return True
            debug_log(f"[Mac] Handshake failed - no token returned")
            return False
        except Exception as e:
            debug_log(f"[Mac] Handshake error: {e}")
            return False

    def get_profile(self) -> dict:
        """Get user profile (includes login/password if not provided)."""
        try:
            profile = self._api_request("get_profile")
            if profile:
                self.username = profile.get("login", self.username)
                self.password = profile.get("password", self.password)
                debug_log(f"[Mac] Profile retrieved: login={self.username}")
            return profile
        except Exception as e:
            debug_log(f"[Mac] Get profile error: {e}")
            return {}

    def init(self) -> bool:
        """Initialize server: handshake and get profile."""
        if not self.handshake():
            return False
        self.get_profile()
        # Remove auth header after profile (not needed for subsequent requests)
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
        return True

    def get_genres(self) -> list:
        """Get list of channel genres/categories."""
        try:
            genres = self._api_request("get_genres", "itv")
            if isinstance(genres, list):
                return genres
            return []
        except Exception as e:
            debug_log(f"[Mac] Get genres error: {e}")
            return []

    def get_channels(self, genre: str = None, page: int = 1) -> dict:
        """Get channels, optionally filtered by genre with pagination."""
        try:
            params = {"p": page}
            if genre:
                params["genre"] = genre
            result = self._api_request("get_ordered_list", "itv", params)
            return result
        except Exception as e:
            debug_log(f"[Mac] Get channels error: {e}")
            return {}

    def get_all_channels(self, genre: str = None, max_channels: int = 500) -> list:
        """Fetch multiple pages of channels."""
        all_channels = []
        page = 1
        while len(all_channels) < max_channels:
            result = self.get_channels(genre=genre, page=page)
            if not result or "data" not in result or not result["data"]:
                break
            all_channels.extend(result["data"])
            total = result.get("total_items", 0)
            max_page = result.get("max_page_items", 20)
            if page * max_page >= total:
                break
            page += 1
        return all_channels[:max_channels]

    def create_link(self, cmd: str) -> str:
        """Create a playable stream link from a channel command.

        If cmd is already a full URL with query params (e.g. has ?mac= or &stream=),
        return it directly - create_link would strip the stream parameter.
        Otherwise, call the portal API to resolve the command.
        """
        try:
            if "?" in cmd and ("mac=" in cmd or "stream=" in cmd):
                debug_log(f"[Mac] create_link: cmd is already a full URL, using directly: {cmd[:100]}...")
                return _fix_ts_extension(cmd)

            debug_log(f"[Mac] create_link called with cmd: {cmd[:120]}...")
            result = self._api_request("create_link", "itv", {"cmd": cmd})
            debug_log(f"[Mac] create_link result: {result}")
            if result and "cmd" in result:
                link = _fix_ts_extension(result["cmd"].replace("ffmpeg ", ""))
                debug_log(f"[Mac] create_link final URL: {link[:120]}...")
                return link
            debug_log(f"[Mac] create_link: no cmd in result")
            return ""
        except Exception as e:
            debug_log(f"[Mac] Create link error: {e}")
            return ""


def validate_mac_credentials(address: str, mac: str, timeout: int = 10) -> tuple:
    """Validate Mac address against a portal server.

    Returns:
        (True, profile_data) on success
        (False, error_message) on failure
    """
    try:
        server = MacServer(address, mac, timeout=timeout)
        if not server.handshake():
            return False, "Handshake failed"

        profile = server.get_profile()
        if not profile:
            return False, "Failed to get profile"

        return True, {
            "address": address,
            "mac": mac,
            "username": server.username,
            "password": server.password,
            "profile": profile
        }
    except requests.exceptions.ConnectionError:
        return False, "Connection failed - host unreachable"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def get_mac_channels(address: str, mac: str, username: str = None, password: str = None,
                     genre: str = None, timeout: int = 15, max_workers: int = 1) -> list:
    """Fetch channels from a Mac Codes portal.

    Fetches genres first, then fetches channels per-genre to ensure complete results.
    If max_workers > 1, fetches genres in parallel using threads.
    Returns list of dicts with keys: name, logo, cmd, category, category_name
    """
    import time as _time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    start = _time.time()
    max_total_time = 300  # 5 minute overall limit for all genres
    try:
        server = MacServer(address, mac, username, password, timeout=timeout)
        if not server.handshake():
            return []

        if not server.username:
            server.get_profile()

        genres = server.get_genres()
        genre_map = {}
        for g in genres:
            gid = str(g.get("id", ""))
            gname = (g.get("title") or "").strip()
            if gid and gname:
                gname_upper = gname.upper()
                if any(ex in gname_upper for ex in EXCLUDE_GENRES):
                    debug_log(f"[Mac] Skipping excluded genre: {gname}")
                    continue
                genre_map[gid] = gname
        debug_log(f"[Mac] Got {len(genre_map)} genres from {address}")

        if genre:
            genre_list = [(genre, genre_map.get(genre, ""))]
        else:
            genre_list = [(gid, gname) for gid, gname in genre_map.items()]
            if not genre_list:
                genre_list = [("", "")]

        if max_workers <= 1:
            channels = []
            seen_cmds = set()
            max_pages = 50

            for gid, gname in genre_list:
                page = 1
                while page <= max_pages:
                    elapsed = _time.time() - start
                    if elapsed > max_total_time:
                        debug_log(f"[Mac] Channel fetch timed out after {elapsed:.0f}s from {address}, got {len(channels)} channels")
                        return channels
                    debug_log(f"[Mac] Fetching genre '{gname}' ({gid}) page {page} from {address}")
                    result = server.get_channels(genre=gid if gid else None, page=page)
                    if not result or "data" not in result:
                        break

                    for item in result["data"]:
                        name = (item.get("name") or "").strip()
                        if not name:
                            continue
                        raw_cmd = (item.get("cmd") or "").strip()
                        if not raw_cmd:
                            continue
                        cmd = raw_cmd.replace("ffmpeg ", "").replace("extension=ts", "extension=m3u8")
                        if cmd in seen_cmds:
                            continue
                        seen_cmds.add(cmd)
                        channels.append({
                            "name": name,
                            "logo": item.get("logo", ""),
                            "cmd": cmd,
                            "category": gid,
                            "category_name": gname if gname else "Other",
                        })

                    total = result.get("total_items", 0)
                    max_page = result.get("max_page_items", 20)
                    debug_log(f"[Mac] Genre '{gname}' page {page}: got {len(result['data'])} items, total={total}, fetched so far={len(channels)}")
                    if page * max_page >= total:
                        break
                    page += 1
        else:
            channels = []
            seen_cmds = set()
            seen_cmds_lock = threading.Lock()
            channels_lock = threading.Lock()
            max_pages = 50
            done_genres = [0]

            def _fetch_genre_batch(genre_batch):
                genre_channels = []
                server_thread = MacServer(address, mac, username, password, timeout=timeout)
                if not server_thread.handshake():
                    return []
                if not server_thread.username:
                    server_thread.get_profile()
                for gid, gname in genre_batch:
                    page = 1
                    while page <= max_pages:
                        elapsed = _time.time() - start
                        if elapsed > max_total_time:
                            return genre_channels
                        result = server_thread.get_channels(genre=gid if gid else None, page=page)
                        if not result or "data" not in result:
                            break
                        for item in result["data"]:
                            name = (item.get("name") or "").strip()
                            if not name:
                                continue
                            raw_cmd = (item.get("cmd") or "").strip()
                            if not raw_cmd:
                                continue
                            cmd = raw_cmd.replace("ffmpeg ", "").replace("extension=ts", "extension=m3u8")
                            with seen_cmds_lock:
                                if cmd in seen_cmds:
                                    continue
                                seen_cmds.add(cmd)
                            genre_channels.append({
                                "name": name,
                                "logo": item.get("logo", ""),
                                "cmd": cmd,
                                "category": gid,
                                "category_name": gname if gname else "Other",
                            })
                        total = result.get("total_items", 0)
                        max_page = result.get("max_page_items", 20)
                        if page * max_page >= total:
                            break
                        page += 1
                    done_genres[0] += 1
                debug_log(f"[Mac] Parallel batch done ({done_genres[0]}/{len(genre_list)}), got {len(genre_channels)} channels from {address}")
                return genre_channels

            workers = min(max_workers, len(genre_list))
            batch_size = max(1, len(genre_list) // workers)
            batches = [genre_list[i:i+batch_size] for i in range(0, len(genre_list), batch_size)]
            debug_log(f"[Mac] Fetching {len(genre_list)} genres in {len(batches)} parallel batches with {workers} workers from {address}")
            executor = ThreadPoolExecutor(max_workers=workers)
            try:
                futures = {executor.submit(_fetch_genre_batch, batch): i for i, batch in enumerate(batches)}
                for future in as_completed(futures):
                    elapsed = _time.time() - start
                    if elapsed > max_total_time:
                        debug_log(f"[Mac] Channel fetch timed out after {elapsed:.0f}s from {address}, got {len(channels)} channels")
                        break
                    try:
                        genre_chs = future.result()
                        if genre_chs:
                            with channels_lock:
                                channels.extend(genre_chs)
                    except Exception as e:
                        debug_log(f"[Mac] Error fetching batch: {e}")
            finally:
                executor.shutdown(wait=False)

        debug_log(f"[Mac] Fetched {len(channels)} channels from {address} in {_time.time() - start:.1f}s")
        return channels
    except Exception as e:
        debug_log(f"[Mac] Failed to fetch channels: {e}")
        return []


def build_mac_stream_url(address: str, mac: str, cmd: str, username: str = None, password: str = None) -> str:
    """Build a mac:// virtual URL that encodes all credentials for deferred resolution."""
    import base64
    creds = f"{address}|{mac}|{username or ''}|{password or ''}"
    encoded_creds = base64.urlsafe_b64encode(creds.encode()).decode()
    encoded_cmd = base64.urlsafe_b64encode(cmd.encode()).decode()
    return f"mac://channels?creds={encoded_creds}&cmd={encoded_cmd}"
