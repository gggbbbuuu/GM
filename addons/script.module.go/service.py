# -*- coding: utf-8 -*-
"""Persistent, localhost-only Android 32-bit Go HTTP bridge bundled in script.module.go.

The xbmc.service entry point of this module loads the Go shared library ONCE,
then serves native.perform() calls from short-lived plug-in interpreters.
The v6 FullRaces extractor and HLS proxy are not modified.
"""
import base64
import http.server
import json
import os
import secrets
import sys
import tempfile
import threading
from urllib.parse import urlsplit

import xbmc
import xbmcaddon
import xbmcvfs

_ADDON_ID = 'script.module.go'
_MAX_REQUEST = 4 * 1024 * 1024
_MAX_REPLY = 20 * 1024 * 1024
_GO_LOCK = threading.RLock()
_REQUEST_COUNT = 0
_NATIVE_READY = False  # ARM32 native library is initialized by the first real Go request.


def _log(message, level=xbmc.LOGINFO):
    xbmc.log('[GoBridge] ' + str(message), level)


def _module():
    try:
        import goclient.native as native
    except ImportError:
        root = xbmcvfs.translatePath(xbmcaddon.Addon('script.module.go').getAddonInfo('path'))
        sys.path.insert(0, os.path.join(root, 'lib'))
        import goclient.native as native
    native._BRIDGE_SERVER = True  # Only this service interpreter loads the Go library
    return native


def _location():
    path = os.path.join(xbmcvfs.translatePath('special://masterprofile/'),
                        'addon_data', _ADDON_ID)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, 'bridge.json')


def _make_handler(native, token):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'

        def log_message(self, fmt, *args):
            # Avoid logging signed URLs, request body, cookies or access token.
            pass

        def _reply(self, status, data):
            encoded = json.dumps(data, separators=(',', ':')).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            global _REQUEST_COUNT, _NATIVE_READY
            if self.path != '/v1/perform' or self.headers.get('X-Go-Bridge-Token') != token:
                self._reply(403, {'error': 'access denied'})
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size <= 0 or size > _MAX_REQUEST:
                    self._reply(413, {'error': 'request too large'})
                    return
                data = json.loads(self.rfile.read(size).decode('utf-8'))
                url = data['url']
                split = urlsplit(url)
                if split.scheme not in ('https', 'http') or not split.hostname:
                    raise ValueError('Only absolute HTTP(S) URLs are accepted')
                body = base64.b64decode(data.get('body_base64', ''), validate=True)
                timeout = max(1, min(120, float(data.get('timeout', 25))))
                method = str(data.get('method', 'GET')).upper()
                if method not in ('GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'):
                    raise ValueError('Invalid HTTP method')
                with _GO_LOCK:
                    # Initialize native Go only when a client actually requests it.
                    # Doing so at Kodi startup can crash some 32-bit Android hosts.
                    # The existing lock ensures only one thread can initialize it.
                    if not _NATIVE_READY:
                        if not native.using_generic_native():
                            raise RuntimeError('Go bridge needs the generic GoRequest/GoFree library')
                        _NATIVE_READY = True
                        _log('Native Go initialized on first request; one library loaded')
                    result = native.perform(method, url, data.get('headers') or {}, body,
                                            data.get('profile') or 'chrome133',
                                            data.get('session') or '', timeout)
                    _REQUEST_COUNT += 1
                    if _REQUEST_COUNT == 1 or _REQUEST_COUNT % 10 == 0:
                        _log('Requests handled: {}'.format(_REQUEST_COUNT))
                response = {'status_code': result.get('status_code', 0),
                            'url': result.get('url') or url,
                            'headers': result.get('headers') or {},
                            'protocol': result.get('protocol') or '',
                            'error': result.get('error') or '',
                            'mitigated': result.get('mitigated') or '',
                            'body_base64': base64.b64encode(result.get('content') or b'').decode('ascii')}
                if len(json.dumps(response)) > _MAX_REPLY:
                    self._reply(413, {'error': 'response too large'})
                else:
                    self._reply(200, response)
            except (KeyError, TypeError, ValueError) as exc:
                self._reply(400, {'error': 'invalid request: ' + type(exc).__name__})
            except Exception as exc:
                _log('Go request error: {}: {}'.format(type(exc).__name__, str(exc)[:300]), xbmc.LOGERROR)
                self._reply(502, {'error': '{}: {}'.format(type(exc).__name__, str(exc)[:200])})

    return Handler


def _publish(location, port, token):
    parent = os.path.dirname(location)
    handle, staging = tempfile.mkstemp(prefix='.bridge-', dir=parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as output:
            json.dump({'port': port, 'token': token, 'schema': 1}, output)
        try:
            os.chmod(staging, 0o600)
        except OSError:
            pass
        os.replace(staging, location)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)


def run():
    # Kodi is authoritative for Android detection. platform.system() can
    # report something other than 'Linux' inside Kodi on Android, so
    # do not reject a device before checking Kodi's platform flag.
    try:
        if not xbmc.getCondVisibility('System.Platform.Android'):
            _log('Non-Android Kodi; built-in Go bridge inactive')
            return
    except (ImportError, AttributeError):
        return
    # Kodi launches registered services on every platform.  Do NOT keep a
    # service or load native Go on Android 64-bit.  On 32-bit Android only,
    # the service owns the library for the life of the Kodi process.
    # Import ctypes only on Android; Xbox UWP Python fails importing kernel32.
    import ctypes
    if ctypes.sizeof(ctypes.c_void_p) != 4:
        _log('Android 64-bit: bridge inactive; direct native Go loader selected')
        return
    native = _module()  # Import-only; do NOT dlopen Go during Kodi startup.
    token = secrets.token_hex(32)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _make_handler(native, token))
    server.daemon_threads = True
    location = _location()
    _publish(location, server.server_port, token)
    _log('Ready on 127.0.0.1:{}; native Go load deferred until first request'.format(server.server_port))
    worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .2},
                              name='KodiGoBridge', daemon=True)
    worker.start()
    try:
        monitor = xbmc.Monitor()
        while not monitor.waitForAbort(1.0):
            pass
    finally:
        try:
            with open(location, 'r', encoding='utf-8') as info:
                current = json.load(info)
            if current.get('token') == token:
                os.unlink(location)
        except (OSError, ValueError):
            pass
        server.shutdown()
        server.server_close()
        worker.join(3)
        _log('Stopped')


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        # A missing kernel facility should not show a Python exception dialog
        # every time Kodi starts. Leave a clear one-line diagnostic in kodi.log.
        _log('Bridge unavailable (Kodi stays usable): {}: {}'.format(
            type(exc).__name__, str(exc)[:300]), xbmc.LOGERROR)
