import re
import time
import base64
import json
import threading
from urllib.parse import urlparse, parse_qs
from ..models import *
from ..tools import debug_log
from .._core import fetch_page, _KODI_UA
from ..util.stream_proxy import get_stream_proxy
from ..util import sportsx_store
from .sportsx_color import COLOR_MAP, DEFAULT_COLOR, HIDE_DEFAULT_COLOR, EXCLUDE_DOMAINS

SCRAPE_INTERVAL = 3600
_scrape_lock = threading.Lock()
_last_scrape_ts = None

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

WORKER_URL_RE = re.compile(
    r'(https?://[^/]+/t=)([A-Za-z0-9+/=]+)(/\d+\.m3u)'
)


def _decode_worker_token(token_b64: str) -> dict:
    """Decode the base64 token from a worker proxy URL."""
    try:
        padded = token_b64 + "=" * (4 - len(token_b64) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}


def parse_m3u(text: str) -> list:
    """Parse M3U text into channel dicts. Handles #EXTVLCOPT headers."""
    channels = []
    lines = text.strip().splitlines()

    def _colorize_word(word):
        color = COLOR_MAP.get(word.upper(), DEFAULT_COLOR)
        broken = " -Broken" if color == "red" else ""
        return f"[COLOR{color}]{word}[/COLOR]{broken}", color

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            name_match = re.search(r',(.+)$', line)
            name = name_match.group(1).strip() if name_match else "Unknown"
            source_color = None
            # Move trailing parenthesized content to front, e.g. "NBA TV (STRMCNTR)" -> "[COLORaqua]STRMCNTR[/COLOR] NBA TV"
            _paren_match = re.search(r'\s*\(([^)]+)\)\s*$', name)
            if _paren_match:
                _word = _paren_match.group(1)
                _prefix = name[:_paren_match.start()].strip()
                _colored, source_color = _colorize_word(_word)
                name = f"{_colored} {_prefix}"
            # Colorize any remaining parenthesized content in-place
            def _sub_paren(m):
                nonlocal source_color
                _colored, _c = _colorize_word(m.group(1))
                if source_color is None:
                    source_color = _c
                return f"({_colored})"
            name = re.sub(r'\(([^)]+)\)', _sub_paren, name)
            # name = re.sub(r'\s*\([^)]*\)\s*', '', name).replace("(", " ").replace(")", " ").strip()
            if not name:
                name = "Unknown"

            i += 1
            ext_headers = {}
            while i < len(lines):
                stripped = lines[i].strip()
                if not stripped or not stripped.startswith("#") or stripped.startswith("#EXTINF"):
                    break
                vlc_match = re.match(r'#EXTVLCOPT:(\S+?)=(.*)', stripped)
                if vlc_match:
                    key = vlc_match.group(1).lower()
                    val = vlc_match.group(2).strip()
                    if key == "http-referrer":
                        ext_headers["Referer"] = val
                    elif key == "http-origin":
                        ext_headers["Origin"] = val
                    elif key == "http-user-agent":
                        ext_headers["User-Agent"] = val
                i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith("#")):
                i += 1
            if i >= len(lines):
                break
            url = lines[i].strip()
            if url and not url.startswith("#"):
                channel = _parse_channel_url(url, name)
                if channel:
                    if ext_headers:
                        channel["headers"] = ext_headers
                    if source_color:
                        channel["source_color"] = source_color
                    channels.append(channel)
        i += 1
    return channels


def _parse_channel_url(url: str, name: str) -> dict:
    """Classify and parse a channel URL."""
    m = WORKER_URL_RE.match(url)
    if m:
        token_data = _decode_worker_token(m.group(2))
        if token_data:
            channel_id = m.group(3).strip("/").replace(".m3u", "")
            return {
                "name": name,
                "url": url,
                "channel_type": "worker",
                "portal": token_data.get("portal", ""),
                "mac": token_data.get("mac", ""),
                "sn": token_data.get("sn", ""),
                "device": token_data.get("device", ""),
                "channel_id": channel_id,
            }
    return {
        "name": name,
        "url": url,
        "channel_type": "direct",
    }


def _fetch_m3u(source_url):
    """Fetch an M3U, retrying with a Kodi UA if the response isn't a playlist.

    Some hosts 302 browser user agents to a block page but serve the real
    file to non-browser agents, so a non-M3U response is retried once.
    """
    text = fetch_page(source_url)
    if text and "#EXTINF" in text:
        return text
    retry = fetch_page(source_url, user_agent=_KODI_UA)
    if retry and "#EXTINF" in retry:
        debug_log(f"[SportsX] Retried {source_url} with Kodi user agent")
        return retry
    return retry or text


def scrape_sportsx_sources(progress=None) -> int:
    """Fetch all M3U sources and cache channels."""
    sources = sportsx_store.get_sources()
    debug_log(f"[SportsX] Scraping {len(sources)} M3U sources")
    all_channels = []
    for source_url in sources:
        try:
            text = _fetch_m3u(source_url)
            if text:
                channels = parse_m3u(text)
                all_channels.extend(channels)
                debug_log(f"[SportsX] Parsed {len(channels)} channels from {source_url}")
        except Exception as e:
            debug_log(f"[SportsX] Failed to fetch {source_url}: {e}")
    if all_channels:
        sportsx_store.clear_channels()
        sportsx_store.add_channels(all_channels)
        sportsx_store.set_last_refresh_ts(time.time())
        debug_log(f"[SportsX] Stored {len(all_channels)} channels")
    return len(all_channels)


def _background_scrape():
    global _last_scrape_ts
    if not _scrape_lock.acquire(blocking=False):
        return
    try:
        _last_scrape_ts = time.time()
        sportsx_store.set_last_scrape_ts(_last_scrape_ts)
        debug_log("[SportsX] Background scrape starting")
        count = scrape_sportsx_sources()
        _last_scrape_ts = time.time()
        sportsx_store.set_last_refresh_ts(_last_scrape_ts)
        debug_log(f"[SportsX] Background scrape complete, {count} channels")
        from ..tools import notify_refresh
        notify_refresh("SportsX: %s channels" % f"{count:,}")
    except Exception as e:
        debug_log(f"[SportsX] Background scrape error: {e}")
    finally:
        _scrape_lock.release()


def _needs_scrape() -> bool:
    global _last_scrape_ts
    if _last_scrape_ts is None:
        _last_scrape_ts = sportsx_store.get_last_refresh_ts()
    if _last_scrape_ts == 0.0:
        return True
    return (time.time() - _last_scrape_ts) >= SCRAPE_INTERVAL


GITHUB_M3U_RE = re.compile(
    r'raw\.githubusercontent\.com/.+\.(m3u8?)(\?|$)', re.IGNORECASE
)


def _domain_of(url: str) -> str:
    """Return scheme://host[:port] for a channel/portal URL.

    Used to show the channel's own origin next to its name (like
    TelegramXtream's "(portal)" suffix). For worker channels this is the
    STB portal from the token; for direct playlist channels it is the host
    of the stream URL itself, not the M3U playlist domain.
    """
    if not url:
        return ""
    try:
        raw = url.split("|", 1)[0].strip()
        parsed = urlparse(raw)
        if not parsed.hostname:
            return ""
        scheme = parsed.scheme or "http"
        if parsed.port:
            return f"{scheme}://{parsed.hostname}:{parsed.port}"
        return f"{scheme}://{parsed.hostname}"
    except Exception:
        return ""


def _title_with_domain(name: str, url: str) -> str:
    domain = _domain_of(url)
    if domain:
        return f"{name}  ({domain})"
    return name


def _host_of(url: str) -> str:
    if not url:
        return ""
    try:
        return (urlparse(url.split("|", 1)[0]).hostname or "").lower()
    except Exception:
        return ""


def _domain_excluded(url: str) -> bool:
    """True if url's host matches any entry in EXCLUDE_DOMAINS (subdomains match)."""
    host = _host_of(url)
    if not host or not EXCLUDE_DOMAINS:
        return False
    for domain in EXCLUDE_DOMAINS:
        d = (domain or "").strip().lower().lstrip(".")
        if not d:
            continue
        if host == d or host.endswith("." + d):
            return True
    return False


def _channel_excluded(ch: dict) -> bool:
    """True if the channel should be hidden from listings."""
    if HIDE_DEFAULT_COLOR and (ch.get("source_color") or "") == DEFAULT_COLOR:
        return True
    if _domain_excluded(ch.get("url", "")):
        return True
    if _domain_excluded(ch.get("portal", "")):
        return True
    return False


class SportsX(JetExtractor):
    def __init__(self):
        self.domains = ["sportsx://", "gojoportaltom3u.gojosare123.workers.dev", "raw.githubusercontent.com"]
        self.name = "SportsX"
        self.short_name = "SX"
        self.resolve_only = False
        self._proxy = None

    def _get_proxy(self):
        if self._proxy is None:
            self._proxy = get_stream_proxy(
                "SportsX",
                {"User-Agent": BROWSER_UA},
                options={"cache_manifest": True, "manifest_ttl": 5.0}
            )
        return self._proxy

    def _build_proxy_link(self, worker_url: str) -> str:
        """Build a proxy link for a worker URL with a refresh callback.

        The worker URL returns an m3u8 with a short-lived token (~20s).
        The refresh_callback re-fetches from the worker URL to get a fresh
        token when the proxy refreshes the manifest.
        """
        _parsed = urlparse(worker_url)
        _origin = f"{_parsed.scheme}://{_parsed.netloc}"
        headers = {"User-Agent": BROWSER_UA, "Referer": worker_url, "Origin": _origin}

        def _refresh():
            """Re-fetch from the worker URL to get a fresh token.

            Simply returns the worker URL so the proxy re-fetches the full
            manifest through the worker, which generates a fresh token each time.
            """
            return {"url": worker_url, "headers": headers}

        return self._get_proxy().get_proxy_url(worker_url, headers, refresh_callback=_refresh)

    def is_available(self, url: JetLink) -> bool:
        addr = url.address
        if addr.startswith("sportsx://"):
            return True
        if WORKER_URL_RE.match(addr):
            return True
        if GITHUB_M3U_RE.search(addr):
            return True
        return False

    def get_items(self, params=None, progress=None):
        items = []
        if self.progress_init(progress, items):
            return items
        
        # Manual refresh trigger
        if params and params.get("refresh"):
            debug_log("[SportsX] Manual refresh triggered")
            from ..tools import is_store_notifications_enabled
            if is_store_notifications_enabled():
                import xbmcgui
                xbmcgui.Dialog().notification(
                    "SportsX",
                    "Refreshing channels...",
                    xbmcgui.NOTIFICATION_INFO,
                    3000,
                )
            t = threading.Thread(target=_background_scrape, daemon=True)
            t.start()
            return items

        data = sportsx_store.load_channels()
        if not data.get("channels"):
            debug_log("[SportsX] No cached channels, performing synchronous fetch")
            import xbmcgui
            xbmcgui.Dialog().notification(
                "SportsX",
                "Fetching channels...",
                xbmcgui.NOTIFICATION_INFO,
                5000,
            )
            count = scrape_sportsx_sources()
            data = sportsx_store.load_channels()
            if not data.get("channels"):
                debug_log("[SportsX] Still no channels after scrape, returning empty")
                return items
            channels = data.get("channels", [])
            debug_log(f"[SportsX] {len(channels)} channels loaded")
            self.progress_update(progress, "Returning scraped channels")
            status = "scraped"
        elif _needs_scrape():
            debug_log("[SportsX] Channels stale, performing synchronous refresh")
            from ..tools import is_store_notifications_enabled
            if is_store_notifications_enabled():
                import xbmcgui
                xbmcgui.Dialog().notification(
                    "SportsX",
                    "Refreshing channels...",
                    xbmcgui.NOTIFICATION_INFO,
                    5000,
                )
            count = scrape_sportsx_sources()
            data = sportsx_store.load_channels()
            if not data.get("channels"):
                debug_log("[SportsX] Still no channels after refresh, returning empty")
                return items
            channels = data.get("channels", [])
            debug_log(f"[SportsX] {len(channels)} channels after refresh")
            self.progress_update(progress, "Returning refreshed channels")
            status = "refreshed"
        else:
            channels = data.get("channels", [])
            debug_log(f"[SportsX] {len(channels)} channels from cache")
            self.progress_update(progress, "Returning cached channels")
            status = "cached"

        items.append(JetItem(
            title="[B]Refresh SportsX[/B]",
            links=[JetLink("sportsx://refresh", links=True)],
            league="SportsX",
        ))

        worker_by_portal = {}
        direct_channels = []

        for ch in channels:
            if _channel_excluded(ch):
                continue
            if ch.get("channel_type") == "worker":
                portal = ch.get("portal", "Unknown")
                if portal not in worker_by_portal:
                    worker_by_portal[portal] = []
                worker_by_portal[portal].append(ch)
            else:
                direct_channels.append(ch)

        for portal, portal_channels in sorted(worker_by_portal.items()):
            for ch in portal_channels:
                worker_url = ch.get("url", "")
                if not worker_url:
                    continue
                encoded_url = base64.urlsafe_b64encode(worker_url.encode()).decode()
                watch_url = f"sportsx://watch?u={encoded_url}"
                items.append(JetItem(
                    title=f"{_title_with_domain(ch['name'], portal)}  [COLORyellow][MAC][/COLOR]",
                    links=[JetLink(watch_url, links=True)],
                    league="SportsX",
                ))

        for ch in direct_channels:
            stream_url = ch.get("url", "")
            ch_headers = ch.get("headers", {})
            if ch_headers:
                pipe_parts = []
                if "Referer" in ch_headers:
                    referer = ch_headers["Referer"]
                    pipe_parts.append(f"referer={referer}")
                    if "Origin" not in ch_headers and referer:
                        _parsed_ref = urlparse(referer)
                        ch_headers["Origin"] = f"{_parsed_ref.scheme}://{_parsed_ref.netloc}"
                if "Origin" in ch_headers:
                    pipe_parts.append(f"origin={ch_headers['Origin']}")
                if "User-Agent" in ch_headers:
                    pipe_parts.append(f"user-agent={ch_headers['User-Agent']}")
                if pipe_parts:
                    stream_url = f"{stream_url}|{'&'.join(pipe_parts)}"
            title = _title_with_domain(ch["name"], ch.get("url", ""))
            items.append(JetItem(
                title=title,
                links=[JetLink(
                    stream_url,
                    direct=True,
                    inputstream=JetInputstreamFFmpegDirect.default(),
                )],
                league="SportsX",
            ))

        return items

    def get_links(self, url):
        addr = url.address
        if addr == "sportsx://refresh":
            debug_log("[SportsX] Manual refresh triggered via link")
            from ..tools import is_store_notifications_enabled
            if is_store_notifications_enabled():
                import xbmcgui
                xbmcgui.Dialog().notification(
                    "SportsX",
                    "Refreshing channels...",
                    xbmcgui.NOTIFICATION_INFO,
                    3000,
                )
            t = threading.Thread(target=_background_scrape, daemon=True)
            t.start()
            return []
        if addr.startswith("sportsx://portal"):
            return self._get_portal_links(url)
        if addr.startswith("sportsx://watch"):
            return self._get_watch_links(url)
        if GITHUB_M3U_RE.search(addr):
            return self._get_source_links(addr)
        return []

    def _get_watch_links(self, url):
        """Resolve a flat worker-channel item (sportsx://watch?u=...) via the proxy."""
        query = parse_qs(urlparse(url.address).query)
        encoded_url = query.get("u", [None])[0]
        if not encoded_url:
            return []
        try:
            worker_url = base64.urlsafe_b64decode(encoded_url).decode()
        except Exception:
            return []
        if not WORKER_URL_RE.match(worker_url):
            return []
        proxy_url = self._build_proxy_link(worker_url)
        return [JetLink(
            proxy_url,
            direct=True,
            inputstream=JetInputstreamAdaptive.hls(),
        )]

    def _get_source_links(self, source_url):
        results = []
        try:
            text = _fetch_m3u(source_url)
            if not text:
                return results
            channels = parse_m3u(text)
            for ch in channels:
                if _channel_excluded(ch):
                    continue
                stream_url = ch.get("url", "")
                if not stream_url:
                    continue
                ch_headers = ch.get("headers", {})
                # Worker channels: origin is the STB portal, not the worker URL.
                # Direct channels: origin is the host of the stream URL itself.
                if ch.get("channel_type") == "worker":
                    title = f"{_title_with_domain(ch['name'], ch.get('portal', ''))}  [COLORyellow][MAC][/COLOR]"
                else:
                    title = _title_with_domain(ch["name"], stream_url)
                if ch.get("channel_type") == "worker":
                    proxy_url = self._build_proxy_link(stream_url)
                    results.append(JetLink(
                        proxy_url,
                        name=title,
                        headers=ch_headers,
                        direct=True,
                        inputstream=JetInputstreamAdaptive.hls(),
                    ))
                else:
                    if ch_headers:
                        pipe_parts = []
                        if "Referer" in ch_headers:
                            referer = ch_headers["Referer"]
                            pipe_parts.append(f"referer={referer}")
                            if "Origin" not in ch_headers and referer:
                                _parsed_ref = urlparse(referer)
                                ch_headers["Origin"] = f"{_parsed_ref.scheme}://{_parsed_ref.netloc}"
                        if "Origin" in ch_headers:
                            pipe_parts.append(f"origin={ch_headers['Origin']}")
                        if "User-Agent" in ch_headers:
                            pipe_parts.append(f"user-agent={ch_headers['User-Agent']}")
                        if pipe_parts:
                            stream_url = f"{stream_url}|{'&'.join(pipe_parts)}"
                    results.append(JetLink(
                        stream_url,
                        name=title,
                        direct=True,
                        inputstream=JetInputstreamFFmpegDirect.default(),
                    ))
        except Exception as e:
            debug_log(f"[SportsX] Failed to parse source {source_url}: {e}")
        return results

    def _get_portal_links(self, url):
        query = parse_qs(urlparse(url.address).query)
        encoded_portal = query.get("portal", [None])[0]
        if not encoded_portal:
            return []
        try:
            portal = base64.urlsafe_b64decode(encoded_portal).decode()
        except Exception:
            return []

        data = sportsx_store.load_channels()
        channels = data.get("channels", [])
        results = []
        for ch in channels:
            if ch.get("portal") != portal:
                continue
            if _channel_excluded(ch):
                continue
            worker_url = ch.get("url", "")
            if worker_url:
                proxy_url = self._build_proxy_link(worker_url)
                # Worker channel origin is the STB portal, not the worker URL.
                title = f"{_title_with_domain(ch['name'], portal)}  [COLORyellow][MAC][/COLOR]"
                results.append(JetLink(
                    proxy_url,
                    name=title,
                    direct=True,
                    inputstream=JetInputstreamAdaptive.hls(),
                ))
        return results

    def get_link(self, url):
        addr = url.address

        if addr.startswith("sportsx://"):
            return url

        if WORKER_URL_RE.match(addr):
            proxy_url = self._build_proxy_link(addr)
            return JetLink(
                proxy_url,
                direct=True,
                inputstream=JetInputstreamAdaptive.hls(),
            )

        if GITHUB_M3U_RE.search(addr):
            return JetLink(addr, links=True)

        return url
