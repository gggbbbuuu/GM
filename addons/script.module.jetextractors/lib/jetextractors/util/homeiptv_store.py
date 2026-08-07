import json
import os
import sqlite3
from typing import Dict, List, Optional
import xbmcaddon
import xbmcvfs
from ..endpoints import TVSCRAPE 
from ..tools import debug_log

ADDON = xbmcaddon.Addon(id="script.module.jetextractors")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
DB_FILE = os.path.join(ADDON_PATH, "homeiptv_data.db")

DEFAULT_SOURCES = [
    TVSCRAPE,
]

DEFAULT_SKIP_PREFIXES = []
DEFAULT_SKIP_PREFIXES = ["PL", "TR", "EX-YU", "MK", "RO", "HU", "RS", "HR", "BG", "GR", "DE", "FR", "IT", "ES", "NL", "PT", "RU", "ARAB"]
DEFAULT_KEEP_PREFIXES = [
    "US:", "USA:", "UK:", "EN:", "CA:", "AU:", "NZ:"
]
DEFAULT_EXCLUDE_GROUPS = [
    "radio", "netflix", "audio", "conciert", "concert", "pel\u00edcula",
    "document", "advent", "comed", "drama", "relig", "western", "fiction",
    "fantasy", "ovie", "classic", "mystery", "action", "lifestyle", "kids",
    "entertain", "bollywood", "animat", "cine", "inema", "film", "imdb",
    "hulu", "netfl", "estreno", "sagas", "release", "thriller", "horror",
    "anime", "karaoke", "musi", "muzi", "xxx", "24/7", "7/24", "vod",
    "adult", "+18", "18+",
]


def _ensure_dir():
    if not os.path.exists(ADDON_PATH):
        try:
            os.makedirs(ADDON_PATH, exist_ok=True)
        except Exception as e:
            debug_log(f"[HomeIPTVStore] Failed to create data dir: {e}")


def _get_db() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS excluded_portals (
            address TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS portals (
            address TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            UNIQUE(address, username, password)
        );
        CREATE TABLE IF NOT EXISTS mac_portals (
            address TEXT NOT NULL,
            mac TEXT NOT NULL,
            username TEXT,
            password TEXT,
            UNIQUE(address, mac)
        );
        CREATE TABLE IF NOT EXISTS channels (
            key TEXT PRIMARY KEY,
            channel_type TEXT DEFAULT 'xtream',
            name TEXT,
            category_name TEXT,
            portal TEXT,
            username TEXT,
            password TEXT,
            stream_id TEXT,
            logo TEXT,
            mac TEXT,
            cmd TEXT
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS iptv_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE
        );
    """)
    conn.commit()
    conn.close()


_init_db()


def get_sources() -> List[str]:
    """Get configured text file source URLs."""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT url FROM iptv_sources").fetchall()
        if rows:
            return [row["url"] for row in rows]
        # Initialize with defaults
        for url in DEFAULT_SOURCES:
            conn.execute("INSERT OR IGNORE INTO iptv_sources (url) VALUES (?)", (url,))
        conn.commit()
        return list(DEFAULT_SOURCES)
    finally:
        conn.close()


def add_source(url: str):
    """Add a text file source URL."""
    conn = _get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO iptv_sources (url) VALUES (?)", (url,))
        conn.commit()
    finally:
        conn.close()


def remove_source(url: str):
    """Remove a text file source URL."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM iptv_sources WHERE url = ?", (url,))
        conn.commit()
    finally:
        conn.close()


def add_portal_credentials(address: str, username: str, password: str):
    """Store portal credentials."""
    conn = _get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO portals (address, username, password) VALUES (?, ?, ?)",
            (address, username, password)
        )
        conn.commit()
    finally:
        conn.close()


def get_portal_credentials(address: str) -> List[Dict]:
    """Get all credentials for a portal."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT username, password FROM portals WHERE address = ?",
            (address,)
        ).fetchall()
        return [{"username": row["username"], "password": row["password"]} for row in rows]
    finally:
        conn.close()


def is_portal_excluded(address: str) -> bool:
    """Check if a portal should be skipped."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT 1 FROM excluded_portals WHERE address = ?", (address,)).fetchone()
        return row is not None
    finally:
        conn.close()


def add_excluded_portal(address: str):
    """Add a portal URL to the exclusion list."""
    conn = _get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO excluded_portals (address) VALUES (?)", (address,))
        conn.commit()
    finally:
        conn.close()


def remove_excluded_portal(address: str):
    """Remove a portal URL from the exclusion list."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM excluded_portals WHERE address = ?", (address,))
        conn.commit()
    finally:
        conn.close()


def get_excluded_portals() -> List[str]:
    """Get all excluded portal URLs."""
    conn = _get_db()
    try:
        return [row["address"] for row in conn.execute("SELECT address FROM excluded_portals")]
    finally:
        conn.close()


def add_channels(channels: List[Dict], portal: str, channel_type: str = "xtream"):
    """Store channels in the database.

    Args:
        channels: List of channel dicts
        portal: Portal address
        channel_type: 'xtream' or 'mac'
    """
    conn = _get_db()
    try:
        for ch in channels:
            name = (ch.get("name") or "").strip()
            if not name:
                continue

            if channel_type == "mac":
                cmd = ch.get("cmd", "")
                if not cmd:
                    continue
                key = f"mac|{portal}|{cmd}"
                cat_name = (ch.get("category_name") or ch.get("category") or "").strip()
                conn.execute(
                    "INSERT OR IGNORE INTO channels (key, channel_type, name, category_name, portal, mac, logo, cmd) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (key, "mac", name, cat_name, portal, ch.get("mac", ""), ch.get("logo", ""), cmd)
                )
            else:
                stream_id = ch.get("stream_id")
                if not stream_id:
                    continue
                key = f"homeiptv_{portal}_{stream_id}_{name}"
                conn.execute(
                    "INSERT OR IGNORE INTO channels (key, channel_type, name, category_name, portal, username, password, stream_id, logo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (key, "xtream", name, (ch.get("category_name") or "").strip(), portal, ch.get("username", ""), ch.get("password", ""), stream_id, ch.get("logo", ""))
                )
        conn.commit()
        debug_log(f"[HomeIPTVStore] Added {len(channels)} channels from {portal}")
    finally:
        conn.close()


def load_channels() -> Dict:
    """Load all channels grouped by portal."""
    conn = _get_db()
    try:
        channels = []
        for row in conn.execute("SELECT * FROM channels"):
            channels.append(dict(row))
        return {"channels": channels}
    finally:
        conn.close()


def filter_channels(channels: List[Dict]) -> List[Dict]:
    """Filter channels based on prefix and exclude rules."""
    filtered = []
    for ch in channels:
        name = ch.get("name", "")
        if not name:
            continue

        # Keep US/UK/CA/AU channels
        name_upper = name.upper()
        if any(name_upper.startswith(p) for p in DEFAULT_KEEP_PREFIXES):
            filtered.append(ch)
            continue

        # Skip foreign channels by prefix
        if any(name_upper.startswith(p) for p in DEFAULT_SKIP_PREFIXES):
            continue

        # Skip excluded groups
        category = (ch.get("category_name") or "").lower()
        if any(ex in category for ex in DEFAULT_EXCLUDE_GROUPS):
            continue

        filtered.append(ch)

    return filtered


def get_all_cached_portals() -> List[Dict]:
    """Get all unique portals with their credentials from cache."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT portal, username, password FROM channels WHERE portal != ''"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def remove_portal_channels(portal: str):
    """Remove all channels for a portal."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM channels WHERE portal = ?", (portal,))
        conn.commit()
    finally:
        conn.close()


def remove_portal_credentials(address: str, username: str = None, password: str = None):
    """Remove portal credentials."""
    conn = _get_db()
    try:
        if username and password:
            conn.execute("DELETE FROM portals WHERE address = ? AND username = ? AND password = ?", (address, username, password))
        else:
            conn.execute("DELETE FROM portals WHERE address = ?", (address,))
        conn.commit()
    finally:
        conn.close()


def add_mac_portal_credentials(address: str, mac: str, username: str = None, password: str = None):
    """Store MAC portal credentials."""
    conn = _get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO mac_portals (address, mac, username, password) VALUES (?, ?, ?, ?)",
            (address, mac, username, password)
        )
        conn.commit()
    finally:
        conn.close()


def get_mac_portal_credentials(address: str) -> List[Dict]:
    """Get all MAC credentials for a portal."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT mac, username, password FROM mac_portals WHERE address = ?",
            (address,)
        ).fetchall()
        return [{"mac": row["mac"], "username": row["username"], "password": row["password"]} for row in rows]
    finally:
        conn.close()


def get_all_mac_portals() -> List[Dict]:
    """Get all unique MAC portals from cache."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT portal, mac, username, password FROM channels WHERE channel_type = 'mac' AND portal != ''"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def remove_mac_portal_channels(portal: str):
    """Remove all MAC channels for a portal."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM channels WHERE portal = ? AND channel_type = 'mac'", (portal,))
        conn.commit()
    finally:
        conn.close()


def remove_mac_portal_credentials(address: str, mac: str = None):
    """Remove MAC portal credentials."""
    conn = _get_db()
    try:
        if mac:
            conn.execute("DELETE FROM mac_portals WHERE address = ? AND mac = ?", (address, mac))
        else:
            conn.execute("DELETE FROM mac_portals WHERE address = ?", (address,))
        conn.commit()
    finally:
        conn.close()


def clear_all():
    """Clear all stored data."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM channels")
        conn.execute("DELETE FROM portals")
        conn.execute("DELETE FROM mac_portals")
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
