import re
import requests
from urllib.parse import urljoin

import xbmc
from ..tools import debug_log


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
