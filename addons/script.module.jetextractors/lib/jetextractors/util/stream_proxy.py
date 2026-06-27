import gzip
import socket
import threading
import time
import uuid
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, urljoin, parse_qs

import requests
import xbmc


PNG_SIG = b'\x89PNG\r\n\x1a\n'


def _strip_png(data: bytes) -> bytes:
    """Remove a PNG wrapper that precedes the actual MPEG-TS payload."""
    if not data.startswith(PNG_SIG):
        return data
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
    return url.replace(".png", ".ts").replace(".PNG", ".TS")


def _rewrite_ts_to_png(url: str) -> str:
    if ".ts?" in url or ".TS?" in url:
        return url.replace(".ts?", ".png?").replace(".TS?", ".png?")
    if url.endswith(".ts") or url.endswith(".TS"):
        return url[:-3] + ".png"
    return url


def _hashable_options(options: dict):
    return frozenset((k, v) for k, v in (options or {}).items())


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
        self.add_icy_metadata = opts.get("add_icy_metadata", True)
        self.request_timeout = opts.get("request_timeout", (5, 30))
        self.max_manifest_size = opts.get("max_manifest_size", 256 * 1024)
        self.max_segment_size = opts.get("max_segment_size", 32 * 1024 * 1024)
        self.chunk_size = opts.get("chunk_size", 64 * 1024)

        self._server = None
        self._thread = None
        self._port = None
        self._lock = threading.Lock()
        self._upstream = {}

    def _ensure_server(self) -> int:
        with self._lock:
            if self._server is not None:
                return self._port

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            sock.close()

            proxy = self

            class _Handler(BaseHTTPRequestHandler):
                def log_message(self, format, *args):
                    pass

                def _fail(self, code: int, body: bytes) -> None:
                    try:
                        self.send_response(code)
                        self.send_header("Content-Type", "text/plain")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    except Exception as e:
                        xbmc.log(f"[{proxy.name}] proxy _fail write error: {e}", xbmc.LOGDEBUG)

                def do_GET(self):
                    self._handle(head_only=False)

                def do_HEAD(self):
                    self._handle(head_only=True)

                def _handle(self, head_only: bool):
                    raw_path = self.path.split("?")[0].lstrip("/")
                    prefix = f"{proxy.name}/"
                    seg_prefix = f"{proxy.name}/seg/"

                    if raw_path.startswith(prefix) and raw_path.endswith(".m3u8"):
                        self._serve_manifest(head_only=head_only)
                    elif raw_path.startswith(seg_prefix):
                        self._serve_segment(head_only=head_only)
                    else:
                        self._fail(404, b"Not found")

                def _serve_manifest(self, head_only: bool):
                    raw_path = self.path.split("?")[0].lstrip("/")
                    token = raw_path[len(f"{proxy.name}/"):-len(".m3u8")]
                    entry = proxy._upstream.get(token)
                    if not entry:
                        self._fail(404, b"Token not found")
                        return

                    upstream_url = entry["url"]
                    headers = entry.get("headers") or {}
                    port = proxy._port
                    now = time.time()

                    cached = entry.get("cache")
                    cache_time = entry.get("cache_time", 0.0)
                    if proxy.cache_manifest and cached and (now - cache_time) < proxy.manifest_ttl:
                        data = cached
                        xbmc.log(f"[{proxy.name}] Serving cached m3u8 ({len(data)} bytes)", xbmc.LOGINFO)
                    else:
                        try:
                            req_headers = dict(proxy.default_headers)
                            req_headers.update(headers)
                            req_headers.setdefault("Accept", "*/*")
                            req_headers.setdefault("Connection", "close")
                            if proxy.add_icy_metadata:
                                req_headers.setdefault("Icy-MetaData", "1")

                            resp = requests.get(
                                upstream_url,
                                timeout=proxy.request_timeout,
                                headers=req_headers,
                                stream=True,
                            )
                            xbmc.log(f"[{proxy.name}] Upstream response: {resp.status_code}", xbmc.LOGINFO)
                            if resp.status_code != 200:
                                xbmc.log(f"[{proxy.name}] Upstream error {resp.status_code}: {resp.text[:200]}", xbmc.LOGWARNING)
                                self._fail(502, f"Upstream {resp.status_code}".encode())
                                resp.close()
                                return

                            raw_bytes = b""
                            for chunk in resp.iter_content(chunk_size=8192):
                                raw_bytes += chunk
                                if len(raw_bytes) > proxy.max_manifest_size:
                                    break
                            resp.close()

                            raw_bytes = _decompress(raw_bytes)
                            body = raw_bytes.decode("utf-8", errors="replace").replace("\x00", "")
                            xbmc.log(f"[{proxy.name}] Upstream body length: {len(body)}", xbmc.LOGINFO)
                            if not body or "#EXTM3U" not in body:
                                xbmc.log(f"[{proxy.name}] Upstream body invalid: {body[:200]}", xbmc.LOGWARNING)
                                self._fail(502, b"Upstream not m3u8")
                                return

                            if proxy.manifest_png_to_ts:
                                body = _rewrite_png_to_ts(body)

                            rewritten = []
                            parsed_upstream = urlparse(upstream_url)
                            upstream_root = f"{parsed_upstream.scheme}://{parsed_upstream.netloc}"
                            for line in body.splitlines():
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
                                # Root-relative segment refs need an absolute base to resolve
                                # correctly through the proxy.
                                if stripped.startswith("/"):
                                    stripped = f"{upstream_root}{stripped}"
                                rewritten.append(
                                    f"http://127.0.0.1:{port}/{proxy.name}/seg/{token}/{stripped}"
                                )
                            data = ("\n".join(rewritten) + "\n").encode("utf-8")
                            entry["cache"] = data
                            entry["cache_time"] = now
                            xbmc.log(f"[{proxy.name}] Rewrote m3u8, {len(rewritten)} lines, {len(data)} bytes", xbmc.LOGINFO)
                        except Exception as e:
                            xbmc.log(f"[{proxy.name}] manifest rebuild failed: {e}", xbmc.LOGWARNING)
                            self._fail(502, b"Upstream error")
                            return

                    self.send_response(200)
                    self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    if not head_only:
                        try:
                            self.wfile.write(data)
                        except (ConnectionAbortedError, BrokenPipeError):
                            pass

                def _serve_segment(self, head_only: bool):
                    prefix = f"/{proxy.name}/seg/"
                    if not self.path.startswith(prefix):
                        self._fail(404, b"Bad proxy path")
                        return
                    rest = self.path[len(prefix):]
                    # Token is a UUID hex string (32 chars) followed by '/' and the segment path.
                    if len(rest) < 33 or rest[32] != "/":
                        self._fail(404, b"Bad token/segment")
                        return
                    token = rest[:32]
                    seg_path = rest[33:]

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

                    xbmc.log(f"[{proxy.name}] Proxy segment: {target}", xbmc.LOGINFO)

                    try:
                        seg_headers = dict(proxy.default_headers)
                        seg_headers.update(headers)
                        seg_headers.setdefault("Accept", "*/*")
                        seg_headers.setdefault("Connection", "close")
                        if proxy.add_icy_metadata:
                            seg_headers.setdefault("Icy-MetaData", "1")

                        upstream_resp = requests.get(
                            target,
                            headers=seg_headers,
                            timeout=proxy.request_timeout,
                            stream=True,
                            allow_redirects=True,
                        )
                        upstream_content_type = upstream_resp.headers.get("Content-Type", "")
                        xbmc.log(
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
                            cl = upstream_resp.headers.get("Content-Length")
                            if cl:
                                self.send_header("Content-Length", cl)
                            self.end_headers()
                            try:
                                for chunk in upstream_resp.iter_content(chunk_size=proxy.chunk_size):
                                    if chunk:
                                        self.wfile.write(chunk)
                            finally:
                                upstream_resp.close()
                            return

                        # PNG-stripping path: buffer the whole segment.
                        segment_data = b""
                        try:
                            for chunk in upstream_resp.iter_content(chunk_size=proxy.chunk_size):
                                if chunk:
                                    segment_data += chunk
                                    if len(segment_data) > proxy.max_segment_size:
                                        break
                        except Exception as e:
                            xbmc.log(f"[{proxy.name}] Segment download error: {e}", xbmc.LOGWARNING)
                            self._fail(502, b"Download error")
                            upstream_resp.close()
                            return
                        finally:
                            upstream_resp.close()

                        original_len = len(segment_data)
                        prefix_hex = " ".join(f"{b:02x}" for b in segment_data[:8])
                        xbmc.log(
                            f"[{proxy.name}] Segment pre-strip: len={original_len}, "
                            f"starts_with_png={segment_data.startswith(PNG_SIG)}, "
                            f"first_bytes={prefix_hex}",
                            xbmc.LOGINFO,
                        )
                        segment_data = _strip_png(segment_data)
                        if len(segment_data) != original_len:
                            xbmc.log(f"[{proxy.name}] Stripped PNG wrapper: {original_len} -> {len(segment_data)} bytes", xbmc.LOGINFO)
                            if len(segment_data) >= 1 and segment_data[0] != 0x47:
                                prefix = " ".join(f"{b:02x}" for b in segment_data[:16])
                                xbmc.log(f"[{proxy.name}] WARNING: Segment starts with 0x{segment_data[0]:02x} (not TS sync 0x47), bytes: {prefix}", xbmc.LOGWARNING)

                        if head_only:
                            self.send_response(200)
                            self.send_header("Content-Type", content_type or "video/mp2t")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            return

                        self.send_response(200)
                        self.send_header("Content-Type", content_type or "video/mp2t")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Content-Length", str(len(segment_data)))
                        self.end_headers()
                        try:
                            self.wfile.write(segment_data)
                            xbmc.log(f"[{proxy.name}] Segment sent {len(segment_data)} bytes, type={content_type}", xbmc.LOGINFO)
                        except (ConnectionAbortedError, BrokenPipeError):
                            pass
                    except Exception as e:
                        xbmc.log(f"[{proxy.name}] proxy segment fetch failed: {e}", xbmc.LOGWARNING)
                        try:
                            self.send_response(502)
                            self.end_headers()
                        except Exception:
                            pass

            server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, name=f"{self.name}Proxy")
            thread.daemon = True
            thread.start()
            self._server = server
            self._thread = thread
            self._port = port
            xbmc.log(f"[{self.name}] Proxy listening on 127.0.0.1:{port}", xbmc.LOGINFO)
            return port

    def get_proxy_url(self, upstream_url: str, headers: dict = None) -> str:
        port = self._ensure_server()
        token = uuid.uuid4().hex
        self._upstream[token] = {
            "url": upstream_url,
            "headers": headers or {},
            "cache": None,
            "cache_time": 0.0,
        }
        return f"http://127.0.0.1:{port}/{self.name}/{token}.m3u8"

    def shutdown(self):
        with self._lock:
            if self._server:
                self._server.shutdown()
                self._server = None
                self._thread = None
                self._port = None
                self._upstream.clear()


# Global instances per (name, options) to avoid spawning multiple servers.
_proxy_instances = {}
_proxy_lock = threading.Lock()


def get_stream_proxy(name: str, default_headers: dict, options: dict = None) -> StreamProxy:
    """Return a singleton StreamProxy for the given name/options."""
    with _proxy_lock:
        key = (name, _hashable_options(options))
        if key not in _proxy_instances:
            _proxy_instances[key] = StreamProxy(name, default_headers, options)
        return _proxy_instances[key]


def build_proxy_url(
    name: str,
    upstream_url: str,
    default_headers: dict,
    options: dict = None,
    per_request_headers: dict = None,
) -> str:
    """One-shot helper: get/create the proxy and register an upstream URL."""
    proxy = get_stream_proxy(name, default_headers, options)
    return proxy.get_proxy_url(upstream_url, per_request_headers)
