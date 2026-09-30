import base64
import binascii
import re
import xbmc
from urllib.parse import urljoin, quote

from ..tools import debug_log
from .manifest_rewriter import _is_variant_playlist
from .segment_processor import _scan_for_ts_sync


def _hex_to_base64url(value: str) -> str:
    return base64.b64encode(binascii.unhexlify(value)).decode("utf-8").replace("+", "-").replace("/", "_").replace("=", "")


def _strip_png_wrapper(data: bytes) -> bytes:
    PNG_SIG = b'\x89PNG\r\n\x1a\n'
    if not data.startswith(PNG_SIG):
        return data
    offset = len(PNG_SIG)
    chunk_count = 0
    idat_data = b''
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            debug_log(f"[XYZ] PNG chunk {chunk_type} exceeds data length, aborting strip", xbmc.LOGWARNING)
            break
        chunk_count += 1
        if chunk_type == b'IEND':
            video_start = chunk_end
            if video_start < len(data):
                debug_log(f"[XYZ] PNG strip found IEND after {chunk_count} chunks, video data at offset {video_start}", xbmc.LOGINFO)
                return data[video_start:]
            debug_log(f"[XYZ] PNG IEND at end of file, no trailing data — scanning for TS sync byte", xbmc.LOGINFO)
            # TS data may be embedded inside IDAT chunks
            if idat_data:
                result = _scan_for_ts_sync(idat_data, 0)
                if result:
                    return result
            result = _scan_for_ts_sync(data, len(PNG_SIG))
            if result:
                return result
            # Try zlib-decompressing collected IDAT data
            if idat_data:
                try:
                    import zlib
                    decompressed = zlib.decompress(idat_data)
                    result = _scan_for_ts_sync(decompressed, 0)
                    if result:
                        return result
                except Exception:
                    pass
            debug_log(f"[XYZ] No TS sync byte found in PNG data", xbmc.LOGWARNING)
            return b''
        if chunk_type == b'IDAT':
            idat_data += data[offset + 8:chunk_end - 4]
        offset = chunk_end
    debug_log(f"[XYZ] PNG IEND not found after {chunk_count} chunks, scanning for TS sync byte", xbmc.LOGWARNING)
    result = _scan_for_ts_sync(data, len(PNG_SIG))
    if result:
        return result
    return data


def _rewrite_m3u8_body(body: str, token: str, port: int, base_url: str = "") -> str:
    def _rewrite_url(url: str) -> str:
        if base_url and not url.startswith("http://") and not url.startswith("https://"):
            url = urljoin(base_url, url)
        return f"http://127.0.0.1:{port}/xyz/seg/{token}/{quote(url, safe='')}"

    rewritten = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        def _rewrite_uri_attr(m):
            uri = m.group(2)
            if uri.startswith("data:"):
                return m.group(0)
            if base_url and not uri.startswith("http://") and not uri.startswith("https://"):
                uri = urljoin(base_url, uri)
            return m.group(1) + f"http://127.0.0.1:{port}/xyz/seg/{token}/{quote(uri, safe='')}" + m.group(3)
        line = re.sub(
            r'(URI=")([^"]+)(")',
            _rewrite_uri_attr,
            line,
        )
        if stripped.startswith("#"):
            rewritten.append(line)
            continue
        rewritten.append(_rewrite_url(stripped))
    return "\n".join(rewritten) + "\n"


def _best_quality_master(body: str) -> str:
    lines = body.splitlines()
    audio_tags = []
    header_lines = []
    variants = []

    i = 0
    in_variants = False
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#EXT-X-MEDIA"):
            audio_tags.append(stripped)
            i += 1
            continue
        if stripped.startswith("#EXT-X-STREAM-INF"):
            in_variants = True
            inf_line = stripped
            bw = 0
            m = re.search(r'BANDWIDTH=(\d+)', stripped)
            if m:
                bw = int(m.group(1))
            j = i + 1
            while j < len(lines):
                url_line = lines[j].strip()
                if url_line and not url_line.startswith("#"):
                    variants.append((bw, inf_line, url_line))
                    i = j + 1
                    break
                j += 1
            else:
                i += 1
            continue
        if not in_variants:
            header_lines.append(lines[i])
        i += 1

    if not variants:
        return body

    def _score(item):
        bw, inf, _url = item
        codecs = ""
        cm = re.search(r'CODECS="([^"]+)"', inf)
        if cm:
            codecs = cm.group(1).lower()
        return bw + (10000000 if "mp4a" in codecs else 0)

    variants.sort(key=_score, reverse=True)
    best_bw, best_inf, best_url = variants[0]
    audio_group = ""
    gm = re.search(r'AUDIO="([^"]+)"', best_inf)
    if gm:
        audio_group = gm.group(1)
        matched = [t for t in audio_tags if f'GROUP-ID="{audio_group}"' in t]
        if matched:
            audio_tags = matched[:1]
    debug_log(f"[XYZ] _best_quality_master: keeping best variant bw={best_bw}, audio={audio_group or 'all'}, "
              f"dropping {len(variants) - 1} lower variants", xbmc.LOGINFO)

    result = header_lines[:]
    for at in audio_tags:
        result.append(at)
    result.append(best_inf)
    result.append(best_url)
    return "\n".join(result) + "\n"


_WIDEVINE_KS = "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"


def _apply_sling_clearkey(body: str, license_key: str) -> str:
    if not body or not license_key or ":" not in license_key:
        return body
    if "#EXT-X-KEY" not in body:
        return body
    kid_hex, key_hex = license_key.split(":", 1)
    kid_hex = re.sub(r"[^a-f0-9]", "", kid_hex.lower())
    key_hex = re.sub(r"[^a-f0-9]", "", key_hex.lower())
    if len(kid_hex) != 32 or len(key_hex) != 32:
        return body
    # ISA 21.5 only copies KEYID when KEYFORMAT is "identity" or Widevine.
    # A ClearKey UUID leaves the KID empty and decryption fails.
    # identity + data URI of the 16-byte KID sets defaultKID; the key comes from drm_legacy.
    kid_b64 = base64.b64encode(binascii.unhexlify(kid_hex)).decode("ascii")
    new_key = (
        '#EXT-X-KEY:METHOD=SAMPLE-AES-CTR,'
        f'URI="data:text/plain;base64,{kid_b64}",'
        f"KEYID=0x{kid_hex},"
        'KEYFORMAT="identity",'
        'KEYFORMATVERSIONS="1"'
    )
    out = []
    changed = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#EXT-X-KEY") and "METHOD=NONE" not in stripped and (
            _WIDEVINE_KS in stripped or "SAMPLE-AES" in stripped
        ):
            out.append(new_key)
            changed = True
        else:
            out.append(line)
    if not changed:
        return body
    debug_log("[XYZ] Rewrote Widevine EXT-X-KEY to ClearKey", xbmc.LOGINFO)
    return "\n".join(out) + "\n"


def _strip_riff_wrapper(data: bytes) -> bytes:
    """Strip a RIFF/WebP wrapper from TS segment data.

    Some dlhd.net streams (MLB, etc.) now wrap TS segments in RIFF/WebP
    containers.  The RIFF header declares only the thumbnail portion
    (e.g. 28 bytes), and the actual TS data begins immediately after.

    Uses the same scanning approach as ``segment_processor._strip_webp`` –
    looks for the TS sync byte (0x47) after the RIFF header and verifies
    the 188-byte sync pattern rather than trusting the declared file size.
    """
    RIFF_SIG = b'RIFF'
    if not data.startswith(RIFF_SIG) or len(data) < 12:
        return data
    file_size = int.from_bytes(data[4:8], "little")
    search_start = 12
    search_end = min(12 + file_size, len(data))
    search_end = max(search_end, min(len(data), 8192))
    for i in range(search_start, search_end):
        if data[i] == 0x47 and i + 188 <= len(data):
            if i + 376 <= len(data) and data[i + 188] == 0x47:
                debug_log(
                    f"[XYZ] Stripped RIFF/WebP wrapper: {len(data)} -> {len(data) - i} bytes "
                    f"(sync at offset {i})",
                    xbmc.LOGINFO,
                )
                return data[i:]
    debug_log(
        f"[XYZ] RIFF header found but no TS sync byte detected, returning raw ({len(data)} bytes)",
        xbmc.LOGWARNING,
    )
    return data


def _parse_iso_duration(iso: str) -> float:
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", iso or "")
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)
