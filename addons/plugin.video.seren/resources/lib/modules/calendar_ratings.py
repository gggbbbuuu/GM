"""Cross-service rating enrichment for the calendar family's Simkl/MDBList
union layer (calendar_data.py/movie_calendar_data.py/tv_schedule_data.py).

Each of those three already resolves a capped (<=_UNION_CAP) set of Simkl
plan-to-watch / MDBList watchlist candidates into Trakt objects via
SimklMenus()._resolve() (a thin Trakt search/tmdb/{id} lookup, confirmed by
reading it) - so an item that appears ONLY because Simkl or MDBList surfaced
it still only ever carried a Trakt/TMDB rating, never the originating
service's own score. Nothing in Seren blended those in anywhere before this.

Deliberately scoped to the union/candidate layer only (the same existing
<=_UNION_CAP set each module already resolves), not every item a calendar
displays - extending either lookup to a module's full Trakt-sourced item set
(a whole month of movies, a whole week of shows) would be an unbounded batch
call outside anything _UNION_CAP bounds, and isn't the gap that was raised
(the complaint was specifically "a show that only appears via Simkl/MDBList
still shows a Trakt/TMDB rating", not "add extra rating sources everywhere").

No caching layer here - every calendar module in this family already makes
live Simkl/MDBList calls on every open (candidate sourcing itself), so two
more bulk calls of the same shape, bounded by the same cap, is the existing
cost profile, not a new one.
"""


def fetch_union_ratings(capped_tmdb_ids, simkl_id_by_tmdb, media_type, providers):
    """Bulk-fetches both services' own ratings for one calendar module's
    capped Simkl/MDBList union-layer candidates. Returns (mdblist_by_tmdb,
    simkl_by_tmdb), both keyed by tmdb_id (unlike Simkl's own ratings
    endpoint, which is keyed by simkl_id - reduced back to tmdb_id here via
    simkl_id_by_tmdb so every caller looks a rating up the same way it looks
    up everything else about a candidate, by tmdb_id).

    Each lookup is independently gated on its own service being configured -
    capped_tmdb_ids mixes both services' candidates together (that's the
    existing union/dedup design), so without this a Simkl-only account would
    still trigger an MDBList API call it has no key for, and vice versa.

    simkl_id_by_tmdb only covers Simkl-sourced candidates (MDBList-sourced
    ones never had a Simkl id in the first place) - a tmdb_id missing from it
    just means no Simkl rating for that candidate, not an error.
    media_type: "show" or "movie".
    """
    if not capped_tmdb_ids:
        return {}, {}

    mdblist_by_tmdb = _mdblist_ratings_by_tmdb(capped_tmdb_ids, media_type) if "mdblist" in providers else {}

    simkl_by_tmdb = {}
    if "simkl" in providers:
        simkl_ids = [simkl_id_by_tmdb[t] for t in capped_tmdb_ids if t in simkl_id_by_tmdb]
        simkl_by_id = _simkl_ratings_by_id(simkl_ids, media_type) if simkl_ids else {}
        simkl_by_tmdb = {
            t: simkl_by_id[simkl_id_by_tmdb[t]]
            for t in capped_tmdb_ids
            if t in simkl_id_by_tmdb and simkl_id_by_tmdb[t] in simkl_by_id
        }

    return mdblist_by_tmdb, simkl_by_tmdb


def pick_best_rating(simkl_rating, mdblist_rating, fallback_rating):
    """Priority: Simkl's own score, then MDBList's own score, then whatever
    Trakt/TMDB rating the item already had (unchanged behavior when neither
    union-sourced rating is available). Order mirrors how the gap was framed
    originally ("Simkl or MDBList's own rating") - arbitrary between the two
    otherwise, just needs to be one consistent, documented order rather than
    decided ad hoc per module."""
    if simkl_rating is not None:
        return simkl_rating
    if mdblist_rating is not None:
        return mdblist_rating
    return fallback_rating


def _simkl_ratings_by_id(simkl_ids, media_type):
    """Bulk Simkl community ratings for a set of the user's own plan-to-watch
    items, keyed by simkl_id (confirmed live against a real account: GET
    /ratings/{type}'s own "id" field IS ids.simkl, cross-checked against the
    same account's plantowatch response - both landed on the same ids for
    the same shows).

    user_watchlist is documented as an optional query param but is NOT -
    omitting it silently returns HTTP 200 with a literal `null` body instead
    of an error (Simkl's own apib spec footnote), so it's always passed
    explicitly here rather than left to a default. fields=ext (adds
    imdb/mal ratings) is deliberately omitted - only Simkl's own score was
    ever the ask.
    """
    if not simkl_ids:
        return {}

    from resources.lib.indexers.simkl import SimklAPI

    simkl_type = {"show": "tv", "movie": "movies"}[media_type]
    items = SimklAPI().get_json(f"ratings/{simkl_type}", user_watchlist="plantowatch")
    if not items:
        return {}

    wanted = set(simkl_ids)
    ratings = {}
    for entry in items:
        entry_id = entry.get("id")
        if entry_id in wanted:
            rating = (entry.get("simkl") or {}).get("rating")
            if rating is not None:
                ratings[entry_id] = rating
    return ratings


def _mdblist_ratings_by_tmdb(tmdb_ids, media_type):
    """Bulk MDBList scores for a set of tmdb_ids, keyed by tmdb_id - MDBList's
    Media Info Batch endpoint takes tmdb ids directly as the media_provider
    path segment, no id-translation step needed (unlike Simkl's own ratings
    endpoint). Up to 200 ids/call; _UNION_CAP=25 never approaches that limit.
    score_average is MDBList's own blended score on a 0-100 scale (confirmed
    against mdblist.apib's own example response: "score_average": 64) - every
    other rating this module family displays (Trakt's, Simkl's, TMDB's) is
    0-10, and the existing f"{rating_value:.1f}" display formatting has no
    per-source scale awareness, so this divides by 10 here rather than
    leaving each caller to remember to. Same field mdblistMenus.py already
    offers as a sort key (that use is unaffected - unrelated code path,
    untouched). 429/5xx retry is already handled at the session layer
    (mdblist.py's _CappedRetry), nothing extra needed here.

    tmdb_ids may arrive as a mix of str/int (Simkl and MDBList don't agree on
    JSON type for the same id - confirmed live elsewhere in this module
    family), so both the query and the match are done as int explicitly.
    """
    if not tmdb_ids:
        return {}

    from resources.lib.indexers.mdblist import MDBListAPI

    mdblist_type = {"show": "show", "movie": "movie"}[media_type]
    items = MDBListAPI().post_json(f"tmdb/{mdblist_type}", {"ids": [str(i) for i in tmdb_ids]})
    if not items:
        return {}

    ratings = {}
    for entry in items:
        score = entry.get("score_average")
        if score is None:
            continue
        try:
            tmdb_id = int((entry.get("ids") or {}).get("tmdb"))
        except (TypeError, ValueError):
            continue
        ratings[tmdb_id] = score / 10
    return ratings
