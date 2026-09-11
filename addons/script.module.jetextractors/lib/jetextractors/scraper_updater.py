"""Remote scraper hot-update module.

Checks a server-hosted manifest for updated scraper files, downloads them,
verifies integrity via SHA-256, and atomically replaces local copies. Updated
modules are hot-reloaded within the current process so no Kodi restart is
required.

Scrapers remain local files — they execute from disk, not from the network.
"""

import os
import sys
import json
import time
import hashlib
import threading
import importlib
from typing import Optional, List, Dict

import requests
import xbmc
import xbmcaddon
import xbmcvfs

from .endpoints import SCRAPERS_MANIFEST, SCRAPERS_DIR
from .tools import debug_log
from .models import JetExtractor

_CACHE_TTL = 6 * 3600
_MANIFEST_TIMEOUT = 10
_FILE_TIMEOUT = 15

_ADDON = xbmcaddon.Addon(id="script.module.jetextractors")
_ADDON_DATA_DIR = xbmcvfs.translatePath(_ADDON.getAddonInfo("profile"))
_CACHE_FILE = os.path.join(_ADDON_DATA_DIR, "scraper_updates.json")

_EXTRACTORS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extractors")
_EXTRACTORS_PKG = "jetextractors.extractors"

_update_lock = threading.Lock()


def _load_cache() -> dict:
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"last_check": 0, "hashes": {}}


def _save_cache(cache: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        with open(_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        debug_log(f"[ScraperUpdater] Failed to save cache: {e}", xbmc.LOGWARNING)


def _compute_file_hash(filename: str) -> Optional[str]:
    path = os.path.join(_EXTRACTORS_DIR, filename)
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def _is_writable() -> bool:
    try:
        test = os.path.join(_EXTRACTORS_DIR, ".write_test")
        with open(test, "w") as f:
            f.write("x")
        os.remove(test)
        return True
    except Exception:
        return False


def _download_and_replace(filename: str, info: dict) -> bool:
    url = info.get("url") or f"{SCRAPERS_DIR}/{filename}"
    expected_hash = info.get("hash", "")
    try:
        debug_log(f"[ScraperUpdater] Downloading {filename} from {url}", xbmc.LOGINFO)
        r = requests.get(url, timeout=_FILE_TIMEOUT)
        r.raise_for_status()
        content = r.content

        if expected_hash:
            actual_hash = hashlib.sha256(content).hexdigest()
            if actual_hash.lower() != expected_hash.lower():
                debug_log(
                    f"[ScraperUpdater] Hash mismatch for {filename}: "
                    f"expected {expected_hash[:12]}..., got {actual_hash[:12]}...",
                    xbmc.LOGERROR,
                )
                return False

        path = os.path.join(_EXTRACTORS_DIR, filename)
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(content)
        os.replace(tmp_path, path)
        debug_log(f"[ScraperUpdater] Updated {filename}", xbmc.LOGINFO)
        return True
    except Exception as e:
        debug_log(f"[ScraperUpdater] Failed to update {filename}: {e}", xbmc.LOGWARNING)
        tmp_path = os.path.join(_EXTRACTORS_DIR, filename) + ".tmp"
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False


def _reload_modules(filenames: List[str]) -> None:
    for filename in filenames:
        modname = filename.replace(".py", "")
        full_modname = f"{_EXTRACTORS_PKG}.{modname}"

        sys.modules.pop(full_modname, None)

        stale = [c for c in JetExtractor.subclasses if getattr(c, "__module__", "") == full_modname]
        for c in stale:
            if c in JetExtractor.subclasses:
                JetExtractor.subclasses.remove(c)

        try:
            importlib.import_module(full_modname)
        except Exception as e:
            debug_log(f"[ScraperUpdater] Failed to re-import {modname}: {e}", xbmc.LOGERROR)

    try:
        from . import extractor as _ext_mod
        _ext_mod._extractor_cache.clear()
        _ext_mod._cache_initialized = False
    except Exception:
        pass


def check_for_updates() -> bool:
    """Check the manifest and apply any scraper updates.

    Returns True if any files were updated. TTL-guarded to run at most once
    per ``_CACHE_TTL`` seconds. Fails silently on network errors — local
    files are always used as fallback.
    """
    with _update_lock:
        cache = _load_cache()
        now = int(time.time())

        if cache.get("last_check", 0) > now - _CACHE_TTL:
            return False

        if not _is_writable():
            cache["last_check"] = now
            _save_cache(cache)
            return False

        try:
            debug_log("[ScraperUpdater] Checking for scraper updates", xbmc.LOGINFO)
            r = requests.get(SCRAPERS_MANIFEST, timeout=_MANIFEST_TIMEOUT)
            r.raise_for_status()
            manifest = r.json()
        except Exception as e:
            debug_log(f"[ScraperUpdater] Failed to fetch manifest: {e}", xbmc.LOGWARNING)
            cache["last_check"] = now
            _save_cache(cache)
            return False

        updated_scrapers: List[str] = []
        updated_hashes: Dict[str, str] = {}

        for filename, info in manifest.get("scrapers", {}).items():
            expected_hash = info.get("hash", "")
            local_hash = _compute_file_hash(filename)
            updated_hashes[filename] = expected_hash

            if local_hash and expected_hash and local_hash.lower() == expected_hash.lower():
                continue

            if _download_and_replace(filename, info):
                updated_scrapers.append(filename)

        cache["last_check"] = now
        cache["hashes"] = updated_hashes
        _save_cache(cache)

        if updated_scrapers:
            debug_log(
                f"[ScraperUpdater] Updated {len(updated_scrapers)} scraper(s): "
                f"{', '.join(updated_scrapers)}",
                xbmc.LOGINFO,
            )
            _reload_modules(updated_scrapers)
        else:
            debug_log("[ScraperUpdater] No updates needed", xbmc.LOGINFO)

        return len(updated_scrapers) > 0
