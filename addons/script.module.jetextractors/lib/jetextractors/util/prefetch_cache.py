import threading
from urllib.parse import urlparse

import requests
import xbmc
from ..tools import debug_log
from .tls_adapter import _ProxyTLSAdapter


def _seg_cache_get(entry, url):
    cache = entry.get("seg_cache")
    if not cache:
        return None
    return cache.get(url)


def _seg_cache_put(entry, url, data, content_type, cap=4):
    cache = entry.setdefault("seg_cache", {})
    if url not in cache:
        while len(cache) >= cap:
            cache.pop(next(iter(cache)))
    cache[url] = (data, content_type)


def _seg_inflight_register(entry, url):
    """Register an in-flight segment download for *url*.

    Returns None when the CALLER owns the download (and must later call
    _seg_inflight_done), or an Event to wait on when another thread already
    owns it.
    """
    inflight = entry.setdefault("seg_inflight", {})
    ev = inflight.get(url)
    if ev is not None:
        return ev
    ev = threading.Event()
    inflight[url] = ev
    return None


def _seg_inflight_done(entry, url):
    inflight = entry.get("seg_inflight")
    if inflight is not None:
        ev = inflight.pop(url, None)
        if ev is not None:
            ev.set()


def _prefetch_segment(proxy, entry, url):
    """Background download of one segment into the token's cache."""
    ev = _seg_inflight_register(entry, url)
    if ev is not None:
        return  # someone else (live handler or another prefetcher) owns it
    try:
        if proxy._abort.is_set() or _seg_cache_get(entry, url) is not None:
            return
        headers = entry.get("headers") or {}
        seg_headers = dict(proxy.default_headers)
        seg_headers.update(headers)
        if proxy.upstream_user_agent:
            seg_headers["User-Agent"] = proxy.upstream_user_agent
        seg_headers.setdefault("Accept", "*/*")
        if not proxy.upstream_keep_alive:
            seg_headers.setdefault("Connection", "close")

        if proxy.segment_strip_origin:
            target_domain = urlparse(url).netloc
            manifest_domain = urlparse(entry["url"]).netloc
            if target_domain and manifest_domain and target_domain != manifest_domain:
                seg_headers.pop("Origin", None)
                seg_headers.pop("Referer", None)

        client = entry.get("session")
        if client is None:
            client = requests
            if proxy.browser_tls:
                client = requests.Session()
                client.verify = False
                client.mount("https://", _ProxyTLSAdapter())
        try:
            resp = client.get(url, headers=seg_headers, timeout=(3, 15), stream=True, allow_redirects=True)
        except Exception as e:
            debug_log(f"[{proxy.name}] Prefetch request failed for {url}: {e}", xbmc.LOGDEBUG)
            return
        if resp.status_code not in (200, 206):
            debug_log(f"[{proxy.name}] Prefetch got status {resp.status_code} for {url}", xbmc.LOGDEBUG)
            resp.close()
            return
        data = b""
        try:
            for chunk in resp.iter_content(chunk_size=proxy.chunk_size):
                if proxy._abort.is_set():
                    return
                if chunk:
                    data += chunk
                    if len(data) > proxy.max_segment_size:
                        break
        except Exception as e:
            debug_log(f"[{proxy.name}] Prefetch download error for {url}: {e}", xbmc.LOGDEBUG)
            return
        finally:
            resp.close()
        if proxy._abort.is_set():
            return
        ctype = resp.headers.get("Content-Type", "")
        _seg_cache_put(entry, url, data, ctype)
        debug_log(f"[{proxy.name}] Prefetched segment: {len(data)} bytes ({url})", xbmc.LOGINFO)
    finally:
        _seg_inflight_done(entry, url)
