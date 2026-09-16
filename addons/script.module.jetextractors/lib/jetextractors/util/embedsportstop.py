import requests
import base64
import re
from urllib.parse import urlparse, urljoin
from typing import List
import platform
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


def is_xbox():
    return 'Xbox' in platform.system()


class _EmbedTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ssl_version=ssl.PROTOCOL_TLS)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.check_hostname = False
        ctx.set_ciphers(
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256:"
            "ECDHE-ECDSA-AES128-GCM-SHA256:"
            "ECDHE-RSA-AES128-GCM-SHA256:"
            "ECDHE-ECDSA-AES256-GCM-SHA384:"
            "ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-CHACHA20-POLY1305"
        )
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

# Only import what's available - catch ALL errors
try:
    from Cryptodome.Cipher import ChaCha20_Poly1305
    CRYPTO_LIB = 'pycryptodome'
except Exception:  # Cryptodome exists but may be broken on Xbox
    try:
        from Crypto.Cipher import ChaCha20_Poly1305
        CRYPTO_LIB = 'pycrypto'
    except Exception:  # PyCrypto not available
        # Xbox Kodi 21 fallback - cryptography is built-in
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        CRYPTO_LIB = 'cryptography'

SINGLE_PATH_HOSTS = ("pooembed", "embedindia")

def _obfuscation_decode(data: bytes) -> bytes:
    return bytes(((b - 0x21 + 71) % 94) + 0x21 for b in data)

def _parse_response(content: bytes) -> bytes:
    i = 0
    while i < len(content):
        tag = content[i]
        i += 1
        field = tag >> 3
        length = 0
        shift = 0
        while True:
            b = content[i]
            i += 1
            length |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        value = content[i:i + length]
        i += length
        if field == 1:
            return value
    raise ValueError("No cipher field found in response")

def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        out.append(byte | 0x80 if n else byte)
        if not n:
            return bytes(out)

def _field(number: int, value: bytes) -> bytes:
    tag = (number << 3) | 2
    return bytes([tag]) + _varint(len(value)) + value

def _build_payload(url: str) -> bytes:
    host = urlparse(url).netloc
    segments = url.rstrip('/').split('/')
    if any(h in host for h in SINGLE_PATH_HOSTS):
        path = '/'.join(segments[4:])
        return _field(1, path.encode())
    sc, stream_id, no = segments[-3:]
    return _field(1, sc.encode()) + _field(2, stream_id.encode()) + _field(3, no.encode())

def _extract_indians_token(html: str) -> str:
    """Try to extract the 'indians' API key from the embed page HTML."""
    patterns = [
        r'["\']indians["\']\s*[:=]\s*["\']([a-f0-9]+)["\']',
        r'indians\s*=\s*["\']([a-f0-9]+)["\']',
        r'localStorage\.setItem\(\s*["\']indians["\']\s*,\s*["\']([a-f0-9]+)["\']',
        r'window\.indians\s*=\s*["\']([a-f0-9]+)["\']',
        r'data-indians=["\']([a-f0-9]+)["\']',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _extract_m3u8_urls_from_html(html: str, base_url: str) -> List[str]:
    """Extract all m3u8 URLs from embed page HTML as a fallback."""
    patterns = [
        r'const\s+streamUrl\s*=\s*["\']([^"\']+)["\']',
        r'source\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
        r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
        r'["\']([^"\']*\.m3u8[^"\']*)["\']',
    ]
    urls = []
    seen = set()
    for p in patterns:
        for match in re.findall(p, html, re.IGNORECASE):
            url = match.strip()
            if url.startswith("//"):
                url = "https:" + url
            elif not url.startswith("http"):
                url = urljoin(base_url, url)
            if "m3u8" in url.lower() and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def get_embedsportstop_stream(url: str) -> str:
    domain = f"https://{urlparse(url).netloc}"
    headers = {
        'indians': '18866ebec06934ba03ad3387e9fc9ebfbf2ea2d0e9305c86797b66c62ee4f8a5',
        'content-type': 'application/octet-stream',
        'origin': domain,
        'referer': url,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'x-requested-with': 'XMLHttpRequest',
    }

    session = requests.Session()
    session.verify = False
    session.mount("https://", _EmbedTLSAdapter())

    # GET the embed page first to establish session/cookies and extract dynamic tokens
    embed_html = ""
    final_url = url
    try:
        get_headers = {
            'User-Agent': headers['user-agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': url,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Ch-Ua': headers['sec-ch-ua'],
            'Sec-Ch-Ua-Mobile': headers['sec-ch-ua-mobile'],
            'Sec-Ch-Ua-Platform': headers['sec-ch-ua-platform'],
        }
        get_resp = session.get(url, headers=get_headers, timeout=10, allow_redirects=True)
        embed_html = get_resp.text
        final_url = get_resp.url
        # Update domain/referer after potential redirect
        final_domain = f"https://{urlparse(final_url).netloc}"
        headers['origin'] = final_domain
        headers['referer'] = final_url
        # Try to extract a refreshed 'indians' token from the page
        token = _extract_indians_token(embed_html)
        if token:
            headers['indians'] = token
    except Exception:
        pass

    # Try POST to /fetch with the encrypted payload
    for fetch_path in ('/fetch', '/api/fetch'):
        response = session.post(
            domain + fetch_path,
            data=_build_payload(url),
            headers=headers
        )

        if response.status_code != 200:
            try:
                body = response.text[:500]
            except Exception:
                body = "<unable to read body>"
        else:
            body = None  # success path

        # Check for valid encrypted response
        ac = response.headers.get('access-control-expose-headers')
        key = response.headers.get(ac) if ac else None
        if key:
            b64_cipher = _parse_response(response.content)
            decoded = _obfuscation_decode(b64_cipher)
            raw = base64.b64decode(decoded + b'=' * (-len(decoded) % 4))
            nonce = raw[:12]
            ct_with_tag = raw[12:]

            if CRYPTO_LIB == 'cryptography':
                cipher = ChaCha20Poly1305(key.encode('utf-8'))
                return cipher.decrypt(nonce, ct_with_tag[:-16], ct_with_tag[-16:]).decode('utf-8').strip()
            else:
                cipher = ChaCha20_Poly1305.new(key=key.encode('utf-8'), nonce=nonce)
                return cipher.decrypt_and_verify(ct_with_tag[:-16], ct_with_tag[-16:]).decode('utf-8').strip()

    # POST failed — try to extract m3u8 directly from the embed page HTML
    if embed_html:
        stream_urls = _extract_m3u8_urls_from_html(embed_html, final_url)
        best_url = None
        for candidate in stream_urls:
            try:
                check = session.get(candidate, headers={
                    'User-Agent': headers['user-agent'],
                    'Referer': final_url,
                    'Origin': final_domain,
                }, timeout=5)
                if check.status_code == 200 and '#EXTM3U' in check.text:
                    best_url = candidate
                    break
            except Exception:
                continue
        if best_url:
            try:
                import xbmc as _xbmc
                _xbmc.log(f"[embedsportstop] POST failed, falling back to HTML m3u8: {best_url}", _xbmc.LOGWARNING)
            except Exception:
                pass
            return best_url

    # All methods failed
    if body:
        raise ValueError(f"EmbedSportStop failed: POST path={fetch_path}, status={response.status_code}: {body}")
    raise ValueError(f"Missing access-control key in response headers\n{response.headers}\nBody: {body}")