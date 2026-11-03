"""Shared taifood/indianservers token mint (embedsports network protocol).

POST https://taifood-blog.asia/fetch with an application/octet-stream
protobuf payload (field 1 = mint key) and the network's `indians` API-key
header returns a ChaCha20-Poly1305-encrypted FRESH
*.indianservers.st/secure/ m3u8 URL.

Used by embedhd_api.py (rockylive events; key = numeric event id or slug)
and embedsport2.py (api.ppv.st streams; key = the iframe path after
/embed/ == the API's uri_name, including `_540p` quality suffixes and
multi-path substreams like `cfb/<date>/<event>/skycast`).

Tokens are short-window/stateful: never cache a minted URL across
resolves; re-mint on every resolve and via the proxy refresh callback.
Hostnames rotate per mint (bharat., netanyahu., vishnu. ...) - accept any
*.indianservers.st. Playlist bodies carry a cosmetic `## IRON DOME`
comment.

The protobuf/crypto primitives (_field/_parse_response/_obfuscation_decode
/CRYPTO_LIB) live in embedsportstop.py - this module is the single
HTTP+decrypt implementation of the issuer on top of them, so the indians
key rotates in ONE place.
"""
import base64
from typing import Optional
from urllib.parse import urlparse

import requests
import xbmc

from .embedsportstop import (
    _field, _parse_response, _obfuscation_decode, CRYPTO_LIB,
)
from ..models import JetInputstreamFFmpegDirect
from ..tools import debug_log

if CRYPTO_LIB == 'cryptography':
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
else:
    try:
        from Cryptodome.Cipher import ChaCha20_Poly1305
    except Exception:
        from Crypto.Cipher import ChaCha20_Poly1305

MINT_HOST = "https://taifood-blog.asia"
MINT_HOST_NETLOC = "taifood-blog.asia"
# Network-wide API key; also hardcoded in util/embedsportstop.py (same
# value; if it rotates, update both).
INDIANS_KEY = "18866ebec06934ba03ad3387e9fc9ebfbf2ea2d0e9305c86797b66c62ee4f8a5"

# indianservers.st rejects Chrome desktop UA + close-per-request segment
# fetches with 403. Mirror streamed.py: Samsung TV UA so segment requests
# look like a real TV player.
STREAMED_TV_UA = (
    "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) SamsungBrowser/16.0 TV Safari/537.36"
)

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)


def ffmpegdirect_live() -> JetInputstreamFFmpegDirect:
    """inputstream.ffmpegdirect in stream_mode='live' (NOT the 'timeshift'
    default). indianservers.st /secure/ URLs use rotating short-lived
    tokens and the CDN 403s segment fetches that stall behind the
    timeshift read thread (see ISSUE_FREEZE.md / streamed.py). Live mode
    keeps segment requests flowing.
    """
    return JetInputstreamFFmpegDirect(
        manifest_type="hls", is_realtime_stream=True, stream_mode="live"
    )


def is_taifood_url(url: str) -> bool:
    try:
        return urlparse(url).netloc == MINT_HOST_NETLOC
    except Exception:
        return False


def uri_name_from_iframe(iframe_url: str) -> Optional[str]:
    """Mint key = the iframe URL path after /embed/ (== the API's
    uri_name, including _540p quality suffixes and multi-path
    substreams)."""
    try:
        path = urlparse(iframe_url).path
    except Exception:
        return None
    marker = "/embed/"
    idx = path.find(marker)
    if idx < 0:
        return None
    key = path[idx + len(marker):].strip("/")
    return key or None


def stream_headers() -> dict:
    return {
        "User-Agent": STREAMED_TV_UA,
        "Referer": f"{MINT_HOST}/",
    }


def mint(event_ref: str, timeout: int = 10) -> Optional[str]:
    """Ask the network issuer for a fresh indianservers stream URL.

    event_ref: mint key - embedsport2 uri_name (e.g. 'nfl-network_540p',
    'cfb/2026-10-31/nd-navy/skycast') or embedhd numeric event id/slug;
    both are accepted as protobuf field 1.
    """
    payload = _field(1, str(event_ref).encode())
    headers = {
        "indians": INDIANS_KEY,
        "content-type": "application/octet-stream",
        "origin": MINT_HOST,
        "referer": f"{MINT_HOST}/",
        "user-agent": DESKTOP_UA,
        "x-requested-with": "XMLHttpRequest",
    }
    try:
        r = requests.post(f"{MINT_HOST}/fetch", data=payload,
                          headers=headers, timeout=timeout, verify=False)
    except Exception as e:
        debug_log(f"[taifood_mint] mint request failed for {event_ref}: {e}", xbmc.LOGWARNING)
        return None
    if r.status_code != 200:
        debug_log(f"[taifood_mint] mint HTTP {r.status_code} for {event_ref}", xbmc.LOGWARNING)
        return None
    ac = r.headers.get('access-control-expose-headers')
    key = r.headers.get(ac) if ac else None
    if not key:
        debug_log(f"[taifood_mint] mint response missing cipher key for {event_ref}", xbmc.LOGWARNING)
        return None
    try:
        cipher_bytes = _parse_response(r.content)
        raw = base64.b64decode(_obfuscation_decode(cipher_bytes) + b'=' * 3)
        nonce, ct = raw[:12], raw[12:]
        if CRYPTO_LIB == 'cryptography':
            stream_url = ChaCha20Poly1305(key.encode('utf-8')).decrypt(
                nonce, ct[:-16], ct[-16:]).decode('utf-8').strip()
        else:
            cipher = ChaCha20_Poly1305.new(key=key.encode('utf-8'), nonce=nonce)
            stream_url = cipher.decrypt_and_verify(ct[:-16], ct[-16:]).decode('utf-8').strip()
    except Exception as e:
        debug_log(f"[taifood_mint] mint decrypt failed for {event_ref}: {e}", xbmc.LOGWARNING)
        return None
    if not stream_url.startswith("http") or ".m3u8" not in stream_url:
        debug_log(f"[taifood_mint] mint returned non-playlist for {event_ref}: {stream_url[:80]}", xbmc.LOGWARNING)
        return None
    debug_log(f"[taifood_mint] Minted stream for {event_ref}: {stream_url[:120]}", xbmc.LOGINFO)
    return stream_url


def verify_m3u8(url: str) -> bool:
    """Samsung TV UA + taifood referer #EXTM3U check on a minted URL."""
    try:
        r = requests.get(url, headers=stream_headers(), timeout=12, verify=False)
        ok = r.status_code == 200 and b'#EXTM3U' in r.content[:4096]
        if not ok:
            debug_log(f"[taifood_mint] minted playlist verify failed (HTTP {r.status_code})", xbmc.LOGWARNING)
        return ok
    except Exception as e:
        debug_log(f"[taifood_mint] minted playlist verify error: {e}", xbmc.LOGDEBUG)
        return False
