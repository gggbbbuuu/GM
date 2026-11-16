"""Reusable HTTP client for Kodi: from goclient import get, post, Session.

Uses native Go HTTP/2 when a platform-matched GoRequest binary is installed.
Bundled Android ARM32 compatibility binary supports only Rugby24 via native Go.
"""
import json as _json
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
# UWP/Xbox must never import .native: importing ctypes itself fails on Kodi 21.
# Kodi's UWP flag distinguishes the Xbox package from ordinary Windows x64.
def _running_on_uwp():
    try:
        import xbmc
        return bool(xbmc.getCondVisibility('System.Platform.UWP'))
    except (ImportError, AttributeError):
        return False

if _running_on_uwp():
    from .uwp_fallback import perform, using_generic_native, target_name, installed_targets
else:
    from .native import perform, using_generic_native, target_name, installed_targets

__all__ = ['get', 'post', 'request', 'Session', 'Response', 'using_generic_native', 'target_name', 'installed_targets']

class Response:
    def __init__(self, status_code=0, content=b'', url='', headers=None, protocol='', error='', mitigated=''):
        self.status_code = int(status_code or 0)
        self.content = content if isinstance(content, bytes) else str(content).encode('utf-8')
        self.url = url
        self.headers = headers or {}
        self.protocol = protocol
        self.error = error or ''
        self.cf_mitigated = mitigated or ''

    @property
    def ok(self):
        return 200 <= self.status_code < 400 and not self.error

    @property
    def text(self):
        import re
        ctype = self.headers.get('content-type', self.headers.get('Content-Type', ''))
        match = re.search(r'charset\s*=\s*["\']?([\w\-]+)', ctype, re.I)
        charset = match.group(1) if match else 'utf-8'
        try:
            return self.content.decode(charset, 'replace')
        except LookupError:
            return self.content.decode('utf-8', 'replace')

    def json(self):
        return _json.loads(self.text)

    def raise_for_status(self):
        if self.error or self.status_code >= 400 or self.status_code == 0:
            raise RuntimeError(self.error or 'HTTP {}'.format(self.status_code))

    def __bool__(self):
        return self.ok


def _with_params(url, params):
    if not params:
        return url
    bits = urlsplit(url)
    pairs = list(parse_qsl(bits.query, keep_blank_values=True))
    if isinstance(params, dict):
        for key, value in params.items():
            if isinstance(value, (list, tuple)):
                pairs.extend((key, v) for v in value)
            else:
                pairs.append((key, value))
    else:
        pairs.extend(params)
    return urlunsplit((bits.scheme, bits.netloc, bits.path, urlencode(pairs), bits.fragment))


def request(method, url, params=None, headers=None, data=None, json=None,
            profile='android', timeout=25, session='default'):
    """Perform GET/POST/etc; returns Response, not a requests.Response object.

    To set JSON body pass json={...}; to send raw bytes pass data=b'...'.
    Cached cookies are scoped by profile, session and timeout in native Go.
    """
    method = str(method).upper().strip()
    if method not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
        raise ValueError('Unsupported HTTP method: ' + method)
    url = _with_params(str(url), params)
    headers = dict(headers or {})
    if json is not None and data is not None:
        raise ValueError('Pass either json or data, not both')
    if json is not None:
        body = _json.dumps(json, separators=(',', ':')).encode('utf-8')
        if not any(k.lower() == 'content-type' for k in headers):
            headers['Content-Type'] = 'application/json'
    elif isinstance(data, dict):
        body = urlencode(data, doseq=True).encode('utf-8')
        if not any(k.lower() == 'content-type' for k in headers):
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
    elif isinstance(data, str):
        body = data.encode('utf-8')
    elif data is None:
        body = b''
    else:
        body = bytes(data)
    result = perform(method=method, url=url, headers=headers, body=body,
                     profile=profile, session=str(session), timeout=int(timeout))
    return Response(**result)


def get(url, **kwargs):
    return request('GET', url, **kwargs)


def post(url, **kwargs):
    return request('POST', url, **kwargs)


class Session:
    """Browser-profile session with persistent cookies in the current Kodi process."""
    def __init__(self, profile='android', headers=None, timeout=25, name=None):
        import uuid
        self.profile = profile
        self.headers = dict(headers or {})
        self.timeout = timeout
        self.name = name or uuid.uuid4().hex

    def request(self, method, url, **kwargs):
        hdr = self.headers.copy()
        hdr.update(kwargs.pop('headers', {}) or {})
        return request(method, url, headers=hdr, profile=kwargs.pop('profile', self.profile),
                       timeout=kwargs.pop('timeout', self.timeout),
                       session=kwargs.pop('session', self.name), **kwargs)

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self.request('POST', url, **kwargs)
