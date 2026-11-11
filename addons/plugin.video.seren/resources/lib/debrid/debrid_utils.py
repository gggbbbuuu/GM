"""Shared utilities for debrid service modules.

Provides:
- Cached IP lookup for CDN passthrough
- Smart auto-delete runtime helpers
"""

import json
import time

from resources.lib.modules.globals import g

# ─── IP Passthrough (cached) ────────────────────────────────────────────────

_cached_ip = None
_cached_ip_time = 0
_IP_CACHE_TTL = 300  # 5 minutes


def get_user_ip():
    """Fetch the user's public IP, cached for 5 minutes.
    Used by debrid services that support IP passthrough for CDN routing."""
    global _cached_ip, _cached_ip_time

    now = time.time()
    if _cached_ip and (now - _cached_ip_time) < _IP_CACHE_TTL:
        return _cached_ip

    try:
        import requests
        resp = requests.get("https://api.ipify.org", timeout=3)
        if resp.ok and resp.text:
            _cached_ip = resp.text.strip()
            _cached_ip_time = now
            return _cached_ip
    except Exception:
        pass

    return _cached_ip  # Return stale cache on failure, or None


# ─── Smart Auto-Delete Helpers ──────────────────────────────────────────────

_PENDING_KEY = "debrid.pending_cleanup"


def store_pending_cleanup(service, item_id, delete_method_name="delete_torrent"):
    """Store a debrid item for potential post-playback cleanup.

    Args:
        service: debrid service name ('real_debrid', 'premiumize', 'all_debrid', 'torbox')
        item_id: the torrent/transfer/magnet ID to track
        delete_method_name: name of the delete method on the debrid class
    """
    data = json.dumps({
        "service": service,
        "item_id": str(item_id),
        "delete_method": delete_method_name,
    })
    g.set_runtime_setting(_PENDING_KEY, data)
    g.log(f"Smart delete: stored pending cleanup for {service} id={item_id}", "info")


def get_pending_cleanup():
    """Retrieve and clear the pending cleanup info.

    Returns dict with {service, item_id, delete_method} or None."""
    raw = g.get_runtime_setting(_PENDING_KEY)
    if not raw:
        return None
    # Clear immediately so it doesn't fire twice
    g.set_runtime_setting(_PENDING_KEY, "")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def discard_pending_cleanup(reason=""):
    """Drop the pending cleanup record without acting on it.

    The watchdog calls this before it resolves each source and when it gives up, so a record left by a source
    that failed (stalled, errored, failed verification) cannot be claimed by a later playback of another source."""
    raw = g.get_runtime_setting(_PENDING_KEY)
    if not raw:
        return
    g.set_runtime_setting(_PENDING_KEY, "")
    g.log(f"Smart delete: discarded the pending cleanup record ({reason or 'no reason given'})", "debug")


_CLAIMS_KEY = "debrid.cleanup_claims"
_CLAIM_MAX_AGE = 12 * 3600  # a claim left behind by a playback that never ended stops counting after 12 hours


def _load_claims():
    raw = g.get_runtime_setting(_CLAIMS_KEY)
    claims = raw if isinstance(raw, list) else []
    cutoff = time.time() - _CLAIM_MAX_AGE
    return [c for c in claims if isinstance(c, dict) and c.get("ts", 0) >= cutoff]


def claim_pending_cleanup(token):
    """Take the pending cleanup record for the playback that just started and register it as an active claim.

    The pending slot is a single global value, so a playback must take its record when it starts: the next
    episode's source resolves (and overwrites the slot) before the previous episode's end callback runs.
    Returns the claimed record (or None) - the caller keeps it and later calls release_cleanup_claim()."""
    pending = get_pending_cleanup()
    if not pending:
        return None
    claims = _load_claims()
    claims.append(
        {"token": token, "service": pending.get("service"), "item_id": pending.get("item_id"), "ts": time.time()}
    )
    g.set_runtime_setting(_CLAIMS_KEY, claims)
    return pending


def release_cleanup_claim(token):
    """Remove the claim a playback registered with claim_pending_cleanup()."""
    claims = [c for c in _load_claims() if c.get("token") != token]
    g.set_runtime_setting(_CLAIMS_KEY, claims)


def cleanup_item_in_use(service, item_id):
    """True when another playback has claimed this item, or a resolved-but-not-yet-started playback has it pending.

    Premiumize (and others) hand back the same transfer for every episode of a season pack, so deleting it when
    one episode ends would pull the stream out from under the next one."""
    item_id = str(item_id)
    if any(c.get("service") == service and str(c.get("item_id")) == item_id for c in _load_claims()):
        return True
    raw = g.get_runtime_setting(_PENDING_KEY)
    if raw:
        try:
            nxt = json.loads(raw)
            return nxt.get("service") == service and str(nxt.get("item_id")) == item_id
        except (json.JSONDecodeError, TypeError, AttributeError):
            return False
    return False
