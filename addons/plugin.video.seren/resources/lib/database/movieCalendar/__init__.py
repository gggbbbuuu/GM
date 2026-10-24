"""Movie Calendar fetch-bookkeeping database.

Tracks which (movie, month) pairs have already been fetched from Trakt's global
"everything releasing" calendar, so re-paging to an already-fetched month is a
local read instead of a live API call. Deliberately NOT a movie content cache -
the actual title/art/rating/args come from the shared trakt_sync movies table at
render time (get_movie_list(), same call movie_calendar_data.py's Trakt-calendar
path already uses), because playback (tools.get_item_information()) hard-requires
a movie to exist there by trakt_id - there is no fallback path for data held only
outside that table. Keeping this table to bookkeeping only means cleanup() below
can freely delete old months without ever touching data other features (My
Movies, sync, tracking) depend on. Mirrors resources/lib/database/tvSchedule's
identical design for TV Schedule's own global layer.

The Simkl/MDBList watchlist-union layer is deliberately NEVER cached here - it's
re-resolved live on every month view, matching tv_schedule_data.py's own
_get_watchlist_layer() precedent: the union is already capped at _UNION_CAP=25
live-resolve calls, cheap enough to always be fresh, and caching it would need
to persist capped_ids/simkl_id_by_tmdb alongside the rows to safely reproduce
get_movie_calendar_month()'s post-hydration date-filter and rating-override
logic - complexity a bookkeeping-only table is specifically designed to avoid.

release_date persists the exact date bookkept for a movie at its original live
fetch - the row still carries no title/art/rating, but this one field must
survive a cache hit unchanged. Without it, a cache-hit re-render has to
re-derive the date from the shared trakt_sync movies table's info.aired, which
metadataHandler.py's _apply_best_fit_release() can independently overwrite
later (its own per-country release-type selection, unrelated to this table) -
confirmed live: a movie bookkept and shown under its 2026-08-07 limited-release
date re-rendered on a later cache hit as 2026-08-21 (its eventual wide-theatrical
date) once the shared column had been overwritten in between. Persisting and
preferring the fetch-time date on every cache hit keeps this table's bookkeeping
decision and its own display permanently consistent, regardless of what the
shared column becomes afterward.

Schema: trakt_movie_id INTEGER, month_key TEXT (YYYY-MM), release_date TEXT
Primary key: trakt_movie_id - one row per movie, whichever month it was first
fetched under. Adding release_date to this dict is picked up automatically by
Database._integrity_check_db()'s checksum compare on next launch - table is
bookkeeping-only, so the resulting rebuild just costs one re-fetch per
still-open month (see above).
"""

import collections

from resources.lib.database import Database
from resources.lib.modules.globals import g

schema = {
    "calendar_movies": {
        "columns": collections.OrderedDict(
            [
                ("trakt_movie_id", ["INTEGER", "NOT NULL"]),
                ("month_key", ["TEXT", "NOT NULL"]),
                ("release_date", ["TEXT"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (trakt_movie_id)"],
        "indices": [
            ("idx_calendar_movies_month_key", ["month_key"]),
        ],
        "default_seed": [],
    }
}


class MovieCalendarDatabase(Database):
    """Persistent fetch-bookkeeping for the Movie Calendar's Trakt-sourced layer.

    Usage from movie_calendar_data.py:
        db = MovieCalendarDatabase()
        rows = db.get_month(month_key)          # None if never fetched, else list of rows
        db.mark_month_fetched(month_key, [(trakt_movie_id, release_date), ...])
        db.cleanup(cutoff_month_key)              # evict months older than the retention window
        db.clear_all()                            # region/language filter changed - drop all bookkeeping
    """

    def __init__(self):
        super().__init__(g.MOVIE_CALENDAR_DB_PATH, schema)

    def get_month(self, month_key):
        """Returns [{"trakt_movie_id":.., "release_date":..}, ...] if this month
        has already been fetched, or None on a cache miss (never fetched)."""
        rows = self.fetchall(
            "SELECT trakt_movie_id, release_date FROM calendar_movies WHERE month_key = ?",
            (month_key,),
        )
        if not rows:
            # A previously-fetched-but-genuinely-empty month (no movies releasing)
            # is indistinguishable from never-fetched without a second signal - the
            # caller only ever asks for months it's about to fetch-if-missing, and
            # an empty result there just means one harmless re-fetch, not a bug.
            return None
        return rows

    def mark_month_fetched(self, month_key, trakt_movie_ids_with_dates):
        """trakt_movie_ids_with_dates: [(trakt_movie_id, release_date), ...] -
        release_date is the date this movie was actually bookkept under (see
        module docstring), not re-derived later."""
        if not trakt_movie_ids_with_dates:
            return
        self.execute_sql(
            "INSERT OR REPLACE INTO calendar_movies (trakt_movie_id, month_key, release_date) VALUES (?, ?, ?)",
            [(mid, month_key, released) for mid, released in trakt_movie_ids_with_dates],
        )

    def cleanup(self, cutoff_month_key):
        """Evict bookkeeping for months older than cutoff_month_key (exclusive
        of the cutoff itself - the caller passes the oldest month still worth
        keeping fresh)."""
        try:
            self.execute_sql(
                "DELETE FROM calendar_movies WHERE month_key < ?", (cutoff_month_key,)
            )
        except Exception as e:
            g.log(f"MovieCalendarDatabase.cleanup error: {e}", "warning")

    def clear_all(self):
        """Drop all bookkeeping - used when the region/language filter changes,
        since a cached month's movie set was fetched under the old filter."""
        try:
            self.execute_sql("DELETE FROM calendar_movies")
            g.log("MovieCalendarDatabase: Cleared all entries", "info")
        except Exception as e:
            g.log(f"MovieCalendarDatabase.clear_all error: {e}", "warning")

    def get_stats(self):
        try:
            # row_factory returns every row as a {column_name: value} dict (see
            # database/__init__.py SQLiteConnection._set_connection_settings) -
            # explicit AS aliases so lookup is by name, not a bare integer index.
            total = self.fetchone("SELECT COUNT(*) AS total FROM calendar_movies")
            months = self.fetchone("SELECT COUNT(DISTINCT month_key) AS months FROM calendar_movies")
            return {"total": total["total"] if total else 0, "months": months["months"] if months else 0}
        except Exception:
            return {"total": 0, "months": 0}
