"""Movie calendar data: one calendar month of movies, ordered by release date.

The Trakt-sourced layer (calendars/all/movies, a public/non-authenticated endpoint)
is unioned with movies on the user's Simkl plan-to-watch or MDBList watchlist that
Trakt's own calendar doesn't already cover - mirrors calendar_data.py/
tv_schedule_data.py's own watchlist-layer union for shows, except a movie has exactly
one release date (no per-week/per-month "which episode" ambiguity), so the extra
layer here is a resolve-then-date-filter instead of an episode picker. The date
filter runs post-hydration - resolving a bare tmdb_id (SimklMenus._resolve(), backed
by Trakt's search/tmdb/{id}) returns only title/year/ids, no release date, so
month-relevance can't be known until get_movie_list() enriches the row. A cache-hit
Trakt-layer stub (see below) carries no date pre-hydration either, so it goes
through the same post-hydration check.

The Trakt-sourced layer is fetch-bookkept per month by MovieCalendarDatabase (see
resources/lib/database/movieCalendar) - re-paging to an already-fetched month skips
the live Trakt call and re-hydrates from the shared trakt_sync table instead, same
pattern tv_schedule_data.py's own TvScheduleDatabase already uses for weeks. The
Simkl/MDBList watchlist-union layer is deliberately never cached - it's already
capped at _UNION_CAP live-resolve calls and stays live on every month view, matching
tv_schedule_data.py's own watchlist layer.
"""
import calendar
import datetime
from functools import lru_cache
import re
import threading

import xbmc

from resources.lib.modules.globals import g
from resources.lib.modules.metadataHandler import MetadataHandler

_MOVIE_CALENDAR_ENDPOINT = "calendars/all/movies/{start_date}/{days}"
_UNION_CAP = 25  # matches calendar_data.py/tv_schedule_data.py's own cap - same per-movie live-resolve cost
_REPAIR_CAP = 25  # separate budget for the stale-bookkeeping self-heal below - independent of _UNION_CAP,
# both can be spent live-refetching in the same month-open (watchlist union resolve + trakt_sync repair)

_fetch_locks_guard = threading.Lock()
_fetch_locks = {}  # month_key -> threading.Lock, created on first use, never evicted


def _fetch_lock(month_key):
    """Per-month lock so a background rolling-prefetch timer (see
    movie_calendar_window.py) and a foreground navigation to the same month
    can't both see a cache miss and both fetch Trakt live. The second caller
    blocks here, then re-checks MovieCalendarDatabase after acquiring - the
    existing `cached is None` branches below already do the right thing once
    that re-check happens inside the lock."""
    with _fetch_locks_guard:
        lock = _fetch_locks.get(month_key)
        if lock is None:
            lock = threading.Lock()
            _fetch_locks[month_key] = lock
        return lock


def get_movie_calendar_month(year, month, prefetch=False):
    """prefetch=True is for the background rolling-prefetch timer only - it
    warms MovieCalendarDatabase's bookkeeping (the Trakt-sourced layer) without
    touching _get_watchlist_movies()'s Simkl/MDBList union layer. That layer is
    deliberately never cached (see module docstring) and resolves through
    SimklMenus()._resolve(), a GUI menu class never exercised off the main
    thread anywhere in this codebase - skipping it here means prefetch never
    has to answer that thread-safety question, and the work would be discarded
    anyway. This can't change what gets bookkept: newly_fetched_ids below is
    only ever populated from non-extra (raw_items-sourced) movies - extra_items
    only ever reaches the `if is_extra:` branch - so an empty extra_items here
    yields the identical bookkept row set a foreground call would write for the
    same month."""
    from resources.lib.modules.syncGateway import configured_providers

    providers = configured_providers()
    if not providers:
        return []

    from resources.lib.indexers.trakt import TraktAPI
    from resources.lib.database.movieCalendar import MovieCalendarDatabase

    month_start_str = datetime.date(year, month, 1).strftime("%Y-%m-%d")
    days_in_month = calendar.monthrange(year, month)[1]
    month_end_str = datetime.date(year, month, days_in_month).strftime("%Y-%m-%d")
    month_key = f"{year:04d}-{month:02d}"

    cal_db = MovieCalendarDatabase()

    with _fetch_lock(month_key):
        cached = cal_db.get_month(month_key)

        if prefetch and cached is not None:
            # Already bookkept - a prefetch's only job is warming this table, which
            # is already warm. Returning here skips the full get_movie_list() hydration
            # pass below entirely, which otherwise runs (and is discarded, since
            # prefetch's caller ignores the return value) while still holding
            # _fetch_lock(month_key) - the same lock a foreground navigation to this
            # month would block on. Steady-state rolling prefetch hits this branch
            # often: one of the two adjacent months is usually the one just left.
            return []

        if cached is None:
            # Unconditional, not gated on "trakt" in providers - calendars/all/movies is a
            # public endpoint (confirmed live: still serves data with Trakt disabled), same
            # as calendars/all/shows in tv_schedule_data.py's own global layer.
            raw_items = _fetch_raw_trakt_calendar(TraktAPI(), year, month)
        else:
            # Bookkeeping-only cache hit (see MovieCalendarDatabase) - reconstruct the
            # stub id list tv_schedule_data.py's own _get_global_layer() rebuilds from on
            # a cache hit; the real content re-hydrates below from the shared trakt_sync
            # table these ids were already inserted into on the original live fetch.
            raw_items = [{"trakt_id": r["trakt_movie_id"]} for r in cached]

        covered_trakt_ids = {i.get("trakt_id") for i in raw_items if i.get("trakt_id")}
        if prefetch:
            extra_items, capped_ids, simkl_id_by_tmdb = [], [], {}
        else:
            extra_items, capped_ids, simkl_id_by_tmdb = _get_watchlist_movies(providers, covered_trakt_ids)
        extra_trakt_ids = {i.get("trakt_id") for i in extra_items if i.get("trakt_id")}

        all_items = raw_items + extra_items
        if not all_items:
            return []  # get_movie_list()'s WHERE trakt_id IN (...) has no empty-list guard

        # NOT i.get("released") - normalization drops that key entirely; a raw calendar
        # item's release date lives at trakt_object.info.aired after get_json()'s
        # normalization pass. Same accessor insert_trakt_movies() itself uses.
        #
        # On a cache hit, the bookkept release_date (see MovieCalendarDatabase) is used
        # instead of re-deriving from post-hydration info - metadataHandler.py's
        # _apply_best_fit_release() can independently overwrite the shared trakt_sync
        # row's info.aired after the original fetch (its own per-country release-type
        # selection, unrelated to this table's bookkeeping), so re-reading it on every
        # cache hit could silently drift the displayed date away from the one this
        # movie was actually bookkept under. Confirmed live: a movie shown under its
        # limited-release date on first fetch re-rendered under its later
        # wide-theatrical date on a subsequent cache hit, once the shared column had
        # been overwritten in between.
        if cached is None:
            released_by_trakt_id = {
                i.get("trakt_id"): MetadataHandler.get_trakt_info(i, "aired")
                for i in raw_items if i.get("trakt_id") and MetadataHandler.get_trakt_info(i, "aired")
            }
        else:
            released_by_trakt_id = {
                r["trakt_movie_id"]: r["release_date"] for r in cached if r["release_date"]
            }

        from resources.lib.database.trakt_sync.movies import TraktSyncDatabase as MoviesDatabase

        movies_db = MoviesDatabase()
        if cached is None:
            # extra_items are already bootstrapped by SimklMenus._resolve()'s own
            # _seed_trakt_sync(); a cache-hit raw_items stub must NOT be inserted here -
            # it carries no real Trakt fields, and the movie is already durably stored in
            # trakt_sync from its original live fetch (MovieCalendarDatabase only
            # bookkeeps which trakt_ids belong to which month, never the content itself).
            movies_db.insert_trakt_movies(raw_items)
        else:
            # The "already durably stored" assumption above can be violated out of band -
            # traktSync.db (movies/movies_meta) and movieCalendar.db are separate files, so
            # an action that clears one (e.g. Rebuild Database) doesn't clear the other. A
            # trakt_id bookkept here with no underlying trakt_sync row would otherwise crash
            # metadataHandler.format_db_object() on every future open of this month, forever,
            # since this branch normally never re-inserts. Capped and sorted the same way
            # _get_watchlist_movies()'s _UNION_CAP is - bounds a single month-open to a fixed
            # number of live re-fetches and converges across repeat opens instead of hanging
            # on a large rebuild. Uses its own _REPAIR_CAP (not _UNION_CAP) since this repair
            # and the watchlist union resolve above are independent live-call budgets that can
            # both be spent in the same month-open. Reuses the same single-movie repair path
            # get_movie()/_get_single_movie_meta() already use elsewhere (checks movies_meta
            # itself, only live-refetches+inserts if actually missing - never touches an
            # already-good row).
            stale_ids = movies_db.missing_trakt_meta_ids(covered_trakt_ids)
            if stale_ids:
                repair_now, repair_later = stale_ids[:_REPAIR_CAP], stale_ids[_REPAIR_CAP:]
                g.log(
                    f"movie_calendar_data: {len(repair_now)} bookkept movie(s) missing from "
                    f"trakt_sync (stale cache after a DB reset) - repairing"
                    + (f", {len(repair_later)} deferred to a later open" if repair_later else ""),
                    "warning",
                )
                for trakt_id in repair_now:
                    try:
                        movies_db._get_single_movie_meta(trakt_id)
                    except Exception as e:
                        # A single movie can genuinely be gone from Trakt entirely (not just
                        # locally wiped) - don't let one bad repair take down this whole
                        # month's view; _apply_best_fit_meta_data() already tolerates the
                        # still-missing trakt_object gracefully via its tmdb/tvdb fallback.
                        g.log(f"movie_calendar_data: repair failed for trakt_id {trakt_id}: {e}", "warning")
        hydrated = movies_db.get_movie_list(all_items, hide_unaired=False, hide_watched=False)

        from resources.lib.modules.calendar_ratings import fetch_union_ratings, pick_best_rating

        if prefetch:
            mdblist_ratings, simkl_ratings = {}, {}
        else:
            mdblist_ratings, simkl_ratings = fetch_union_ratings(capped_ids, simkl_id_by_tmdb, "movie", providers)

        result = []
        newly_fetched_ids = []
        for movie in hydrated:
            trakt_id = movie.get("trakt_id")
            is_extra = trakt_id in extra_trakt_ids
            # A cache-hit raw item needs the same post-hydration date re-check an extra
            # item always needed - its stub carried no date at all, and even a genuine
            # live raw item's date can in principle drift after being bookkept (a
            # rescheduled release; tv_schedule_data.py's _get_global_layer() documents
            # the same Trakt-calendar boundary quirk for episodes).
            needs_date_check = is_extra or cached is not None
            released = released_by_trakt_id.get(trakt_id)
            if released is None and needs_date_check:
                # get_movie_list()'s own _update_movies() enriches a freshly-seeded row
                # (extended=True Trakt refetch + format_db_object()) on its first hydration
                # pass, which is what just happened above - confirmed live via direct SQL
                # that movies.air_date (written from this same info["aired"], see movies.py's
                # upsert) was populated for every Simkl/MDBList candidate right after this
                # exact call, even though none of them had a date pre-hydration.
                info = movie.get("info") or {}
                released = info.get("aired") or info.get("premiered")
            if needs_date_check and not (released and month_start_str <= released[:10] <= month_end_str):
                continue  # candidate's real release date isn't in this month after all
            if is_extra:
                # get_movie_list()'s SELECT never lists tmdb_id as its own column
                # (only trakt_id is - confirmed by reading its SQL directly), so
                # a hydrated movie has no top-level tmdb_id at all, unlike the
                # pre-hydration resolved object _get_watchlist_movies() returned.
                # It's still there, just nested - format_meta()'s upsert writes
                # tmdb_id into the info blob itself (confirmed via
                # _update_movies()'s own i["info"].get("tmdb_id") read), and
                # _classify_and_annotate() below already reads other fields off
                # this same info dict the same way.
                tmdb_id = (movie.get("info") or {}).get("tmdb_id")
                rating = pick_best_rating(simkl_ratings.get(tmdb_id), mdblist_ratings.get(tmdb_id), None)
                if rating is not None:
                    movie["_rating_override"] = rating
            elif cached is None and trakt_id and released and month_start_str <= released[:10] <= month_end_str:
                # Write-path filter, independent of needs_date_check above (which
                # deliberately never re-checks a live raw item's date for DISPLAY -
                # see module docstring). Bookkeeping still needs it: MovieCalendarDatabase's
                # primary key is trakt_movie_id alone, so writing this movie under this
                # month here, when Trakt's calendar endpoint returned it outside the exact
                # requested window (the same boundary quirk tv_schedule_data.py's own
                # _get_global_layer() documents for episodes), would let a later live fetch
                # of its real month INSERT OR REPLACE this row away - or vice versa,
                # whichever month is fetched second silently steals the row. A boundary/
                # dateless item still displays this pass unchanged; it's just never
                # trusted for a future cache reconstruction of either month.
                #
                # released here is this fetch's own raw calendar-endpoint date (see
                # released_by_trakt_id above) - persisted alongside so a future cache
                # hit redisplays this exact date instead of re-deriving it later.
                newly_fetched_ids.append((trakt_id, released))
            _classify_and_annotate(movie, released)
            result.append(movie)

        if newly_fetched_ids:
            cal_db.mark_month_fetched(month_key, newly_fetched_ids)

    result.sort(key=lambda m: (m.get("_calendar_released") or "", (m.get("info") or {}).get("title") or ""))

    extra_in_month = sum(1 for m in result if m.get("trakt_id") in extra_trakt_ids)
    g.log(
        f"movie_calendar_data: {len(extra_items)} Simkl/MDBList watchlist movie(s) resolved, "
        f"{extra_in_month} release in {year}-{month:02d}" + (" [prefetch]" if prefetch else ""),
        "debug",
    )
    return result


def retention_cutoff():
    """Oldest month_key still worth keeping fetched: current month and the 2
    before it are the retained edge, so cleanup() drops anything older than
    that (matches tv_schedule_data.py's own retention_cutoff() shape - one
    month of margin beyond the eventual current-1 rolling prefetch)."""
    today = datetime.date.today()
    cutoff_year, cutoff_month = shift_month(today.year, today.month, -2)
    return f"{cutoff_year:04d}-{cutoff_month:02d}"


def _get_watchlist_movies(providers, covered_trakt_ids):
    """Simkl plan-to-watch + MDBList watchlist movies not already covered by Trakt's
    own calendar. Candidates are capped BEFORE their release date is known (a bare
    tmdb_id carries no date - it only appears after resolving against Trakt, and even
    then not until after hydration - see get_movie_calendar_month()), so the cap bounds
    live-resolve cost, not month-relevance: a watchlist larger than _UNION_CAP can leave
    a real this-month release unresolved if it isn't among the first _UNION_CAP
    candidates seen. Same tradeoff calendar_data.py/tv_schedule_data.py already accept
    for shows; logged here so it's diagnosable rather than silent."""
    candidate_tmdb_ids = {}  # dict (not set) purely to preserve first-seen order for the cap
    simkl_id_by_tmdb = {}
    if "simkl" in providers:
        for tmdb_id, simkl_id in _simkl_plantowatch_movie_tmdb_ids():
            _add_candidate(candidate_tmdb_ids, tmdb_id)
            if simkl_id is not None:
                simkl_id_by_tmdb.setdefault(tmdb_id, simkl_id)
    if "mdblist" in providers:
        for tmdb_id in _mdblist_watchlist_movie_tmdb_ids():
            _add_candidate(candidate_tmdb_ids, tmdb_id)

    if not candidate_tmdb_ids:
        return [], [], {}

    capped_ids = list(candidate_tmdb_ids)[:_UNION_CAP]
    dropped = len(candidate_tmdb_ids) - len(capped_ids)
    if dropped > 0:
        g.log(f"movie_calendar_data: union cap reached, dropped {dropped} Simkl/MDBList-only movie(s) this fetch", "warning")

    from resources.lib.gui.simklMenus import Menus as SimklMenus

    resolved = SimklMenus()._resolve(capped_ids, "movie")
    seen_trakt_ids = set(covered_trakt_ids)
    items = []
    for movie in resolved:
        trakt_id = movie.get("trakt_id")
        if not trakt_id or trakt_id in seen_trakt_ids:
            continue
        seen_trakt_ids.add(trakt_id)
        items.append(movie)
    return items, capped_ids, simkl_id_by_tmdb


def _add_candidate(candidate_tmdb_ids, tmdb_id):
    # Simkl and MDBList disagree on the JSON type of a tmdb_id (str vs int) - normalize
    # to int so the same movie watchlisted on both services collapses to one candidate
    # instead of silently burning two cap slots (confirmed live: Simkl gave '364279',
    # MDBList gave 687163 for two different movies, but the mismatch is real whenever
    # the same movie appears on both).
    try:
        candidate_tmdb_ids.setdefault(int(tmdb_id), None)
    except (TypeError, ValueError):
        pass


def _simkl_plantowatch_movie_tmdb_ids():
    """Movie-side sibling of calendar_data.py's _simkl_plantowatch_tmdb_ids() - same
    fetch+extract shape (now (tmdb_id, simkl_id) pairs, for the same Simkl-rating
    lookup need), against Simkl's movies/plantowatch endpoint instead of shows/."""
    from resources.lib.indexers.simkl import SimklAPI

    page = SimklAPI().get_json("sync/all-items/movies/plantowatch")
    if page is None:
        return []
    pairs = []
    for entry in page.get("movies") or []:
        ids = (entry.get("movie") or {}).get("ids") or {}
        tmdb_id = ids.get("tmdb")
        if tmdb_id is None:
            continue
        try:
            tmdb_id = int(tmdb_id)
        except (TypeError, ValueError):
            continue
        pairs.append((tmdb_id, ids.get("simkl")))
    return pairs


def _mdblist_watchlist_movie_tmdb_ids():
    """Movie-side sibling of calendar_data.py's _mdblist_watchlist_tmdb_ids() - same
    underlying bridgeSync reader (already returns both movie:/show: prefixed keys),
    filtered to "movie:" instead of "show:"."""
    from resources.lib.modules.bridgeSync import _read_mdblist_watchlist

    watchlist = _read_mdblist_watchlist()
    return [tmdb_id for key, tmdb_id in watchlist.items() if key.startswith("movie:")]


def shift_month(year, month, delta):
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def _fetch_raw_trakt_calendar(trakt_api, year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    start_date = datetime.date(year, month, 1)
    # Server-side filter, confirmed live (Trakt narrows the result set itself:
    # 200->109 shows, 24->1 movies in test probes). Blank setting means the
    # param is omitted, preserving today's unfiltered behaviour exactly.
    filters = {}
    region = g.get_setting("calendar.region")
    if region:
        filters["countries"] = region
    language = g.get_setting("calendar.language")
    if language:
        filters["languages"] = language
    raw = trakt_api.get_json(
        _MOVIE_CALENDAR_ENDPOINT.format(start_date=start_date.strftime("%Y-%m-%d"), days=days_in_month),
        extended="full",
        pull_all=True,
        **filters,
    )
    return raw or []


def _classify_and_annotate(movie, released):
    # Checked on the raw hydrated dict, before get_list_item_with_properties()/add_directory_item()
    # injects a default-poster fallback that would otherwise mask "no poster."
    info = movie.get("info") or {}
    art = movie.get("art") or {}

    movie["_calendar_released"] = released
    movie["_calendar_countdown"] = _format_countdown(released)
    movie["_calendar_date_label"] = _format_release_date(released)

    has_poster = bool(art.get("poster"))
    # Key-presence check, NOT truthiness - a real 0-vote movie has
    # rating.tmdb={"rating":0.0,"votes":0}, which is populated data, not "thin" data.
    has_tmdb_rating = "rating.tmdb" in info

    # _rating_override (Simkl/MDBList's own score for a union-sourced movie -
    # see get_movie_calendar_month()) takes precedence when present; falls
    # through to the existing TMDB/Trakt chain otherwise. Deliberately not
    # consulted by has_tmdb_rating above - that flag tracks whether TMDB's
    # own metadata pipeline has finished populating this movie, a data-
    # completeness signal unrelated to which number gets displayed.
    rating_value = movie.get("_rating_override")
    if rating_value is None:
        rating_value = (info.get("rating.tmdb") or {}).get("rating")
    if rating_value is None:
        rating_value = info.get("rating")  # Trakt community rating - display fallback only
    movie["_calendar_rating_display"] = f"{rating_value:.1f}" if isinstance(rating_value, (int, float)) else ""

    if not _is_released(released):
        movie["_calendar_status"] = "upcoming"
    elif has_poster and has_tmdb_rating:
        movie["_calendar_status"] = "released_complete"
    else:
        movie["_calendar_status"] = "released_incomplete"


def _is_released(released):
    if not released:
        return False
    return released < g.datetime_to_string(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


def _format_countdown(released):
    if not released:
        return ""
    try:
        from resources.lib.common import tools

        days = (tools.parse_datetime(released) - datetime.date.today()).days
        return str(max(days, 0))
    except (ValueError, TypeError):
        return ""


@lru_cache(maxsize=1)
def _calendar_date_format():
    # Drop the year - the calendar's own month/year header already carries it.
    # Regex-strip (not a hardcoded "%m/%d") to keep whatever day/month order
    # the user's Kodi region actually uses. Cached for the process lifetime -
    # Kodi's system region format does not change without a restart, same
    # assumption locale_playback._stream_language_names() already makes.
    return re.sub(r"[/.\-]?%[Yy][/.\-]?", "", xbmc.getRegion("dateshort"), count=1)


def _format_release_date(released):
    if not released:
        return ""
    try:
        from resources.lib.common import tools

        return tools.parse_datetime(released).strftime(_calendar_date_format())
    except (ValueError, TypeError):
        return released
