import re
import time
from concurrent.futures import as_completed
from functools import cached_property
from urllib.parse import quote

import xbmcgui

from resources.lib.common.thread_pool import ThreadPoolExecutor
from resources.lib.modules.globals import g

# MDBList's /lists/{listid}/items `sort` enum - key, display-string-id pairs, in the
# order they're offered in the sort picker. Covers all 25 keys the API documents.
_LIST_ITEMS_SORT_OPTIONS = [
    ("rank", 31015),
    ("title", 31036),
    ("score", 31016),
    ("added", 31038),
    ("released", 31019),
    ("releasedigital", 31020),
    ("imdbrating", 31021),
    ("imdbvotes", 31022),
    ("imdbpopular", 31024),
    ("tmdbpopular", 31025),
    ("metacritic", 31029),
    ("rtomatoes", 31027),
    ("rtaudience", 31028),
    ("myanimelist", 31030),
    ("letterrating", 31031),
    ("lettervotes", 31032),
    ("rogerebert", 31026),
    ("last_air_date", 31023),
    ("runtime", 31035),
    ("budget", 31033),
    ("revenue", 31034),
    ("sort_title", 31037),
    ("usort", 31017),
    ("score_average", 31018),
    ("random", 31039),
]

# Supporter-only rating filters: API param prefix -> display-string-id. Prefixes are
# MDBList's filter_<prefix>_min/_max names, which don't all match the sort keys above
# (e.g. sort's "rtomatoes" is filter's "tomatorating" for the same underlying source).
_RATING_FILTER_SOURCES = [
    ("score", 31016),
    ("imdbrating", 31021),
    ("tmdbrating", 31040),
    ("metarating", 31029),
    ("tomatorating", 31027),
    ("popcornrating", 31028),
    ("letterrating", 31031),
    ("malrating", 31030),
]

# g.REQUEST_PARAMS keys that carry list-items sort/filter state across requests (Next
# Page and re-entering the picker both need to preserve whatever's currently active).
_FILTER_KEYS = (
    "sort", "order", "filter_title", "filter_genre", "released_from", "released_to",
    "filter_score_min", "filter_score_max",
    "filter_imdbrating_min", "filter_imdbrating_max",
    "filter_tmdbrating_min", "filter_tmdbrating_max",
    "filter_metarating_min", "filter_metarating_max",
    "filter_tomatorating_min", "filter_tomatorating_max",
    "filter_popcornrating_min", "filter_popcornrating_max",
    "filter_letterrating_min", "filter_letterrating_max",
    "filter_malrating_min", "filter_malrating_max",
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# next_up() deliberately doesn't use self.page_limit (item.limit, default 20) directly -
# every candidate show that reaches _pick_next_unwatched can trigger a cold TMDb bootstrap
# of that show's entire episode catalog (get_episode_list -> _try_update_episodes), which is
# one-time-per-show but synchronous, so a general browse-page-size setting is the wrong bound
# for "how many shows to cold-bootstrap in one call" - a live report measured ~123s for 20
# shows on a Trakt-disabled, never-cached account. This caps worst-case latency regardless of
# item.limit while still respecting a smaller user preference (see next_up()'s min() call).
# It bounds the number of PICKS (rows shown), not the shows examined: a recently watched show
# with nothing left to watch yields no pick, and with only the 10 most recent shows examined a
# Shield account saw 6 rows where mdblist.com's own Up Next had 10 (3.9.54).
_NEXT_UP_SHOW_CAP = 10

# next_up() walks the shows newest-watched first until it has _NEXT_UP_SHOW_CAP picks, but stops at
# whichever comes first: this many shows examined, or this many seconds spent (checked before each
# show, so one cold show can overshoot by its own bootstrap time). The seconds bound is the real
# protection - per-show cost ranges from a few hundred ms (cached) to several seconds (cold).
_NEXT_UP_SCAN_CAP = 40
_NEXT_UP_TIME_BUDGET = 25.0

# in_progress_shows() lists every started, unfinished show, so unlike next_up() it has no 10-pick cap - but it keeps the same
# scan and time bounds (a cold show costs one episode-catalog bootstrap) and stops after this many rows.
_IN_PROGRESS_SHOW_CAP = 30


def _is_zero_progress(progress):
    """True for a sync/playback entry sitting at 0% (a player that was only started, nothing watched). MDBList sends the
    percentage as a string ("17.67"); a missing or non-numeric value is not 0%, so that row is kept."""
    try:
        return float(progress) <= 0
    except (TypeError, ValueError):
        return False


class Menus:
    """MDBList-sourced menus (Recently Watched, In-Progress, Collection, Dropped Shows).

    Items are local mdblistSync.db (or, for in-progress, live sync/playback) rows
    keyed by tmdb_id. Each is resolved to a Trakt object via TraktAPI.search_by_tmdb_id
    (Trakt's ID lookup - no personal OAuth needed) before being handed to the existing,
    unmodified Trakt-native ListBuilder methods. This lets MDBList-only items render
    and play through the exact same proven pipeline as any normally-browsed Trakt item,
    rather than a parallel MDBList-native pipeline that would still need to separately
    solve source-search's own trakt_id requirement.
    """

    def __init__(self):
        self.page_limit = g.get_int_setting("item.limit")

    @cached_property
    def mdblist_database(self):
        from resources.lib.database.mdblist_sync import MDBListSyncDatabase

        return MDBListSyncDatabase()

    @cached_property
    def mdblist_api(self):
        from resources.lib.indexers.mdblist import MDBListAPI

        return MDBListAPI()

    @cached_property
    def trakt_api(self):
        from resources.lib.indexers.trakt import TraktAPI

        return TraktAPI()

    @cached_property
    def hidden_database(self):
        from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase as HiddenDatabase

        return HiddenDatabase()

    @cached_property
    def list_builder(self):
        from resources.lib.modules.list_builder import ListBuilder

        return ListBuilder()

    def _resolve(self, tmdb_ids, media_type):
        """Resolves tmdb_ids to Trakt objects in parallel (mirrors debrid/external_cache.py's
        ThreadPoolExecutor + as_completed pattern), dropping (and logging) any id Trakt has
        no match for - or that errors/times out - rather than failing the whole list."""
        if not tmdb_ids:
            return []

        resolved = []
        executor = ThreadPoolExecutor(max_workers=min(10, len(tmdb_ids)))
        try:
            futures = {
                executor.submit(self.trakt_api.search_by_tmdb_id, tmdb_id, media_type): tmdb_id
                for tmdb_id in tmdb_ids
            }
            try:
                for future in as_completed(futures, timeout=20):
                    resolved_item = self._collect_resolved(future, futures[future], media_type)
                    if resolved_item:
                        resolved.append(resolved_item)
            except Exception as e:
                g.log(f"MDBList menus: resolve batch timed out, using partial results: {e}", "warning")
                for future in futures:
                    if future.done():
                        resolved_item = self._collect_resolved(future, futures[future], media_type)
                        if resolved_item:
                            resolved.append(resolved_item)
        finally:
            # `with ThreadPoolExecutor(...)` would block here on shutdown(wait=True) regardless
            # of the as_completed timeout above, silently turning the 20s ceiling into "however
            # long the slowest straggler takes." wait=False actually enforces the ceiling.
            # cancel_futures drops queued-but-unstarted lookups - common/thread_pool.py's
            # ThreadPoolExecutor backports this to Python 3.8. Futures already running still
            # finish in the background; nothing here waits on or reads their results.
            executor.shutdown(wait=False, cancel_futures=True)

        if resolved:
            self._seed_trakt_sync(resolved, media_type)
        return resolved

    @staticmethod
    def _seed_trakt_sync(resolved, media_type):
        """Writes freshly-resolved items into the local Trakt sync DB via the same
        insert_trakt_movies/insert_trakt_shows path every native Trakt-list menu (Watchlist,
        Collection, etc.) goes through before rendering. Without this, movie_menu_builder/
        show_list_builder's get_movie_list/get_show_list crash on any trakt_id that's never
        been locally synced before - _update_movies/_update_shows only refresh existing rows,
        they don't create them from scratch."""
        if media_type == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase as MoviesDatabase

            MoviesDatabase().insert_trakt_movies(resolved)
        else:
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase

            ShowsDatabase().insert_trakt_shows(resolved)

    @staticmethod
    def _collect_resolved(future, tmdb_id, media_type):
        try:
            trakt_object = future.result()
        except Exception as e:
            g.log(f"MDBList menus: error resolving tmdb_id {tmdb_id} ({media_type}): {e}", "warning")
            return None
        if not trakt_object or not trakt_object.get("trakt_id"):
            g.log(f"MDBList menus: no Trakt match for tmdb_id {tmdb_id} ({media_type}), skipping", "debug")
            return None
        return trakt_object

    def _live_playback_rows(self, media_type):
        """Live GET /sync/playback - fresher than the local bookmarks cache, which
        only updates on scrobble events and can go stale between syncs."""
        entries = self.mdblist_api.get_json("sync/playback") or []
        if isinstance(entries, dict):
            entries = entries.get("items") or []

        rows = []
        for entry in entries:
            if entry.get("type") != media_type:
                continue
            paused_at = entry.get("paused_at")
            if media_type == "movie":
                tmdb_id = (entry.get("movie") or {}).get("ids", {}).get("tmdb")
                if tmdb_id:
                    rows.append({"tmdb_id": tmdb_id, "paused_at": paused_at})
            elif media_type == "episode":
                show = entry.get("show") or {}
                episode = entry.get("episode") or {}
                tmdb_id = show.get("ids", {}).get("tmdb")
                season = episode.get("season")
                number = episode.get("number")
                if _is_zero_progress(entry.get("progress")):
                    continue
                if tmdb_id and season is not None and number is not None:
                    rows.append(
                        {"tmdb_id": tmdb_id, "season": season, "number": number, "paused_at": paused_at}
                    )
        return rows

    def recent_movies(self):
        rows = self.mdblist_database.get_recent_movies(self.page_limit)
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "movie")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, no_paging=True, hide_watched=False)

    def recent_shows(self):
        rows = self.mdblist_database.get_recent_shows(self.page_limit)
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "show")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, no_paging=True, hide_watched=False)

    def next_up(self):
        """MDBList-scoped 'Next Up': one row per actively-watched show (per MDBList's own
        watched history), each showing that show's next unwatched episode - most recently
        watched show first. Modeled on Red Light's 'MDBList Next Up' (episode.mdblist_next),
        which solves the same naming/identity problem this does: Seren already has a
        Trakt-native Next Up (showsNextUp), so this needs its own label and must work
        entirely off MDBList's own watched state, not trakt_sync's - trakt_sync.episodes.
        watched only reflects Trakt's own activity sync and is meaningless for a
        Trakt-disabled user.

        Anchor and sort are different aggregates over the same watched rows:
        get_recent_shows sorts by MAX(last_watched_at) per show (recency, used for list
        order), while _pick_next_unwatched below checks the full watched set per show to
        find the first gap - not just "one after the last watched" - so an out-of-order
        rewatch doesn't misplace the anchor and a show only leaves the list once every
        episode is watched, matching the reporter's spec exactly.

        Shows are resolved one at a time (like in_progress_episodes above), not through
        the batched _resolve() - _resolve() only echoes back Trakt's own tmdb_id per
        result (which can legitimately differ from the id it was queried with), in
        as_completed() arrival order. This method needs the original MDBList tmdb_id
        intact on every result, both to look up that show's watched set and to preserve
        recent_shows' own recency order, so it keeps that id in scope directly instead of
        trusting it to round-trip through Trakt. get_episode_skeleton() self-bootstraps the
        show row on a cache miss (_update_mill_format_shows -> _get_single_show_meta ->
        _update_single_meta), so skipping _resolve()'s own seeding step is safe. It returns
        only ids, numbering and air dates - get_episode_list() would format and re-save every
        episode of every show on each open - and only the one picked episode per show is
        passed on, so mixed_episode_builder formats just those.

        hide_watched=False on the final mixed_episode_builder call is load-bearing, not
        cosmetic: get_mixed_episode_list() re-applies TraktSyncDatabase's own hide_watched
        default against trakt_sync's e.watched column, which - same as above - is Trakt's
        own flag and not meaningful here. Without the override it can silently empty the
        list for exactly this feature's target users (Trakt disabled, MDBList/Simkl only).

        Capped at _NEXT_UP_SHOW_CAP picks rather than self.page_limit - see that constant's
        comment for why a general browse-page-size setting is the wrong bound here. Shows are
        examined newest-watched first and shows with nothing left to watch are skipped without
        using up a pick; the walk ends at that many picks, _NEXT_UP_SCAN_CAP shows examined,
        or _NEXT_UP_TIME_BUDGET seconds, whichever comes first.

        Only individually watched episodes count as watched. The show and season rows that
        _sync_watched stores in bulk_watched_shows/bulk_watched_seasons are NOT used: MDBList's
        sync/watched returns one for every show and season with any watch history (a Shield
        account had all 93 shows in the table, each stamped with its newest episode's time),
        and crediting them marked every aired episode watched, so Next Up came back empty
        while mdblist.com's own Up Next listed ten shows with gaps (The Office at S1E2, 1%
        watched). The cost of ignoring them: a show that was genuinely bulk-marked watched on
        MDBList and has few individually tracked episodes can show an early episode as its
        'next' (the stale-row problem the old expansion existed to hide)."""
        pick_cap = min(self.page_limit, _NEXT_UP_SHOW_CAP)
        recent_shows = self.mdblist_database.get_recent_shows(_NEXT_UP_SCAN_CAP)
        if not recent_shows:
            g.cancel_directory()
            return

        watched_by_show = {}
        for row in self.mdblist_database.get_all_watched_episode_tmdb_keys():
            watched_by_show.setdefault(row["show_tmdb_id"], set()).add((row["season"], row["number"]))

        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase

        shows_db = ShowsDatabase()
        episodes = []
        started = time.monotonic()
        examined = 0
        for row in recent_shows:
            if len(episodes) >= pick_cap:
                break
            if examined and time.monotonic() - started > _NEXT_UP_TIME_BUDGET:
                g.log(
                    f"MDBList menus: next-up stopped after {examined} shows ({len(episodes)} picks): "
                    f"over the {_NEXT_UP_TIME_BUDGET:.0f}s budget",
                    "debug",
                )
                break
            show_tmdb_id = row["tmdb_id"]
            watched_set = watched_by_show.get(show_tmdb_id)
            if not watched_set:
                continue
            examined += 1
            trakt_show = self.trakt_api.search_by_tmdb_id(show_tmdb_id, "show")
            if not trakt_show or not trakt_show.get("trakt_id"):
                g.log(
                    f"MDBList menus: no Trakt match for tmdb_id {show_tmdb_id} (show), "
                    "skipping next-up",
                    "debug",
                )
                continue
            show_episodes = shows_db.get_episode_skeleton(trakt_show["trakt_id"])
            next_episode = self._pick_next_unwatched(show_episodes, watched_set)
            if next_episode:
                episodes.append(
                    {"trakt_id": next_episode["trakt_id"], "trakt_show_id": next_episode["trakt_show_id"]}
                )

        g.log(f"MDBList menus: next-up examined {examined} shows, {len(episodes)} picks", "debug")
        if not episodes:
            g.cancel_directory()
            return
        self.list_builder.mixed_episode_builder(episodes, no_paging=True, hide_watched=False)

    @staticmethod
    def _pick_next_unwatched(episodes, watched_set):
        """First already-aired, non-special episode not in watched_set, in season/number
        order (get_episode_list's own order). Specials (season 0) are skipped explicitly -
        get_episode_list only drops them when hide_specials is on, and season/number order
        otherwise sorts them first, where they'd wrongly win as 'next' for every show
        (absent from MDBList's watched set by construction, same as any real unwatched
        episode). Unaired episodes are skipped too, so a caught-up show disappears from
        the list instead of offering an unplayable row as its 'next' episode.

        Matches against db_season/db_number (the DB-authoritative columns get_episode_list
        exposes alongside info), not info["season"]/info["episode"] - the latter can hold
        TMDb absolute numbering for shows where formatting rewrote it (see get_episode_list's
        comment), which would silently fail to match watched_set's real season/number keys
        and made every episode of an affected show look unwatched, always picking season 1.
        No fallback to info[...] when db_season/db_number is None: insert_trakt_episodes
        always seeds both from Trakt's own data, and both _format_episodes callers require
        a pre-existing (already Trakt-seeded) row via INNER JOIN before formatting can ever
        run - so this can't actually be None on a real row, and a fallback here would only
        reintroduce the type risk (info's copy can be a string from raw JSON) this fix
        removes."""
        import datetime

        from resources.lib.modules.calendar_data import get_air_date

        now = g.datetime_to_string(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
        for episode in episodes:
            season = episode.get("db_season")
            number = episode.get("db_number")
            if not season or number is None:
                continue
            if (season, number) in watched_set:
                continue
            air_date = get_air_date(episode)
            if not air_date or air_date > now:
                continue
            return episode
        return None

    def in_progress_movies(self):
        rows = self._live_playback_rows("movie")
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "movie")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, no_paging=True)

    def in_progress_episodes(self):
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase

        rows = self._live_playback_rows("episode")
        shows_db = ShowsDatabase()
        hidden_shows = self.hidden_database.get_hidden_items("progress_watched", "tvshow")
        episodes = []
        for row in rows:
            trakt_show = self.trakt_api.search_by_tmdb_id(row["tmdb_id"], "show")
            if not trakt_show or not trakt_show.get("trakt_id"):
                g.log(
                    f"MDBList menus: no Trakt match for tmdb_id {row['tmdb_id']} (show), "
                    "skipping in-progress episode",
                    "debug",
                )
                continue
            if trakt_show["trakt_id"] in hidden_shows:
                continue
            episode = shows_db.get_episode_action_args(trakt_show["trakt_id"], row["season"], row["number"])
            if not episode:
                continue
            episodes.append(episode)
        if not episodes:
            g.cancel_directory()
            return
        self.list_builder.mixed_episode_builder(episodes, no_paging=True)

    def _get_dropped_tmdb_ids(self):
        """tmdb ids on MDBList's dropped list (live GET sync/dropped, shows only, looped over has_more like
        dropped_shows_bulk_restore). A failed call returns what was read so far (possibly nothing): in_progress_shows()
        then keeps a dropped show rather than emptying the list."""
        tmdb_ids = set()
        offset = 0
        for _ in range(20):
            response = self.mdblist_api.get_json("sync/dropped", offset=offset, limit=5000)
            if not isinstance(response, dict):
                break
            for entry in response.get("shows") or []:
                tmdb_id = ((entry.get("show") or {}).get("ids") or {}).get("tmdb")
                if tmdb_id is not None:
                    tmdb_ids.add(tmdb_id)
            if not (response.get("pagination") or {}).get("has_more"):
                break
            offset += 5000
        return tmdb_ids

    def in_progress_shows(self):
        """MDBList-scoped 'In Progress Shows': every show started and not finished, most recently active first -
        the show-level counterpart of in_progress_episodes() (which is one row per paused episode and so misses a
        show followed between episodes), like Trakt's In Progress.

        A show is listed when either (a) it has an individually watched episode (mdblistSync.db, kept in sync with
        sync/watched) and _pick_next_unwatched finds an aired, non-special episode still unwatched - exactly next_up()'s
        rule, so bulk show/season marks are ignored for the same reason (see next_up()) - or (b) it has an episode paused
        part-way (live sync/playback, 0% entries already dropped by _live_playback_rows), which is unfinished by itself
        and needs no episode catalog. Activity time is the later of the show's newest watch and its newest pause (first 19
        characters compared: local writes and MDBList's own strings need not share a format). Shows on MDBList's dropped
        list and shows hidden from progress are left out; a failed dropped lookup keeps them (see
        _get_dropped_tmdb_ids).

        Shows are resolved one at a time, not through _resolve(): _resolve() returns Trakt objects in completion order
        and the show's tmdb_id is needed to look up its watched set and to keep the activity order. hide_watched=False
        on the builder is load-bearing for the same reason as in next_up(): the builder's own default filters on
        Trakt's watched column, which means nothing for an MDBList-only user and can empty the list.

        Same bounds as next_up() (_NEXT_UP_SCAN_CAP most recently watched shows, _NEXT_UP_TIME_BUDGET seconds, checked
        before each show) plus _IN_PROGRESS_SHOW_CAP rows."""
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase

        activity = {}
        paused = set()
        for row in self._live_playback_rows("episode"):
            paused.add(row["tmdb_id"])
            ts = str(row.get("paused_at") or "")[:19]
            if ts > activity.get(row["tmdb_id"], ""):
                activity[row["tmdb_id"]] = ts
            activity.setdefault(row["tmdb_id"], ts)
        for row in self.mdblist_database.get_recent_shows(_NEXT_UP_SCAN_CAP):
            ts = str(row["last_watched_at"] or "")[:19]
            if ts > activity.get(row["tmdb_id"], ""):
                activity[row["tmdb_id"]] = ts
            activity.setdefault(row["tmdb_id"], ts)
        if not activity:
            g.cancel_directory()
            return

        watched_by_show = {}
        for row in self.mdblist_database.get_all_watched_episode_tmdb_keys():
            watched_by_show.setdefault(row["show_tmdb_id"], set()).add((row["season"], row["number"]))

        dropped = self._get_dropped_tmdb_ids()
        hidden_shows = self.hidden_database.get_hidden_items("progress_watched", "tvshow")
        shows_db = ShowsDatabase()
        shows = []
        started = time.monotonic()
        examined = 0
        for tmdb_id, _ in sorted(activity.items(), key=lambda item: item[1], reverse=True):
            if len(shows) >= _IN_PROGRESS_SHOW_CAP:
                break
            if tmdb_id in dropped:
                continue
            if examined and time.monotonic() - started > _NEXT_UP_TIME_BUDGET:
                g.log(
                    f"MDBList menus: in-progress shows stopped after {examined} shows ({len(shows)} listed): "
                    f"over the {_NEXT_UP_TIME_BUDGET:.0f}s budget",
                    "debug",
                )
                break
            examined += 1
            trakt_show = self.trakt_api.search_by_tmdb_id(tmdb_id, "show")
            if not trakt_show or not trakt_show.get("trakt_id"):
                g.log(
                    f"MDBList menus: no Trakt match for tmdb_id {tmdb_id} (show), skipping in-progress show",
                    "debug",
                )
                continue
            if trakt_show["trakt_id"] in hidden_shows:
                continue
            if tmdb_id not in paused:
                watched_set = watched_by_show.get(tmdb_id)
                if not watched_set:
                    continue
                show_episodes = shows_db.get_episode_skeleton(trakt_show["trakt_id"])
                if not self._pick_next_unwatched(show_episodes, watched_set):
                    continue
            shows.append(trakt_show)

        g.log(f"MDBList menus: in-progress shows examined {examined} shows, {len(shows)} listed", "debug")
        if not shows:
            g.cancel_directory()
            return
        self._seed_trakt_sync(shows, "show")
        self.list_builder.show_list_builder(shows, no_paging=True, hide_watched=False)

    @staticmethod
    def _list_context_menu(lst):
        """Right-click actions for a My Lists row. Only Rename/Privacy - Delete is API-
        restricted to static lists, which never reach this menu (they report mediatype=None,
        so my_lists()'s own movie/show filter above always excludes them - see
        _mdblist_static_lists()'s docstring in trakt_context_menu.py for the same finding).
        Static lists are managed from there instead, where they're already reachable.
        """
        list_id = lst.get("id")
        rename_url = g.create_url(
            g.BASE_URL,
            {
                "action": "mdblistListManager",
                "action_args": {"list_id": list_id, "op": "rename", "name": lst.get("name", "")},
            },
        )
        make_private = not lst.get("private")
        privacy_label = g.get_language_string(31055) if make_private else g.get_language_string(31056)
        privacy_url = g.create_url(
            g.BASE_URL,
            {
                "action": "mdblistListManager",
                "action_args": {"list_id": list_id, "op": "privacy", "private": make_private},
            },
        )
        return [
            (g.get_language_string(31054), f'RunPlugin("{rename_url}")'),
            (privacy_label, f'RunPlugin("{privacy_url}")'),
        ]

    def my_lists(self, media_type):
        """Mirrors listsHelper.py's _create_list_menu (Trakt's My Lists) - live API call
        rather than a DB cache, since MDBList list membership isn't synced locally.

        No `sort` kwarg is passed to lists_menu_builder - that would register Kodi's
        client-side SORT_METHOD_LABEL, which silently re-alphabetizes on screen and
        would mask the server-driven sort (ranked/name/created) chosen below. Leaving
        it unset keeps SORT_METHOD_NONE, so the order MDBList returns is authoritative.
        """
        # Carries the active sort forward the same way Next Page does (list_builder.py
        # copies g.REQUEST_PARAMS wholesale) - without this, a second visit to "Sort
        # by..." starts from a request with no `sort` param, and cancelling that dialog
        # would silently revert to the default instead of keeping the current choice.
        current_sort = {"sort": g.REQUEST_PARAMS["sort"]} if g.REQUEST_PARAMS.get("sort") else {}
        g.add_directory_item(
            g.get_language_string(30998),
            action="mdblistMyListsSort",
            mediatype=media_type,
            special_sort="top",
            **current_sort,
        )

        mdb_media_type = "movie" if media_type == "movies" else "show"
        sort = g.REQUEST_PARAMS.get("sort") or "ranked"
        lists = self.mdblist_api.get_json("lists/user", sort=sort) or []
        trakt_list = [
            {
                "info": {"title": self._list_display_name(lst), "mediatype": "list"},
                "args": {"list_id": lst.get("id")},
                "cm": self._list_context_menu(lst),
            }
            for lst in lists
            if lst.get("mediatype") == mdb_media_type
        ]
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.lists_menu_builder(trakt_list, action="mdblistListItems", media_type=media_type)

    def my_lists_sort_picker(self, media_type):
        """Entry point for the "Sort by..." control item on My Lists. Prompts, then
        renders through my_lists() directly (mirrors movieMenus.py's movies_search ->
        movies_search_results split) rather than a Container.Update redirect."""
        heading = f"{g.ADDON_NAME}: {g.get_language_string(30998)}"
        options = [
            (g.get_language_string(30999), "ranked"),
            (g.get_language_string(31000), "name"),
            (g.get_language_string(31001), "created"),
        ]
        selection = xbmcgui.Dialog().select(heading, [label for label, _ in options])
        if selection != -1:
            g.REQUEST_PARAMS["sort"] = options[selection][1]
        self.my_lists(media_type)

    @staticmethod
    def _list_display_name(lst):
        subtitle = g.get_language_string(31041).format(lst.get("items", 0))
        tags = []
        if lst.get("private"):
            tags.append(g.get_language_string(31042))
        if lst.get("dynamic"):
            tags.append(g.get_language_string(31043))
        if tags:
            subtitle = f"{subtitle} · {' · '.join(tags)}"
        return f"{lst.get('name', '')}  {g.color_string(f'[{subtitle}]')}"

    def list_manager(self, action_args):
        """Dispatched from a My Lists row's context menu (see _list_context_menu). Only
        rename/privacy reach here - dynamic lists (the only ones this menu ever shows) can't
        be deleted per the API, so there's no "op" value for it."""
        list_id = action_args["list_id"]
        op = action_args["op"]
        if op == "rename":
            self._rename_list(list_id, action_args.get("name", ""))
        elif op == "privacy":
            self._set_list_privacy(list_id, action_args.get("private", False))

    def _rename_list(self, list_id, current_name):
        name = g.get_keyboard_input(heading=g.get_language_string(31054), default=current_name)
        if not name or name == current_name:
            return
        response = self.mdblist_api.put(f"lists/{list_id}", {"name": name})
        if response is None or not response.ok:
            g.notification(
                f"{g.ADDON_NAME}: {g.get_language_string(30961)}",
                g.get_language_string(30287),
            )
            g.log(f"Failed to rename MDBList list {list_id}\nResponse: {response}")
            return
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30961)}",
            g.get_language_string(31058).format(name),
        )
        g.container_refresh()
        g.trigger_widget_refresh()

    def _set_list_privacy(self, list_id, private):
        response = self.mdblist_api.put(f"lists/{list_id}", {"private": private})
        if response is None or not response.ok:
            g.notification(
                f"{g.ADDON_NAME}: {g.get_language_string(30961)}",
                g.get_language_string(30287),
            )
            g.log(f"Failed to update MDBList list {list_id} privacy\nResponse: {response}")
            return
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30961)}",
            g.get_language_string(31059),
        )
        g.container_refresh()
        g.trigger_widget_refresh()

    def list_items(self):
        """Unlike recent_movies/recent_shows, list content can be arbitrarily long, so this
        fetches and resolves a single bounded page (<=page_limit Trakt lookups, well under
        the _resolve timeout) instead of the whole list. force_next_page passes MDBList's own
        has_more through directly - the default length-based heuristic would misfire here,
        since _resolve can drop unmatched items and shrink a full page below page_limit.

        Uses get() rather than get_json() because MDBList signals pagination via the
        X-Has-More response header, not a body field - get_json() only returns the parsed
        body, so the header would otherwise be unreachable here.

        sort/order/filter_* are read from g.REQUEST_PARAMS rather than function args, same
        as list_id/media_type above - this lets them ride the existing Next Page rebuild
        (list_builder.py copies g.REQUEST_PARAMS forward wholesale) with no extra plumbing.
        """
        arguments = g.REQUEST_PARAMS['action_args']
        list_id = arguments['list_id']
        media_type = g.REQUEST_PARAMS.get('media_type')
        mdb_media_type = "movie" if media_type == "movies" else "show"

        # Same forwarding as my_lists()'s sort control - without carrying the active
        # sort/filter_* along, a second visit to "Sort / Filter..." would start from a
        # request with none of them set, silently dropping whatever's currently applied
        # (list_items_menu()'s "Clear All Filters" option would also never appear).
        active_filters = {key: g.REQUEST_PARAMS[key] for key in _FILTER_KEYS if g.REQUEST_PARAMS.get(key)}
        g.add_directory_item(
            g.get_language_string(31002),
            action="mdblistListItemsMenu",
            action_args={"list_id": list_id},
            media_type=media_type,
            special_sort="top",
            **active_filters,
        )

        offset = (g.PAGE - 1) * self.page_limit
        query_params = {"limit": self.page_limit, "offset": offset}
        for key in _FILTER_KEYS:
            value = g.REQUEST_PARAMS.get(key)
            if value:
                query_params[key] = value

        try:
            api_response = self.mdblist_api.get(f"lists/{list_id}/items", **query_params)
        except Exception as e:
            g.log(f"MDBList menus: failed to fetch list items for list {list_id}: {e}", "error")
            api_response = None

        if api_response is not None and api_response.ok:
            try:
                response = api_response.json()
            except ValueError:
                response = {}
            has_more = api_response.headers.get("X-Has-More", "").lower() == "true"
        else:
            response = {}
            has_more = False

        raw_items = response.get("movies" if mdb_media_type == "movie" else "shows") or []
        tmdb_ids = [item["id"] for item in raw_items if item.get("id")]
        trakt_list = self._resolve(tmdb_ids, mdb_media_type)
        if not trakt_list:
            g.cancel_directory()
            return
        if mdb_media_type == "movie":
            self.list_builder.movie_menu_builder(trakt_list, hide_watched=False, force_next_page=has_more)
        else:
            self.list_builder.show_list_builder(trakt_list, hide_watched=False, force_next_page=has_more)

    def list_items_menu(self):
        """Hub for list-items' "Sort / Filter..." control item: prompts via a nested
        Dialog().select()/input(), applies the choice to g.REQUEST_PARAMS (resetting to
        page 1 - a new sort/filter on page 3 of the old query would otherwise land on
        page 3 of the new one), then renders through the unchanged list_items()."""
        heading = f"{g.ADDON_NAME}: {g.get_language_string(31002)}"
        options = [(g.get_language_string(30998), "sort")]
        options.append((g.get_language_string(31003), "filter_title"))
        options.append((g.get_language_string(31004), "filter_genre"))
        options.append((g.get_language_string(31005), "released"))
        if self.mdblist_api.is_supporter():
            options.append((g.get_language_string(31006), "rating"))
        if any(g.REQUEST_PARAMS.get(key) for key in _FILTER_KEYS):
            options.append((g.get_language_string(31007), "clear"))

        selection = xbmcgui.Dialog().select(heading, [label for label, _ in options])
        if selection != -1:
            choice = options[selection][1]
            {
                "sort": self._pick_sort,
                "filter_title": self._pick_filter_title,
                "filter_genre": self._pick_filter_genre,
                "released": self._pick_release_range,
                "rating": self._pick_rating_filter,
                "clear": self._clear_filters,
            }[choice]()
        self.list_items()

    @staticmethod
    def _pick_sort():
        heading = f"{g.ADDON_NAME}: {g.get_language_string(30998)}"
        labels = [g.get_language_string(sid) for _, sid in _LIST_ITEMS_SORT_OPTIONS]
        selection = xbmcgui.Dialog().select(heading, labels)
        if selection == -1:
            return
        sort_key = _LIST_ITEMS_SORT_OPTIONS[selection][0]

        order_selection = xbmcgui.Dialog().select(
            heading, [g.get_language_string(31008), g.get_language_string(31009)]
        )
        if order_selection == -1:
            return

        g.REQUEST_PARAMS["sort"] = sort_key
        g.REQUEST_PARAMS["order"] = "asc" if order_selection == 0 else "desc"
        g.REQUEST_PARAMS["page"] = 1
        g.PAGE = 1

    @staticmethod
    def _pick_filter_title():
        current = g.REQUEST_PARAMS.get("filter_title", "")
        value = g.get_keyboard_input(heading=g.get_language_string(31003), default=current)
        if value is None:
            return
        if value:
            g.REQUEST_PARAMS["filter_title"] = value
        else:
            g.REQUEST_PARAMS.pop("filter_title", None)
        g.REQUEST_PARAMS["page"] = 1
        g.PAGE = 1

    def _pick_filter_genre(self):
        # anime=0 (regular genres) - the spec doesn't document a default when omitted,
        # and the endpoint's own example response is all-anime, so this is passed
        # explicitly rather than relied on.
        genres = self.mdblist_api.get_json("genres", anime=0) or []
        heading = f"{g.ADDON_NAME}: {g.get_language_string(31004)}"
        labels = [g.get_language_string(31010)] + [genre.get("title", genre.get("slug", "")) for genre in genres]
        selection = xbmcgui.Dialog().select(heading, labels)
        if selection == -1:
            return
        if selection == 0:
            g.REQUEST_PARAMS.pop("filter_genre", None)
        else:
            g.REQUEST_PARAMS["filter_genre"] = genres[selection - 1].get("slug")
        g.REQUEST_PARAMS["page"] = 1
        g.PAGE = 1

    @staticmethod
    def _pick_release_range():
        from_value = g.get_keyboard_input(
            heading=g.get_language_string(31011), default=g.REQUEST_PARAMS.get("released_from", "")
        )
        if from_value is None:
            return
        to_value = g.get_keyboard_input(
            heading=g.get_language_string(31012), default=g.REQUEST_PARAMS.get("released_to", "")
        )
        if to_value is None:
            return

        if from_value and _DATE_RE.match(from_value):
            g.REQUEST_PARAMS["released_from"] = from_value
        elif not from_value:
            g.REQUEST_PARAMS.pop("released_from", None)
        if to_value and _DATE_RE.match(to_value):
            g.REQUEST_PARAMS["released_to"] = to_value
        elif not to_value:
            g.REQUEST_PARAMS.pop("released_to", None)
        g.REQUEST_PARAMS["page"] = 1
        g.PAGE = 1

    @staticmethod
    def _pick_rating_filter():
        heading = f"{g.ADDON_NAME}: {g.get_language_string(31006)}"
        labels = [g.get_language_string(sid) for _, sid in _RATING_FILTER_SOURCES]
        selection = xbmcgui.Dialog().select(heading, labels)
        if selection == -1:
            return
        prefix, label_id = _RATING_FILTER_SOURCES[selection]
        source_label = g.get_language_string(label_id)

        min_key, max_key = f"filter_{prefix}_min", f"filter_{prefix}_max"
        min_value = xbmcgui.Dialog().input(
            f"{source_label}: {g.get_language_string(31013)}",
            str(g.REQUEST_PARAMS.get(min_key, "")),
            xbmcgui.INPUT_NUMERIC,
        )
        max_value = xbmcgui.Dialog().input(
            f"{source_label}: {g.get_language_string(31014)}",
            str(g.REQUEST_PARAMS.get(max_key, "")),
            xbmcgui.INPUT_NUMERIC,
        )

        if min_value:
            g.REQUEST_PARAMS[min_key] = min_value
        else:
            g.REQUEST_PARAMS.pop(min_key, None)
        if max_value:
            g.REQUEST_PARAMS[max_key] = max_value
        else:
            g.REQUEST_PARAMS.pop(max_key, None)
        g.REQUEST_PARAMS["page"] = 1
        g.PAGE = 1

    @staticmethod
    def _clear_filters():
        for key in _FILTER_KEYS:
            g.REQUEST_PARAMS.pop(key, None)
        g.REQUEST_PARAMS["page"] = 1
        g.PAGE = 1

    # region Discover (Phase 4) - browsing other users'/public lists, read-only.
    # Always media_type-paired at the entry point (movieMenus.py/tvshowMenus.py, same as
    # In Progress/Recently Watched/My Lists above) rather than one unified mixed screen -
    # Top/Search/User-lists all return movie and show lists together with no server-side
    # mediatype filter, but list_items() (reused as-is below) only ever renders one
    # mediatype per call, and a single mixed directory would also surface show-lists under
    # the Movies menu, fighting this addon's existing navigation model. Splitting client-side
    # here - the same `if lst.get("mediatype") == mdb_media_type` idiom my_lists() already
    # uses - needs zero changes to list_items()/list_builder.py, so the already-live-verified
    # My Lists path is untouched. Public lists with an unset mediatype (mixed-content or
    # unset-mediatype static lists, same class as Phase 1/3's own static-list finding) are
    # silently excluded from both the movie and show views - a known, deferred gap, not fixed
    # here, matching the user's Phase 3 choice not to unify browsing across list shapes.

    def discover_hub(self, media_type):
        g.add_directory_item(
            g.get_language_string(31065),
            action="mdblistTopLists",
            description=g.get_language_string(31577),
            mediatype=media_type,
            menu_item=g.create_icon_dict("list", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(31066),
            action="mdblistListSearch",
            description=g.get_language_string(31578),
            action_args={"media_type": media_type},
            menu_item=g.create_icon_dict("movies_search", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(31067),
            action="mdblistUserLists",
            description=g.get_language_string(31579),
            action_args={"media_type": media_type},
            menu_item=g.create_icon_dict("list", g.ICONS_PATH),
        )
        g.close_directory(g.CONTENT_MENU)

    def _discover_results(self, lists, media_type):
        """Shared render step for Top/Search/User-lists. no_paging=True: none of the
        3 source endpoints document limit/offset params (confirmed against mdblist.apib -
        unlike /lists/{listid}/items, they always return their full result set in one
        response), so Kodi's own length-based Next Page heuristic would otherwise offer a
        button that just re-fetches the identical unpaginated list, not a new page."""
        mdb_media_type = "movie" if media_type == "movies" else "show"
        trakt_list = [
            {
                "info": {"title": self._list_display_name(lst), "mediatype": "list"},
                "args": {"list_id": lst.get("id")},
            }
            for lst in lists
            if lst.get("mediatype") == mdb_media_type
        ]
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.lists_menu_builder(
            trakt_list, action="mdblistListItems", media_type=media_type, no_paging=True
        )

    def top_lists(self, media_type):
        lists = self.mdblist_api.get_json("lists/top") or []
        self._discover_results(lists, media_type)

    def list_search(self, action_args):
        media_type = action_args.get("media_type")
        query = action_args.get("query")
        if not query:
            query = g.get_keyboard_input(heading=g.get_language_string(31066))
            if not query:
                g.cancel_directory(silent=True)
                return
        lists = self.mdblist_api.get_json("lists/search", query=query) or []
        self._discover_results(lists, media_type)

    def user_lists(self, action_args):
        media_type = action_args.get("media_type")
        username = action_args.get("username")
        if not username:
            username = g.get_keyboard_input(heading=g.get_language_string(31067))
            if not username:
                g.cancel_directory(silent=True)
                return
        lists = self.mdblist_api.get_json(f"lists/user/{quote(username, safe='')}") or []
        self._discover_results(lists, media_type)

    def liked_lists(self, media_type):
        """MDBList lists this account has liked (not owned) - grouped in this region and
        implemented like top_lists()/list_search()/user_lists() above (other users' lists,
        no rename/privacy context menu, unlike my_lists()'s own-list entries), reusing
        _discover_results() directly rather than duplicating its list-comprehension.

        /lists/liked isn't in mdblist.apib (unlike /lists/user, /sync/collection,
        /sync/dropped, /watchlist/items, which all are) - confirmed working via a live call
        and cross-referenced against two other addons' source (both independently call this
        same undocumented path), but it's a softer guarantee than this file's other
        endpoints. Response envelope is {"lists": [...], "pagination": {...}} - unwrapped
        here since _discover_results() (like top_lists() etc.) expects a plain list.
        """
        response = self.mdblist_api.get_json("lists/liked") or {}
        self._discover_results(response.get("lists") or [], media_type)

    # endregion

    # region Collection / Dropped - live status-style menus, mirroring simklMenus.py's
    # _status_movies/_status_shows: never written to mdblistSync.db (that table isn't
    # read by bridgeSync.py at all today, but keeping every status-style menu live-fetch-
    # only is the same deliberate choice simklMenus.py documents on its own class, and
    # this stays consistent with it rather than introduce a second convention).

    def _collection(self, media_type):
        """Live MDBList sync/collection fetch for Collection Movies/Shows - resolved via
        Trakt and rendered through list_builder, same as recent_movies()/list_items()
        above, never written into mdblistSync.db.

        Unlike list_items()'s /lists/{id}/items or dropped_shows()'s /sync/dropped below,
        /sync/collection has no mediatype filter or path-suffix param anywhere in its spec
        (mdblist.apib's Sync group - contrast /lists/{user}/{list}/items's documented
        .../movie/, .../show/ suffixes): movies and shows share one offset/limit window
        and one has_more flag. That's inferred from the response shape (a single
        pagination block wrapping both arrays), not a documented guarantee - the spec
        never states in prose that the two types share a cursor, only implies it
        structurally.

        Requests the documented max (limit=5000) rather than the 1000 default, then
        slices the requested type's array client-side by page - same idiom as Simkl's
        _status_movies/_status_shows (simklMenus.py), which have zero server pagination
        at all and always slice a fully-fetched bucket client-side. A pathological
        account with >5000 combined collected items, skewed so one type sorts entirely
        outside the window, could still starve the other type on its last page or two -
        a known limitation of the shared cursor, not fixed here.
        """
        response = self.mdblist_api.get_json("sync/collection", limit=5000, offset=0) or {}

        entry_key = "movies" if media_type == "movie" else "shows"
        object_key = "movie" if media_type == "movie" else "show"
        tmdb_ids = []
        for entry in response.get(entry_key) or []:
            ids = (entry.get(object_key) or {}).get("ids") or {}
            tmdb_id = ids.get("tmdb")
            if tmdb_id is not None:
                tmdb_ids.append(tmdb_id)

        page_start = (g.PAGE - 1) * self.page_limit
        page_end = g.PAGE * self.page_limit
        has_more = len(tmdb_ids) > page_end
        trakt_list = self._resolve(tmdb_ids[page_start:page_end], media_type)
        if not trakt_list:
            g.cancel_directory()
            return
        # Mirrors this addon's own Trakt Collection menus' asymmetry: my_movie_collection
        # (movieMenus.py) doesn't override hide_watched, my_shows_collection (tvshowMenus.py)
        # forces hide_watched=False - matched here per-type rather than picking one
        # convention, since that's what the existing sibling menus already do.
        if media_type == "movie":
            self.list_builder.movie_menu_builder(trakt_list, force_next_page=has_more)
        else:
            self.list_builder.show_list_builder(trakt_list, hide_watched=False, force_next_page=has_more)

    def collection_movies(self):
        self._collection("movie")

    def collection_shows(self):
        self._collection("show")

    def dropped_shows(self):
        """Live MDBList sync/dropped fetch - shows only. The API's own POST rules state
        "Shows only" (mdblist.apib's Dropped Shows section) and there is no dropped-movies
        equivalent anywhere in the spec, unlike Simkl which has both.

        Unlike _collection() above, /sync/dropped is single-type and paginates for real -
        its own offset/limit/has_more, not inferred from response shape - so this uses
        true server-side paging instead of fetch-then-slice. Two different pagination
        idioms in one file is intentional, not an inconsistency to fix: each endpoint's
        actual contract dictates which one applies.
        """
        offset = (g.PAGE - 1) * self.page_limit
        response = self.mdblist_api.get_json("sync/dropped", offset=offset, limit=self.page_limit) or {}

        tmdb_ids = []
        for entry in response.get("shows") or []:
            ids = (entry.get("show") or {}).get("ids") or {}
            tmdb_id = ids.get("tmdb")
            if tmdb_id is not None:
                tmdb_ids.append(tmdb_id)

        has_more = bool((response.get("pagination") or {}).get("has_more"))
        if g.PAGE == 1:
            g.add_directory_item(
                g.get_language_string(31547),
                action="mdblistDroppedShowsRestore",
                description=g.get_language_string(31548),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
        trakt_list = self._resolve(tmdb_ids, "show")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, hide_watched=False, force_next_page=has_more)

    def dropped_shows_bulk_restore(self):
        """Live-fetch sync/dropped raw (not Trakt-resolved, unlike dropped_shows() above) -
        the multiselect dialog only needs title/year text, and MDBList's own response
        already carries both directly on each entry (mdblist.apib's Dropped Shows GET
        example), so there's no need to round-trip through Trakt just to power a plain-
        text picker. Mirrors tvshowMenus.py's dropped_shows_bulk_restore() shape (fetch
        all, multiselect, POST .../remove) but keyed on tmdb ids, MDBList's own id space,
        rather than trakt_id. No local DB write on restore, matching dropped_shows()
        being live-fetch-only above - there was never a local dropped record to clear.

        Loops offset/has_more (dropped_shows()'s own real server-side pagination, see
        its docstring) to collect every dropped show rather than capping at one page -
        unlike _collection()'s documented 5000-item limitation above, sync/dropped is
        single-type with a real has_more flag, so there's no shared-cursor obstacle to
        looping past it, and the multiselect dialog needs the complete set anyway.
        """
        entries = []
        offset = 0
        while True:
            response = self.mdblist_api.get_json("sync/dropped", offset=offset, limit=5000) or {}
            for entry in response.get("shows") or []:
                show = entry.get("show") or {}
                tmdb_id = (show.get("ids") or {}).get("tmdb")
                if tmdb_id is None:
                    continue
                title = show.get("title") or ""
                year = show.get("year")
                entries.append((tmdb_id, f"{title} ({year})" if year else title))
            if not (response.get("pagination") or {}).get("has_more"):
                break
            offset += 5000

        if not entries:
            g.notification(g.ADDON_NAME, g.get_language_string(31550))
            self.dropped_shows()
            return

        selected = xbmcgui.Dialog().multiselect(
            f"{g.ADDON_NAME}: {g.get_language_string(31548)}", [e[1] for e in entries]
        )
        if not selected:
            self.dropped_shows()
            return

        tmdb_ids = [entries[i][0] for i in selected]
        self.mdblist_api.post_json(
            "sync/dropped/remove", {"shows": [{"ids": {"tmdb": i}} for i in tmdb_ids]}
        )

        g.notification(g.ADDON_NAME, g.get_language_string(31549).format(len(tmdb_ids)))
        self.dropped_shows()

    def _watchlist(self, media_type):
        """Live MDBList watchlist/items fetch for Watchlist Movies/Shows. mdblist.apib's
        Watchlist group documents limit/offset, but a live response carries one pagination
        block for both movies and shows together (same shared-cursor shape as
        sync/collection above) - so this uses _collection()'s fetch-5000-then-slice idiom,
        for the same reason. Never written into mdblistSync.db, same as Collection/Dropped.

        Unlike _collection()/dropped_shows(), each entry's ids sit flat on the entry itself
        (entry["ids"]["tmdb"]) rather than nested under a "movie"/"show" sub-key - confirmed
        against a live response, not assumed from the sibling endpoints' shape.

        Seren already writes to this watchlist via cross_sync.py's mirror_watchlist_add_
        from_trakt/from_simkl whenever a user watchlists something on Trakt or sets Simkl
        to Plan to Watch - this is the first menu that lets a user actually see it.
        """
        response = self.mdblist_api.get_json("watchlist/items", limit=5000, offset=0) or {}

        entry_key = "movies" if media_type == "movie" else "shows"
        tmdb_ids = []
        for entry in response.get(entry_key) or []:
            tmdb_id = (entry.get("ids") or {}).get("tmdb")
            if tmdb_id is not None:
                tmdb_ids.append(tmdb_id)

        page_start = (g.PAGE - 1) * self.page_limit
        page_end = g.PAGE * self.page_limit
        has_more = len(tmdb_ids) > page_end
        trakt_list = self._resolve(tmdb_ids[page_start:page_end], media_type)
        if not trakt_list:
            g.cancel_directory()
            return
        if media_type == "movie":
            self.list_builder.movie_menu_builder(trakt_list, force_next_page=has_more)
        else:
            self.list_builder.show_list_builder(trakt_list, hide_watched=False, force_next_page=has_more)

    def watchlist_movies(self):
        self._watchlist("movie")

    def watchlist_shows(self):
        self._watchlist("show")

    # endregion
