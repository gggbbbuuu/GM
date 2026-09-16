import re
import requests
from urllib.parse import urljoin, urlparse

import xbmc
from ..tools import debug_log


class _UrllibResponse:
    """Adapter that makes an urllib response compatible with the
    `requests.Response` interface used by `_resolve_variant_to_media`."""
    def __init__(self, status_code, resp_headers, body_bytes, url, read_func=None, close_func=None):
        self.status_code = status_code
        self._resp_headers = resp_headers
        self.headers = type("H", (), {"get": lambda self, k, default="": resp_headers.get(k.lower(), default)})()
        self.url = url
        self._body = body_bytes
        self._read_func = read_func
        self._close_func = close_func
        self._consumed = False

    def iter_content(self, chunk_size=8192):
        if self._read_func is not None and not self._consumed:
            while True:
                chunk = self._read_func(chunk_size)
                if not chunk:
                    break
                yield chunk
        elif self._read_func is not None and self._consumed:
            for i in range(0, len(self._body), chunk_size):
                yield self._body[i:i + chunk_size]
        else:
            for i in range(0, len(self._body), chunk_size):
                yield self._body[i:i + chunk_size]
        self._consumed = True

    @property
    def text(self):
        if self._read_func is not None and not self._consumed:
            data = b""
            while True:
                chunk = self._read_func(8192)
                if not chunk:
                    break
                data += chunk
            self._body = data
            self._consumed = True
        return self._body.decode("utf-8", errors="replace")

    def close(self):
        if self._close_func:
            self._close_func()
        self._consumed = True


class _UrllibClient:
    """Adapter that wraps urllib to provide a `.get()` method compatible
    with the requests.Session interface used by `_resolve_variant_to_media`
    and the proxy's segment serving."""
    def __init__(self, proxy=None):
        self._proxy = proxy

    def get(self, url, headers=None, timeout=(5, 15), stream=True, allow_redirects=True):
        """Returns a _UrllibResponse that behaves like requests.Response."""
        try:
            from six.moves import urllib_request, urllib_error
        except ImportError:
            from urllib import request as urllib_request
            from urllib import error as urllib_error
        import ssl
        import gzip
        import io

        req = urllib_request.Request(url)
        for k, v in (headers or {}).items():
            if k.lower() == 'accept-encoding':
                req.add_header(k, 'gzip, deflate')
            else:
                req.add_header(k, v)

        parsed = urlparse(url)
        if parsed.scheme == 'https':
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            opener = urllib_request.build_opener(urllib_request.HTTPSHandler(context=ctx))
        else:
            opener = urllib_request.build_opener()

        if not allow_redirects:
            class NoRedirect(urllib_request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            if parsed.scheme == 'https':
                opener = urllib_request.build_opener(urllib_request.HTTPSHandler(context=ctx), NoRedirect)
            else:
                opener = urllib_request.build_opener(NoRedirect)

        resp = opener.open(req, timeout=timeout if isinstance(timeout, int) else timeout[1])
        status = resp.getcode()
        resp_headers = {}
        for h in resp.headers.items():
            resp_headers[h[0].lower()] = h[1]
        final_url = resp.geturl()

        if not stream:
            body = resp.read()
            resp.close()
            # Handle gzip
            if resp_headers.get('content-encoding', '').lower() == 'gzip':
                body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
            return _UrllibResponse(status, resp_headers, body, final_url, read_func=None, close_func=None)

        # Streaming: keep resp open, provide read() and close()
        # Handle gzip streaming via a decompressor pipe
        is_gzip = resp_headers.get('content-encoding', '').lower() == 'gzip'
        if is_gzip:
            gzip_reader = gzip.GzipFile(fileobj=resp)

            def _read(chunk_size=8192):
                return gzip_reader.read(chunk_size)
        else:

            def _read(chunk_size=8192):
                return resp.read(chunk_size)

        def _close():
            resp.close()

        return _UrllibResponse(status, resp_headers, b"", final_url, read_func=_read, close_func=_close)


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
