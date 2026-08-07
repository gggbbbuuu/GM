import json
import os
import re
import sqlite3
from typing import Dict, List, Optional, Tuple
import xbmc
import xbmcaddon
import xbmcvfs
from ..tools import debug_log

ADDON = xbmcaddon.Addon(id="script.module.jetextractors")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
DB_FILE = os.path.join(ADDON_PATH, "telegram_data.db")

DEFAULT_SKIP_PREFIXES = ["PL", "TR", "EX-YU", "MK", "RO", "HU", "RS", "HR", "BG", "GR", "DE", "FR", "IT", "ES", "NL", "PT", "RU", "ARAB"]
DEFAULT_KEEP_PREFIXES = ["US:", "USA:", "UK:", "EN:", "CA:", "AU:", "NZ:"]
DEFAULT_EXCLUDE_GROUPS = [
    "radio", "netflix", "audio", "conciert", "concert", "pel\u00edcula",
    "document", "advent", "comed", "drama", "relig", "western", "fiction",
    "fantasy", "ovie", "classic", "mystery", "action", "lifestyle", "kids",
    "entertain", "bollywood", "animat", "cine", "inema", "film", "imdb",
    "hulu", "netfl", "estreno", "sagas", "release", "thriller", "horror",
    "anime", "karaoke", "musi", "muzi", "xxx", "24/7", "7/24", "vod",
    "adult", "+18", "18+",
]

DEFAULT_TELEGRAM_SOURCES = [
    "https://t.me/michelstv4/10622",
    # "https://t.me/michelstv4/10583",
    # "https://t.me/michelstv4/10584",
]

MAX_POSTS_PER_SYNC = 10


def _ensure_dir():
    if not os.path.exists(ADDON_PATH):
        try:
            os.makedirs(ADDON_PATH, exist_ok=True)
        except Exception as e:
            debug_log(f"[TelegramStore] Failed to create data dir: {e}")


def _log_info(msg):
    try:
        xbmc.log(f"[TelegramStore] {msg}", xbmc.LOGINFO)
    except Exception:
        pass


def _get_db() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_schema(conn):
    """Add new columns to existing tables if they don't exist."""
    try:
        # Check if channel_type column exists in channels table
        cursor = conn.execute("PRAGMA table_info(channels)")
        columns = [row[1] for row in cursor.fetchall()]

        if "channel_type" not in columns:
            debug_log("[TelegramStore] Migrating: adding channel_type column")
            conn.execute("ALTER TABLE channels ADD COLUMN channel_type TEXT DEFAULT 'xtream'")

        if "mac" not in columns:
            debug_log("[TelegramStore] Migrating: adding mac column")
            conn.execute("ALTER TABLE channels ADD COLUMN mac TEXT")

        if "logo" not in columns:
            debug_log("[TelegramStore] Migrating: adding logo column")
            conn.execute("ALTER TABLE channels ADD COLUMN logo TEXT")

        if "cmd" not in columns:
            debug_log("[TelegramStore] Migrating: adding cmd column")
            conn.execute("ALTER TABLE channels ADD COLUMN cmd TEXT")

        conn.commit()
    except Exception as e:
        debug_log(f"[TelegramStore] Schema migration error: {e}")


def _init_db():
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS portals (
            address TEXT NOT NULL,
            credentials TEXT NOT NULL,
            UNIQUE(address, credentials)
        );
        CREATE TABLE IF NOT EXISTS channels (
            key TEXT PRIMARY KEY,
            channel_type TEXT DEFAULT 'xtream',
            stream_id TEXT,
            name TEXT,
            category_name TEXT,
            portal TEXT,
            username TEXT,
            password TEXT,
            mac TEXT,
            logo TEXT,
            cmd TEXT
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS telegram_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS telegram_pointers (
            channel TEXT PRIMARY KEY,
            post_id INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS excluded_portals (
            address TEXT PRIMARY KEY
        );
    """)
    conn.commit()
    _migrate_schema(conn)
    conn.close()


_init_db()


def _migrate_schema(conn):
    """Add new columns to existing tables if they don't exist."""
    try:
        # Check if channel_type column exists in channels table
        cursor = conn.execute("PRAGMA table_info(channels)")
        columns = [row[1] for row in cursor.fetchall()]

        if "channel_type" not in columns:
            debug_log("[TelegramStore] Migrating: adding channel_type column")
            conn.execute("ALTER TABLE channels ADD COLUMN channel_type TEXT DEFAULT 'xtream'")

        if "mac" not in columns:
            debug_log("[TelegramStore] Migrating: adding mac column")
            conn.execute("ALTER TABLE channels ADD COLUMN mac TEXT")

        if "logo" not in columns:
            debug_log("[TelegramStore] Migrating: adding logo column")
            conn.execute("ALTER TABLE channels ADD COLUMN logo TEXT")

        if "cmd" not in columns:
            debug_log("[TelegramStore] Migrating: adding cmd column")
            conn.execute("ALTER TABLE channels ADD COLUMN cmd TEXT")

        conn.commit()
    except Exception as e:
        debug_log(f"[TelegramStore] Schema migration error: {e}")


def _migrate_from_json():
    """One-time migration from old JSON file to DB."""
    old_file = os.path.join(ADDON_PATH, "telegram_channels.json")
    if not os.path.exists(old_file):
        return
    try:
        with open(old_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        conn = _get_db()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM channels").fetchone()
            if row["cnt"] > 0:
                return
            for addr, creds_list in data.get("portals", {}).items():
                for cred in creds_list:
                    conn.execute("INSERT OR IGNORE INTO portals (address, credentials) VALUES (?, ?)", (addr, cred))
            for ch in data.get("channels", []):
                conn.execute(
                    "INSERT OR IGNORE INTO channels (key, stream_id, name, category_name, portal, username, password) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ch.get("key"), ch.get("stream_id"), ch.get("name"), ch.get("category_name"), ch.get("portal"), ch.get("username", ""), ch.get("password", ""))
                )
            conn.commit()
            debug_log(f"[TelegramStore] Migrated {len(data.get('channels', []))} channels from JSON")
        finally:
            conn.close()
        os.rename(old_file, old_file + ".bak")
    except Exception as e:
        debug_log(f"[TelegramStore] Migration error: {e}")


_migrate_from_json()


def load_channels() -> Dict:
    """Load all data as a dict (for backward compatibility)."""
    conn = _get_db()
    try:
        portals = {}
        for row in conn.execute("SELECT address, credentials FROM portals"):
            addr = row["address"]
            if addr not in portals:
                portals[addr] = []
            portals[addr].append(row["credentials"])

        channels = []
        for row in conn.execute("SELECT * FROM channels"):
            channels.append(dict(row))

        settings = {}
        for row in conn.execute("SELECT key, value FROM settings"):
            try:
                settings[row["key"]] = json.loads(row["value"])
            except Exception:
                settings[row["key"]] = row["value"]

        sources = [row["url"] for row in conn.execute("SELECT url FROM telegram_sources ORDER BY id")]

        pointers = {}
        for row in conn.execute("SELECT channel, post_id FROM telegram_pointers"):
            pointers[row["channel"]] = row["post_id"]

        return {
            "portals": portals,
            "channels": channels,
            "skip_prefixes": settings.get("skip_prefixes", DEFAULT_SKIP_PREFIXES),
            "keep_prefixes": settings.get("keep_prefixes", DEFAULT_KEEP_PREFIXES),
            "exclude_groups": settings.get("exclude_groups", DEFAULT_EXCLUDE_GROUPS),
            "telegram_sources": sources if sources else DEFAULT_TELEGRAM_SOURCES,
            "telegram_pointers": pointers,
        }
    finally:
        conn.close()


def add_mac_portal_credentials(address: str, mac: str, username: str = None, password: str = None):
    """Add or update Mac portal credentials in DB."""
    creds = f"mac:{mac}"
    if username:
        creds += f"|{username}|{password or ''}"
    conn = _get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO portals (address, credentials) VALUES (?, ?)", (address, creds))
        conn.commit()
    finally:
        conn.close()


def get_mac_portal_credentials(portal: str) -> List[Tuple[str, str, str]]:
    """Get list of (mac, username, password) tuples for a Mac portal."""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT credentials FROM portals WHERE address = ?", (portal,)).fetchall()
        result = []
        for r in rows:
            creds = r["credentials"]
            if creds.startswith("mac:"):
                parts = creds[4:].split("|", 2)
                mac = parts[0]
                username = parts[1] if len(parts) > 1 else None
                password = parts[2] if len(parts) > 2 else None
                result.append((mac, username, password))
        return result
    finally:
        conn.close()


def get_all_mac_portals() -> List[Dict]:
    """Get all Mac portal credentials."""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT address, credentials FROM portals WHERE credentials LIKE 'mac:%'").fetchall()
        result = []
        for r in rows:
            creds = r["credentials"]
            if creds.startswith("mac:"):
                parts = creds[4:].split("|", 2)
                mac = parts[0]
                username = parts[1] if len(parts) > 1 else None
                password = parts[2] if len(parts) > 2 else None
                result.append({
                    "address": r["address"],
                    "mac": mac,
                    "username": username,
                    "password": password
                })
        return result
    finally:
        conn.close()


def save_channels(data: Dict):
    """Save full data dict (used for migration/compat). Prefer individual ops."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM portals")
        conn.execute("DELETE FROM channels")
        conn.execute("DELETE FROM settings")
        conn.execute("DELETE FROM telegram_sources")
        conn.execute("DELETE FROM telegram_pointers")

        for addr, creds_list in data.get("portals", {}).items():
            for cred in creds_list:
                conn.execute("INSERT OR IGNORE INTO portals (address, credentials) VALUES (?, ?)", (addr, cred))

        for ch in data.get("channels", []):
            conn.execute(
                "INSERT OR REPLACE INTO channels (key, stream_id, name, category_name, portal, username, password) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ch.get("key"), ch.get("stream_id"), ch.get("name"), ch.get("category_name"), ch.get("portal"), ch.get("username", ""), ch.get("password", ""))
            )

        for key in ("skip_prefixes", "keep_prefixes", "exclude_groups"):
            if key in data:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(data[key])))

        for url in data.get("telegram_sources", []):
            conn.execute("INSERT OR IGNORE INTO telegram_sources (url) VALUES (?)", (url,))

        for channel, post_id in data.get("telegram_pointers", {}).items():
            conn.execute("INSERT OR REPLACE INTO telegram_pointers (channel, post_id) VALUES (?, ?)", (channel, post_id))

        conn.commit()
    except Exception as e:
        debug_log(f"[TelegramStore] Save error: {e}")
    finally:
        conn.close()


def add_portal_credentials(address: str, username: str, password: str):
    """Add or update portal credentials in DB."""
    creds = f"{username}|{password}"
    conn = _get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO portals (address, credentials) VALUES (?, ?)", (address, creds))
        conn.commit()
    finally:
        conn.close()


def add_channels(channels: List[Dict], portal: str, channel_type: str = "xtream"):
    """Add channels to the database.

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
                conn.execute(
                    "INSERT OR IGNORE INTO channels (key, channel_type, name, category_name, portal, mac, logo, cmd) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (key, "mac", name, (ch.get("category_name") or "").strip(), portal, ch.get("mac", ""), ch.get("logo", ""), cmd)
                )
            else:
                stream_id = ch.get("stream_id")
                if not stream_id:
                    continue
                key = f"{portal}|{stream_id}"
                conn.execute(
                    "INSERT OR IGNORE INTO channels (key, channel_type, stream_id, name, category_name, portal, username, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (key, "xtream", stream_id, name, (ch.get("category_name") or "").strip(), portal, ch.get("username", ""), ch.get("password", ""))
                )
        conn.commit()
    finally:
        conn.close()


def search_channels(query: str) -> List[Dict]:
    """Search cached channels by name."""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT * FROM channels WHERE name LIKE ?", (f"%{query}%",)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_portal_credentials(portal: str) -> List[Tuple[str, str]]:
    """Get list of (username, password) tuples for a portal."""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT credentials FROM portals WHERE address = ?", (portal,)).fetchall()
        return [tuple(r["credentials"].split("|", 1)) for r in rows]
    finally:
        conn.close()


def get_telegram_sources() -> List[str]:
    """Get configured Telegram channel source URLs."""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT url FROM telegram_sources ORDER BY id").fetchall()
        if rows:
            return [r["url"] for r in rows]
        return DEFAULT_TELEGRAM_SOURCES
    finally:
        conn.close()


def set_telegram_sources(sources: List[str]):
    """Set the list of Telegram channel source URLs."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM telegram_sources")
        for url in sources:
            conn.execute("INSERT OR IGNORE INTO telegram_sources (url) VALUES (?)", (url,))
        conn.commit()
    finally:
        conn.close()


def get_telegram_pointer(channel: str) -> Optional[int]:
    """Get the last-scraped post ID for a channel."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT post_id FROM telegram_pointers WHERE channel = ?", (channel,)).fetchone()
        return row["post_id"] if row else None
    finally:
        conn.close()


def set_telegram_pointer(channel: str, post_id: int):
    """Save the last-scraped post ID for a channel."""
    conn = _get_db()
    try:
        conn.execute("INSERT OR REPLACE INTO telegram_pointers (channel, post_id) VALUES (?, ?)", (channel, post_id))
        conn.commit()
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


def is_portal_excluded(address: str) -> bool:
    """Check if a portal URL is in the exclusion list."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT 1 FROM excluded_portals WHERE address = ?", (address,)).fetchone()
        return row is not None
    finally:
        conn.close()


def get_filter() -> dict:
    conn = _get_db()
    try:
        settings = {}
        for row in conn.execute("SELECT key, value FROM settings"):
            try:
                settings[row["key"]] = json.loads(row["value"])
            except Exception:
                settings[row["key"]] = row["value"]
        return {
            "skip_prefixes": settings.get("skip_prefixes", DEFAULT_SKIP_PREFIXES),
            "keep_prefixes": settings.get("keep_prefixes", DEFAULT_KEEP_PREFIXES),
            "exclude_groups": settings.get("exclude_groups", DEFAULT_EXCLUDE_GROUPS),
        }
    finally:
        conn.close()


def _matches_skip_prefix(name_upper: str, code: str) -> bool:
    escaped = re.escape(code)
    pattern = rf'[\(\[\-]?{escaped}[\)\]\:\/\|\- ]'
    return bool(re.match(pattern, name_upper))


def _channel_passes_filter(name: str, category: str, skip_prefixes: list, keep_prefixes: list, exclude_groups: list) -> bool:
    name_upper = (name or "").upper()
    cat_upper = (category or "").upper()

    for grp in exclude_groups:
        if grp.upper() in cat_upper or grp.upper() in name_upper:
            return False

    for prefix in keep_prefixes:
        if name_upper.startswith(prefix.upper()):
            return True
    for prefix in skip_prefixes:
        if _matches_skip_prefix(name_upper, prefix.upper()):
            return False
    return True


def get_all_cached_portals() -> List[Dict]:
    """Get all unique portals with their credentials from cache."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT portal, username, password, channel_type FROM channels WHERE portal != ''"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def remove_portal_channels(portal: str, channel_type: str = None):
    """Remove all channels for a portal."""
    conn = _get_db()
    try:
        if channel_type:
            conn.execute("DELETE FROM channels WHERE portal = ? AND channel_type = ?", (portal, channel_type))
        else:
            conn.execute("DELETE FROM channels WHERE portal = ?", (portal,))
        conn.commit()
    finally:
        conn.close()


def remove_portal_credentials(address: str):
    """Remove portal credentials."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM portals WHERE address = ?", (address,))
        conn.commit()
    finally:
        conn.close()


def remove_mac_portal_credentials(address: str):
    """Remove MAC portal credentials."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM portals WHERE address = ? AND credentials LIKE 'mac:%'", (address,))
        conn.commit()
    finally:
        conn.close()


def filter_channels(channels: List[Dict]) -> List[Dict]:
    """Filter channels by name, category, and excluded portals."""
    flt = get_filter()
    skip_prefixes = flt.get("skip_prefixes", [])
    keep_prefixes = flt.get("keep_prefixes", [])
    exclude_groups = flt.get("exclude_groups", [])
    excluded = set(get_excluded_portals())
    return [ch for ch in channels if ch.get("portal", "") not in excluded and _channel_passes_filter(
        ch.get("name", ""), ch.get("category_name", "") or ch.get("category", ""), skip_prefixes, keep_prefixes, exclude_groups
    )]


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
