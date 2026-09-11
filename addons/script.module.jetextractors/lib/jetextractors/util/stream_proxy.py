from .tls_adapter import _ProxyTLSAdapter
from .segment_processor import (
    PNG_SIG,
    WEBP_SIG,
    WEBP_LABEL,
    _strip_png,
    _strip_webp,
    _decompress,
    _rewrite_png_to_ts,
    _rewrite_png_to_image,
    _rewrite_ts_to_png,
)
from .manifest_rewriter import _is_variant_playlist, _resolve_variant_to_media
from .prefetch_cache import (
    _seg_cache_get,
    _seg_cache_put,
    _seg_inflight_register,
    _seg_inflight_done,
    _prefetch_segment,
)
from .proxy_server import (
    StreamProxy,
    get_stream_proxy,
    set_active_proxy,
    get_active_proxy,
    clear_active_proxy,
    abort_active_proxy,
    shutdown_active_proxy,
    build_proxy_url,
    _hashable_options,
)
