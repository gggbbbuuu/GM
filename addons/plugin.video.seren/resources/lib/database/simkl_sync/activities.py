from functools import cached_property

import xbmc

from resources.lib.database import simkl_sync
from resources.lib.modules.exceptions import ActivitySyncFailure
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g


class SimklSyncDatabase(simkl_sync.SimklSyncDatabase):
    def __init__(self):
        super().__init__()

    @cached_property
    def simkl_api(self):
        from resources.lib.indexers.simkl import SimklAPI

        return SimklAPI()

    def _update_activity_record(self, record, value):
        self.execute_sql(f"UPDATE activities SET {record}=? WHERE sync_id=1", (value,))

    def clear_last_sync(self):
        """Clear-button counterpart to force_sync(). Notifies here rather than in
        set_base_activities() itself, since force_sync() also calls that as its
        first step - notifying there would fire a misleading "cleared" toast on
        every Force Sync click too."""
        self.set_base_activities()
        g.notification(g.ADDON_NAME, g.get_language_string(31121))

    def force_sync(self):
        """Resets the sync cursor to base_date and re-runs a full sync. Uses
        set_base_activities() rather than the existing flush_activities() (which
        deletes movies/shows/bookmarks) so this button's semantics match Trakt's
        non-destructive "Clear last sync time" - flush_activities() stays reserved
        for its original account-switch use case."""
        from resources.lib.database.trakt_sync import clear_list_cache

        self.set_base_activities()
        clear_list_cache()
        self.sync_activities()

    def sync_activities(self):
        with GlobalLock("simkl.sync"):
            if not g.get_bool_setting("simkl.enabled") or not g.get_setting("simkl.auth"):
                g.log("SimklSync: Simkl disabled or no auth present, no sync will occur", "warning")
                return

            self.refresh_activities()
            remote_activities = self.simkl_api.get_json("sync/activities")
            if not remote_activities:
                g.log("Simkl Activities Sync Failure: unable to connect to Simkl", "error")
                return True

            # Cheapest possible check first, per simkl.apib's own recommended sync loop -
            # if the top-level cursor hasn't moved, nothing in any tracked domain changed.
            remote_all = remote_activities.get("all")
            if remote_all and remote_all == self.activities["all_at"]:
                return

            movies_count = 0
            shows_count = 0
            playback_count = 0
            any_failed = False

            remote_movies = remote_activities.get("movies") or {}
            remote_shows = remote_activities.get("tv_shows") or {}
            remote_anime = remote_activities.get("anime") or {}

            movies_remote_completed = remote_movies.get("completed")
            movies_stale = self.requires_update(movies_remote_completed, self.activities["movies_completed_at"])
            if movies_stale:
                try:
                    movies_count = self._sync_movies()
                    self._update_activity_record(
                        "movies_completed_at", movies_remote_completed or self._get_datetime_now()
                    )
                except ActivitySyncFailure as e:
                    any_failed = True
                    g.log(f"Failed to sync Simkl watched movies: {e}", "error")

            shows_remote_completed = remote_shows.get("completed")
            shows_remote_watching = remote_shows.get("watching")
            shows_stale = self.requires_update(shows_remote_completed, self.activities["tv_shows_completed_at"])
            watching_stale = self.requires_update(shows_remote_watching, self.activities["tv_shows_watching_at"])
            if shows_stale or watching_stale:
                try:
                    shows_count = self._sync_shows()
                    self._update_activity_record(
                        "tv_shows_completed_at", shows_remote_completed or self._get_datetime_now()
                    )
                    self._update_activity_record(
                        "tv_shows_watching_at", shows_remote_watching or self._get_datetime_now()
                    )
                except ActivitySyncFailure as e:
                    any_failed = True
                    g.log(f"Failed to sync Simkl watched shows: {e}", "error")

            # Anime cursors live in addon settings, not the activities table, for the same
            # reason movies_removed_at/tv_shows_removed_at do (see set_base_activities()) -
            # adding columns to the schema dict triggers a full destructive rebuild on every
            # existing install. Anime entries are routed into the existing movies/shows
            # tables by anime_type (see _sync_anime()), not a separate table.
            anime_remote_completed = remote_anime.get("completed")
            anime_completed_local = g.get_setting("simkl.anime_completed_at") or self.base_date
            anime_remote_watching = remote_anime.get("watching")
            anime_watching_local = g.get_setting("simkl.anime_watching_at") or self.base_date
            anime_stale = self.requires_update(anime_remote_completed, anime_completed_local)
            anime_watching_stale = self.requires_update(anime_remote_watching, anime_watching_local)
            if anime_stale or anime_watching_stale:
                try:
                    anime_movies_count, anime_shows_count = self._sync_anime()
                    movies_count += anime_movies_count
                    shows_count += anime_shows_count
                    g.set_setting("simkl.anime_completed_at", anime_remote_completed or self._get_datetime_now())
                    g.set_setting("simkl.anime_watching_at", anime_remote_watching or self._get_datetime_now())
                except ActivitySyncFailure as e:
                    any_failed = True
                    g.log(f"Failed to sync Simkl anime: {e}", "error")

            # date_from delta pulls (_sync_movies/_sync_shows/_sync_anime above) can never
            # surface a removal or a status move away from completed/watching - simkl.apib
            # is explicit that "date_from won't surface removals - you can only detect them
            # by diffing." Triggered on movies_stale/shows_stale/watching_stale/anime_stale
            # too, not just removed_from_list moving: a watching->dropped transition bumps
            # watching's own timestamp (already covered above), and re-deriving "what's
            # currently completed/watching" via the ids_only diff is what actually detects
            # that a show left the bucket Seren tracks, same mechanism either way. Anime
            # staleness triggers both reconciles (not just one) because _reconcile_removed_
            # movies/shows both union in the whole anime id set - see those methods.
            movies_removed_remote = remote_movies.get("removed_from_list")
            movies_removed_local = g.get_setting("simkl.movies_removed_at") or self.base_date
            anime_removed_remote = remote_anime.get("removed_from_list")
            anime_removed_local = g.get_setting("simkl.anime_removed_at") or self.base_date
            anime_removed_stale = self.requires_update(anime_removed_remote, anime_removed_local)
            movies_reconcile_ran = (
                movies_stale
                or anime_stale
                or anime_watching_stale
                or anime_removed_stale
                or self.requires_update(movies_removed_remote, movies_removed_local)
            )
            movies_reconcile_ok = False
            if movies_reconcile_ran:
                try:
                    self._reconcile_removed_movies()
                    g.set_setting("simkl.movies_removed_at", movies_removed_remote or self._get_datetime_now())
                    movies_reconcile_ok = True
                except ActivitySyncFailure as e:
                    any_failed = True
                    g.log(f"Failed to reconcile removed/dropped Simkl movies: {e}", "error")

            shows_removed_remote = remote_shows.get("removed_from_list")
            shows_removed_local = g.get_setting("simkl.tv_shows_removed_at") or self.base_date
            shows_reconcile_ran = (
                shows_stale
                or watching_stale
                or anime_stale
                or anime_watching_stale
                or anime_removed_stale
                or self.requires_update(shows_removed_remote, shows_removed_local)
            )
            shows_reconcile_ok = False
            if shows_reconcile_ran:
                try:
                    self._reconcile_removed_shows()
                    g.set_setting("simkl.tv_shows_removed_at", shows_removed_remote or self._get_datetime_now())
                    shows_reconcile_ok = True
                except ActivitySyncFailure as e:
                    any_failed = True
                    g.log(f"Failed to reconcile removed/dropped Simkl shows: {e}", "error")

            # Anime's removed_at cursor is only consumed by the two reconciles above (it
            # gates their trigger condition, not a fetch of its own) - only advance it once
            # both actually succeeded, tracked locally rather than via the broader
            # any_failed flag so an unrelated failure elsewhere this cycle (e.g. regular
            # movies sync) can't block this cursor from advancing when the reconciles it
            # actually gates both went fine. anime_removed_stale is OR'd into both *_ran
            # conditions above, so reaching this branch guarantees both *_ok flags were
            # genuinely evaluated (never left at their uninitialized False default).
            if anime_removed_stale and movies_reconcile_ok and shows_reconcile_ok:
                g.set_setting("simkl.anime_removed_at", anime_removed_remote or self._get_datetime_now())

            movies_playback_remote = remote_movies.get("playback") or self.base_date
            shows_playback_remote = remote_shows.get("playback") or self.base_date
            anime_playback_remote = remote_anime.get("playback") or self.base_date
            playback_remote = max(
                movies_playback_remote,
                shows_playback_remote,
                anime_playback_remote,
                key=simkl_sync._parse_simkl_datetime,
            )
            if self.requires_update(playback_remote, self.activities["playback_at"]):
                try:
                    playback_count = self._sync_playback()
                    self._update_activity_record("playback_at", playback_remote)
                except ActivitySyncFailure as e:
                    any_failed = True
                    g.log(f"Failed to sync Simkl playback: {e}", "error")

            # Only advance the top-level fast-exit cursor when every sub-sync that ran this
            # cycle actually succeeded - otherwise a failed domain's stale cursor (correctly
            # left unadvanced above, for retry) would still get skipped next cycle by the
            # early-exit at the top of this method, stranding it until an unrelated activity
            # happens to bump `all` again.
            if remote_all and not any_failed:
                self._update_activity_record("all_at", remote_all)

            if movies_count or shows_count or playback_count:
                g.notification_unless_playing(
                    g.ADDON_NAME,
                    g.get_language_string(31084).format(movies_count + shows_count, playback_count),
                )
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=widgetRefresh&playing=False")')

    def _sync_movies(self):
        """Pulls GET /sync/all-items/movies/completed. date_from is omitted only on the
        very first sync (simkl.apib's two-phase model: initial full pull, then
        activities-checked deltas) - every later call must pass it or risk the client_id
        suspension simkl.apib documents for un-gated /sync/all-items polling."""
        date_from = (
            None
            if self.activities["movies_completed_at"] == self.base_date
            else self.activities["movies_completed_at"]
        )
        try:
            params = {"date_from": date_from} if date_from else {}
            page = self.simkl_api.get_json_or_raise("sync/all-items/movies/completed", **params) or {}

            rows = []
            for entry in page.get("movies") or []:
                ids = (entry.get("movie") or {}).get("ids") or {}
                simkl_id = ids.get("simkl") or ids.get("simkl_id")
                if not simkl_id:
                    continue
                rows.append((simkl_id, ids.get("tmdb"), ids.get("imdb"), 1, entry.get("last_watched_at")))

            if rows:
                self.execute_sql(
                    "REPLACE INTO movies (simkl_id, tmdb_id, imdb_id, watched, last_watched_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    rows,
                )
            return len(rows)
        except ActivitySyncFailure:
            raise
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _sync_shows(self):
        """Pulls GET /sync/all-items/shows/{completed,watching}. Stores Simkl's own
        watched_episodes_count/total_episodes_count/next_to_watch summary per show -
        deliberately no per-episode mill. Two remote paths for real per-episode data
        were evaluated and rejected, not just the default response's omission:
        extended=full alone excludes seasons[].episodes[] for completed/dropped
        (simkl.apib:9582); include_all_episodes=yes extends coverage to those buckets
        (simkl.apib:9589, :3628) but may synthesize virtual episode rows for shows
        without real per-episode history, so the data itself isn't trustworthy. The
        on-demand POST /sync/watched?extended=episodes (simkl.apib:84, 4586-4645)
        returns real per-episode watched booleans, but simkl.apib:4594 documents
        calling it alongside the bulk /sync/all-items pull this method already does
        as a client_id-suspension pattern. Per-episode watched checkmarks are
        therefore not available from Simkl-sourced rows; this is a deliberate
        deferral, documented in Simkl_Implementation_Plan.md, not an oversight."""
        total = 0
        try:
            total += self._sync_shows_status(
                "completed",
                None
                if self.activities["tv_shows_completed_at"] == self.base_date
                else self.activities["tv_shows_completed_at"],
            )
            total += self._sync_shows_status(
                "watching",
                None
                if self.activities["tv_shows_watching_at"] == self.base_date
                else self.activities["tv_shows_watching_at"],
            )
        except ActivitySyncFailure:
            raise
        except Exception as e:
            raise ActivitySyncFailure(e) from e
        return total

    def _sync_shows_status(self, status, date_from):
        params = {"date_from": date_from} if date_from else {}
        page = self.simkl_api.get_json_or_raise(f"sync/all-items/shows/{status}", **params) or {}

        rows = []
        for entry in page.get("shows") or []:
            ids = (entry.get("show") or {}).get("ids") or {}
            simkl_id = ids.get("simkl") or ids.get("simkl_id")
            if not simkl_id:
                continue
            rows.append(
                (
                    simkl_id,
                    ids.get("tmdb"),
                    ids.get("tvdb"),
                    ids.get("imdb"),
                    entry.get("status"),
                    entry.get("watched_episodes_count") or 0,
                    entry.get("total_episodes_count") or 0,
                    entry.get("next_to_watch"),
                    entry.get("last_watched_at"),
                )
            )

        if rows:
            self.execute_sql(
                "REPLACE INTO shows (simkl_id, tmdb_id, tvdb_id, imdb_id, status, "
                "watched_episodes_count, total_episodes_count, next_to_watch, last_watched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def _sync_anime(self):
        """Pulls GET /sync/all-items/anime/{completed,watching}. Simkl's anime bucket is
        a single list mixing anime movies and anime TV-likes (anime_type: tv/special/ova/
        movie/music video/ona - simkl.apib), unlike movies/shows which are already split
        by Simkl into separate endpoints. Routed here into Seren's existing movies/shows
        tables by anime_type rather than a new table, since those are the only tables any
        consumer (get_recent_movies/shows, bridgeSync) actually reads - simkl_id is
        globally unique across Simkl's catalog, so an anime-sourced row coexists safely
        with movie/show-sourced rows in the same table.

        This deliberately reverses Simkl_Implementation_Plan.md's original "movies + TV
        shows only, anime explicitly out of scope" scope decision - that note was about
        AniDB-style episode numbering (still not handled here, matching the plan's
        original numbering concern), not about whether watched/completion status syncs at
        all. Live-confirmed 2026-07-18 against a real account that mainstream titles
        Simkl buckets as anime (not just numbering-divergent ones) were going completely
        unsynced, per explicit user instruction to fix it."""
        movies_total = 0
        shows_total = 0
        try:
            for status in ("completed", "watching"):
                date_from = g.get_setting(f"simkl.anime_{status}_at") or None
                if date_from == self.base_date:
                    date_from = None
                status_movies, status_shows = self._sync_anime_status(status, date_from)
                movies_total += status_movies
                shows_total += status_shows
        except ActivitySyncFailure:
            raise
        except Exception as e:
            raise ActivitySyncFailure(e) from e
        return movies_total, shows_total

    def _sync_anime_status(self, status, date_from):
        params = {"date_from": date_from} if date_from else {}
        page = self.simkl_api.get_json_or_raise(f"sync/all-items/anime/{status}", **params) or {}

        movie_rows = []
        show_rows = []
        for entry in page.get("anime") or []:
            ids = (entry.get("show") or {}).get("ids") or {}
            simkl_id = ids.get("simkl") or ids.get("simkl_id")
            if not simkl_id:
                continue
            if entry.get("anime_type") == "movie":
                movie_rows.append((simkl_id, ids.get("tmdb"), ids.get("imdb"), 1, entry.get("last_watched_at")))
            else:
                show_rows.append(
                    (
                        simkl_id,
                        ids.get("tmdb"),
                        ids.get("tvdb"),
                        ids.get("imdb"),
                        entry.get("status"),
                        entry.get("watched_episodes_count") or 0,
                        entry.get("total_episodes_count") or 0,
                        entry.get("next_to_watch"),
                        entry.get("last_watched_at"),
                    )
                )

        if movie_rows:
            self.execute_sql(
                "REPLACE INTO movies (simkl_id, tmdb_id, imdb_id, watched, last_watched_at) "
                "VALUES (?, ?, ?, ?, ?)",
                movie_rows,
            )
        if show_rows:
            self.execute_sql(
                "REPLACE INTO shows (simkl_id, tmdb_id, tvdb_id, imdb_id, status, "
                "watched_episodes_count, total_episodes_count, next_to_watch, last_watched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                show_rows,
            )
        return len(movie_rows), len(show_rows)

    def _reconcile_removed_movies(self):
        """Fired when Simkl's movies.removed_from_list timestamp moves, or when
        movies.completed does (a plain date_from delta can silently miss a movie
        leaving completed, same underlying gap - see sync_activities()). date_from
        can never surface removals (simkl.apib: "date_from won't surface removals -
        you can only detect them by diffing"), so this re-derives the full current
        completed-movies id set via extended=simkl_ids_only (cheapest possible
        payload - just ids.simkl per item) and deletes any locally-cached movie
        no longer in it.

        get_json() returns None on any request failure (exception, non-2xx,
        unparseable body) - but a 200 response missing the "movies" key
        entirely (some other unexpected shape) would slip past an is-None-only
        check and be misread as "zero movies", deleting every locally-cached
        row. The unlike-_sync_movies() distinction is what makes this
        dangerous specifically here: _sync_movies() can safely treat a
        confirmed-empty or malformed page as "zero movies" because it's
        additive-only (REPLACE, no DELETE), so nothing new this cycle is the
        only consequence. This method deletes on the same empty result, so it
        also requires the
        "movies" key to genuinely be present - true even for a legitimately
        empty list ({"movies": []}) - before treating the fetch as trustworthy
        enough to diff against for deletion.

        Also unions in the full current anime id set (completed + watching, both
        statuses, not filtered by anime_type) - anime-sourced movie rows (see
        _sync_anime()) live in this same table, and this diff is the only thing
        that would otherwise see them as unrecognized/stale and delete them every
        cycle. Not filtering by anime_type is deliberate: simkl_id is globally
        unique across Simkl's catalog and this table only ever contains real
        anime-movie rows to begin with, so folding in anime-show ids too is a
        harmless superset, not a correctness risk - it can only prevent a
        wrongful deletion, never cause one."""
        try:
            page = self.simkl_api.get_json("sync/all-items/movies/completed", extended="simkl_ids_only")
            if page is None or "movies" not in page:
                raise ActivitySyncFailure(
                    "empty or malformed response from Simkl "
                    "(sync/all-items/movies/completed?extended=simkl_ids_only)"
                )
            current_ids = {
                (entry.get("movie") or {}).get("ids", {}).get("simkl") for entry in (page.get("movies") or [])
            }
            for anime_status in ("completed", "watching"):
                anime_page = self.simkl_api.get_json(
                    f"sync/all-items/anime/{anime_status}", extended="simkl_ids_only"
                )
                if anime_page is None or "anime" not in anime_page:
                    raise ActivitySyncFailure(
                        f"empty or malformed response from Simkl "
                        f"(sync/all-items/anime/{anime_status}?extended=simkl_ids_only)"
                    )
                current_ids.update(
                    (entry.get("show") or {}).get("ids", {}).get("simkl")
                    for entry in (anime_page.get("anime") or [])
                )
            current_ids.discard(None)
            local_ids = {row["simkl_id"] for row in self.fetchall("SELECT simkl_id FROM movies")}
            stale_ids = local_ids - current_ids
            if stale_ids:
                self.execute_sql(
                    f"DELETE FROM movies WHERE simkl_id IN ({','.join('?' * len(stale_ids))})",
                    tuple(stale_ids),
                )
            return len(stale_ids)
        except ActivitySyncFailure:
            raise
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _reconcile_removed_shows(self):
        """Same mechanism as _reconcile_removed_movies, for shows - unioned across
        both statuses Seren tracks (completed + watching), since a show leaving
        either one (removed entirely, or moved to hold/dropped/plantowatch) should
        no longer be in Seren's local cache either. See _reconcile_removed_movies'
        docstring for why each page requires its expected key present, not just
        a non-None response, before being trusted for a deletion diff.

        Also unions in the full current anime id set, same as _reconcile_removed_
        movies and for the same reason (anime-sourced show-like rows, i.e. every
        anime_type other than "movie", live in this same table) - see that
        method's docstring for why not filtering by anime_type here is safe."""
        try:
            current_ids = set()
            for status in ("completed", "watching"):
                page = self.simkl_api.get_json(f"sync/all-items/shows/{status}", extended="simkl_ids_only")
                if page is None or "shows" not in page:
                    raise ActivitySyncFailure(
                        f"empty or malformed response from Simkl "
                        f"(sync/all-items/shows/{status}?extended=simkl_ids_only)"
                    )
                current_ids.update(
                    (entry.get("show") or {}).get("ids", {}).get("simkl") for entry in (page.get("shows") or [])
                )
                anime_page = self.simkl_api.get_json(f"sync/all-items/anime/{status}", extended="simkl_ids_only")
                if anime_page is None or "anime" not in anime_page:
                    raise ActivitySyncFailure(
                        f"empty or malformed response from Simkl "
                        f"(sync/all-items/anime/{status}?extended=simkl_ids_only)"
                    )
                current_ids.update(
                    (entry.get("show") or {}).get("ids", {}).get("simkl")
                    for entry in (anime_page.get("anime") or [])
                )
            current_ids.discard(None)
            local_ids = {row["simkl_id"] for row in self.fetchall("SELECT simkl_id FROM shows")}
            stale_ids = local_ids - current_ids
            if stale_ids:
                self.execute_sql(
                    f"DELETE FROM shows WHERE simkl_id IN ({','.join('?' * len(stale_ids))})",
                    tuple(stale_ids),
                )
            return len(stale_ids)
        except ActivitySyncFailure:
            raise
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _sync_playback(self):
        """Pulls GET /sync/playback (flat array, full replace). No date_from here even
        though the endpoint accepts one: filtering to a delta would only return sessions
        that changed since last sync, and the DELETE FROM bookmarks below would then
        wrongly drop still-valid, unchanged paused sessions. date_from is for
        /sync/all-items' incremental model, not this full-snapshot one - the outer
        sync_activities() cursor gate already prevents this from being polled on a
        timer, which is what simkl.apib actually warns against."""
        try:
            entries = self.simkl_api.get_json("sync/playback")
            if entries is None:
                raise ActivitySyncFailure("empty response from Simkl (sync/playback)")
            if isinstance(entries, dict):
                entries = entries.get("items") or []

            rows = []
            for entry in entries:
                progress = entry.get("progress")
                paused_at = entry.get("paused_at")
                media_type = entry.get("type")
                playback_id = entry.get("id")
                if progress is None or not paused_at:
                    continue

                if media_type == "movie":
                    ids = (entry.get("movie") or {}).get("ids") or {}
                    simkl_id = ids.get("simkl") or ids.get("simkl_id")
                    if not simkl_id:
                        continue
                    rows.append(
                        (simkl_id, None, None, "movie", ids.get("tmdb"), playback_id, str(progress), paused_at)
                    )
                elif media_type == "episode":
                    episode = entry.get("episode") or {}
                    ids = (entry.get("show") or {}).get("ids") or {}
                    simkl_id = ids.get("simkl") or ids.get("simkl_id")
                    season = episode.get("season")
                    number = episode.get("number")
                    if not simkl_id or season is None or number is None:
                        continue
                    rows.append(
                        (
                            simkl_id,
                            season,
                            number,
                            "episode",
                            ids.get("tmdb"),
                            playback_id,
                            str(progress),
                            paused_at,
                        )
                    )

            self.execute_sql("DELETE FROM bookmarks")
            if rows:
                self.execute_sql(
                    "INSERT INTO bookmarks (simkl_id, season, number, media_type, tmdb_id, playback_id, "
                    "percent_played, paused_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                    rows,
                )
            return len(rows)
        except ActivitySyncFailure:
            raise
        except Exception as e:
            raise ActivitySyncFailure(e) from e
