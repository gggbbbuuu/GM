import re
import base64
import requests
from urllib.parse import urlparse, urlencode, parse_qs, unquote
from typing import Optional, List

try:
    from .models import JetLink
except ImportError:
    JetLink = None

_a1 = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome"
_a2 = "/131.0.0.0 Safari/537.36"
_BROWSER_UA = _a1 + _a2

def _x9(k: str) -> str:
    _r = []
    for i, c in enumerate(k):
        _r.append(chr(ord(c) ^ (i % 7 + 1)))
    return "".join(_r)

def _m3(s: str) -> str:
    _t = []
    for i in range(len(s)):
        _c = ord(s[i])
        if _c >= 65 and _c <= 90:
            _t.append(chr(((_c - 65 + 13) % 26) + 65))
        elif _c >= 97 and _c <= 122:
            _t.append(chr(((_c - 97 + 13) % 26) + 97))
        else:
            _t.append(s[i])
    return "".join(_t)

def get_headers(referer: str = None, origin: str = None) -> dict:
    h = {
        "User-Agent": _BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        h["Referer"] = referer
    if origin:
        h["Origin"] = origin
    return h

def get_session(referer: str = None, origin: str = None) -> requests.Session:
    s = requests.Session()
    s.headers.update(get_headers(referer, origin))
    return s

def decode_stream(encoded: str) -> str:
    try:
        _d1 = base64.b64decode(encoded)
        _d2 = base64.b64decode(_d1)
        return _d2.decode("utf-8")
    except Exception:
        pass
    try:
        return base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return encoded

def find_m3u8(html: str, base_url: str = "") -> Optional[str]:
    _pats = [
        r'(?:source|src|file)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
        r'["\']([^"\']*\.m3u8[^"\']*)["\']',
    ]
    for p in _pats:
        _m = re.findall(p, html, re.IGNORECASE)
        if _m:
            u = _m[0]
            if u.startswith("//"):
                u = "https:" + u
            elif not u.startswith("http") and base_url:
                _bp = urlparse(base_url)
                u = f"{_bp.scheme}://{_bp.netloc}{u}"
            return u
    return None

def find_iframes(html: str, base_url: str = "") -> List[str]:
    _iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    _results = []
    for u in _iframes:
        if u.startswith("//"):
            u = "https:" + u
        elif not u.startswith("http") and base_url:
            _bp = urlparse(base_url)
            if u.startswith("/"):
                u = f"{_bp.scheme}://{_bp.netloc}{u}"
            else:
                u = f"{_bp.scheme}://{_bp.netloc}/{'/'.join(_bp.path.split('/')[:-1])}/{u}"
        _results.append(u)
    return _results

def make_link(url: str, referer: str = None, origin: str = None) -> "JetLink":
    h = {}
    if referer:
        h["Referer"] = referer
    if origin:
        h["Origin"] = origin
    h["User-Agent"] = _BROWSER_UA
    if JetLink is not None:
        return JetLink(url, headers=h)
    return url

def unpack_js(html: str) -> Optional[str]:
    import jsunpack
    _m = re.findall(r"(eval\(function\(p,a,c,k,e,d\).+?{}\)\))", html)
    if _m:
        try:
            return jsunpack.unpack(_m[0])
        except Exception:
            pass
    return None

def char_array_decode(data: str) -> str:
    try:
        return "".join(chr(int(x)) for x in data.split(","))
    except Exception:
        return data

def fetch_page(url: str, referer: str = None, session: requests.Session = None) -> str:
    _h = get_headers(referer)
    if session:
        r = session.get(url, timeout=10)
    else:
        r = requests.get(url, headers=_h, timeout=10)
    r.raise_for_status()
    return r.text

def _v_check():
    import xbmcaddon as _xa
    _ma = _xa.Addon("script.module.jetextractors")
    _v = _ma.getAddonInfo("version")
    _t = tuple(int(x) for x in _v.split("."))
    return _t
