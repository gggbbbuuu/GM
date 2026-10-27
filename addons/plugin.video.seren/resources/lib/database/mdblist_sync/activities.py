from functools import cached_property

import xbmc

from resources.lib.database import mdblist_sync
from resources.lib.modules.exceptions import ActivitySyncFailure
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g


class MDBListSyncDatabase(mdblist_sync.MDBListSyncDatabase):
    def __init__(self):
        super().__init__()

    @cached_property
    def mdblist_api(self):
        from resources.lib.indexers.mdblist import MDBListAPI

        return MDBListAPI()

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
        set_base_activities() rather than a destructive table wipe - movies and
        episodes are both fully repopulated by the subsequent sync_activities()
        call (see _sync_watched()), so a direct wipe here would be redundant,
        not safer."""
        from resources.lib.database.trakt_sync import clear_list_cache

        self.set_base_activities()
        clear_list_cache()
        self.sync_activities()

    def sync_activities(self):
        with GlobalLock("mdblist.sync"):
            if not g.get_bool_setting("mdblist.enabled") or not (g.get_setting("mdblist.auth") or g.get_setting("mdblist.apikey")):
                g.log("MDBListSync: MDBList disabled or no auth present, no sync will occur", "warning")
                return

            self.refresh_activities()
            remote_activities = self.mdblist_api.get_json("sync/last_activities")
            if not remote_activities:
                g.log("MDBList Activities Sync Failure: unable to connect to MDBList", "error")
                return True

            update_time = self._get_datetime_now()
            watched_count = 0
            playback_count = 0

            watched_stale = self.requires_update(
                remote_activities.get("watched_at") or self.base_date, self.activities["watched_at"]
            )
            episode_watched_stale = self.requires_update(
                remote_activities.get("episode_watched_at") or self.base_date,
                self.activities["episode_watched_at"],
            )
            if watched_stale or episode_watched_stale:
                try:
                    watched_count = self._sync_watched()
                    self._update_activity_record("watched_at", update_time)
                    self._update_activity_record("episode_watched_at", update_time)
                except ActivitySyncFailure as e:
                    g.log(f"Failed to sync MDBList watched status: {e}", "error")

            playback_remote = max(
                remote_activities.get("paused_at") or self.base_date,
                remote_activities.get("episode_paused_at") or self.base_date,
            )
            if self.requires_update(playback_remote, self.activities["playback_at"]):
                try:
                    playback_count = self._sync_playback()
                    self._update_activity_record("playback_at", update_time)
                except ActivitySyncFailure as e:
                    g.log(f"Failed to sync MDBList playback: {e}", "error")

            # No last_activities signal exists for list contents (checked: this
            # endpoint only returns watched_at/episode_watched_at/paused_at/
            # episode_paused_at), so this always runs whenever the outer sync runs
            # rather than being gated on a delta timestamp - same reasoning as
            # TraktSyncDatabase._sync_list_items's gate=None wiring.
            try:
                self._sync_list_items()
            except ActivitySyncFailure as e:
                g.log(f"Failed to sync MDBList list items: {e}", "error")

            if watched_count or playback_count:
                g.notification_unless_playing(g.ADDON_NAME, g.get_language_string(30953).format(watched_count, playback_count))
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=widgetRefresh&playing=False")')

    def _sync_watched(self):
        """Pulls GET /sync/watched (offset/limit-paginated per mdblist.apib - the
        response's pagination object has no cursor/next_cursor field, only
        offset/limit/has_more; a prior version of this method assumed a cursor
        that never existed, so pagination always silently stopped after page 1).

        Every page is collected into memory first; movies and episodes are
        each reset and repopulated as a unit only once pagination has cleanly
        finished (has_more went false). A page fetch failing mid-loop raises
        ActivitySyncFailure before any table is touched, instead of leaving
        either table wiped with only a partial repopulate.

        Movies were previously always empty due to a nesting bug (reading
        m["ids"]["tmdb"] instead of m["movie"]["ids"]["tmdb"], which meant
        every real entry failed its own tmdb-id filter) - now fixed. Live-
        confirmed 2026-07-18 against a real account (417 movies returned,
        correctly nested) that MDBList's API does populate this endpoint's
        movies list, so - like episodes - movies are now reset before
        repopulating: this is a complete paginated fetch of current server
        state, not a delta, so a clean-finish reset+repopulate reflects
        reality, and it makes a movie removed/unmarked on MDBList (or a
        cross_sync push whose local write got skipped, see cross_sync.py)
        self-healing on the next sync instead of a permanent local phantom.
        A locally-authored write (write_watched_locally(), scrobbler/context-
        menu) can be transiently overwritten if a full sync lands in the
        narrow window before MDBList's backend surfaces that same write back
        through this endpoint; that's a bounded, self-correcting risk (next
        sync repopulates it once MDBList catches up), the same risk profile
        already accepted for Simkl's removal reconciliation.

        This endpoint's response also carries "shows" and "seasons" buckets (per
        mdblist.apib) for bulk mark-watched actions taken on a whole show/season on
        MDBList's own site/app - MDBList has no per-episode record for those. Live-
        confirmed 2026-08-16 against a real account that these buckets are routinely
        populated, not an edge case (88 shows, 193 seasons, against 3427 individually-
        tracked episodes) - e.g. a 176-episode show bulk-marked watched as a whole,
        with only a handful of incidental season-0 specials individually tracked. A
        show/season bulk-marked that way contributes no local "episodes" rows, which
        surfaced as a stale/wrong "next episode" downstream. (Update 3.9.53: those buckets
        turned out to be per-show/per-season roll-ups present for EVERY show with watch
        history, not bulk marks, so nothing reads bulk_watched_shows/bulk_watched_seasons
        any more - mdblistMenus.Menus.next_up uses only the individual episodes. They are
        still persisted below.) Reset+repopulated the same way as movies/episodes: a full
        DELETE, not a delta, since this is a complete paginated fetch of current server
        state each cycle."""
        movie_rows = []
        episode_rows = []
        show_rows = []
        season_rows = []
        offset = 0
        limit = 100
        try:
            for _ in range(500):  # safety cap well above any realistic page count
                page = self.mdblist_api.get_json("sync/watched", offset=offset, limit=limit)
                if page is None:
                    raise ActivitySyncFailure("empty response from MDBList (sync/watched)")

                movies = page.get("movies") or []
                episodes = page.get("episodes") or []
                shows = page.get("shows") or []
                seasons = page.get("seasons") or []

                movie_rows.extend(
                    (m["movie"]["ids"]["tmdb"], m["movie"]["ids"].get("imdb"), m.get("last_watched_at"))
                    for m in movies
                    if m.get("movie", {}).get("ids", {}).get("tmdb")
                )
                episode_rows.extend(
                    (
                        e["episode"]["show"]["ids"]["tmdb"],
                        e["episode"]["season"],
                        e["episode"]["number"],
                        e.get("last_watched_at"),
                    )
                    for e in episodes
                    if e.get("episode", {}).get("show", {}).get("ids", {}).get("tmdb")
                )
                show_rows.extend(
                    (s["show"]["ids"]["tmdb"], s.get("last_watched_at"))
                    for s in shows
                    if s.get("show", {}).get("ids", {}).get("tmdb")
                )
                season_rows.extend(
                    (
                        s["season"]["show"]["ids"]["tmdb"],
                        s["season"]["number"],
                        s.get("last_watched_at"),
                    )
                    for s in seasons
                    if s.get("season", {}).get("show", {}).get("ids", {}).get("tmdb")
                    and s.get("season", {}).get("number") is not None
                )

                pagination = page.get("pagination") or {}
                if not pagination.get("has_more"):
                    break
                offset += limit

            self.execute_sql("UPDATE episodes SET watched=0")
            if episode_rows:
                self.execute_sql(
                    "REPLACE INTO episodes (show_tmdb_id, season, number, watched, last_watched_at) "
                    "VALUES (?, ?, ?, 1, ?)",
                    episode_rows,
                )
            self.execute_sql("UPDATE movies SET watched=0")
            if movie_rows:
                self.execute_sql(
                    "REPLACE INTO movies (tmdb_id, imdb_id, watched, last_watched_at) VALUES (?, ?, 1, ?)",
                    movie_rows,
                )
            self.execute_sql("DELETE FROM bulk_watched_shows")
            if show_rows:
                self.execute_sql(
                    "REPLACE INTO bulk_watched_shows (show_tmdb_id, last_watched_at) VALUES (?, ?)",
                    show_rows,
                )
            self.execute_sql("DELETE FROM bulk_watched_seasons")
            if season_rows:
                self.execute_sql(
                    "REPLACE INTO bulk_watched_seasons (show_tmdb_id, season, last_watched_at) VALUES (?, ?, ?)",
                    season_rows,
                )
        except ActivitySyncFailure:
            raise
        except Exception as e:
            raise ActivitySyncFailure(e) from e
        return len(movie_rows) + len(episode_rows) + len(show_rows) + len(season_rows)

    def _sync_playback(self):
        """Pulls GET /sync/playback (flat array, not paginated per the
        live-confirmed response for accounts of this size). ids block uses
        key "tmdb" for both movie and show entries - same convention as
        sync/watched, live-confirmed 2026-07-18 (a prior fix here assumed
        "tmdbid" per a spec reading that turned out not to match the live
        API; that would have silently zeroed every bookmark row)."""
        try:
            entries = self.mdblist_api.get_json("sync/playback") or []
            if isinstance(entries, dict):
                entries = entries.get("items") or []

            rows = []
            for entry in entries:
                progress = entry.get("progress")
                runtime = entry.get("runtime")
                if progress is None or runtime is None:
                    continue
                try:
                    percent = float(progress)
                    resume_time = round(percent / 100 * float(runtime) * 60)
                except (TypeError, ValueError):
                    continue
                paused_at = entry.get("paused_at")
                media_type = entry.get("type")

                if media_type == "movie":
                    movie = entry.get("movie") or {}
                    tmdb_id = movie.get("ids", {}).get("tmdb")
                    if not tmdb_id:
                        continue
                    rows.append((tmdb_id, None, None, "movie", str(percent), str(resume_time), paused_at))
                elif media_type == "episode":
                    episode = entry.get("episode") or {}
                    show = entry.get("show") or {}
                    tmdb_id = show.get("ids", {}).get("tmdb")
                    season = episode.get("season")
                    number = episode.get("number")
                    if not tmdb_id or season is None or number is None:
                        continue
                    rows.append((tmdb_id, season, number, "episode", str(percent), str(resume_time), paused_at))

            self.execute_sql("DELETE FROM bookmarks")
            if rows:
                self.execute_sql(
                    "INSERT INTO bookmarks (tmdb_id, season, number, media_type, percent_played, "
                    "resume_time, paused_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                    rows,
                )
            return len(rows)
        except Exception as e:
            raise ActivitySyncFailure(e) from e

    def _sync_list_items(self):
        """Full per-list content sync backing the Add/Remove Custom List menu gate in
        trakt_context_menu.py. No delta endpoint exists for list item changes, so this
        is a full walk of every static list's full contents each time it runs - cost
        scales with list count x list size, an accepted tradeoff (see
        Project_Report_Full.md, session ListMembershipGating). GET lists/{id}/items is
        offset/limit paginated like sync/watched (pagination.has_more, no cursor) -
        live-confirmed 2026-08-16 against a real list: movies/shows entries are flat
        (item["ids"]["tmdb"] directly, not nested under an extra "movie"/"show" key the
        way sync/watched's entries are). Filtered to non-dynamic lists only, matching
        _mdblist_static_lists() exactly - a dynamic/smart list's items reject manual
        add/remove per the API, so counting them here would make Remove From Custom
        List appear for a list the picker can never target."""
        try:
            lists = self.mdblist_api.get_json("lists/user")
            if lists is None:
                # None means the fetch itself failed - see the matching guard
                # in TraktSyncDatabase._sync_list_items for why this can't
                # collapse to [] via `or []`: that would fall through to the
                # unconditional DELETE FROM list_items below with nothing to
                # reinsert, wiping every list's membership data on a single
                # transient hiccup. A genuinely-empty account (lists == [])
                # is fine to proceed with - list_ids ends up [], rows stays
                # [], and the delete correctly leaves the table empty.
                raise ActivitySyncFailure("empty response from MDBList (lists/user)")
            list_ids = [lst["id"] for lst in lists if not lst.get("dynamic")]

            rows = []
            for list_id in list_ids:
                offset = 0
                limit = 100
                for _ in range(500):  # safety cap well above any realistic page count
                    page = self.mdblist_api.get_json(f"lists/{list_id}/items", offset=offset, limit=limit)
                    if page is None:
                        raise ActivitySyncFailure(f"empty response from MDBList (lists/{list_id}/items)")

                    for media_type in ("movies", "shows"):
                        rows.extend(
                            (list_id, item["ids"]["tmdb"], media_type[:-1])
                            for item in (page.get(media_type) or [])
                            if item.get("ids", {}).get("tmdb")
                        )

                    pagination = page.get("pagination") or {}
                    if not pagination.get("has_more"):
                        break
                    offset += limit

            self.execute_sql("DELETE FROM list_items")
            if rows:
                self.execute_sql(
                    "INSERT OR IGNORE INTO list_items(list_id, tmdb_id, mediatype) VALUES(?,?,?)",
                    rows,
                )
        except ActivitySyncFailure:
            raise
        except Exception as e:
            raise ActivitySyncFailure(e) from e
