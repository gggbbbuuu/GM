import os
import json
import sqlite3
import time
from typing import Dict, List
from urllib.parse import urlparse
import xbmc
import xbmcaddon
import xbmcvfs
from ..tools import debug_log
from ..endpoints import SPORTSX_M3U, DOM_M3U, SPORTSX_SOURCES, LOOP_SOURCES

ADDON = xbmcaddon.Addon(id="script.module.jetextractors")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
DB_FILE = os.path.join(ADDON_PATH, "sportsx_data.db")

REFRESH_INTERVAL = 3600

DEFAULT_SOURCES = [SPORTSX_M3U, DOM_M3U]

_CREATE_TABLES_SQL = """
    CREATE TABLE IF NOT EXISTS channels (
        key TEXT PRIMARY KEY,
        name TEXT,
        url TEXT,
        channel_type TEXT DEFAULT 'direct',
        portal TEXT,
        mac TEXT,
        sn TEXT,
        device TEXT,
        channel_id TEXT,
        logo TEXT,
        headers TEXT
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    CREATE TABLE IF NOT EXISTS m3u_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL UNIQUE
    );
"""

_SOURCES_CACHE: List[str] = []
_SOURCES_CACHE_TS: float = 0.0
_SOURCES_CACHE_TTL = 300


REMOTE_SOURCE_FILES = [SPORTSX_SOURCES, LOOP_SOURCES]

MAX_SOURCES_PER_FILE = 10


def _is_source_url(line: str) -> bool:
    """Return True only for absolute http(s) URLs."""
    try:
        parsed = urlparse(line)
    except Exception:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _get_default_sources() -> List[str]:
    """Get default source URLs, fetching from remote txt files when available.

    Each remote txt file (REMOTE_SOURCE_FILES) should contain one URL per line.
    This allows source URLs to be changed remotely without a code update.
    All reachable files are merged (duplicates removed, order preserved).
    Falls back to the hardcoded DEFAULT_SOURCES if every fetch fails.
    """
    global _SOURCES_CACHE, _SOURCES_CACHE_TS
    now = time.time()
    if _SOURCES_CACHE and (now - _SOURCES_CACHE_TS) < _SOURCES_CACHE_TTL:
        return list(_SOURCES_CACHE)
    try:
        from .._core import fetch_page, _KODI_UA
        urls: List[str] = []
        for source_file in REMOTE_SOURCE_FILES:
            try:
                text = fetch_page(source_file, user_agent=_KODI_UA)
            except Exception as e:
                debug_log(f"[SportsXStore] Failed to fetch {source_file}: {e}")
                continue
            if not text:
                debug_log(f"[SportsXStore] No content from {source_file}")
                continue
            stripped = text.strip()
            if stripped.startswith("<"):
                debug_log(f"[SportsXStore] {source_file} returned HTML, not a source list - skipped")
                continue
            candidates = [
                line.strip()
                for line in stripped.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            found = [line for line in candidates if _is_source_url(line)]
            kept = found[:MAX_SOURCES_PER_FILE]
            if len(kept) < len(found):
                debug_log(f"[SportsXStore] {source_file}: capped to {MAX_SOURCES_PER_FILE} sources (file listed {len(found)})")
            added = 0
            for url in kept:
                if url not in urls:
                    urls.append(url)
                    added += 1
            debug_log(f"[SportsXStore] {source_file}: {added} new sources ({len(kept)} valid of {len(candidates)} lines)")
        if urls:
            _SOURCES_CACHE = urls
            _SOURCES_CACHE_TS = now
            debug_log(f"[SportsXStore] Using {len(urls)} sources from remote config")
            return list(urls)
    except Exception as e:
        debug_log(f"[SportsXStore] Failed to fetch remote sources: {e}")
    debug_log("[SportsXStore] Falling back to hardcoded DEFAULT_SOURCES")
    return list(DEFAULT_SOURCES)


def _ensure_dir():
    if not os.path.exists(ADDON_PATH):
        try:
            os.makedirs(ADDON_PATH, exist_ok=True)
        except Exception as e:
            debug_log(f"[SportsXStore] Failed to create data dir: {e}")


def _get_db() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    conn.executescript(_CREATE_TABLES_SQL)
    return conn


def _init_db():
    conn = _get_db()
    try:
        conn.execute("SELECT headers FROM channels LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE channels ADD COLUMN headers TEXT")
        conn.commit()
    conn.close()


_init_db()


def get_sources() -> List[str]:
    """Get configured M3U source URLs."""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT url FROM m3u_sources").fetchall()
        if rows:
            return [row["url"] for row in rows]
        sources = _get_default_sources()
        for url in sources:
            conn.execute("INSERT OR IGNORE INTO m3u_sources (url) VALUES (?)", (url,))
        conn.commit()
        return list(sources)
    finally:
        conn.close()


def add_source(url: str):
    """Add an M3U source URL."""
    conn = _get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO m3u_sources (url) VALUES (?)", (url,))
        conn.commit()
    finally:
        conn.close()


def remove_source(url: str):
    """Remove an M3U source URL."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM m3u_sources WHERE url = ?", (url,))
        conn.commit()
    finally:
        conn.close()


def add_channels(channels: List[Dict]):
    """Store channels in the database."""
    conn = _get_db()
    try:
        rows = []
        for ch in channels:
            name = (ch.get("name") or "").strip()
            url = (ch.get("url") or "").strip()
            if not name or not url:
                continue
            channel_type = ch.get("channel_type", "direct")
            headers_json = json.dumps(ch.get("headers") or {}) if ch.get("headers") else None
            if channel_type == "worker":
                portal = ch.get("portal", "")
                mac = ch.get("mac", "")
                channel_id = ch.get("channel_id", "")
                key = f"sportsx_{portal}_{channel_id}_{name}"
                rows.append((
                    key, name, url, channel_type,
                    portal, mac,
                    ch.get("sn", ""), ch.get("device", ""),
                    channel_id, ch.get("logo", ""),
                    headers_json,
                ))
            else:
                key = f"sportsx_{name}"
                rows.append((
                    key, name, url, channel_type,
                    "", "", "", "", "", ch.get("logo", ""),
                    headers_json,
                ))
        if rows:
            conn.executemany(
                "INSERT OR REPLACE INTO channels (key, name, url, channel_type, portal, mac, sn, device, channel_id, logo, headers) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows
            )
            conn.commit()
            debug_log(f"[SportsXStore] Stored {len(rows)} channels")
    finally:
        conn.close()


def load_channels() -> Dict:
    """Load all channels."""
    conn = _get_db()
    try:
        channels = []
        for row in conn.execute("SELECT * FROM channels ORDER BY name"):
            ch = dict(row)
            headers_raw = ch.get("headers")
            if headers_raw:
                try:
                    ch["headers"] = json.loads(headers_raw)
                except (json.JSONDecodeError, TypeError):
                    ch["headers"] = {}
            else:
                ch["headers"] = {}
            channels.append(ch)
        return {"channels": channels}
    finally:
        conn.close()


def get_channel_count() -> int:
    """Get the number of stored channels."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM channels").fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def clear_channels():
    """Clear all stored channels."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM channels")
        conn.commit()
        debug_log("[SportsXStore] Cleared all channels", xbmc.LOGINFO)
    finally:
        conn.close()


def get_last_refresh_ts() -> float:
    """Get the last refresh timestamp."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'last_refresh_ts'").fetchone()
        if row:
            try:
                return float(row["value"])
            except (ValueError, TypeError):
                return 0.0
        return 0.0
    finally:
        conn.close()


def set_last_refresh_ts(ts: float):
    """Save the last refresh timestamp."""
    conn = _get_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('last_refresh_ts', ?)",
            (str(ts),)
        )
        conn.commit()
    finally:
        conn.close()


def get_last_scrape_ts() -> float:
    """Get the last scrape timestamp from the database."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'last_scrape_ts'").fetchone()
        if row:
            try:
                return float(row["value"])
            except (ValueError, TypeError):
                return 0.0
        return 0.0
    finally:
        conn.close()


def set_last_scrape_ts(ts: float):
    """Save the last scrape timestamp to the database."""
    conn = _get_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('last_scrape_ts', ?)",
            (str(ts),)
        )
        conn.commit()
    finally:
        conn.close()


def is_stale() -> bool:
    """Check if the channel data is stale (older than REFRESH_INTERVAL)."""
    last = get_last_refresh_ts()
    return (time.time() - last) > REFRESH_INTERVAL


def clear_all():
    """Clear all stored data."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM channels")
        conn.execute("DELETE FROM settings")
        conn.commit()
        debug_log("[SportsXStore] Cleared all data")
    finally:
        conn.close()


def search_channels(query: str) -> List[Dict]:
    """Search channels by name (case-insensitive LIKE match)."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM channels WHERE name LIKE ? ORDER BY name",
            (f"%{query}%",)
        ).fetchall()
        results = []
        for row in rows:
            ch = dict(row)
            headers_raw = ch.get("headers")
            if headers_raw:
                try:
                    ch["headers"] = json.loads(headers_raw)
                except (json.JSONDecodeError, TypeError):
                    ch["headers"] = {}
            else:
                ch["headers"] = {}
            results.append(ch)
        return results
    finally:
        conn.close()
