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
DB_FILE = os.path.join(ADDON_PATH, "backdoor2_data.db")

REFRESH_INTERVAL = 86400


def _ensure_dir():
    if not os.path.exists(ADDON_PATH):
        try:
            os.makedirs(ADDON_PATH, exist_ok=True)
        except Exception as e:
            debug_log(f"[Backdoor2Store] Failed to create data dir: {e}")


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
            embed_url TEXT,
            channel_id TEXT,
            league TEXT DEFAULT '24/7 Channels'
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
    """Store 24/7 channels in the database."""
    conn = _get_db()
    try:
        rows = []
        for ch in channels:
            name = (ch.get("name") or "").strip()
            embed_url = (ch.get("embed_url") or "").strip()
            channel_id = (ch.get("channel_id") or "").strip()
            if not name or not embed_url:
                continue
            key = f"bck2_{channel_id}_{name}" if channel_id else f"bck2_{name}"
            rows.append((key, name, embed_url, channel_id, "24/7 Channels"))
        if rows:
            conn.executemany(
                "INSERT OR REPLACE INTO channels (key, name, embed_url, channel_id, league) VALUES (?, ?, ?, ?, ?)",
                rows
            )
            conn.commit()
            debug_log(f"[Backdoor2Store] Stored {len(rows)} 24/7 channels", xbmc.LOGINFO)
    finally:
        conn.close()


def load_channels() -> Dict:
    """Load all 24/7 channels."""
    conn = _get_db()
    try:
        channels = []
        for row in conn.execute("SELECT * FROM channels ORDER BY name"):
            channels.append(dict(row))
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
        debug_log("[Backdoor2Store] Cleared all 24/7 channels", xbmc.LOGINFO)
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
    """Check if the data is stale (older than REFRESH_INTERVAL)."""
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
