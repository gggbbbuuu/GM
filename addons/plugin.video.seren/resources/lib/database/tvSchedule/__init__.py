"""TV Schedule fetch-bookkeeping database.

Tracks which (episode, week) pairs have already been fetched from Trakt's global
"everything airing" calendar, so re-paging to an already-fetched week is a local
read instead of a live API call. Deliberately NOT an episode content cache - the
actual title/art/rating/args come from the shared trakt_sync shows/episodes
tables at render time (get_mixed_episode_list(), same call calendar_data.py's
Trakt-calendar path already uses), because playback (tools.get_item_information())
hard-requires an episode to exist there by trakt_id - there is no fallback path
for data held only outside those tables. Keeping this table to bookkeeping only
means cleanup() below can freely delete old weeks without ever touching data
other features (My Shows, sync, tracking) depend on.

Schema: trakt_episode_id INTEGER, trakt_show_id TEXT, week_start TEXT
Primary key: trakt_episode_id - one row per episode, whichever week it was
first fetched under.
"""

import collections

from resources.lib.database import Database
from resources.lib.modules.globals import g

schema = {
    "schedule_episodes": {
        "columns": collections.OrderedDict(
            [
                ("trakt_episode_id", ["INTEGER", "NOT NULL"]),
                ("trakt_show_id", ["INTEGER", "NOT NULL"]),
                ("week_start", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (trakt_episode_id)"],
        "indices": [
            ("idx_schedule_episodes_week_start", ["week_start"]),
        ],
        "default_seed": [],
    }
}


class TvScheduleDatabase(Database):
    """Persistent fetch-bookkeeping for the TV Schedule's global calendar layer.

    Usage from tv_schedule_data.py:
        db = TvScheduleDatabase()
        rows = db.get_week(week_start_str)     # None if never fetched, else list of rows
        db.mark_week_fetched(week_start_str, [(episode_id, show_id), ...])
        db.cleanup(cutoff_week_start_str)       # evict weeks older than the retention window
        db.clear_all()                          # region/language filter changed - drop all bookkeeping
    """

    def __init__(self):
        super().__init__(g.TV_SCHEDULE_DB_PATH, schema)

    def get_week(self, week_start):
        """Returns [{"trakt_episode_id":.., "trakt_show_id":..}, ...] if this
        week has already been fetched, or None on a cache miss (never fetched)."""
        rows = self.fetchall(
            "SELECT trakt_episode_id, trakt_show_id FROM schedule_episodes WHERE week_start = ?",
            (week_start,),
        )
        if not rows:
            # A previously-fetched-but-genuinely-empty week (no shows airing) is
            # indistinguishable from never-fetched without a second signal - the
            # caller only ever asks for weeks it's about to fetch-if-missing, and
            # an empty result there just means one harmless re-fetch, not a bug.
            return None
        return rows

    def mark_week_fetched(self, week_start, episode_show_pairs):
        """episode_show_pairs: iterable of (trakt_episode_id, trakt_show_id)."""
        if not episode_show_pairs:
            return
        self.execute_sql(
            "INSERT OR REPLACE INTO schedule_episodes (trakt_episode_id, trakt_show_id, week_start) "
            "VALUES (?, ?, ?)",
            [(eid, sid, week_start) for eid, sid in episode_show_pairs],
        )

    def cleanup(self, cutoff_week_start):
        """Evict bookkeeping for weeks older than cutoff_week_start (exclusive
        of the cutoff itself - the caller passes the oldest week still worth
        keeping fresh)."""
        try:
            self.execute_sql(
                "DELETE FROM schedule_episodes WHERE week_start < ?", (cutoff_week_start,)
            )
        except Exception as e:
            g.log(f"TvScheduleDatabase.cleanup error: {e}", "warning")

    def clear_all(self):
        """Drop all bookkeeping - used when the region/language filter changes,
        since a cached week's episode set was fetched under the old filter."""
        try:
            self.execute_sql("DELETE FROM schedule_episodes")
            g.log("TvScheduleDatabase: Cleared all entries", "info")
        except Exception as e:
            g.log(f"TvScheduleDatabase.clear_all error: {e}", "warning")

    def get_stats(self):
        try:
            # row_factory returns every row as a {column_name: value} dict (see
            # database/__init__.py SQLiteConnection._set_connection_settings) -
            # explicit AS aliases so lookup is by name, not a bare integer index.
            total = self.fetchone("SELECT COUNT(*) AS total FROM schedule_episodes")
            weeks = self.fetchone("SELECT COUNT(DISTINCT week_start) AS weeks FROM schedule_episodes")
            return {"total": total["total"] if total else 0, "weeks": weeks["weeks"] if weeks else 0}
        except Exception:
            return {"total": 0, "weeks": 0}
