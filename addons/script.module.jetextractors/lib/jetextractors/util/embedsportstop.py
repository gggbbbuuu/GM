import requests
import base64
from urllib.parse import urlparse
import platform

def is_xbox():
    return 'Xbox' in platform.system()

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

def get_embedsportstop_stream(url: str) -> str:
    domain = f"https://{urlparse(url).netloc}"
    headers = {
        'indians': '18866ebec06934ba03ad3387e9fc9ebfbf2ea2d0e9305c86797b66c62ee4f8a5',
        'content-type': 'application/octet-stream',
        'origin': domain,
        'referer': url,
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }
    
    # Disable SSL verification only on Xbox
    if is_xbox():
        response = requests.post(
            domain + '/fetch',
            data=_build_payload(url),
            headers=headers,
            verify=False
        )
    else:
        response = requests.post(
            domain + '/fetch',
            data=_build_payload(url),
            headers=headers
        )
    
    ac = response.headers.get('access-control-expose-headers')
    key = response.headers.get(ac)
    if not key:
        raise ValueError(f"Missing access-control key in response headers\n{response.headers}")

    b64_cipher = _parse_response(response.content)
    decoded = _obfuscation_decode(b64_cipher)
    raw = base64.b64decode(decoded + b'=' * (-len(decoded) % 4))
    nonce = raw[:12]
    ct_with_tag = raw[12:]

    # Decrypt using the library that was successfully imported
    if CRYPTO_LIB == 'cryptography':
        # Xbox: uses cryptography module (built into Kodi 21)
        cipher = ChaCha20Poly1305(key.encode('utf-8'))
        return cipher.decrypt(nonce, ct_with_tag[:-16], ct_with_tag[-16:]).decode('utf-8').strip()
    else:
        # All other platforms: uses PyCryptodome or PyCrypto
        cipher = ChaCha20_Poly1305.new(key=key.encode('utf-8'), nonce=nonce)
        return cipher.decrypt_and_verify(ct_with_tag[:-16], ct_with_tag[-16:]).decode('utf-8').strip()