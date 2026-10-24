import collections
import json
import os

from resources.lib.database import Database
from resources.lib.database import _evict_thread_connection
from resources.lib.database import _get_thread_connection
from resources.lib.modules.globals import g

schema = {
    "snapshot": {
        "columns": collections.OrderedDict(
            [
                ("domain", ["TEXT", "NOT NULL"]),
                ("service", ["TEXT", "NOT NULL"]),
                ("media_type", ["TEXT", "NOT NULL"]),
                ("tmdb_id", ["INTEGER", "NOT NULL"]),
                ("item_key", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY(domain, service, media_type, item_key)"],
        "indices": [
            ("idx_bridge_snapshot_lookup", ["domain", "service", "media_type"]),
        ],
        "default_seed": [],
    },
}


class BridgeSyncDatabase(Database):
    """Persists each domain+service+media_type's full item-set as of the last
    successful bridgeSync run. bridgeSync.py diffs the freshly-read current set
    against this snapshot to find only what's genuinely new since last run
    (newly_added = current - snapshot), pushes that outward, then overwrites the
    snapshot with the current set. This is deliberately NOT a monotonic
    "ever-seen" record - it must reset when an item disappears from a service
    (e.g. unwatched externally), or a later legitimate re-add would be silently
    blocked. See modules/bridgeSync.py's module docstring for the full rationale
    (advisor-reviewed: this is what avoids the reversal-bug risk of a naive
    full-current-state diff against another service's own state)."""

    def __init__(self):
        super().__init__(g.BRIDGE_SYNC_DB_PATH, schema)

    def get_snapshot(self, domain, service, media_type):
        """Returns {item_key: tmdb_id} for every item this (domain, service,
        media_type) held as of the last successful run."""
        rows = self.fetchall(
            "SELECT item_key, tmdb_id FROM snapshot WHERE domain=? AND service=? AND media_type=?",
            (domain, service, media_type),
        )
        return {r["item_key"]: r["tmdb_id"] for r in rows}

    def replace_snapshot(self, domain, service, media_type, current_items):
        """Overwrites the stored set for this (domain, service, media_type) with
        current_items ({item_key: tmdb_id}) - always the full set, never a partial
        update, so a missing item is correctly treated as "gone" next run."""
        self.execute_sql(
            "DELETE FROM snapshot WHERE domain=? AND service=? AND media_type=?",
            (domain, service, media_type),
        )
        if current_items:
            rows = [
                (domain, service, media_type, tmdb_id, item_key)
                for item_key, tmdb_id in current_items.items()
            ]
            self.execute_sql(
                "INSERT INTO snapshot (domain, service, media_type, tmdb_id, item_key) VALUES (?, ?, ?, ?, ?)",
                rows,
            )

    def replace_snapshots(self, snapshots):
        """Overwrites several snapshots at once - {(domain, service, media_type): {item_key: tmdb_id}} - in ONE
        transaction. A crash between a DELETE and its INSERT would leave a snapshot empty, and an empty snapshot
        makes every item on that service look new on the next run, so nothing here may be applied piecemeal.
        Each snapshot is still a full replacement, never a partial update (see replace_snapshot)."""
        connection = _get_thread_connection(self._db_file)
        try:
            with connection.transaction() as cursor:
                for (domain, service, media_type), current_items in snapshots.items():
                    cursor.execute(
                        "DELETE FROM snapshot WHERE domain=? AND service=? AND media_type=?",
                        (domain, service, media_type),
                    )
                    if current_items:
                        cursor.executemany(
                            "INSERT INTO snapshot (domain, service, media_type, tmdb_id, item_key) VALUES (?, ?, ?, ?, ?)",
                            [
                                (domain, service, media_type, int(tmdb_id), str(item_key))
                                for item_key, tmdb_id in current_items.items()
                            ],
                        )
        except Exception:
            _evict_thread_connection(self._db_file)
            raise

    # Bridge state that is not a set of items (Simkl's last-seen activity stamp and its saved library views) is
    # kept in a JSON file beside the database, not in a table here: this class's schema is checksummed and any
    # change to it rebuilds - i.e. wipes - the whole database, snapshots included, and an empty snapshot makes
    # every item look new on every service.

    @property
    def _meta_path(self):
        return os.path.join(os.path.dirname(self._db_file), "bridgeSyncMeta.json")

    def get_meta(self):
        """Returns the saved meta dict ({} when there is none yet). A corrupt file raises - the caller decides."""
        try:
            with open(self._meta_path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return {}
        return data if isinstance(data, dict) else {}

    def set_meta(self, meta):
        """Writes the meta dict atomically (temp file + replace), so an interrupted write cannot leave a
        truncated file behind."""
        path = self._meta_path
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(meta, f)
        os.replace(path + ".tmp", path)
