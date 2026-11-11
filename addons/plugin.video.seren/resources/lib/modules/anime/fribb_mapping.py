"""Fribb anime-lists — offline anime ID index (replaces the Otaku-Mappings DB).

github.com/Fribb/anime-lists publishes one JSON list that links AniList, MAL, AniDB, Kitsu, Simkl,
TheTVDB, TMDb and IMDb ids (and TVDB/TMDb season + episode offset).  The list is downloaded once a
week, converted to an indexed SQLite file in the add-on's userdata and queried from there, so a
lookup never holds the 7.5 MB JSON in memory.

What it does NOT carry, compared with the old Otaku-Mappings DB: Trakt ids and the TVDB "part"
(cour) number.  ``thetvdb_part`` is therefore always None; ``thetvdb_season`` is the TVDB season,
or ``'a'`` when the entry has a TVDB id but no TVDB season (how the list marks absolute-ordered
shows such as One Piece), or None.

Row choice when one TMDb/IMDb id has several entries (one per season/cour): TV first, then ONA, then
everything else; then the lowest TMDb season (season 0 / unknown last), then the lowest episode
offset, then the lowest MAL/AniList id.  That is the show's first-season entry.
"""

import os
import json
import sqlite3
import time

import requests

from resources.lib.modules.globals import g

FRIBB_URL = "https://raw.githubusercontent.com/Fribb/anime-lists/master/anime-list-full.json"
_DB_NAME = "animeFribb.db"
_LEGACY_DB_NAME = "animeMappings.db"  # Otaku-Mappings file written by 3.9.67 and earlier
_REFRESH_SECONDS = 7 * 24 * 3600
_MIN_ENTRIES = 30000   # the list holds ~39,600; anything much smaller is a broken download
_SHRINK_FLOOR = 0.9    # a new list smaller than 90% of the one we have is not trusted
_SCHEMA = (
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)",
    "CREATE TABLE anime ("
    "id INTEGER PRIMARY KEY, type_rank INTEGER NOT NULL, season_rank INTEGER NOT NULL, tmdb_offset INTEGER NOT NULL, "
    "type TEXT, anilist_id INTEGER, mal_id INTEGER, anidb_id INTEGER, kitsu_id INTEGER, simkl_id INTEGER, "
    "tvdb_id INTEGER, tvdb_season INTEGER, tmdb_tv INTEGER)",
    "CREATE TABLE imdb (imdb_id TEXT NOT NULL, anime_id INTEGER NOT NULL)",
    "CREATE INDEX idx_anime_tmdb ON anime(tmdb_tv)",
    "CREATE INDEX idx_anime_anidb ON anime(anidb_id)",
    "CREATE INDEX idx_imdb ON imdb(imdb_id)",
)
_PICK_ORDER = "ORDER BY type_rank, season_rank, tmdb_offset, COALESCE(mal_id, anilist_id)"
_HAS_ANIME_ID = "(anilist_id IS NOT NULL OR mal_id IS NOT NULL)"


def db_path():
    return os.path.join(g.ADDON_USERDATA_PATH, _DB_NAME)


def _int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _connect():
    """Read connection to the index, or None when it is missing or not a Fribb index."""
    path = db_path()
    if not os.path.exists(path):
        return None
    try:
        conn = sqlite3.connect(path, timeout=3)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT value FROM meta WHERE key='source'").fetchone()
        if not row or row["value"] != "fribb":
            conn.close()
            return None
        return conn
    except Exception as e:
        g.log(f"Fribb index open failed: {e}", "debug")
        return None


def _season_value(row):
    if row["tvdb_season"] is not None:
        return row["tvdb_season"]
    if row["tvdb_id"] and row["type"] == "TV":
        return "a"
    return None


def lookup(imdb_id=None, tmdb_id=None):
    """Anime ID dict for a TV show by IMDb id, then TMDb TV id; None when unmapped.

    Keys match what anilist_mapping.get_anime_ids returns.  thetvdb_part is always None."""
    conn = _connect()
    if conn is None:
        return None
    try:
        row = None
        if imdb_id:
            row = conn.execute(
                f"SELECT * FROM anime WHERE {_HAS_ANIME_ID} AND id IN (SELECT anime_id FROM imdb WHERE imdb_id=?) "
                f"{_PICK_ORDER} LIMIT 1", (str(imdb_id),)).fetchone()
        tmdb = _int(tmdb_id)
        if row is None and tmdb:
            row = conn.execute(
                f"SELECT * FROM anime WHERE {_HAS_ANIME_ID} AND tmdb_tv=? {_PICK_ORDER} LIMIT 1", (tmdb,)).fetchone()
        if row is None:
            return None
        return {
            "anilist_id": row["anilist_id"],
            "mal_id": row["mal_id"],
            "anidb_id": row["anidb_id"],
            "kitsu_id": row["kitsu_id"],
            "simkl_id": row["simkl_id"],
            "thetvdb_id": row["tvdb_id"],
            "themoviedb_id": row["tmdb_tv"],
            "thetvdb_season": _season_value(row),
            "thetvdb_part": None,
        }
    except Exception as e:
        g.log(f"Fribb lookup failed: {e}", "debug")
        return None
    finally:
        conn.close()


def lookup_episode(imdb_id=None, tmdb_id=None, season=None, episode=None):
    """The entry (cour) that a TMDb season/episode of an anime show belongs to.

    Returns (entry, reason).  entry is the id dict ``lookup`` returns for that cour plus
    ``anime_episode`` (the episode's number inside the cour) and ``next_anilist_id`` (the next cour of
    the same season, or None); it is None when the index cannot say, with reason ``no_data`` (the index
    carries no TMDb season for this show at all), ``other_season`` (it carries seasons, but none is this
    one) or ``ambiguous`` (two entries share an episode offset, the first cour's offset is not 0, or the
    episode lies before the first listed cour).  TV/ONA entries are used; a season that only has OVA
    entries (the list files some whole seasons under OVA) uses those.  Only the cached ``lookup`` stays show-level: nothing
    here is cached or written.  Offsets are the list's own and about 1 in 10 are off by an episode, so
    callers that need certainty must check the result against an air date."""
    season, episode = _int(season), _int(episode)
    if not season or season < 1 or not episode or episode < 1:
        return None, "no_data"
    conn = _connect()
    if conn is None:
        return None, "no_data"
    try:
        # season_rank is a season of that TMDb show, so the TMDb id decides; an IMDb id is used only without one
        if _int(tmdb_id):
            clause, value = "tmdb_tv=?", _int(tmdb_id)
        elif imdb_id:
            clause, value = "id IN (SELECT anime_id FROM imdb WHERE imdb_id=?)", str(imdb_id)
        else:
            return None, "no_data"
        rows = []
        for kind in ("type_rank <= 1", "type = 'OVA'"):
            rows = conn.execute(
                f"SELECT * FROM anime WHERE {_HAS_ANIME_ID} AND {kind} AND season_rank=? AND {clause} "
                f"ORDER BY type_rank, tmdb_offset, COALESCE(mal_id, anilist_id)", (season, value)).fetchall()
            if rows:
                break
        if not rows:
            known = conn.execute(
                f"SELECT 1 FROM anime WHERE {_HAS_ANIME_ID} AND type_rank <= 1 AND season_rank NOT IN (?, 999) AND {clause} LIMIT 1",
                (season, value)).fetchone()
            return None, "other_season" if known else "no_data"
        if any(row["type_rank"] == 0 for row in rows):
            rows = [row for row in rows if row["type_rank"] == 0]
        offsets = [row["tmdb_offset"] for row in rows]
        if len(set(offsets)) < len(offsets) or offsets[0] != 0:
            return None, "ambiguous"    # tied offsets, or a first cour that does not start the season
        chosen = [index for index, offset in enumerate(offsets) if offset < episode]
        if not chosen:
            return None, "ambiguous"
        row = rows[chosen[-1]]
        following = rows[chosen[-1] + 1] if chosen[-1] + 1 < len(rows) else None
        return {
            "anilist_id": row["anilist_id"],
            "mal_id": row["mal_id"],
            "anidb_id": row["anidb_id"],
            "kitsu_id": row["kitsu_id"],
            "simkl_id": row["simkl_id"],
            "thetvdb_id": row["tvdb_id"],
            "themoviedb_id": row["tmdb_tv"],
            "thetvdb_season": _season_value(row),
            "thetvdb_part": None,
            "anime_episode": episode - row["tmdb_offset"],
            "tmdb_offset": row["tmdb_offset"],
            "tmdb_season": row["season_rank"],
            "next_anilist_id": following["anilist_id"] if following else None,
        }, None
    except Exception as e:
        g.log(f"Fribb episode lookup failed: {e}", "debug")
        return None, "no_data"
    finally:
        conn.close()


def bridge_records(anilist_ids):
    """{AniList id: {'kind': 'tv', 'ids': [TMDb TV id], 'season': TMDb season or None, 'offset': episode offset}} for the AniList ids the
    index knows a TMDb TV id for (the cross-service bridge maps Simkl's per-cour anime entries with it). ``season`` is None when the
    index carries no TMDb season (or season 0: specials are not bridged). Reads only."""
    ids = [i for i in dict.fromkeys(_int(x) for x in anilist_ids) if i]
    conn = _connect() if ids else None
    if conn is None:
        return {}
    out = {}
    try:
        for start in range(0, len(ids), 500):
            chunk = ids[start:start + 500]
            query = (f"SELECT anilist_id, tmdb_tv, season_rank, tmdb_offset FROM anime WHERE tmdb_tv IS NOT NULL AND anilist_id IN "
                     f"({','.join('?' * len(chunk))}) ORDER BY id")
            for row in conn.execute(query, chunk):
                if row["anilist_id"] not in out:
                    season = row["season_rank"]
                    out[row["anilist_id"]] = {
                        "kind": "tv",
                        "ids": [row["tmdb_tv"]],
                        "season": None if not season or season == 999 else season,
                        "offset": row["tmdb_offset"] or 0,
                    }
    except Exception as e:
        g.log(f"Fribb bridge records failed: {e}", "debug")
        return {}
    finally:
        conn.close()
    return out


def bridge_tv_entries(tmdb_id):
    """[(AniList id, TMDb season or None, episode offset)] of the index's entries for a TMDb TV id, lowest AniList id first; empty when the
    show is unknown or there is no index. Reads only."""
    tmdb = _int(tmdb_id)
    conn = _connect() if tmdb else None
    if conn is None:
        return []
    try:
        seen, out = set(), []
        for row in conn.execute("SELECT anilist_id, season_rank, tmdb_offset FROM anime WHERE tmdb_tv=? AND anilist_id IS NOT NULL "
                                "ORDER BY anilist_id, id", (tmdb,)):
            if row["anilist_id"] in seen:
                continue
            seen.add(row["anilist_id"])
            season = row["season_rank"]
            out.append((row["anilist_id"], None if not season or season == 999 else season, row["tmdb_offset"] or 0))
        return out
    except Exception as e:
        g.log(f"Fribb bridge entries failed: {e}", "debug")
        return []
    finally:
        conn.close()


def bridge_mal_id(tmdb_id, anilist_id):
    """MAL id of an AniList entry of a TMDb TV show (sent along with the AniList id to Simkl), or None."""
    tmdb, anilist = _int(tmdb_id), _int(anilist_id)
    conn = _connect() if tmdb and anilist else None
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT mal_id FROM anime WHERE tmdb_tv=? AND anilist_id=? AND mal_id IS NOT NULL LIMIT 1", (tmdb, anilist)).fetchone()
        return row["mal_id"] if row else None
    except Exception as e:
        g.log(f"Fribb bridge mal id failed: {e}", "debug")
        return None
    finally:
        conn.close()


def lookup_anidb(anidb_id):
    """{'imdb_id', 'themoviedb_id'} for an AniDB id (TMDb TV id only, never a movie id), or None."""
    anidb = _int(anidb_id)
    conn = _connect() if anidb else None
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT id, tmdb_tv FROM anime WHERE anidb_id=? LIMIT 1", (anidb,)).fetchone()
        if row is None:
            return None
        imdb = conn.execute("SELECT imdb_id FROM imdb WHERE anime_id=? ORDER BY rowid LIMIT 1", (row["id"],)).fetchone()
        return {"imdb_id": imdb["imdb_id"] if imdb else None, "themoviedb_id": row["tmdb_tv"]}
    except Exception as e:
        g.log(f"Fribb AniDB lookup failed: {e}", "debug")
        return None
    finally:
        conn.close()


def _meta(conn, key):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def _current_state():
    """(built_at, entry count) of the index on disk, (0, 0) when there is none."""
    conn = _connect()
    if conn is None:
        return 0, 0
    try:
        return _int(_meta(conn, "built_at")) or 0, _int(_meta(conn, "count")) or 0
    except Exception:
        return 0, 0
    finally:
        conn.close()


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _build(entries, path):
    """Write the index for the entries to path; returns the number of rows."""
    _remove(path)
    conn = sqlite3.connect(path)
    try:
        for statement in _SCHEMA:
            conn.execute(statement)
        rows = 0
        with conn:
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                anilist, mal, anidb = _int(entry.get("anilist_id")), _int(entry.get("mal_id")), _int(entry.get("anidb_id"))
                if not (anilist or mal or anidb):
                    continue
                tmdb = entry.get("themoviedb_id") if isinstance(entry.get("themoviedb_id"), dict) else {}
                season = entry.get("season") if isinstance(entry.get("season"), dict) else {}
                offset = entry.get("episode_offset") if isinstance(entry.get("episode_offset"), dict) else {}
                kind = entry.get("type")
                tmdb_season = _int(season.get("tmdb"))
                cursor = conn.execute(
                    "INSERT INTO anime (type_rank, season_rank, tmdb_offset, type, anilist_id, mal_id, anidb_id, kitsu_id, "
                    "simkl_id, tvdb_id, tvdb_season, tmdb_tv) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        0 if kind == "TV" else 1 if kind == "ONA" else 2,
                        tmdb_season if tmdb_season else 999,
                        _int(offset.get("tmdb")) or 0,
                        kind, anilist, mal, anidb, _int(entry.get("kitsu_id")), _int(entry.get("simkl_id")),
                        _int(entry.get("tvdb_id")), _int(season.get("tvdb")), _int(tmdb.get("tv")),
                    ),
                )
                for imdb in entry.get("imdb_id") or ():
                    if isinstance(imdb, str) and imdb.startswith("tt"):
                        conn.execute("INSERT INTO imdb (imdb_id, anime_id) VALUES (?,?)", (imdb, cursor.lastrowid))
                rows += 1
            conn.execute("INSERT INTO meta VALUES ('source', 'fribb')")
            conn.execute("INSERT INTO meta VALUES ('built_at', ?)", (str(int(time.time())),))
            conn.execute("INSERT INTO meta VALUES ('count', ?)", (str(rows),))
        return rows
    finally:
        conn.close()


def update_db(force=False):
    """Download the Fribb list and rebuild the index when it is older than a week.

    Also removes the Otaku-Mappings file left by earlier versions.  The old index is kept when the
    download fails or the new list looks broken.  Returns True when a usable index is on disk."""
    _remove(os.path.join(g.ADDON_USERDATA_PATH, _LEGACY_DB_NAME))
    built_at, old_count = _current_state()
    if not force and built_at and 0 <= time.time() - built_at < _REFRESH_SECONDS:
        g.log(f"Fribb anime index is {(time.time() - built_at) / 86400:.1f} days old, skipping update", "debug")
        return True

    path = db_path()
    suffix = f".{os.getpid()}.tmp"
    json_tmp, db_tmp = path + ".json" + suffix, path + suffix
    g.log("Updating Fribb anime index...", "info")
    try:
        response = requests.get(FRIBB_URL, stream=True, timeout=(10, 60), headers={"User-Agent": "Seren"})
        response.raise_for_status()
        with open(json_tmp, "wb") as handle:
            for chunk in response.iter_content(65536):
                if g.abort_requested():
                    return bool(old_count)
                handle.write(chunk)
        with open(json_tmp, "rb") as handle:
            entries = json.load(handle)
        _remove(json_tmp)
        if not isinstance(entries, list) or len(entries) < _MIN_ENTRIES:
            g.log(f"Fribb list rejected: {len(entries) if isinstance(entries, list) else type(entries).__name__} entries", "warning")
            return bool(old_count)
        if g.abort_requested():
            return bool(old_count)
        rows = _build(entries, db_tmp)
        del entries
        if rows < _MIN_ENTRIES or (old_count and rows < old_count * _SHRINK_FLOOR):
            g.log(f"Fribb index rejected: {rows} rows (current index has {old_count})", "warning")
            return bool(old_count)
        os.replace(db_tmp, path)
        g.log(f"Fribb anime index updated: {rows} entries", "info")
        return True
    except Exception as e:
        g.log(f"Fribb anime index update failed: {e}", "warning")
        return bool(old_count)
    finally:
        _remove(json_tmp)
        _remove(db_tmp)
