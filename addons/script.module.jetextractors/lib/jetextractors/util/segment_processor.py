import gzip
import zlib


PNG_SIG = b'\x89PNG\r\n\x1a\n'
WEBP_SIG = b'RIFF'
WEBP_LABEL = b'WEBP'


def _strip_png(data: bytes) -> bytes:
    """Remove a PNG wrapper that precedes the actual MPEG-TS payload."""
    if not data.startswith(PNG_SIG):
        return _strip_webp(data)
    offset = len(PNG_SIG)
    chunk_count = 0
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            break
        chunk_count += 1
        if chunk_type == b'IEND':
            video_start = chunk_end
            if video_start < len(data):
                return data[video_start:]
            return b''
        offset = chunk_end
    return data


def _strip_webp(data: bytes) -> bytes:
    """Remove a WebP wrapper that precedes the actual MPEG-TS payload."""
    if not data.startswith(WEBP_SIG) or len(data) < 12 or data[8:12] != WEBP_LABEL:
        return data
    # RIFF header: 4 bytes "RIFF" + 4 bytes file size + 4 bytes "WEBP"
    file_size = int.from_bytes(data[4:8], "little")
    # TS sync byte is 0x47; scan after RIFF header for first 0x47
    search_start = 12
    search_end = min(12 + file_size, len(data))
    # Also look further in case RIFF size is wrong
    search_end = max(search_end, min(len(data), 8192))
    for i in range(search_start, search_end):
        if data[i] == 0x47 and i + 188 <= len(data):
            # Verify TS sync pattern (0x47 appears every 188 bytes)
            if i + 376 <= len(data) and data[i + 188] == 0x47:
                return data[i:]
    return data


def _decompress(data: bytes) -> bytes:
    """Best-effort gzip/zlib decompression."""
    try:
        if data[:2] == b'\x1f\x8b':
            return gzip.decompress(data)
        elif data[:2] in (b'\x78\x9c', b'\x78\x01', b'\x78\xda'):
            return zlib.decompress(data)
    except Exception:
        pass
    return data


def _rewrite_png_to_ts(url: str) -> str:
    result = url.replace(".png", ".ts").replace(".PNG", ".TS")
    idx = result.rfind(".image")
    if idx != -1:
        result = result[:idx] + ".ts" + result[idx + 6:]
    return result


def _rewrite_png_to_image(url: str) -> str:
    """Convert .png extension to .image so the CDN serves WebP instead of 403."""
    lower = url.lower()
    idx = lower.rfind(".png")
    if idx != -1:
        return url[:idx] + ".image" + url[idx + 4:]
    return url


def _rewrite_ts_to_png(url: str) -> str:
    if ".ts?" in url or ".TS?" in url:
        return url.replace(".ts?", ".png?").replace(".TS?", ".png?")
    if url.endswith(".ts") or url.endswith(".TS"):
        return url[:-3] + ".png"
    return url
