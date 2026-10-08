# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Localhost HTTP proxy for tricky streams (MoQ/WebSocket -> FLV transmux
    plus generic m3u8 pass-through), owned by the resolvers that need it.
'''

import base64
import collections
import errno
import http.server
import json
import os
import queue
import re
import socketserver
import threading
import time
import urllib.parse
import urllib.error
import urllib.request

try:
    import xbmc
    import xbmcaddon
except ImportError:
    xbmc = None
    xbmcaddon = None

try:
    import websocket  # script.module.websocket / websocket-client
except ImportError:
    websocket = None

DEFAULT_PORT = 50199
DEFAULT_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
)

ADDON_ID = 'script.module.resolveurl.pluginsgr'

# Engine manifest dir (ytresolver TEMP_PATH = 'special://temp/' + ADDON_ID).
# Both interpreters see the same filesystem, unlike module globals.
_YT_ENGINE_TEMP = 'special://temp/plugin.video.youtube'


def _yt_mpd_path(video_id):
    '''Filesystem path of the engine-written manifest, or None.

    Lazy imports: moq_proxy must stay light for resolvers that never
    touch YouTube (mega/vindral import this module too).
    '''
    try:
        from ytresolver.kodion.constants import TEMP_PATH as _engine_temp
        base = _engine_temp
    except Exception:
        base = _YT_ENGINE_TEMP
    try:
        import xbmcvfs
        translated = xbmcvfs.translatePath(base)
        if translated:
            base = translated
    except Exception:
        pass
    if base.startswith('special://'):
        return None
    return os.path.join(base, video_id + '.mpd')


g_proxy_server = None
g_proxy_thread = None
g_stream_manager = None
g_external_port = None
g_yt_mpds = {}
_YT_MPD_MAX = 50
g_failed_hosts = {}
_FAILED_HOST_TTL = 300.0
_YT_ORIGIN_RE = re.compile(r'https?://[^/"\'\s]+(/youtube/(?:stream|manifest)[^"\'\s]*)')
_shutdown = threading.Event()
_lock = threading.Lock()


def _log(msg, level=None):
    try:
        if xbmc is not None:
            xbmc.log(f'PluginsGR Proxy: {msg}', level if level is not None else xbmc.LOGDEBUG)
            return
    except Exception:
        pass
    # Fallback outside Kodi (tests); keep quiet unless it looks like an error.
    if isinstance(msg, str) and msg.lower().startswith(('error', 'timeout')):
        print(f'PluginsGR Proxy: {msg}')


def _get_ua():
    try:
        from resolveurl import common
        ua = getattr(common, 'RAND_UA', None)
        if ua:
            return ua
    except Exception:
        pass
    return DEFAULT_UA


def get_proxy_port(default=DEFAULT_PORT):
    '''Resolve the proxy port from the PluginsGR setting, falling back to default.'''
    if xbmcaddon is not None:
        try:
            value = xbmcaddon.Addon(ADDON_ID).getSetting('proxy_port')
            if value not in (None, ''):
                return int(value)
        except Exception:
            pass
    return default


class StreamManager:

    def __init__(self, ws_url, origin=None):

        self.ws_url = ws_url
        self.origin = origin
        self.ws = None
        self.audio_ids = set()
        self.video_ids = set()

        self.video_init_tag = None
        self.audio_init_tag = None
        self.media_buffer = collections.deque(maxlen=150)
        self.clients = []
        self.stop_event = threading.Event()
        self.init_ready = threading.Event()
        self.first_ts = None

        self.last_active_time = time.time()

        self.thread = threading.Thread(target=self._ws_reader, daemon=True)
        self.ping_thread = None
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass

    def write_flv_tag(self, tag_type, timestamp_ms, payload):
        """Wraps raw payload into a standard FLV Tag."""
        tag = bytearray()
        tag.append(tag_type)
        tag.extend(len(payload).to_bytes(3, 'big'))
        tag.extend((timestamp_ms & 0xFFFFFF).to_bytes(3, 'big'))
        tag.append((timestamp_ms >> 24) & 0xFF)
        tag.extend(b'\x00\x00\x00')  # StreamID
        tag.extend(payload)
        tag.extend((11 + len(payload)).to_bytes(4, 'big'))  # PreviousTagSize
        return tag

    def _pinger(self):

        while not self.stop_event.is_set():
            if self.stop_event.wait(5.0):
                break
            try:
                if self.ws and getattr(self.ws, 'connected', True):
                    self.ws.send(json.dumps({"type": "ping"}))
            except Exception:
                break

    def _ws_reader(self):
        _log(f'Connecting MoQ WSS... {self.ws_url}')
        if websocket is None:
            _log('websocket module not available, cannot proxy MoQ stream')
            self.init_ready.set()
            return

        headers = {
            'User-Agent': _get_ua(),
            'Origin': self.origin
        }

        try:

            self.ws = websocket.create_connection(self.ws_url, header=headers, timeout=15)
            _log('MoQ connected. Awaiting handshakes...')

            self.ping_thread = threading.Thread(target=self._pinger, daemon=True)
            self.ping_thread.start()

            while not self.stop_event.is_set():

                if len(self.clients) > 0:
                    self.last_active_time = time.time()
                elif time.time() - self.last_active_time > 10.0:
                    _log('No clients active for 10s. Auto-closing stream.')
                    self.stop()
                    break
                # -----------------------

                msg = self.ws.recv()
                if not msg:
                    continue

                # 1. Parse JSON Control Plane
                if isinstance(msg, str):
                    try:
                        data = json.loads(msg)
                        msg_type = data.get('type')

                        if msg_type in ('ping', 'pong'):
                            continue

                        if msg_type == 'renditions':
                            for r in data.get('renditions', []):
                                codec = r.get('codec', '')
                                if codec in ('aac', 'mp3', 'opus'):
                                    self.audio_ids.add(r['id'])
                                elif codec in ('h264', 'h265', 'av1'):
                                    self.video_ids.add(r['id'])
                            _log(f'Mapped Video IDs {self.video_ids}, Audio IDs {self.audio_ids}')
                    except Exception:
                        pass
                    continue

                # 2. Parse Binary Media Plane (MoQ)
                elif isinstance(msg, bytes):
                    if len(msg) < 17:
                        continue

                    offset = int.from_bytes(msg[1:3], 'big')
                    flags = msg[3]
                    rend_id = msg[4]
                    timestamp = int.from_bytes(msg[5:13], 'big')
                    timescale = int.from_bytes(msg[13:17], 'big')
                    if timescale == 0:
                        timescale = 1000

                    if self.first_ts is None:
                        self.first_ts = timestamp
                    ts_ms = max(0, int((timestamp - self.first_ts) * 1000 / timescale))

                    comp_time = 0
                    if flags & 16 and len(msg) >= 19:
                        comp_time = int.from_bytes(msg[17:19], 'big', signed=True)
                    comp_time_ms = int(comp_time * 1000 / timescale)

                    payload = msg[offset:]
                    is_init = bool(flags & 2)
                    is_sync = bool(flags & 1)

                    tag = None

                    # 3A. Trans-mux H.264 to FLV Video Tag
                    if rend_id in self.video_ids:
                        payload_wrap = bytearray()
                        if is_init:
                            payload_wrap.extend(b'\x17\x00\x00\x00\x00')
                        else:
                            payload_wrap.append(0x17 if is_sync else 0x27)
                            payload_wrap.append(0x01)
                            payload_wrap.extend((comp_time_ms & 0xFFFFFF).to_bytes(3, 'big'))

                        payload_wrap.extend(payload)
                        tag = self.write_flv_tag(9, ts_ms, payload_wrap)

                        if is_init:
                            if not self.video_init_tag:
                                _log('Captured H.264 INIT.')
                            self.video_init_tag = tag

                    # 3B. Trans-mux AAC to FLV Audio Tag
                    elif rend_id in self.audio_ids:
                        payload_wrap = bytearray()
                        payload_wrap.append(0xAF)
                        payload_wrap.append(0x00 if is_init else 0x01)
                        payload_wrap.extend(payload)
                        tag = self.write_flv_tag(8, ts_ms, payload_wrap)

                        if is_init:
                            if not self.audio_init_tag:
                                _log('Captured AAC INIT.')
                            self.audio_init_tag = tag

                    # 4. Broadcast Tag to clients
                    if tag:
                        if is_init:
                            if self.video_init_tag:
                                self.init_ready.set()
                        else:
                            self.media_buffer.append(tag)
                            for client_q in list(self.clients):
                                try:
                                    client_q.put_nowait(tag)
                                except queue.Full:
                                    pass

        except Exception as e:
            if not self.stop_event.is_set():
                _log(f'WSS Loop Error: {e}')
        finally:
            self.init_ready.set()
            _log('WSS Background Thread Closed')


class ProxyRequestHandler(http.server.BaseHTTPRequestHandler):

    def do_HEAD(self):

        path = urllib.parse.urlparse(self.path).path
        if path.endswith('.mpd'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/dash+xml')
            self.end_headers()
            return

        if '.m3u8' in self.path:
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
            self.end_headers()
            return

        self.send_response(200)
        self.send_header('Content-Type', 'video/x-flv')
        self.end_headers()

    def _serve_yt_mpd(self, video_id):
        # Module state is per-interpreter: the store below only hits when
        # serving in the same invoker that stored. The file fallback is the
        # cross-interpreter path (service serves what the router resolved).
        with _lock:
            xml = g_yt_mpds.get(video_id)
        if not xml:
            path = _yt_mpd_path(video_id)
            if path:
                try:
                    with open(path, 'rb') as f:
                        xml = f.read()
                except OSError:
                    xml = None
        if not xml:
            self.send_error(404, 'Unknown MPD')
            return
        try:
            port = self.server.server_address[1]
            text = xml.decode('utf-8')
            text = _YT_ORIGIN_RE.sub(
                lambda m: 'http://127.0.0.1:{0}{1}'.format(port, m.group(1)), text)
            body = text.encode('utf-8')
        except Exception:
            self.send_error(500, 'MPD rewrite failed')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/dash+xml')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _relay_yt_stream(self, query):
        # Split manually: parse_qs would corrupt base64 '+' in __headers,
        # and raw pairs are forwarded to googlevideo untouched.
        headers_b64 = ''
        hosts = []
        path = '/videoplayback'
        method = 'POST'
        keep = []
        for part in (query or '').split('&'):
            if not part or '=' not in part:
                continue
            raw_key, raw_value = part.split('=', 1)
            key = urllib.parse.unquote(raw_key)
            if key == '__headers':
                headers_b64 = urllib.parse.unquote(raw_value)
            elif key == '__host':
                hosts.append(urllib.parse.unquote(raw_value))
            elif key == '__path':
                path = urllib.parse.unquote(raw_value) or path
            elif key == '__method':
                method = (urllib.parse.unquote(raw_value) or method).upper()
            elif key == '__id':
                continue
            elif key.startswith('__'):
                continue
            else:
                keep.append(part)

        try:
            headers = json.loads(base64.b64decode(headers_b64).decode('utf-8')) if headers_b64 else {}
        except Exception:
            headers = {}
        if not isinstance(headers, dict):
            headers = {}

        if 'Range' in self.headers:
            headers['Range'] = self.headers['Range']

        if not hosts:
            self.send_error(400, 'No upstream host')
            return

        now = time.time()
        with _lock:
            expired = [h for h, ts in g_failed_hosts.items() if now - ts >= _FAILED_HOST_TTL]
            for h in expired:
                del g_failed_hosts[h]
            alive = [h for h in hosts if h not in g_failed_hosts]
            failed = [h for h in hosts if h in g_failed_hosts]
        ordered_hosts = alive + failed

        upstream_qs = '&'.join(keep)
        body = None
        resp_headers = {}
        for idx, host in enumerate(ordered_hosts):
            if _shutdown.is_set():
                return
            is_last = (idx == len(ordered_hosts) - 1)
            fetch_timeout = 20 if is_last else 5
            url = 'https://{0}{1}'.format(host, path)
            if upstream_qs:
                url += '?' + upstream_qs
            try:
                try:
                    body, resp_headers = _fetch_upstream(url, headers, method, timeout=fetch_timeout)
                except TypeError:
                    body, resp_headers = _fetch_upstream(url, headers, method)
                with _lock:
                    g_failed_hosts.pop(host, None)
                break
            except Exception as e:
                with _lock:
                    g_failed_hosts[host] = time.time()
                _log(f'YT relay host {host} failed: {e}')

        if body is None:
            self.send_error(502, 'Upstream fetch failed')
            return

        lowered = {k.lower(): v for k, v in resp_headers.items()}
        content_range = lowered.get('content-range')
        self.send_response(206 if content_range else 200)
        self.send_header('Content-Type', lowered.get('content-type', 'video/mp4'))
        if content_range:
            self.send_header('Content-Range', content_range)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):

        global g_stream_manager

        if _shutdown.is_set():
            self.send_error(503, 'Proxy is shutting down')
            return

        parsed = urllib.parse.urlparse(self.path)

        mpd_match = re.match(r'/yt/([\w-]{11})\.mpd$', parsed.path)
        if mpd_match:
            self._serve_yt_mpd(mpd_match.group(1))
            return

        if parsed.path.startswith('/youtube/stream'):
            self._relay_yt_stream(parsed.query)
            return

        if '.m3u8' in self.path:
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                vid_b64 = query['stream'][0]
                vid_url_with_headers = base64.urlsafe_b64decode(vid_b64).decode('utf-8')

                # Parse URL and headers
                parts = vid_url_with_headers.split('|', 1)
                url = parts[0]
                headers = {'User-Agent': _get_ua()}
                if len(parts) > 1 and parts[1]:
                    header_pairs = parts[1].split('&')
                    for pair in header_pairs:
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            headers[key] = urllib.parse.unquote(value)

                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    content = response.read()

                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            except Exception as e:

                _log(f'M3U8 proxy error: {e}')
                self.send_error(500, f"M3U8 proxy error: {e}")

            return

        elif '?ws=' in self.path:
            try:
                parsed = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed.query)
                ws_b64 = qs['ws'][0]
                ws_url = base64.urlsafe_b64decode(ws_b64).decode('utf-8')
                origin = qs.get('origin', [None])[0]

                if not g_stream_manager or g_stream_manager.ws_url != ws_url or g_stream_manager.stop_event.is_set():
                    if g_stream_manager:
                        g_stream_manager.stop()
                    _log('Booting Stream Manager...')
                    g_stream_manager = StreamManager(ws_url, origin)
            except Exception as e:
                self.send_error(400, f"Invalid WSS parameter: {e}")
                return

        manager = g_stream_manager
        if manager is None:
            self.send_error(404, "Stream not initialized")
            return

        # Satisfy ResolveURL Probe
        self.send_response(200)
        self.send_header('Content-Type', 'video/x-flv')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Bounded wait for the first media (exit promptly on Kodi abort/shutdown).
        deadline = time.time() + 15.0
        while not manager.init_ready.is_set():
            if _shutdown.is_set():
                return
            if time.time() >= deadline:
                _log('Timeout waiting for MoQ Media.')
                return
            manager.init_ready.wait(0.25)

        try:
            # 1. Write the mandatory FLV File Header
            self.wfile.write(b'FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00')

            # 2. Write the cached Video/Audio Sequence Headers
            if manager.video_init_tag:
                self.wfile.write(manager.video_init_tag)
            if manager.audio_init_tag:
                self.wfile.write(manager.audio_init_tag)

            # 3. Write rolling buffer
            for tag in list(manager.media_buffer):
                self.wfile.write(tag)
        except (ConnectionResetError, BrokenPipeError):
            _log('Probe check finished.')
            return
        except Exception:
            return

        client_q = queue.Queue(maxsize=300)
        manager.clients.append(client_q)
        _log('FLV muxing live to player...')

        # Same 15s idle-client semantics as before, but sliced so shutdown
        # is honoured within a fraction of a second instead of up to 15s.
        idle_deadline = time.time() + 15.0
        try:
            while not _shutdown.is_set():
                try:
                    tag = client_q.get(timeout=0.25)
                except queue.Empty:
                    if time.time() >= idle_deadline:
                        break
                    continue
                idle_deadline = time.time() + 15.0
                self.wfile.write(tag)
        except Exception:
            pass
        finally:
            if manager and client_q in manager.clients:
                manager.clients.remove(client_q)

    def log_message(self, format, *args):
        return


class ThreadedHttpServer(socketserver.ThreadingMixIn, http.server.HTTPServer):

    allow_reuse_address = True
    daemon_threads = True


def _probe_existing(port):
    '''HEAD-probe 127.0.0.1:port; True only if it answers like our FLV proxy.'''
    try:
        req = urllib.request.Request(f'http://127.0.0.1:{port}/', method='HEAD')
        try:
            resp = urllib.request.urlopen(req, timeout=1.0)
        except urllib.error.HTTPError as e:
            # A live HTTP server, just not ours (e.g. 404/501).
            try:
                e.close()
            except Exception:
                pass
            return False
        try:
            return resp.status == 200 and resp.headers.get_content_type() == 'video/x-flv'
        finally:
            try:
                resp.close()
            except Exception:
                pass
    except Exception:
        return False


def start_server(port=None):
    '''Idempotent proxy startup. Returns the bound port, or None on failure.

    Cross-interpreter note: the xbmc.service entry (run_service) binds the
    configured port at login in its own invoker. Resolvers run in a *different*
    invoker (plugin router) with separate module state, so their bind attempt
    hits EADDRINUSE. That path returns the configured port *without creating
    any threads* in the router invoker, which is what keeps Kodi exits clean.
    '''

    global g_proxy_server, g_proxy_thread, g_external_port

    with _lock:
        if g_proxy_server:
            try:
                return g_proxy_server.server_address[1]
            except Exception:
                pass
        if g_external_port is not None:
            return g_external_port

        bind_port = get_proxy_port() if port is None else port

        try:
            server = ThreadedHttpServer(('', bind_port), ProxyRequestHandler)
        except OSError as e:
            if getattr(e, 'errno', None) == errno.EADDRINUSE:
                owned_port = get_proxy_port() if not bind_port else bind_port
                if _probe_existing(owned_port):
                    _log(f'Port {owned_port} is already served by the running proxy (owned by the service)')
                    g_external_port = owned_port
                    return owned_port
                _log(f'Port {bind_port} is in use by another process', xbmc.LOGWARNING if xbmc is not None else None)
                return None
            _log(f'Failed to start proxy on port {bind_port}: {e}')
            return None
        except Exception as e:
            _log(f'Failed to start proxy on port {bind_port}: {e}')
            return None

        _shutdown.clear()
        g_proxy_server = server
        actual_port = server.server_address[1]
        g_proxy_thread = threading.Thread(
            target=server.serve_forever, kwargs={'poll_interval': 0.25},
            daemon=True, name='PluginsGRProxyServe'
        )
        g_proxy_thread.start()

        _log(f'Listening on {actual_port}')
        return actual_port


def stop_server():

    global g_proxy_server, g_proxy_thread, g_stream_manager, g_external_port, g_yt_mpds, g_failed_hosts

    _shutdown.set()

    with _lock:
        manager, g_stream_manager = g_stream_manager, None
        server, g_proxy_server = g_proxy_server, None
        thread, g_proxy_thread = g_proxy_thread, None
        g_external_port = None
        g_yt_mpds = {}
        g_failed_hosts = {}

    if manager is not None:
        try:
            manager.stop()
        except Exception:
            pass
        try:
            if manager.thread is not None:
                manager.thread.join(timeout=3.0)
        except Exception:
            pass
        try:
            if manager.ping_thread is not None:
                manager.ping_thread.join(timeout=3.0)
        except Exception:
            pass

    if server is not None:
        try:
            server.shutdown()
        except Exception:
            pass
        try:
            server.server_close()
        except Exception:
            pass

    # Bounded join: daemon handler threads are skipped by server_close()
    # (_Threads only tracks non-daemon) and self-terminate on _shutdown.
    if thread is not None:
        try:
            thread.join(timeout=3.0)
        except Exception:
            pass


def run_service():
    '''xbmc.service entry point. Owns the proxy for the whole session.

    Binds at login in the service invoker and tears everything down on
    abort, before the script ends, so no Python thread outlives us and
    Kodi can exit cleanly.
    '''

    monitor = xbmc.Monitor() if xbmc is not None and hasattr(xbmc, 'Monitor') else None

    start_server()

    if monitor is None:
        return

    try:
        while not monitor.abortRequested():
            if monitor.waitForAbort(1.0):
                break
    finally:
        _log('Service stopping proxy')
        stop_server()


def stop_stream():
    '''Stop the active MoQ stream without shutting down the HTTP server.'''
    global g_stream_manager

    with _lock:
        if g_stream_manager:
            g_stream_manager.stop()
            g_stream_manager = None


def _fetch_upstream(url, headers, method='GET', timeout=20):
    '''Fetch bytes via plain urllib. Returns (body_bytes, headers_dict).

    Kept as a module function so tests can monkeypatch it; HTTP errors
    propagate to the caller (host failover lives there).
    '''
    data = b'' if method == 'POST' else None
    req = urllib.request.Request(url, data=data, headers=dict(headers or {}), method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), dict(resp.headers)


def serve_yt_mpd(video_id, xml_bytes=None):
    '''Register an engine-generated DASH manifest for serving (prunes oldest
    beyond cap). Bytes are optional: when omitted, serving falls back to the
    engine-written file, which is what crosses interpreter boundaries.'''
    if xml_bytes is not None:
        if isinstance(xml_bytes, str):
            xml_bytes = xml_bytes.encode('utf-8')
        with _lock:
            g_yt_mpds.pop(video_id, None)
            g_yt_mpds[video_id] = xml_bytes or b''
            while len(g_yt_mpds) > _YT_MPD_MAX:
                g_yt_mpds.pop(next(iter(g_yt_mpds)))
    return build_yt_mpd_url(video_id)


def build_yt_mpd_url(video_id):
    bound_port = _bound_port(None)
    return f'http://127.0.0.1:{bound_port}/yt/{video_id}.mpd'


def _bound_port(port):
    bound = start_server(port=port)
    if bound is not None:
        return bound
    return get_proxy_port() if port is None else port


def build_ws_proxy_url(ws_url, origin=None, port=None, path='live.flv'):
    '''Ensure the proxy is running and return the localhost FLV URL for a MoQ ws URL.'''
    bound_port = _bound_port(port)
    ws_b64 = base64.urlsafe_b64encode(ws_url.encode('utf-8')).decode('utf-8')
    if origin:
        origin_q = urllib.parse.quote(origin, safe='')
        return f'http://127.0.0.1:{bound_port}/{path}?ws={ws_b64}&origin={origin_q}'
    return f'http://127.0.0.1:{bound_port}/{path}?ws={ws_b64}'


def build_m3u8_proxy_url(target_url, headers=None, port=None):
    '''Ensure the proxy is running and return the localhost m3u8 relay URL.'''
    bound_port = _bound_port(port)
    payload = target_url
    if headers:
        pairs = '&'.join(f'{k}={urllib.parse.quote(str(v), safe="")}' for k, v in headers.items())
        payload = f'{target_url}|{pairs}'
    stream_b64 = base64.urlsafe_b64encode(payload.encode('utf-8')).decode('utf-8')
    return f'http://127.0.0.1:{bound_port}/proxy.m3u8?stream={stream_b64}'


def build_yt_stream_url(url, port=None):
    '''Ensure the proxy is running and return the rewritten localhost YouTube stream relay URL.'''
    bound_port = _bound_port(port)
    return _YT_ORIGIN_RE.sub(
        lambda m: f'http://127.0.0.1:{bound_port}{m.group(1)}', url)

