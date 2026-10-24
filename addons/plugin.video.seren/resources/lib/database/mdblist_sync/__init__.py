import collections
import datetime

import xbmcgui

from resources.lib.common import tools
from resources.lib.database import Database
from resources.lib.modules.globals import g

schema = {
    "movies": {
        "columns": collections.OrderedDict(
            [
                ("tmdb_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("imdb_id", ["TEXT", "NULL"]),
                ("watched", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("last_watched_at", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": [],
        "indices": [("idx_mdblist_movies_watched", ["watched"])],
        "default_seed": [],
    },
    "episodes": {
        "columns": collections.OrderedDict(
            [
                ("show_tmdb_id", ["INTEGER", "NOT NULL"]),
                ("season", ["INTEGER", "NOT NULL"]),
                ("number", ["INTEGER", "NOT NULL"]),
                ("watched", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("last_watched_at", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY(show_tmdb_id, season, number)"],
        "indices": [("idx_mdblist_episodes_show", ["show_tmdb_id"])],
        "default_seed": [],
    },
    "bulk_watched_shows": {
        # MDBList's sync/watched "shows" bucket: whole-show mark-watched actions taken on
        # MDBList's own site/app, which never produce per-episode "episodes" entries. See
        # activities.py's _sync_watched docstring for why this needs its own table.
        "columns": collections.OrderedDict(
            [
                ("show_tmdb_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("last_watched_at", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": [],
        "indices": [],
        "default_seed": [],
    },
    "bulk_watched_seasons": {
        # MDBList's sync/watched "seasons" bucket: whole-season mark-watched actions, same
        # gap as bulk_watched_shows above but scoped to one season instead of the whole show.
        "columns": collections.OrderedDict(
            [
                ("show_tmdb_id", ["INTEGER", "NOT NULL"]),
                ("season", ["INTEGER", "NOT NULL"]),
                ("last_watched_at", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY(show_tmdb_id, season)"],
        "indices": [("idx_mdblist_bulk_seasons_show", ["show_tmdb_id"])],
        "default_seed": [],
    },
    "bookmarks": {
        "columns": collections.OrderedDict(
            [
                ("tmdb_id", ["INTEGER", "NOT NULL"]),
                ("season", ["INTEGER", "NULL"]),
                ("number", ["INTEGER", "NULL"]),
                ("media_type", ["TEXT", "NOT NULL"]),
                ("percent_played", ["TEXT", "NOT NULL"]),
                ("resume_time", ["TEXT", "NULL"]),
                ("paused_at", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY(tmdb_id, season, number, media_type)"],
        "indices": [("idx_mdblist_bookmarks_paused", ["paused_at"])],
        "default_seed": [],
    },
    "activities": {
        "columns": collections.OrderedDict(
            [
                ("sync_id", ["INTEGER", "PRIMARY KEY"]),
                ("watched_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("episode_watched_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("playback_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("watchlisted_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("mdblist_username", ["TEXT", "NULL"]),
                ("last_activities_call", ["INTEGER", "NOT NULL", "DEFAULT 1"]),
            ]
        ),
        "table_constraints": ["UNIQUE(sync_id)"],
        "default_seed": [],
    },
}


# Session-level set of db_file paths already migrated for the list_items table
# below - mirrors trakt_sync's _WATCHLIST_FAVORITES_MIGRATED/_LIST_ITEMS_MIGRATED
# pattern, avoiding a repeat CREATE TABLE IF NOT EXISTS round trip on every
# MDBListSyncDatabase() construction.
_LIST_ITEMS_MIGRATED = set()


class MDBListSyncDatabase(Database):
    def __init__(self):
        super().__init__(g.MDBLIST_SYNC_DB_PATH, schema)
        self._migrate_list_items_tables()

        self.activities = {}
        self.base_date = "1970-01-01T00:00:00"
        self.refresh_activities()

        if self.activities is None:
            self.set_base_activities()

    def refresh_activities(self):
        self.activities = self.fetchone("SELECT * FROM activities WHERE sync_id=1")

    def set_base_activities(self):
        self.execute_sql(
            "REPLACE INTO activities(sync_id, mdblist_username) VALUES(1, ?)",
            (g.get_setting("mdblist.username"),),
        )
        self.activities = self.fetchone("SELECT * FROM activities WHERE sync_id=1")

    def re_build_database(self, silent=False):
        """Mirrors TraktSyncDatabase.re_build_database's shape (trakt_sync/__init__.py) -
        physical drop+recreate via the inherited rebuild_database(), then a full resync via
        force_sync(), reusing that method's already-correct set_base_activities()+
        clear_list_cache()+sync_activities() sequence instead of duplicating it."""
        if not silent:
            confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30179))
            if confirm == 0:
                return

        self.rebuild_database()
        # list_items lives outside the schema dict (see _migrate_list_items_tables'
        # docstring) so a fresh MDBListSyncDatabase() below won't recreate it unless this
        # process-lifetime migration guard is cleared first - see the identical fix/comment
        # in trakt_sync/__init__.py's re_build_database for the full failure mode.
        _LIST_ITEMS_MIGRATED.discard(self._db_file)

        from resources.lib.database.mdblist_sync import activities

        activities.MDBListSyncDatabase().force_sync()

    def _migrate_list_items_tables(self):
        """CREATE TABLE IF NOT EXISTS, deliberately not a `schema` dict entry - see
        trakt_sync's identical _migrate_list_items_tables docstring for why: any change
        to `schema` changes _integrity_check_db's md5 checksum, and a mismatch triggers
        rebuild_database(), which drops every table in this db file before recreating
        them empty. Keyed by tmdb_id (MDBList's own item identifier, matching
        _info_to_mdblist_list_object's payload shape and MDBListSyncDatabase's existing
        watched-status tables) rather than trakt_id."""
        if self._db_file in _LIST_ITEMS_MIGRATED:
            return
        self.execute_sql(
            "CREATE TABLE IF NOT EXISTS list_items ("
            "list_id INTEGER NOT NULL, tmdb_id INTEGER NOT NULL, mediatype TEXT NOT NULL, "
            "PRIMARY KEY(list_id, tmdb_id, mediatype))"
        )
        self.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_list_items_lookup ON list_items(tmdb_id, mediatype)"
        )
        _LIST_ITEMS_MIGRATED.add(self._db_file)

    def get_list_membership_count(self, tmdb_id, mediatype):
        """Returns how many synced lists this item is currently in. Mirrors
        TraktSyncDatabase.get_list_membership_count."""
        in_count = self.fetchone(
            "SELECT COUNT(*) as c FROM list_items WHERE tmdb_id=? AND mediatype=?",
            (tmdb_id, mediatype),
        )
        return in_count["c"]

    def add_list_membership(self, list_id, tmdb_id, mediatype):
        self.execute_sql(
            "INSERT OR IGNORE INTO list_items(list_id, tmdb_id, mediatype) VALUES(?,?,?)",
            (list_id, tmdb_id, mediatype),
        )

    def remove_list_membership(self, list_id, tmdb_id, mediatype):
        self.execute_sql(
            "DELETE FROM list_items WHERE list_id=? AND tmdb_id=? AND mediatype=?",
            (list_id, tmdb_id, mediatype),
        )

    @staticmethod
    def _get_datetime_now():
        return g.datetime_to_string(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))

    @staticmethod
    def requires_update(new_date, old_date):
        return tools.parse_datetime(new_date, False) > tools.parse_datetime(old_date, False)

    def write_watched_locally(self, mediatype, info):
        """Writes a movie/episode watched mark directly to the local sync tables and
        clears any matching stale bookmark. Shared by the scrobbler (player.py) and the
        context-menu mark-watched action, so a mark made via either path is reflected
        in Seren's own local view immediately instead of waiting for the next periodic
        activities sync (both movies and episodes are otherwise fully repopulated from
        MDBList's remote GET /sync/watched by _sync_watched() - live-confirmed
        2026-07-18 that this endpoint does return movies)."""
        try:
            now = self._get_datetime_now()
            if mediatype == "movie":
                tmdb_id = info.get("tmdb_id")
                if not tmdb_id:
                    return
                self.execute_sql(
                    "REPLACE INTO movies (tmdb_id, imdb_id, watched, last_watched_at) VALUES (?, ?, 1, ?)",
                    (tmdb_id, info.get("imdb_id"), now),
                )
                self.execute_sql("DELETE FROM bookmarks WHERE tmdb_id=? AND media_type='movie'", (tmdb_id,))
            elif mediatype == "episode":
                tmdb_show_id = info.get("tmdb_show_id")
                season = info.get("season")
                episode = info.get("episode")
                if not tmdb_show_id or season is None or episode is None:
                    return
                self.execute_sql(
                    "REPLACE INTO episodes (show_tmdb_id, season, number, watched, last_watched_at) VALUES (?, ?, ?, 1, ?)",
                    (tmdb_show_id, season, episode, now),
                )
                self.execute_sql(
                    "DELETE FROM bookmarks WHERE tmdb_id=? AND season=? AND number=? AND media_type='episode'",
                    (tmdb_show_id, season, episode),
                )
        except Exception:
            g.log_stacktrace()

    def write_unwatched_locally(self, mediatype, info):
        """Mirrors write_watched_locally for the mark-unwatched action - without this,
        the local watched flag set by write_watched_locally never clears, so a
        watched-state toggle gated on this table would stay stuck on "watched" after
        the user marks an item unwatched. Bookmarks are intentionally left alone here
        (unlike the watched path) - unmarking watched doesn't imply the resume point
        should be discarded."""
        try:
            if mediatype == "movie":
                tmdb_id = info.get("tmdb_id")
                if not tmdb_id:
                    return
                self.execute_sql(
                    "REPLACE INTO movies (tmdb_id, imdb_id, watched, last_watched_at) VALUES (?, ?, 0, NULL)",
                    (tmdb_id, info.get("imdb_id")),
                )
            elif mediatype == "episode":
                tmdb_show_id = info.get("tmdb_show_id")
                season = info.get("season")
                episode = info.get("episode")
                if not tmdb_show_id or season is None or episode is None:
                    return
                self.execute_sql(
                    "REPLACE INTO episodes (show_tmdb_id, season, number, watched, last_watched_at) VALUES (?, ?, ?, 0, NULL)",
                    (tmdb_show_id, season, episode),
                )
        except Exception:
            g.log_stacktrace()

    def is_movie_watched(self, tmdb_id):
        """Single-item watched lookup for the context-menu toggle - deliberately not
        get_all_watched_movie_tmdb_ids(), which pulls the whole table to test one row."""
        if not tmdb_id:
            return False
        row = self.fetchone("SELECT watched FROM movies WHERE tmdb_id=?", (tmdb_id,))
        return bool(row and row["watched"])

    def is_episode_watched(self, show_tmdb_id, season, number):
        if not show_tmdb_id or season is None or number is None:
            return False
        row = self.fetchone(
            "SELECT watched FROM episodes WHERE show_tmdb_id=? AND season=? AND number=?",
            (show_tmdb_id, season, number),
        )
        return bool(row and row["watched"])

    def get_watched_episode_count(self, show_tmdb_id, season=None):
        """Local watched-episode count for the season/tvshow watched-toggle gate in
        trakt_context_menu.py. season=None aggregates the whole show, excluding
        specials (season>0) to match Trakt's shows.episode_count convention - the
        denominator borrowed for the tvshow cell, since MDBList has no local
        show-level total of its own. A specific season needs no such filter: both
        sides are already scoped to the same season number by the caller."""
        if not show_tmdb_id:
            return 0
        if season is not None:
            row = self.fetchone(
                "SELECT COUNT(*) AS count FROM episodes WHERE show_tmdb_id=? AND season=? AND watched=1",
                (show_tmdb_id, season),
            )
        else:
            row = self.fetchone(
                "SELECT COUNT(*) AS count FROM episodes WHERE show_tmdb_id=? AND season>0 AND watched=1",
                (show_tmdb_id,),
            )
        return row["count"] if row else 0

    def get_bookmark(self, tmdb_id, media_type, season=None, number=None):
        """Local playback-bookmark lookup for the context-menu Clear Progress gate in
        trakt_context_menu.py - mirrors TraktSyncDatabase.get_bookmark()'s role for Trakt's
        own _handle_progress_option. Reads the bookmarks table populated by the periodic
        activity sync (mdblist_sync/activities.py), not a live API call."""
        if not tmdb_id:
            return None
        if media_type == "movie":
            return self.fetchone("SELECT * FROM bookmarks WHERE tmdb_id=? AND media_type='movie'", (tmdb_id,))
        if season is None or number is None:
            return None
        return self.fetchone(
            "SELECT * FROM bookmarks WHERE tmdb_id=? AND season=? AND number=? AND media_type='episode'",
            (tmdb_id, season, number),
        )

    def get_recent_movies(self, limit, offset=0, force_all=False):
        """Locally-synced watched movies, newest first. Populated both by
        write_watched_locally() (scrobbler/context-menu, immediate) and by
        _sync_watched()'s periodic remote reconciliation (MDBList's GET
        /sync/watched - live-confirmed 2026-07-18 to return movies)."""
        query = """
            SELECT tmdb_id, last_watched_at
            FROM movies
            WHERE watched = 1
            ORDER BY last_watched_at DESC
            """
        if not force_all:
            query += f" LIMIT {limit} OFFSET {offset}"
        return self.fetchall(query)

    def get_recent_shows(self, limit, offset=0, force_all=False):
        """Locally-synced watched episodes rolled up to show level (latest episode's
        last_watched_at per show), newest first."""
        query = """
            SELECT show_tmdb_id AS tmdb_id, MAX(last_watched_at) AS last_watched_at
            FROM episodes
            WHERE watched = 1
            GROUP BY show_tmdb_id
            ORDER BY last_watched_at DESC
            """
        if not force_all:
            query += f" LIMIT {limit} OFFSET {offset}"
        return self.fetchall(query)

    def get_all_watched_movie_tmdb_ids(self):
        """bridgeSync's read-side for the Watched/movie domain. Reflects both
        locally-authored writes (write_watched_locally, immediate) and MDBList's
        own remote state (_sync_watched()'s periodic reconciliation - live-
        confirmed 2026-07-18 that GET /sync/watched does return movies), so
        MDBList is now a genuine out-of-band source for this media_type too,
        not just a push target."""
        return self.fetchall("SELECT tmdb_id FROM movies WHERE watched = 1")

    def get_all_watched_episode_tmdb_keys(self):
        """bridgeSync's read-side for the Watched/episode domain. Unlike movies,
        this table IS kept in sync with MDBList's real remote state on every
        activities cycle (see activities.py's _sync_watched), so it's safe to
        treat as a genuine out-of-band source, not just a target."""
        return self.fetchall("SELECT show_tmdb_id, season, number FROM episodes WHERE watched = 1")

    def get_bulk_watched_shows(self):
        """Whole-show MDBList mark-watched actions, keyed by show tmdb_id -> the mark's own
        last_watched_at. Populated by activities.py's _sync_watched from sync/watched's
        "shows" bucket. Consumed by mdblistMenus.Menus.next_up to credit aired episodes
        MDBList has no individual "episodes" entry for - see that method for how the
        timestamp is used (air-date gated, not an unconditional whole-show credit)."""
        rows = self.fetchall("SELECT show_tmdb_id, last_watched_at FROM bulk_watched_shows")
        return {row["show_tmdb_id"]: row["last_watched_at"] for row in rows}

    def get_bulk_watched_seasons(self):
        """Whole-season MDBList mark-watched actions, keyed by show tmdb_id -> the set of
        bulk-marked season numbers. Same population/consumption path as
        get_bulk_watched_shows, but a season mark is an unambiguous bounded claim (every
        episode in season N), so next_up() expands it unconditionally, unlike the show-level
        table's air-date gating."""
        rows = self.fetchall("SELECT show_tmdb_id, season FROM bulk_watched_seasons")
        result = {}
        for row in rows:
            result.setdefault(row["show_tmdb_id"], set()).add(row["season"])
        return result
