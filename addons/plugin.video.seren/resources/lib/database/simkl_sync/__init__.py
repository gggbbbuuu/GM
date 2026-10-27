import collections
import datetime

import xbmcgui

from resources.lib.database import Database
from resources.lib.modules.globals import g

schema = {
    "movies": {
        "columns": collections.OrderedDict(
            [
                ("simkl_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("imdb_id", ["TEXT", "NULL"]),
                ("watched", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("last_watched_at", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": [],
        "indices": [
            ("idx_simkl_movies_tmdb", ["tmdb_id"]),
            ("idx_simkl_movies_watched", ["watched"]),
        ],
        "default_seed": [],
    },
    "shows": {
        "columns": collections.OrderedDict(
            [
                ("simkl_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("tvdb_id", ["TEXT", "NULL"]),
                ("imdb_id", ["TEXT", "NULL"]),
                ("status", ["TEXT", "NULL"]),
                ("watched_episodes_count", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("total_episodes_count", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("next_to_watch", ["TEXT", "NULL"]),
                ("last_watched_at", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": [],
        "indices": [
            ("idx_simkl_shows_tmdb", ["tmdb_id"]),
            ("idx_simkl_shows_last_watched", ["last_watched_at"]),
        ],
        "default_seed": [],
    },
    "bookmarks": {
        "columns": collections.OrderedDict(
            [
                ("simkl_id", ["INTEGER", "NOT NULL"]),
                ("season", ["INTEGER", "NULL"]),
                ("number", ["INTEGER", "NULL"]),
                ("media_type", ["TEXT", "NOT NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("playback_id", ["INTEGER", "NULL"]),
                ("percent_played", ["TEXT", "NOT NULL"]),
                ("paused_at", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY(simkl_id, season, number, media_type)"],
        "indices": [
            ("idx_simkl_bookmarks_paused", ["paused_at"]),
            ("idx_simkl_bookmarks_tmdb", ["tmdb_id"]),
        ],
        "default_seed": [],
    },
    "activities": {
        "columns": collections.OrderedDict(
            [
                ("sync_id", ["INTEGER", "PRIMARY KEY"]),
                ("all_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00+00:00'"]),
                ("movies_completed_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00+00:00'"]),
                ("tv_shows_completed_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00+00:00'"]),
                ("tv_shows_watching_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00+00:00'"]),
                ("playback_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00+00:00'"]),
                ("simkl_username", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(sync_id)"],
        "default_seed": [],
    },
}


def _parse_simkl_datetime(string_date):
    """Simkl's cursor/item timestamps come back as either Z-suffixed or numeric-offset
    ISO8601 (both forms appear across simkl.apib) - normalized to tz-aware here so every
    comparison this module makes is apples-to-apples. Deliberately not
    tools.parse_datetime(), which rstrip("Z")'s the offset away entirely and returns a
    naive datetime - fine for Trakt/MDBList's bare timestamps, but comparing that against
    an aware datetime raises TypeError."""
    if not string_date:
        return None
    return datetime.datetime.fromisoformat(string_date.replace("Z", "+00:00"))


class SimklSyncDatabase(Database):
    def __init__(self):
        super().__init__(g.SIMKL_SYNC_DB_PATH, schema)

        self.activities = {}
        self.base_date = "1970-01-01T00:00:00+00:00"
        self.refresh_activities()

        if self.activities is None:
            self.set_base_activities()

    def refresh_activities(self):
        self.activities = self.fetchone("SELECT * FROM activities WHERE sync_id=1")

    def set_base_activities(self):
        self.execute_sql(
            "REPLACE INTO activities(sync_id, simkl_username) VALUES(1, ?)",
            (g.get_setting("simkl.username"),),
        )
        self.activities = self.fetchone("SELECT * FROM activities WHERE sync_id=1")
        # Removal-reconciliation cursors live in addon settings, not this table (see
        # _reconcile_removed_movies/_reconcile_removed_shows in activities.py) - adding
        # columns here would change this schema dict's checksum and trigger
        # Database._integrity_check_db's rebuild_database() on every existing install,
        # which wipes movies/shows/bookmarks for everyone, not just migrates activities.
        g.set_setting("simkl.movies_removed_at", self.base_date)
        g.set_setting("simkl.tv_shows_removed_at", self.base_date)
        # Anime has no dedicated activities-table columns at all (unlike movies/shows,
        # which get completed_at/watching_at columns plus a settings-based removed_at) -
        # all three of its cursors live in settings for the same schema-checksum reason.
        g.set_setting("simkl.anime_completed_at", self.base_date)
        g.set_setting("simkl.anime_watching_at", self.base_date)
        g.set_setting("simkl.anime_removed_at", self.base_date)

    def re_build_database(self, silent=False):
        """Mirrors TraktSyncDatabase.re_build_database's shape (trakt_sync/__init__.py) -
        physical drop+recreate via the inherited rebuild_database(), then a full resync via
        force_sync(). No process-lifetime migration guard to discard here (unlike Trakt/
        MDBList's list_items) - SimklSyncDatabase has no tables/columns added outside the
        schema dict, so rebuild_database()'s recreate-from-schema step is already complete
        on its own; set_base_activities() (called inside force_sync()) also resets the
        removal-reconciliation cursors it always writes to settings."""
        if not silent:
            confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30179))
            if confirm == 0:
                return

        self.rebuild_database()

        from resources.lib.database.simkl_sync import activities

        activities.SimklSyncDatabase().force_sync()

    def flush_activities(self):
        """Wipes local watch-state and resets sync cursors to base_date - called on a
        Simkl account switch (mirrors Trakt's flush_activities/clear_user_information,
        collapsed into one method since Simkl's tables hold only watch-state, not a
        browsable catalog cache like Trakt's - there's nothing worth preserving across
        a user switch)."""
        from resources.lib.database.trakt_sync import clear_list_cache

        self.execute_sql("DELETE FROM movies")
        self.execute_sql("DELETE FROM shows")
        self.execute_sql("DELETE FROM bookmarks")
        self.execute_sql("DELETE FROM activities")
        self.set_base_activities()
        clear_list_cache()

    def set_simkl_user(self, simkl_username):
        g.log(f"Setting Simkl Username: {simkl_username}")
        self.execute_sql("UPDATE activities SET simkl_username=?", (simkl_username,))

    @staticmethod
    def _get_datetime_now():
        # Kept tz-aware (unlike g.datetime_to_string()'s naive output) so a fallback
        # stamp here never collides with a _parse_simkl_datetime() comparison elsewhere.
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    @staticmethod
    def requires_update(new_date, old_date):
        new_dt = _parse_simkl_datetime(new_date)
        old_dt = _parse_simkl_datetime(old_date)
        if new_dt is None:
            return False
        if old_dt is None:
            return True
        return new_dt > old_dt

    def get_recent_movies(self, limit, offset=0, force_all=False):
        """Locally-synced watched movies, newest first. tmdb_id IS NOT NULL: unlike
        MDBList's tmdb-keyed tables, Simkl rows aren't guaranteed a tmdb_id (Phase 3
        confirmed it's nullable and sometimes absent) - excluded here rather than
        reaching Menus._resolve() and wasting a search/tmdb/None call."""
        query = """
            SELECT simkl_id, tmdb_id, last_watched_at
            FROM movies
            WHERE watched = 1 AND tmdb_id IS NOT NULL
            ORDER BY last_watched_at DESC
            """
        if not force_all:
            query += f" LIMIT {limit} OFFSET {offset}"
        return self.fetchall(query)

    def get_recent_shows(self, limit, offset=0, force_all=False):
        """Locally-synced shows with watched progress, newest first - ordered by
        Simkl's own per-show last_watched_at aggregate (no per-episode rows to MAX()
        over; see Simkl_Implementation_Plan.md Phase 3 notes on aggregate-only
        tracking). tmdb_id IS NOT NULL: see get_recent_movies."""
        query = """
            SELECT simkl_id, tmdb_id, last_watched_at
            FROM shows
            WHERE watched_episodes_count > 0 AND tmdb_id IS NOT NULL
            ORDER BY last_watched_at DESC
            """
        if not force_all:
            query += f" LIMIT {limit} OFFSET {offset}"
        return self.fetchall(query)

    def get_next_to_watch_shows(self):
        """Actively-watching shows with Simkl's own next-episode pointer, most recently
        watched first. next_to_watch is synced by _sync_shows_status/_sync_anime_status
        (as 'S01E04', or a bare 'E2' for some anime entries) and was never read before
        the Simkl Next Up menu. watched_episodes_count > 0 keeps shows that were only
        added to the list out, like Trakt's and MDBList's Next Up; tmdb_id IS NOT NULL:
        see get_recent_movies. Unbounded on purpose - the menu caps after discarding
        values it cannot place."""
        return self.fetchall(
            """
            SELECT simkl_id, tmdb_id, next_to_watch, last_watched_at
            FROM shows
            WHERE status = 'watching' AND watched_episodes_count > 0
              AND next_to_watch IS NOT NULL AND tmdb_id IS NOT NULL
            ORDER BY last_watched_at DESC
            """
        )

    def get_bookmarks(self, media_type):
        """Locally-synced paused/in-progress sessions for Phase 4's In Progress menus.
        Reads Phase 3's bookmarks table directly (kept current via _sync_playback's
        full-snapshot replace on every sync_activities() cycle) rather than a live API
        call - unlike MDBList's _live_playback_rows(), which fetches live because its
        own local cache only updates on scrobble events and can go stale between syncs.
        Simkl has no such gap here, so the already-synced local table is authoritative.
        tmdb_id IS NOT NULL: see get_recent_movies."""
        query = """
            SELECT tmdb_id, season, number, playback_id, paused_at
            FROM bookmarks
            WHERE media_type = ? AND tmdb_id IS NOT NULL
            ORDER BY paused_at DESC
            """
        return self.fetchall(query, (media_type,))

    def remove_bookmark(self, tmdb_id, media_type, season=None, number=None):
        """Deletes a local bookmark row by tmdb_id rather than the table's own
        simkl_id-based PK - context-menu callers only have a tmdb_id (items reach the
        context menu as Trakt objects). Not strictly required for correctness - the
        next sync_activities() cycle's _sync_playback() full-snapshot replace would
        eventually reconcile this anyway - but deleting immediately avoids a
        just-cleared item lingering in the In Progress menu until the next sync."""
        if media_type == "movie":
            self.execute_sql("DELETE FROM bookmarks WHERE tmdb_id=? AND media_type='movie'", (tmdb_id,))
        else:
            self.execute_sql(
                "DELETE FROM bookmarks WHERE tmdb_id=? AND season=? AND number=? AND media_type='episode'",
                (tmdb_id, season, number),
            )

    def is_movie_watched(self, tmdb_id):
        """Single-item watched lookup for the context-menu toggle."""
        if not tmdb_id:
            return False
        row = self.fetchone("SELECT watched FROM movies WHERE tmdb_id=?", (tmdb_id,))
        return bool(row and row["watched"])

    def is_show_fully_watched(self, tmdb_id):
        """last_watched_at alone can't gate this - activities.py populates it from both
        the completed AND watching status buckets, so a show with 3 of 40 episodes
        watched already has a non-null last_watched_at. Compare against
        total_episodes_count instead (mirrors Trakt's own unwatched_episodes > 0
        polarity in _handle_watched_options) so a partly-watched show still offers
        "Mark Watched" rather than hiding it."""
        if not tmdb_id:
            return False
        row = self.fetchone(
            "SELECT watched_episodes_count, total_episodes_count FROM shows WHERE tmdb_id=?", (tmdb_id,)
        )
        if not row:
            return False
        total = row["total_episodes_count"] or 0
        return bool(total) and row["watched_episodes_count"] >= total

    def is_show_in_library(self, tmdb_id):
        """True when the show has a synced row (Simkl completed/watching, see activities._sync_shows_status).
        Gate for the context-menu Rate entry: rating a show Simkl does not have yet adds it to the library."""
        if not tmdb_id:
            return False
        return bool(self.fetchone("SELECT 1 FROM shows WHERE tmdb_id=?", (tmdb_id,)))

    def mark_movie_watched_locally(self, tmdb_id):
        """Write-through so the toggle flips immediately instead of waiting on the next
        periodic activities sync. UPDATE-only, keyed by the tmdb_id index rather than
        the table's own simkl_id PK - mirrors remove_bookmark's rationale above:
        context-menu callers only have a tmdb_id. No-ops if the row doesn't exist yet
        (item never seen by a periodic sync) - the next sync populates it normally."""
        if not tmdb_id:
            return
        self.execute_sql(
            "UPDATE movies SET watched=1, last_watched_at=? WHERE tmdb_id=?",
            (self._get_datetime_now(), tmdb_id),
        )

    def mark_movie_unwatched_locally(self, tmdb_id):
        if not tmdb_id:
            return
        self.execute_sql("UPDATE movies SET watched=0, last_watched_at=NULL WHERE tmdb_id=?", (tmdb_id,))

    def mark_show_watched_locally(self, tmdb_id):
        """Sets watched_episodes_count to the row's own total_episodes_count (from the
        last periodic sync) rather than a sentinel - Seren already stores a real total,
        unlike TMDb Helper's cache schema which fakes one. No-op when total is unknown
        (0) - can't claim "fully watched" without a real denominator, and the next sync
        fills it in."""
        if not tmdb_id:
            return
        self.execute_sql(
            "UPDATE shows SET watched_episodes_count=total_episodes_count, last_watched_at=? "
            "WHERE tmdb_id=? AND total_episodes_count > 0",
            (self._get_datetime_now(), tmdb_id),
        )

    def mark_show_unwatched_locally(self, tmdb_id):
        if not tmdb_id:
            return
        self.execute_sql(
            "UPDATE shows SET watched_episodes_count=0, last_watched_at=NULL WHERE tmdb_id=?", (tmdb_id,)
        )

    def upsert_movie_watched_locally(self, simkl_id, tmdb_id, imdb_id):
        """Write-through for the scrobbler (player.py), which - unlike the context-menu
        toggle's mark_movie_watched_locally - may be marking an item with no existing
        local row (first-ever watch, never seen by a periodic sync). REPLACE is safe
        here because movies' entire column set (simkl_id, tmdb_id, imdb_id, watched,
        last_watched_at) is known at scrobble time, unlike shows below."""
        if not simkl_id:
            return
        self.execute_sql(
            "REPLACE INTO movies (simkl_id, tmdb_id, imdb_id, watched, last_watched_at) VALUES (?, ?, ?, 1, ?)",
            (simkl_id, tmdb_id, imdb_id, self._get_datetime_now()),
        )

    def upsert_show_episode_watched_locally(self, tmdb_id, simkl_id, imdb_id=None, tvdb_id=None):
        """Write-through for the scrobbler when a single episode finishes. Unlike
        movies, REPLACE is unsafe here - shows also carries status/next_to_watch/
        total_episodes_count columns a REPLACE with only scrobble-known fields would
        silently reset on an existing row. UPDATE preserves them and clamps the
        increment to total_episodes_count so a real denominator can't be exceeded.
        INSERT (row not seen by any periodic sync yet) leaves total_episodes_count at
        the schema default of 0 - is_show_fully_watched() correctly stays False until
        a sync learns the real denominator; that's the honest state given what a
        single scrobble event can know, not a gap. Requires simkl_id on the insert
        branch only (the table's NOT NULL PK) - callers without one should skip
        calling this rather than guess."""
        if not tmdb_id:
            return
        now = self._get_datetime_now()
        if self.fetchone("SELECT tmdb_id FROM shows WHERE tmdb_id=?", (tmdb_id,)):
            self.execute_sql(
                "UPDATE shows SET watched_episodes_count = MIN(watched_episodes_count + 1, "
                "CASE WHEN total_episodes_count > 0 THEN total_episodes_count ELSE watched_episodes_count + 1 END), "
                "last_watched_at=? WHERE tmdb_id=?",
                (now, tmdb_id),
            )
        elif simkl_id:
            self.execute_sql(
                "INSERT INTO shows (simkl_id, tmdb_id, tvdb_id, imdb_id, watched_episodes_count, "
                "total_episodes_count, last_watched_at) VALUES (?, ?, ?, ?, 1, 0, ?)",
                (simkl_id, tmdb_id, tvdb_id, imdb_id, now),
            )
