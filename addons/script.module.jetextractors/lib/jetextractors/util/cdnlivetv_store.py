import os
import sqlite3
import time
from typing import Dict, List
import xbmc
import xbmcaddon
import xbmcvfs
from ..tools import debug_log

ADDON = xbmcaddon.Addon(id="script.module.jetextractors")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
DB_FILE = os.path.join(ADDON_PATH, "cdnlivetv_data.db")

REFRESH_INTERVAL = 43200


def _ensure_dir():
    if not os.path.exists(ADDON_PATH):
        try:
            os.makedirs(ADDON_PATH, exist_ok=True)
        except Exception as e:
            debug_log(f"[CDNLiveTVStore] Failed to create data dir: {e}")


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
        CREATE TABLE IF NOT EXISTS channels (
            key TEXT PRIMARY KEY,
            name TEXT,
            url TEXT,
            image TEXT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()


_init_db()


def add_channels(channels: List[Dict]):
    """Store CDNLiveTV channels in the database."""
    conn = _get_db()
    try:
        rows = []
        for ch in channels:
            name = (ch.get("name") or "").strip()
            url = (ch.get("url") or "").strip()
            if not name or not url:
                continue
            key = f"cdn_{name}"
            rows.append((
                key, name, url,
                ch.get("image", ""),
                ch.get("status", ""),
            ))
        if rows:
            conn.executemany(
                "INSERT OR REPLACE INTO channels (key, name, url, image, status) VALUES (?, ?, ?, ?, ?)",
                rows
            )
            conn.commit()
            debug_log(f"[CDNLiveTVStore] Stored {len(rows)} channels", xbmc.LOGINFO)
    finally:
        conn.close()


def load_channels() -> List[Dict]:
    """Load all stored channels."""
    conn = _get_db()
    try:
        channels = []
        for row in conn.execute("SELECT * FROM channels ORDER BY name"):
            channels.append(dict(row))
        return channels
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
        debug_log("[CDNLiveTVStore] Cleared all channels", xbmc.LOGINFO)
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
        return [dict(row) for row in rows]
    finally:
        conn.close()
