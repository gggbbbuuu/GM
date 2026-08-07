from ..models import *
from typing import Optional, List, Tuple
import requests
import re
import json
import base64
import binascii
import xbmc
import threading
import socket
import uuid
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, quote, unquote
from ..tools import debug_log
from ..util import embedsportstop
from ..util.stream_proxy import get_stream_proxy

_XYZ_PROXY = {
    "server": None,
    "thread": None,
    "port": None,
    "lock": threading.Lock(),
    "upstream": {},
}

_DEFAULT_HEADERS = {
    "Origin": "https://xyzstreams.st",
    "Referer": "https://xyzstreams.st/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
}


def _strip_png_wrapper(data: bytes) -> bytes:
    
    PNG_SIG = b'\x89PNG\r\n\x1a\n'
    if not data.startswith(PNG_SIG):
        return data
    offset = len(PNG_SIG)
    chunk_count = 0
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            debug_log(f"[XYZ] PNG chunk {chunk_type} exceeds data length, aborting strip", xbmc.LOGWARNING)
            break
        chunk_count += 1
        if chunk_type == b'IEND':
            video_start = chunk_end
            if video_start < len(data):
                debug_log(f"[XYZ] PNG strip found IEND after {chunk_count} chunks, video data at offset {video_start}", xbmc.LOGINFO)
                return data[video_start:]
            debug_log(f"[XYZ] PNG IEND at end of file, no video data", xbmc.LOGWARNING)
            return b''
        offset = chunk_end
    debug_log(f"[XYZ] PNG IEND not found after {chunk_count} chunks, returning raw data", xbmc.LOGWARNING)
    return data


def _rewrite_m3u8_body(body: str, token: str, port: int, base_url: str = "") -> str:
    """Rewrite every media URL in an m3u8 so Kodi stays routed through our proxy.

    When *base_url* is provided, relative URLs are first resolved against it
    so that multi-level HLS hierarchies (247 streams) keep the correct origin.
    """
    def _rewrite_url(url: str) -> str:
        if base_url and not url.startswith("http://") and not url.startswith("https://"):
            url = urljoin(base_url, url)
        return f"http://127.0.0.1:{port}/xyz/seg/{token}/{quote(url, safe='')}"

    rewritten = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Rewrite URI="..." attributes inside #EXT tags (e.g. EXT-X-MEDIA, EXT-X-KEY)
        def _rewrite_uri_attr(m):
            uri = m.group(2)
            if base_url and not uri.startswith("http://") and not uri.startswith("https://"):
                uri = urljoin(base_url, uri)
            return m.group(1) + f"http://127.0.0.1:{port}/xyz/seg/{token}/{quote(uri, safe='')}" + m.group(3)
        line = re.sub(
            r'(URI=")([^"]+)(")',
            _rewrite_uri_attr,
            line,
        )
        if stripped.startswith("#"):
            rewritten.append(line)
            continue
        rewritten.append(_rewrite_url(stripped))
    return "\n".join(rewritten) + "\n"


def _parse_variant_qualities(m3u8_url: str, headers: dict) -> List[Tuple[str, str, int]]:
    """Fetch a 247 variant playlist and return (name, variant_url, bandwidth) tuples.
    
    Deduplicates by resolution, keeping the highest-bandwidth variant for each resolution.
    """
    all_variants: List[Tuple[str, str, int]] = []
    try:
        resp = requests.get(m3u8_url, headers=headers, timeout=(5, 15))
        if resp.status_code != 200:
            return all_variants
        body = resp.text.replace("\x00", "")
        if not body or "#EXTM3U" not in body:
            return all_variants
        if not _is_variant_playlist(body):
            return all_variants
        base_url = resp.url
        lines = body.splitlines()
        current_bw = 0
        current_res = ""
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#EXT-X-STREAM-INF"):
                m = re.search(r'BANDWIDTH=(\d+)', stripped)
                if m:
                    current_bw = int(m.group(1))
                rm = re.search(r'RESOLUTION=(\d+x\d+)', stripped)
                if rm:
                    current_res = rm.group(1)
            elif stripped and not stripped.startswith("#"):
                variant_url = urljoin(base_url, stripped)
                name = current_res if current_res else f"{current_bw // 1000}k"
                all_variants.append((name, variant_url, current_bw))
                current_bw = 0
                current_res = ""
    except Exception as e:
        debug_log(f"[XYZ] Failed to parse variant qualities: {e}", xbmc.LOGDEBUG)
    
    # Deduplicate by resolution, keeping highest bandwidth for each
    best_by_res: dict = {}
    for name, variant_url, bw in all_variants:
        if name not in best_by_res or bw > best_by_res[name][2]:
            best_by_res[name] = (name, variant_url, bw)
    
    # Sort by bandwidth descending
    qualities = sorted(best_by_res.values(), key=lambda x: x[2], reverse=True)
    return qualities



    """Convert a hex string to base64url (no padding)."""
    return base64.b64encode(binascii.unhexlify(value)).decode("utf-8").replace("+", "-").replace("/", "_").replace("=", "")


def _is_variant_playlist(body: str) -> bool:
    """Return True if the m3u8 body is a variant playlist (has EXT-X-STREAM-INF but no EXTINF)."""
    has_stream_inf = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#EXT-X-STREAM-INF"):
            has_stream_inf = True
        elif stripped.startswith("#EXTINF"):
            return False
    return has_stream_inf


def _sort_variant_playlist(body: str) -> str:
    """Reorder a variant playlist so the highest-bandwidth variant is first."""
    lines = body.splitlines()
    variants = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#EXT-X-STREAM-INF"):
            bw = 0
            m = re.search(r'BANDWIDTH=(\d+)', stripped)
            if m:
                bw = int(m.group(1))
            if i + 1 < len(lines):
                variants.append((bw, lines[i], lines[i + 1]))
                i += 2
                continue
        i += 1
    if not variants:
        return body

    variants.sort(key=lambda x: x[0], reverse=True)
    prefix = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#EXT-X-STREAM-INF"):
            break
        prefix.append(line)
    result = prefix[:]
    for bw, inf, url in variants:
        result.append(inf)
        result.append(url)
    return "\n".join(result) + "\n"


def _resolve_variant_to_media(body: str, base_url: str, session: 'requests.Session',
                              headers: dict, depth: int = 0) -> str:
    """Recursively resolve a variant playlist down to a media playlist.

    247 streams use multi-level HLS: master -> variant playlists -> media playlists.
    ISA expects child manifests to be media playlists (with EXTINF/segments), so we
    must flatten nested variant playlists before serving them.

    Picks the highest-bandwidth variant so ISA gets the best quality stream.
    """
    if depth > 5:
        return body
    if not _is_variant_playlist(body):
        return body

    best_variant_url = None
    best_bandwidth = -1

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        bw = 0
        for prev_line in body.splitlines():
            prev_stripped = prev_line.strip()
            if prev_stripped.startswith("#EXT-X-STREAM-INF"):
                m = re.search(r'BANDWIDTH=(\d+)', prev_stripped)
                if m:
                    bw = int(m.group(1))
                break

        if best_variant_url is None or bw > best_bandwidth:
            best_variant_url = urljoin(base_url, stripped)
            best_bandwidth = bw

    if not best_variant_url:
        return body

    debug_log(f"[XYZ] Resolving best variant (depth={depth}, bw={best_bandwidth}): {best_variant_url}", xbmc.LOGINFO)
    try:
        child_resp = session.get(best_variant_url, headers=headers, timeout=(5, 15))
        if child_resp.status_code != 200:
            debug_log(f"[XYZ] Variant child returned {child_resp.status_code}: {best_variant_url}", xbmc.LOGWARNING)
            return body
        child_body = child_resp.text
        child_body = child_body.replace("\x00", "")
        if not child_body or "#EXTM3U" not in child_body:
            return body
        child_body = child_body.replace(".png", ".ts")
        if _is_variant_playlist(child_body):
            child_body = _resolve_variant_to_media(child_body, best_variant_url, session, headers, depth + 1)
        if "#EXTINF" in child_body:
            return child_body
    except Exception as e:
        debug_log(f"[XYZ] Variant child fetch failed: {e}", xbmc.LOGWARNING)
    return body


def _extract_clearkey(stream_url: str, headers: dict, timeout: float) -> Optional[str]:
    """Fetch the HLS manifest and return an InputStream Adaptive ClearKey license_key."""
    try:
        resp = requests.get(stream_url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None
        m = re.search(r"ck=([a-f0-9]+)(?:%3A|:)([a-f0-9]+)", resp.text, re.IGNORECASE)
        if not m:
            return None
        kid_b64 = _hex_to_base64url(m.group(1))
        key_b64 = _hex_to_base64url(m.group(2))
        return f"{kid_b64}:{key_b64}"
    except Exception as e:
        debug_log(f"[XYZ] ClearKey extraction failed: {e}", xbmc.LOGDEBUG)
    return None


class _XYZProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        raw_path_for_token = self.path.split("?")[0].lstrip("/")
        upstream_map = _XYZ_PROXY["upstream"]
        debug_log(f"[XYZ] Proxy GET {self.path}", xbmc.LOGINFO)

        
        if raw_path_for_token.startswith("xyz/") and raw_path_for_token.endswith(".m3u8"):
            token = raw_path_for_token[len("xyz/"):-len(".m3u8")]
            entry = upstream_map.get(token)
            if not entry:
                debug_log(f"[XYZ] Token not found: {token}", xbmc.LOGWARNING)
                self._fail(404, b"Token not found")
                return
            upstream_url = entry["url"]
            headers = entry.get("headers") or {}
            port = _XYZ_PROXY["port"]
            debug_log(f"[XYZ] Proxy fetching upstream m3u8: {upstream_url}", xbmc.LOGINFO)
            now = time.time()
            is_live_247 = "247" in upstream_url
            if not is_live_247 and entry.get("cache") and (now - entry.get("cache_time", 0)) < 0.5:
                data = entry["cache"]
                debug_log(f"[XYZ] Serving cached m3u8 ({len(data)} bytes)", xbmc.LOGINFO)
            else:
                try:
                   
                    req_headers = dict(_DEFAULT_HEADERS)
                    req_headers.update(headers)
                    session = entry.get("session") or requests.Session()
                    resp = session.get(
                        upstream_url, timeout=(5, 15), headers=req_headers
                    )
                    debug_log(f"[XYZ] Upstream response: {resp.status_code} (final URL: {resp.url})", xbmc.LOGINFO)
                    if resp.status_code != 200:
                        debug_log(f"[XYZ] Upstream error {resp.status_code}: {resp.text[:200]}", xbmc.LOGWARNING)
                        self._fail(502, f"Upstream {resp.status_code}".encode())
                        return
                    
                    raw_bytes = resp.content
                    if len(raw_bytes) > 256 * 1024:
                        raw_bytes = raw_bytes[:256 * 1024]
                    final_url = resp.url
                    resp.close()
                   
                    try:
                        import gzip, zlib
                        if raw_bytes[:2] == b'\x1f\x8b':
                            raw_bytes = gzip.decompress(raw_bytes)
                        elif raw_bytes[:2] in (b'\x78\x9c', b'\x78\x01', b'\x78\xda'):
                            raw_bytes = zlib.decompress(raw_bytes)
                    except Exception:
                        pass
                    try:
                        body = raw_bytes.decode("utf-8", errors="replace")
                    except Exception:
                        body = raw_bytes.decode("utf-8", errors="ignore")
                    body = body.replace("\x00", "")
                    debug_log(f"[XYZ] Upstream body length: {len(body)}", xbmc.LOGINFO)
                    if not body or "#EXTM3U" not in body:
                        debug_log(f"[XYZ] Upstream body invalid: {body[:200]}", xbmc.LOGWARNING)
                        self._fail(502, b"Upstream not m3u8")
                        return
                    
                    body = body.replace(".png", ".ts")
                    debug_log(f"[XYZ] Original m3u8 first 500 chars:\n{body[:500]}", xbmc.LOGINFO)

                    if _is_variant_playlist(body):
                        debug_log(f"[XYZ] Sorting variant playlist by highest bandwidth first", xbmc.LOGINFO)
                        body = _sort_variant_playlist(body)

                    # All streams go through proxy URL rewriting so that
                    # InputStream Adaptive fetches segments through our proxy,
                    # which maintains the server-side session cookie chain.
                    rewritten_body = _rewrite_m3u8_body(body, token, port, base_url=final_url)
                    data = rewritten_body.encode("utf-8")
                    entry["cache"] = data
                    entry["cache_time"] = now
                    debug_log(f"[XYZ] Rewrote m3u8, {len(rewritten_body.splitlines())} lines, {len(data)} bytes", xbmc.LOGINFO)
                    
                    try:
                        debug_manifest = data.decode('utf-8', errors='replace')[:500]
                        debug_log(f"[XYZ] Rewritten m3u8 first 500 chars:\n{debug_manifest}", xbmc.LOGINFO)
                    except Exception:
                        pass
                except Exception as e:
                    debug_log(f"[XYZ] manifest rebuild failed: {e}", xbmc.LOGWARNING)
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
                debug_log(f"[XYZ] Sent m3u8 response ({len(data)} bytes), Content-Type: application/vnd.apple.mpegurl", xbmc.LOGINFO)
            except (ConnectionAbortedError, BrokenPipeError) as e:
                debug_log(f"[XYZ] client disconnected during manifest write: {e}", xbmc.LOGDEBUG)
            return

        
        if raw_path_for_token.startswith("xyz/seg/"):
            full_path = self.path.split("?")[0].lstrip("/")
            token_and_rest = full_path[len("xyz/seg/"):]
            if "/" in token_and_rest:
                token, seg_path = token_and_rest.split("/", 1)
                seg_path = unquote(seg_path)
            else:
                token, seg_path = token_and_rest, ""
            entry = upstream_map.get(token)
            if not entry or not seg_path:
                debug_log(f"[XYZ] Segment token/path not found: {token}/{seg_path}", xbmc.LOGWARNING)
                self._fail(404, b"Token/segment not found")
                return
            upstream_url = entry["url"]
            headers = entry.get("headers") or {}
            
            parsed_upstream = urlparse(upstream_url)
            auth_query = parsed_upstream.query
            
            def _rewrite_ts_to_png(url: str) -> str:
                
                if ".ts?" in url or ".TS?" in url:
                    return url.replace(".ts?", ".png?").replace(".TS?", ".png?")
                if url.endswith(".ts") or url.endswith(".TS"):
                    return url[:-3] + ".png"
                return url
            if seg_path.startswith("http://") or seg_path.startswith("https://"):
                target = _rewrite_ts_to_png(seg_path)
            else:
                target = _rewrite_ts_to_png(urljoin(upstream_url, seg_path))
            
            # Only merge upstream auth params when the segment path was relative
            # (resolved against upstream_url). Absolute URLs (stream.xyzstreams.st)
            # have their own query params - merging 247's auth_query corrupts them.
            if auth_query and not (seg_path.startswith("http://") or seg_path.startswith("https://")):
                target_parsed = urlparse(target)
                target_qs = parse_qs(target_parsed.query)
                auth_qs = parse_qs(auth_query)
                merged_qs = dict(target_qs)
                for key, values in auth_qs.items():
                    if key not in merged_qs:
                        merged_qs[key] = values
                merged_query = urlencode(merged_qs, doseq=True)
                target = target_parsed._replace(query=merged_query).geturl()
            debug_log(f"[XYZ] Proxy segment: {target}", xbmc.LOGINFO)
            try:
                session = entry.get("session") or requests.Session()
               
                seg_headers = dict(_DEFAULT_HEADERS)
                seg_headers.update(headers)
                upstream_resp = session.get(
                    target, headers=seg_headers, timeout=(5, 30), stream=True, allow_redirects=True
                )
                upstream_content_type = upstream_resp.headers.get("Content-Type", "")
                debug_log(f"[XYZ] Segment upstream status: {upstream_resp.status_code}, Content-Type: {upstream_content_type}, Target: {target}", xbmc.LOGINFO)
                if upstream_resp.status_code not in (200, 206):
                    self.send_response(upstream_resp.status_code)
                    self.end_headers()
                    try:
                        upstream_resp.close()
                    except Exception:
                        pass
                    return
                content_type = upstream_content_type if upstream_content_type else "video/mp2t"
                
                ct_lower = content_type.lower()
                if any(bad in ct_lower for bad in ("javascript", "text/", "image/", "application/json")):
                    content_type = "video/mp2t"
                
                if target.lower().endswith(".png"):
                    content_type = "video/mp2t"

                
                segment_data = b""
                try:
                    for chunk in upstream_resp.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            segment_data += chunk
                            if len(segment_data) > 32 * 1024 * 1024:  # Safety cap at 32MB
                                break
                except Exception as e:
                    debug_log(f"[XYZ] Segment download error: {e}", xbmc.LOGWARNING)
                    self._fail(502, b"Download error")
                    upstream_resp.close()
                    return
                finally:
                    upstream_resp.close()

                
                original_len = len(segment_data)
                segment_data = _strip_png_wrapper(segment_data)
                if len(segment_data) != original_len:
                    debug_log(f"[XYZ] Stripped PNG wrapper: {original_len} -> {len(segment_data)} bytes", xbmc.LOGINFO)
                    
                    if len(segment_data) >= 16:
                        prefix = " ".join(f"{b:02x}" for b in segment_data[:16])
                        debug_log(f"[XYZ] Segment first bytes after PNG strip: {prefix}", xbmc.LOGINFO)
                        
                        if segment_data[0] != 0x47:
                            debug_log(f"[XYZ] WARNING: First byte after PNG strip is 0x{segment_data[0]:02x}, expected 0x47 (TS sync)", xbmc.LOGWARNING)
                else:
                    
                    if len(segment_data) >= 1 and segment_data[0] != 0x47:
                        prefix = " ".join(f"{b:02x}" for b in segment_data[:16])
                        debug_log(f"[XYZ] WARNING: Segment starts with 0x{segment_data[0]:02x} (not TS sync 0x47), bytes: {prefix}", xbmc.LOGWARNING)

                # If the upstream returned another HLS manifest (variant/playlist),
                # decide how to expose it to Kodi.
                is_m3u8 = "mpegurl" in content_type.lower() or segment_data.startswith(b"#EXTM3U")
                if is_m3u8:
                    try:
                        manifest_body = segment_data.decode("utf-8", errors="replace")
                        manifest_body = manifest_body.replace("\x00", "")
                        manifest_body = manifest_body.replace(".png", ".ts")

                        if _is_variant_playlist(manifest_body):
                            seg_headers = dict(_DEFAULT_HEADERS)
                            seg_headers.update(headers)
                            manifest_body = _resolve_variant_to_media(
                                manifest_body, target, session, seg_headers
                            )
                            debug_log(
                                f"[XYZ] Resolved variant playlist to media playlist ({len(manifest_body.splitlines())} lines)",
                                xbmc.LOGINFO,
                            )

                        port = _XYZ_PROXY["port"]
                        rewritten_body = _rewrite_m3u8_body(manifest_body, token, port, base_url=target)
                        segment_data = rewritten_body.encode("utf-8")
                        content_type = "application/vnd.apple.mpegurl"
                        debug_log(
                            f"[XYZ] Rewrote nested manifest ({len(rewritten_body.splitlines())} lines)",
                            xbmc.LOGINFO,
                        )
                    except Exception as e:
                        debug_log(f"[XYZ] Nested manifest rewrite failed: {e}", xbmc.LOGWARNING)

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(segment_data)))
                self.end_headers()
                try:
                    self.wfile.write(segment_data)
                    debug_log(f"[XYZ] Segment sent {len(segment_data)} bytes, type={content_type}", xbmc.LOGINFO)
                except (ConnectionAbortedError, BrokenPipeError) as e:
                    debug_log(f"[XYZ] client disconnected mid-segment: {e}", xbmc.LOGDEBUG)
            except Exception as e:
                debug_log(f"[XYZ] proxy segment fetch failed for {target}: {e}", xbmc.LOGWARNING)
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
            debug_log(f"[XYZ] _fail write error: {e}", xbmc.LOGDEBUG)


def _ensure_xyz_proxy() -> int:
    with _XYZ_PROXY["lock"]:
        if _XYZ_PROXY["server"] is not None:
            return _XYZ_PROXY["port"]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        server = ThreadingHTTPServer(("127.0.0.1", port), _XYZProxyHandler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, name="XYZProxy")
        thread.daemon = True
        thread.start()
        _XYZ_PROXY["server"] = server
        _XYZ_PROXY["thread"] = thread
        _XYZ_PROXY["port"] = port
        debug_log(f"[XYZ] Proxy listening on 127.0.0.1:{port}", xbmc.LOGINFO)
        return port


class XYZ(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["xyzstreams.st"]
        self.name = "XYZ"
        self.short_name = "XYZ"
        self.base_url = f"https://{self.domains[0]}"
        self.embed_api = f"{self.base_url}/embedapi.json"
        self.scoreboard_api = "https://api.streamxyz.shop:2053/api/scoreboard"
        self.alt_streams_api = "https://api.ppv.st/api/streams"

        self.stream_headers = {
            "Origin": self.base_url,
            "Referer": self.base_url + "/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
        # "Accept": "*/*",
        # "Accept-Language": "en-US,en;q=0.9",
        # "Accept-Encoding": "gzip, deflate, br, zstd",
        # "DNT": "1",
        # "Sec-Ch-Ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        # "Sec-Ch-Ua-Mobile": "?0",
        # "Sec-Ch-Ua-Platform": '"Windows"',
        # "Sec-Fetch-Dest": "empty",
        # "Sec-Fetch-Mode": "cors",
        # "Sec-Fetch-Site": "cross-site",
    }

    def _build_proxy_link(self, upstream_url: str, headers: dict) -> str:
        port = _ensure_xyz_proxy()
        token = uuid.uuid4().hex
        _XYZ_PROXY["upstream"][token] = {
            "url": upstream_url,
            "headers": headers or {},
            "cache": None,
            "cache_time": 0.0,
            "session": requests.Session(),
        }
        proxy_url = f"http://127.0.0.1:{port}/xyz/{token}.m3u8"
        debug_log(f"[XYZ] Proxy registered: {proxy_url}", xbmc.LOGINFO)
        return proxy_url

    def _fetch_scoreboard(self) -> List[JetItem]:
        items: List[JetItem] = []
        try:
            headers = dict(self.stream_headers)
            headers["Accept"] = "application/json"
            resp = requests.get(
                self.scoreboard_api,
                timeout=self.timeout,
                headers=headers,
            )
            if resp.status_code != 200:
                debug_log(f"[XYZ] Scoreboard API returned {resp.status_code}", xbmc.LOGDEBUG)
                return items
            data = resp.json()
            if not isinstance(data, list):
                return items
            for game in data:
                if not isinstance(game, dict):
                    continue
                away = game.get("away", {})
                home = game.get("home", {})
                away_name = away.get("name", "Away")
                home_name = home.get("name", "Home")
                title = f"{away_name} @ {home_name}"
                feeds = game.get("feeds", {})
                if not feeds:
                    continue
                links: List[JetLink] = []
                for feed_name, feed_url in feeds.items():
                    if not feed_url or not isinstance(feed_url, str):
                        continue
                    proxy_url = self._build_proxy_link(feed_url, dict(self.stream_headers))
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=feed_name,
                            headers=dict(self.stream_headers),
                            inputstream=JetInputstreamFFmpegDirect.default(),
                            resolveurl=False,
                        )
                    )
                if links:
                    status = game.get("statusText", "")
                    if status:
                        title = f"[{status}] {title}"
                    items.append(
                        JetItem(
                            title=title,
                            league="MLB",
                            links=links,
                        )
                    )
        except Exception as e:
            debug_log(f"[XYZ] Scoreboard fetch failed: {e}", xbmc.LOGDEBUG)
        return items

    def _extract_js_array(self, html: str, var_name: str) -> list:
        try:
            m = re.search(rf"const\s+{re.escape(var_name)}\s*=\s*(\[.*?\]);", html, re.DOTALL)
            if not m:
                return []
            raw = m.group(1)
            # Strip JS comments (avoiding :// in URLs)
            raw = re.sub(r"(?<!:)//.*?$", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
            # Convert single-quoted strings to double-quoted
            raw = re.sub(
                r"'((?:\\.|[^'\\])*)'",
                lambda match: '"' + match.group(1).replace("\\'", "'") + '"',
                raw,
            )
            # Convert unquoted object keys to JSON-quoted keys
            raw = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', raw)
            # Remove trailing commas before } or ]
            raw = re.sub(r",\s*(?=[}\]])", "", raw)
            return json.loads(raw)
        except Exception as e:
            debug_log(f"[XYZ] Failed to parse {var_name}: {e}", xbmc.LOGDEBUG)
            return []

    def _parse_events(self, html: str) -> List[JetItem]:
        items: List[JetItem] = []
        for event in self._extract_js_array(html, "EVENTS_DATA"):
            if not isinstance(event, dict):
                continue
            title = event.get("title", "Event").strip()
            href = event.get("href", "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = self.base_url + href
            elif not href.startswith("http"):
                href = f"{self.base_url}/{href}"

            league = self._guess_league(title, event.get("category"))

            start = event.get("start", "")
            end = event.get("end", "")
            status = ""
            if start and end:
                try:
                    import time as _time
                    now = _time.time()
                    start_ts = self._parse_iso_ts(start)
                    end_ts = self._parse_iso_ts(end)
                    if start_ts and end_ts:
                        if now < start_ts:
                            status = "Upcoming"
                        elif now > end_ts:
                            status = "Ended"
                        else:
                            status = "LIVE"
                except Exception:
                    pass

            if status:
                title = f"[{status}] {title}"

            items.append(
                JetItem(
                    title=title,
                    league=league,
                    links=[JetLink(href, links=True)],
                )
            )
        return items

    def _parse_sling_map(self, html: str) -> List[JetItem]:
        """Parse SLING_LINEUP_MAP (object/dict with 80+ channels)."""
        items: List[JetItem] = []
        try:
            m = re.search(r"const\s+SLING_LINEUP_MAP\s*=\s*(\{.*?\});", html, re.DOTALL)
            if not m:
                debug_log("[XYZ] SLING_LINEUP_MAP not found in HTML", xbmc.LOGDEBUG)
                return items
            raw = m.group(1)
            # Convert single-quoted strings to double-quoted
            raw = re.sub(
                r"'((?:\\.|[^'\\])*)'",
                lambda match: '"' + match.group(1).replace("\\'", "'") + '"',
                raw,
            )
            # Convert unquoted keys to quoted
            raw = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', raw)
            # Remove trailing commas
            raw = re.sub(r",\s*(?=[}\]])", "", raw)
            channels_map = json.loads(raw)
            if not isinstance(channels_map, dict):
                return items
            for key, chan in channels_map.items():
                if not isinstance(chan, dict):
                    continue
                name = chan.get("displayName", "").strip()
                if not name:
                    continue
                embed_url = chan.get("embedUrl", "").strip()
                if embed_url:
                    if embed_url.startswith("http://") or embed_url.startswith("https://"):
                        embed_url_abs = embed_url
                    elif embed_url.startswith("/"):
                        embed_url_abs = self.base_url + embed_url
                    else:
                        embed_url_abs = f"{self.base_url}/{embed_url}"
                else:
                    stream_id = chan.get("id", "")
                    if not stream_id:
                        continue
                    embed_url_abs = f"{self.base_url}/247.html?streamid={stream_id}&proid=sling"
                items.append(
                    JetItem(
                        title=name,
                        league="Cable",
                        links=[JetLink(embed_url_abs, links=True)],
                    )
                )
        except Exception as e:
            debug_log(f"[XYZ] Failed to parse SLING_LINEUP_MAP: {e}", xbmc.LOGWARNING)
        return items

    def _fetch_homepage_data(self) -> Tuple[List[JetItem], List[JetItem]]:
        events: List[JetItem] = []
        channels: List[JetItem] = []
        try:
            headers = dict(self.stream_headers)
            resp = requests.get(self.base_url, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                return events, channels
            html = resp.text
            events = self._parse_events(html)
            channels = self._parse_sling_map(html)
        except Exception as e:
            debug_log(f"[XYZ] Homepage fetch failed: {e}", xbmc.LOGDEBUG)
        return events, channels

    def _fetch_alt_streams(self) -> List[JetItem]:
        items: List[JetItem] = []
        try:
            headers = dict(self.stream_headers)
            headers.update({
                "Accept": "application/json",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/alt",
            })
            resp = requests.get(
                self.alt_streams_api,
                timeout=self.timeout,
                headers=headers,
            )
            if resp.status_code != 200:
                debug_log(f"[XYZ] Alt streams API returned {resp.status_code}", xbmc.LOGWARNING)
                return items
            data = resp.json()
            if not isinstance(data, dict) or not data.get("success"):
                return items
            categories = data.get("streams", [])
            if not isinstance(categories, list):
                return items
            now = time.time()
            for category in categories:
                if not isinstance(category, dict):
                    continue
                category_name = str(category.get("category") or "Sports").strip()
                streams = category.get("streams", [])
                if not isinstance(streams, list):
                    continue
                for stream in streams:
                    if not isinstance(stream, dict):
                        continue
                    title = str(stream.get("name") or "Stream").strip()
                    iframe = stream.get("iframe")
                    if not title or not isinstance(iframe, str) or not iframe.startswith(("http://", "https://")):
                        continue
                    resolver_url = f"{self.base_url}/jetextractor/alt?url={quote(iframe, safe='')}"
                    links = [JetLink(resolver_url, name=str(stream.get("tag") or "Main"), links=True)]
                    substreams = stream.get("substreams", [])
                    if isinstance(substreams, list):
                        for substream in substreams:
                            if not isinstance(substream, dict):
                                continue
                            sub_iframe = substream.get("iframe")
                            if isinstance(sub_iframe, str) and sub_iframe.startswith(("http://", "https://")):
                                links.append(
                                    JetLink(
                                        f"{self.base_url}/jetextractor/alt?url={quote(sub_iframe, safe='')}",
                                        name=str(substream.get("tag") or substream.get("name") or "Alternate"),
                                        links=True,
                                    )
                                )
                    starts_at = stream.get("starts_at")
                    ends_at = stream.get("ends_at")
                    always_live = bool(stream.get("always_live") or category.get("always_live"))
                    status = "LIVE" if always_live else None
                    if not always_live and isinstance(starts_at, (int, float)):
                        if now < starts_at:
                            status = "Upcoming"
                        elif isinstance(ends_at, (int, float)) and now > ends_at:
                            status = "Ended"
                        else:
                            status = "LIVE"
                    items.append(
                        JetItem(
                            title=title,
                            league=self._guess_league(title, category_name),
                            links=links,
                            status=status,
                            icon=stream.get("poster"),
                        )
                    )
        except Exception as e:
            debug_log(f"[XYZ] Alt streams fetch failed: {e}", xbmc.LOGWARNING)
        return items

    def _parse_iso_ts(self, ts: str) -> Optional[float]:
        try:
            ts = ts.replace("Z", "+00:00")
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception:
            return None

    def _guess_league(self, title: str, category: Optional[str] = None) -> str:
        if category:
            cat = category.lower()
            if cat in ("football", "soccer"):
                return "Soccer"
            if cat in ("american football", "football (american)"):
                return "NFL"
            if cat in ("combat sports", "mma", "boxing"):
                return "MMA / Boxing"
            if cat == "basketball":
                return "NBA"
            if cat == "baseball":
                return "MLB"
            if cat == "hockey":
                return "NHL"
            if cat == "football (american)":
                return "NFL"
        t = title.lower()
        if any(x in t for x in ["ufc", "boxing", "wwe"]):
            return "MMA / Boxing"
        if any(x in t for x in ["nhl", "golden knights", "hurricanes"]):
            return "NHL"
        if any(x in t for x in ["mlb", "baseball", "yankees", "dodgers"]):
            return "MLB"
        if any(x in t for x in ["nba", "basketball", "lakers", "celtics"]):
            return "NBA"
        if any(x in t for x in ["nfl", "football", "super bowl", "chiefs"]):
            return "NFL"
        if any(x in t for x in ["fifa", "world cup", "epl", "premier league", "la liga", "bundesliga", "serie a", "uefa", "champions league"]):
            return "Soccer"
        return "Sports"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        homepage_items, channel_items = self._fetch_homepage_data()
        alt_items = self._fetch_alt_streams()
        items.extend(homepage_items)
        items.extend(channel_items)
        items.extend(alt_items)

        debug_log(f"[XYZ] Total items: {len(items)} (Events={len(homepage_items)}, Channels={len(channel_items)}, Alt={len(alt_items)})", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        debug_log(f"[XYZ] get_links called for: {url.address}", xbmc.LOGINFO)
        links: List[JetLink] = []
        if "127.0.0.1" in url.address and "/xyz/" in url.address:
            links.append(
                JetLink(
                    address=url.address,
                    name=url.name or "Stream",
                    headers=dict(self.stream_headers),
                    inputstream=JetInputstreamFFmpegDirect.default(),
                    resolveurl=False,
                )
            )
            return links

        parsed_url = urlparse(url.address)
        if parsed_url.path == "/jetextractor/alt":
            iframe_urls = parse_qs(parsed_url.query).get("url", [])
            if not iframe_urls:
                return links
            embed_url = iframe_urls[0]
        else:
            embed_url = url.address

        if "embedindia" in urlparse(embed_url).netloc:
            try:
                stream_url = embedsportstop.get_embedsportstop_stream(embed_url)
                if stream_url:
                    embed_origin = f"{urlparse(embed_url).scheme}://{urlparse(embed_url).netloc}"
                    headers = {
                        "Origin": embed_origin,
                        "Referer": f"{embed_origin}/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
                        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": '"Windows"',
                        "Accept": "*/*",
                    }
                    debug_log(f"[XYZ] Resolved embedindia stream URL: {stream_url}", xbmc.LOGINFO)
                    proxy = get_stream_proxy(
                        "xyz_alt",
                        headers,
                        options={
                            "strip_png": True,
                            "manifest_png_to_ts": True,
                            "proxy_absolute_urls": True,
                            "cache_manifest": False,
                            "add_icy_metadata": False,
                            "browser_tls": True,
                        },
                    )
                    proxy_url = proxy.get_proxy_url(stream_url, headers)
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=url.name or "Stream",
                            inputstream=JetInputstreamAdaptive(
                                manifest_type="hls",
                                manifest_headers=headers,
                            ),
                            resolveurl=False,
                        )
                    )
            except Exception as e:
                debug_log(f"[XYZ] EmbedIndia resolution failed: {e}", xbmc.LOGWARNING)
            return links

        if ".m3u8" in url.address or ".mpd" in url.address:
            proxy_url = self._build_proxy_link(url.address, dict(self.stream_headers))
            if "247" in urlparse(url.address).netloc:
                license_key = _extract_clearkey(
                    url.address, dict(self.stream_headers), self.timeout
                )
                if license_key:
                    inputstream = JetInputstreamAdaptive(
                        manifest_type="hls",
                        license_type="org.w3.clearkey",
                        license_key=license_key,
                    )
                else:
                    inputstream = JetInputstreamAdaptive(manifest_type="hls")
            else:
                inputstream = JetInputstreamAdaptive(manifest_type="hls")
            links.append(
                JetLink(
                    address=proxy_url,
                    name=url.name or "Stream",
                    headers=dict(self.stream_headers),
                    inputstream=inputstream,
                    resolveurl=False,
                )
            )
            return links

        try:
            headers = dict(self.stream_headers)
            resp = requests.get(url.address, timeout=self.timeout, headers=headers)
            if resp.status_code != 200:
                debug_log(f"[XYZ] Embed page returned {resp.status_code}", xbmc.LOGWARNING)
                return links

            html = resp.text
            stream_urls = []
            m = re.search(r'const\s+streamUrl\s*=\s*"([^"]+)"', html)
            if m:
                stream_urls.append(m.group(1))
            stream_urls.extend(re.findall(r'source\s*[:=]\s*"(https?://[^"]+)"', html))
            stream_urls.extend(re.findall(r'(https?://[^\s"\'<>]+(?:\.m3u8|\.mpd)[^\s"\'<>]*)', html))

            # Drop JavaScript template literals and keep real URLs
            valid_urls = [
                u for u in stream_urls
                if "${" not in u and (u.startswith("http://") or u.startswith("https://"))
            ]

            # Embed pages (247.html / cbs2.html etc.) often build the URL with JS.
            # If nothing static was found, build it from the embed URL's own params.
            if not valid_urls:
                stream_id_match = re.search(r'[?&]streamid=([^&]+)', url.address)
                if stream_id_match:
                    stream_id = stream_id_match.group(1)
                    pro_id = "sling"
                    pro_id_match = re.search(r'[?&]proid=([^&]+)', url.address)
                    if pro_id_match:
                        pro_id = pro_id_match.group(1)
                    if "247v2.xyzstreams.st" in html:
                        valid_urls.append(
                            f"https://247v2.xyzstreams.st/?stream_id={stream_id}&pro_id={pro_id}&index.m3u8"
                        )
                    else:
                        valid_urls.append(
                            f"https://247.xyzstreams.st/?stream_id={stream_id}&pro_id={pro_id}&index.mpd"
                        )

            seen = set()
            for m3u8 in valid_urls:
                if m3u8 in seen:
                    continue
                seen.add(m3u8)
                debug_log(f"[XYZ] Found stream: {m3u8}", xbmc.LOGINFO)
                slug_match = re.search(r'[?&]stream_id=([^&]+)', m3u8)
                slug = slug_match.group(1) if slug_match else "Stream"

                # For 247 streams, fetch the variant playlist and offer each quality as a separate link
                if "247" in urlparse(m3u8).netloc:
                    qualities = _parse_variant_qualities(m3u8, dict(self.stream_headers))
                    if qualities:
                        debug_log(f"[XYZ] Found {len(qualities)} quality variants for {slug}", xbmc.LOGINFO)
                        for name, variant_url, bw in qualities:
                            proxy_url = self._build_proxy_link(variant_url, dict(self.stream_headers))
                            license_key = _extract_clearkey(
                                variant_url, dict(self.stream_headers), self.timeout
                            )
                            if license_key:
                                inputstream = JetInputstreamAdaptive(
                                    manifest_type="hls",
                                    license_type="org.w3.clearkey",
                                    license_key=license_key,
                                )
                            else:
                                inputstream = JetInputstreamAdaptive(manifest_type="hls")
                            links.append(
                                JetLink(
                                    address=proxy_url,
                                    name=f"{slug} - {name}",
                                    headers=dict(self.stream_headers),
                                    inputstream=inputstream,
                                    resolveurl=False,
                                )
                            )
                        continue

                proxy_url = self._build_proxy_link(m3u8, dict(self.stream_headers))

                # The 247.xyzstreams proxies serve DRM-wrapped HLS/DASH.
                # InputStream Adaptive with the manifest's ClearKey is required.
                if "247" in urlparse(m3u8).netloc:
                    license_key = _extract_clearkey(
                        m3u8, dict(self.stream_headers), self.timeout
                    )
                    if license_key:
                        debug_log(f"[XYZ] Using ClearKey for {slug}", xbmc.LOGINFO)
                        inputstream = JetInputstreamAdaptive(
                            manifest_type="hls",
                            license_type="org.w3.clearkey",
                            license_key=license_key,
                        )
                    else:
                        inputstream = JetInputstreamAdaptive(manifest_type="hls")
                else:
                    inputstream = JetInputstreamAdaptive(manifest_type="hls")

                links.append(
                    JetLink(
                        address=proxy_url,
                        name=slug,
                        headers=dict(self.stream_headers),
                        inputstream=inputstream,
                        resolveurl=False,
                    )
                )
            if not links:
                debug_log("[XYZ] No streams found in embed page", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[XYZ] Error in get_links: {e}", xbmc.LOGERROR)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        debug_log(f"[XYZ] get_link called for: {url.address}", xbmc.LOGINFO)
        if "127.0.0.1" in url.address and "/xyz/" in url.address:
            return JetLink(
                address=url.address,
                headers=dict(self.stream_headers),
                inputstream=JetInputstreamFFmpegDirect.default(),
                resolveurl=False,
            )

        if ".m3u8" in url.address or ".mpd" in url.address:
            proxy_url = self._build_proxy_link(url.address, dict(self.stream_headers))
            if "247" in urlparse(url.address).netloc:
                license_key = _extract_clearkey(
                    url.address, dict(self.stream_headers), self.timeout
                )
                if license_key:
                    inputstream = JetInputstreamAdaptive(
                        manifest_type="hls",
                        license_type="org.w3.clearkey",
                        license_key=license_key,
                    )
                else:
                    inputstream = JetInputstreamAdaptive(manifest_type="hls")
            else:
                inputstream = JetInputstreamAdaptive(manifest_type="hls")
            return JetLink(
                address=proxy_url,
                headers=dict(self.stream_headers),
                inputstream=inputstream,
                resolveurl=False,
            )

        links = self.get_links(url)
        if links:
            return links[0]
        return JetLink(address=url.address)
