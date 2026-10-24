"""
On-action cross-service mirror (Phase 7, Layer 2). Hooked into the tail end of
TraktContextMenu's existing action methods (gui/trakt_context_menu.py) - never
adds new UI. Every public function here is called AFTER the source service's
own write has already succeeded and the user has already seen a success
notification, so failures in here are logged only, never surfaced or raised -
a mirror failure must not make an already-successful primary action look
broken. Any missed mirror self-heals on the next bridgeSync pass
(modules/bridgeSync.py), which is why this layer never needs its own retry
logic.

Direct API calls only - never instantiates a target service's own sync-
database force/full-sync methods, which would re-trigger that service's own
write-and-notify path and could create a mirror-triggers-mirror echo loop.

Domain coverage mirrors the real shape of the 3 providers' existing UI, which
is asymmetric:
- Watched: all 3 services have native Mark Watched/Unwatched actions, so
  mirror_watched() is genuinely 3-way and takes a `source` argument.
- Watchlist: only Trakt has a generic Add/Remove Watchlist action (gated to
  movie/tvshow only - see TraktContextMenu._handle_watchlist_options). Simkl's
  only entry point is _simkl_set_status's plantowatch option, which is
  add-only by nature (it's a status picker, not a toggle). MDBList has no
  native watchlist UI action at all (its "Add/Remove List" buttons are
  user-named custom lists, a different feature - not mirrored here, matching
  Trakt's own custom lists having no cross-service equivalent either).
- Collection: Trakt-only UI action; Simkl has no Collection endpoint at all
  (hard API constraint). Mirrors to MDBList only.
- Rating: Simkl-only UI action (Trakt/MDBList have no rate button in this
  codebase). Mirrors to Trakt + MDBList, write-only (POST), which is why this
  is safe to ship even though the bridge's own Rating domain is deferred
  pending verification that MDBList/Simkl's ratings-read endpoints actually
  return bulk data.
"""

from resources.lib.modules.globals import g
from resources.lib.modules.syncGateway import configured_providers


def _enabled():
    return g.get_bool_setting("crosssync.enabled", False)


def _targets(source):
    if not _enabled():
        return set()
    return set(configured_providers()) - {source}


def _show_tmdb_id(item_information):
    mediatype = item_information["mediatype"]
    return item_information["tmdb_id"] if mediatype == "tvshow" else item_information["tmdb_show_id"]


def _ids_payload(item_information, extra_fields=None):
    """Nested tmdb-keyed shape shared by Trakt sync/history, MDBList
    sync/watched + sync/collection, and Simkl sync/history + sync/ratings -
    all four accept the identical {"movies"|"shows": [{"ids": {"tmdb": N},
    "seasons": [...]}]} nesting for season/episode granularity (verified
    against simkl.apib and the MDBList apib directly, not just docs prose).
    extra_fields merges into the per-item dict (e.g. {"rating": 8})."""
    mediatype = item_information["mediatype"]
    extra_fields = extra_fields or {}
    if mediatype == "movie":
        return {"movies": [{**extra_fields, "ids": {"tmdb": item_information["tmdb_id"]}}]}
    if mediatype == "tvshow":
        return {"shows": [{**extra_fields, "ids": {"tmdb": item_information["tmdb_id"]}}]}
    if mediatype == "season":
        return {
            "shows": [
                {
                    **extra_fields,
                    "ids": {"tmdb": item_information["tmdb_show_id"]},
                    "seasons": [{"number": item_information["season"]}],
                }
            ]
        }
    if mediatype == "episode":
        return {
            "shows": [
                {
                    **extra_fields,
                    "ids": {"tmdb": item_information["tmdb_show_id"]},
                    "seasons": [
                        {
                            "number": item_information["season"],
                            "episodes": [{"number": item_information["episode"]}],
                        }
                    ],
                }
            ]
        }
    return None


def _mdblist_flat_payload(item_information):
    """Flat shape required by MDBList's POST /watchlist/items/{add|remove} -
    different from _ids_payload's nested shape (verified against the MDBList
    apib directly). Movie/tvshow only - watchlist mirror never receives
    season/episode items, since Trakt's own watchlist UI is gated to
    movie/tvshow (see module docstring)."""
    mediatype = item_information["mediatype"]
    if mediatype == "movie":
        return {"movies": [{"tmdb": item_information["tmdb_id"]}]}
    if mediatype == "tvshow":
        return {"shows": [{"tmdb": item_information["tmdb_id"]}]}
    return None


def _simkl_status_payload(item_information, to_status):
    """Flat shape required by Simkl's POST /sync/add-to-list - matches
    TraktContextMenu._simkl_set_status's own payload exactly. Movie/tvshow
    only, same reasoning as _mdblist_flat_payload."""
    mediatype = item_information["mediatype"]
    if mediatype == "movie":
        return {"movies": [{"to": to_status, "ids": {"tmdb": item_information["tmdb_id"]}}]}
    if mediatype == "tvshow":
        return {"shows": [{"to": to_status, "ids": {"tmdb": item_information["tmdb_id"]}}]}
    return None


def _simkl_movie_watched(item_information):
    """True when Simkl's synced data has this movie as watched. Simkl marks a movie as unwatched when it is
    set to Plan to Watch, so a watchlist mirror must leave such a movie alone (local data, no request)."""
    from resources.lib.database.simkl_sync import SimklSyncDatabase

    return item_information["mediatype"] == "movie" and SimklSyncDatabase().is_movie_watched(
        item_information.get("tmdb_id")
    )


def _resolve_trakt_id(item_information):
    """Resolves this item's tmdb_id to a Trakt object via Trakt's ID lookup
    search (no personal OAuth required - works even when Trakt is only
    configured as a cross-sync target, not used natively). Cached by
    search_by_tmdb_id itself, so repeat lookups for the same item are free.
    Returns None if Trakt has no match."""
    from resources.lib.indexers.trakt import TraktAPI

    mediatype = item_information["mediatype"]
    is_show_level = mediatype in ("tvshow", "season", "episode")
    tmdb_id = _show_tmdb_id(item_information) if mediatype in ("season", "episode") else item_information["tmdb_id"]
    obj = TraktAPI().search_by_tmdb_id(tmdb_id, "show" if is_show_level else "movie")
    return obj.get("trakt_id") if obj else None


# region Watched (3-way, all services have a native Mark Watched/Unwatched action)


def mirror_watched(source, item_information, watched):
    for target in _targets(source):
        try:
            if target == "trakt":
                _push_watched_to_trakt(item_information, watched)
            elif target == "mdblist":
                _push_watched_to_mdblist(item_information, watched)
            elif target == "simkl":
                _push_watched_to_simkl(item_information, watched)
        except Exception as e:
            g.log(f"cross_sync: failed to mirror watched={watched} from {source} to {target}: {e}", "error")


def _push_watched_to_trakt(item_information, watched):
    from resources.lib.indexers.trakt import TraktAPI

    payload = _ids_payload(item_information)
    if payload is None:
        return
    response = TraktAPI().post_json("sync/history" if watched else "sync/history/remove", payload)
    if not response:
        g.log("cross_sync: trakt watched push got no response, skipping local write", "warning")
        return
    _write_trakt_watched_local(item_information, watched)


def _write_trakt_watched_local(item_information, watched):
    mediatype = item_information["mediatype"]
    trakt_id = _resolve_trakt_id(item_information)
    if not trakt_id:
        return
    if mediatype == "movie":
        from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

        db = TraktSyncDatabase()
        db.mark_movie_watched(trakt_id) if watched else db.mark_movie_unwatched(trakt_id)
        return

    from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

    db = TraktSyncDatabase()
    if mediatype == "episode":
        if watched:
            db.mark_episode_watched(trakt_id, item_information["season"], item_information["episode"])
        else:
            db.mark_episode_unwatched(trakt_id, item_information["season"], item_information["episode"])
    elif mediatype == "season":
        db.mark_season_watched(trakt_id, item_information["season"], 1 if watched else 0)
    elif mediatype == "tvshow":
        db.mark_show_watched(trakt_id, 1 if watched else 0)


def _push_watched_to_mdblist(item_information, watched):
    from resources.lib.indexers.mdblist import MDBListAPI

    payload = _ids_payload(item_information)
    if payload is None:
        return
    response = MDBListAPI().post_json("sync/watched" if watched else "sync/watched/remove", payload)
    if not response:
        g.log("cross_sync: mdblist watched push got no response, skipping local write", "warning")
        return
    if watched:
        from resources.lib.database.mdblist_sync import MDBListSyncDatabase

        MDBListSyncDatabase().write_watched_locally(item_information["mediatype"], item_information)


def _push_watched_to_simkl(item_information, watched):
    from resources.lib.indexers.simkl import SimklAPI

    payload = _ids_payload(item_information)
    if payload is None:
        return
    SimklAPI().post_json("sync/history" if watched else "sync/history/remove", payload)


# endregion

# region Watchlist (Trakt <-> MDBList full; Trakt/Simkl add-only per Simkl's destructive remove)


def mirror_watchlist_add_from_trakt(item_information):
    for target in _targets("trakt"):
        try:
            if target == "mdblist":
                from resources.lib.indexers.mdblist import MDBListAPI

                payload = _mdblist_flat_payload(item_information)
                if payload is not None:
                    MDBListAPI().post_json("watchlist/items/add", payload)
            elif target == "simkl":
                from resources.lib.indexers.simkl import SimklAPI

                if _simkl_movie_watched(item_information):
                    g.log(
                        f"cross_sync: movie {item_information.get('tmdb_id')} is watched on Simkl - "
                        "not moved to Plan to Watch",
                        "info",
                    )
                    continue
                payload = _simkl_status_payload(item_information, "plantowatch")
                if payload is not None:
                    SimklAPI().post_json("sync/add-to-list", payload)
        except Exception as e:
            g.log(f"cross_sync: failed to mirror watchlist-add from trakt to {target}: {e}", "error")


def mirror_watchlist_remove_from_trakt(item_information):
    """Never mirrors to Simkl - its only removal endpoint (sync/history/remove)
    clears ALL list status for an item, not just watchlist/plantowatch, so a
    remove mirror there would be destructive rather than corrective."""
    if "mdblist" not in _targets("trakt"):
        return
    try:
        from resources.lib.indexers.mdblist import MDBListAPI

        payload = _mdblist_flat_payload(item_information)
        if payload is not None:
            MDBListAPI().post_json("watchlist/items/remove", payload)
    except Exception as e:
        g.log(f"cross_sync: failed to mirror watchlist-remove from trakt to mdblist: {e}", "error")


def mirror_watchlist_add_from_simkl(item_information):
    """Called only when _simkl_set_status's to_status == "plantowatch" -
    mirrors unconditionally to both other services, matching the reference
    implementation's ItemSimklPlanToWatch._cross_sync() precedent."""
    for target in _targets("simkl"):
        try:
            if target == "trakt":
                from resources.lib.indexers.trakt import TraktAPI

                payload = _ids_payload(item_information)
                if payload is not None:
                    TraktAPI().post_json("sync/watchlist", payload)
            elif target == "mdblist":
                from resources.lib.indexers.mdblist import MDBListAPI

                payload = _mdblist_flat_payload(item_information)
                if payload is not None:
                    MDBListAPI().post_json("watchlist/items/add", payload)
        except Exception as e:
            g.log(f"cross_sync: failed to mirror watchlist-add from simkl to {target}: {e}", "error")


# endregion

# region Collection (Trakt <-> MDBList only; Simkl has no Collection endpoint)


def mirror_collection_add_from_trakt(item_information):
    if "mdblist" not in _targets("trakt"):
        return
    try:
        from resources.lib.indexers.mdblist import MDBListAPI

        payload = _ids_payload(item_information)
        if payload is not None:
            MDBListAPI().post_json("sync/collection", payload)
    except Exception as e:
        g.log(f"cross_sync: failed to mirror collection-add from trakt to mdblist: {e}", "error")


def mirror_collection_remove_from_trakt(item_information):
    if "mdblist" not in _targets("trakt"):
        return
    try:
        from resources.lib.indexers.mdblist import MDBListAPI

        payload = _ids_payload(item_information)
        if payload is not None:
            MDBListAPI().post_json("sync/collection/remove", payload)
    except Exception as e:
        g.log(f"cross_sync: failed to mirror collection-remove from trakt to mdblist: {e}", "error")


# endregion

# region Rating (Simkl-originated only; Trakt/MDBList have no rate action in this UI)


def mirror_rating_from_simkl(item_information, rating):
    for target in _targets("simkl"):
        try:
            payload = _ids_payload(item_information, {"rating": rating})
            if payload is None:
                continue
            if target == "trakt":
                from resources.lib.indexers.trakt import TraktAPI

                TraktAPI().post_json("sync/ratings", payload)
            elif target == "mdblist":
                from resources.lib.indexers.mdblist import MDBListAPI

                MDBListAPI().post_json("sync/ratings", payload)
        except Exception as e:
            g.log(f"cross_sync: failed to mirror rating from simkl to {target}: {e}", "error")


def mirror_rating_clear_from_simkl(item_information):
    for target in _targets("simkl"):
        try:
            payload = _ids_payload(item_information)
            if payload is None:
                continue
            if target == "trakt":
                from resources.lib.indexers.trakt import TraktAPI

                TraktAPI().post_json("sync/ratings/remove", payload)
            elif target == "mdblist":
                from resources.lib.indexers.mdblist import MDBListAPI

                MDBListAPI().post_json("sync/ratings/remove", payload)
        except Exception as e:
            g.log(f"cross_sync: failed to mirror rating-clear from simkl to {target}: {e}", "error")


# endregion
