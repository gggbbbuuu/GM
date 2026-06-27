from ..models import *
from typing import Optional, List
import requests
import time
import xbmc
import socket
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


SCRAPE_URL = "https://magnetic.website/Jetextractor/FCTV/fctv_scrape1.json"

# Hard-coded player host used as the Referer / Origin for the upstream
# CDN. The player host rotates frequently, but the scraper can capture the
# live one per request and store it in _PATCH_PROXY["upstream"][token].
PLAYER_REFERER = "https://zac07eo.mpipzni2naturally32kistomach.ru/"

# Full set of headers needed by the CDN. The CDN checks Sec-Ch-Ua and
# Sec-Fetch-* in addition to Origin/Referer/User-Agent.
# NOTE: Origin should be the site domain (fctv33.ws), NOT the player host.
# The Referer is the player host. These are checked by the CDN separately.
FCTV_FULL_HEADERS = {
    "Origin": "https://fctv33.ws",
    "Referer": "https://zac07eo.mpipzni2naturally32kistomach.ru/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "DNT": "1",
    "Sec-Ch-Ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}

_PATCH_PROXY = {
    "server": None,
    "thread": None,
    "port": None,
    "lock": threading.Lock(),
    "upstream": {},  # token -> {"url": str, "headers": dict}
}


class _FCTVProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        # Keep query string for segment requests, strip for m3u8 token extraction
        raw_path_for_token = self.path.split("?")[0].lstrip("/")
        upstream_map = _PATCH_PROXY["upstream"]
        xbmc.log(f"[FCTV] Proxy GET {self.path}", xbmc.LOGINFO)

        # /fctv/{token}.m3u8 -> fetch upstream, rewrite segments
        if raw_path_for_token.startswith("fctv/") and raw_path_for_token.endswith(".m3u8"):
            token = raw_path_for_token[len("fctv/"):-len(".m3u8")]
            entry = upstream_map.get(token)
            if not entry:
                xbmc.log(f"[FCTV] Token not found: {token}", xbmc.LOGWARNING)
                self._fail(404, b"Token not found")
                return
            upstream_url = entry["url"]
            headers = entry.get("headers") or {}
            port = _PATCH_PROXY["port"]
            xbmc.log(f"[FCTV] Proxy fetching upstream m3u8: {upstream_url}", xbmc.LOGINFO)
            # 1-second cache so subsequent m3u8 polls return instantly.
            now = time.time()
            if entry.get("cache") and (now - entry.get("cache_time", 0)) < 1.0:
                data = entry["cache"]
                xbmc.log(f"[FCTV] Serving cached m3u8 ({len(data)} bytes)", xbmc.LOGINFO)
            else:
                try:
                    # Don't request compression - get plain text m3u8
                    req_headers = dict(headers)
                    req_headers.pop("Accept-Encoding", None)
                    resp = requests.get(
                        upstream_url, timeout=8, headers=req_headers, stream=False
                    )
                    xbmc.log(f"[FCTV] Upstream response: {resp.status_code}", xbmc.LOGINFO)
                    xbmc.log(f"[FCTV] Upstream content-type: {resp.headers.get('Content-Type', 'unknown')}", xbmc.LOGINFO)
                    xbmc.log(f"[FCTV] Upstream content-encoding: {resp.headers.get('Content-Encoding', 'none')}", xbmc.LOGINFO)
                    if resp.status_code != 200:
                        xbmc.log(f"[FCTV] Upstream error {resp.status_code}: {resp.text[:200]}", xbmc.LOGWARNING)
                        self._fail(502, f"Upstream {resp.status_code}".encode())
                        return
                    # Use content (bytes) and decode with error handling to avoid
                    # "embedded null character" issues with resp.text
                    raw_bytes = resp.content
                    xbmc.log(f"[FCTV] Upstream raw bytes: {len(raw_bytes)}", xbmc.LOGINFO)
                    # Try to decompress if needed
                    try:
                        import gzip
                        import zlib
                        # Check if it's gzip
                        if raw_bytes[:2] == b'\x1f\x8b':
                            xbmc.log("[FCTV] Detected gzip, decompressing...", xbmc.LOGINFO)
                            raw_bytes = gzip.decompress(raw_bytes)
                        # Check if it's zlib/deflate
                        elif raw_bytes[:2] == b'\x78\x9c' or raw_bytes[:2] == b'\x78\x01' or raw_bytes[:2] == b'\x78\xda':
                            xbmc.log("[FCTV] Detected zlib/deflate, decompressing...", xbmc.LOGINFO)
                            raw_bytes = zlib.decompress(raw_bytes)
                    except Exception as decomp_err:
                        xbmc.log(f"[FCTV] Decompression attempt failed: {decomp_err}", xbmc.LOGDEBUG)
                    try:
                        body = raw_bytes.decode("utf-8", errors="replace")
                    except Exception:
                        body = raw_bytes.decode("utf-8", errors="ignore")
                    # Remove any embedded null characters that can break string operations
                    body = body.replace("\x00", "")
                    xbmc.log(f"[FCTV] Upstream body length: {len(body)}", xbmc.LOGINFO)
                    xbmc.log(f"[FCTV] Upstream body first 100 chars: {repr(body[:100])}", xbmc.LOGINFO)
                    if not body or "#EXTM3U" not in body:
                        xbmc.log(f"[FCTV] Upstream body invalid: {body[:200]}", xbmc.LOGWARNING)
                        self._fail(502, b"Upstream not m3u8")
                        return
                    # Rewrite relative segment URLs back through this
                    # proxy so each segment is fetched with the correct
                    # headers and the 302 redirect chain is followed
                    # inside the proxy (ffmpeg-direct in timeshift mode
                    # relies on the proxy to handle per-request CDN
                    # token rotation).
                    rewritten = []
                    for line in body.splitlines():
                        stripped = line.strip()
                        if not stripped:
                            continue
                        if stripped.startswith("#"):
                            rewritten.append(line)
                            continue
                        if stripped.startswith("http://") or stripped.startswith("https://"):
                            rewritten.append(line)
                            continue
                        rewritten.append(
                            f"http://127.0.0.1:{port}/fctv/seg/{token}/{stripped}"
                        )
                    data = ("\n".join(rewritten) + "\n").encode("utf-8")
                    entry["cache"] = data
                    entry["cache_time"] = now
                    xbmc.log(f"[FCTV] Rewrote m3u8, {len(rewritten)} lines, {len(data)} bytes", xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f"[FCTV] manifest rebuild failed: {e}", xbmc.LOGWARNING)
                    self._fail(502, b"Upstream error")
                    return
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(data)
                xbmc.log(f"[FCTV] Sent m3u8 response ({len(data)} bytes)", xbmc.LOGINFO)
            except (ConnectionAbortedError, BrokenPipeError) as e:
                xbmc.log(f"[FCTV] client disconnected during manifest write: {e}", xbmc.LOGDEBUG)
            return

        # /fctv/seg/{token}/{seg_path} -> proxy segment
        if raw_path_for_token.startswith("fctv/seg/"):
            # Use the full path including query string for segments
            full_path = self.path.lstrip("/")
            token_and_rest = full_path[len("fctv/seg/"):]
            if "/" in token_and_rest:
                token, seg_path = token_and_rest.split("/", 1)
            else:
                token, seg_path = token_and_rest, ""
            entry = upstream_map.get(token)
            if not entry or not seg_path:
                xbmc.log(f"[FCTV] Segment token/path not found: {token}/{seg_path}", xbmc.LOGWARNING)
                self._fail(404, b"Token/segment not found")
                return
            upstream_url = entry["url"]
            headers = entry.get("headers") or {}
            base = upstream_url.rsplit("/", 1)[0] + "/"
            target = base + seg_path
            xbmc.log(f"[FCTV] Proxy segment: {target}", xbmc.LOGINFO)
            try:
                # resolve redirects on our end so ffmpeg gets the
                # final URL + correct headers in a single round-trip
                session = requests.Session()
                upstream_resp = session.get(
                    target, headers=headers, timeout=15, stream=True, allow_redirects=True
                )
                xbmc.log(f"[FCTV] Segment upstream status: {upstream_resp.status_code}", xbmc.LOGINFO)
                if upstream_resp.status_code not in (200, 206):
                    self.send_response(upstream_resp.status_code)
                    self.end_headers()
                    try:
                        upstream_resp.close()
                    except Exception:
                        pass
                    return
                content_type = upstream_resp.headers.get("Content-Type", "video/mp2t")
                if "javascript" in content_type.lower() or content_type.startswith("text/"):
                    content_type = "video/mp2t"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                cl = upstream_resp.headers.get("Content-Length")
                if cl:
                    self.send_header("Content-Length", cl)
                self.end_headers()
                bytes_sent = 0
                try:
                    for chunk in upstream_resp.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            self.wfile.write(chunk)
                            bytes_sent += len(chunk)
                except (ConnectionAbortedError, BrokenPipeError) as e:
                    xbmc.log(
                        f"[FCTV] client disconnected mid-segment: {e}", xbmc.LOGDEBUG
                    )
                finally:
                    xbmc.log(f"[FCTV] Segment sent {bytes_sent} bytes", xbmc.LOGINFO)
                    try:
                        upstream_resp.close()
                    except Exception:
                        pass
            except Exception as e:
                xbmc.log(
                    f"[FCTV] proxy segment fetch failed for {target}: {e}",
                    xbmc.LOGWARNING,
                )
                try:
                    self.send_response(502)
                    self.end_headers()
                except Exception:
                    pass
            return

        self._fail(404, b"Not found")

    def _fail(self, code: int, body: bytes) -> None:
        try:
            self.send_response(code)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            xbmc.log(f"[FCTV] _fail write error: {e}", xbmc.LOGDEBUG)


def _ensure_proxy() -> int:
    with _PATCH_PROXY["lock"]:
        if _PATCH_PROXY["server"] is not None:
            return _PATCH_PROXY["port"]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        server = ThreadingHTTPServer(("127.0.0.1", port), _FCTVProxyHandler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, name="FCTVProxy")
        thread.daemon = True
        thread.start()
        _PATCH_PROXY["server"] = server
        _PATCH_PROXY["thread"] = thread
        _PATCH_PROXY["port"] = port
        xbmc.log(f"[FCTV] Patch proxy listening on 127.0.0.1:{port}", xbmc.LOGINFO)
        return port


class FCTV(JetExtractor):
    def __init__(self) -> None:
        self.domains = [
            "fctv33.ws", "www.fctv33.ws", "fctv33.net", "www.fctv33.net",
            "fctv33hd.yachts", "fctv33.com",
            "jack09eo.mpstickv5m73jgravity.my",
            "127.0.0.1",
        ]
        self.domains_regex = True
        self.name = "FCTV33"
        self.short_name = "FCTV"

        self.scrape_data: List[dict] = []
        self.last_fetch: float = 0.0

    def _refresh(self) -> None:
        now = time.time()
        if self.scrape_data and (now - self.last_fetch) < 30:
            return
        try:
            r = requests.get(
                SCRAPE_URL,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    self.scrape_data = data
                    self.last_fetch = now
                    xbmc.log(
                        f"[FCTV] Loaded {len(data)} entries from scrape JSON",
                        xbmc.LOGINFO,
                    )
        except Exception as e:
            xbmc.log(f"[FCTV] Failed to fetch scrape JSON: {e}", xbmc.LOGWARNING)

    def _build_proxy_link(self, upstream_url: str, headers: dict) -> str:
        """Register an upstream m3u8 in the local proxy and return the
        proxy URL Kodi should open.

        The first call to the proxy URL prefetches the upstream m3u8
        synchronously (so Kodi gets a fast response) and caches the
        rewritten manifest for a short window. Subsequent calls in
        the same window return the cached manifest."""
        port = _ensure_proxy()
        token = uuid.uuid4().hex
        _PATCH_PROXY["upstream"][token] = {
            "url": upstream_url,
            "headers": headers or {},
            "cache": None,
            "cache_time": 0.0,
        }
        proxy_url = f"http://127.0.0.1:{port}/fctv/{token}.m3u8"
        xbmc.log(
            f"[FCTV] Live proxy registered: {proxy_url} (headers={headers})",
            xbmc.LOGINFO,
        )
        return proxy_url

    def _prefetch(self, token: str) -> None:
        """Best-effort prefetch of the upstream m3u8 into the proxy cache.
        Runs in a background thread so it never blocks the caller."""
        entry = _PATCH_PROXY["upstream"].get(token)
        if not entry:
            return

        def _do():
            try:
                # Don't request compression - get plain text m3u8
                req_headers = dict(entry.get("headers") or {})
                req_headers.pop("Accept-Encoding", None)
                resp = requests.get(
                    entry["url"], timeout=8, headers=req_headers
                )
                if resp.status_code != 200:
                    return
                # Use content (bytes) and decode with error handling
                raw_bytes = resp.content
                # Try to decompress if needed
                try:
                    import gzip
                    import zlib
                    if raw_bytes[:2] == b'\x1f\x8b':
                        raw_bytes = gzip.decompress(raw_bytes)
                    elif raw_bytes[:2] == b'\x78\x9c' or raw_bytes[:2] == b'\x78\x01' or raw_bytes[:2] == b'\x78\xda':
                        raw_bytes = zlib.decompress(raw_bytes)
                except Exception:
                    pass
                try:
                    body = raw_bytes.decode("utf-8", errors="replace")
                except Exception:
                    body = raw_bytes.decode("utf-8", errors="ignore")
                # Remove any embedded null characters that can break string operations
                body = body.replace("\x00", "")
                if not body or "#EXTM3U" not in body:
                    return
                port = _PATCH_PROXY["port"]
                rewritten = []
                for line in body.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("#"):
                        rewritten.append(line)
                        continue
                    if stripped.startswith("http://") or stripped.startswith("https://"):
                        rewritten.append(line)
                        continue
                    rewritten.append(
                        f"http://127.0.0.1:{port}/fctv/seg/{token}/{stripped}"
                    )
                data = ("\n".join(rewritten) + "\n").encode("utf-8")
                entry["cache"] = data
                entry["cache_time"] = time.time()
            except Exception as e:
                xbmc.log(f"[FCTV] prefetch failed: {e}", xbmc.LOGDEBUG)

        threading.Thread(target=_do, daemon=True, name=f"FCTVPrefetch-{token[:6]}").start()

    def _normalize(self, entry: dict) -> Optional[JetItem]:
        url = entry.get("url") or ""
        if not url:
            return None
        title = entry.get("title") or url
        league = entry.get("league") or entry.get("group") or "Sports"
        links = []
        for l in entry.get("links") or []:
            addr = l.get("address") if isinstance(l, dict) else None
            if not addr:
                continue
            upstream_headers = l.get("headers") if isinstance(l, dict) else None
            if not upstream_headers:
                upstream_headers = {}
            xbmc.log(f"[FCTV] Scraped headers for {addr}: {upstream_headers}", xbmc.LOGINFO)
            # Use the full header set so the CDN's anti-bot checks pass
            # (Sec-Ch-Ua, Sec-Fetch-*, etc). User-supplied headers from
            # the scraper override defaults if present.
            merged = dict(FCTV_FULL_HEADERS)
            for k, v in (upstream_headers or {}).items():
                if v:
                    merged[k] = v
            upstream_headers = merged
            xbmc.log(f"[FCTV] Merged headers: {upstream_headers}", xbmc.LOGINFO)
            name = l.get("channel") if isinstance(l, dict) else None
            # Hand Kodi the local proxy URL. The proxy rebuilds the
            # upstream m3u8 fresh on every fetch (so the CDN token
            # rotation is invisible to Kodi) and rewrites all segment
            # URLs through the proxy.
            try:
                proxy_url = self._build_proxy_link(addr, upstream_headers)
                # Kick off a background prefetch so the proxy's first
                # response to Kodi is instant (avoids the 30s ffmpeg
                # open timeout while the upstream CDN is contacted).
                token = proxy_url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                self._prefetch(token)
            except Exception as e:
                xbmc.log(f"[FCTV] proxy registration failed, using raw URL: {e}", xbmc.LOGWARNING)
                proxy_url = addr
            # The proxy is responsible for the upstream segment fetches,
            # but we ALSO pass headers on the JetLink so ffmpeg has
            # valid Referer/Origin/User-Agent when it follows any
            # redirects itself (the same way RoxieStreams does).
            link_headers = dict(upstream_headers)
            inp = JetInputstreamFFmpegDirect.default()
            xbmc.log(f"[FCTV] Creating JetLink with proxy_url={proxy_url}, headers={link_headers}", xbmc.LOGINFO)
            links.append(
                JetLink(
                    address=proxy_url,
                    name=name,
                    headers=link_headers,
                    resolveurl=False,
                    inputstream=inp,
                    direct=True,
                )
            )
        if not links:
            return None
        return JetItem(
            title=title,
            league=league,
            links=links,
            status=entry.get("status"),
            icon=entry.get("icon"),
        )

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        self._refresh()
        for entry in self.scrape_data:
            item = self._normalize(entry)
            if item is not None:
                items.append(item)

        xbmc.log(f"[FCTV] Total items: {len(items)}", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        return [url]

    def get_link(self, url: JetLink) -> JetLink:
        # The link should already be a proxy URL set up by _normalize, but
        # re-register if needed (e.g. on a stale token).
        if "127.0.0.1" in url.address and "/fctv/" in url.address:
            return url
        self._refresh()
        for entry in self.scrape_data:
            for l in entry.get("links") or []:
                if not isinstance(l, dict):
                    continue
                if l.get("address") == url.address:
                    base_headers = l.get("headers") or {}
                    merged = dict(FCTV_FULL_HEADERS)
                    for k, v in base_headers.items():
                        if v:
                            merged[k] = v
                    headers = merged
                    try:
                        proxy_url = self._build_proxy_link(url.address, headers)
                    except Exception:
                        return url
                    return JetLink(
                        address=proxy_url,
                        name=l.get("channel") or url.name,
                        headers=headers,
                        resolveurl=False,
                        inputstream=JetInputstreamFFmpegDirect.default(),
                        direct=True,
                    )
        return url
