import json
import os
import re
import time
from typing import Callable, Dict, List

import xbmcaddon
import xbmcvfs

from ..tools import debug_log

ADDON = xbmcaddon.Addon(id="script.module.jetextractors")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CONFIG_FILE = os.path.join(ADDON_PATH, "iptv_filters.json")

CONFIG_TTL = 60.0

EXTRACTOR_NAMES = ("telegram_xtream", "homeiptv", "myiptv")

DEFAULT_EXCLUDE_CATEGORIES_CONTAINS = [
    "radio", "netflix", "audio", "conciert", "concert", "película",
    "document", "advent", "comed", "drama", "relig", "western", "fiction",
    "fantasy", "ovie", "classic", "mystery", "action", "lifestyle", "kids",
    "entertain", "bollywood", "animat", "cine", "inema", "film", "imdb",
    "hulu", "netfl", "estreno", "sagas", "release", "thriller", "horror",
    "anime", "karaoke", "musi", "muzi", "xxx", "24/7", "7/24", "vod",
    "adult", "+18", "18+",
]

DEFAULT_EXCLUDE_PREFIXES = [
    "PL", "TR", "EX-YU", "MK", "RO", "HU", "RS", "HR", "BG", "GR",
    "DE", "FR", "IT", "ES", "NL", "PT", "RU", "ARAB", "EU", "ALB",
]

DEFAULT_KEEP_PREFIXES = ["US:", "USA:", "UK:", "EN:", "CA:", "AU:", "NZ:"]

_config_cache: Dict = {}
_config_cache_ts: float = 0.0


def _default_section() -> dict:
    return {
        "enabled": True,
        "exclude_portals": [],
        "exclude_categories": {
            "contains": list(DEFAULT_EXCLUDE_CATEGORIES_CONTAINS),
            "exact": [],
            "regex": [],
        },
        "exclude_channels": {
            "contains": [],
            "exact": [],
            "regex": [],
        },
        "exclude_prefixes": list(DEFAULT_EXCLUDE_PREFIXES),
        "keep_prefixes": list(DEFAULT_KEEP_PREFIXES),
        "keep_bypasses_exclusion": False,
        "drop_empty_names": True,
    }


def _default_config() -> dict:
    cfg = {
        "_comment": (
            "Structured channel filters for TelegramXtream, HomeIPTV, MyIPTV. "
            "Edit this file and save; changes apply within ~60s (or restart Kodi). "
            "Match types: contains = substring, exact = full string, regex = Python regex. "
            "All matching is case-insensitive."
        ),
        "global": {
            "enabled": True,
            "debug": False,
        },
    }
    for name in EXTRACTOR_NAMES:
        cfg[name] = _default_section()
    return cfg


def _ensure_dir():
    if not os.path.exists(ADDON_PATH):
        try:
            os.makedirs(ADDON_PATH, exist_ok=True)
        except Exception as e:
            debug_log(f"[IPTVFilter] Failed to create data dir: {e}")


def _ensure_config_file():
    try:
        _ensure_dir()
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(_default_config(), f, indent=2, ensure_ascii=False)
            debug_log(f"[IPTVFilter] Wrote default filter config: {CONFIG_FILE}")
    except Exception as e:
        debug_log(f"[IPTVFilter] Failed to write default config: {e}")


def _load_raw_config() -> dict:
    global _config_cache, _config_cache_ts
    now = time.time()
    if _config_cache and (now - _config_cache_ts) < CONFIG_TTL:
        return _config_cache
    _ensure_config_file()
    cfg = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        debug_log(f"[IPTVFilter] Failed to read config, using defaults: {e}")
        cfg = _default_config()
    if not isinstance(cfg, dict):
        cfg = _default_config()
    _config_cache = cfg
    _config_cache_ts = now
    return cfg


def invalidate_cache():
    global _config_cache, _config_cache_ts
    _config_cache = {}
    _config_cache_ts = 0.0


def load_filter_config(extractor_name: str) -> dict:
    """Load the merged filter config for one extractor."""
    raw = _load_raw_config()
    global_cfg = raw.get("global", {}) or {}
    if not isinstance(global_cfg, dict):
        global_cfg = {}
    section = raw.get(extractor_name, {}) or {}
    if not isinstance(section, dict):
        section = {}

    merged = _default_section()
    for key, value in section.items():
        if key.startswith("_"):
            continue
        merged[key] = value

    for key in ("exclude_categories", "exclude_channels"):
        base = merged.get(key)
        if not isinstance(base, dict):
            base = {}
        merged[key] = {
            "contains": list(base.get("contains") or []),
            "exact": list(base.get("exact") or []),
            "regex": list(base.get("regex") or []),
        }

    for key in ("exclude_portals", "exclude_prefixes", "keep_prefixes"):
        val = merged.get(key)
        merged[key] = list(val) if isinstance(val, list) else []

    merged["_global"] = global_cfg
    merged["_extractor"] = extractor_name
    return merged


def _norm(text) -> str:
    return (text or "").strip().upper()


def _matches_rules(text_upper: str, rules: dict, label: str, debug: bool, extractor: str) -> bool:
    if not text_upper or not rules:
        return False

    for needle in rules.get("contains") or []:
        n = _norm(needle)
        if n and n in text_upper:
            if debug:
                debug_log(f"[IPTVFilter] {extractor}: {label} contains '{needle}' in '{text_upper[:80]}'")
            return True

    for needle in rules.get("exact") or []:
        n = _norm(needle)
        if n and n == text_upper:
            if debug:
                debug_log(f"[IPTVFilter] {extractor}: {label} exact '{needle}'")
            return True

    for pattern in rules.get("regex") or []:
        try:
            if re.search(pattern, text_upper, re.IGNORECASE):
                if debug:
                    debug_log(f"[IPTVFilter] {extractor}: {label} regex '{pattern}'")
                return True
        except re.error as e:
            debug_log(f"[IPTVFilter] Bad regex '{pattern}': {e}")

    return False


def _matches_skip_prefix(name_upper: str, code: str) -> bool:
    escaped = re.escape(code)
    pattern = rf'[\(\[\-]?{escaped}[\)\]\:\/\|\- ]'
    return bool(re.match(pattern, name_upper))


def channel_passes_filter(ch: dict, cfg: dict) -> bool:
    """Return True when a channel dict should be kept."""
    name = ch.get("name") or ""
    category = ch.get("category_name") or ch.get("category") or ""
    portal = ch.get("portal") or ""

    if cfg.get("drop_empty_names", True) and not name.strip():
        return False

    name_u = _norm(name)
    cat_u = _norm(category)
    debug = bool((cfg.get("_global") or {}).get("debug"))
    extractor = cfg.get("_extractor", "?")

    if portal:
        portal_l = portal.lower()
        for p in cfg.get("exclude_portals") or []:
            if p and str(p).lower() in portal_l:
                if debug:
                    debug_log(f"[IPTVFilter] {extractor}: portal '{portal}' matched exclude '{p}'")
                return False

    if _matches_rules(name_u, cfg.get("exclude_channels") or {}, "channel", debug, extractor):
        return False

    if _matches_rules(cat_u, cfg.get("exclude_categories") or {}, "category", debug, extractor):
        return False

    if _matches_rules(name_u, cfg.get("exclude_categories") or {}, "category-on-name", debug, extractor):
        return False

    keep_hit = False
    for prefix in cfg.get("keep_prefixes") or []:
        p = _norm(prefix)
        if p and name_u.startswith(p):
            keep_hit = True
            break

    skip_hit = False
    for prefix in cfg.get("exclude_prefixes") or []:
        p = _norm(prefix)
        if p and _matches_skip_prefix(name_u, p):
            skip_hit = True
            if debug:
                debug_log(f"[IPTVFilter] {extractor}: prefix '{p}' matched '{name_u[:60]}'")
            break

    if keep_hit:
        if cfg.get("keep_bypasses_exclusion", False):
            return True
        return not skip_hit

    return not skip_hit


def filter_channels_shared(
    channels: List[dict],
    extractor_name: str,
    excluded_portals_fn: Callable[[], List[str]] = None,
) -> List[dict]:
    """Filter a channel list using the shared structured config."""
    cfg = load_filter_config(extractor_name)

    global_enabled = bool((cfg.get("_global") or {}).get("enabled", True))
    section_enabled = bool(cfg.get("enabled", True))
    if not global_enabled or not section_enabled:
        debug_log(f"[IPTVFilter] {extractor_name}: filtering disabled, returning all channels")
        return list(channels)

    if excluded_portals_fn:
        try:
            db_excluded = list(excluded_portals_fn() or [])
            if db_excluded:
                cfg = dict(cfg)
                cfg["exclude_portals"] = list(cfg.get("exclude_portals") or []) + db_excluded
        except Exception as e:
            debug_log(f"[IPTVFilter] excluded_portals_fn error: {e}")

    result = []
    for ch in channels:
        if channel_passes_filter(ch, cfg):
            result.append(ch)
    return result
