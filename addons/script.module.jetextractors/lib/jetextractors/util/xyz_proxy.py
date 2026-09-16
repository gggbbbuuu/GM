import base64
import binascii
import json
import re
import socket
import threading
import time
import uuid
import xbmc
import requests
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, List, Tuple, Dict
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, quote, unquote

from ..tools import debug_log
from .._core import get_session
from .xyz_helpers import (
    _hex_to_base64url,
    _strip_png_wrapper,
    _strip_riff_wrapper,
    _rewrite_m3u8_body,
    _best_quality_master,
)
from .manifest_rewriter import _is_variant_playlist


_XYZ_PROXY = {
    "server": None,
    "thread": None,
    "port": None,
    "lock": threading.Lock(),
    "upstream": {},
    "abort": threading.Event(),
    "client_sockets": set(),
    "client_sockets_lock": threading.Lock(),
    "idle_timer": None,
}

XYZ_PROXY_IDLE_TIMEOUT = 120

_DEFAULT_HEADERS = {
    "Origin": "https://xyzstreams.st",
    "Referer": "https://xyzstreams.st/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
}


def _reset_xyz_idle_timer():
    """Reset the idle shutdown timer. Called on each incoming request.
    If no requests arrive within XYZ_PROXY_IDLE_TIMEOUT seconds, the proxy
    shuts itself down so that subsequent CCurlFile::Stat gets an immediate
    'connection refused' instead of a 20-second timeout."""
    with _XYZ_PROXY["lock"]:
        _reset_xyz_idle_timer_locked()


def _reset_xyz_idle_timer_locked():
    """Inner timer reset. Caller MUST already hold _XYZ_PROXY['lock']."""
    if _XYZ_PROXY["server"] is None:
        return
    old = _XYZ_PROXY.get("idle_timer")
    if old:
        old.cancel()
        debug_log("[XYZ] Idle timer cancelled (new request arrived)", xbmc.LOGDEBUG)
    timer = threading.Timer(XYZ_PROXY_IDLE_TIMEOUT, _xyz_idle_shutdown)
    timer.daemon = True
    _XYZ_PROXY["idle_timer"] = timer
    timer.start()
    debug_log(f"[XYZ] Idle timer started ({XYZ_PROXY_IDLE_TIMEOUT}s)", xbmc.LOGDEBUG)


def _xyz_idle_shutdown():
    """Shut down the proxy if it has been idle for XYZ_PROXY_IDLE_TIMEOUT seconds."""
    if _XYZ_PROXY["abort"].is_set():
        debug_log("[XYZ] Idle timer: abort already set, skipping", xbmc.LOGDEBUG)
        return
    with _XYZ_PROXY["lock"]:
        if _XYZ_PROXY["server"] is None:
            debug_log("[XYZ] Idle timer: server already None, skipping", xbmc.LOGDEBUG)
            return
        has_clients = bool(_XYZ_PROXY["client_sockets"])
        client_count = len(_XYZ_PROXY["client_sockets"])
    if has_clients:
        debug_log(f"[XYZ] Idle timer: {client_count} clients still active, resetting timer", xbmc.LOGDEBUG)
        _reset_xyz_idle_timer()
        return
    debug_log(
        f"[XYZ] Proxy idle for {XYZ_PROXY_IDLE_TIMEOUT}s, shutting down to avoid Stat freeze",
        xbmc.LOGINFO,
    )
    _shutdown_xyz_proxy()


def _parse_variant_qualities(m3u8_url: str, headers: dict) -> List[Tuple[str, str, int]]:
    """Fetch a 247 variant playlist and return (name, variant_url, bandwidth) tuples.

    Deduplicates by resolution, keeping the highest-bandwidth variant for each resolution.
    """
    all_variants: List[Tuple[str, str, int]] = []
    try:
        resp = get_session().get(m3u8_url, headers=headers, timeout=(5, 15))
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

    best_by_res: dict = {}
    for name, variant_url, bw in all_variants:
        if name not in best_by_res or bw > best_by_res[name][2]:
            best_by_res[name] = (name, variant_url, bw)

    qualities = sorted(best_by_res.values(), key=lambda x: x[2], reverse=True)
    return qualities


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
        ssl_verify = "247.xyzstreams.st" not in best_variant_url and "247v2.dlhd.net" not in best_variant_url
        child_resp = session.get(best_variant_url, headers=headers, timeout=(5, 15), verify=ssl_verify)
        if child_resp.status_code != 200:
            debug_log(f"[XYZ] Variant child returned {child_resp.status_code}: {best_variant_url}", xbmc.LOGWARNING)
            return body
        child_body = child_resp.text
        child_body = child_body.replace("\x00", "")
        if not child_body or "#EXTM3U" not in child_body:
            return body
        child_body = child_body.replace(".png", ".ts").replace(".image", ".ts")
        if _is_variant_playlist(child_body):
            child_body = _resolve_variant_to_media(child_body, best_variant_url, session, headers, depth + 1)
        if "#EXTINF" in child_body:
            return child_body
    except Exception as e:
        debug_log(f"[XYZ] Variant child fetch failed: {e}", xbmc.LOGWARNING)
    return body


def _extract_clearkey(stream_url: str, headers: dict, timeout: float) -> Optional[str]:
    """Fetch the HLS manifest and return an InputStream Adaptive ClearKey license_key.

    Extracts ck= from the stream URL query parameters or from the manifest body.
    """
    debug_log(f"[XYZ] _extract_clearkey called with URL: {stream_url[:200]}...", xbmc.LOGDEBUG)
    try:
        parsed = urlparse(stream_url)
        qs = parse_qs(parsed.query)
        ck_param = qs.get("ck", [])
        debug_log(f"[XYZ] Query string ck param: {ck_param}", xbmc.LOGDEBUG)
        if ck_param:
            ck_value = ck_param[0]
            m = re.match(r"^([a-f0-9]+)[:%3A]([a-f0-9]+)$", ck_value, re.IGNORECASE)
            if m:
                kid_hex, key_hex = m.group(1), m.group(2)
                kid_b64 = _hex_to_base64url(kid_hex)
                key_b64 = _hex_to_base64url(key_hex)
                debug_log(f"[XYZ] Extracted ClearKey from URL query: kid={kid_hex[:8]}..., key={key_hex[:8]}...", xbmc.LOGINFO)
                return f"{kid_b64}:{key_b64}"
            else:
                debug_log(f"[XYZ] ck= value format mismatch: {ck_value[:50]}", xbmc.LOGWARNING)

        ssl_verify = "247.xyzstreams.st" not in stream_url and "247v2.dlhd.net" not in stream_url
        resp = get_session().get(stream_url, headers=headers, timeout=timeout, verify=ssl_verify)
        if resp.status_code != 200:
            return None
        text = resp.text

        m = re.search(r"ck=([a-f0-9]+)(?:%3A|:)([a-f0-9]+)", text, re.IGNORECASE)
        if m:
            kid_hex, key_hex = m.group(1), m.group(2)
            kid_b64 = _hex_to_base64url(kid_hex)
            key_b64 = _hex_to_base64url(key_hex)
            debug_log(f"[XYZ] Extracted ClearKey from manifest body: kid={kid_hex[:8]}..., key={key_hex[:8]}...", xbmc.LOGINFO)
            return f"{kid_b64}:{key_b64}"

        debug_log("[XYZ] No ClearKey found in URL query or manifest body", xbmc.LOGDEBUG)
    except Exception as e:
        debug_log(f"[XYZ] ClearKey extraction failed: {e}", xbmc.LOGDEBUG)
    return None


class _XYZProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def handle(self):
        with _XYZ_PROXY["client_sockets_lock"]:
            _XYZ_PROXY["client_sockets"].add(self.connection)
        client_id = id(self.connection) & 0xFFFF
        debug_log(f"[XYZ] Connection {client_id} opened (total={len(_XYZ_PROXY['client_sockets'])})", xbmc.LOGDEBUG)
        try:
            self.connection.settimeout(10)
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError,
                OSError, ValueError) as e:
            debug_log(f"[XYZ] Connection {client_id} error: {type(e).__name__}", xbmc.LOGDEBUG)
        finally:
            with _XYZ_PROXY["client_sockets_lock"]:
                _XYZ_PROXY["client_sockets"].discard(self.connection)
            debug_log(f"[XYZ] Connection {client_id} closed (remaining={len(_XYZ_PROXY['client_sockets'])})", xbmc.LOGDEBUG)

    def do_GET(self):
        self._handle(head_only=False)

    def do_HEAD(self):
        self._handle(head_only=True)

    def _handle(self, head_only: bool):
        _reset_xyz_idle_timer()
        if _XYZ_PROXY["abort"].is_set():
            self._fail(503, b"Proxy shutting down")
            return
        raw_path_for_token = self.path.split("?")[0].lstrip("/")
        upstream_map = _XYZ_PROXY["upstream"]
        debug_log(f"[XYZ] Proxy {'HEAD' if head_only else 'GET'} {self.path}", xbmc.LOGINFO)

        if raw_path_for_token.startswith("xyz/") and raw_path_for_token.endswith(".m3u8"):
            self._serve_manifest(head_only=head_only)
        elif raw_path_for_token.startswith("xyz/seg/"):
            self._serve_segment(head_only=head_only)
        else:
            self._fail(404, b"Not found")

    def _serve_manifest(self, head_only: bool):
        raw_path = self.path.split("?")[0].lstrip("/")
        token = raw_path[len("xyz/"):-len(".m3u8")]
        entry = _XYZ_PROXY["upstream"].get(token)
        if not entry:
            self._fail(404, b"Token not found")
            return

        cached = entry.get("cache")
        if head_only:
            if cached:
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                self.send_header("Content-Length", str(len(cached)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Connection", "close")
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Connection", "close")
                self.end_headers()
            debug_log(f"[XYZ] HEAD manifest ({'cached' if cached else 'empty'})", xbmc.LOGINFO)
            return

        now = time.time()
        cache_time = entry.get("cache_time", 0.0)
        cache_age = now - cache_time if cache_time > 0 else float('inf')
        upstream_url = entry["url"]
        headers = entry.get("headers") or {}
        port = _XYZ_PROXY["port"]
        is_live_247 = "247" in upstream_url

        if cached and (is_live_247 or cache_age < 0.5):
            data = cached
            debug_log(f"[XYZ] Serving cached m3u8 ({len(data)} bytes, age={cache_age:.1f}s)", xbmc.LOGINFO)
        elif cached:
            data = cached
            debug_log(f"[XYZ] Serving stale cached m3u8 ({len(data)} bytes, age={cache_age:.1f}s), refreshing background", xbmc.LOGINFO)
            def _refresh():
                try:
                    self._refresh_cache(entry, token)
                except Exception as e:
                    debug_log(f"[XYZ] Background refresh failed: {e}", xbmc.LOGWARNING)
            t = threading.Thread(target=_refresh, name="XYZRefresh")
            t.daemon = True
            t.start()
        else:
            data = self._fetch_manifest(entry, token, upstream_url, headers, port)
            if data is None:
                return

        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(data)
            debug_log(f"[XYZ] Sent m3u8 response ({len(data)} bytes)", xbmc.LOGINFO)
        except (ConnectionAbortedError, BrokenPipeError) as e:
            debug_log(f"[XYZ] client disconnected during manifest write: {e}", xbmc.LOGDEBUG)

    def _fetch_manifest(self, entry, token, upstream_url, headers, port):
        debug_log(f"[XYZ] Proxy fetching upstream m3u8: {upstream_url}", xbmc.LOGINFO)
        now = time.time()
        try:
            req_headers = dict(_DEFAULT_HEADERS)
            req_headers.update(headers)
            session = entry.get("session") or requests.Session()
            ssl_verify = "247.xyzstreams.st" not in upstream_url and "247v2.dlhd.net" not in upstream_url
            resp = session.get(
                upstream_url, timeout=(5, 15), headers=req_headers, verify=ssl_verify
            )
            debug_log(f"[XYZ] Upstream response: {resp.status_code} (final URL: {resp.url})", xbmc.LOGINFO)
            if resp.status_code != 200:
                debug_log(f"[XYZ] Upstream error {resp.status_code}: {resp.text[:200]}", xbmc.LOGWARNING)
                self._fail(502, f"Upstream {resp.status_code}".encode())
                return None

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
                return None

            body = body.replace(".png", ".ts").replace(".image", ".ts")

            decoded_url = unquote(final_url)
            is_video_only = "/widevine/video/" in decoded_url.lower()

            if is_video_only:
                debug_log("[XYZ] Detected video-only manifest URL, attempting to find audio companion", xbmc.LOGINFO)
                audio_decoded = decoded_url.replace("/widevine/video/", "/widevine/audio/")
                debug_log(f"[XYZ] Audio manifest URL: {audio_decoded[:200]}...", xbmc.LOGDEBUG)

                try:
                    debug_log("[XYZ] Fetching audio manifest...", xbmc.LOGDEBUG)
                    ssl_verify = "247.xyzstreams.st" not in audio_decoded and "247v2.dlhd.net" not in audio_decoded
                    audio_resp = session.get(audio_decoded, headers=req_headers, timeout=(5, 15), verify=ssl_verify)
                    debug_log(f"[XYZ] Audio manifest response status: {audio_resp.status_code}", xbmc.LOGINFO)
                    if audio_resp.status_code == 200:
                        audio_text = audio_resp.text.replace("\x00", "")
                        debug_log(f"[XYZ] Audio manifest body length: {len(audio_text)}, has EXTM3U: {'#EXTM3U' in audio_text}, has EXTINF: {'#EXTINF' in audio_text}", xbmc.LOGDEBUG)
                        if "#EXTM3U" in audio_text and "#EXTINF" in audio_text:
                            debug_log(f"[XYZ] Found audio companion manifest ({len(audio_text)} bytes)", xbmc.LOGINFO)
                            audio_token = uuid.uuid4().hex
                            audio_port = _XYZ_PROXY["port"]
                            _XYZ_PROXY["upstream"][audio_token] = {
                                "url": audio_decoded,
                                "headers": dict(req_headers),
                                "cache": None,
                                "cache_time": time.time(),
                                "session": session,
                                "license_key": entry.get("license_key"),
                            }
                            audio_proxy_url = f"http://127.0.0.1:{audio_port}/xyz/{audio_token}.m3u8"

                            ext_media = f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Audio",DEFAULT=YES,AUTOSELECT=YES,URI="{audio_proxy_url}"'
                            body = body.replace("#EXT-X-VERSION:", f"#EXT-X-VERSION:\n{ext_media}", 1)
                            debug_log(f"[XYZ] Injected audio MEDIA tag: {audio_proxy_url}", xbmc.LOGINFO)
                        else:
                            debug_log("[XYZ] Audio manifest response was not valid HLS", xbmc.LOGWARNING)
                    else:
                        debug_log(f"[XYZ] Audio manifest returned status {audio_resp.status_code}: {audio_resp.text[:200]}", xbmc.LOGWARNING)
                except Exception as e:
                    debug_log(f"[XYZ] Failed to fetch audio manifest: {type(e).__name__}: {e}", xbmc.LOGERROR)
            else:
                debug_log(f"[XYZ] Not detected as video-only (decoded URL: {decoded_url[:150]}...)", xbmc.LOGDEBUG)

            if "#EXT-X-KEY:METHOD=NONE" in body:
                debug_log("[XYZ] Manifest has METHOD=NONE (segments may still be encrypted)", xbmc.LOGDEBUG)

            debug_log(f"[XYZ] Original m3u8 first 1000 chars:\n{body[:1000]}", xbmc.LOGINFO)

            if _is_variant_playlist(body):
                body = _best_quality_master(body)

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
            return data
        except Exception as e:
            debug_log(f"[XYZ] manifest rebuild failed: {e}", xbmc.LOGWARNING)
            self._fail(502, b"Upstream error")
            return None

    def _refresh_cache(self, entry, token):
        if _XYZ_PROXY["abort"].is_set():
            return
        debug_log(f"[XYZ] Background refresh starting for {token[:8]}...", xbmc.LOGINFO)
        upstream_url = entry["url"]
        headers = entry.get("headers") or {}
        port = _XYZ_PROXY["port"]

        try:
            req_headers = dict(_DEFAULT_HEADERS)
            req_headers.update(headers)
            session = entry.get("session") or requests.Session()
            ssl_verify = "247.xyzstreams.st" not in upstream_url and "247v2.dlhd.net" not in upstream_url
            resp = session.get(upstream_url, timeout=(5, 15), headers=req_headers, verify=ssl_verify)
            if resp.status_code != 200:
                debug_log(f"[XYZ] Background refresh upstream error {resp.status_code}", xbmc.LOGWARNING)
                resp.close()
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
            body = raw_bytes.decode("utf-8", errors="replace").replace("\x00", "")
            if not body or "#EXTM3U" not in body:
                return
            body = body.replace(".png", ".ts").replace(".image", ".ts")
            if _is_variant_playlist(body):
                body = _best_quality_master(body)
            rewritten_body = _rewrite_m3u8_body(body, token, port, base_url=final_url)
            data = rewritten_body.encode("utf-8")
            if not _XYZ_PROXY["abort"].is_set():
                entry["cache"] = data
                entry["cache_time"] = time.time()
                debug_log(f"[XYZ] Background refresh completed: {len(data)} bytes", xbmc.LOGINFO)
        except Exception as e:
            debug_log(f"[XYZ] Background refresh failed: {e}", xbmc.LOGWARNING)

    def _serve_segment(self, head_only: bool):
        if _XYZ_PROXY["abort"].is_set():
            self._fail(503, b"Proxy shutting down")
            return
        full_path = self.path.split("?")[0].lstrip("/")
        token_and_rest = full_path[len("xyz/seg/"):]
        if "/" in token_and_rest:
            token, seg_path = token_and_rest.split("/", 1)
            seg_path = unquote(seg_path)
        else:
            token, seg_path = token_and_rest, ""
        entry = _XYZ_PROXY["upstream"].get(token)
        if not entry or not seg_path:
            debug_log(f"[XYZ] Segment token/path not found: {token}/{seg_path}", xbmc.LOGWARNING)
            self._fail(404, b"Token/segment not found")
            return

        if head_only:
            self.send_response(200)
            self.send_header("Content-Type", "video/mp2t")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Connection", "close")
            self.end_headers()
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
                if ".png" in target:
                    image_target = target.replace(".png", ".image")
                    if image_target != target:
                        debug_log(f"[XYZ] Segment fetch failed ({upstream_resp.status_code}), retrying with .image extension: {image_target[:120]}", xbmc.LOGDEBUG)
                        upstream_resp.close()
                        upstream_resp = session.get(
                            image_target, headers=seg_headers, timeout=(5, 30), stream=True, allow_redirects=True
                        )
                        upstream_content_type = upstream_resp.headers.get("Content-Type", "")
                        debug_log(f"[XYZ] Segment retry (.image) status: {upstream_resp.status_code}, Content-Type: {upstream_content_type}", xbmc.LOGINFO)
                        target = image_target
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

            if target.lower().endswith(".png") or target.lower().endswith(".image"):
                content_type = "video/mp2t"

            segment_data = b""
            try:
                for chunk in upstream_resp.iter_content(chunk_size=64 * 1024):
                    if _XYZ_PROXY["abort"].is_set():
                        break
                    if chunk:
                        segment_data += chunk
                        if len(segment_data) > 32 * 1024 * 1024:
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
            segment_data = _strip_riff_wrapper(segment_data)
            if len(segment_data) != original_len:
                debug_log(f"[XYZ] Stripped wrapper: {original_len} -> {len(segment_data)} bytes", xbmc.LOGINFO)

                if len(segment_data) >= 16:
                    prefix = " ".join(f"{b:02x}" for b in segment_data[:16])
                    debug_log(f"[XYZ] Segment first bytes after strip: {prefix}", xbmc.LOGINFO)

                    if segment_data[0] != 0x47:
                        debug_log(f"[XYZ] WARNING: First byte after strip is 0x{segment_data[0]:02x}, expected 0x47 (TS sync)", xbmc.LOGWARNING)
            else:
                if len(segment_data) >= 1 and segment_data[0] != 0x47:
                    prefix = " ".join(f"{b:02x}" for b in segment_data[:16])
                    debug_log(f"[XYZ] WARNING: Segment starts with 0x{segment_data[0]:02x} (not TS sync 0x47), bytes: {prefix}", xbmc.LOGWARNING)

            is_m3u8 = "mpegurl" in content_type.lower() or segment_data.startswith(b"#EXTM3U")
            if is_m3u8:
                try:
                    manifest_body = segment_data.decode("utf-8", errors="replace")
                    manifest_body = manifest_body.replace("\x00", "")
                    manifest_body = manifest_body.replace(".png", ".ts").replace(".image", ".ts")

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
            self.send_header("Connection", "close")
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
                self.send_header("Connection", "close")
                self.end_headers()
            except Exception:
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
            debug_log(f"[XYZ] _fail write error: {e}", xbmc.LOGDEBUG)


def _ensure_xyz_proxy() -> int:
    with _XYZ_PROXY["lock"]:
        if _XYZ_PROXY["server"] is not None:
            _reset_xyz_idle_timer_locked()
            return _XYZ_PROXY["port"]
        _XYZ_PROXY["abort"].clear()
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
        _reset_xyz_idle_timer_locked()
        return port


def _shutdown_xyz_proxy():
    debug_log("[XYZ] _shutdown_xyz_proxy called", xbmc.LOGINFO)
    with _XYZ_PROXY["lock"]:
        _XYZ_PROXY["abort"].set()
        old_timer = _XYZ_PROXY.get("idle_timer")
        if old_timer:
            old_timer.cancel()
            _XYZ_PROXY["idle_timer"] = None
        with _XYZ_PROXY["client_sockets_lock"]:
            sockets = list(_XYZ_PROXY["client_sockets"])
            _XYZ_PROXY["client_sockets"].clear()
        for s in sockets:
            try:
                s.close()
            except Exception:
                pass
        if _XYZ_PROXY["server"]:
            _XYZ_PROXY["server"].shutdown()
            _XYZ_PROXY["server"].server_close()
            _XYZ_PROXY["server"] = None
            _XYZ_PROXY["thread"] = None
            _XYZ_PROXY["port"] = None
            _XYZ_PROXY["upstream"].clear()
