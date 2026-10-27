"""Calendar data aggregation for the windowed airing calendar (Phase 6,
Implementation_Plan.md).

Merges Trakt's own calendar (recent + upcoming - the same two windows already
used by tvshowMenus.py's my_recent_episodes()/my_upcoming_episodes(), just
unified into one list) with shows that are only on Simkl's plan-to-watch list
or MDBList's watchlist. Those two need real per-show episode lookups, not
just an extra API call: Trakt's calendars/my/shows endpoint is scoped to
shows watched/collected/watchlisted on Trakt itself (confirmed via Trakt's
own API documentation), so a Simkl/MDBList-only show never appears there,
even once its tmdb_id is resolved to a Trakt object.

Both paths converge on the same normalized episode-row shape Seren already
uses everywhere (trakt_id, info, cast, art, args, ...) - the Trakt-calendar
path via TraktSyncDatabase.get_mixed_episode_list() (the same DB call
mixed_episode_builder() already makes), the union path via
TraktSyncDatabase.get_episode_list() per resolved show. Both read the same
episodes.info column, so a rating comes along for free on either path - no
separate enrichment step. Corrected after live-testing: info["rating"] is
Trakt's own community rating as a plain float (trakt.py's EpisodeNormalization
maps raw "rating" straight to output key "rating", a number - not a nested
{rating, votes} dict; that nested shape exists separately under the
namespaced "rating.trakt" key, which this module doesn't use). TMDB's own
rating is separately namespaced under "rating.tmdb". episodes.user_rating is
the signed-in user's own personal rating, not a community score.
"""
import datetime

from resources.lib.modules.globals import g

_UNION_CAP = 25  # hard cap on Simkl/MDBList-only shows resolved per open - each
                 # costs a live search_by_tmdb_id + get_episode_list call, not a
                 # cache hit (get_episode_list always runs _try_update_episodes()
                 # first). Past this cap, stop and log the dropped count instead
                 # of letting a large plan-to-watch/watchlist hang the window.


def get_air_date(episode):
    """Episode air date, matching list_builder.py's is_aired() fallback chain
    exactly (top-level air_date, then info.aired, then info.premiered) - Trakt's
    own normalization (trakt.py EpisodeNormalization/MixedEpisodeNormalization)
    writes the date to info.aired/info.premiered, never to a bare "air_date"
    key, confirmed against the real schema during live-testing (this function
    replaces an earlier, wrong assumption that "air_date" itself was the key,
    which silently zeroed out every date-based comparison in this module)."""
    info = episode.get("info") or {}
    return episode.get("air_date") or info.get("aired") or info.get("premiered")


def get_calendar_episodes():
    """Returns one chronologically-sorted list of normalized episode rows
    spanning recent (13 days back) through upcoming (30 days forward)."""
    from resources.lib.modules.syncGateway import configured_providers
    from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase
    from resources.lib.indexers.trakt import TraktAPI

    providers = configured_providers()
    if not providers:
        # Matches movie_calendar_data.py's/tv_schedule_data.py's own guard -
        # this module never had one (nothing to gate before now: with every
        # branch below already conditional on a specific provider, zero
        # providers meant zero API calls and an empty result regardless).
        # The Trakt-off fallback below is a real, unconditional API call
        # though, so without this guard a zero-provider user would newly
        # start seeing Trakt's public "everything airing" feed instead of
        # the empty result every other zero-provider path already gives.
        return []

    recent_start = datetime.date.today() - datetime.timedelta(days=13)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    if "trakt" in providers:
        raw_calendar_items = _fetch_raw_trakt_calendar(TraktAPI(), recent_start, tomorrow)
    else:
        # calendars/my/shows is OAuth-only (unlike movie_calendar_data.py's/
        # tv_schedule_data.py's own base layers, both calendars/all/* - public,
        # no account needed) - there's no personal-watchlist equivalent to fall
        # back to when Trakt is off, so this mirrors the other two calendars'
        # own public floor layer instead of returning nothing here. The
        # Simkl/MDBList union below already runs independent of Trakt's state
        # either way, unaffected by this branch.
        raw_calendar_items = _fetch_public_trakt_calendar(TraktAPI(), recent_start, tomorrow)
    covered_show_ids = {i["trakt_show_id"] for i in raw_calendar_items if i.get("trakt_show_id")}

    shows_db = ShowsDatabase()
    trakt_items = shows_db.get_mixed_episode_list(raw_calendar_items, hide_unaired=False, hide_watched=False) if raw_calendar_items else []
    # get_mixed_episode_list() applies the user's hide-watched / hide-specials settings and returns None
    # for every calendar item those filters drop (MetadataHandler.sort_list_items) - same guard as
    # tv_schedule_data.py; without it the sort below raises on the first dropped episode.
    trakt_items = [i for i in trakt_items if i is not None]

    candidate_tmdb_ids = {}  # dict (not set) purely to preserve first-seen order for the cap
    simkl_id_by_tmdb = {}
    # Simkl/MDBList are enrichment on top of Trakt's own calendar, not a hard dependency -
    # both helpers already degrade to [] on a transient fetch failure (get_json returns
    # None on failure, never raises), so no try/except is needed at this call site.
    if "simkl" in providers:
        for tmdb_id, simkl_id in _simkl_plantowatch_tmdb_ids():
            candidate_tmdb_ids.setdefault(tmdb_id, None)
            if simkl_id is not None:
                simkl_id_by_tmdb.setdefault(tmdb_id, simkl_id)
    if "mdblist" in providers:
        for tmdb_id in _mdblist_watchlist_tmdb_ids():
            candidate_tmdb_ids.setdefault(tmdb_id, None)

    capped_ids = list(candidate_tmdb_ids)[:_UNION_CAP]
    dropped = len(candidate_tmdb_ids) - len(capped_ids)
    if dropped > 0:
        g.log(f"calendar_data: union cap reached, dropped {dropped} Simkl/MDBList-only show(s) this open", "warning")

    extra_items = _resolve_extra_shows(capped_ids, covered_show_ids, shows_db)
    _annotate_union_ratings(extra_items, capped_ids, simkl_id_by_tmdb, providers)

    merged = trakt_items + extra_items
    merged.sort(key=lambda i: get_air_date(i) or "")
    return merged


def _annotate_union_ratings(extra_items, capped_ids, simkl_id_by_tmdb, providers):
    """Attaches _calendar_rating_override onto each Simkl/MDBList-union episode
    (never onto Trakt-sourced rows - that set never goes through
    _resolve_extra_shows(), so it never carries a _source_tmdb_id tag to
    match against). calendar_view.rating_text() prefers this over info["rating"] when
    present; mutating info["rating"] directly instead would have corrupted a
    cached, shared episode object used by unrelated features."""
    if not extra_items:
        return

    from resources.lib.modules.calendar_ratings import fetch_union_ratings, pick_best_rating

    mdblist_ratings, simkl_ratings = fetch_union_ratings(capped_ids, simkl_id_by_tmdb, "show", providers)
    if not mdblist_ratings and not simkl_ratings:
        return

    for item in extra_items:
        tmdb_id = item.pop("_source_tmdb_id", None)
        rating = pick_best_rating(simkl_ratings.get(tmdb_id), mdblist_ratings.get(tmdb_id), None)
        if rating is not None:
            item["_calendar_rating_override"] = rating


def _fetch_raw_trakt_calendar(trakt_api, recent_start, tomorrow):
    """Same two windows tvshowMenus.py already fetches - unchanged values,
    just returned as raw Trakt objects instead of being handed straight to
    mixed_episode_builder(). Hidden-shows filter matches my_recent_episodes()'s
    own (tvshowMenus.py ~L525-536); my_upcoming_episodes() doesn't apply it
    today, but a merged calendar view is one list, one filter, applied once."""
    from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase as HiddenDatabase

    recent = trakt_api.get_json(
        f"calendars/my/shows/{recent_start.strftime('%Y-%m-%d')}/14", extended="full", pull_all=True
    ) or []

    upcoming = trakt_api.get_json(
        f"calendars/my/shows/{g.datetime_to_string(tomorrow)}/30", extended="full", pull_all=True
    ) or []

    hidden_shows = HiddenDatabase().get_hidden_items("calendar", "tvshow")
    return [i for i in (recent + upcoming) if i.get("trakt_show_id") not in hidden_shows]


def _fetch_public_trakt_calendar(trakt_api, recent_start, tomorrow):
    """Trakt-off fallback covering the same combined window
    _fetch_raw_trakt_calendar() does (recent_start through tomorrow+29, 44
    days total) - calendars/all/shows is the same public, non-authenticated
    endpoint movie_calendar_data.py's own base layer already uses (confirmed
    live: still serves data with Trakt disabled), so this only replaces the
    personal-watchlist source above; the Simkl/MDBList union layer already
    runs independent of Trakt's state either way."""
    from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase as HiddenDatabase

    span_days = (tomorrow - recent_start).days + 30
    raw = trakt_api.get_json(
        f"calendars/all/shows/{recent_start.strftime('%Y-%m-%d')}/{span_days}", extended="full", pull_all=True
    ) or []

    hidden_shows = HiddenDatabase().get_hidden_items("calendar", "tvshow")
    return [i for i in raw if i.get("trakt_show_id") not in hidden_shows]


def _simkl_plantowatch_tmdb_ids():
    """Fetch+extract half of simklMenus.py's _status_shows("plantowatch") -
    deliberately not the resolve/render half, since this module needs raw
    tmdb_ids to dedupe against the Trakt set before resolving, not a rendered
    directory (_status_shows() itself calls g.cancel_directory() on empty,
    which doesn't apply here). Also reused by tv_schedule_data.py's own
    watchlist layer (same Simkl plantowatch source, same candidate-cap need).

    Returns (tmdb_id, simkl_id) pairs, not bare tmdb_ids - simkl_id is only
    ever available here, before SimklMenus._resolve() converts a candidate to
    a Trakt object and drops everything Simkl-specific; both calendar_data.py
    and tv_schedule_data.py need it to look up Simkl's own rating for a
    Simkl-sourced item afterwards. tmdb_id is normalized to int - Simkl and
    MDBList don't agree on JSON type for the same id (confirmed live
    elsewhere in this module family), and the rating lookup this feeds
    depends on consistent typing to match at all."""
    from resources.lib.indexers.simkl import SimklAPI

    page = SimklAPI().get_json("sync/all-items/shows/plantowatch")
    if page is None:
        return []
    pairs = []
    for entry in page.get("shows") or []:
        ids = (entry.get("show") or {}).get("ids") or {}
        tmdb_id = ids.get("tmdb")
        if tmdb_id is None:
            continue
        try:
            tmdb_id = int(tmdb_id)
        except (TypeError, ValueError):
            continue
        pairs.append((tmdb_id, ids.get("simkl")))
    return pairs


def _mdblist_watchlist_tmdb_ids():
    """Reuses bridgeSync's own paginated watchlist reader as-is (same
    server-side 1000-item-per-page cap applies, same as bridgeSync's own
    use) - "show:" prefixed keys only, movies aren't in scope for an airing
    calendar."""
    from resources.lib.modules.bridgeSync import _read_mdblist_watchlist

    watchlist = _read_mdblist_watchlist()
    return [tmdb_id for key, tmdb_id in watchlist.items() if key.startswith("show:")]


def _resolve_extra_shows(tmdb_ids, covered_show_ids, shows_db):
    """Resolves capped tmdb_ids to Trakt shows, reusing simklMenus.py's tested
    _resolve() (deliberately not a third copy of that logic - mdblistMenus.py
    already carries a second). Skips anything that turns out to already be
    covered by Trakt's own calendar (possible if a show is on both Trakt's
    list and Simkl's plantowatch) before paying for an episode lookup.

    seen_show_ids also catches a second case found live: Simkl and MDBList can
    reference the same real-world show under two different tmdb_ids (observed
    with an anthology series), which both survive candidate_tmdb_ids' dedup
    upstream (different dict keys) but resolve to the same trakt_show_id here
    - without this, that show's episode was added twice."""
    if not tmdb_ids:
        return []

    from resources.lib.gui.simklMenus import Menus as SimklMenus

    resolved_shows = SimklMenus()._resolve(tmdb_ids, "show")
    seen_show_ids = set(covered_show_ids)
    items = []
    for show in resolved_shows:
        trakt_show_id = show.get("trakt_id")
        if not trakt_show_id or trakt_show_id in seen_show_ids:
            continue
        seen_show_ids.add(trakt_show_id)
        episodes = shows_db.get_episode_list(trakt_show_id, hide_unaired=False) or []
        episode = _pick_relevant_episode(episodes)
        if episode:
            # Transient tag, popped by _annotate_union_ratings() - an episode
            # object carries no tmdb_id of its own (only its parent show
            # does, and that's about to go out of scope), so this is the only
            # point the association survives to the rating-lookup step.
            episode["_source_tmdb_id"] = show.get("tmdb_id")
            items.append(episode)
    return items


def _pick_relevant_episode(episodes):
    """Picks whichever of 'next unaired' or 'most recently aired' falls
    nearest today from a show's full episode list - matching what a single
    calendar row for this show should show."""
    now = g.datetime_to_string(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    dated = [(e, get_air_date(e)) for e in episodes]
    dated = [(e, d) for e, d in dated if d]
    upcoming = [(e, d) for e, d in dated if d >= now]
    if upcoming:
        return min(upcoming, key=lambda pair: pair[1])[0]
    if dated:
        return max(dated, key=lambda pair: pair[1])[0]
    return None
