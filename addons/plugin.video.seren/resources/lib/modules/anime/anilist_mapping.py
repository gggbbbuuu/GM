"""Anime ID Mapping — bridges Seren's TMDB/IMDB/Trakt IDs to all anime database IDs.

Primary source:  Fribb anime-lists, converted to an offline SQLite index (see fribb_mapping.py).
Fallback 1:      arm.haglund.dev API (the service Fribb's list also feeds).
Fallback 2:      AniList reverse search (title → AniList ID → cross-reference via ARM).
Fallback 3:      Simkl API (public, client_id only — no user auth required).

The Fribb list (github.com/Fribb/anime-lists) gives instant offline lookups by IMDb or TMDb TV id.
It contains: mal_id, anilist_id, kitsu_id, anidb_id, simkl_id, thetvdb_id, themoviedb_id,
imdb_id, plus the TVDB/TMDb season and episode offset. It has no Trakt ids and no TVDB part
number, so a lookup by Trakt id alone finds nothing here (every caller also passes imdb/tmdb)
and thetvdb_part is always None.

Maps between: anilist, mal, thetvdb, themoviedb, imdb, anidb, kitsu, simkl.

Results are cached in SQLite (anime_id_map table in animeCache.db) with 30-day TTL,
surviving across sessions.  A fast module-level dict provides L1 cache within the
current session to avoid repeated DB reads.
"""

import datetime
import time

import requests

from resources.lib.modules.globals import g

# L1 session cache: {cache_key: {anilist_id, mal_id, anidb_id, kitsu_id, ...}}
# Backed by SQLite L2 cache in AnimeCache.anime_id_map (30-day TTL).
_id_cache = {}

# Simkl public API — only needs client_id, no user authentication
_SIMKL_CLIENT_ID = '59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8'
_SIMKL_BASE = 'https://api.simkl.com'

# AniList GraphQL endpoint
_ANILIST_URL = 'https://graphql.anilist.co'


def get_anime_ids(imdb_id=None, tmdb_id=None, trakt_id=None):
    """Map IMDB, TMDB, or Trakt ID to all anime database IDs.

    Args:
        imdb_id: IMDB ID string (e.g. "tt5370118")
        tmdb_id: TMDB ID int or string
        trakt_id: Trakt show ID int or string (cache key only; the Fribb index has no Trakt ids,
                  so a call with only a Trakt id is answered by the online fallbacks, which
                  cannot resolve it either and return None)

    Returns:
        dict with keys: anilist_id, mal_id, anidb_id, kitsu_id, thetvdb_id,
        themoviedb_id, simkl_id.  Any value may be None if unmapped.
        Returns None entirely if no mapping found at all.
    """
    if imdb_id:
        cache_key = imdb_id
    elif tmdb_id:
        cache_key = f"tmdb_{tmdb_id}"
    elif trakt_id:
        cache_key = f"trakt_{trakt_id}"
    else:
        return None

    # ── L1: session dict ─────────────────────────────────────────────────
    if cache_key in _id_cache:
        return _id_cache[cache_key]

    # ── L2: SQLite persistent cache (30-day TTL) ─────────────────────────
    result = _get_from_sqlite(cache_key)
    if result:
        _id_cache[cache_key] = result
        return result

    result = None

    # ── Stage 0: Fribb local index (instant, offline; no Trakt ids in it) ─
    result = _query_mapping_db(imdb_id=imdb_id, tmdb_id=tmdb_id)
    if result:
        g.log(
            f"Anime ID mapping (Fribb index): "
            f"MAL={result.get('mal_id')}, AniDB={result.get('anidb_id')}, "
            f"Simkl={result.get('simkl_id')}, Kitsu={result.get('kitsu_id')}",
            "debug"
        )

    # ── Stage 1: ARM API fallback (if DB missed or incomplete) ───────────
    if not result:
        if imdb_id:
            result = _query_arm(imdb_id, "imdb")
        if not result and tmdb_id:
            result = _query_arm(str(tmdb_id), "tmdb")

    # ── Stage 2: AniList reverse search (title → AniList ID) ────────────
    if not result:
        result = _anilist_reverse_search(imdb_id=imdb_id, tmdb_id=tmdb_id)

    # ── Stage 3: Simkl fallback for missing AniDB ────────────────────────
    if result and not result.get('anidb_id'):
        anidb_from_simkl = _simkl_get_anidb(
            mal_id=result.get('mal_id'),
            anilist_id=result.get('anilist_id'),
            imdb_id=imdb_id,
            tmdb_id=tmdb_id
        )
        if anidb_from_simkl:
            result.update(anidb_from_simkl)

    # ── Stage 4: Full Simkl fallback if everything else returned nothing ─
    if not result:
        result = _simkl_full_lookup(imdb_id=imdb_id, tmdb_id=tmdb_id)

    # ── Persist to both caches ───────────────────────────────────────────
    _id_cache[cache_key] = result
    if result:
        _save_to_sqlite(cache_key, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  SQLite Persistent Cache (L2) — via AnimeCache
# ═══════════════════════════════════════════════════════════════════════════

def _get_from_sqlite(cache_key):
    """Read cached ID mapping from SQLite.  Returns dict or None."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        row = AnimeCache().get_id_map(cache_key)
        if row and (row.get('anilist_id') or row.get('mal_id')):
            g.log(f"Anime ID mapping (SQLite cache hit): key={cache_key}", "debug")
            return row
    except Exception as e:
        g.log(f"Anime ID SQLite read failed: {e}", "debug")
    return None


def _save_to_sqlite(cache_key, ids):
    """Persist ID mapping to SQLite cache."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        AnimeCache().set_id_map(cache_key, ids)
    except Exception as e:
        g.log(f"Anime ID SQLite write failed: {e}", "debug")


# ═══════════════════════════════════════════════════════════════════════════
#  Fribb offline index (github.com/Fribb/anime-lists) — see fribb_mapping.py
# ═══════════════════════════════════════════════════════════════════════════

def _query_mapping_db(imdb_id=None, tmdb_id=None):
    """Query the local Fribb index for anime ID mappings (IMDb id first, then TMDb TV id).

    Returns full ID dict or None.
    """
    from resources.lib.modules.anime.fribb_mapping import lookup
    return lookup(imdb_id=imdb_id, tmdb_id=tmdb_id)


def update_mapping_db():
    """Download or refresh the Fribb index, and remove the Otaku-Mappings file older versions left.

    Called from housekeeping at startup and from the updateAnimeMappings action.
    Skips the download if the index was built within the last 7 days.
    """
    from resources.lib.modules.anime.fribb_mapping import update_db
    return update_db()


# ═══════════════════════════════════════════════════════════════════════════
#  ARM API (arm.haglund.dev)
# ═══════════════════════════════════════════════════════════════════════════

def _query_arm(external_id, source):
    """Query arm.haglund.dev to map external IDs to all anime database IDs.

    Returns:
        dict with all available ID fields, or None.
    """
    url_map = {
        "imdb":     f"https://arm.haglund.dev/api/v2/imdb?id={external_id}",
        "tmdb":     f"https://arm.haglund.dev/api/v2/themoviedb?id={external_id}",
        "thetvdb":  f"https://arm.haglund.dev/api/v2/thetvdb?id={external_id}",
    }
    url = url_map.get(source)
    if not url:
        return None

    try:
        response = requests.get(url, timeout=5, headers={"User-Agent": "Seren"})
        if not response.ok:
            return None

        data = response.json()
        if not data:
            return None

        # ARM API returns a list when multiple anime map to the same external ID
        # (e.g. multi-season shows).  Take the first entry (typically best match).
        if isinstance(data, list):
            data = data[0] if data else None
            if not data:
                return None

        result = _extract_arm_ids(data)
        if not result:
            return None

        g.log(
            f"Anime ID mapping (ARM): {source}={external_id} → "
            f"AniList={result.get('anilist_id')}, MAL={result.get('mal_id')}, "
            f"AniDB={result.get('anidb_id')}, Kitsu={result.get('kitsu_id')}",
            "debug"
        )
        return result

    except requests.RequestException as e:
        g.log(f"ARM API failed ({source}={external_id}): {e}", "warning")
        return None
    except (ValueError, KeyError) as e:
        g.log(f"ARM API parse error ({source}={external_id}): {e}", "warning")
        return None


def _extract_arm_ids(data):
    """Extract all available IDs from an ARM API response dict."""
    anilist_id = data.get("anilist")
    mal_id = data.get("mal")

    if not anilist_id and not mal_id:
        return None

    return {
        "anilist_id":     anilist_id,
        "mal_id":         mal_id,
        "anidb_id":       data.get("anidb"),
        "kitsu_id":       data.get("kitsu"),
        "thetvdb_id":     data.get("thetvdb"),
        "themoviedb_id":  data.get("themoviedb"),
        "simkl_id":       None,  # ARM doesn't return Simkl IDs
    }


# ═══════════════════════════════════════════════════════════════════════════
#  AniList Reverse Search (title → AniList ID → cross-reference via ARM)
# ═══════════════════════════════════════════════════════════════════════════

def _anilist_reverse_search(imdb_id=None, tmdb_id=None):
    """Search AniList by title when ARM and the Fribb index both miss.

    Uses TMDb title to search AniList, then maps the found MAL ID back through
    ARM to get the full ID set.

    Returns:
        dict with all anime IDs, or None.
    """
    # We need a title to search with — attempt a lightweight TMDb lookup.
    title = None
    try:
        if tmdb_id:
            tmdb_key = g.get_setting("tmdb.apikey", "9f3ca569aa46b6fb13931ec96ab8ae7e")
            if tmdb_key:
                resp = requests.get(
                    f"https://api.themoviedb.org/3/tv/{tmdb_id}",
                    params={"api_key": tmdb_key},
                    timeout=5,
                    headers={"User-Agent": "Seren"},
                )
                if resp.ok:
                    data = resp.json()
                    title = data.get("name") or data.get("original_name")
    except Exception:
        pass

    if not title:
        return None

    # Search AniList by title
    query = """
    query ($search: String) {
        Media(search: $search, type: ANIME) {
            id
            idMal
        }
    }
    """
    try:
        resp = requests.post(
            _ANILIST_URL,
            json={"query": query, "variables": {"search": title}},
            timeout=5,
            headers={"Content-Type": "application/json", "User-Agent": "Seren"},
        )
        if not resp.ok:
            return None

        data = resp.json()
        media = data.get("data", {}).get("Media")
        if not media:
            return None

        anilist_id = media.get("id")
        mal_id = media.get("idMal")

        if not anilist_id:
            return None

        g.log(
            f"Anime ID mapping (AniList search): title='{title}' → "
            f"AniList={anilist_id}, MAL={mal_id}",
            "debug"
        )

        # Try to get the full ID set via ARM using the MAL ID
        full_ids = None
        if mal_id:
            try:
                arm_resp = requests.get(
                    f"https://arm.haglund.dev/api/v2/mal?id={mal_id}",
                    timeout=5,
                    headers={"User-Agent": "Seren"},
                )
                if arm_resp.ok:
                    arm_data = arm_resp.json()
                    if isinstance(arm_data, list):
                        arm_data = arm_data[0] if arm_data else None
                    if arm_data:
                        full_ids = _extract_arm_ids(arm_data)
            except Exception:
                pass

        if full_ids:
            # Ensure AniList ID is set (ARM may not return it)
            full_ids["anilist_id"] = full_ids.get("anilist_id") or anilist_id
            full_ids["mal_id"] = full_ids.get("mal_id") or mal_id
            return full_ids

        # Minimal result if ARM didn't work
        return {
            "anilist_id": anilist_id,
            "mal_id": mal_id,
            "anidb_id": None,
            "kitsu_id": None,
            "thetvdb_id": None,
            "themoviedb_id": int(tmdb_id) if tmdb_id else None,
            "simkl_id": None,
        }

    except Exception as e:
        g.log(f"AniList reverse search failed: {e}", "warning")

    # ── Last resort: AniDB Titles Dump offline reverse lookup ────────────
    # Zero API cost — uses pre-indexed SQLite from weekly dump download
    if not title:
        return None
    try:
        from resources.lib.modules.anime.anidb_titles import lookup_anidb_id_by_title
        anidb_id = lookup_anidb_id_by_title(title)
        if anidb_id:
            g.log(f"Anime ID mapping (AniDB Titles Dump): title='{title}' → AniDB={anidb_id}", "debug")
            return {
                'anilist_id': None, 'mal_id': None, 'anidb_id': anidb_id,
                'kitsu_id': None, 'simkl_id': None,
                'thetvdb_id': None, 'themoviedb_id': int(tmdb_id) if tmdb_id else None,
            }
    except Exception as e:
        g.log(f"AniDB Titles Dump fallback failed: {e}", "debug")
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  Simkl API (api.simkl.com) — public, no user auth needed
# ═══════════════════════════════════════════════════════════════════════════

def _simkl_get_anidb(mal_id=None, anilist_id=None, imdb_id=None, tmdb_id=None):
    """Query Simkl specifically to get anidb_id (and any other missing IDs).

    Tries MAL → AniList → IMDB → TMDB in order of reliability.

    Returns:
        dict with discovered IDs to merge into existing result, or None.
    """
    ids = _simkl_search_ids(mal_id=mal_id, anilist_id=anilist_id,
                            imdb_id=imdb_id, tmdb_id=tmdb_id)
    if ids and ids.get('anidb_id'):
        return ids
    return None


def _simkl_full_lookup(imdb_id=None, tmdb_id=None):
    """Full Simkl lookup when ARM returned nothing.  Returns full ID dict or None."""
    ids = _simkl_search_ids(imdb_id=imdb_id, tmdb_id=tmdb_id)
    if ids and (ids.get('anilist_id') or ids.get('mal_id')):
        return ids
    return None


def _simkl_search_ids(mal_id=None, anilist_id=None, imdb_id=None, tmdb_id=None):
    """Search Simkl for an anime by available IDs, return all mapped IDs.

    Flow: search/id → get simkl_id → /anime/{simkl_id}?extended=full → extract ids
    """
    simkl_id = None
    search_order = []
    if mal_id:
        search_order.append(('mal', mal_id))
    if anilist_id:
        search_order.append(('anilist', anilist_id))
    if imdb_id:
        search_order.append(('imdb', imdb_id))
    if tmdb_id:
        search_order.append(('tmdb', tmdb_id))

    for id_type, id_val in search_order:
        simkl_id = _simkl_find(id_type, id_val)
        if simkl_id:
            break

    if not simkl_id:
        return None

    return _simkl_get_full_ids(simkl_id)


def _simkl_find(id_type, id_value):
    """Search Simkl by external ID to get the simkl_id."""
    try:
        params = {
            id_type: id_value,
            'client_id': _SIMKL_CLIENT_ID,
        }
        response = requests.get(
            f'{_SIMKL_BASE}/search/id',
            params=params,
            timeout=5,
            headers={"User-Agent": "Seren"}
        )
        if not response.ok:
            return None

        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get('ids', {}).get('simkl')
        return None

    except (requests.RequestException, ValueError, KeyError) as e:
        g.log(f"Simkl search failed ({id_type}={id_value}): {e}", "warning")
        return None


def _simkl_get_full_ids(simkl_id):
    """Get full anime info from Simkl to extract all mapped IDs."""
    try:
        params = {
            'extended': 'full',
            'client_id': _SIMKL_CLIENT_ID,
        }
        response = requests.get(
            f'{_SIMKL_BASE}/anime/{simkl_id}',
            params=params,
            timeout=5,
            headers={"User-Agent": "Seren"}
        )
        if not response.ok:
            return None

        data = response.json()
        if not data or 'ids' not in data:
            return None

        ids = data['ids']
        result = {
            "anilist_id":     ids.get('anilist'),
            "mal_id":         ids.get('mal'),
            "anidb_id":       ids.get('anidb'),
            "kitsu_id":       ids.get('kitsu'),
            "thetvdb_id":     ids.get('tvdb') or ids.get('thetvdb'),
            "themoviedb_id":  ids.get('tmdb') or ids.get('themoviedb'),
            "simkl_id":       ids.get('simkl') or simkl_id,
        }

        g.log(
            f"Anime ID mapping (Simkl): simkl={simkl_id} → "
            f"AniList={result.get('anilist_id')}, MAL={result.get('mal_id')}, "
            f"AniDB={result.get('anidb_id')}, Kitsu={result.get('kitsu_id')}",
            "debug"
        )
        return result

    except (requests.RequestException, ValueError, KeyError) as e:
        g.log(f"Simkl full lookup failed (simkl={simkl_id}): {e}", "warning")
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  Public convenience methods
# ═══════════════════════════════════════════════════════════════════════════

def get_anime_ids_for_item(item_information):
    """Convenience method to extract anime IDs from Seren's item_information dict.

    Args:
        item_information: Seren's standard item info dict

    Returns:
        dict with all anime database IDs, or None if not anime or mapping fails.
    """
    info = item_information.get("info", {})

    # Quick genre check — only look up IDs for anime content
    genres = info.get("genre", [])
    if not isinstance(genres, list):
        genres = [genres] if genres else []
    is_anime = any("anime" in g_str.lower() for g_str in genres)

    # Also check country_origin for Japanese content with animation genre
    if not is_anime:
        country = info.get("country_origin", "")
        has_animation = any("animation" in g_str.lower() for g_str in genres)
        if has_animation and country.upper() in ("JP", "JPN", "JAPAN", "CN", "CHN", "CHINA"):
            is_anime = True

    if not is_anime:
        return None

    imdb_id, tmdb_id, trakt_id = _show_ids_from_info(info)
    return get_anime_ids(imdb_id=imdb_id, tmdb_id=tmdb_id, trakt_id=trakt_id)


def _show_ids_from_info(info):
    """(imdb, tmdb, trakt) ids of the SHOW an item belongs to; None for a missing id.

    An episode's own imdb_id / tmdb_id / trakt_id identify the EPISODE, which the Fribb index and the
    online fallbacks do not know, so for an episode only the show-level ids are used."""
    if info.get("tmdb_show_id") or info.get("tvshow.tmdb_id") or info.get("trakt_show_id") or info.get("tvshow.imdb_id"):
        imdb_id = info.get("tvshow.imdb_id", "")
        tmdb_id = info.get("tmdb_show_id", "") or info.get("tvshow.tmdb_id", "")
        trakt_id = info.get("trakt_show_id", "")
    else:
        imdb_id = info.get("imdb_id", "")
        tmdb_id = info.get("tmdb_id", "")
        trakt_id = info.get("trakt_id", "")
    return imdb_id or None, tmdb_id or None, trakt_id or None


# AniList run of an entry, {anilist_id: (start date, end date or None, episode count or None) or None}, kept for the session
_runs = {}
_runs_retry_after = 0.0    # after a failed AniList request nothing is asked again for 5 minutes (an episode list asks once per episode)
_DATE_SLACK = datetime.timedelta(days=3)


def _air_date(info):
    """The episode's air date from an item's info dict, or None."""
    value = str(info.get("aired") or info.get("premiered") or "")[:10]
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _date_of(value):
    try:
        return datetime.date(value["year"], value["month"], value["day"])
    except (KeyError, TypeError, ValueError):
        return None


def _runs_of(anilist_ids):
    """{anilist_id: (start, end, episodes)} for the ids; None for an id AniList has no full start date for."""
    global _runs_retry_after
    missing = [anilist_id for anilist_id in anilist_ids if anilist_id and anilist_id not in _runs]
    if missing and time.time() >= _runs_retry_after:
        query = ("query ($ids: [Int], $perpage: Int) { Page(perPage: $perpage) { media(id_in: $ids, type: ANIME) "
                 "{ id episodes startDate { year month day } endDate { year month day } } } }")
        try:
            response = requests.post(_ANILIST_URL, json={"query": query, "variables": {"ids": missing, "perpage": len(missing)}},
                                     timeout=5, headers={"User-Agent": "Seren"})
            if response.ok:
                for media in ((response.json().get("data") or {}).get("Page") or {}).get("media") or ():
                    start = _date_of(media.get("startDate"))
                    _runs[media["id"]] = (start, _date_of(media.get("endDate")), media.get("episodes")) if start else None
            else:
                _runs_retry_after = time.time() + 300
        except (requests.RequestException, ValueError) as e:
            _runs_retry_after = time.time() + 300
            g.log(f"AniList run dates fetch failed: {e}", "debug")
    return {anilist_id: _runs.get(anilist_id) for anilist_id in anilist_ids if anilist_id}


def _air_date_fits(entry, aired):
    """True when the episode belongs to the entry's run by AniList: aired from its start date (3 days of
    slack) until it ended or the next cour of the same season started, and its number inside the entry
    is not above the entry's episode count.  False when that cannot be established."""
    if aired is None or not entry.get("anilist_id"):
        return False
    runs = _runs_of([entry["anilist_id"], entry.get("next_anilist_id")])
    run = runs.get(entry["anilist_id"])
    if run is None or aired < run[0] - _DATE_SLACK:
        return False
    start, end, episodes = run
    if end is not None and aired > end + _DATE_SLACK:
        return False
    if episodes and entry["anime_episode"] > episodes:
        return False
    following = runs.get(entry.get("next_anilist_id"))
    return following is None or aired < following[0] - _DATE_SLACK


def resolve_episode_entry(item_information):
    """Anime ids of the entry (cour) a Trakt/TMDb episode belongs to, and its number inside that entry.

    Returns (anime_ids, episode_in_entry), or None when the item is not an anime episode, is not mapped,
    or the index cannot say with confidence which entry it is.  Used for AniSkip / Anime-Skip, which key
    on the entry's own MAL / AniList id and count episodes from 1 inside it.  Season 1 of a show the
    index holds no season data for keeps the show's first entry and the plain episode number; a later
    season, or a cour choice the air date does not confirm, returns None rather than a guess.  The
    cached get_anime_ids results are never changed."""
    info = item_information.get("info") or {}
    if not (info.get("tmdb_show_id") or info.get("tvshow.tmdb_id") or info.get("tvshow.imdb_id")):
        return None
    try:
        season, episode = int(info.get("season")), int(info.get("episode"))
    except (TypeError, ValueError):
        return None
    ids = get_anime_ids_for_item(item_information)
    if not ids or not episode:
        return None
    imdb_id, tmdb_id, _ = _show_ids_from_info(info)

    from resources.lib.modules.anime.fribb_mapping import lookup_episode
    entry, reason = lookup_episode(imdb_id=imdb_id, tmdb_id=tmdb_id, season=season, episode=episode)
    if entry is None:
        if reason == "no_data" and season <= 1:
            return ids, episode
        g.log(f"Anime episode entry: S{season}E{episode} not resolved ({reason})", "debug")
        return None
    # The show's first entry with the unchanged episode number needs no check
    if not (entry["anilist_id"] == ids.get("anilist_id") and entry["mal_id"] == ids.get("mal_id")
            and entry["anime_episode"] == episode):
        if not _air_date_fits(entry, _air_date(info)):
            g.log(f"Anime episode entry: S{season}E{episode} -> AniList {entry['anilist_id']} not confirmed by the air date", "debug")
            return None
    g.log(f"Anime episode entry: S{season}E{episode} -> AniList {entry['anilist_id']}, MAL {entry['mal_id']}, "
          f"episode {entry['anime_episode']}", "debug")
    return entry, entry["anime_episode"]


def invalidate_cache():
    """Clear the session-level ID cache."""
    global _id_cache
    _id_cache = {}
