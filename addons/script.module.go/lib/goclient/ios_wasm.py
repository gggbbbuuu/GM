# -*- coding: utf-8 -*-
"""iOS remote WASM backend for script.module.go based on v1.0.5.
Uses original tls-client v1.16.0 HTTP/2, Chrome 133 or ConfirmedAndroid via JSC/Python TCP.
The compressed WASM is downloaded using the existing v1.0.5 HTTPS server.
"""
import base64
import json
import threading
import http.server
import ctypes
import hashlib
import os
import platform
import socket
import sys
import time
import traceback
import zlib
import http.cookiejar
import urllib.request
import urllib.parse
import email.message
from urllib.parse import urlsplit

import xbmc
import xbmcgui
import xbmcvfs

ADDON_ID='script.module.go'
VERSION='1.0.7'
ROOT=os.path.dirname(os.path.abspath(__file__))
VOID=ctypes.c_void_p
EXCPTR=ctypes.POINTER(VOID)

_WASM_ZLIB_B64 = ()

JS_SHA256 = '08b58bba0cad2be35bfc78f312abac31372d7907a90bafa5b3b9533918461990'
_JS_B64 = ()

def load_wasm(row):
    """Download verified iPhone WASM from the SAME v1.0.5 native base URL.

    Raw and XZ hashes/sizes pinned in resources/native/ios.json. Never fall
    back to Python Requests or an unverified/legacy local WASM binary.
    """
    from . import native as _native
    import lzma
    import tempfile
    from urllib.request import Request, urlopen
    from urllib.parse import urlsplit as split

    manifest_path = os.path.join(_native._native_root(), 'ios.json')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    entry = manifest['files']['ios-arm64']
    path = entry['path']
    if path != 'ios-wasm/go_request_api_h2.wasm.xz':
        raise RuntimeError('Invalid iOS WASM path in signed-in-addon index')
    expected = int(entry['size'])
    compressed_expected = int(entry['xz_size'])
    digest_raw = str(entry['sha256']).lower()
    digest_xz = str(entry['xz_sha256']).lower()
    if not 0 < expected <= 32*1024*1024 or not 0 < compressed_expected <= 16*1024*1024:
        raise RuntimeError('Invalid iOS WASM payload size')
    if any(len(v) != 64 or any(c not in '0123456789abcdef' for c in v)
           for v in (digest_raw, digest_xz)):
        raise RuntimeError('Invalid iOS WASM payload hashes')
    cache_dir = _native._remote_cache_root()
    os.makedirs(cache_dir, exist_ok=True)
    cached = os.path.join(cache_dir, 'ios-arm64-' + digest_raw + '.wasm')
    # Verify cache on every new interpreter. A previous failed download never
    # overwrites an existing valid file.
    if _native._verified_cached_file(cached, {'size': expected, 'sha256': digest_raw}):
        row('00 WASM SOURCE: verified native-cache')
    else:
        base = _native._remote_base_url()
        url = base + '/' + path
        tmp_xz = None
        tmp_raw = None
        try:
            with tempfile.NamedTemporaryFile('wb', dir=cache_dir, prefix='.wasm-download-',
                                             suffix='.xz', delete=False) as out:
                tmp_xz = out.name
                req = Request(url, headers={'User-Agent': 'Kodi-script.module.go/1.0.7'})
                with urlopen(req, timeout=45) as response:
                    if response.getcode() != 200:
                        raise RuntimeError('WASM download returned HTTP ' + str(response.getcode()))
                    if (response.headers.get('Content-Encoding') or 'identity').lower() != 'identity':
                        raise RuntimeError('WASM server applied unexpected HTTP content encoding')
                    final = split(response.geturl())
                    source = split(base)
                    if (final.scheme.lower() != 'https' or
                        (final.hostname, final.port) != (source.hostname, source.port)):
                        raise RuntimeError('WASM download redirected outside trusted HTTPS host')
                    length_header = response.headers.get('Content-Length')
                    if length_header is not None and int(length_header) != compressed_expected:
                        raise RuntimeError('Unexpected compressed WASM Content-Length')
                    total = 0
                    h = hashlib.sha256()
                    for chunk in iter(lambda: response.read(256*1024), b''):
                        total += len(chunk)
                        if total > compressed_expected:
                            raise RuntimeError('Compressed WASM exceeds pinned size')
                        out.write(chunk)
                        h.update(chunk)
                    if total != compressed_expected or h.hexdigest() != digest_xz:
                        raise RuntimeError('Compressed WASM length or SHA256 mismatch')
            with tempfile.NamedTemporaryFile('wb', dir=cache_dir, prefix='.wasm-extract-',
                                             suffix='.wasm', delete=False) as out:
                tmp_raw = out.name
                h = hashlib.sha256()
                total = 0
                with lzma.open(tmp_xz,'rb') as src:
                    for chunk in iter(lambda: src.read(256*1024), b''):
                        total += len(chunk)
                        if total > expected:
                            raise RuntimeError('Raw WASM exceeds pinned size')
                        out.write(chunk)
                        h.update(chunk)
                if total != expected or h.hexdigest() != digest_raw:
                    raise RuntimeError('Raw WASM length or SHA256 mismatch')
            os.replace(tmp_raw, cached)
            tmp_raw = None
            row('00 WASM SOURCE: remote iOS WASM downloaded, verified and cached')
        finally:
            for path_to_clean in (tmp_xz, tmp_raw):
                if path_to_clean:
                    try: os.unlink(path_to_clean)
                    except OSError: pass
    with open(cached, 'rb') as f:
        binary = f.read()
    if len(binary) != expected or hashlib.sha256(binary).hexdigest() != digest_raw:
        raise RuntimeError('WASM cached file failed final SHA256/size verification')
    row('00 WASM PAYLOAD: PASS (%d bytes, SHA-256 verified)' % len(binary))
    return binary

def load_js(row):
    p=os.path.join(ROOT,'wasi_bridge.js')
    if os.path.isfile(p):
        with open(p,'rb') as f:data=f.read()
        row('02 JS SOURCE: standalone wasi_bridge.js')
    else:
        raise RuntimeError('Required packaged wasi_bridge.js is missing')
    if hashlib.sha256(data).hexdigest()!=JS_SHA256:
        raise RuntimeError('JS SHA-256 mismatch')
    return data.decode('utf-8')

class JSC:
    def __init__(self):
        self.lib = ctypes.CDLL('/System/Library/Frameworks/JavaScriptCore.framework/JavaScriptCore')
        self._fn('JSGlobalContextCreate', VOID, [VOID])
        self._fn('JSGlobalContextRelease', None, [VOID])
        self._fn('JSStringCreateWithUTF8CString', VOID, [ctypes.c_char_p])
        self._fn('JSStringRelease', None, [VOID])
        self._fn('JSEvaluateScript', VOID, [VOID, VOID, VOID, VOID, ctypes.c_int, EXCPTR])
        self._fn('JSValueToStringCopy', VOID, [VOID, VOID, EXCPTR])
        self._fn('JSStringGetMaximumUTF8CStringSize', ctypes.c_size_t, [VOID])
        self._fn('JSStringGetUTF8CString', ctypes.c_size_t, [VOID, ctypes.c_void_p, ctypes.c_size_t])
        self._fn('JSContextGetGlobalObject', VOID, [VOID])
        self._fn('JSObjectMakeFunctionWithCallback', VOID, [VOID, VOID, VOID])
        self._fn('JSObjectSetProperty', None, [VOID, VOID, VOID, VOID, ctypes.c_uint, EXCPTR])
        self._fn('JSValueMakeString', VOID, [VOID, VOID])
        self.callbacks = []  # keep ctypes callbacks strongly referenced
        self.ctx = self.lib.JSGlobalContextCreate(None)
        if not self.ctx:
            raise RuntimeError('JSGlobalContextCreate returned NULL')

    def _fn(self, name, restype, argtypes):
        fn = getattr(self.lib, name)
        fn.restype, fn.argtypes = restype, argtypes

    def _jsstring(self, text):
        ptr = self.lib.JSStringCreateWithUTF8CString(text.encode('utf-8'))
        if not ptr:
            raise RuntimeError('JSStringCreateWithUTF8CString returned NULL')
        return ptr

    def _value(self, ctx, value):
        ex = VOID()
        s = self.lib.JSValueToStringCopy(ctx, value, ctypes.byref(ex))
        if ex.value or not s:
            return '<could not stringify JS value>'
        try:
            size = self.lib.JSStringGetMaximumUTF8CStringSize(s)
            if size > 524288:
                raise RuntimeError('JSC output too large')
            buf = ctypes.create_string_buffer(size)
            self.lib.JSStringGetUTF8CString(s, buf, size)
            return buf.value.decode('utf-8', 'replace')
        finally:
            self.lib.JSStringRelease(s)

    def eval(self, code):
        s = self._jsstring(code)
        try:
            ex = VOID()
            val = self.lib.JSEvaluateScript(self.ctx, s, None, None, 1, ctypes.byref(ex))
            if ex.value:
                raise RuntimeError('JavaScript exception: ' + self._value(self.ctx, ex))
            if not val:
                raise RuntimeError('JSEvaluateScript returned NULL')
            return self._value(self.ctx, val)
        finally:
            self.lib.JSStringRelease(s)

    def callback(self, name, handler):
        signature = ctypes.CFUNCTYPE(VOID, VOID, VOID, VOID, ctypes.c_size_t,
                                    ctypes.POINTER(VOID), EXCPTR)
        def func(ctx, _function, _this, count, argv, _exception):
            try:
                params = [self._value(ctx, argv[i]) for i in range(count)]
                result = str(handler(*params))
            except BaseException as exc:
                # Never let Python errors unwind through the native C ABI.
                result = ('~1' if name == '__python_net' and count > 0 and
                          self._value(ctx, argv[0]) == 'R' else '-1')
                xbmc.log('[script.module.go iOS WASM] callback error: ' + repr(exc), xbmc.LOGERROR)
            js = self._jsstring(result)
            try:
                return self.lib.JSValueMakeString(ctx, js)
            finally:
                self.lib.JSStringRelease(js)
        cb = signature(func)
        self.callbacks.append(cb)
        key = self._jsstring(name)
        try:
            cbfn = self.lib.JSObjectMakeFunctionWithCallback(
                self.ctx, key, ctypes.cast(cb, VOID))
            if not cbfn:
                raise RuntimeError('JSObjectMakeFunctionWithCallback failed')
            ex = VOID()
            obj = self.lib.JSContextGetGlobalObject(self.ctx)
            self.lib.JSObjectSetProperty(self.ctx, obj, key, cbfn, 0, ctypes.byref(ex))
            if ex.value:
                raise RuntimeError('Cannot register callback: ' + self._value(self.ctx, ex))
        finally:
            self.lib.JSStringRelease(key)

    def close(self):
        if self.ctx:
            self.lib.JSGlobalContextRelease(self.ctx)
            self.ctx = None
        self.callbacks.clear()




class PublicTLS:
    def __init__(self,port):
        self.port=port;self.open_sockets={};self.next_fd=1
        self.counts={'connect':0,'write_calls':0,'write_bytes':0,'read_calls':0,'read_bytes':0,'close':0,'random':0}
    def handle(self,op,a='',b=''):
        if op=='N':
            n=int(a)
            if not 0<=n<=256:return '~1'
            self.counts['random']+=1
            return os.urandom(n).hex()
        if op=='C':
            # Go's dialer supplies host:port. Allow HTTP/HTTPS destinations
            # including arbitrary origin ports; reject malformed addresses.
            parsed=urllib.parse.urlsplit('tcp://'+str(a))
            host=parsed.hostname
            port=parsed.port
            if not host or not port or parsed.username is not None or parsed.password is not None or parsed.path not in ('','/') or parsed.query or parsed.fragment:
                raise ValueError('Invalid TCP destination')
            address=(host,port)
            sock=socket.create_connection(address,timeout=8)
            sock.setblocking(False)
            fd=self.next_fd;self.next_fd+=1;self.open_sockets[fd]=sock
            self.counts['connect']+=1
            return str(fd)
        fd=int(a)
        if op=='X':
            sock=self.open_sockets.pop(fd,None)
            if sock is not None:sock.close()
            self.counts['close']+=1
            return '0'
        sock=self.open_sockets[fd]
        try:
            if op=='W':
                data=bytes.fromhex(b)
                if len(data)>256:raise ValueError('TCP write exceeds 256')
                n=sock.send(data)
                if n:self.counts['write_calls']+=1;self.counts['write_bytes']+=n
                return str(n if n else -2)
            if op=='R':
                size=int(b)
                if not 0<=size<=256:return '~1'
                data=sock.recv(size)
                if data:self.counts['read_calls']+=1;self.counts['read_bytes']+=len(data)
                return data.hex()
        except (BlockingIOError,InterruptedError):
            return '~2' if op=='R' else '-2'
        return '~1'
    def close(self):
        for sock in self.open_sockets.values():
            try:sock.close()
            except OSError:pass
        self.open_sockets.clear()


class _CookieResponse:
    """Provide separate Set-Cookie headers to Python's standard CookieJar."""
    def __init__(self, headers):
        self._headers=email.message.Message()
        for item in headers:
            self._headers.add_header('Set-Cookie',item)
    def info(self):
        return self._headers


class ReusableIOSBackend:
    """Isolated v1.0 experiment: compiled WASM reused across fresh Go instances.

    The Python CookieJar persists separately per session because a fresh
    Go instance has no shared in-memory Go cookie jar. Not production-hardened.
    """
    def __init__(self,port=None,log=lambda msg:None):
        self.log=log
        self.lock=threading.RLock()
        self.net=PublicTLS(port)
        self.jsc=None
        self.input_bytes=b''
        self.cookies={}
        self.compiles=0
        self.invocations=0
        binary=load_wasm(log)
        try:
            jsc=JSC()
            self.jsc=jsc
            jsc.callback('__python_chunk',lambda off,size:
                base64.b64encode(binary[int(off):int(off)+int(size)]).decode('ascii'))
            jsc.callback('__python_input_chunk',lambda off,size:
                base64.b64encode(self.input_bytes[int(off):int(off)+int(size)]).decode('ascii'))
            jsc.callback('__python_net',self.net.handle)
            jsc.eval(load_js(log))
            log('01 JSC: PASS')
            log('02 WASM TRANSFER: '+jsc.eval('__goBridge.transfer(%d,%d)' %
                (len(binary),zlib.adler32(binary)&0xffffffff)))
            log('03 WASI COMPILE ONCE: '+jsc.eval('__goBridge.compile()'))
            self.compiles=1
        except BaseException:
            self.close()
            raise

    def perform(self,method,url,headers=None,body=b'',profile='chrome_133',session='default',timeout=25):
        if not isinstance(url,str) or len(url)>8192:
            raise ValueError('URL required (max 8192 characters)')
        parts=urlsplit(url)
        if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password:
            raise ValueError('Only absolute HTTP(S) URLs are supported')
        method=str(method).upper()
        if method not in ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'):
            raise ValueError('Unsupported v1.0 method '+method)
        # The native v1.0.5 API defaults to the genuine Android TLS profile.
        # Only the Chrome spelling is an alias; do not rewrite Android to Chrome.
        profile=str(profile or 'android').strip().lower()
        if profile == 'chrome133':
            profile='chrome_133'
        if profile not in ('android','chrome_133'):
            raise ValueError('Supported profiles are android, chrome133 and chrome_133')
        if not 1 <= int(timeout) <= 60:
            raise ValueError('v1.0 timeout must be between 1 and 60 seconds')
        body=bytes(body)
        if len(body)>196608:raise ValueError('v1.0 request body maximum is 192KiB')
        headers=dict(headers or {})
        if any('\r' in k or '\n' in k or '\r' in v or '\n' in v for k,v in headers.items()):
            raise ValueError('Invalid request header')
        with self.lock:
            key=(profile,str(session))
            jar=self.cookies.setdefault(key,http.cookiejar.CookieJar())
            request=urllib.request.Request(url,headers=headers)
            if not any(k.lower()=='cookie' for k in headers):
                jar.add_cookie_header(request)
                cookie=request.get_header('Cookie')
                if cookie:headers['Cookie']=cookie
            batch={'requests':[{'method':method,'url':url,
                 'headers':headers,'body_base64':base64.b64encode(body).decode('ascii'),
                 'profile':profile,'session':str(session),'timeout_seconds':int(timeout)}]}
            self.input_bytes=json.dumps(batch,separators=(',',':')).encode('utf-8')
            if len(self.input_bytes)>262144:
                raise ValueError('Request JSON input too large')
            jsc=self.jsc
            if jsc is None:raise RuntimeError('Backend closed')
            try:
                jsc.eval('__goBridge.instantiate()')
                jsc.eval('__goBridge.setInput(%d,%d)' %
                         (len(self.input_bytes),zlib.adler32(self.input_bytes)&0xffffffff))
                code=jsc.eval('__goBridge.start()')
                size=int(jsc.eval('__goBridge.stdoutLength()'))
                if size<1 or size>2097152:raise RuntimeError('Go output size outside 2MiB bound')
                stdout=''.join(jsc.eval('__goBridge.stdoutChunk(%d,%d)'%(pos,4096))
                    for pos in range(0,size,4096))
                if code!='EXIT 0':raise RuntimeError('Go WASI exit: '+code+' '+stdout[-400:])
                marker='GO_REQUEST_API_JSON:'
                if marker not in stdout:raise RuntimeError('Go output missing JSON marker: '+stdout[-400:])
                raw=stdout.split(marker,1)[1].splitlines()[0]
                responses=json.loads(base64.b64decode(raw,validate=True))['results']
                if len(responses)!=1:raise RuntimeError('Unexpected Go response count')
                result=responses[0]
                # Go v1.0 preserves multiple independent Set-Cookie fields.
                cookie_lines=result.get('set_cookies') or []
                if cookie_lines:
                    jar.extract_cookies(_CookieResponse(cookie_lines),request)
                self.invocations+=1
                return {'status_code':result.get('status',0),
                    'content':base64.b64decode(result.get('body_base64',''),validate=True),
                    'url':result.get('url') or url,
                    'headers':result.get('headers') or {},
                    'protocol':result.get('protocol') or '',
                    'error':result.get('error') or '',
                    'mitigated':result.get('cf_mitigated') or ''}
            finally:
                self.input_bytes=b''
                try:jsc.eval('__goBridge.releaseInstance()')
                except BaseException:pass
                self.net.close()
                try:
                    fn=getattr(jsc.lib,'JSGarbageCollect')
                    fn.argtypes=[VOID];fn.restype=None
                    fn(jsc.ctx)
                except (AttributeError,ValueError):pass

    def close(self):
        with self.lock:
            self.net.close()
            if self.jsc:
                self.jsc.close()
                self.jsc=None



# Universal module entry point. One cached JavaScriptCore context and compiled
# WASM module per Python interpreter. Calls are serialized by the backend.
_INSTANCE_LOCK = threading.RLock()
_INSTANCE = None

def _write_kodi_log(message):
    try:
        xbmc.log('[script.module.go iOS WASM] ' + str(message), xbmc.LOGINFO)
    except (ImportError, AttributeError):
        pass

def _instance():
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = ReusableIOSBackend(log=_write_kodi_log)
        return _INSTANCE

def perform(method, url, headers, body, profile, session, timeout):
    global _INSTANCE
    # Never change the TLS engine implicitly on an error.
    with _INSTANCE_LOCK:
        backend = _instance()
        try:
            return backend.perform(method=method, url=url, headers=headers,
                                   body=body, profile=profile, session=session,
                                   timeout=timeout)
        except (RuntimeError, OSError):
            # If a JSC/WASI runtime error occurs, discard the damaged instance.
            # The next request may retry initialization; callers get the error.
            _INSTANCE = None
            backend.close()
            raise

def runtime_stats():
    """Diagnostic counters; does not initialize the WASM runtime."""
    with _INSTANCE_LOCK:
        b = _INSTANCE
        return {'initialized': bool(b),
                'compiles': b.compiles if b else 0,
                'invocations': b.invocations if b else 0,
                'tcp': dict(b.net.counts) if b else {}}

def shutdown():
    """Explicit cleanup for diagnostics and addon unload."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        b, _INSTANCE = _INSTANCE, None
        if b is not None:
            b.close()
