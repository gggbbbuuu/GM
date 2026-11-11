"""
Periodic cross-service reconciliation (Phase 7, Layer 1). Catches changes
made directly on a service's own website/app, outside Kodi - the on-action
mirror (modules/cross_sync.py, Layer 2) only ever fires from a Kodi-
originated action.

Checked on Seren's existing maintenance-loop cadence (service.py) but only
actually executes once per crosssync.intervalMinutes (default 180). Also
gated on at least 2 of {trakt, mdblist, simkl} being configured - a genuinely
N-way design, not Trakt-hub-centric, so a Simkl+MDBList-only setup with no
Trakt still gets a full bridge between the two. If crosssync.enabled is left
on from before a service dropped below that threshold (disabled, revoked, or
never re-authed), _enabled() self-heals it back to off as a side effect - see
its own comment. Only ever forces off, never back on.

Snapshot-delta reconciliation, not a raw current-state diff. Each
(domain, service, media_type) keeps a persisted snapshot of its last fully-
accounted-for item set (database/bridge_sync). Every run:
  newly_added = current - snapshot
and only that gets pushed outward, to whichever other active services are
missing it. An item only enters the next snapshot once it's confirmed
present everywhere (already there, or the push just succeeded) - a failed
push leaves it out, so it's retried next run instead of silently dropped.
Items that vanish from current are dropped from the snapshot too, so a later
genuine re-add is still recognised as new - unless the vanished item is a
removal still being confirmed (see "Removals" below), which stays in the
snapshot until it is resolved.

This is what avoids the reversal bug a raw current-state diff has: if an
item is removed from service A directly (outside Kodi) while service B still
has it, a naive `current_B - current_A` diff would treat B's copy as
"missing from A, push it" and resurrect the very thing the user just
removed. Snapshot-gating means B's copy is old news (it was already in
snapshot_B last run), not new evidence - it only gets pushed if it
genuinely disappeared from B too and then came back.

Removals (setting crosssync.removals, same options and default as TMDb Helper
Multiservice's cross_sync_removals): an item that is in a service's snapshot
and is no longer listed by that service was removed there (unwatched, or taken
off a list on the website / in an app), and the same removal is carried to the
other services. Removing is destructive (Trakt history/remove deletes every
play of the item), so it is cautious:
  - an item must be missing on two runs in a row before anything is removed
    (a bad read does not repeat itself);
  - more than a few items vanishing from one service at once (cap = max(10,
    40 for episodes, 5 % of the snapshot)) is taken for an incomplete read and
    removes nothing;
  - a watched item that was played again on a service that still lists it
    after the end of the previous run is kept and sent back to the service
    that lost it (an unwatch followed by a rewatch inside one interval);
  - what is about to be removed is written to bridge_removals.jsonl first,
    with the watch dates it held;
  - a removal the bridge made is remembered for a few days, so a service that
    is slow to stop listing the item is asked again instead of the item being
    read as a new addition;
  - setting values: 0 off, 1 log only, 2 watchlist and collection (default),
    3 also watched history (opt-in: Trakt's history/remove deletes all plays).
Simkl: only a real unwatch counts (a movie back on plan-to-watch; an episode
Simkl really recorded; a watchlist item that is gone from Simkl's library),
never a move to completed / dropped / on hold.

A service whose read failed is skipped for the cycle - as a source and as a
target - and its snapshot is left untouched. A failed read is never treated
as "empty" (that would shrink the snapshot and later resurrect removals, or
make every item look missing from that service and flood its history).

Every service is read live (not from Seren's local sync tables): the local
tables are rebuilt in place by the activity syncs (Trakt zeroes every
episode's watched flag before repopulating, and only knows episodes that
were already milled), so a bridge run that lands mid-sync or before milling
would see a partial Trakt. Trakt is paged to an empty page, MDBList to
has_more=false, Simkl is read in full or not at all.

Domain coverage:
- Watched/movie: full 3-way (trakt, mdblist, simkl).
- Watched/episode: full 3-way. Specials (season 0) are left out on every
  side (Trakt's watched sync does not carry them, so they would all look
  missing from Trakt and be logged as fake plays). Whole shows are never
  pushed - a show-level mark means "every episode". Simkl's anime bucket uses
  different episode numbering (every cour is its own entry, counted from 1), so
  anime episodes are not sent to Simkl. Simkl's own anime episodes are carried to Trakt
  and MDBList in TMDb numbering when crosssync.anime is on (anime/bridge_entries.py
  maps them, each one only when AniZip and TMDb agree on its air date); the default
  is log only: the Kodi log says what would be copied and nothing is. The other way,
  anime episodes watched on Trakt go to Simkl by (entry, number) when crosssync.animeSimkl
  is on (a separate pass after the reconcile, see _anime_simkl_sync). Anime un-watches
  (crosssync.animeRemovals, needs crosssync.removals 3 and crosssync.anime On) go by
  (entry, number) in both directions; whatever the removals settings, an episode that
  Simkl itself dropped is remembered (meta anime_simkl_unwatched) and not sent back
  from Trakt until it is played again. From
  Simkl to Trakt only episodes the user actually recorded on Simkl go out
  (the rest are synthetic rows Simkl invents for completed shows, with
  approximate dates).
- Watchlist/movie+tvshow: full 3-way, Simkl as plan-to-watch. An item Simkl
  already has in another status (completed, watching, hold, dropped, not
  interested) is never overwritten - an add-to-list moves its status.
- Collection/movie+tvshow: trakt + mdblist only. Simkl has no Collection
  endpoint at all (confirmed absent from its API).
- Progress: one-directional Trakt -> mdblist/simkl. No snapshot (a resume
  position changes on every playback anyway), but a resume point is only sent
  where it would not do harm:
    * not when MDBList, Simkl (or Trakt itself) recorded the item as watched at
      or after the time Trakt saved the point - Trakt marks an item watched
      from 80 % while MDBList and Simkl do from 75 %, so Trakt keeps the
      resume point of an item the others already count as watched, and sending
      it on would put the finished item back "in progress" there;
    * not when the target already holds a resume point for the item that is
      the same or newer (paused_at) - it would overwrite progress made there;
    * a target whose resume points cannot be read is skipped for the run;
    * Simkl keeps one resume point per show, so of a show's episodes only the
      one Trakt saved last is sent.
  A post that gets no usable answer is counted and logged.
- Rating: on-action mirror only (cross_sync.py); it is a value+timestamp, not
  set-membership, so it needs a different mechanism than everything above.

Simkl is read only when /sync/activities says it changed since the last
cycle (Simkl asks apps not to poll its lists unconditionally); otherwise the
views saved by the last cycle (database/bridge_sync meta) are used. Its writes
are spaced 21 s apart (per-user write lock, a second write inside it is
answered 400 rate_limit).

Trakt history is an additive play log, not a set: every POST without a
watched_at stamps a new play. So watched pushes to Trakt and Simkl carry the
source's real watch date, go out at most _HISTORY_CAP items per domain per
cycle, and a result that does not add up is given up on rather than retried.
Caps are shared per target across all sources, so two sources cannot each use
the full budget.

An item this run pushed to a service is accounted for on that service's side
too (its snapshot, and its `newly`): it did not originate there, so it is
never sent onward from there. Without that a synthetic Simkl episode could be
laundered into Trakt via MDBList, past the filter applied to Simkl itself.
"""

import json
import os
import re
import time
from datetime import datetime, timezone

from resources.lib.modules.globals import g
from resources.lib.modules.syncGateway import configured_providers

_WATCHED = "watched"
_WATCHLIST = "watchlist"
_COLLECTION = "collection"

_BATCH_SIZE = 100  # max items per Trakt / Simkl call
_MDB_CHUNK = 50  # max items per MDBList call (live-tested chunk size, a safe margin below the 200 proven)
_HISTORY_CAP = 50  # max Trakt history pushes (each one is a new play) per domain per cycle
_MDB_EPISODE_CAP = 250  # max MDBList episode pushes per cycle (API-call budget while the first runs converge)
_SIMKL_CAP = 300  # max Simkl pushes per domain per cycle (<= 3 calls: Simkl locks writes for 20 s per user)
_SIMKL_LOCK_SECONDS = 21
_SIMKL_PROGRESS_CAP = 20  # max Simkl resume posts per cycle (each one waits out the 21 s write lock)
_RESUME_FAIL_RUNS = 2  # a Simkl resume point refused on this many runs in a row is not sent again for _RESUME_FAIL_SECONDS ...
_RESUME_FAIL_SECONDS = 86400  # ... unless Trakt's copy of it changes (a title Simkl does not know answers 404 every time)
_PAGE_CAP = 200  # safety cap on Trakt pages per read
_READ_TIMEOUT = 30  # seconds: a full-library page is far bigger than the 10 s default request budget was sized for
_TARGET_NAMES = {"mdblist": "MDBList", "simkl": "Simkl", "trakt": "Trakt"}
# Simkl names the Dropped status per app: a token of Seren's app reads back "dropped", an app with the older
# vocabulary (TMDb Helper's) reads back "notinteresting" - live-probed 2026-10-14. Both mean the user dropped it.
_SIMKL_DROPPED = ("dropped", "notinteresting")
_STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_RUNNING_KEY = "seren.bridgeSync.running"
_RUNNING_STALE_SECONDS = 60 * 60
_REMOVE_MASS_CAP = 10  # more than this many items (or 5 % of the snapshot) vanishing from one service at once looks like an
_REMOVE_MASS_CAP_EPISODES = 40  # incomplete read, not the user: nothing is removed from the other services for it
_REMOVE_CLOCK_MARGIN = 90  # seconds a play must be newer than the end of the last run to count as "played again"
_REMOVE_RECENT_DAYS = 3  # how long an item the bridge removed is not taken for a new addition if the service still lists it
_JOURNAL_FILE = "bridge_removals.jsonl"  # addon_data: one line per removal the bridge made (what, where, the dates it held)
_JOURNAL_LINES = 2000
_OLD_ACTIVITY_STAMP = "2000-01-01T00:00:00"  # older than any Trakt activity, but not Seren's base date (see _trakt_force_refresh)
_REMOVE_CONFIRM_SECONDS = 180  # an item must have been missing this long, as well as on two runs: runs can now follow each other within a minute (bridgeTrigger.py)
_REMOVALS_DEFAULT = 2  # setting crosssync.removals: 0 off, 1 log only, 2 watchlist + collection, 3 also watched history
_ANIME_DEFAULT = 1  # setting crosssync.anime: 0 off, 1 log only, 2 on - Simkl's anime episodes are carried to Trakt / MDBList
_ANIME_SIMKL_DEFAULT = 1  # setting crosssync.animeSimkl: 0 off, 1 log only, 2 on - anime episodes watched on Trakt are sent to Simkl
_ANIME_REMOVALS_DEFAULT = 1  # setting crosssync.animeRemovals: 0 off, 1 log only, 2 on - an anime episode un-watched on one service is un-watched on the others
_ANIME_COORDS_GONE_SECONDS = 3 * 86400  # how long the entry coordinates of an anime episode that left Simkl's mapped view are kept for the removal check
_ANIME_JOURNAL_FILE = "bridge_anime_simkl.jsonl"  # addon_data: one line per anime episode the bridge sent to Simkl (entry ids, number, TMDb key, date)
_ANIME_REFUSED_SECONDS = 7 * 86400  # an anime episode Simkl refused is not sent again for this long
_ANIME_PUSH_CHUNK = 100  # episodes per Simkl anime request (several entries share one request)
_ANIME_CYCLE_CAP = 100  # anime episodes sent to Simkl per cycle: the 21 s write spacing keeps a run short, a backlog takes a few cycles
_ANIME_SENT_SECONDS = 3 * 86400  # how long a sent episode is waited for to show up when Simkl is read back


def _enabled():
    if not g.get_bool_setting("crosssync.enabled", False):
        return False
    if len(configured_providers()) < 2:
        # Stale "on" toggle from before a service dropped below the 2-provider minimum
        # (disabled, revoked, or never re-authed) - correct it here, on Seren's existing
        # maintenance-loop cadence (service.py), rather than only reactively on the next
        # settings-dialog close. Never auto-enables back on.
        g.set_setting("crosssync.enabled", False)
        return False
    return True


def _interval_elapsed():
    # crosssync.lastRunAt is an undeclared hidden setting, not in settings.xml (same pattern as simkl.anime_completed_at).
    interval_seconds = g.get_int_setting("crosssync.intervalMinutes", 180) * 60
    last_run = g.get_float_setting("crosssync.lastRunAt", 0.0)
    return (time.time() - last_run) >= interval_seconds


def _acquire_run():
    """Non-blocking single-run guard (a long Simkl-paced run must not overlap the next scheduled one).
    The marker is a timestamp so a run that died without clearing it stops blocking after an hour."""
    try:
        started = float(g.get_runtime_setting(_RUNNING_KEY) or 0)
    except (TypeError, ValueError):
        started = 0.0
    if started and (time.time() - started) < _RUNNING_STALE_SECONDS:
        return False
    g.set_runtime_setting(_RUNNING_KEY, str(time.time()))
    return True


def _release_run():
    g.clear_runtime_setting(_RUNNING_KEY)


def run(force=False):
    """Returns True when a reconciliation really ran (the trigger schedules follow-ups only after one)."""
    if not _enabled():
        return False
    if not force and not _interval_elapsed():
        return False
    if not _acquire_run():
        g.log("bridgeSync: a previous run is still in progress - skipping", "info")
        return False
    try:
        from resources.lib.database.bridge_sync import BridgeSyncDatabase

        bridge = _Bridge(configured_providers(), BridgeSyncDatabase())
        bridge.run()
        g.set_setting("crosssync.lastRunAt", time.time())
        _rebaseline(bridge)
        return True
    finally:
        _release_run()


def _rebaseline(bridge):
    """After a run: take the services' activity stamps as they are now, so the run's own pushes do not start the next one."""
    from resources.lib.modules.bridgeTrigger import dynamic_enabled

    if dynamic_enabled():
        try:
            bridge.rebaseline_activity()
        except Exception as e:
            g.log(f"bridgeSync: activity stamps not saved: {e}", "warning")


def _pending_removals():
    """True while an item first found missing within the last two confirm windows waits for its second check. An entry
    that stays pending for good (log-only mode, a target that keeps failing) stops counting, so it cannot keep the
    trigger scheduling follow-up runs."""
    try:
        from resources.lib.database.bridge_sync import BridgeSyncDatabase

        meta = BridgeSyncDatabase().get_meta() or {}
        seen = meta.get("removals_seen") or {}
        now = time.time()
        for label, items in (meta.get("removals") or {}).items():
            for key in items or ():
                at = (seen.get(label) or {}).get(key)
                if at and now - at <= 2 * _REMOVE_CONFIRM_SECONDS:
                    return True
    except Exception:
        pass
    return False


def run_now():
    """Forced run, started by the trigger (action bridgeSyncNow). Still respects crosssync.enabled and the one-run guard;
    always tells the trigger it is over, even when it did nothing."""
    from resources.lib.modules.bridgeTrigger import publish_finished

    ran = False
    try:
        ran = run(force=True)
    finally:
        publish_finished(ran and _pending_removals())


def poll():
    """One poll of the services' activity stamps (action bridgeTriggerPoll); a change runs the bridge in this interpreter."""
    from resources.lib.modules.bridgeTrigger import dynamic_enabled, publish_finished

    ran = False
    try:
        if not dynamic_enabled() or not _enabled():
            return
        if not _acquire_run():
            return
        try:
            from resources.lib.database.bridge_sync import BridgeSyncDatabase

            bridge = _Bridge(configured_providers(), BridgeSyncDatabase())
            changed = bridge.poll_activity()
            if changed:
                g.log(f"bridgeSync: running - new activity on {', '.join(changed)}", "info")
                bridge.run()
                g.set_setting("crosssync.lastRunAt", time.time())
                _rebaseline(bridge)
                ran = True
        finally:
            _release_run()
    finally:
        publish_finished(ran and _pending_removals())


class _Bridge:
    """State of one bridge run: the services involved, this run's saved/loaded Simkl views, the watch dates seen
    on the other services and the per-run caches."""

    def __init__(self, services, bridge_db):
        self.services = set(services)
        self.db = bridge_db
        self._ok = True  # False once the snapshot store failed: no further pushes this run
        self._apis = {}
        self._meta = None  # persisted beside the snapshots: Simkl's last-seen activity stamp + its saved views
        self._simkl = None  # this run's Simkl views (see _simkl_prepare); None = Simkl unreadable
        self._simkl_prepared = False
        self._simkl_last_write = 0.0
        self._stamps = {}  # {(media, item_key): newest last_watched_at seen on any service, Trakt included}
        self._anime_stamps = {}  # {key: Simkl's watched_at} of the mapped anime episodes: the date they carry on Trakt, whichever service sends them
        self._anime_keys = set()  # Simkl anime episodes taken into this run's Simkl view (crosssync.anime on): only ever sources
        self._anime_cache = None  # (mapped {key: watched_at}, stats) of Simkl's anime episodes in TMDb numbering, one per run
        self._anime_coords = {}  # {TMDb key: (AniList id, number inside the entry)} of this run's mapped anime episodes
        self._anime_known_memo = {}  # {tmdb id: True if the Fribb index knows the show}
        self._anime_synth_cache = None  # TMDb keys of anime episodes Simkl holds only as bulk-marked rows
        self._anime_gone = {}  # {TMDb key: (AniList id, number)} kept for a few days for keys that left the mapped view: what an un-watch on Simkl is checked against
        self._anime_coords_done = False
        self._anime_removal_logged = set()
        self._anime_dirty = False  # this run wrote anime episodes to Simkl: its saved views are stale, read it again next cycle
        self._simkl_loaded = False  # True when this run re-read Simkl (not the saved views)
        self._tstamps = {}  # {(media, item_key): last_watched_at as Trakt itself reports it}: the date an episode carries to Simkl
        self._mdb_watched_cache = None  # one MDBList /sync/watched read per run (movies + episodes)
        self._simkl_prev_real = set()  # episodes Simkl held a real record for at the last cycle (before this run's read)
        self._run_started = ""  # UTC ISO time this run started
        self._removed = {}  # {service: count} removed by this run

    # region Entry point

    def run(self):
        g.log("bridgeSync: starting reconciliation", "info")
        self._run_started = self._utc_now()
        try:
            from resources.lib.modules.anime import bridge_entries

            bridge_entries.begin_run()  # the service lives for hours: forget the per-run anime caches
        except Exception as e:
            g.log(f"bridgeSync: anime cache reset failed - {type(e).__name__}", "warning")
        for fn in (
            self._sync_watched_movies,
            self._sync_watched_episodes,
            self._sync_watchlist,
            self._sync_collection,
            self._sync_progress,
        ):
            if g.abort_requested():
                return
            try:
                fn()
            except Exception as e:
                g.log(f"bridgeSync: {fn.__name__} error: {e}", "error")
        self._simkl_finish()
        self._finish_run()
        g.log("bridgeSync: reconciliation complete", "info")

    # endregion

    # region API handles

    def _api(self, service):
        if service not in self._apis:
            if service == "trakt":
                from resources.lib.indexers.trakt import TraktAPI as api_class
            elif service == "mdblist":
                from resources.lib.indexers.mdblist import MDBListAPI as api_class
            else:
                from resources.lib.indexers.simkl import SimklAPI as api_class
            self._apis[service] = api_class()
        return self._apis[service]

    # endregion

    # region Trakt readers (live; every reader returns None on failure, never an empty dict that would
    # look like "Trakt has nothing")

    def _trakt_pages(self, path, limit=100, **params):
        """Every row of a paged Trakt list, read to an empty page (the X-Pagination counts are unreliable on
        some endpoints, and a server-side cap below `limit` must not look like the last page). None if any
        page fails or the page budget runs out."""
        api = self._api("trakt")
        rows = []
        for page in range(1, _PAGE_CAP + 1):
            try:
                response = api.get(path, page=page, limit=limit, timeout=_READ_TIMEOUT, **params)
                if response is None or response.status_code != 200:
                    g.log(f"bridgeSync: trakt {path} page {page} read failed", "warning")
                    return None
                data = response.json()
            except Exception as e:
                g.log(f"bridgeSync: trakt {path} page {page} read failed: {e}", "warning")
                return None
            if not isinstance(data, list):
                return None
            if not data:
                return rows
            rows.extend(data)
        g.log(f"bridgeSync: trakt {path} read did not finish within {_PAGE_CAP} pages", "warning")
        return None

    @staticmethod
    def _played(entry):
        plays = entry.get("plays")
        return not isinstance(plays, int) or plays > 0

    def _trakt_watched_movies(self):
        rows = self._trakt_pages("sync/watched/movies")
        if rows is None:
            return None
        result = {}
        for item in rows:
            tmdb_id = ((item.get("movie") or {}).get("ids") or {}).get("tmdb")
            if tmdb_id and self._played(item):
                result[str(tmdb_id)] = int(tmdb_id)
                self._note_stamp("movie", str(tmdb_id), item.get("last_watched_at"))
        return result

    def _trakt_watched_episodes(self):
        """{'show:season:number': show_tmdb_id}. Specials (season 0) are left out on every side."""
        rows = self._trakt_pages("sync/watched/shows", extended="progress")
        if rows is None:
            return None
        result = {}
        for item in rows:
            tmdb_id = ((item.get("show") or {}).get("ids") or {}).get("tmdb")
            if not tmdb_id:
                continue
            for season in item.get("seasons") or []:
                if not season.get("number"):
                    continue
                for episode in season.get("episodes") or []:
                    if episode.get("number") is None or not self._played(episode):
                        continue
                    key = f"{tmdb_id}:{season['number']}:{episode['number']}"
                    result[key] = int(tmdb_id)
                    self._note_stamp("episode", key, episode.get("last_watched_at"))
                    stamp = episode.get("last_watched_at")
                    if isinstance(stamp, str) and _STAMP_RE.match(stamp) and stamp > self._tstamps.get(("episode", key), ""):
                        self._tstamps[("episode", key)] = stamp
        return result

    def _trakt_set(self, kind):
        """Watchlist ('watchlist') or collection ('collection') as {'movie:<id>' / 'show:<id>': id}, or None.
        Paged explicitly: Trakt applies default pagination even to an unparameterised call."""
        result = {}
        for endpoint, media in (("movies", "movie"), ("shows", "show")):
            path = f"users/me/watchlist/{endpoint}" if kind == _WATCHLIST else f"sync/collection/{endpoint}"
            rows = self._trakt_pages(path, limit=250)
            if rows is None:
                return None
            for entry in rows:
                tmdb_id = ((entry.get(media) or {}).get("ids") or {}).get("tmdb")
                if tmdb_id:
                    result[f"{media}:{tmdb_id}"] = int(tmdb_id)
        return result

    # endregion

    # region MDBList readers (live)

    def _mdb_get_paginated(self, path, max_pages=50):
        """Walks a shared-cursor MDBList sync endpoint (one offset/limit window spanning movies+shows+seasons+
        episodes combined) to completion via has_more, merging each page's arrays.

        Returns None if any page fails or the page budget runs out: a failed read must not look like an empty
        MDBList. A successful read of an empty account is a real {}."""
        api = self._api("mdblist")
        combined = {}
        offset = 0
        for _ in range(max_pages):
            try:
                page = api.get_json(path, offset=offset, limit=1000, timeout=_READ_TIMEOUT)
            except Exception as e:
                g.log(f"bridgeSync: mdblist {path} read failed: {e}", "warning")
                return None
            if not isinstance(page, dict):
                g.log(f"bridgeSync: mdblist {path} read failed at offset {offset}", "warning")
                return None
            consumed = 0
            for key in ("movies", "shows", "seasons", "episodes"):
                if page.get(key):
                    combined.setdefault(key, []).extend(page[key])
                    consumed += len(page[key])
            if not (page.get("pagination") or {}).get("has_more"):
                return combined
            if not consumed:
                g.log(f"bridgeSync: mdblist {path} claims more data but returned none at offset {offset}", "warning")
                return None
            offset += consumed  # the window actually served, in case the server caps the page below the request
        return None

    def _mdb_watched_raw(self):
        if self._mdb_watched_cache is None:
            self._mdb_watched_cache = self._mdb_get_paginated("sync/watched")
        return self._mdb_watched_cache

    def _mdb_watched_movies(self):
        raw = self._mdb_watched_raw()
        if raw is None:
            return None
        result = {}
        for item in raw.get("movies") or []:
            tmdb_id = ((item.get("movie") or {}).get("ids") or {}).get("tmdb")
            if tmdb_id:
                result[str(tmdb_id)] = int(tmdb_id)
                self._note_stamp("movie", str(tmdb_id), item.get("last_watched_at"))
        return result

    def _mdb_watched_episodes(self):
        """{'show:season:number': show_tmdb_id}. Whole-show / whole-season marks have no episode rows and so do
        not appear here; season 0 (specials) is not bridged."""
        raw = self._mdb_watched_raw()
        if raw is None:
            return None
        result = {}
        for item in raw.get("episodes") or []:
            episode = item.get("episode") or {}
            show = episode.get("show") if isinstance(episode.get("show"), dict) else {}
            tmdb_id = (show.get("ids") or {}).get("tmdb")
            season, number = episode.get("season"), episode.get("number")
            if not tmdb_id or not season or number is None:
                continue
            key = f"{tmdb_id}:{season}:{number}"
            result[key] = int(tmdb_id)
            self._note_stamp("episode", key, item.get("last_watched_at"))
        return result

    def _mdb_list_ids(self, path):
        """GET list endpoint -> {'movie:<id>' / 'show:<id>': tmdb_id}, or None if the read failed. Handles both
        the flat watchlist shape ({"id": tmdb}) and the nested Trakt-style one (sync/collection)."""
        raw = self._mdb_get_paginated(path)
        if raw is None:
            return None
        result = {}

        def add(media, tmdb_id):
            if tmdb_id:
                result[f"{media}:{tmdb_id}"] = int(tmdb_id)

        for item in raw.get("movies") or []:
            add("movie", item.get("id") or ((item.get("movie") or {}).get("ids") or {}).get("tmdb"))
        for item in raw.get("shows") or []:
            add("show", item.get("id") or ((item.get("show") or {}).get("ids") or {}).get("tmdb"))
        return result

    # endregion

    # region Simkl readers (live, activity-gated)

    # Simkl views: {'movies': {tmdb: [status, last_watched_at]}, 'shows': {tmdb: [status, last_watched_at]},
    #   'anime': [tmdb of anime shows], 'ep_yes': {'show:season:number': show tmdb} (every episode Simkl counts as
    #   watched, including synthetic rows for completed shows), 'ep_real': {key: watched_at} (episodes the user
    #   actually recorded, the only ones that may go to Trakt history), 'anime_eps': {AniList id: {'tmdb': id, 'eps':
    # {number inside the entry: watched_at}}} (Simkl's anime episodes, mapped to TMDb numbers at use - see
    # _anime_mapped), 'anime_status': {AniList id: status}, 'anime_synth': {AniList id: {'tmdb': id, 'eps': {number: ''}}}
    # (episodes Simkl holds only as bulk-marked rows), 'anime_loaded': whether the anime episodes were read}.
    # Shows = the shows bucket plus the anime bucket (statuses; the anime episodes go on from 'anime_eps').

    def _simkl_get_ok(self, path, **params):
        """Returns (ok, data): ok is False for a failed request; a null body is an empty bucket (Simkl answers
        that way for a bucket with nothing in it) and comes back as (True, None)."""
        try:
            return True, self._api("simkl").get_json_or_raise(path, timeout=_READ_TIMEOUT, **params)
        except Exception as e:
            g.log(f"bridgeSync: simkl {path} read failed: {e}", "warning")
            return False, None

    def _simkl_activity(self):
        """Simkl's top-level activity stamp (GET /sync/activities, cheap), or None if the request failed."""
        ok, data = self._simkl_get_ok("sync/activities")
        stamp = data.get("all") if ok and isinstance(data, dict) else None
        return stamp if isinstance(stamp, str) and stamp else None

    def _simkl_load(self):
        """Reads Simkl's library (4 requests, 5 with crosssync.anime on). None if any request failed - never a partial view."""
        full = {"extended": "full", "episode_watched_at": "yes"}
        anime_on = self._anime_reads()
        plan = [
            ("movies", "sync/all-items/movies/", {}),
            ("yes", "sync/all-items/shows/", {**full, "include_all_episodes": "yes"}),
            ("real", "sync/all-items/shows/", {**full, "include_all_episodes": "original"}),
            ("anime", "sync/all-items/anime/", {**full, "include_all_episodes": "original"} if anime_on else {}),
        ]
        if anime_on:
            plan.append(("anime_all", "sync/all-items/anime/", {**full, "include_all_episodes": "yes"}))  # also the bulk-marked rows
        reads = {}
        for name, path, params in plan:
            ok, data = self._simkl_get_ok(path, **params)
            if not ok or not (data is None or isinstance(data, dict)):
                g.log(f"bridgeSync: Simkl {path} read failed - skipping Simkl this cycle", "info")
                return None
            reads[name] = data or {}
        views = {
            "movies": {},
            "shows": {},
            "anime": [],
            "ep_yes": {},
            "ep_real": {},
            "anime_eps": {},
            "anime_status": {},
            "anime_synth": {},
            "anime_loaded": anime_on,
        }
        for item in reads["movies"].get("movies") or []:
            tmdb_id = ((item.get("movie") or {}).get("ids") or {}).get("tmdb")
            if tmdb_id:
                views["movies"][str(tmdb_id)] = [item.get("status"), item.get("last_watched_at")]
        for item in reads["anime"].get("anime") or []:
            media = item.get("show") or item.get("movie") or item
            tmdb_id = (media.get("ids") or {}).get("tmdb")
            self._simkl_anime_episodes(views, item, media)
            if not tmdb_id:
                continue
            if item.get("anime_type") == "movie" or "movie" in item:
                views["movies"][str(tmdb_id)] = [item.get("status"), item.get("last_watched_at")]
            else:
                views["shows"][str(tmdb_id)] = [item.get("status"), item.get("last_watched_at")]
                views["anime"].append(str(tmdb_id))
        for item in (reads.get("anime_all") or {}).get("anime") or []:
            # episodes Simkl holds only as bulk-marked rows (an entry completed in one go): watched for "is it on Simkl", never sent on
            media = item.get("show") or item.get("movie") or item
            ids = media.get("ids") or {}
            if item.get("anime_type") == "movie" or "movie" in item:
                continue
            try:
                anilist_id = int(ids.get("anilist"))
            except (TypeError, ValueError):
                continue
            real = (views["anime_eps"].get(str(anilist_id)) or {}).get("eps") or {}
            extra = {
                str(e["number"]): ""
                for s in item.get("seasons") or []
                for e in s.get("episodes") or []
                if e.get("number") is not None and str(e["number"]) not in real
            }
            if extra:
                views["anime_synth"][str(anilist_id)] = {"tmdb": ids.get("tmdb"), "eps": extra}
        for name, target in (("yes", "ep_yes"), ("real", "ep_real")):
            for item in reads[name].get("shows") or []:
                tmdb_id = ((item.get("show") or {}).get("ids") or {}).get("tmdb")
                if not tmdb_id:
                    continue
                if name == "yes":
                    views["shows"][str(tmdb_id)] = [item.get("status"), item.get("last_watched_at")]
                for season in item.get("seasons") or []:
                    if not season.get("number"):  # season 0 (specials) is not bridged
                        continue
                    for episode in season.get("episodes") or []:
                        if episode.get("number") is None:
                            continue
                        key = f"{tmdb_id}:{season['number']}:{episode['number']}"
                        views[target][key] = str(tmdb_id) if name == "yes" else (episode.get("watched_at") or "")
        return views

    @staticmethod
    def _simkl_anime_episodes(views, item, media):
        """Keeps the episodes Simkl really recorded for one anime entry, as numbered INSIDE the entry:
        views["anime_eps"] = {AniList id: {"tmdb": Simkl's TMDb id or None, "eps": {number: watched_at}}}. They are mapped to
        TMDb numbers every cycle (_anime_mapped), not here, so a corrected Fribb index takes effect without re-reading Simkl."""
        if item.get("anime_type") == "movie" or "movie" in item:
            return
        ids = media.get("ids") or {}
        try:
            anilist_id = int(ids.get("anilist"))
        except (TypeError, ValueError):
            return
        views["anime_status"][str(anilist_id)] = item.get("status")  # every entry, also the ones with no watched episodes
        eps = {}
        for season in item.get("seasons") or []:
            for episode in season.get("episodes") or []:
                if episode.get("number") is not None:
                    eps[str(episode["number"])] = episode.get("watched_at") or ""
        if eps:
            views["anime_eps"][str(anilist_id)] = {"tmdb": ids.get("tmdb"), "eps": eps}

    def _simkl_prepare(self):
        """Fills self._simkl for this run: the saved views when Simkl's activity stamp has not moved since the
        last cycle, else a fresh read. Simkl asks apps to check /sync/activities before reading lists."""
        self._simkl_prepared = True
        self._simkl = None
        self._simkl_loaded = False
        if "simkl" not in self.services:
            return
        meta = self._meta_data()
        # what Simkl held a real record for at the end of the last cycle, kept before this run's read replaces it
        self._simkl_prev_real = set(((meta.get("simkl") or {}).get("ep_real")) or ())
        stamp = self._simkl_activity()
        if stamp is None:
            g.log("bridgeSync: Simkl activity check failed - skipping Simkl this cycle", "info")
            return
        saved = meta.get("simkl")
        # views saved before the anime episodes were read (or with crosssync.anime off) cannot serve a run with it on
        if saved and meta.get("simkl_activity") == stamp and (saved.get("anime_loaded") or not self._anime_reads()):
            self._simkl = saved
            return
        self._simkl = self._simkl_load()
        self._simkl_loaded = self._simkl is not None

    def _simkl_state(self):
        if not self._simkl_prepared:
            self._simkl_prepare()
        return self._simkl

    def _simkl_finish(self):
        """End of a run: remember Simkl's views and (after our own writes) its activity stamp so the next
        cycle can skip the reads when nothing moved."""
        if not self._simkl_prepared or self._simkl is None or not self._ok:
            return
        meta = self._meta_data()
        stamp = self._simkl_activity()
        if stamp is None or self._anime_dirty:
            meta.pop("simkl_activity", None)  # unknown (or anime episodes were just written to Simkl): re-read next cycle
        else:
            meta["simkl_activity"] = stamp
        meta["simkl"] = self._simkl
        self._meta_save()

    def _simkl_watched_movies(self):
        views = self._simkl_state()
        if views is None:
            return None
        result = {}
        for tmdb_id, (status, stamp) in views["movies"].items():
            if status == "completed":
                result[tmdb_id] = int(tmdb_id)
                self._note_stamp("movie", tmdb_id, stamp)
        return result

    def _simkl_watched_episodes(self):
        views = self._simkl_state()
        if views is None:
            return None
        for key, stamp in views["ep_real"].items():
            self._note_stamp("episode", key, stamp)
        result = {k: int(v) for k, v in views["ep_yes"].items()}
        if self._anime_reads():
            mapped, _stats = self._anime_mapped()
            self._anime_coords_update()
            if self._anime_mode() == 2:
                # Simkl's anime episodes in TMDb numbering. Never put in ep_yes / ep_real (the saved views) and never a removal source
                for key, stamp in mapped.items():
                    if key not in result:
                        result[key] = int(key.split(":")[0])
                        self._anime_keys.add(key)
                        if isinstance(stamp, str) and _STAMP_RE.match(stamp):
                            self._anime_stamps[key] = stamp
        return result

    @staticmethod
    def _anime_mode():
        """crosssync.anime: 0 off, 1 log only (default), 2 on."""
        try:
            mode = int(g.get_int_setting("crosssync.anime", _ANIME_DEFAULT))
        except Exception:
            return _ANIME_DEFAULT
        return mode if 0 <= mode <= 2 else _ANIME_DEFAULT

    def _anime_mapped(self):
        """(mapped {"tmdb:season:episode": watched_at}, stats) of the anime episodes Simkl recorded, in TMDb numbering; ({}, None)
        when off or Simkl is unreadable. Computed once per run."""
        if self._anime_cache is not None:
            return self._anime_cache
        self._anime_cache = ({}, None)
        views = self._simkl_state() if self._anime_reads() else None
        entries = (views or {}).get("anime_eps")
        if not entries:
            return self._anime_cache
        try:
            from resources.lib.modules.anime import bridge_entries

            coords = {}
            self._anime_cache = bridge_entries.map_entries(entries, bridge_entries.TmdbReader(), None, coords)
            self._anime_coords.update(coords)
        except Exception as e:
            g.log(f"bridgeSync: anime episode mapping failed - {type(e).__name__}: {e}", "warning")
        return self._anime_cache

    def _anime_known(self, tmdb_id):
        """True when the Fribb anime index knows the show (an anime Simkl numbers by entry). Memoized for the run."""
        key = str(tmdb_id)
        if key not in self._anime_known_memo:
            try:
                from resources.lib.modules.anime import fribb_mapping

                self._anime_known_memo[key] = bool(fribb_mapping.bridge_tv_entries(tmdb_id))
            except Exception:
                self._anime_known_memo[key] = False
        return self._anime_known_memo[key]

    @staticmethod
    def _anime_simkl_mode():
        """crosssync.animeSimkl: 0 off, 1 log only (default), 2 on - anime episodes watched on Trakt are sent to Simkl."""
        try:
            mode = int(g.get_int_setting("crosssync.animeSimkl", _ANIME_SIMKL_DEFAULT))
        except Exception:
            return _ANIME_SIMKL_DEFAULT
        return mode if 0 <= mode <= 2 else _ANIME_SIMKL_DEFAULT

    def _anime_reads(self):
        """True when either anime setting needs Simkl's anime episodes."""
        return bool(self._anime_mode() or self._anime_simkl_mode())

    def _anime_synth_keys(self):
        """TMDb keys of the anime episodes Simkl holds only as bulk-marked rows (an entry completed in one go: the 'original' view lists no
        episodes for it although Simkl counts them watched). They are on Simkl, so the Trakt -> Simkl pass must not send them (found live
        2026-11-05 with TMDb Helper: the first entry sent was already completed 12/12 there); they never go the other way (approximate dates)."""
        if self._anime_synth_cache is not None:
            return self._anime_synth_cache
        self._anime_synth_cache = set()
        entries = (self._simkl_state() or {}).get("anime_synth")
        if entries and self._anime_reads():
            try:
                from resources.lib.modules.anime import bridge_entries

                self._anime_synth_cache = set(bridge_entries.map_entries(entries, bridge_entries.TmdbReader())[0])
            except Exception as e:
                g.log(f"bridgeSync: anime bulk-marked mapping failed - {type(e).__name__}: {e}", "warning")
        return self._anime_synth_cache

    def _anime_journal(self, rows):
        """Appends what was sent to Simkl to bridge_anime_simkl.jsonl so a bad batch can be undone exactly."""
        try:
            with open(os.path.join(g.ADDON_USERDATA_PATH, _ANIME_JOURNAL_FILE), "a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row) + "\n")
        except Exception as e:
            g.log(f"bridgeSync: anime Simkl journal not written ({type(e).__name__})", "warning")

    def _anime_simkl_sync(self, current):
        """Anime episodes watched on Trakt -> Simkl (crosssync.animeSimkl). Simkl numbers every cour from 1, so each TMDb episode is
        resolved to its entry (AniZip air date) and round-tripped through the same mapping that reads Simkl back; it goes out as
        {"anime": [{"ids": {anilist, mal}, "episodes": [{number, watched_at}]}]} with Trakt's own watch date. This is a separate pass,
        not part of the reconcile: the reconcile recorded every anime episode as "not for Simkl" long ago, so the backlog would never be
        "new" there. What Simkl already has (read back every cycle) decides what is missing, so nothing is sent twice."""
        mode = self._anime_simkl_mode()
        if not mode or not self._ok or "simkl" not in self.services:
            return
        views = self._simkl_state()
        trakt, simkl = current.get("trakt"), current.get("simkl")
        if views is None or trakt is None or simkl is None:
            return
        mapped, _stats = self._anime_mapped()
        synth = self._anime_synth_keys()
        anime_shows, shows = set(views.get("anime") or []), views.get("shows") or {}
        meta = self._meta_data()
        refused = meta.setdefault("anime_simkl_refused", {})
        unwatching = (meta.get("removals") or {}).get("watched|simkl|episode") or {}  # un-watched on Simkl, removal waiting its second run: not to be sent back
        now = time.time()
        for key in [k for k, at in refused.items() if now - at > _ANIME_REFUSED_SECONDS]:
            refused.pop(key, None)
        sent_book = meta.setdefault("anime_simkl_sent", {})
        lost = 0
        for key, at in list(sent_book.items()):
            if key in mapped or key in simkl or key in synth:
                sent_book.pop(key, None)  # read back: it landed
            elif self._simkl_loaded and now - at > 120:
                sent_book.pop(key, None)  # Simkl was read again and does not hold it as that episode: never send it again
                refused[key] = now
                lost += 1
            elif now - at > _ANIME_SENT_SECONDS:
                sent_book.pop(key, None)
        if lost:
            g.log(f"bridgeSync: {lost} anime episode(s) sent to Simkl did not read back as the same episode - not sent again for a week", "info")
        book = meta.setdefault("anime_simkl_unwatched", {})  # {key: epoch Simkl was seen to have dropped it}: not sent back, whatever crosssync.removals is
        for key in [k for k in book if k not in trakt or k in simkl or k in mapped]:
            book.pop(key, None)  # off Trakt too, or on Simkl again
        counts = {"on_trakt": 0, "present": 0, "regular_show": 0, "no_date": 0, "refused": 0, "unwatched": 0}
        cand = {}
        for key, tid in trakt.items():
            sv = str(tid)
            if not self._anime_known(tid):
                continue  # not an anime the Fribb index knows
            counts["on_trakt"] += 1
            if sv in shows and sv not in anime_shows:
                counts["regular_show"] += 1  # Simkl keeps it as an ordinary show: the normal path handles it
            elif key in simkl or key in mapped or key in synth:
                counts["present"] += 1
            elif key in refused or key in unwatching:
                counts["refused"] += 1
            elif key in book and self._tstamps.get(("episode", key), "")[:19] <= self._iso_utc(book[key] + _REMOVE_CLOCK_MARGIN):
                counts["unwatched"] += 1  # un-watched on Simkl and not played again on Trakt since: it stays un-watched there
            elif not self._tstamps.get(("episode", key)):
                counts["no_date"] += 1  # without Trakt's date Simkl would date it today
            else:
                book.pop(key, None)  # (played again on Trakt after Simkl dropped it: a new watch)
                cand[key] = int(tid)
        try:
            from resources.lib.modules.anime import bridge_entries

            tmdb, cache = bridge_entries.TmdbReader(), {}
        except Exception as e:
            g.log(f"bridgeSync: anime to Simkl unavailable - {type(e).__name__}: {e}", "warning")
            return
        status = views.get("anime_status") or {}
        out = {"later": 0, "none": 0, "dropped": 0}
        none_by_show = {}
        resolved = {}
        for key in sorted(cand):
            _, season, episode = key.split(":")
            try:
                state, found = bridge_entries.forward_entry(cand[key], int(season), int(episode), tmdb, cache)
            except Exception as e:
                g.log(f"bridgeSync: anime entry lookup {key} failed - {type(e).__name__}", "info")
                state, found = "later", None
            if state != "ok":
                out[state] += 1
                if state == "none":
                    none_by_show[cand[key]] = none_by_show.get(cand[key], 0) + 1
            elif status.get(str(found["anilist"])) in _SIMKL_DROPPED:
                out["dropped"] += 1
            else:
                resolved[key] = found
        groups = {}
        for key, found in resolved.items():
            groups.setdefault(found["anilist"], {"ids": found["ids"], "eps": []})["eps"].append((found["number"], key))
        summary = (
            f"anime on Trakt {counts['on_trakt']}: already on Simkl {counts['present']}, ordinary Simkl shows {counts['regular_show']}, "
            f"refused before {counts['refused']}, un-watched on Simkl {counts['unwatched']}, no Trakt date {counts['no_date']}; missing on Simkl {len(cand)}: "
            f"resolvable {len(resolved)} in {len(groups)} entries, later {out['later']}, no entry {out['none']}, dropped on Simkl {out['dropped']}"
        )
        if mode == 1:
            g.log(f"bridgeSync (anime to Simkl, log only): {summary}", "info")
            if none_by_show:
                top = sorted(none_by_show.items(), key=lambda kv: -kv[1])[:12]
                g.log(f"bridgeSync (anime to Simkl, log only): no entry for (TMDb show: episodes) {', '.join(f'{s}: {n}' for s, n in top)}", "info")
            return
        if not resolved:
            if cand:
                g.log(f"bridgeSync (anime to Simkl): nothing to send now - {summary}", "info")
            return
        limit = meta.get("anime_simkl_limit")  # entries per cycle; set by hand for a first small write, None = no limit
        entries = sorted(groups)
        if isinstance(limit, int) and limit > 0:
            entries = entries[:limit]
        flat = [(al, groups[al]["ids"], n, k) for al in entries for n, k in sorted(groups[al]["eps"])][:_ANIME_CYCLE_CAP]
        g.log(f"bridgeSync (anime to Simkl): sending {len(flat)} episodes of {len({f[0] for f in flat})} entries - {summary}", "info")
        sent_total = 0
        for j in range(0, len(flat), _ANIME_PUSH_CHUNK):
            part = flat[j : j + _ANIME_PUSH_CHUNK]
            by_entry = {}
            for al, ids, n, k in part:
                by_entry.setdefault(al, {"ids": ids, "episodes": []})["episodes"].append({"number": n, "watched_at": self._tstamps[("episode", k)]})
            ok, data = self._post("simkl", "sync/history", {"anime": list(by_entry.values())})
            if not ok:
                break  # no usable answer: nothing assumed, retried next cycle
            if (data.get("not_found") or {}) and any(data["not_found"].values()):
                for _, _, _, k in part:  # Simkl named something it could not match: do not send these again for a while
                    refused[k] = now
                g.log(f"bridgeSync: Simkl did not take part of an anime request ({len(part)} episodes) - not retried for a week: {self._result_text(data)}", "info")
                continue
            for al, ids, n, k in part:
                simkl[k] = int(k.split(":")[0])
                self._anime_keys.add(k)
                self._anime_coords[k] = (al, n)
                sent_book[k] = now
            self._anime_journal(
                [{"at": now, "anilist": al, "ids": ids, "number": n, "key": k, "watched_at": self._tstamps[("episode", k)]} for al, ids, n, k in part]
            )
            sent_total += len(part)
            self._anime_dirty = True
        if sent_total:
            g.log(f"bridgeSync ->Simkl: {sent_total} anime episodes", "info")
        self._meta_save()

    @staticmethod
    def _anime_removal_mode():
        """crosssync.animeRemovals: 0 off, 1 log only (default), 2 on - an anime episode un-watched on one service is un-watched on the others
        (needs crosssync.removals 3 as well; the same two-run / 3-minute / mass-vanish guards apply)."""
        try:
            mode = int(g.get_int_setting("crosssync.animeRemovals", _ANIME_REMOVALS_DEFAULT))
        except Exception:
            return _ANIME_REMOVALS_DEFAULT
        return mode if 0 <= mode <= 2 else _ANIME_REMOVALS_DEFAULT

    def _anime_coords_update(self):
        """Remembers, for the removal check, which entry and number each mapped anime key is on Simkl, and for a few days after a key leaves
        the mapping (a removal needs two runs, so the coordinates must outlive the first one). Also records, for good, the keys Simkl itself
        dropped (meta anime_simkl_unwatched): the Trakt -> Simkl pass must not send those back, whatever crosssync.removals is."""
        if self._anime_coords_done:
            return
        self._anime_coords_done = True
        meta = self._meta_data()
        prev = meta.get("anime_coords") or {}
        gone = meta.get("anime_coords_gone") or {}
        now = time.time()
        current = {k: [int(v[0]), int(v[1])] for k, v in self._anime_coords.items()}
        for key, value in prev.items():
            if key not in current and key not in gone:
                gone[key] = list(value) + [now]
        for key in list(gone):
            if key in current or now - gone[key][2] > _ANIME_COORDS_GONE_SECONDS:
                del gone[key]
        meta["anime_coords"] = current
        meta["anime_coords_gone"] = gone
        self._anime_gone = {k: (v[0], v[1]) for k, v in gone.items()}
        book = meta.setdefault("anime_simkl_unwatched", {})
        ours = (meta.get("removed_recent") or {}).get("watched|simkl|episode") or {}  # removed from Simkl by this bridge: not Simkl's own un-watch
        for key in self._anime_gone:
            if key not in book and key not in ours and self._anime_simkl_dropped(key):
                book[key] = now

    def _anime_simkl_dropped(self, key):
        """True when Simkl itself dropped this anime episode: the entry is still on the list with a watching / completed / on-hold status
        and no longer holds that episode among the episodes it recorded. Decided in the entry's own numbering, never by the TMDb key
        (a key can leave the mapping only because the index or TMDb changed)."""
        coord = self._anime_gone.get(key)
        if coord is None:
            return False
        views = self._simkl or {}
        al, n = str(coord[0]), str(coord[1])
        status = (views.get("anime_status") or {}).get(al)
        if status is None or status in _SIMKL_DROPPED or status == "plantowatch":
            return False  # off the list, dropped, or back on plan-to-watch: a status move, not an episode un-watch
        real = ((views.get("anime_eps") or {}).get(al) or {}).get("eps") or {}
        synth = ((views.get("anime_synth") or {}).get(al) or {}).get("eps") or {}
        if n in real or n in synth:
            return False  # Simkl still holds it: only the mapping changed
        meta = self._meta_data()
        had = sum(1 for v in list((meta.get("anime_coords") or {}).values()) + [list(c) for c in self._anime_gone.values()] if str(v[0]) == al)
        if not real and had > 1:
            if (al, "reset") not in self._anime_removal_logged:
                self._anime_removal_logged.add((al, "reset"))
                g.log(f"bridgeSync: Simkl anime entry {al} lost all its recorded episodes at once - looks like a status reset, not removed elsewhere", "info")
            return False
        return True

    def _anime_unwatched(self, key):
        """True when an anime episode that left the mapped view was un-watched on Simkl and crosssync.animeRemovals is On (removal_ok for Simkl)."""
        mode = self._anime_removal_mode()
        if not mode or key not in self._anime_gone or not self._anime_simkl_dropped(key):
            return False
        if mode == 1:
            if key not in self._anime_removal_logged:
                self._anime_removal_logged.add(key)
                al, n = self._anime_gone[key]
                g.log(f"bridgeSync (anime removals, log only): {key} (AniList {al} episode {n}) was un-watched on Simkl - would be removed from the other services", "info")
            return False
        return True

    def _anime_removable(self, items):
        """The anime episodes among `items` ({key: tmdb id}) that may be un-watched on Simkl: crosssync.animeRemovals = On and the key's
        entry coordinates are known from this run's reading of Simkl. Log only (1) names them and removes nothing."""
        mode = self._anime_removal_mode()
        if not items or not mode:
            return {}
        known = {k: v for k, v in items.items() if k in self._anime_coords}
        if mode == 1:
            for key in sorted(known):
                if ("to", key) not in self._anime_removal_logged:
                    self._anime_removal_logged.add(("to", key))
                    al, n = self._anime_coords[key]
                    g.log(f"bridgeSync (anime removals, log only): {key} was un-watched elsewhere - would be removed from Simkl (AniList {al} episode {n})", "info")
            return {}
        return known

    def _remove_anime_simkl(self, items):
        """Un-watches anime episodes {key: tmdb id} on Simkl by (AniList entry, number): {"anime": [{"ids": ..., "episodes": [{"number": n}]}]} to
        sync/history/remove (verified live 2026-11-05 with TMDb Helper: deleted.episodes counts them and Simkl moves the entry's status itself).
        Returns the keys done."""
        from resources.lib.modules.anime import fribb_mapping

        groups = {}
        for key in items:
            al, n = self._anime_coords[key]
            groups.setdefault(al, {"tmdb": items[key], "eps": []})["eps"].append((n, key))
        entries = []
        for al, grp in sorted(groups.items()):
            ids = {"anilist": al}
            mal = fribb_mapping.bridge_mal_id(grp["tmdb"], al)
            if mal:
                ids["mal"] = mal
            entries.append({"ids": ids, "episodes": [{"number": n} for n, _ in sorted(grp["eps"])]})
        done = set()
        for j in range(0, len(entries), 25):
            part = entries[j : j + 25]
            ok, data = self._post("simkl", "sync/history/remove", {"anime": part})
            if not ok or any((data.get("not_found") or {}).values()):
                g.log(f"bridgeSync: Simkl anime removal not confirmed - {self._result_text(data) if ok else 'no answer'}", "info")
                continue
            for entry in part:
                for episode in entry["episodes"]:
                    key = next(k for n, k in groups[entry["ids"]["anilist"]]["eps"] if n == episode["number"])
                    done.add(key)
                    (((self._simkl or {}).get("anime_eps") or {}).get(str(entry["ids"]["anilist"])) or {}).get("eps", {}).pop(str(episode["number"]), None)
        if done:
            self._anime_dirty = True
            # the bridge took these off Simkl itself: forget their entry coordinates, or the next runs would read the missing episode as
            # Simkl's own un-watch (and keep it from being sent back when it is watched on Trakt again)
            meta = self._meta_data()
            for key in done:
                for name in ("anime_coords", "anime_coords_gone", "anime_simkl_unwatched"):
                    (meta.get(name) or {}).pop(key, None)
                self._anime_gone.pop(key, None)
            g.log(f"bridgeSync xSimkl: removed {len(done)} anime episode(s)", "info")
        return done

    def _anime_log_only(self, current):
        """crosssync.anime = 1: says what mode 2 would send, changes nothing (no snapshot, no push)."""
        mapped, stats = self._anime_mapped()
        if stats is None:
            return
        parts = []
        for service in ("trakt", "mdblist"):
            have = current.get(service)
            if have is None:
                continue
            would = sorted(k for k in mapped if k not in have)
            shows = {k.split(":")[0] for k in would}
            parts.append(f"{_TARGET_NAMES[service]} {len(would)} episodes of {len(shows)} shows")
        g.log(
            f"bridgeSync (anime, log only): Simkl anime episodes {stats['episodes']}, mapped {len(mapped)} "
            f"({stats['mapped_entries']}/{stats['entries']} entries); would send: {'; '.join(parts) or 'nothing'}; "
            f"left out: no Fribb record {stats['no_record']}, not a tv season {stats['not_tv']}, show id mismatch {stats['tmdb_mismatch']}, "
            f"season missing at TMDb {stats['no_season']}, air date unconfirmed {stats['unconfirmed']}, rejected {stats['rejected']}",
            "info",
        )

    def _simkl_set(self):
        """{'movie:<id>' / 'show:<id>': id} Simkl has on plan-to-watch, or None."""
        views = self._simkl_state()
        if views is None:
            return None
        result = {}
        for kind, bucket in (("movie", "movies"), ("show", "shows")):
            for tmdb_id, (status, _) in views[bucket].items():
                if status == "plantowatch":
                    result[f"{kind}:{tmdb_id}"] = int(tmdb_id)
        return result

    def _simkl_status(self, key):
        """Simkl's status for a 'movie:<id>' / 'show:<id>' key, or None when it is not in the library."""
        views = self._simkl_state() or {}
        kind, _, tmdb_id = key.partition(":")
        entry = (views.get("movies" if kind == "movie" else "shows") or {}).get(tmdb_id)
        return entry[0] if entry else None

    # endregion

    # region Activity stamps (bridgeTrigger)

    def _activity_stamps(self):
        """{service: stamp} read FRESH (never the copies the activity syncs keep, which would hide a change). A service whose
        read failed is left out: no conclusion is drawn from it."""
        stamps = {}
        for service in sorted(self.services):
            value = None
            try:
                if service == "trakt":
                    response = self._api("trakt").get("sync/last_activities", timeout=_READ_TIMEOUT)
                    data = response.json() if response is not None and response.status_code == 200 else None
                    value = data.get("all") if isinstance(data, dict) else None
                elif service == "mdblist":
                    data = self._api("mdblist").get_json("sync/last_activities", timeout=_READ_TIMEOUT)
                    if isinstance(data, dict) and data:
                        # server_time is the server's clock and moves on every call (live-checked 2026-11-05): not an activity
                        value = json.dumps({k: v for k, v in data.items() if k not in ("expiry", "server_time")}, sort_keys=True)
                elif service == "simkl":
                    value = self._simkl_activity()
            except Exception as e:
                g.log(f"bridgeSync: {service} activity stamp read failed: {e}", "warning")
            if value:
                stamps[service] = str(value)
        return stamps

    def poll_activity(self):
        """Services whose stamp moved since the last poll / run. A service seen for the first time only sets its baseline;
        a service that moved keeps its OLD saved stamp until a run has finished (rebaseline_activity), so a failed run is
        not forgotten."""
        meta = self._meta_data()
        saved = meta.get("trigger_stamps") or {}
        stamps = self._activity_stamps()
        changed = [s for s, v in stamps.items() if s in saved and saved[s] != v]
        meta["trigger_stamps"] = {**saved, **{s: v for s, v in stamps.items() if s not in changed}}
        self._meta_save()
        return changed

    def rebaseline_activity(self):
        meta = self._meta_data()
        stamps = self._activity_stamps()
        if stamps:
            meta["trigger_stamps"] = {**(meta.get("trigger_stamps") or {}), **stamps}
            self._meta_save()

    # endregion

    # region Meta + snapshots

    def _meta_data(self):
        if self._meta is None:
            try:
                self._meta = self.db.get_meta()
            except Exception as e:
                g.log(f"bridgeSync: meta unreadable ({type(e).__name__}) - treating as empty", "warning")
                self._meta = {}
        return self._meta

    def _meta_save(self):
        try:
            self.db.set_meta(self._meta)
        except Exception as e:
            self._ok = False
            g.log(f"bridgeSync: meta not saved ({type(e).__name__}) - no further pushes this cycle", "error")

    def _reconcile(self, domain, media, current, push_fn, caps=None, skip=None, remove_fn=None, removal_ok=None):
        """current: {service: {item_key: tmdb_id} or None (read failed)} for the services that are configured.
        remove_fn(items, source, target) -> succeeded keys, removal_ok(source, key) -> bool: carry removals made
        outside Seren over to the other services (see _removals; the crosssync.removals setting decides whether
        and what).
        push_fn(items, source, target) -> (succeeded, given_up), both subsets of items.keys():
        succeeded = confirmed present on the target now; given_up = permanently unresolvable there
        (e.g. a tmdb id the target does not know) - counted as reconciled so it is not retried forever.
        Anything in neither set stays unresolved and is retried next cycle. Items are pushed as batched API
        calls per (source, target) pair, not one call per item - these libraries run into the hundreds.
        caps: {target: max items pushed to that target per cycle, across all sources}; the rest stay unresolved.
        skip(missing, source, target) -> keys that must not go to that target (counted as reconciled, and
        taken out before the cap so they cannot use its budget).
        Mutates `current` in place so a push earlier in this run is visible to later sources. An item this run
        pushed to a service is accounted for on that service's side too (its snapshot, and its `newly`) - it
        did not originate there, so it is never sent onward from there (that would launder an item past the
        filters applied to its real source).

        Trakt history is not idempotent (see module docstring), which is why a retry is only safe where the
        target answers with set-membership semantics, and why the Trakt/Simkl history pushes give up instead of
        retrying a result that does not add up."""
        if not self._ok or len(current) < 2:
            return
        snaps = {}
        try:
            for service in current:
                snaps[service] = self.db.get_snapshot(domain, service, media)
        except Exception as e:
            self._ok = False
            g.log(f"bridgeSync: snapshot store unreadable ({type(e).__name__}) - no pushes until it is fixed", "error")
            return
        budget = dict(caps or {})
        pushed = {}  # {service: {item_key: id}} put there by this run
        touched = set()
        # Removals run before the additions so a removed item is neither mistaken for "old news" nor for a new
        # addition. The meta (pending confirmations, what was just removed) is saved inside, before any addition.
        held = self._removals(domain, media, current, snaps, remove_fn, removal_ok) if remove_fn else {}
        if not self._ok:
            return
        recent = self._meta_data().get("removed_recent") or {}
        for source in list(current):
            cur = current[source]
            if cur is None:
                continue  # unreadable: snapshot untouched, nothing sourced from it
            label = f"{domain}|{source}|{media}"
            snap = snaps[source]
            # an item the bridge removed from this service that it still lists is the removal not showing yet,
            # not a new addition
            lagging = {
                k
                for k, at in (recent.get(label) or {}).items()
                if time.time() - at <= _REMOVE_RECENT_DAYS * 86400
                and not (domain == _WATCHED and self._newer_than(media, k, self._iso_utc(at)))  # played again since: new, not lagging
            }
            newly = {k: v for k, v in cur.items() if k not in snap and k not in pushed.get(source, {}) and k not in lagging}
            carried = {k: v for k, v in snap.items() if k in cur or k in held.get(source, ())}
            unresolved = set()
            for target in current:
                if target == source or not newly:
                    continue
                if current[target] is None:  # cannot tell what the target has: retry later
                    unresolved.update(newly)
                    continue
                missing = {k: v for k, v in newly.items() if k not in current[target]}
                if missing and skip:
                    skipped = set(skip(missing, source, target))
                    missing = {k: v for k, v in missing.items() if k not in skipped}
                if not missing:
                    continue
                if target in budget:
                    cap = budget[target]
                    if len(missing) > cap:
                        g.log(
                            f"bridgeSync: {label} ->{_TARGET_NAMES[target]}: {len(missing)} new, sending {cap} this cycle",
                            "info",
                        )
                        keep = dict(sorted(missing.items())[:cap])
                        unresolved.update(set(missing) - set(keep))
                        missing = keep
                    budget[target] = cap - len(missing)
                    if not missing:
                        continue
                try:
                    succeeded, given_up = push_fn(missing, source, target)
                except Exception as e:
                    succeeded, given_up = set(), set()
                    g.log(f"bridgeSync: {label} ->{_TARGET_NAMES[target]} push error: {e}", "error")
                if succeeded:
                    current[target].update({k: missing[k] for k in succeeded})
                    pushed.setdefault(target, {}).update({k: missing[k] for k in succeeded})
                    g.log(f"bridgeSync ->{_TARGET_NAMES[target]}: {len(succeeded)} {media} ({domain})", "info")
                if given_up:
                    g.log(
                        f"bridgeSync: {label} ->{_TARGET_NAMES[target]}: {len(given_up)} not accepted, giving up on them",
                        "warning",
                    )
                unresolved.update(set(missing) - set(succeeded) - set(given_up))
            snaps[source] = {**carried, **{k: v for k, v in newly.items() if k not in unresolved}}
            touched.add(source)
        for target, items in pushed.items():
            snaps[target] = {**snaps[target], **{k: v for k, v in items.items() if k in current[target]}}
            touched.add(target)
        try:
            self.db.replace_snapshots({(domain, service, media): snaps[service] for service in touched})
        except Exception as e:
            self._ok = False
            g.log(f"bridgeSync: snapshots not saved ({type(e).__name__}) - no further pushes this cycle", "error")

    # endregion

    # region Removals made outside Seren (see the module docstring)

    @staticmethod
    def _utc_now():
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def _iso_utc(epoch):
        return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def _removal_mode():
        try:
            mode = int(g.get_int_setting("crosssync.removals", _REMOVALS_DEFAULT))
        except Exception:
            return _REMOVALS_DEFAULT
        return mode if 0 <= mode <= 3 else _REMOVALS_DEFAULT

    @staticmethod
    def _removal_active(domain, mode):
        return mode in (1, 3) or (mode == 2 and domain in (_WATCHLIST, _COLLECTION))

    def _newer_than(self, media, key, since):
        """True when an item was played (on any service that still lists it, Trakt included: Seren reads Trakt live,
        so its last_watched_at is in the same table) after `since`, a UTC ISO time - the end of the last run, since
        what the bridge itself pushed during that run carries stamps up to then. The margin covers the difference
        between this computer's clock and the services'."""
        newest = max(self._stamps.get((media, key), ""), self._anime_stamps.get(key, "") if media == "episode" else "")
        if not since or not newest:
            return False
        try:
            fmt = "%Y-%m-%dT%H:%M:%S"
            return (datetime.strptime(newest[:19], fmt) - datetime.strptime(since[:19], fmt)).total_seconds() > _REMOVE_CLOCK_MARGIN
        except ValueError:
            return False

    def _removal_ok(self, domain, media):
        """removal_ok(source, key): False for a change that only looks like a removal on that service."""

        def ok(source, key):
            if source != "simkl":
                return True
            views = self._simkl or {}
            if domain == _WATCHED and media == "movie":
                entry = (views.get("movies") or {}).get(key)  # unwatched on Simkl = back on plan-to-watch (or gone)
                return entry is None or entry[0] == "plantowatch"
            if domain == _WATCHED and key in self._anime_keys:
                return False  # a mapped anime episode: its mapping can change with the index, so it never counts as a removal
            if domain == _WATCHED and key in self._anime_gone:
                return self._anime_unwatched(key)  # left the mapping: an un-watch only if Simkl itself dropped (entry, number)
            if domain == _WATCHED:
                # only an episode Simkl really recorded (the rest are synthetic rows); one already waiting for its
                # second run no longer shows in the views saved after the first
                pending = (self._meta_data().get("removals") or {}).get("watched|simkl|episode", {})
                return key in self._simkl_prev_real or key in pending
            if domain == _WATCHLIST:
                return self._simkl_status(key) is None  # a move to completed / dropped / hold is not a removal
            return True

        return ok

    def _journal(self, domain, media, source, target, items):
        """Writes what is about to be removed to bridge_removals.jsonl (service, item, the date it held) before the call."""
        try:
            path = os.path.join(g.ADDON_USERDATA_PATH, _JOURNAL_FILE)
            with open(path, "a", encoding="utf-8") as f:
                for key, tmdb_id in sorted(items.items()):
                    f.write(
                        json.dumps(
                            {
                                "at": self._utc_now(),
                                "from": source,
                                "removed_on": target,
                                "domain": domain,
                                "media": media,
                                "key": key,
                                "tmdb": tmdb_id,
                                "watched_at": self._stamps.get((media, key)),
                            }
                        )
                        + "\n"
                    )
        except Exception as e:
            g.log(f"bridgeSync: removal journal not written: {e}", "warning")

    def _journal_trim(self):
        try:
            path = os.path.join(g.ADDON_USERDATA_PATH, _JOURNAL_FILE)
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > _JOURNAL_LINES:
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(lines[-_JOURNAL_LINES:])
        except FileNotFoundError:
            pass
        except Exception as e:
            g.log(f"bridgeSync: removal journal not trimmed: {e}", "warning")

    def _finish_run(self):
        """Remembers when this run ended (the baseline for "played again since") and keeps the journal short."""
        if not self._ok:
            return
        self._meta_data()["last_run_utc"] = self._utc_now()  # the END of the run: its own pushes are not "played again"
        self._journal_trim()
        self._meta_save()

    def _removed_done(self, domain, media, source, target, done, current, snaps):
        """Bookkeeping for items just removed from `target`: out of this run's view and its snapshot, and noted so a
        service that is slow to stop listing them does not make them look like new additions."""
        label = f"{domain}|{target}|{media}"
        recent = self._meta_data().setdefault("removed_recent", {}).setdefault(label, {})
        for key in done:
            current[target].pop(key, None)
            snaps.get(target, {}).pop(key, None)
            recent[key] = time.time()
        if done:
            self._removed[target] = self._removed.get(target, 0) + len(done)
            origin = f" - removed on {_TARGET_NAMES[source]}" if source in _TARGET_NAMES else ""
            g.log(f"bridgeSync x{_TARGET_NAMES[target]}: removed {len(done)} {media} ({domain}){origin}", "info")

    def _removals(self, domain, media, current, snaps, remove_fn, removal_ok):
        """Carries removals over to the other services. Returns {source: keys that must stay in its snapshot until the
        removal is resolved}. Runs before the additions so a removed item is not mistaken for "old news" or "new"."""
        mode = self._removal_mode()
        if not self._removal_active(domain, mode):
            return {}
        meta = self._meta_data()
        pending = meta.setdefault("removals", {})
        recent = meta.setdefault("removed_recent", {})
        seen_all = meta.setdefault("removals_seen", {})  # when each key was first found missing
        before = json.dumps([pending, recent, seen_all], sort_keys=True)
        prev_run = meta.get("last_run_utc") or self._run_started
        held = {}
        if mode >= 2:
            # an item the bridge removed that its service still lists: ask again, for a few days
            for target, cur in current.items():
                label = f"{domain}|{target}|{media}"
                rec = recent.get(label)
                if not rec or cur is None:
                    continue
                for key, at in list(rec.items()):
                    if key not in cur or time.time() - at > _REMOVE_RECENT_DAYS * 86400:
                        rec.pop(key, None)
                again = {k: cur[k] for k in rec if k in cur}
                if domain == _WATCHED:
                    for key in [k for k in again if self._newer_than(media, k, self._iso_utc(rec[k]))]:
                        rec.pop(key, None)  # played again after the bridge removed it: a new watch, not a removal still showing
                        snaps.get(target, {}).pop(key, None)  # new on this service again: the additions pass carries it to the others
                        del again[key]
                        g.log(f"bridgeSync: {label}: {key} was played again after it was removed - kept", "info")
                if again:
                    self._journal(domain, media, "retry", target, again)
                    try:
                        done = remove_fn(again, "retry", target)
                    except Exception as e:
                        done = set()
                        g.log(f"bridgeSync: {label} removal retry error: {e}", "error")
                    self._removed_done(domain, media, "retry", target, done, current, snaps)
        for source, cur in current.items():
            if cur is None:
                continue  # unreadable: nothing is concluded from it
            label = f"{domain}|{source}|{media}"
            snap = snaps.get(source) or {}
            pend = pending.setdefault(label, {})
            seen = seen_all.setdefault(label, {})
            gone = {k for k in snap if k not in cur}
            if removal_ok:
                gone = {k for k in gone if removal_ok(source, k)}
            for key in [k for k in pend if k not in gone]:
                del pend[key]  # listed again, or only a status move: not a removal
            for key in [k for k in seen if k not in pend and k not in gone]:
                del seen[key]
            if not gone:
                continue
            cap = max(_REMOVE_MASS_CAP_EPISODES if media == "episode" else _REMOVE_MASS_CAP, len(snap) // 20)
            if len(gone) > cap:
                g.log(
                    f"bridgeSync: {label}: {len(gone)} items vanished at once - looks like an incomplete read, "
                    "nothing removed from the other services for it",
                    "warning",
                )
                pend.clear()
                seen.clear()
                continue
            # missing on a second run AND for long enough (a pending entry from before this check has no first-seen time: old enough)
            confirmed = {k for k in gone if k in pend and time.time() - seen.get(k, 0) >= _REMOVE_CONFIRM_SECONDS}
            for key in gone:
                pend.setdefault(key, prev_run)
                seen.setdefault(key, time.time())
            held[source] = set(gone)
            if not confirmed:
                g.log(
                    f"bridgeSync: {label}: {len(gone)} item(s) no longer listed - removed elsewhere only if still missing next run",
                    "info",
                )
                continue
            if mode == 1:
                g.log(
                    f"bridgeSync (log only): {label}: would remove {len(confirmed)} from the other services: "
                    f"{', '.join(sorted(confirmed)[:10])}",
                    "info",
                )
                continue
            unresolved = self._apply_removals(domain, media, source, confirmed, pend, current, snaps, remove_fn)
            for key in confirmed - unresolved:
                pend.pop(key, None)
                held[source].discard(key)
        if json.dumps([pending, recent, seen_all], sort_keys=True) != before:
            self._meta_save()  # before any addition, so a removal and its bookkeeping are never saved apart
        return held

    def _apply_removals(self, domain, media, source, confirmed, pend, current, snaps, remove_fn):
        """Removes the confirmed items from every other service that still lists them. Returns the keys not finished."""
        unresolved = set()
        for target, cur in current.items():
            if target == source:
                continue
            if cur is None:
                # unreadable this run: if it may still hold the item the removal is not finished, so it stays pending
                held_there = snaps.get(target) or {}
                unresolved.update(k for k in confirmed if k in held_there)
                continue
            items = {k: cur[k] for k in confirmed if k in cur}
            if domain == _WATCHED:
                newer = {k for k in items if self._newer_than(media, k, pend.get(k))}
                if newer:
                    g.log(
                        f"bridgeSync: {domain}|{target}|{media}: {len(newer)} item(s) played again on {_TARGET_NAMES[target]} "
                        f"since they were removed on {_TARGET_NAMES[source]} - kept, and sent back",
                        "info",
                    )
                    snap_target = snaps.setdefault(target, {})
                    for key in newer:
                        snap_target.pop(key, None)  # new on the target again: the additions pass sends it back
                        del items[key]
            anime_items = {}
            if target == "simkl" and media == "episode":
                # TMDb numbers are the wrong coordinates on Simkl's anime entries: those go by (entry, number) or not at all
                anime_items = self._anime_removable({k: v for k, v in items.items() if k in self._anime_keys})
                items = {k: v for k, v in items.items() if k not in self._anime_keys}
            if not items and not anime_items:
                continue
            self._journal(domain, media, source, target, {**items, **anime_items})
            done = set()
            try:
                if items:
                    done |= set(remove_fn(items, source, target) or ())
                if anime_items:
                    done |= self._remove_anime_simkl(anime_items)
            except Exception as e:
                g.log(f"bridgeSync: {domain}|{target}|{media} removal error: {e}", "error")
            self._removed_done(domain, media, source, target, done, current, snaps)
            unresolved.update((set(items) | set(anime_items)) - done)
        return unresolved

    def _forget_in_views(self, domain, media, keys):
        """After removing from Simkl: keeps the views saved for the next cycle in step with it."""
        views = self._simkl
        if views is None:
            return
        for key in keys:
            if domain == _WATCHED and media == "movie":
                views["movies"].pop(key, None)
            elif domain == _WATCHED:
                views["ep_yes"].pop(key, None)
                views["ep_real"].pop(key, None)
            else:
                kind, _, tmdb_id = key.partition(":")
                views["movies" if kind == "movie" else "shows"].pop(tmdb_id, None)

    def _trakt_force_refresh(self, domain, media):
        """Seren's own Trakt sync re-reads a category only when Trakt's activity stamp moved, and a removal may not
        move it: reset the local stamps so the next sync pass re-reads what the bridge just removed. The old date
        must not be Seren's base date (1970-01-01): all_activities holding that exact value is how Seren tells a
        first-ever sync, which would turn this into a full first-run resync with a progress dialog."""
        columns = {
            (_WATCHED, "movie"): ("movies_watched",),
            (_WATCHED, "episode"): ("shows_watched",),
            (_WATCHLIST, "movie_or_show"): ("movies_watchlisted", "shows_watchlisted"),
            (_COLLECTION, "movie_or_show"): ("movies_collected", "shows_collected"),
        }.get((domain, media), ())
        if not columns:
            return
        try:
            from resources.lib.database.trakt_sync.activities import TraktSyncDatabase

            db = TraktSyncDatabase()
            for column in (*columns, "all_activities"):
                db._update_activity_record(column, _OLD_ACTIVITY_STAMP)
        except Exception as e:
            g.log(f"bridgeSync: could not reset the Trakt activity stamps: {e}", "warning")

    def _remove_watched(self, media, items, source, target):
        """Unwatches items {key: tmdb_id} on `target`. Returns the keys that went through."""
        succeeded = set()
        path = "sync/watched/remove" if target == "mdblist" else "sync/history/remove"
        for chunk in self._chunks(items, _MDB_CHUNK if target == "mdblist" else _BATCH_SIZE):
            if media == "movie":
                payload = {"movies": [{"ids": {"tmdb": int(v)}} for _, v in sorted(chunk.items())]}
            else:
                shows = []
                for key, show_id in sorted(chunk.items()):
                    _, season, number = key.split(":")
                    shows.append(
                        {"ids": {"tmdb": int(show_id)}, "seasons": [{"number": int(season), "episodes": [{"number": int(number)}]}]}
                    )
                payload = {"shows": shows}
            ok, _data = self._post(target, path, payload)
            if not ok:
                break
            succeeded |= set(chunk)
            if target == "simkl":
                self._forget_in_views(_WATCHED, media, chunk)
        if succeeded and target == "trakt":
            self._trakt_force_refresh(_WATCHED, media)
        return succeeded

    def _remove_set(self, domain, items, source, target):
        """Takes items {'movie:<id>' / 'show:<id>': tmdb_id} off the watchlist / collection of `target`."""
        succeeded = set()
        if target == "simkl":
            path = "sync/history/remove"  # clears every status, so only an item still on plan-to-watch goes
            done_already = {k for k in items if self._simkl_status(k) != "plantowatch"}
            succeeded |= done_already
            items = {k: v for k, v in items.items() if k not in done_already}
        elif target == "trakt":
            path = f"sync/{domain}/remove"
        else:
            path = "watchlist/items/remove" if domain == _WATCHLIST else "sync/collection/remove"
        for chunk in self._chunks(items, _MDB_CHUNK if target == "mdblist" else _BATCH_SIZE):
            payload = {}
            for key, tmdb_id in sorted(chunk.items()):
                kind = "movies" if key.startswith("movie:") else "shows"
                entry = {"tmdb": int(tmdb_id)} if (target == "mdblist" and domain == _WATCHLIST) else {"ids": {"tmdb": int(tmdb_id)}}
                payload.setdefault(kind, []).append(entry)
            ok, _data = self._post(target, path, payload)
            if not ok:
                break
            succeeded |= set(chunk)
            if target == "simkl":
                self._forget_in_views(domain, "movie_or_show", chunk)
        if succeeded and target == "trakt":
            self._trakt_force_refresh(domain, "movie_or_show")
        return succeeded

    # endregion

    # region Push helpers

    @staticmethod
    def _chunks(items, size):
        keys = sorted(items)
        for i in range(0, len(keys), size):
            yield {k: items[k] for k in keys[i : i + size]}

    def _note_stamp(self, media, item_key, stamp):
        """Remembers the newest valid ISO last_watched_at seen for an item (used as watched_at on Trakt / Simkl)."""
        if not item_key or not isinstance(stamp, str) or not _STAMP_RE.match(stamp):
            return
        key = (media, str(item_key))
        if stamp > self._stamps.get(key, ""):
            self._stamps[key] = stamp

    @staticmethod
    def _count(data, media):
        """Total of added + existing + updated for one media key in a push response."""
        total = 0
        for part in ("added", "existing", "updated"):
            value = (data or {}).get(part) or {}
            value = value.get(media, 0) if isinstance(value, dict) else 0
            total += len(value) if isinstance(value, list) else (value if isinstance(value, int) else 0)
        return total

    @staticmethod
    def _not_found_ids(data, media):
        """Itemized tmdb ids from response['not_found'][media] ([{'ids': {'tmdb': N}}]); empty when the service
        only reports a count."""
        entries = ((data or {}).get("not_found") or {}).get(media)
        found = set()
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    tmdb_id = (entry.get("ids") or {}).get("tmdb") or entry.get("tmdb")
                    if tmdb_id:
                        found.add(str(tmdb_id))
        return found

    @staticmethod
    def _not_found_episode_keys(data):
        """'show:season:number' of every episode in response['not_found']['episodes'] - MDBList itemizes unmatched
        episodes as [{'season': S, 'number': N, 'show': {'ids': {'tmdb': T}}}] (live-captured 2026-10-14). Empty when
        the service only reports a count, in which case nothing can be attributed and the chunk is retried."""
        keys = set()
        entries = ((data or {}).get("not_found") or {}).get("episodes")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    tmdb_id = ((entry.get("show") or {}).get("ids") or {}).get("tmdb")
                    season, number = entry.get("season"), entry.get("number")
                    if tmdb_id and season is not None and number is not None:
                        keys.add(f"{tmdb_id}:{season}:{number}")
        return keys

    @staticmethod
    def _not_found_count(data, media):
        value = ((data or {}).get("not_found") or {}).get(media)
        return len(value) if isinstance(value, list) else (value if isinstance(value, int) else 0)

    @staticmethod
    def _result_text(data):
        """Counts only, from a push response ({'added': {'movies': 3}, 'not_found': {'movies': [..]}})."""
        parts = []
        for key in ("added", "existing", "updated", "not_found"):
            value = data.get(key) if isinstance(data, dict) else None
            if isinstance(value, dict):
                counts = {
                    k: (len(v) if isinstance(v, list) else v) for k, v in value.items() if isinstance(v, (int, list)) and v
                }
                if counts:
                    parts.append(f"{key}={counts}")
        return " ".join(parts)

    def _wait(self, seconds):
        g.wait_for_abort(seconds)

    def _simkl_pace(self):
        """Simkl locks writes per user for 20 s (a second write inside it is answered 400 rate_limit)."""
        if self._simkl_last_write:
            remaining = _SIMKL_LOCK_SECONDS - (time.monotonic() - self._simkl_last_write)
            if remaining > 0:
                self._wait(remaining)

    def _post(self, target, path, payload):
        """POSTs payload to a service. Returns (ok, data); ok False = no usable answer (an HTTP error, nothing
        assumed applied). Raw requests responses are used on purpose: Trakt's guard hands back a 4xx/429 response
        object (and None on a 403), so neither a returned object nor the parsed body alone proves success."""
        if target == "simkl":
            self._simkl_pace()
        if g.abort_requested():
            return False, {}
        try:
            response = self._api(target).post(path, payload)
        except Exception as e:
            g.log(f"bridgeSync: {_TARGET_NAMES[target]} {path} error: {e}", "error")
            return False, {}
        if target == "simkl":
            self._simkl_last_write = time.monotonic()
        if response is None or not response.ok:
            g.log(
                f"bridgeSync: {_TARGET_NAMES[target]} {path} push failed "
                f"(HTTP {getattr(response, 'status_code', 'no answer')}) - retry next cycle",
                "error",
            )
            return False, {}
        try:
            data = response.json()
        except Exception:
            data = {}
        data = data if isinstance(data, dict) else {}
        text = self._result_text(data)
        if text:
            g.log(f"bridgeSync: {_TARGET_NAMES[target]} {path} -> {text}", "info")
        return True, data

    def _push_watched_movies(self, items, source, target):
        """items {tmdb_id_str: tmdb_id}. Trakt history logs a new play per item, so a chunk whose result does
        not add up is given up on rather than retried; MDBList / Simkl are set-membership endpoints and are
        simply retried."""
        succeeded, given_up = set(), set()
        for chunk in self._chunks(items, _MDB_CHUNK if target == "mdblist" else _BATCH_SIZE):
            entries = []
            for key, tmdb_id in sorted(chunk.items()):
                entry = {"ids": {"tmdb": int(tmdb_id)}}
                stamp = self._stamps.get(("movie", key))
                if stamp and target in ("trakt", "simkl"):
                    entry["watched_at"] = stamp
                entries.append(entry)
            ok, data = self._post(target, "sync/watched" if target == "mdblist" else "sync/history", {"movies": entries})
            if not ok:
                break
            rejected = self._not_found_ids(data, "movies")
            good = {k for k, v in chunk.items() if str(v) not in rejected}
            given_up |= set(chunk) - good
            if self._count(data, "movies") >= len(good):
                succeeded |= good
            elif target in ("trakt", "simkl"):
                g.log(
                    f"bridgeSync: {_TARGET_NAMES[target]} history confirmed fewer movies than sent ({len(good)}) - not retrying",
                    "error",
                )
                given_up |= good
        return succeeded, given_up

    def _skip_episodes(self, missing, source, target):
        """Episodes that must not go to `target`: anime shows to Simkl (different numbering), and from Simkl to
        Trakt anything the user did not actually record there (synthetic rows, approximate dates)."""
        views = self._simkl or {}
        if target == "simkl":
            anime = set(views.get("anime") or [])
            shows = views.get("shows") or {}
            guard = self._anime_reads()  # an anime Simkl does not hold: TMDb numbers can land in the wrong cour there

            def is_anime(v):
                sv = str(v)
                if sv in anime:
                    return True
                return guard and sv not in shows and self._anime_known(v)

            return {k for k, v in missing.items() if is_anime(v) or shows.get(str(v), [None])[0] in _SIMKL_DROPPED}
        if source == "simkl" and target == "trakt":
            # the mapped anime episodes (_anime_keys) are real records by construction
            return {k for k in missing if k not in (views.get("ep_real") or {}) and k not in self._anime_keys}
        return set()

    def _skip_movies(self, missing, source, target):
        """A watched mark moves a Simkl movie out of its status: leave a movie the user dropped
        alone."""
        if target != "simkl":
            return set()
        movies = (self._simkl or {}).get("movies") or {}
        return {k for k in missing if (movies.get(k) or [None])[0] in _SIMKL_DROPPED}

    def _skip_watchlist(self, missing, source, target):
        """Plan-to-watch adds move an item's status: never overwrite one Simkl has in another status."""
        if target != "simkl":
            return set()
        blocked = {k for k in missing if self._simkl_status(k) not in (None, "plantowatch")}
        if blocked:
            g.log(f"bridgeSync: {len(blocked)} watchlist item(s) already in another Simkl status - left alone", "info")
        return blocked

    def _push_watched_episodes(self, items, source, target):
        """items {'show:season:number': show_tmdb_id} -> one shows[] entry per episode (both Trakt and MDBList
        process each array entry as its own directive, so repeating a show id across entries is fine)."""
        succeeded, given_up = set(), set()
        for chunk in self._chunks(items, _MDB_CHUNK if target == "mdblist" else _BATCH_SIZE):
            shows = []
            for key, show_id in sorted(chunk.items()):
                _, season, number = key.split(":")
                episode = {"number": int(number)}
                # a mapped anime episode keeps the date Simkl recorded, also when MDBList (which stores no date) is the one sending it
                stamp = self._anime_stamps.get(key) or self._stamps.get(("episode", key))
                if stamp and target in ("trakt", "simkl"):
                    episode["watched_at"] = stamp
                shows.append({"ids": {"tmdb": int(show_id)}, "seasons": [{"number": int(season), "episodes": [episode]}]})
            ok, data = self._post(target, "sync/watched" if target == "mdblist" else "sync/history", {"shows": shows})
            if not ok:
                break
            if target == "simkl":
                rejected = self._not_found_ids(data, "shows")
                sent = {k for k, v in chunk.items() if str(v) not in rejected}
            elif target == "mdblist":
                # MDBList itemizes the episodes it cannot match: those are given up (never retried), the rest count normally
                rejected = self._not_found_episode_keys(data)
                sent = {k for k in chunk if k not in rejected}
            else:
                sent = set(chunk)
            given_up |= set(chunk) - sent
            if self._count(data, "episodes") >= len(sent):
                succeeded |= sent
            elif target in ("trakt", "simkl"):
                g.log(
                    f"bridgeSync: {_TARGET_NAMES[target]} history confirmed fewer episodes than sent ({len(sent)}) - not retrying",
                    "error",
                )
                given_up |= sent
        return succeeded, given_up

    def _push_set(self, domain, items, source, target):
        """Watchlist / collection push. items {'movie:<id>' / 'show:<id>': tmdb_id}."""
        succeeded, given_up = set(), set()
        is_watchlist = domain == _WATCHLIST
        if target == "trakt":
            path = f"sync/{domain}"
        elif target == "simkl":
            path = "sync/add-to-list"  # moves an item's status; items in another status are skipped beforehand
        else:
            path = "watchlist/items/add" if is_watchlist else "sync/collection"
        for chunk in self._chunks(items, _MDB_CHUNK if target == "mdblist" else _BATCH_SIZE):
            payload = {}
            for key, tmdb_id in sorted(chunk.items()):
                kind = "movies" if key.startswith("movie:") else "shows"
                if target == "simkl":
                    entry = {"ids": {"tmdb": int(tmdb_id)}, "to": "plantowatch"}
                else:
                    entry = {"tmdb": int(tmdb_id)} if (target == "mdblist" and is_watchlist) else {"ids": {"tmdb": int(tmdb_id)}}
                payload.setdefault(kind, []).append(entry)
            ok, data = self._post(target, path, payload)
            if not ok:
                break
            if target == "simkl":
                rejected = {(m, i) for m in ("movies", "shows") for i in self._not_found_ids(data, m)}
                sent = set()
                for key, tmdb_id in chunk.items():
                    kind = "movies" if key.startswith("movie:") else "shows"
                    (given_up if (kind, str(tmdb_id)) in rejected else sent).add(key)
                if sum(self._count(data, m) for m in ("movies", "shows")) >= len(sent):
                    succeeded |= sent
                else:
                    g.log(
                        f"bridgeSync: Simkl confirmed fewer watchlist items than sent ({len(sent)}) - not retrying",
                        "error",
                    )
                    given_up |= sent
                continue
            if target == "trakt":
                rejected = {(m, i) for m in ("movies", "shows") for i in self._not_found_ids(data, m)}
                for key, tmdb_id in chunk.items():
                    kind = "movies" if key.startswith("movie:") else "shows"
                    (given_up if (kind, str(tmdb_id)) in rejected else succeeded).add(key)
                continue
            landed = sum(self._count(data, m) for m in ("movies", "shows"))
            if landed >= len(chunk):
                succeeded |= set(chunk)
            elif is_watchlist and sum(self._not_found_count(data, m) for m in ("movies", "shows")):
                # MDBList only counts rejections: read the watchlist back to see which items landed
                readback = self._mdb_list_ids("watchlist/items")
                if readback is not None:
                    for key in chunk:
                        (succeeded if key in readback else given_up).add(key)
        return succeeded, given_up

    # endregion

    # region Sync domains

    def _current(self, trakt=None, mdblist=None, simkl=None):
        """Assembles {service: dict or None} for the configured services; each argument is a zero-argument
        reader (None = the domain does not cover that service). A service that is not configured is simply
        absent; one whose read failed is present as None."""
        current = {}
        for service, reader in (("trakt", trakt), ("mdblist", mdblist), ("simkl", simkl)):
            if reader and service in self.services:
                current[service] = reader()
                if current[service] is None:
                    g.log(f"bridgeSync: {_TARGET_NAMES[service]} read failed - skipping it this cycle", "info")
        return current

    def _sync_watched_movies(self):
        current = self._current(self._trakt_watched_movies, self._mdb_watched_movies, self._simkl_watched_movies)
        self._reconcile(
            _WATCHED,
            "movie",
            current,
            self._push_watched_movies,
            caps={"trakt": _HISTORY_CAP, "simkl": _SIMKL_CAP},
            skip=self._skip_movies,
            remove_fn=lambda i, s, t: self._remove_watched("movie", i, s, t),
            removal_ok=self._removal_ok(_WATCHED, "movie"),
        )
        self._simkl_record_movies(current.get("simkl"))

    def _sync_watched_episodes(self):
        current = self._current(self._trakt_watched_episodes, self._mdb_watched_episodes, self._simkl_watched_episodes)
        self._reconcile(
            _WATCHED,
            "episode",
            current,
            self._push_watched_episodes,
            caps={"trakt": _HISTORY_CAP, "mdblist": _MDB_EPISODE_CAP, "simkl": _SIMKL_CAP},
            skip=self._skip_episodes,
            remove_fn=lambda i, s, t: self._remove_watched("episode", i, s, t),
            removal_ok=self._removal_ok(_WATCHED, "episode"),
        )
        if self._simkl is not None and current.get("simkl") is not None:
            self._simkl["ep_yes"].update({k: str(v) for k, v in current["simkl"].items() if k not in self._anime_keys})
        if self._anime_mode() == 1:
            self._anime_log_only(current)
        self._anime_simkl_sync(current)

    def _simkl_record_movies(self, current_simkl):
        """Keeps the saved Simkl views in step with what this cycle pushed to Simkl."""
        if self._simkl is None or current_simkl is None:
            return
        for tmdb_id in current_simkl:
            entry = self._simkl["movies"].get(tmdb_id)
            if not entry or entry[0] != "completed":
                self._simkl["movies"][tmdb_id] = ["completed", self._stamps.get(("movie", tmdb_id)) or ""]

    def _sync_watchlist(self):
        current = self._current(
            lambda: self._trakt_set(_WATCHLIST), lambda: self._mdb_list_ids("watchlist/items"), self._simkl_set
        )
        self._reconcile(
            _WATCHLIST,
            "movie_or_show",
            current,
            lambda i, s, t: self._push_set(_WATCHLIST, i, s, t),
            caps={"simkl": _SIMKL_CAP},
            skip=self._skip_watchlist,
            remove_fn=lambda i, s, t: self._remove_set(_WATCHLIST, i, s, t),
            removal_ok=self._removal_ok(_WATCHLIST, "movie_or_show"),
        )
        if self._simkl is not None and current.get("simkl") is not None:
            for key in current["simkl"]:
                kind, _, tmdb_id = key.partition(":")
                bucket = self._simkl["movies" if kind == "movie" else "shows"]
                bucket.setdefault(tmdb_id, ["plantowatch", ""])

    def _sync_collection(self):
        """Trakt <-> MDBList only - Simkl has no collection endpoint."""
        current = self._current(lambda: self._trakt_set(_COLLECTION), lambda: self._mdb_list_ids("sync/collection"))
        self._reconcile(
            _COLLECTION,
            "movie_or_show",
            current,
            lambda i, s, t: self._push_set(_COLLECTION, i, s, t),
            remove_fn=lambda i, s, t: self._remove_set(_COLLECTION, i, s, t),
            removal_ok=self._removal_ok(_COLLECTION, "movie_or_show"),
        )

    # endregion

    # region Progress (one-directional Trakt -> others, idempotent, no snapshot)

    def _get_raw_json(self, url):
        """TraktAPI.get_json() normalizes responses (_handle_response), which flattens/renames fields -
        _progress_payloads() below is built against Trakt's raw un-normalized movie/show/episode.ids.tmdb +
        episode.season/number shape (verified against modules/player.py's own request builders), so this
        bypasses normalization instead of adapting the extraction."""
        response = self._api("trakt").get(url)
        if response is None:
            return None
        try:
            return response.json()
        except (ValueError, AttributeError) as e:
            g.log(f"bridgeSync: failed to parse raw Trakt JSON for {url}: {e}", "error")
            return None

    def _trakt_playback(self, kind):
        """Trakt's resume points ('movies' / 'episodes') as a list of raw rows, or None when the read failed (an
        error body, not a list, must not look like 'no resume points')."""
        data = self._get_raw_json(f"sync/playback/{kind}")
        return data if isinstance(data, list) else None

    def _resume_refused(self, row):
        """True when Simkl refused this exact resume point (same Trakt paused_at) on the last runs and a day has not passed."""
        rec = (self._meta_data().get("simkl_resume_failed") or {}).get(f"{row['media']}:{row['key']}")
        return bool(
            rec and rec[0] == (row["paused_at"] or "") and rec[1] >= _RESUME_FAIL_RUNS and time.time() - rec[2] < _RESUME_FAIL_SECONDS
        )

    def _resume_note(self, row, ok):
        """Remember a Simkl resume post that got no usable answer (and forget it once it works), so an item Simkl does not
        know is not posted again on every run. Entries older than a week go. Saved with the meta at the end of the run."""
        now = time.time()
        book = self._meta_data().setdefault("simkl_resume_failed", {})
        for old in [k for k, v in book.items() if now - v[2] > 7 * 86400]:
            del book[old]
        key = f"{row['media']}:{row['key']}"
        if ok:
            book.pop(key, None)
            return
        rec = book.get(key)
        if rec and rec[0] == (row["paused_at"] or ""):
            rec[1] += 1
            rec[2] = now
        else:
            book[key] = [row["paused_at"] or "", 1, now]

    @staticmethod
    def _resume_due(have, paused_at):
        """Whether a Trakt resume point should go to a target. `have` is the paused_at of the target's resume point for
        the item (None = it has none, False = it has one without a time)."""
        if have is None:
            return True  # the target holds none (or it expired): send
        if have is False or not isinstance(paused_at, str) or not _STAMP_RE.match(paused_at):
            return False  # cannot tell which is newer: leave what the target holds
        return paused_at[:19] > str(have)[:19]

    @staticmethod
    def _note_have(have, key, at):
        if not key[1] or key[1] == "None":
            return
        if isinstance(at, str) and _STAMP_RE.match(at):
            prev = have.get(key)
            if not isinstance(prev, str) or at > prev:
                have[key] = at
        else:
            have.setdefault(key, False)

    def _mdb_playback(self):
        """MDBList's resume points as {('movie', tmdb) / ('episode', show_tmdb, season, number): paused_at}, or None."""
        try:
            data = self._api("mdblist").get_json("sync/playback", timeout=_READ_TIMEOUT)
        except Exception as e:
            g.log(f"bridgeSync: mdblist sync/playback read failed: {e}", "warning")
            return None
        if isinstance(data, dict):
            data = data.get("items")
        if not isinstance(data, list):
            return None
        have = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            at = item.get("paused_at") or item.get("updated_at")
            if item.get("type") == "episode" or item.get("episode"):
                episode = item.get("episode") or {}
                tmdb_id = ((item.get("show") or {}).get("ids") or {}).get("tmdb")
                season, number = episode.get("season"), episode.get("number")
                if season is None or number is None:
                    continue
                self._note_have(have, ("episode", str(tmdb_id), int(season), int(number)), at)
            else:
                self._note_have(have, ("movie", str(((item.get("movie") or {}).get("ids") or {}).get("tmdb"))), at)
        return have

    def _simkl_playback(self):
        """Simkl's resume points as {('movie', tmdb) / ('show', tmdb): paused_at} (Simkl keeps one per show), or None."""
        ok, data = self._simkl_get_ok("sync/playback")
        if not ok:
            return None
        data = [] if data is None else data
        if isinstance(data, dict):
            data = data.get("items")
        if not isinstance(data, list):
            return None
        have = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            at = item.get("paused_at")
            if item.get("movie") or item.get("type") == "movie":
                self._note_have(have, ("movie", str(((item.get("movie") or {}).get("ids") or {}).get("tmdb"))), at)
            else:
                media = item.get("show") or item.get("anime") or {}
                self._note_have(have, ("show", str((media.get("ids") or {}).get("tmdb"))), at)
        return have

    def _progress_row(self, media_type, entry):
        """One Trakt resume point as a dict (the two payloads plus what the checks below need), or None."""
        built = self._progress_payloads(media_type, entry)
        if not built:
            return None
        mdb_payload, simkl_payload = built
        paused_at = entry.get("paused_at")
        if media_type == "movie":
            tmdb_id = str(((entry.get("movie") or {}).get("ids") or {}).get("tmdb"))
            return {
                "media": "movie",
                "key": tmdb_id,
                "show": None,
                "mdb_have": ("movie", tmdb_id),
                "simkl_have": ("movie", tmdb_id),
                "paused_at": paused_at,
                "progress": simkl_payload["progress"],
                "mdblist": mdb_payload,
                "simkl": simkl_payload,
            }
        show_id = str(((entry.get("show") or {}).get("ids") or {}).get("tmdb"))
        season, number = int(entry["episode"]["season"]), int(entry["episode"]["number"])
        return {
            "media": "episode",
            "key": f"{show_id}:{season}:{number}",
            "show": show_id,
            "mdb_have": ("episode", show_id, season, number),
            "simkl_have": ("show", show_id),
            "paused_at": paused_at,
            "progress": simkl_payload["progress"],
            "mdblist": mdb_payload,
            "simkl": simkl_payload,
        }

    def _finished_elsewhere(self, row, threshold):
        """True when the item is already watched on a service (any, Trakt included) and the resume point is either
        no older than that watch, or at or beyond the target's own watched threshold. Trakt marks an item watched
        from 80 % while a target may do so from less, so Trakt keeps the resume point of an item the target already
        counts as watched; sent on, it would put the finished item back "in progress" there. An item watched only
        before the Trakt point (a rewatch under way) keeps its resume point."""
        stamp = self._stamps.get((row["media"], row["key"]))
        if not stamp:
            return False
        paused_at = row["paused_at"]
        if isinstance(paused_at, str) and _STAMP_RE.match(paused_at) and stamp[:19] >= paused_at[:19]:
            return True
        try:
            return float(row["progress"]) >= threshold
        except (TypeError, ValueError):
            return False

    def _sync_progress(self):
        """Trakt resume points -> MDBList and Simkl (the reverse is not possible: Trakt's playback is read-only)."""
        if "trakt" not in self.services or not (g.get_setting("trakt.auth") and g.get_bool_setting("trakt.enabled", False)):
            return
        if "mdblist" not in self.services and "simkl" not in self.services:
            return
        try:
            movies = self._trakt_playback("movies")
            episodes = self._trakt_playback("episodes")
        except Exception as e:
            g.log(f"bridgeSync: progress read failed: {e}", "error")
            return
        if movies is None or episodes is None:
            g.log("bridgeSync: Trakt resume points could not be read - none sent this cycle", "info")
            return
        if movies:
            g.log(f"bridgeSync: trakt playback movie entry keys: {sorted(movies[0].keys())}", "debug")
        if episodes:
            g.log(f"bridgeSync: trakt playback episode entry keys: {sorted(episodes[0].keys())}", "debug")

        rows = []
        for media_type, entries in (("movie", movies), ("episode", episodes)):
            for entry in entries:
                if isinstance(entry, dict):
                    row = self._progress_row(media_type, entry)
                    if row:
                        rows.append(row)

        # A resume point the target already holds, or holds newer, is left alone: sending it again would overwrite
        # progress made there since. A target whose resume points cannot be read is skipped this run.
        failed = {"mdblist": 0, "simkl": 0}  # a post that got no usable answer: counted and logged, never silent
        sends = {"mdblist": [], "simkl": []}
        if "mdblist" in self.services:
            have = self._mdb_playback()
            if have is None:
                g.log("bridgeSync: MDBList resume points could not be read - none sent to it this cycle", "info")
            else:
                threshold = g.get_int_setting("mdblist.playCountMinimumPercent", 80)
                sends["mdblist"] = [
                    r
                    for r in rows
                    if not self._finished_elsewhere(r, threshold) and self._resume_due(have.get(r["mdb_have"]), r["paused_at"])
                ]
        if "simkl" in self.services:
            have = self._simkl_playback()
            if have is None:
                g.log("bridgeSync: Simkl resume points could not be read - none sent to it this cycle", "info")
            else:
                threshold = g.get_int_setting("simkl.playCountMinimumPercent", 80)
                # Simkl keeps one resume point per show, so of a show's episodes only the one Trakt saved last goes
                # to it (sent in turn, the last of them would win whichever was newest)
                newest = {}
                chosen = []
                for r in rows:
                    if self._finished_elsewhere(r, threshold):
                        continue
                    if r["media"] == "movie":
                        chosen.append(r)
                    elif r["show"] not in newest or (r["paused_at"] or "") > (newest[r["show"]]["paused_at"] or ""):
                        newest[r["show"]] = r
                chosen.extend(newest.values())
                due = [r for r in chosen if self._resume_due(have.get(r["simkl_have"]), r["paused_at"])]
                refused = [r for r in due if self._resume_refused(r)]
                if refused:
                    g.log(
                        f"bridgeSync: {len(refused)} Trakt resume point(s) not sent to Simkl - it refused them on the last runs "
                        f"and they have not changed (tried again in a day)",
                        "info",
                    )
                sends["simkl"] = sorted(
                    (r for r in due if r not in refused),
                    key=lambda r: r["paused_at"] or "",
                    reverse=True,
                )[:_SIMKL_PROGRESS_CAP]

        for target in ("mdblist", "simkl"):
            for row in sends[target]:
                ok, _data = self._post(target, "scrobble/pause", row[target])
                failed[target] += not ok
                if target == "simkl":
                    self._resume_note(row, ok)
            if sends[target]:
                g.log(f"bridgeSync ->{_TARGET_NAMES[target]}: {len(sends[target])} progress", "info")
            if failed[target]:
                g.log(f"bridgeSync: {failed[target]} {_TARGET_NAMES[target]} resume post(s) got no usable answer", "warning")

    @staticmethod
    def _progress_payloads(media_type, entry):
        """(mdblist_payload, simkl_payload) for one Trakt playback row, or None. Payload shapes verified against
        modules/player.py's own _build_mdblist_object/_build_simkl_object (the scrobbler's already-live-tested
        request builders), not assumed from docs - MDBList and Simkl nest the episode identity differently
        (show.season.episode vs a sibling top-level episode key) and it would be easy to get this wrong by
        treating them as interchangeable."""
        progress = entry.get("progress")
        if progress is None:
            return None
        # MDBList rejects progress values with more than 5 total digits (e.g. Trakt's raw 37.7697 -> 400 "no
        # more than 5 digits in total") - round once, upfront, for both payloads. Guarded because round() is
        # the first numeric use of progress here - a non-numeric value would otherwise raise uncaught and abort
        # the rest of this cycle's loop.
        try:
            progress = round(progress, 2)
        except TypeError:
            return None

        if media_type == "movie":
            tmdb_id = ((entry.get("movie") or {}).get("ids") or {}).get("tmdb")
            if not tmdb_id:
                return None
            return (
                {"movie": {"ids": {"tmdb": tmdb_id}}, "progress": progress},
                {"progress": progress, "movie": {"ids": {"tmdb": tmdb_id}}},
            )
        episode = entry.get("episode") or {}
        show_tmdb_id = ((entry.get("show") or {}).get("ids") or {}).get("tmdb")
        season = episode.get("season")
        number = episode.get("number")
        if not show_tmdb_id or season is None or number is None:
            return None
        return (
            {
                "show": {
                    "ids": {"tmdb": show_tmdb_id},
                    "season": {"number": season, "episode": {"number": number}},
                },
                "progress": progress,
            },
            {
                "progress": progress,
                "show": {"ids": {"tmdb": show_tmdb_id}},
                "episode": {"season": season, "number": number},
            },
        )

    # endregion


# region Legacy reader shared with the calendars


def _read_mdblist_watchlist():
    """Paginates explicitly (offset/limit, no cursor - same shape as
    sync/collection) because the server silently caps limit at 1000
    regardless of what's requested (confirmed live: requesting 5000 still
    echoes back limit:1000), so a watchlist past 1000 items would otherwise
    only ever see its first page. Used by the TV/movie calendars
    (calendar_data.py, movie_calendar_data.py) as a best-effort read: a failed
    page returns what was read so far. The bridge itself does NOT use this - it
    reads strictly (a partial read there would shrink its snapshot)."""
    from resources.lib.indexers.mdblist import MDBListAPI

    api = MDBListAPI()
    current = {}
    offset = 0
    limit = 1000  # mdblist's actual max page size for watchlist/items (server-capped, confirmed live)
    for _ in range(50):  # safety cap well above any realistic page count
        data = api.get_json("watchlist/items", offset=offset, limit=limit)
        if data is None:
            g.log("bridgeSync: mdblist watchlist read failed mid-pagination, returning partial result", "warning")
            break
        for entry in data.get("movies") or []:
            tmdb_id = entry.get("id")
            if tmdb_id:
                current[f"movie:{tmdb_id}"] = tmdb_id
        for entry in data.get("shows") or []:
            tmdb_id = entry.get("id")
            if tmdb_id:
                current[f"show:{tmdb_id}"] = tmdb_id
        if not (data.get("pagination") or {}).get("has_more"):
            break
        offset += limit
    return current


# endregion
