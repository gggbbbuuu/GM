"""Simkl anime entries <-> TMDb season / episode numbers for the cross-service bridge (bridgeSync.py).

Ported from TMDb Helper 7.0.55 (api/anilist/entry_map.py + the entry lookup of episodes.py), whose mapping is proven live on this
account; only the data access differs (Seren's animeFribb.db through fribb_mapping.bridge_*, AniZip and TMDb reads cached in
animeBridgeCache.db).

Simkl keeps every anime cour as its own entry with episodes numbered from 1. The Fribb index says which TMDb show and season an
entry belongs to and how many TMDb episodes come before it (`offset`), so episode N of an entry is TMDb episode `offset + N`.
A Fribb offset is wrong about one time in seven, so an entry that needs an offset, or that shares its TMDb season with another
entry, is only taken for episodes whose air date AniZip and TMDb agree on. An episode that cannot be confirmed is left out, never
guessed: it is simply not bridged.

Two cases where the index is wrong are repaired here, each only for an episode whose AniZip and TMDb air dates agree: an entry the
index puts in a season TMDb does not have (TMDb keeps the cours in season 1: the entry starts after `TMDb's episode count - the
entry's episode count` episodes of the last season TMDb has, and it must be the only such entry of the show), and an entry whose
offset runs past the end of its TMDb season (the offset becomes `season's episode count - the entry's episode count`).
"""
import json
import os
import sqlite3
import sys
import time

from datetime import date

from resources.lib.modules.anime import fribb_mapping as fribb
from resources.lib.modules.globals import g

ANIZIP_URL = "https://api.ani.zip/mappings"
CACHE_DB = "animeBridgeCache.db"
DATE_TOLERANCE = 3                    # days between the TMDb and the AniZip air date of the same episode
TIMEOUT = 5
MAX_FETCHES = 200                     # AniZip entries fetched per run (an entry is cached for 30 days once all its episodes have aired)
MAX_CANDIDATES = 4                    # entries tried for one episode
TTL_SETTLED = 30 * 24 * 3600
TTL_AIRING = 24 * 3600                # an entry with an episode aired in the last AIRING_WINDOW (or still to air)
AIRING_WINDOW = 45 * 24 * 3600
TTL_FAILED = 10 * 60
TTL_TMDB = 12 * 3600

episodes = sys.modules[__name__]      # the mapping code below calls episodes.entry_status / episodes.entry_for_episode

_memory = {}                          # per process: AniList id -> {number: {'airdate': 'YYYY-MM-DD'}}
_tmdb_memory = {}
_index_memo = {}
_fetched = 0


def kodi_log(message, level=1):
    g.log(message, "info" if level >= 1 else "debug")


def begin_run():
    """Forget what this process remembers (the service lives for hours): call at the start of every bridge run."""
    global _fetched
    _memory.clear()
    _tmdb_memory.clear()
    _index_memo.clear()
    _fetched = 0


# region cache + fetch

def _connect():
    try:
        conn = sqlite3.connect(os.path.join(g.ADDON_USERDATA_PATH, CACHE_DB), timeout=3)
        conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, fetched REAL, ttl REAL, ok INTEGER, value TEXT)")
        return conn
    except sqlite3.Error as e:
        kodi_log(f"Anime bridge cache unavailable: {type(e).__name__}", 0)
        return None


def _cache_read(key, now):
    """(fresh, value or None, stale value or None): the saved answer for a key."""
    conn = _connect()
    if conn is None:
        return False, None, None
    try:
        row = conn.execute("SELECT fetched, ttl, ok, value FROM kv WHERE key=?", (key,)).fetchone()
        if not row:
            return False, None, None
        value = json.loads(row[3]) if row[2] and row[3] else None
        return now - row[0] < row[1], value, value
    except (sqlite3.Error, ValueError):
        return False, None, None
    finally:
        conn.close()


def _cache_write(key, value, ttl, ok, now):
    conn = _connect()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("INSERT OR REPLACE INTO kv VALUES (?,?,?,?,?)", (key, now, ttl, 1 if ok else 0, json.dumps(value) if ok else None))
    except sqlite3.Error as e:
        kodi_log(f"Anime bridge cache write failed: {type(e).__name__}", 0)
    finally:
        conn.close()


def _to_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _anizip_episodes(anilist_id):
    """{number: {'airdate': 'YYYY-MM-DD'}} of one AniList entry from AniZip, {} for an id AniZip does not know, None when it could not be had
    right now (fetch cap or failure)."""
    global _fetched
    if anilist_id in _memory:
        return _memory[anilist_id]
    now = time.time()
    key = f"az:{anilist_id}"
    fresh, value, stale = _cache_read(key, now)
    if fresh:
        result = {int(k): v for k, v in value.items()} if value is not None else None
        if result is not None:
            _memory[anilist_id] = result
        return result
    if _fetched >= MAX_FETCHES:
        return {int(k): v for k, v in stale.items()} if stale else None
    _fetched += 1
    import requests
    result = None
    try:
        response = requests.get(ANIZIP_URL, params={"anilist_id": str(anilist_id)}, timeout=TIMEOUT, headers={"User-Agent": "Seren"})
        if response.status_code == 404:
            result = {}
        elif response.status_code == 200:
            data = response.json()
            eps = data.get("episodes") if isinstance(data, dict) else None
            result = {}
            for number, ep in (eps.items() if isinstance(eps, dict) else ()):
                if str(number).isdigit() and int(number) >= 1 and isinstance(ep, dict):
                    result[int(number)] = {"airdate": str(ep.get("airDate") or ep.get("airdate") or "")[:10]}
    except Exception as e:
        kodi_log(f"Anime bridge: AniZip request failed for {anilist_id}: {type(e).__name__}", 1)
        result = None
    if result is None:
        _cache_write(key, stale, TTL_FAILED, bool(stale), now)
        return {int(k): v for k, v in stale.items()} if stale else None
    airing = any(_to_date(e["airdate"]) is None or time.mktime(_to_date(e["airdate"]).timetuple()) > now - AIRING_WINDOW for e in result.values())
    _cache_write(key, {str(k): v for k, v in result.items()}, TTL_AIRING if (airing or not result) else TTL_SETTLED, True, now)
    _memory[anilist_id] = result
    return result


def _tmdb_raw(path):
    """Raw TMDb JSON for 'tv/<id>' or 'tv/<id>/season/<n>' (cached 12 hours), or None."""
    if path in _tmdb_memory:
        return _tmdb_memory[path]
    now = time.time()
    fresh, value, stale = _cache_read(f"tmdb:{path}", now)
    if fresh and value is not None:
        _tmdb_memory[path] = value
        return value
    data = None
    try:
        from resources.lib.indexers.tmdb import TMDBAPI
        response = TMDBAPI().get(path, timeout=10)
        data = response.json() if response is not None else None
    except Exception as e:
        kodi_log(f"Anime bridge: TMDb {path} failed - {type(e).__name__}", 1)
    if isinstance(data, dict) and data:
        _cache_write(f"tmdb:{path}", data, TTL_TMDB, True, now)
        _tmdb_memory[path] = data
        return data
    return stale if isinstance(stale, dict) else None


class TmdbReader:
    """What the mapping code asks TMDb: the show (seasons with episode_count) or one season (episodes with air_date)."""

    @staticmethod
    def get_request_sc(kind, tmdb_id, sub=None, season=None):
        return _tmdb_raw(f"tv/{tmdb_id}" if sub is None else f"tv/{tmdb_id}/season/{season}")


# endregion

# region entry lookup (episodes.py of TMDb Helper)

def _index_entries(tmdb_id):
    key = str(tmdb_id)
    if key not in _index_memo:
        _index_memo[key] = fribb.bridge_tv_entries(tmdb_id)
    return _index_memo[key]


def entry_for_episode(tmdb_id, season, episode, tmdb_airdate=None):
    """(AniList id, number inside the entry) or None - see entry_status, which also says WHY there is none."""
    return entry_status(tmdb_id, season, episode, tmdb_airdate)[1]


def entry_status(tmdb_id, season, episode, tmdb_airdate=None):
    """('ok', (AniList id, number inside the entry)), ('later', None) when AniZip could not be asked right now, or ('none', None) when
    no entry fits, for TMDb episode `season`x`episode` of a show the Fribb index knows. A mapping only counts when AniZip's air date
    agrees with TMDb's within DATE_TOLERANCE days; with no air date to check, only a single candidate counts."""
    entries = _index_entries(tmdb_id)
    if not entries:
        return "none", None
    try:
        season, episode = int(season), int(episode)
    except (ValueError, TypeError):
        return "none", None
    if season < 1 or episode < 1:
        return "none", None
    candidates = [(anilist_id, offset or 0) for anilist_id, entry_season, offset in entries
                  if entry_season == season and (offset or 0) < episode]
    candidates.sort(key=lambda c: (-c[1], c[0]))
    candidates = candidates[:MAX_CANDIDATES]
    tmdb_date = _to_date(tmdb_airdate) if tmdb_airdate else None
    later = False
    for anilist_id, offset in candidates:
        eps = _anizip_episodes(anilist_id)
        if eps is None:
            later = True
            continue
        data = eps.get(episode - offset)
        if not data:
            continue
        aired = _to_date(data["airdate"])
        if tmdb_date and aired:
            if abs((aired - tmdb_date).days) > DATE_TOLERANCE:
                continue
        elif len(candidates) > 1:
            continue
        return "ok", (anilist_id, episode - offset)
    return ("later" if later else "none"), None

# endregion

# region mapping (entry_map.py of TMDb Helper, unchanged apart from the data access)

def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _airdates(tmdb_api, cache, tmdb_id, season):
    """{episode number: air date} of one TMDb season, or None when TMDb could not be asked (the episodes are then unconfirmed)."""
    key = (tmdb_id, season)
    if key not in cache:
        try:
            data = tmdb_api.get_request_sc('tv', tmdb_id, 'season', season) if tmdb_api else None
        except Exception as exc:
            kodi_log(f'Anime entry map: TMDb season {tmdb_id} S{season} failed - {type(exc).__name__}', 1)
            data = None
        cache[key] = {e.get('episode_number'): e.get('air_date') for e in (data or {}).get('episodes') or []} if data else None
    return cache[key]


def _season_counts(tmdb_api, cache, tmdb_id):
    """{season number: episode count (None when TMDb does not say)} of a TMDb show, or None when TMDb could not be asked."""
    key = (tmdb_id, 'counts')
    if key not in cache:
        try:
            data = tmdb_api.get_request_sc('tv', tmdb_id) if tmdb_api else None
        except Exception as exc:
            kodi_log(f'Anime entry map: TMDb show {tmdb_id} failed - {type(exc).__name__}', 1)
            data = None
        seasons = (data or {}).get('seasons') if isinstance(data, dict) else None
        cache[key] = {s.get('season_number'): s.get('episode_count') for s in seasons} if seasons else None
    return cache[key]


def _season_missing(tmdb_api, cache, tmdb_id, season):
    """True only when TMDb answered for the show and its season list does not hold `season` (the index says season 2 but TMDb keeps
    the cours merged in season 1): Trakt and MDBList would refuse every episode, and the bridge would send them again every cycle.
    A failed request never counts as 'missing'."""
    counts = _season_counts(tmdb_api, cache, tmdb_id)
    return counts is not None and season not in counts


def _entry_episodes(anilist_id):
    """AniZip's {number: dict} for an entry, or None when it could not be had right now."""
    try:
        return _anizip_episodes(anilist_id)
    except Exception:
        return None


def _to_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _alternative(tmdb_id, anilist_id, season, offset, tmdb_api, cache):
    """Where the index's (season, offset) of an entry is wrong, the placement the episode counts imply:
    ('ok', (season, offset, AniZip episodes of the entry)), ('later', None) when AniZip could not be asked, else ('none', None).
    Never used without an air-date check per episode (_confirm)."""
    counts = _season_counts(tmdb_api, cache, tmdb_id)
    if not counts or season is None or season < 1:
        return 'none', None
    if season in counts:
        total = counts[season]
        if offset <= 0 or not total:
            return 'none', None
        target = season
    else:
        if [a for a, s, _o in fribb.bridge_tv_entries(tmdb_id) if s is not None and s >= 1 and s not in counts] != [anilist_id]:
            return 'none', None                       # several entries in missing seasons: where each starts is not clear
        bases = [s for s in counts if s is not None and 1 <= s < season]
        total = counts[max(bases)] if bases else None
        if not total:
            return 'none', None
        target = max(bases)
    eps = _entry_episodes(anilist_id)
    if eps is None:
        return 'later', None
    if not eps:
        return 'none', None
    new = total - max(eps)
    if new < (0 if target == season else 1) or (target == season and new == offset):
        return 'none', None
    return 'ok', (target, new, eps)


def _confirm(tmdb_api, cache, tmdb_id, season, tmdb_episode, number, eps):
    """True when TMDb's and AniZip's air dates of this episode both exist and agree."""
    dates = _airdates(tmdb_api, cache, tmdb_id, season)
    if not dates:
        return False
    tmdb_date, aired = _to_date(dates.get(tmdb_episode)) if dates.get(tmdb_episode) else None, _to_date((eps.get(number) or {}).get('airdate'))
    return bool(tmdb_date and aired and abs((aired - tmdb_date).days) <= DATE_TOLERANCE)


def map_entries(entries, tmdb_api=None, season_cache=None, coords=None):
    """entries: {AniList id: {'tmdb': Simkl's TMDb id or None, 'eps': {episode number in the entry: watched_at}}}.

    Returns ({'tmdb:season:episode': watched_at}, stats). Reads only: the Fribb index, the AniZip cache and (for entries that need a
    check) TMDb season lists. `stats` counts what was left out and why, for the log. When `coords` is a dict it is filled with
    {'tmdb:season:episode': (AniList id, number inside the entry)} for every key returned (what un-watches are checked against)."""
    stats = {'entries': 0, 'mapped_entries': 0, 'episodes': 0, 'no_record': 0, 'not_tv': 0, 'tmdb_mismatch': 0,
             'checked_ok': 0, 'unconfirmed': 0, 'rejected': 0, 'no_season': 0}
    out = {}
    ids = {}
    for key in entries:
        anilist_id = _int(key)
        if anilist_id:
            ids[anilist_id] = entries[key]
    records = fribb.bridge_records(list(ids)) if ids else {}
    season_cache = {} if season_cache is None else season_cache
    for anilist_id, entry in sorted(ids.items()):
        eps = entry.get('eps') or {}
        stats['entries'] += 1
        stats['episodes'] += len(eps)
        rec = records.get(anilist_id)
        if not rec:
            stats['no_record'] += len(eps)
            continue
        if rec['kind'] != 'tv' or rec['season'] is None:
            stats['not_tv'] += len(eps)
            continue
        simkl_tmdb = _int(entry.get('tmdb'))
        if simkl_tmdb:
            if simkl_tmdb not in rec['ids']:
                stats['tmdb_mismatch'] += len(eps)     # Simkl and Fribb disagree which show this is: never guess
                kodi_log(f'Anime entry map: AniList {anilist_id}: Simkl TMDb {simkl_tmdb} is not Fribb\'s {rec["ids"]} - left out', 1)
                continue
            tmdb_id = simkl_tmdb
        elif len(rec['ids']) == 1:
            tmdb_id = rec['ids'][0]
        else:
            stats['tmdb_mismatch'] += len(eps)
            continue
        season, offset = int(rec['season']), int(rec['offset'] or 0)
        missing = _season_missing(tmdb_api, season_cache, tmdb_id, season)
        shared = sum(1 for _, s, _o in fribb.bridge_tv_entries(tmdb_id) if s == season) > 1
        check = offset > 0 or shared
        totals = _season_counts(tmdb_api, season_cache, tmdb_id) or {}
        fixed = None                                   # the repair for this entry, worked out at the first episode the index cannot place
        logged = False
        mapped_here = 0
        for number, stamp in eps.items():
            n = _int(number)
            if not n or n < 1:
                continue
            placed = None
            why = 'rejected'
            if not missing:
                tmdb_episode = offset + n
                if check and totals.get(season) and tmdb_episode > totals[season]:
                    pass                                 # TMDb has no such episode: the index offset cannot be right (a plain entry is trusted: TMDb's count can lag an airing show)
                elif check:
                    dates = _airdates(tmdb_api, season_cache, tmdb_id, season)
                    if dates is None:
                        stats['unconfirmed'] += 1
                        continue
                    found = episodes.entry_for_episode(tmdb_id, season, tmdb_episode, dates.get(tmdb_episode))
                    if found == (anilist_id, n):
                        stats['checked_ok'] += 1
                        placed = (season, tmdb_episode)
                    else:
                        why = 'rejected' if found or dates.get(tmdb_episode) else 'unconfirmed'
                else:
                    placed = (season, tmdb_episode)
            if placed is None:
                if fixed is None:
                    fixed = _alternative(tmdb_id, anilist_id, season, offset, tmdb_api, season_cache)
                if fixed[0] == 'ok':
                    alt_season, alt_offset, alt_eps = fixed[1]
                    alt_episode = alt_offset + n
                    key = f'{tmdb_id}:{alt_season}:{alt_episode}'
                    if (alt_episode <= (totals.get(alt_season) or alt_episode) and key not in out
                            and _confirm(tmdb_api, season_cache, tmdb_id, alt_season, alt_episode, n, alt_eps)):
                        stats['checked_ok'] += 1
                        placed = (alt_season, alt_episode)
                if placed is None:
                    if missing and fixed[0] == 'none':
                        stats['no_season'] += 1
                        if not logged:
                            logged = True
                            kodi_log(f'Anime entry map: AniList {anilist_id}: TMDb {tmdb_id} has no season {season} - left out', 1)
                    else:
                        stats['unconfirmed' if (fixed[0] == 'later' or missing) else why] += 1
                    continue
            out[f'{tmdb_id}:{placed[0]}:{placed[1]}'] = stamp or ''
            if coords is not None:
                coords[f'{tmdb_id}:{placed[0]}:{placed[1]}'] = (anilist_id, n)
            mapped_here += 1
        if mapped_here:
            stats['mapped_entries'] += 1
    return out, stats


def _forward_alternative(tmdb_id, season, episode, tmdb_api, cache):
    """('ok', (AniList id, number)) / ('later', None) / ('none', None) for a TMDb episode the index places nowhere, by the repairs above."""
    later = False
    for anilist_id, entry_season, offset in sorted(fribb.bridge_tv_entries(tmdb_id), key=lambda e: e[0]):
        if entry_season is None:
            continue
        state, value = _alternative(tmdb_id, anilist_id, entry_season, offset or 0, tmdb_api, cache)
        if state == 'later':
            later = True
            continue
        if state != 'ok' or value[0] != season:
            continue
        target, new, eps = value
        number = episode - new
        if 1 <= number <= max(eps) and _confirm(tmdb_api, cache, tmdb_id, season, episode, number, eps):
            return 'ok', (anilist_id, number)
    return ('later' if later else 'none'), None


def forward_entry(tmdb_id, season, episode, tmdb_api=None, cache=None):
    """TMDb episode -> the Simkl anime entry it belongs to, for sending a watched mark to Simkl.

    ('ok', {'anilist': id, 'number': n, 'ids': {'anilist': id, 'mal': id}}), ('later', None) when AniZip or TMDb could not be asked
    right now, or ('none', None) when no entry fits. Every 'ok' is round-tripped through map_entries (the same mapping that reads Simkl
    back): what we send must read back as the very episode it came from, or Simkl would hold (entry, n) and the reverse direction would
    copy a DIFFERENT TMDb episode to Trakt."""
    cache = {} if cache is None else cache
    dates = _airdates(tmdb_api, cache, tmdb_id, int(season))
    if dates is None:
        return 'later', None
    status, found = episodes.entry_status(tmdb_id, season, episode, dates.get(int(episode)))
    if status == 'none':
        status, found = _forward_alternative(tmdb_id, int(season), int(episode), tmdb_api, cache)
    if status != 'ok':
        return status, None
    anilist_id, number = found
    back, _stats = map_entries({anilist_id: {'tmdb': tmdb_id, 'eps': {number: ''}}}, tmdb_api, cache)
    if f'{tmdb_id}:{int(season)}:{int(episode)}' not in back:
        return 'none', None
    ids = {'anilist': anilist_id}
    mal_id = fribb.bridge_mal_id(tmdb_id, anilist_id)
    if mal_id:
        ids['mal'] = mal_id
    return 'ok', {'anilist': anilist_id, 'number': number, 'ids': ids}

# endregion
