import gzip
import zlib


PNG_SIG = b'\x89PNG\r\n\x1a\n'
WEBP_SIG = b'RIFF'
WEBP_LABEL = b'WEBP'

# Framing headers written into the decoded pixel bytes of the "TikTok-style"
# PNG wrapper. TIKTIKPX is 8 bytes + big-endian uint32 gzip length + gzip;
# the other two are 10-byte magics with no length field.
TIKTIK_PIXELS = bytes([84, 73, 75, 84, 73, 75, 80, 88])   # b'TIKTIKPX'
TIKTIK_RAW = bytes([84, 73, 75, 84, 73, 75, 84, 82, 65, 87])  # b'TIKTIKTRAW'
TIKTIK_GZ = bytes([84, 73, 75, 84, 73, 75, 84, 83, 71, 90])   # b'TIKTIKTSGZ'
GZIP_MAGIC = b'\x1f\x8b'


def _ts_from_gzip_blob(blob: bytes) -> bytes:
    """Gunzip ``blob`` and return it only if the result is MPEG-TS."""
    if len(blob) < 2 or blob[:2] != GZIP_MAGIC:
        return b''
    try:
        ts = gzip.decompress(blob)
    except Exception:
        return b''
    if len(ts) < 188 or ts[0] != 0x47:
        return b''
    return ts


def _unwrap_tiktik_pixels(pixels: bytes) -> bytes:
    """Recover the MPEG-TS from ``TIKTIK``-framed pixel bytes.

    Three header shapes are used by this CDN family:

    * ``TIKTIKPX``  - 8-byte magic, big-endian uint32 gzip length, gzip blob
    * ``TIKTIKTRAW`` - 10-byte magic, raw MPEG-TS filling the rest of the image
    * ``TIKTIKTSGZ`` - 10-byte magic, gzip stream filling the rest of the image

    Returns b'' when the pixels are not framed this way.
    """
    if pixels[:8] == TIKTIK_PIXELS:
        length = int.from_bytes(pixels[8:12], 'big')
        if 0 < length <= len(pixels) - 12:
            ts = _ts_from_gzip_blob(pixels[12:12 + length])
            if ts:
                return ts
        return b''
    if pixels[:10] == TIKTIK_RAW:
        ts = pixels[10:]
        if len(ts) >= 188 and ts[0] == 0x47:
            return ts[:len(ts) - (len(ts) % 188)]
        return b''
    if pixels[:10] == TIKTIK_GZ:
        return _ts_from_gzip_blob(pixels[10:])
    return b''


def _scan_for_ts_sync(data: bytes, search_start: int = 0, min_packets: int = 2) -> bytes:
    """Scan for the MPEG-TS sync byte (0x47), verifying the 188-byte packet
    pattern by checking that ``min_packets`` consecutive 0x47 sync bytes are
    present at 188-byte intervals.

    Uses ``bytes.find`` (C-level) for speed over large payloads.

    ``min_packets`` defaults to 2 for backwards compatibility, but callers
    scanning *unverified* data (compressed image payloads, encrypted blobs)
    must pass a higher value (8 or more) — a single 0x47/0x47 pair occurs by
    chance roughly every 250 KB of random data, which previously caused
    compressed PNG payload to be mistaken for MPEG-TS.
    """
    if min_packets < 2:
        min_packets = 2
    if len(data) < 188 * min_packets + 1:
        return b''
    limit = len(data) - 188 * min_packets
    while search_start < limit:
        idx = data.find(b'\x47', search_start, limit)
        if idx == -1:
            return b''
        ok = True
        for k in range(1, min_packets + 1):
            if data[idx + 188 * k] != 0x47:
                ok = False
                break
        if ok:
            return data[idx:]
        search_start = idx + 1
    return b''


def _swar_add_bytes(a: bytes, b: bytes) -> bytes:
    """Byte-wise addition (mod 256) of two equal-length byte strings.

    SWAR (SIMD-within-a-register) trick using Python big integers, so a whole
    1.5 KB row can be filtered in a handful of C-level operations instead of a
    per-byte Python loop. The 0x7f masks keep each byte's sum below 0x100 so
    no carry leaks into the neighbouring byte.
    """
    n = len(a)
    if n == 0 or n != len(b):
        return b''
    ia = int.from_bytes(a, 'big')
    ib = int.from_bytes(b, 'big')
    mask = int.from_bytes(b'\x7f' * n, 'big')
    high = int.from_bytes(b'\x80' * n, 'big')
    return (((ia & mask) + (ib & mask)) ^ ((ia ^ ib) & high)).to_bytes(n, 'big')


def _prefix_sum_plane(plane: bytes) -> bytes:
    """Cumulative byte-wise sum (mod 256) of a single interleaved plane."""
    n = len(plane)
    if n == 0:
        return plane
    total = int.from_bytes(plane, 'big')
    raw = total.to_bytes(n, 'big')
    step = 1
    while step < n:
        shifted = (total >> (8 * step)).to_bytes(n, 'big')
        raw = _swar_add_bytes(raw, shifted)
        total = int.from_bytes(raw, 'big')
        step <<= 1
    return raw


def _png_bpp(bit_depth: int, color_type: int) -> int:
    """Bytes per pixel for a non-interlaced PNG, or 0 if unsupported."""
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 0)
    if not channels:
        return 0
    if color_type == 3 or bit_depth not in (8, 16):
        # Palette indices / sub-byte depths do not store a raw byte stream.
        return 0
    return channels * (bit_depth // 8)


def _unfilter_scanlines(inflated: bytes, height: int, stride: int, bpp: int) -> bytes:
    """Reconstruct PNG pixel bytes from inflated (filtered) scanlines.

    Implements the five standard PNG filter types. Filter 0/1/2 use
    slice copies and big-integer arithmetic; filters 3 (Average) and
    4 (Paeth) are inherently sequential and use a per-byte loop, but only
    for the rows that actually use them.
    """
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for row in range(height):
        row_start = row * stride
        if pos + 1 + stride > len(inflated):
            break
        ftype = inflated[pos]
        pos += 1
        raw = inflated[pos:pos + stride]
        pos += stride

        if ftype == 0:
            out[row_start:row_start + stride] = raw
        elif ftype == 1:
            line = bytearray(stride)
            if bpp == 1:
                line[:] = _prefix_sum_plane(raw)
            else:
                for c in range(bpp):
                    line[c::bpp] = _prefix_sum_plane(bytes(raw[c::bpp]))
            out[row_start:row_start + stride] = line
        elif ftype == 2:
            out[row_start:row_start + stride] = _swar_add_bytes(raw, bytes(prev))
        else:
            line = bytearray(raw)
            if ftype == 3:
                for x in range(stride):
                    left = line[x - bpp] if x >= bpp else 0
                    line[x] = (line[x] + ((left + prev[x]) >> 1)) & 0xFF
            else:
                for x in range(stride):
                    if x >= bpp:
                        a = line[x - bpp]
                        c = prev[x - bpp]
                    else:
                        a = 0
                        c = 0
                    b = prev[x]
                    p = a + b - c
                    pa = abs(p - a)
                    pb = abs(p - b)
                    pc = abs(p - c)
                    if pa <= pb and pa <= pc:
                        pr = a
                    elif pb <= pc:
                        pr = b
                    else:
                        pr = c
                    line[x] = (line[x] + pr) & 0xFF
            out[row_start:row_start + stride] = line
        prev = out[row_start:row_start + stride]
    return bytes(out)


def _decode_png_image_payload(idat_data: bytes, ihdr: tuple) -> bytes:
    """Decode a PNG whose *pixel bytes* carry the MPEG-TS payload.

    The TikTok-style wrapper used by the ``.sbs``/``premium.hls.st`` premium
    HLS streams (and similar CDN families) is a real PNG image: a 512xN RGB
    image whose filtered scanlines compress a ``TIKTIKPX``-framed, gzipped
    MPEG-TS. The payload is therefore only recoverable after a full PNG
    decode (zlib inflate + scanline un-filtering), and the pixel stream is
    *not* a bare TS — the 0x47 sync bytes found inside it belong to the
    gzip-compressed blob, so scanning pixel bytes for 0x47 yields a
    plausible-looking but badly damaged stream.

    Returns the reconstructed TS, or b'' when the IDAT is not an image
    payload.
    """
    if not idat_data or not ihdr:
        return b''
    width, height, bit_depth, color_type, interlace = ihdr
    bpp = _png_bpp(bit_depth, color_type)
    if not bpp or interlace:
        return b''
    stride = width * bpp
    if height <= 0 or stride <= 0 or stride > 4 * 1024 * 1024:
        return b''
    try:
        inflated = zlib.decompress(idat_data)
    except Exception:
        try:
            inflated = zlib.decompressobj().decompress(idat_data)
        except Exception:
            return b''
    if len(inflated) < (stride + 1) * height:
        return b''
    pixels = _unfilter_scanlines(inflated, height, stride, bpp)
    if bpp == 4:
        # RGBA: drop the alpha plane to reach the RGB stream.
        rgb = bytearray(len(pixels) // 4 * 3)
        rgb[0::3] = pixels[0::4]
        rgb[1::3] = pixels[1::4]
        rgb[2::3] = pixels[2::4]
        pixels = bytes(rgb)
    ts = _unwrap_tiktik_pixels(pixels)
    if ts:
        return ts
    # Fall back to a direct pixel-stream TS (no TIKTIKPX framing).
    return _scan_for_ts_sync(pixels, 0, min_packets=8)


def _strip_png(data: bytes) -> bytes:
    """Remove a PNG wrapper that precedes the actual MPEG-TS payload.

    Handles four wrapping strategies:
    1. TS data appended after the IEND chunk (original format).
    2. TS data embedded in the *pixel data* of a real PNG image
       (TikTok-style wrapping: zlib-compressed IDAT scanlines that must be
       un-filtered to recover the TS byte stream).
    3. TS data embedded as raw bytes inside IDAT chunks
       (PNG used as a plain container, IEND at the end with no trailing data).
    4. TS data inside a zlib stream that is not a valid image layout.
    """
    if not data.startswith(PNG_SIG):
        return _strip_webp(data)
    offset = len(PNG_SIG)
    idat_data = b''
    ihdr = None
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            break
        if chunk_type == b'IEND':
            video_start = chunk_end
            if video_start < len(data):
                return data[video_start:]
            # No data after IEND — TS payload may be inside the IDAT image.
            return _extract_ts_from_idat(data, idat_data, ihdr)
        if chunk_type == b'IDAT':
            idat_data += data[offset + 8:chunk_end - 4]
        elif chunk_type == b'IHDR' and length >= 13 and ihdr is None:
            ihdr = (
                int.from_bytes(data[offset + 8:offset + 12], "big"),   # width
                int.from_bytes(data[offset + 12:offset + 16], "big"),  # height
                data[offset + 16],                                     # bit depth
                data[offset + 17],                                     # color type
                data[offset + 20],                                     # interlace
            )
        offset = chunk_end
    return data


def _extract_ts_from_idat(png_data: bytes, idat_data: bytes, ihdr: tuple = None) -> bytes:
    """Try to extract TS data from PNG IDAT chunk content."""
    # Case 1: Real PNG image whose pixel bytes are the TS payload
    if idat_data:
        result = _decode_png_image_payload(idat_data, ihdr)
        if result:
            return result
    # Case 2: Raw TS data inside IDAT (not zlib-compressed)
    if idat_data:
        result = _scan_for_ts_sync(idat_data, 0, min_packets=8)
        if result:
            return result
    # Case 3: TS sync byte somewhere in the raw PNG (outside known chunks)
    result = _scan_for_ts_sync(png_data, len(PNG_SIG), min_packets=8)
    if result:
        return result
    # Case 4: TS data inside zlib-compressed IDAT content that is not a
    # valid image layout
    if idat_data:
        try:
            decompressed = zlib.decompress(idat_data)
            result = _scan_for_ts_sync(decompressed, 0, min_packets=8)
            if result:
                return result
        except Exception:
            pass
    return b''


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
