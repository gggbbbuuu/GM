import re
from concurrent.futures import as_completed
from functools import cached_property

from resources.lib.common.thread_pool import ThreadPoolExecutor
from resources.lib.modules.globals import g

# Same bound and reason as mdblistMenus._NEXT_UP_SHOW_CAP: every show reaching the episode
# lookup can trigger a one-time, synchronous cold bootstrap of that show's season list.
_NEXT_UP_SHOW_CAP = 10

# Simkl's next_to_watch is 'S01E04' for most shows. Some anime entries carry a bare 'E2'
# (no season): Simkl counts those per entry (cour/season), which cannot be mapped to a Trakt
# season/episode without an anime id table, so they are skipped rather than guessed.
_NEXT_TO_WATCH_REGEX = re.compile(r"^S(\d+)E(\d+)$", re.IGNORECASE)


class Menus:
    """Simkl-sourced menus (Recently Watched, In Progress, and the per-status
    browse entries - movies: Plan to Watch/Completed/Dropped; shows: Watching/Plan
    to Watch/Hold/Completed/Dropped).

    recent_movies/recent_shows/in_progress_* read local simklSync.db rows (built
    Phase 3) keyed by tmdb_id. _status_movies()/_status_shows() instead call Simkl's
    sync/all-items/{movies,shows}/{status} live, per menu-open - deliberately not
    synced into simklSync.db, since that table's movies.watched=1 rows are what
    recent_movies() shows as watched (bridgeSync used to read them for the cross-service
    push; since 3.9.31 it reads Simkl live) (see _status_movies' own docstring; _status_shows() is lower-risk still, since
    trakt_sync.shows has no watched/collected column at all to corrupt). Either way,
    each item is resolved to a Trakt object via TraktAPI.search_by_tmdb_id (Trakt's
    ID lookup - no personal OAuth needed) before being handed to the existing,
    unmodified Trakt-native ListBuilder methods - identical reuse path to
    mdblistMenus.py's Menus class. Unlike that file, there is still no My Lists/
    Discover section here: Simkl's "lists" are watch-status buckets, not named
    lists - the per-status browse entries above are the closest equivalent Simkl
    has to that concept.
    """

    def __init__(self):
        self.page_limit = g.get_int_setting("item.limit")
        self.page_start = (g.PAGE - 1) * self.page_limit
        self.page_end = g.PAGE * self.page_limit

    @cached_property
    def simkl_database(self):
        from resources.lib.database.simkl_sync import SimklSyncDatabase

        return SimklSyncDatabase()

    @cached_property
    def trakt_api(self):
        from resources.lib.indexers.trakt import TraktAPI

        return TraktAPI()

    @cached_property
    def simkl_api(self):
        from resources.lib.indexers.simkl import SimklAPI

        return SimklAPI()

    @cached_property
    def hidden_database(self):
        from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase as HiddenDatabase

        return HiddenDatabase()

    @cached_property
    def list_builder(self):
        from resources.lib.modules.list_builder import ListBuilder

        return ListBuilder()

    def _resolve(self, tmdb_ids, media_type):
        """Resolves tmdb_ids to Trakt objects in parallel (mirrors
        mdblistMenus.py's Menus._resolve() exactly), dropping (and logging) any id
        Trakt has no match for - or that errors/times out - rather than failing the
        whole list. tmdb_ids is already NULL-filtered by the SimklSyncDatabase query
        methods that feed this (get_recent_movies/get_recent_shows/get_bookmarks all
        filter tmdb_id IS NOT NULL), so no None-guard is needed here."""
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
                g.log(f"Simkl menus: resolve batch timed out, using partial results: {e}", "warning")
                for future in futures:
                    if future.done():
                        resolved_item = self._collect_resolved(future, futures[future], media_type)
                        if resolved_item:
                            resolved.append(resolved_item)
        finally:
            # wait=False enforces the 20s as_completed ceiling rather than blocking on
            # shutdown - see mdblistMenus.py's identical finally block for the full
            # reasoning. cancel_futures drops queued-but-unstarted lookups (backported to
            # Python 3.8 by common/thread_pool.py); running futures still finish in the
            # background, and nothing here reads their results.
            executor.shutdown(wait=False, cancel_futures=True)

        if resolved:
            self._seed_trakt_sync(resolved, media_type)
        return resolved

    @staticmethod
    def _seed_trakt_sync(resolved, media_type):
        """Writes freshly-resolved items into the local Trakt sync DB, identical to
        mdblistMenus.py's Menus._seed_trakt_sync() - see that method's docstring for
        why this is required before movie_menu_builder/show_list_builder can render
        them."""
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
            g.log(f"Simkl menus: error resolving tmdb_id {tmdb_id} ({media_type}): {e}", "warning")
            return None
        if not trakt_object or not trakt_object.get("trakt_id"):
            g.log(f"Simkl menus: no Trakt match for tmdb_id {tmdb_id} ({media_type}), skipping", "debug")
            return None
        return trakt_object

    def recent_movies(self):
        rows = self.simkl_database.get_recent_movies(self.page_limit)
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "movie")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, no_paging=True, hide_watched=False)

    def recent_shows(self):
        rows = self.simkl_database.get_recent_shows(self.page_limit)
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "show")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, no_paging=True, hide_watched=False)

    def in_progress_movies(self):
        rows = self.simkl_database.get_bookmarks("movie")
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "movie")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, no_paging=True)

    def in_progress_episodes(self):
        rows = self.simkl_database.get_bookmarks("episode")
        if not rows:
            g.cancel_directory()
            return
        episodes = self._resolve_episode_rows(rows)
        if not episodes:
            g.cancel_directory()
            return
        self.list_builder.mixed_episode_builder(episodes, no_paging=True)

    def next_up(self):
        """Simkl-scoped 'Next Up': one row per actively-watching show (Simkl status
        'watching' with at least one watched episode), showing Simkl's own next_to_watch
        episode, most recently watched show first. Reads the local simklSync.db shows table
        (kept current by syncSimklActivities) - no live API call - and resolves each pick the
        same way in_progress_episodes() does: Trakt id lookup, then one SELECT for that
        episode's ids; get_mixed_episode_list() then formats only those episodes. It never
        calls get_episode_list(), which formats every episode of the show.

        Only 'SxxEyy' values are placed. A bare 'E2' (some anime entries) is skipped and
        counted in the log. hide_watched=False is load-bearing for the same reason as in
        mdblistMenus.next_up(): get_mixed_episode_list() would otherwise apply Trakt's own
        watched flag, meaningless for a Trakt-disabled user. Unaired episodes still drop out
        through its hide_unaired default, so a lagging next_to_watch shows nothing, not an
        unplayable row."""
        targets = []
        unplaced = 0
        for row in self.simkl_database.get_next_to_watch_shows():
            match = _NEXT_TO_WATCH_REGEX.match((row["next_to_watch"] or "").strip())
            if not match or int(match.group(1)) < 1:
                unplaced += 1
                continue
            targets.append({"tmdb_id": row["tmdb_id"], "season": int(match.group(1)), "number": int(match.group(2))})
            if len(targets) >= _NEXT_UP_SHOW_CAP:
                break
        if unplaced:
            g.log(f"Simkl menus: next-up skipped {unplaced} show(s) whose next_to_watch has no season", "debug")
        episodes = self._resolve_episode_rows(targets) if targets else []
        if not episodes:
            g.cancel_directory()
            return
        self.list_builder.mixed_episode_builder(episodes, no_paging=True, hide_watched=False)

    def _resolve_episode_rows(self, rows):
        """rows: dicts with tmdb_id/season/number. Returns episode action-args dicts in row
        order, dropping rows Trakt cannot place, shows hidden under progress_watched, and
        anything that errors or misses the 20 s ceiling."""
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase

        shows_db = ShowsDatabase()
        hidden_shows = self.hidden_database.get_hidden_items("progress_watched", "tvshow")
        results = [None] * len(rows)
        executor = ThreadPoolExecutor(max_workers=min(10, len(rows)))
        try:
            futures = {
                executor.submit(self.trakt_api.search_by_tmdb_id, row["tmdb_id"], "show"): i
                for i, row in enumerate(rows)
            }
            seen = set()
            try:
                for future in as_completed(futures, timeout=20):
                    i = futures[future]
                    results[i] = self._collect_in_progress_episode(future, rows[i], shows_db, hidden_shows)
                    seen.add(i)
            except Exception as e:
                g.log(f"Simkl menus: in-progress episode resolve batch timed out, using partial results: {e}", "warning")
                for future in futures:
                    i = futures[future]
                    if i not in seen and future.done():
                        results[i] = self._collect_in_progress_episode(future, rows[i], shows_db, hidden_shows)
        finally:
            # wait=False enforces the 20s as_completed ceiling rather than blocking on
            # shutdown - see _resolve()'s identical finally block for the full reasoning.
            # cancel_futures drops queued-but-unstarted lookups (backported to Python 3.8
            # by common/thread_pool.py); running futures finish in the background unread.
            executor.shutdown(wait=False, cancel_futures=True)
        return [ep for ep in results if ep]

    @staticmethod
    def _collect_in_progress_episode(future, row, shows_db, hidden_shows):
        try:
            trakt_show = future.result()
        except Exception as e:
            g.log(f"Simkl menus: error resolving tmdb_id {row['tmdb_id']} (show): {e}", "warning")
            return None
        if not trakt_show or not trakt_show.get("trakt_id"):
            g.log(
                f"Simkl menus: no Trakt match for tmdb_id {row['tmdb_id']} (show), "
                "skipping in-progress episode",
                "debug",
            )
            return None
        if trakt_show["trakt_id"] in hidden_shows:
            return None
        try:
            return shows_db.get_episode_action_args(trakt_show["trakt_id"], row["season"], row["number"])
        except Exception as e:
            g.log(f"Simkl menus: error building episode args for tmdb_id {row['tmdb_id']} (show): {e}", "warning")
            return None

    def _status_movies(self, status):
        """Live Simkl status-bucket fetch for My Movies (Plan to Watch/Completed/
        Dropped) - resolves via Trakt and renders through list_builder same as
        recent_movies()/in_progress_movies(), rather than writing into the local
        simklSync.db movies table. That table's watched=1 rows are what recent_movies()
        shows as watched (bridgeSync used to read them too, before 3.9.31) - seeding
        plantowatch/dropped (i.e. unwatched) rows into it would show them as watched.

        sync/all-items has no server-side pagination - one call always returns the
        whole bucket - so the tmdb_id list is sliced to the current page *before*
        the resolve step, bounding the Trakt-search cost to one page regardless of
        bucket size (a Completed bucket can run into the hundreds).

        force_next_page is passed explicitly (mirrors mdblistMenus.py's has_more
        pattern) rather than left to list_builder's default len(list_items) >=
        page_limit heuristic: that heuristic assumes the renderer receives at most
        one page's worth of rows, but resolve() can silently drop tmdb_ids with no
        Trakt match, so a full raw slice can render short. has_more instead reflects
        whether unsliced candidates remain past this page, independent of how many
        of this page's candidates actually resolved."""
        page = self.simkl_api.get_json(f"sync/all-items/movies/{status}")
        if page is None:
            g.cancel_directory()
            return

        tmdb_ids = []
        for entry in page.get("movies") or []:
            ids = (entry.get("movie") or {}).get("ids") or {}
            tmdb_id = ids.get("tmdb")
            if tmdb_id is not None:
                tmdb_ids.append(tmdb_id)

        has_more = len(tmdb_ids) > self.page_end
        trakt_list = self._resolve(tmdb_ids[self.page_start : self.page_end], "movie")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, hide_watched=False, force_next_page=has_more)

    def plan_to_watch_movies(self):
        self._status_movies("plantowatch")

    def completed_movies(self):
        self._status_movies("completed")

    def dropped_movies(self):
        self._status_movies("dropped")

    def _status_shows(self, status):
        """Show-side sibling of _status_movies - same live-fetch-then-resolve
        rationale applies (see that method's docstring), and is in fact even lower-
        risk here: insert_trakt_shows()'s upsert has no watched/collected column at
        all (show-level watch state doesn't exist in trakt_sync.shows - it's tracked
        per-episode elsewhere, untouched by this path), so there is no field this
        could corrupt even in principle.

        Also passes force_next_page explicitly - see _status_movies' docstring for
        why the default page_limit heuristic isn't reliable here (confirmed live:
        Completed Shows rendered 1 item but still showed a Next Page that led to a
        genuinely empty page, before this was added)."""
        page = self.simkl_api.get_json(f"sync/all-items/shows/{status}")
        if page is None:
            g.cancel_directory()
            return

        tmdb_ids = []
        for entry in page.get("shows") or []:
            ids = (entry.get("show") or {}).get("ids") or {}
            tmdb_id = ids.get("tmdb")
            if tmdb_id is not None:
                tmdb_ids.append(tmdb_id)

        has_more = len(tmdb_ids) > self.page_end
        trakt_list = self._resolve(tmdb_ids[self.page_start : self.page_end], "show")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, hide_watched=False, force_next_page=has_more)

    def watching_shows(self):
        self._status_shows("watching")

    def plan_to_watch_shows(self):
        self._status_shows("plantowatch")

    def hold_shows(self):
        self._status_shows("hold")

    def completed_shows(self):
        self._status_shows("completed")

    def dropped_shows(self):
        self._status_shows("dropped")
