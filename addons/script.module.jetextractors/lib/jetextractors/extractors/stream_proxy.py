import gzip
import re
import selectors
import socket
import threading
import time
import uuid
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, urljoin, parse_qs, quote, unquote

import requests
import xbmc
from ..tools import debug_log
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class _ProxyTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ssl_version=ssl.PROTOCOL_TLS)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = False
        context.set_ciphers(
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256:"
            "ECDHE-ECDSA-AES128-GCM-SHA256:"
            "ECDHE-RSA-AES128-GCM-SHA256:"
            "ECDHE-ECDSA-AES256-GCM-SHA384:"
            "ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-CHACHA20-POLY1305"
        )
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


PNG_SIG = b'\x89PNG\r\n\x1a\n'
WEBP_SIG = b'RIFF'
WEBP_LABEL = b'WEBP'


def _strip_png(data: bytes) -> bytes:
    """Remove a PNG wrapper that precedes the actual MPEG-TS payload."""
    if not data.startswith(PNG_SIG):
        return _strip_webp(data)
    offset = len(PNG_SIG)
    chunk_count = 0
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            break
        chunk_count += 1
        if chunk_type == b'IEND':
            video_start = chunk_end
            if video_start < len(data):
                return data[video_start:]
            return b''
        offset = chunk_end
    return data


def _strip_webp(data: bytes) -> bytes:
    """Remove a WebP wrapper that precedes the actual MPEG-TS payload."""
    if not data.startswith(WEBP_SIG) or len(data) < 12 or data[8:12] != WEBP_LABEL:
        return data
    # RIFF header: 4 bytes "RIFF" + 4 bytes file size + 4 bytes "WEBP"
    file_size = int.from_bytes(data[4:8], "little")
    # TS sync byte is 0x47; scan after RIFF header for first 0x47
    search_start = 12
    search_end = min(12 + file_size, len(data))
    # Also look further in case RIFF size is wrong
    search_end = max(search_end, min(len(data), 8192))
    for i in range(search_start, search_end):
        if data[i] == 0x47 and i + 188 <= len(data):
            # Verify TS sync pattern (0x47 appears every 188 bytes)
            if i + 376 <= len(data) and data[i + 188] == 0x47:
                return data[i:]
    return data


def _decompress(data: bytes) -> bytes:
    """Best-effort gzip/zlib decompression."""
    try:
        if data[:2] == b'\x1f\x8b':
            return gzip.decompress(data)
        elif data[:2] in (b'\x78\x9c', b'\x78\x01', b'\x78\xda'):
            return zlib.decompress(data)
    except Exception:
        pass
    return data


def _rewrite_png_to_ts(url: str) -> str:
    result = url.replace(".png", ".ts").replace(".PNG", ".TS")
    idx = result.rfind(".image")
    if idx != -1:
        result = result[:idx] + ".ts" + result[idx + 6:]
    return result


def _rewrite_png_to_image(url: str) -> str:
    """Convert .png extension to .image so the CDN serves WebP instead of 403."""
    lower = url.lower()
    idx = lower.rfind(".png")
    if idx != -1:
        return url[:idx] + ".image" + url[idx + 4:]
    return url


def _rewrite_ts_to_png(url: str) -> str:
    if ".ts?" in url or ".TS?" in url:
        return url.replace(".ts?", ".png?").replace(".TS?", ".png?")
    if url.endswith(".ts") or url.endswith(".TS"):
        return url[:-3] + ".png"
    return url


def _is_variant_playlist(body: str) -> bool:
    has_stream_inf = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#EXT-X-STREAM-INF"):
            has_stream_inf = True
        elif stripped.startswith("#EXTINF"):
            return False
    return has_stream_inf


def _resolve_variant_to_media(body: str, base_url: str, session: requests.Session,
                              headers: dict, depth: int = 0) -> str:
    if depth > 5:
        return body
    if not _is_variant_playlist(body):
        return body

    best_variant_url = None
    best_bandwidth = -1
    # Collect #EXT-X-MEDIA tags (e.g. AUDIO renditions) so they aren't lost
    # when we resolve to a single variant.
    media_tags = []

    lines = body.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#EXT-X-MEDIA"):
            media_tags.append(stripped)
        if stripped.startswith("#EXT-X-STREAM-INF"):
            bw = 0
            m = re.search(r'BANDWIDTH=(\d+)', stripped)
            if m:
                bw = int(m.group(1))
            if i + 1 < len(lines):
                variant_line = lines[i + 1].strip()
                if variant_line and not variant_line.startswith("#"):
                    variant_url = urljoin(base_url, variant_line)
                    if best_variant_url is None or bw > best_bandwidth:
                        best_variant_url = variant_url
                        best_bandwidth = bw
            i += 2
            continue
        i += 1

    if not best_variant_url:
        return body

    debug_log(f"[StreamProxy] Resolving best variant (depth={depth}, bw={best_bandwidth}): {best_variant_url}", xbmc.LOGINFO)
    try:
        child_resp = session.get(best_variant_url, headers=headers, timeout=(5, 15), stream=True)
        if child_resp.status_code != 200:
            debug_log(f"[StreamProxy] Variant child returned {child_resp.status_code}: {best_variant_url}", xbmc.LOGWARNING)
            return body
        raw_bytes = b""
        for chunk in child_resp.iter_content(chunk_size=8192):
            raw_bytes += chunk
            if len(raw_bytes) > 256 * 1024:
                break
        child_resp.close()
        child_body = raw_bytes.decode("utf-8", errors="replace").replace("\x00", "")
        if not child_body or "#EXTM3U" not in child_body:
            return body
        if _is_variant_playlist(child_body):
            child_body = _resolve_variant_to_media(child_body, best_variant_url, session, headers, depth + 1)
        if "#EXTINF" in child_body:
            # Prepend any #EXT-X-MEDIA tags (e.g. AUDIO) from the master
            # so ISA can still find the audio rendition.
            if media_tags:
                header, _, rest = child_body.partition("\n")
                child_body = header + "\n" + "\n".join(media_tags) + "\n" + rest
            return child_body
    except Exception as e:
        debug_log(f"[StreamProxy] Variant child fetch failed: {e}", xbmc.LOGWARNING)
    return body


def _hashable_options(options: dict):
    return frozenset((k, v) for k, v in (options or {}).items())


# -- Segment prefetch machinery (option: prefetch_segments) ------------------
# See ISSUE_BUFFERING.md: FFmpeg's native HLS client downloads segments one at
# a time (depth 1); the proxy prefetches the next segment in the background so
# the effective pipeline depth becomes 2 and cache hits are served instantly.

def _seg_cache_get(entry, url):
    cache = entry.get("seg_cache")
    if not cache:
        return None
    return cache.get(url)


def _seg_cache_put(entry, url, data, content_type, cap=4):
    cache = entry.setdefault("seg_cache", {})
    if url not in cache:
        while len(cache) >= cap:
            cache.pop(next(iter(cache)))
    cache[url] = (data, content_type)


def _seg_inflight_register(entry, url):
    """Register an in-flight segment download for *url*.

    Returns None when the CALLER owns the download (and must later call
    _seg_inflight_done), or an Event to wait on when another thread already
    owns it.
    """
    inflight = entry.setdefault("seg_inflight", {})
    ev = inflight.get(url)
    if ev is not None:
        return ev
    ev = threading.Event()
    inflight[url] = ev
    return None


def _seg_inflight_done(entry, url):
    inflight = entry.get("seg_inflight")
    if inflight is not None:
        ev = inflight.pop(url, None)
        if ev is not None:
            ev.set()


def _prefetch_segment(proxy, entry, url):
    """Background download of one segment into the token's cache."""
    ev = _seg_inflight_register(entry, url)
    if ev is not None:
        return  # someone else (live handler or another prefetcher) owns it
    try:
        if proxy._abort.is_set() or _seg_cache_get(entry, url) is not None:
            return
        headers = entry.get("headers") or {}
        seg_headers = dict(proxy.default_headers)
        seg_headers.update(headers)
        if proxy.upstream_user_agent:
            seg_headers["User-Agent"] = proxy.upstream_user_agent
        seg_headers.setdefault("Accept", "*/*")
        if not proxy.upstream_keep_alive:
            seg_headers.setdefault("Connection", "close")

        if proxy.segment_strip_origin:
            target_domain = urlparse(url).netloc
            manifest_domain = urlparse(entry["url"]).netloc
            if target_domain and manifest_domain and target_domain != manifest_domain:
                seg_headers.pop("Origin", None)
                seg_headers.pop("Referer", None)

        client = entry.get("session")
        if client is None:
            client = requests
            if proxy.browser_tls:
                client = requests.Session()
                client.verify = False
                client.mount("https://", _ProxyTLSAdapter())
        try:
            resp = client.get(url, headers=seg_headers, timeout=(3, 15), stream=True, allow_redirects=True)
        except Exception as e:
            debug_log(f"[{proxy.name}] Prefetch request failed for {url}: {e}", xbmc.LOGDEBUG)
            return
        if resp.status_code not in (200, 206):
            debug_log(f"[{proxy.name}] Prefetch got status {resp.status_code} for {url}", xbmc.LOGDEBUG)
            resp.close()
            return
        data = b""
        try:
            for chunk in resp.iter_content(chunk_size=proxy.chunk_size):
                if proxy._abort.is_set():
                    return
                if chunk:
                    data += chunk
                    if len(data) > proxy.max_segment_size:
                        break
        except Exception as e:
            debug_log(f"[{proxy.name}] Prefetch download error for {url}: {e}", xbmc.LOGDEBUG)
            return
        finally:
            resp.close()
        if proxy._abort.is_set():
            return
        ctype = resp.headers.get("Content-Type", "")
        _seg_cache_put(entry, url, data, ctype)
        debug_log(f"[{proxy.name}] Prefetched segment: {len(data)} bytes ({url})", xbmc.LOGINFO)
    finally:
        _seg_inflight_done(entry, url)


class StreamProxy:
    """Local HTTP proxy that rewrites HLS manifests and proxies segments.

    Options (all optional, defaults shown):
        manifest_png_to_ts (False): Rewrite .png segment refs to .ts in the
            manifest served to Kodi.
        fetch_png_segments (False): When fetching upstream segments, rewrite
            .ts back to .png (use with strip_png for TikTok-style wrappers).
        proxy_absolute_urls (True): Rewrite absolute segment/playlist URLs so
            they also flow through the proxy. Set False to leave absolute URLs
            untouched (matches the original RoxieStreams behaviour).
        strip_png (False): Strip PNG wrappers from segment payloads.
        user_agent (None): If set, override the User-Agent header for all
            upstream requests (manifest and segment fetches). Useful for
            CDNs that filter by UA (e.g. Samsung TV UA for strmd.st).
        cache_manifest (True): Cache the rewritten manifest for manifest_ttl
            seconds to avoid hammering the upstream playlist.
        manifest_ttl (2.0): Manifest cache lifetime.
        add_icy_metadata (True): Add Icy-MetaData header to upstream requests.
        request_timeout ((5, 30)): requests timeout tuple.
        max_manifest_size (262144): Maximum bytes to read for a manifest.
        max_segment_size (33554432): Maximum bytes to buffer when stripping PNG.
        chunk_size (65536): Chunk size for streaming/buffering.
    """

    def __init__(self, name: str, default_headers: dict, options: dict = None):
        self.name = name
        self.default_headers = dict(default_headers) if default_headers else {}
        opts = dict(options) if options else {}

        self.manifest_png_to_ts = opts.get("manifest_png_to_ts", False)
        self.fetch_png_segments = opts.get("fetch_png_segments", False)
        self.proxy_absolute_urls = opts.get("proxy_absolute_urls", True)
        self.strip_png = opts.get("strip_png", False)
        self.cache_manifest = opts.get("cache_manifest", True)
        self.manifest_ttl = opts.get("manifest_ttl", 2.0)
        self.keep_alive = opts.get("keep_alive", True)
        self.add_icy_metadata = opts.get("add_icy_metadata", True)
        self.browser_tls = opts.get("browser_tls", False)
        self.request_timeout = opts.get("request_timeout", (3, 8))
        self.max_manifest_size = opts.get("max_manifest_size", 256 * 1024)
        self.max_segment_size = opts.get("max_segment_size", 32 * 1024 * 1024)
        self.chunk_size = opts.get("chunk_size", 64 * 1024)
        self.upstream_user_agent = opts.get("user_agent", None)
        # upstream_keep_alive (False): when True, do not force Connection: close
        # on upstream manifest/segment requests, so the per-token requests
        # session pool reuses TCP+TLS connections to the CDN (saves a
        # handshake on every segment).
        self.upstream_keep_alive = opts.get("upstream_keep_alive", False)
        # prefetch_segments (False): when True, background-prefetch the next
        # manifest segment on each segment request, serving it from a small
        # in-memory cache. Counters the depth-1 serialized segment pipeline of
        # FFmpeg's native HLS client (see ISSUE_BUFFERING.md).
        self.prefetch_segments = opts.get("prefetch_segments", False)
        # segment_strip_origin (False): When True, strip Origin and Referer
        # headers from segment requests when the target domain differs from
        # the manifest domain. Useful for CDNs that block cross-origin requests.
        self.segment_strip_origin = opts.get("segment_strip_origin", False)

        self._server = None
        self._thread = None
        self._port = None
        self._lock = threading.Lock()
        self._upstream = {}
        self._abort = threading.Event()
        self._last_activity = time.time()
        self._watchdog_thread = None
        self._client_sockets = set()
        self._client_sockets_lock = threading.Lock()

    def _ensure_server(self) -> int:
        with self._lock:
            if self._server is not None:
                return self._port
            self._abort.clear()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            sock.close()

            proxy = self

            class _Handler(BaseHTTPRequestHandler):
                # HTTP/1.1 enables keep-alive by default. FFmpeg keeps the manifest
                # connection open and re-fetches periodically. When Kodi kills the
                # player it closes the socket → readline() returns empty → handler
                # exits → FFmpeg gets immediate connection reset (<100ms cleanup).
                protocol_version = "HTTP/1.1"

                def log_message(self, format, *args):
                    pass

                def _fail(self, code: int, body: bytes) -> None:
                    try:
                        self.send_response(code)
                        self.send_header("Content-Type", "text/plain")
                        self.send_header("Content-Length", str(len(body)))
                        self.send_header("Connection", "close")
                        self.end_headers()
                        self.wfile.write(body)
                    except Exception as e:
                        debug_log(f"[{proxy.name}] proxy _fail write error: {e}", xbmc.LOGDEBUG)

                def do_GET(self):
                    try:
                        self._handle(head_only=False)
                    except Exception as e:
                        debug_log(f"[{proxy.name}] do_GET exception: {type(e).__name__}: {e}", xbmc.LOGWARNING)
                        try:
                            self._fail(500, b"Internal proxy error")
                        except Exception:
                            pass

                def do_HEAD(self):
                    try:
                        self._handle(head_only=True)
                    except Exception as e:
                        debug_log(f"[{proxy.name}] do_HEAD exception: {type(e).__name__}: {e}", xbmc.LOGWARNING)
                        try:
                            self._fail(500, b"Internal proxy error")
                        except Exception:
                            pass

                def _handle(self, head_only: bool):
                    # Track this client socket so shutdown() can force-close it
                    # immediately instead of letting FFmpeg block ~20s on its
                    # internal TCP timeout after player close.
                    with proxy._client_sockets_lock:
                        proxy._client_sockets.add(self.connection)
                    try:
                        proxy._last_activity = time.time()
                        if proxy._abort.is_set():
                            self._fail(503, b"Proxy shutting down")
                            return
                        raw_path = self.path.split("?")[0].lstrip("/")
                        prefix = f"{proxy.name}/"
                        seg_prefix = f"{proxy.name}/seg/"

                        debug_log(f"[{proxy.name}] _handle {'HEAD' if head_only else 'GET'} path={self.path[:120]}", xbmc.LOGDEBUG)

                        if raw_path.startswith(prefix) and (raw_path.endswith(".m3u8") or raw_path.endswith(".mpd")):
                            # When keep_alive=False (e.g. inputstream.adaptive),
                            # close connections immediately so the handler thread
                            # exits fast. This prevents Kodi's CCurlFile::Stat
                            # from timing out on the proxy URL after player close.
                            # When keep_alive=True (inputstream.ffmpegdirect),
                            # keep connections open for FFmpeg's periodic re-fetches.
                            if proxy.keep_alive:
                                try:
                                    self.connection.settimeout(15)
                                except Exception:
                                    pass
                            else:
                                try:
                                    self.connection.settimeout(3)
                                except Exception:
                                    pass
                            self._serve_manifest(head_only=head_only)
                        elif raw_path.startswith(seg_prefix):
                            # Segments: short timeout so broken pipes are detected fast.
                            try:
                                self.connection.settimeout(3)
                            except Exception:
                                pass
                            self._serve_segment(head_only=head_only)
                        else:
                            self._fail(404, b"Not found")
                    finally:
                        with proxy._client_sockets_lock:
                            proxy._client_sockets.discard(self.connection)

                def _serve_manifest(self, head_only: bool):
                    raw_path = self.path.split("?")[0].lstrip("/")
                    is_dmpd = raw_path.endswith(".mpd")
                    ext_len = len(".mpd") if is_dmpd else len(".m3u8")
                    token = raw_path[len(f"{proxy.name}/"):-ext_len]
                    entry = proxy._upstream.get(token)
                    if not entry:
                        self._fail(404, b"Token not found")
                        return

                    # HEAD requests (Kodi VFS stat checks, curl-based) must never
                    # trigger upstream fetches. After the player closes, Kodi's
                    # CCurlFile::Stat sends a HEAD to the manifest URL. If the
                    # 2-second cache has expired, the proxy re-fetches from
                    # upstream which can hang for 20+ seconds on expired tokens,
                    # freezing the UI. Serving from cache (or minimal headers)
                    # returns instantly.
                    if head_only:
                        cached = entry.get("cache")
                        if cached:
                            content_type = "application/dash+xml" if is_dmpd else "application/vnd.apple.mpegurl"
                            self.send_response(200)
                            self.send_header("Content-Type", content_type)
                            self.send_header("Content-Length", str(len(cached)))
                            self.send_header("Access-Control-Allow-Origin", "*")
                            if not proxy.keep_alive:
                                self.send_header("Connection", "close")
                            self.end_headers()
                        else:
                            self.send_response(200)
                            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            if not proxy.keep_alive:
                                self.send_header("Connection", "close")
                            self.end_headers()
                        debug_log(f"[{proxy.name}] HEAD manifest served from cache ({'cached' if cached else 'empty'})", xbmc.LOGINFO)
                        return

                    upstream_url = entry["url"]
                    headers = entry.get("headers") or {}
                    port = proxy._port
                    now = time.time()

                    cached = entry.get("cache")
                    cache_time = entry.get("cache_time", 0.0)
                    cache_age = now - cache_time if cache_time > 0 else float('inf')

                    # Stale-while-revalidate: if we have ANY cached data, serve it
                    # immediately and refresh in background. This prevents the proxy
                    # from blocking on slow upstream fetches after player close.
                    if proxy.cache_manifest and cached and cache_age < proxy.manifest_ttl:
                        # Fresh cache: serve directly
                        data = cached
                        content_type = "application/dash+xml" if raw_path.endswith(".mpd") else "application/vnd.apple.mpegurl"
                        debug_log(f"[{proxy.name}] Serving fresh cached manifest ({len(data)} bytes, age={cache_age:.1f}s)", xbmc.LOGINFO)
                    elif proxy.cache_manifest and cached:
                        # Stale cache: serve immediately, refresh in background
                        data = cached
                        content_type = "application/dash+xml" if raw_path.endswith(".mpd") else "application/vnd.apple.mpegurl"
                        debug_log(f"[{proxy.name}] Serving stale cached manifest ({len(data)} bytes, age={cache_age:.1f}s), refreshing in background", xbmc.LOGINFO)

                        # Background refresh: spawn a thread to update the cache
                        def _refresh_cache():
                            try:
                                self._refresh_manifest_cache(entry, token, raw_path)
                            except Exception as e:
                                debug_log(f"[{proxy.name}] Background manifest refresh failed: {e}", xbmc.LOGWARNING)

                        refresh_thread = threading.Thread(target=_refresh_cache, name=f"{proxy.name}Refresh")
                        refresh_thread.daemon = True
                        refresh_thread.start()
                    else:
                        # No cache: fetch from upstream (blocking)
                        data, content_type = self._fetch_manifest_upstream(entry, token, raw_path, headers, port, head_only)
                        if data is None:
                            return
                        entry["cache"] = data
                        entry["cache_time"] = now

                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Cache-Control", "no-store")
                    if not proxy.keep_alive:
                        self.send_header("Connection", "close")
                    self.end_headers()
                    if not head_only:
                        try:
                            self.wfile.write(data)
                            self.wfile.flush()
                        except (ConnectionAbortedError, BrokenPipeError):
                            pass

                def _fetch_manifest_upstream(self, entry, token, raw_path, headers, port, head_only):
                    """Fetch manifest from upstream. Returns (data, content_type) or (None, None) on failure."""
                    upstream_url = entry["url"]
                    urls_to_try = [upstream_url] + (entry.get("fallback_urls") or [])
                    working_url = None
                    body = None

                    token_session = requests.Session()
                    if proxy.browser_tls:
                        token_session.verify = False
                        token_session.mount("https://", _ProxyTLSAdapter())
                    entry["session"] = token_session
                    request_client = token_session

                    for try_url in urls_to_try:
                        try:
                            req_headers = dict(proxy.default_headers)
                            req_headers.update(headers)
                            if proxy.upstream_user_agent:
                                req_headers["User-Agent"] = proxy.upstream_user_agent
                            req_headers.setdefault("Accept", "*/*")
                            req_headers.setdefault("Accept-Language", "en-US,en;q=0.9")
                            if not proxy.upstream_keep_alive:
                                req_headers.setdefault("Connection", "close")
                            if proxy.add_icy_metadata:
                                req_headers.setdefault("Icy-MetaData", "1")
                            debug_log(f"[{proxy.name}] Requesting {try_url} with headers: {req_headers}", xbmc.LOGINFO)

                            resp = request_client.get(
                                try_url,
                                timeout=proxy.request_timeout,
                                headers=req_headers,
                                stream=True,
                            )
                            debug_log(f"[{proxy.name}] Upstream response: {resp.status_code} for {try_url}", xbmc.LOGINFO)
                            if resp.status_code != 200:
                                debug_log(f"[{proxy.name}] Upstream error {resp.status_code}: {resp.text[:200]}", xbmc.LOGWARNING)
                                resp.close()
                                continue

                            raw_bytes = b""
                            for chunk in resp.iter_content(chunk_size=8192):
                                if proxy._abort.is_set():
                                    resp.close()
                                    debug_log(f"[{proxy.name}] Manifest fetch aborted", xbmc.LOGINFO)
                                    return None, None
                                raw_bytes += chunk
                                if len(raw_bytes) > proxy.max_manifest_size:
                                    break
                            resp.close()

                            raw_bytes = _decompress(raw_bytes)
                            body = raw_bytes.decode("utf-8", errors="replace").replace("\x00", "")
                            debug_log(f"[{proxy.name}] Upstream body length: {len(body)}", xbmc.LOGINFO)
                            is_hls = "#EXTM3U" in body
                            is_dash = "<?xml" in body[:500] or "<MPD" in body[:500] or "MPD" in body[:200]
                            if not body or (not is_hls and not is_dash):
                                debug_log(f"[{proxy.name}] Upstream body invalid: {body[:200]}", xbmc.LOGWARNING)
                                continue

                            working_url = resp.url
                            break
                        except Exception as e:
                            debug_log(f"[{proxy.name}] Upstream fetch failed for {try_url}: {e}", xbmc.LOGWARNING)
                            continue

                    if not working_url:
                        self._fail(502, b"All upstream URLs failed")
                        return None, None

                    is_hls = "#EXTM3U" in body
                    if is_hls:
                        # If the master playlist has #EXT-X-MEDIA audio renditions,
                        # don't resolve to a single variant - let ISA handle the full
                        # master so it can select audio+video separately.
                        has_media_audio = any(
                            "TYPE=AUDIO" in line.upper()
                            for line in body.splitlines()
                            if line.strip().startswith("#EXT-X-MEDIA")
                        )
                        if _is_variant_playlist(body) and not has_media_audio:
                            request_client_inner = entry.get("session")
                            if request_client_inner is None:
                                request_client_inner = requests
                                if proxy.browser_tls:
                                    request_client_inner = requests.Session()
                                    request_client_inner.verify = False
                                    request_client_inner.mount("https://", _ProxyTLSAdapter())
                            variant_headers = dict(proxy.default_headers)
                            variant_headers.update(headers)
                            variant_headers.setdefault("Accept", "*/*")
                            resolved = _resolve_variant_to_media(body, working_url, request_client_inner, variant_headers)
                            if resolved is not body:
                                body = resolved
                                debug_log(f"[{proxy.name}] Resolved variant playlist to media playlist ({len(body.splitlines())} lines)", xbmc.LOGINFO)
                    # Apply png-to-ts rewrite AFTER variant resolution so it
                    # processes the actual media playlist segment URLs.
                    # NOTE: _rewrite_png_to_image in the encoding loop handles
                    # .png→.image conversion for segment URLs. The manifest body
                    # rewrite is only needed when the CDN serves actual PNG-wrapped
                    # TS (not WebP-wrapped), so skip it when strip_png is active.
                    if proxy.manifest_png_to_ts and not proxy.strip_png:
                        body = _rewrite_png_to_ts(body)
                    if is_hls:
                        # HLS manifest: rewrite segment refs to proxy
                        rewritten = []
                        seg_urls = []
                        parsed_upstream = urlparse(working_url)
                        upstream_root = f"{parsed_upstream.scheme}://{parsed_upstream.netloc}"
                        for line in body.splitlines():
                            stripped = line.strip()
                            if not stripped:
                                continue
                            if stripped.startswith("#"):
                                # Rewrite URI attributes in HLS tags (#EXT-X-MEDIA,
                                # #EXT-X-MAP, #EXT-X-KEY, etc.) so ISA fetches
                                # them through the proxy instead of upstream.
                                if proxy.proxy_absolute_urls and "URI=" in stripped.upper():
                                    def _rewrite_hls_uri(m):
                                        quote_char = m.group(1)
                                        uri_val = m.group(2)
                                        if uri_val.startswith("http://") or uri_val.startswith("https://"):
                                            return f'URI={quote_char}{uri_val}{quote_char}'
                                        if uri_val.startswith("/"):
                                            uri_val = f"{upstream_root}{uri_val}"
                                        else:
                                            uri_val = urljoin(working_url, uri_val)
                                        return f'URI={quote_char}http://127.0.0.1:{port}/{proxy.name}/seg/{token}/{quote(_rewrite_png_to_image(uri_val), safe="")}{quote_char}'
                                    stripped = re.sub(r'URI=(["\'])([^"\']*)\1', _rewrite_hls_uri, stripped)
                                rewritten.append(stripped)
                                continue
                            if not proxy.proxy_absolute_urls and (
                                stripped.startswith("http://") or stripped.startswith("https://")
                            ):
                                rewritten.append(line)
                                continue
                            # Root-relative segment refs need an absolute base to resolve
                            # correctly through the proxy.
                            if stripped.startswith("/"):
                                stripped = f"{upstream_root}{stripped}"
                            rewritten.append(
                                f"http://127.0.0.1:{port}/{proxy.name}/seg/{token}/{quote(_rewrite_png_to_image(stripped), safe='')}"
                            )
                            # Track the ordered upstream segment list (matching the
                            # serve-time resolution) for the prefetcher.
                            seg_url = stripped
                            if not (seg_url.startswith("http://") or seg_url.startswith("https://")):
                                seg_url = urljoin(working_url, seg_url)
                            seg_urls.append(seg_url)
                        if proxy.prefetch_segments:
                            entry["seg_list"] = seg_urls
                        data = ("\n".join(rewritten) + "\n").encode("utf-8")
                        content_type = "application/vnd.apple.mpegurl"
                        debug_log(f"[{proxy.name}] Rewrote m3u8, {len(rewritten)} lines, {len(data)} bytes (from {working_url})", xbmc.LOGINFO)
                    else:
                        # DASH manifest: rewrite relative segment URLs to absolute upstream URLs
                        parsed_upstream = urlparse(working_url)
                        upstream_base = f"{parsed_upstream.scheme}://{parsed_upstream.netloc}"
                        upstream_dir = working_url.rsplit("/", 1)[0] + "/"
                        # Rewrite relative URLs in XML attributes (e.g., media="file.mp4")
                        def _rewrite_dash_url(m):
                            attr_val = m.group(0)
                            prefix = m.group(1)
                            url_val = m.group(2)
                            suffix = m.group(3)
                            if url_val.startswith("http://") or url_val.startswith("https://"):
                                return attr_val
                            if url_val.startswith("/"):
                                return f'{prefix}{upstream_base}{url_val}{suffix}'
                            return f'{prefix}{upstream_dir}{url_val}{suffix}'
                        body = re.sub(r'((?:media|src|url|location|initialization)=")([^"]+)(")', _rewrite_dash_url, body)
                        body = re.sub(r"((?:media|src|url|location|initialization)=')([^']+)(')", _rewrite_dash_url, body)
                        # Also rewrite BaseURL element content
                        def _rewrite_dash_baseurl(m):
                            url_val = m.group(1)
                            if url_val.startswith("http://") or url_val.startswith("https://"):
                                return m.group(0)
                            if url_val.startswith("/"):
                                return f'<BaseURL>{upstream_base}{url_val}</BaseURL>'
                            return f'<BaseURL>{upstream_dir}{url_val}</BaseURL>'
                        body = re.sub(r'<BaseURL>([^<]+)</BaseURL>', _rewrite_dash_baseurl, body)
                        data = body.encode("utf-8")
                        content_type = "application/dash+xml"
                        debug_log(f"[{proxy.name}] Serving DASH manifest, {len(data)} bytes (from {working_url})", xbmc.LOGINFO)

                    entry["url"] = working_url
                    return data, content_type

                def _refresh_manifest_cache(self, entry, token, raw_path):
                    """Background refresh of stale manifest cache."""
                    if proxy._abort.is_set():
                        return

                    debug_log(f"[{proxy.name}] Background refresh starting for token {token[:8]}...", xbmc.LOGINFO)
                    headers = entry.get("headers") or {}
                    port = proxy._port

                    data, content_type = self._fetch_manifest_upstream(entry, token, raw_path, headers, port, False)
                    if data is not None and not proxy._abort.is_set():
                        entry["cache"] = data
                        entry["cache_time"] = time.time()
                        debug_log(f"[{proxy.name}] Background refresh completed: {len(data)} bytes", xbmc.LOGINFO)
                    elif proxy._abort.is_set():
                        debug_log(f"[{proxy.name}] Background refresh aborted (proxy shutting down)", xbmc.LOGINFO)
                    else:
                        debug_log(f"[{proxy.name}] Background refresh failed to fetch upstream", xbmc.LOGWARNING)

                def _serve_segment(self, head_only: bool):
                    if proxy._abort.is_set():
                        self._fail(503, b"Proxy shutting down")
                        return
                    prefix = f"/{proxy.name}/seg/"
                    if not self.path.startswith(prefix):
                        self._fail(404, b"Bad proxy path")
                        return
                    rest = self.path.split("?")[0].lstrip("/")
                    rest = rest[len(f"{proxy.name}/seg/"):]
                    # Token is a UUID hex string (32 chars) followed by '/' and the segment path.
                    if len(rest) < 33 or rest[32] != "/":
                        self._fail(404, b"Bad token/segment")
                        return
                    token = rest[:32]
                    seg_path = unquote(rest[33:])

                    entry = proxy._upstream.get(token)
                    if not entry or not seg_path:
                        self._fail(404, b"Token/segment not found")
                        return

                    upstream_url = entry["url"]
                    headers = entry.get("headers") or {}
                    parsed_upstream = urlparse(upstream_url)
                    auth_query = parsed_upstream.query
                    base = f"{parsed_upstream.scheme}://{parsed_upstream.netloc}{parsed_upstream.path.rsplit('/', 1)[0]}/"

                    if seg_path.startswith("http://") or seg_path.startswith("https://"):
                        target = seg_path
                    else:
                        target = urljoin(base, seg_path)

                    if proxy.fetch_png_segments:
                        target = _rewrite_ts_to_png(target)

                    if auth_query:
                        # Only append upstream auth params if the segment doesn't already
                        # contain them (different tokens can cause upstream 403s).
                        target_qs_keys = set(parse_qs(urlparse(target).query).keys())
                        auth_qs_keys = set(parse_qs(auth_query).keys())
                        if not auth_qs_keys.intersection(target_qs_keys):
                            target += ("&" if "?" in target else "?") + auth_query

                    # Prefetch: kick the next segment's background download as
                    # early as possible (GET only), then serve from cache on hit
                    # or coalesce with an in-flight prefetch.
                    owns_fetch = True
                    if not head_only and proxy.prefetch_segments:
                        self._kick_prefetch(entry, token, target)
                        hit = _seg_cache_get(entry, target)
                        if hit is not None:
                            data, ctype = hit
                            debug_log(f"[{proxy.name}] Segment served from prefetch cache: {len(data)} bytes ({target})", xbmc.LOGINFO)
                            self._send_segment_data(data, ctype, target, token)
                            return
                        ev = _seg_inflight_register(entry, target)
                        if ev is not None:
                            # A prefetch for this segment is already downloading:
                            # wait for it instead of starting a duplicate
                            # download (upstream bandwidth is the bottleneck).
                            owns_fetch = False
                            debug_log(f"[{proxy.name}] Waiting on in-flight prefetch: {target}", xbmc.LOGINFO)
                            ev.wait(timeout=3)
                            hit = _seg_cache_get(entry, target)
                            if hit is not None:
                                data, ctype = hit
                                self._send_segment_data(data, ctype, target, token)
                                return
                            # Prefetch failed or was aborted: fetch ourselves.
                            ev2 = _seg_inflight_register(entry, target)
                            if ev2 is not None:
                                ev2.wait(timeout=3)
                                hit = _seg_cache_get(entry, target)
                                if hit is not None:
                                    data, ctype = hit
                                    self._send_segment_data(data, ctype, target, token)
                                    return
                                self._fail(502, b"Segment fetch congestion")
                                return
                            owns_fetch = True

                    debug_log(f"[{proxy.name}] Proxy segment: {target}", xbmc.LOGINFO)

                    # HEAD requests (Kodi VFS stat checks) should never trigger
                    # upstream segment fetches which can hang on CDNs with expired
                    # tokens. Return minimal headers instantly.
                    if head_only:
                        self.send_response(200)
                        self.send_header("Content-Type", "video/mp2t")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        return

                    try:
                        if proxy._abort.is_set():
                            self._fail(503, b"Proxy shutting down")
                            return
                        
                        seg_headers = dict(proxy.default_headers)
                        seg_headers.update(headers)
                        if proxy.upstream_user_agent:
                            seg_headers["User-Agent"] = proxy.upstream_user_agent
                        seg_headers.setdefault("Accept", "*/*")
                        if not proxy.upstream_keep_alive:
                            seg_headers.setdefault("Connection", "close")

                        # Strip Origin/Referer when segment domain differs from
                        # manifest domain (avoids CDN403 on cross-origin).
                        if proxy.segment_strip_origin:
                            target_domain = urlparse(target).netloc
                            manifest_domain = urlparse(entry["url"]).netloc
                            if target_domain and manifest_domain and target_domain != manifest_domain:
                                seg_headers.pop("Origin", None)
                                seg_headers.pop("Referer", None)

                        segment_client = entry.get("session")
                        if segment_client is None:
                            segment_client = requests
                            if proxy.browser_tls:
                                segment_client = requests.Session()
                                segment_client.verify = False
                                segment_client.mount("https://", _ProxyTLSAdapter())

                        upstream_resp = segment_client.get(
                            target,
                            headers=seg_headers,
                            timeout=(3, 5),
                            stream=True,
                            allow_redirects=True,
                        )
                        if proxy._abort.is_set():
                            upstream_resp.close()
                            self._fail(503, b"Proxy shutting down")
                            return
                        upstream_content_type = upstream_resp.headers.get("Content-Type", "")
                        debug_log(
                            f"[{proxy.name}] Segment upstream status: {upstream_resp.status_code}, "
                            f"Content-Type: {upstream_content_type}, Target: {target}",
                            xbmc.LOGINFO,
                        )
                        if upstream_resp.status_code not in (200, 206):
                            self.send_response(upstream_resp.status_code)
                            self.end_headers()
                            upstream_resp.close()
                            return

                        content_type = upstream_content_type if upstream_content_type else "video/mp2t"
                        ct_lower = content_type.lower()
                        if any(bad in ct_lower for bad in ("javascript", "text/", "image/", "application/json")):
                            content_type = "video/mp2t"
                        if proxy.fetch_png_segments and target.lower().endswith(".png"):
                            content_type = "video/mp2t"

                        # Fast path: no payload modification, stream directly.
                        if not proxy.strip_png:
                            if head_only:
                                upstream_resp.close()
                                self.send_response(200)
                                self.send_header("Content-Type", content_type or "video/mp2t")
                                self.send_header("Access-Control-Allow-Origin", "*")
                                self.end_headers()
                                return

                            self.send_response(200)
                            self.send_header("Content-Type", content_type or "video/mp2t")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.send_header("Connection", "close")
                            cl = upstream_resp.headers.get("Content-Length")
                            if cl:
                                self.send_header("Content-Length", cl)
                            self.end_headers()
                            try:
                                for chunk in upstream_resp.iter_content(chunk_size=proxy.chunk_size):
                                    if proxy._abort.is_set():
                                        break
                                    if chunk:
                                        self.wfile.write(chunk)
                            except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError, OSError):
                                pass
                            finally:
                                upstream_resp.close()
                            return

                        # strip_png path with sniffing: payloads that are
                        # neither PNG-wrapped nor nested playlists stream
                        # straight through (ISSUE_BUFFERING.md); everything
                        # else keeps the buffered behavior.
                        it = upstream_resp.iter_content(chunk_size=proxy.chunk_size)
                        head = b""
                        try:
                            for chunk in it:
                                if proxy._abort.is_set():
                                    upstream_resp.close()
                                    return
                                if chunk:
                                    head += chunk
                                    if len(head) >= 8:
                                        break
                        except Exception as e:
                            debug_log(f"[{proxy.name}] Segment download error: {e}", xbmc.LOGWARNING)
                            self._fail(502, b"Download error")
                            upstream_resp.close()
                            return

                        starts_with_webp_head = (len(head) >= 12
                                and head[:4] == WEBP_SIG
                                and head[8:12] == WEBP_LABEL)
                        if (len(head) >= 8
                                and not head.startswith(PNG_SIG)
                                and not starts_with_webp_head
                                and not head.startswith(b"#EXTM3U")):
                            # Raw TS payload (no PNG wrapper): stream
                            # progressively instead of buffering the whole
                            # segment first.
                            self.send_response(200)
                            self.send_header("Content-Type", content_type or "video/mp2t")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.send_header("Connection", "close")
                            cl = upstream_resp.headers.get("Content-Length")
                            if cl:
                                self.send_header("Content-Length", cl)
                            self.end_headers()
                            try:
                                self.wfile.write(head)
                                for chunk in it:
                                    if proxy._abort.is_set():
                                        break
                                    if chunk:
                                        self.wfile.write(chunk)
                            except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError, OSError):
                                pass
                            finally:
                                upstream_resp.close()
                            debug_log(f"[{proxy.name}] Segment streamed (no PNG wrapper), head={len(head)} bytes", xbmc.LOGINFO)
                            return

                        # PNG-wrapped or nested-m3u8 payload: buffer the rest.
                        segment_data = head
                        try:
                            for chunk in it:
                                if proxy._abort.is_set():
                                    break
                                if chunk:
                                    segment_data += chunk
                                    if len(segment_data) > proxy.max_segment_size:
                                        break
                        except Exception as e:
                            debug_log(f"[{proxy.name}] Segment download error: {e}", xbmc.LOGWARNING)
                            self._fail(502, b"Download error")
                            upstream_resp.close()
                            return
                        finally:
                            upstream_resp.close()

                        self._send_segment_data(segment_data, content_type, target, token, head_only)
                    except Exception as e:
                        debug_log(f"[{proxy.name}] proxy segment fetch failed: {e}", xbmc.LOGWARNING)
                        try:
                            self.send_response(502)
                            self.end_headers()
                        except Exception:
                            pass
                    finally:
                        if proxy.prefetch_segments and owns_fetch:
                            _seg_inflight_done(entry, target)

                def _send_segment_data(self, segment_data, content_type, target, token, head_only=False):
                    """Serve segment bytes already in memory (buffered download
                    or prefetch cache) with full post-processing: content-type
                    fix, PNG strip, fMP4/TS detection, nested-m3u8 rewrite."""
                    content_type = content_type if content_type else "video/mp2t"
                    ct_lower = content_type.lower()
                    if any(bad in ct_lower for bad in ("javascript", "text/", "image/", "application/json")):
                        content_type = "video/mp2t"
                    if proxy.fetch_png_segments and target.lower().endswith(".png"):
                        content_type = "video/mp2t"

                    original_len = len(segment_data)
                    prefix_hex = " ".join(f"{b:02x}" for b in segment_data[:8])
                    starts_with_webp = segment_data[:4] == WEBP_SIG and len(segment_data) >= 12 and segment_data[8:12] == WEBP_LABEL
                    debug_log(
                        f"[{proxy.name}] Segment pre-strip: len={original_len}, "
                        f"starts_with_png={segment_data.startswith(PNG_SIG)}, "
                        f"starts_with_webp={starts_with_webp}, "
                        f"first_bytes={prefix_hex}",
                        xbmc.LOGINFO,
                    )
                    segment_data = _strip_png(segment_data)
                    if len(segment_data) != original_len:
                        debug_log(f"[{proxy.name}] Stripped image wrapper: {original_len} -> {len(segment_data)} bytes", xbmc.LOGINFO)
                        # Detect fMP4 (ftyp box at offset 4-7) after PNG strip
                        if (len(segment_data) >= 8
                                and segment_data[4:8] == b"ftyp"):
                            content_type = "video/mp4"
                            debug_log(f"[{proxy.name}] Detected fMP4 after PNG strip, setting content-type to video/mp4", xbmc.LOGINFO)
                        elif len(segment_data) >= 1 and segment_data[0] != 0x47:
                            prefix = " ".join(f"{b:02x}" for b in segment_data[:16])
                            debug_log(f"[{proxy.name}] WARNING: Segment starts with 0x{segment_data[0]:02x} (not TS sync 0x47), bytes: {prefix}", xbmc.LOGWARNING)

                    is_m3u8 = segment_data.startswith(b"#EXTM3U") or "mpegurl" in content_type.lower()
                    if is_m3u8:
                        try:
                            manifest_body = segment_data.decode("utf-8", errors="replace").replace("\x00", "")
                            if proxy.manifest_png_to_ts and not proxy.strip_png:
                                manifest_body = _rewrite_png_to_ts(manifest_body)
                            rewritten = []
                            parsed_target = urlparse(target)
                            target_base = f"{parsed_target.scheme}://{parsed_target.netloc}"
                            target_dir = target.rsplit("/", 1)[0] + "/"
                            for line in manifest_body.splitlines():
                                stripped = line.strip()
                                if not stripped:
                                    continue
                                if stripped.startswith("#"):
                                    rewritten.append(line)
                                    continue
                                if not proxy.proxy_absolute_urls and (
                                    stripped.startswith("http://") or stripped.startswith("https://")
                                ):
                                    rewritten.append(line)
                                    continue
                                if stripped.startswith("/"):
                                    stripped = f"{target_base}{stripped}"
                                elif not stripped.startswith("http://") and not stripped.startswith("https://"):
                                    stripped = urljoin(target_dir, stripped)
                                rewritten.append(
                                    f"http://127.0.0.1:{proxy._port}/{proxy.name}/seg/{token}/{quote(_rewrite_png_to_image(stripped), safe='')}"
                                )
                            segment_data = ("\n".join(rewritten) + "\n").encode("utf-8")
                            content_type = "application/vnd.apple.mpegurl"
                            debug_log(
                                f"[{proxy.name}] Nested m3u8 detected and rewritten ({len(rewritten)} lines)",
                                xbmc.LOGINFO,
                            )
                        except Exception as e:
                            debug_log(f"[{proxy.name}] Nested m3u8 rewrite failed: {e}", xbmc.LOGWARNING)

                    if head_only:
                        self.send_response(200)
                        self.send_header("Content-Type", content_type or "video/mp2t")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Connection", "close")
                        self.end_headers()
                        return

                    self.send_response(200)
                    self.send_header("Content-Type", content_type or "video/mp2t")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Connection", "close")
                    self.send_header("Content-Length", str(len(segment_data)))
                    self.end_headers()
                    try:
                        self.wfile.write(segment_data)
                        debug_log(f"[{proxy.name}] Segment sent {len(segment_data)} bytes, type={content_type}", xbmc.LOGINFO)
                    except (ConnectionAbortedError, BrokenPipeError):
                        pass

                def _final_target(self, entry, abs_url):
                    """Apply the same transforms _serve_segment applies to a
                    manifest segment reference (PNG rewrite + auth-query
                    append), so prefetch cache keys match serve-time targets."""
                    target = abs_url
                    if proxy.fetch_png_segments:
                        target = _rewrite_ts_to_png(target)
                    auth_query = urlparse(entry["url"]).query
                    if auth_query:
                        target_qs_keys = set(parse_qs(urlparse(target).query).keys())
                        auth_qs_keys = set(parse_qs(auth_query).keys())
                        if not auth_qs_keys.intersection(target_qs_keys):
                            target += ("&" if "?" in target else "?") + auth_query
                    return target

                def _kick_prefetch(self, entry, token, current_target):
                    """Background-prefetch the segment after *current_target* in
                    the token's current manifest segment list."""
                    if proxy._abort.is_set():
                        return
                    seg_list = entry.get("seg_list") or []
                    if not seg_list:
                        return
                    finals = [self._final_target(entry, u) for u in seg_list]
                    try:
                        idx = finals.index(current_target)
                    except ValueError:
                        return
                    nxt = idx + 1
                    if nxt >= len(finals):
                        return
                    url = finals[nxt]
                    if _seg_cache_get(entry, url) is not None:
                        return
                    t = threading.Thread(
                        target=_prefetch_segment,
                        args=(proxy, entry, url),
                        name=f"{proxy.name}Prefetch",
                    )
                    t.daemon = True
                    t.start()

            server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
            server.daemon_threads = True

            def _serve():
                # Custom accept loop instead of serve_forever(). Exits within
                # 0.2s of abort() being set — serve_forever() only exits when
                # server.shutdown() sets its flag or when select() raises on
                # the closed listen socket, and on Windows closing a socket
                # out from under select() is NOT guaranteed to wake it. A
                # serve thread left spinning here keeps the plugin invoker
                # stuck in its "waiting on thread ..." teardown state long
                # after playback ends, which correlates with the GIL
                # starvation deadlock on the NEXT playback's close.
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(server, selectors.EVENT_READ)
                        while not proxy._abort.is_set():
                            if selector.select(0.2):
                                server._handle_request_noblock()
                except OSError:
                    # Listen socket closed by abort() — exit quietly.
                    pass
                except Exception as e:
                    debug_log(f"[{proxy.name}] proxy serve loop error: {e}", xbmc.LOGWARNING)

            thread = threading.Thread(target=_serve, name=f"{self.name}Proxy")
            thread.daemon = True
            thread.start()
            self._server = server
            self._thread = thread
            self._port = port
            self._last_activity = time.time()
            if self._watchdog_thread is None or not self._watchdog_thread.is_alive():
                self._watchdog_thread = threading.Thread(target=self._watchdog, name=f"{self.name}Watchdog")
                self._watchdog_thread.daemon = True
                self._watchdog_thread.start()
            debug_log(f"[{self.name}] Proxy listening on 127.0.0.1:{port}", xbmc.LOGINFO)
            return port

    def _watchdog(self):
        while not self._abort.is_set():
            self._abort.wait(timeout=3)
            if self._abort.is_set():
                break
            idle = time.time() - self._last_activity
            # 12s: comfortably above typical live-HLS manifest/segment refetch
            # intervals (~4-10s) so healthy playback is never killed mid-stream.
            # A lingering-but-responsive proxy is harmless: Kodi's post-playback
            # Stat calls are answered from cache instantly (no freeze), so a
            # longer cleanup delay is safe.
            if idle > 12:
                debug_log(f"[{self.name}] Proxy idle for >{idle:.1f}s, shutting down", xbmc.LOGINFO)
                self.shutdown()
                break

    def get_proxy_url(self, upstream_url: str, headers: dict = None, fallback_urls: list = None) -> str:
        port = self._ensure_server()
        token = uuid.uuid4().hex
        self._upstream[token] = {
            "url": upstream_url,
            "headers": headers or {},
            "fallback_urls": fallback_urls or [],
            "cache": None,
            "cache_time": 0.0,
        }
        set_active_proxy(self)
        return f"http://127.0.0.1:{port}/{self.name}/{token}.m3u8"

    def abort(self):
        """Non-blocking, callback-safe teardown.

        Sets the abort flag and closes BOTH the listen socket and every
        tracked client socket at the OS level. After this call:
          * new connect() attempts fail instantly (ECONNREFUSED), so Kodi's
            CCurlFile::Stat cannot hang ~20s on an orphaned proxy URL, and
          * FFmpeg gets an immediate TCP reset on its open connection
            instead of blocking on its internal ~20s timeout.

        Deliberately uses NO xbmc.* API calls, NO logging and does NOT wait
        for serve_forever() to exit, so it is safe to call from fragile
        contexts (xbmc.Player callbacks firing while the interpreter is
        tearing down with the GIL contended).
        """
        self._abort.set()
        with self._client_sockets_lock:
            sockets = list(self._client_sockets)
            self._client_sockets.clear()
        for s in sockets:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                s.close()
            except Exception:
                pass
        with self._lock:
            server = self._server
            self._server = None
            self._thread = None
            self._port = None
            self._upstream.clear()
        if server is not None:
            try:
                # Closing the listen socket makes new connections fail at the
                # kernel level, and makes the accept loop's select() raise so
                # serve_forever() exits on its own (daemon thread).
                server.socket.close()
            except Exception:
                pass
        # Let observers (e.g. a plugin script waiting for playback cleanup)
        # see that this proxy is gone. Identity-checked: never clears a newer
        # proxy that registered after this one.
        clear_active_proxy(self)

    def shutdown(self, force=False):
        with self._lock:
            server = self._server
        self.abort()
        if server is not None:
            # If force is True, close the listen socket immediately to wake
            # the serve loop. This prevents the 0.2s select() timeout from
            # delaying shutdown.
            if force:
                try:
                    server.socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    server.socket.close()
                except Exception:
                    pass
            # NOTE: no server.shutdown() — that waits for serve_forever() to
            # exit, but the custom _serve loop is used instead (it exits on
            # _abort within 0.2s), so BaseServer.shutdown() would block
            # forever. server_close() is enough (the socket is already closed
            # by abort(); this just finalises the server object).
            try:
                server.server_close()
            except Exception:
                pass


# Global instances per (name, options) to avoid spawning multiple servers.
_proxy_instances = {}
_proxy_lock = threading.Lock()

# Track the most-recently-used proxy so consuming addons can tear it down
# when playback ends (mirrors ULAMA's service-level onPlayBackStopped).
_active_proxy = None
_active_proxy_lock = threading.Lock()


def get_stream_proxy(name: str, default_headers: dict, options: dict = None) -> StreamProxy:
    """Return a singleton StreamProxy for the given name/options."""
    with _proxy_lock:
        key = (name, _hashable_options(options))
        if key not in _proxy_instances:
            _proxy_instances[key] = StreamProxy(name, default_headers, options)
        return _proxy_instances[key]


def set_active_proxy(proxy: StreamProxy):
    """Register *proxy* as the active one (called when a proxy URL is handed to Kodi)."""
    global _active_proxy
    with _active_proxy_lock:
        _active_proxy = proxy


def get_active_proxy() -> StreamProxy:
    """Return the currently active proxy, or None."""
    with _active_proxy_lock:
        return _active_proxy


def clear_active_proxy(proxy: StreamProxy):
    """Clear the global active proxy if it currently points to *proxy*.

    Called by StreamProxy.abort() so observers polling get_active_proxy()
    (pure Python, GIL-friendly) can detect proxy death without any Kodi API
    calls. Identity check prevents clearing a newer proxy registered after
    this one.
    """
    global _active_proxy
    with _active_proxy_lock:
        if _active_proxy is proxy:
            _active_proxy = None


def abort_active_proxy():
    """Non-blocking abort of the active proxy (safe for xbmc.Player callbacks).

    Unlike shutdown_active_proxy() this performs no blocking server shutdown
    and no logging/Kodi API calls, so it cannot stall a callback thread that
    holds the GIL while Kodi's main thread is frozen waiting on VFS Stat
    calls against the proxy URL (the player-close freeze).
    """
    proxy = get_active_proxy()
    if proxy is None:
        return
    with _active_proxy_lock:
        _active_proxy = None
    try:
        proxy.abort()
    except Exception:
        pass


def shutdown_active_proxy():
    """Shut down the active proxy (if any). Called from PlaybackMonitor callbacks."""
    proxy = get_active_proxy()
    if proxy is None:
        return
    with _active_proxy_lock:
        _active_proxy = None
    debug_log("[StreamProxy] shutdown_active_proxy: shutting down", xbmc.LOGINFO)
    try:
        proxy.shutdown(force=True)
    except Exception as e:
        debug_log(f"[StreamProxy] shutdown_active_proxy error: {e}", xbmc.LOGWARNING)


def build_proxy_url(
    name: str,
    upstream_url: str,
    default_headers: dict,
    options: dict = None,
    per_request_headers: dict = None,
    fallback_urls: list = None,
) -> str:
    """One-shot helper: get/create the proxy and register an upstream URL."""
    proxy = get_stream_proxy(name, default_headers, options)
    return proxy.get_proxy_url(upstream_url, per_request_headers, fallback_urls=fallback_urls)
