import base64
import binascii
import re
import xbmc
from urllib.parse import urljoin, quote

from ..tools import debug_log
from .manifest_rewriter import _is_variant_playlist


def _hex_to_base64url(value: str) -> str:
    return base64.b64encode(binascii.unhexlify(value)).decode("utf-8").replace("+", "-").replace("/", "_").replace("=", "")


def _strip_png_wrapper(data: bytes) -> bytes:
    PNG_SIG = b'\x89PNG\r\n\x1a\n'
    if not data.startswith(PNG_SIG):
        return data
    offset = len(PNG_SIG)
    chunk_count = 0
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
            debug_log(f"[XYZ] PNG IEND at end of file, no video data", xbmc.LOGWARNING)
            return b''
        offset = chunk_end
    debug_log(f"[XYZ] PNG IEND not found after {chunk_count} chunks, returning raw data", xbmc.LOGWARNING)
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

    variants.sort(key=lambda x: x[0], reverse=True)
    best_bw, best_inf, best_url = variants[0]
    debug_log(f"[XYZ] _best_quality_master: keeping best variant bw={best_bw}, "
              f"dropping {len(variants) - 1} lower variants", xbmc.LOGINFO)

    result = header_lines[:]
    for at in audio_tags:
        result.append(at)
    result.append(best_inf)
    result.append(best_url)
    return "\n".join(result) + "\n"


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
