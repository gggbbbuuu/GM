"""Backward-compatible wrapper around the universal stream proxy.

New extractors should import from jetextractors.util.stream_proxy directly.
This module keeps the old get_proxy(name, default_headers) API working.
"""
import threading

from .stream_proxy import StreamProxy, get_stream_proxy


class PngProxy:
    """Thin wrapper that behaves like the original PngProxy."""

    def __init__(self, name: str, default_headers: dict):
        self.name = name
        self.default_headers = default_headers
        self._proxy = get_stream_proxy(
            name,
            default_headers,
            options={
                "strip_png": True,
                "manifest_png_to_ts": True,
                "fetch_png_segments": False,
                "cache_manifest": True,
                "manifest_ttl": 2.0,
            },
        )

    def get_proxy_url(self, upstream_url: str, headers: dict = None) -> str:
        return self._proxy.get_proxy_url(upstream_url, headers)

    def shutdown(self):
        self._proxy.shutdown()


# Global instances per extractor name to avoid spawning multiple servers
_proxy_instances = {}
_proxy_lock = threading.Lock()


def get_proxy(name: str, default_headers: dict) -> PngProxy:
    with _proxy_lock:
        if name not in _proxy_instances:
            _proxy_instances[name] = PngProxy(name, default_headers)
        return _proxy_instances[name]
