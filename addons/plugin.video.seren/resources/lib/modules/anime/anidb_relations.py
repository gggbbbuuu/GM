"""AniDB Related Anime — sequel/prequel/side-story navigation.

get_related_anime(anidb_id) parses <relatedanime> from the cached AniDB XML
(via anidb_data.py — no extra API call) and resolves each related AniDB ID to
IMDB/TMDb IDs via the local Fribb index (instant, offline) and a Trakt ID via Trakt's TMDb lookup.

Result cached in SQLite anime_relations table (30-day TTL).
Returns [] on failure — never raises.
"""

import json

from resources.lib.modules.globals import g

_RELATION_PRIORITY = {
    "Sequel": 0,
    "Prequel": 1,
    "Side Story": 2,
    "Parent Story": 3,
    "Alternative Version": 4,
    "Summary": 5,
    "Other": 6,
}


def get_related_anime(anidb_id):
    """Return related anime for a given AniDB ID.

    Args:
        anidb_id: AniDB anime ID (int)

    Returns:
        list of dicts sorted by relation type:
        [{'anidb_id': int, 'relation_type': str, 'title': str,
          'trakt_id': int|None, 'imdb_id': str|None,
          'themoviedb_id': int|None}, ...]
        Returns [] if no relations or on failure.
    """
    if not anidb_id:
        return []

    # 1. SQLite cache
    cached = _get_cached(anidb_id)
    if cached is not None:
        return cached

    # 2. Parse from AniDB full data (shared XML, no extra API call)
    relations = _parse_relations(anidb_id)

    # 3. Resolve IDs for each related anime
    resolved = []
    for rel in relations:
        related_id = rel.get("anidb_id")
        if not related_id:
            continue
        ids = _resolve_ids(related_id)
        resolved.append({
            "anidb_id": related_id,
            "relation_type": rel.get("relation_type", "Other"),
            "title": rel.get("title", ""),
            "trakt_id": ids.get("trakt_id"),
            "imdb_id": ids.get("imdb_id"),
            "themoviedb_id": ids.get("themoviedb_id"),
        })

    # Sort by relation priority
    resolved.sort(key=lambda x: _RELATION_PRIORITY.get(x["relation_type"], 99))

    _set_cached(anidb_id, resolved)
    g.log(f"AniDB relations: {len(resolved)} related anime for anidb_id={anidb_id}", "debug")
    return resolved


# ── Private ───────────────────────────────────────────────────────────────────

def _parse_relations(anidb_id):
    """Parse <relatedanime> from AniDB XML via anidb_data shared cache."""
    try:
        import xml.etree.ElementTree as ET
        from resources.lib.modules.anime.anidb_data import get_anidb_data, _fetch_xml

        # anidb_data caches the parsed dict — we need raw XML for <relatedanime>
        # which isn't included in the parsed dict. Fetch raw XML directly.
        xml_text = _fetch_xml(anidb_id)
        if not xml_text:
            return []

        root = ET.fromstring(xml_text)
        if root.tag == "error":
            return []

        related_el = root.find("relatedanime")
        if related_el is None:
            return []

        relations = []
        for anime_el in related_el.findall("anime"):
            try:
                rel_id = int(anime_el.get("id", 0))
            except (ValueError, TypeError):
                continue
            if not rel_id:
                continue
            relation_type = anime_el.get("type", "Other")
            title = (anime_el.text or "").strip()
            relations.append({
                "anidb_id": rel_id,
                "relation_type": relation_type,
                "title": title,
            })
        return relations

    except Exception as e:
        g.log(f"AniDB relations parse failed (anidb_id={anidb_id}): {e}", "debug")
        return []


def _resolve_ids(anidb_id):
    """Resolve AniDB ID to IMDB/TMDb IDs via the Fribb index, and to a Trakt ID from the TMDb TV id.

    The Fribb list has no Trakt ids, so the Trakt id comes from Trakt's TMDb ID lookup (cached, needs
    no Trakt login).  Only an entry with a TMDb TV id is looked up, as a show: TMDb movie ids share
    one number space with TV ids and would match an unrelated show.

    Returns dict with trakt_id, imdb_id, themoviedb_id (all may be None).
    """
    try:
        from resources.lib.modules.anime.fribb_mapping import lookup_anidb
        row = lookup_anidb(anidb_id)
        if not row:
            return {}
        trakt_id = None
        if row["themoviedb_id"]:
            try:
                from resources.lib.indexers.trakt import TraktAPI
                trakt_show = TraktAPI().search_by_tmdb_id(row["themoviedb_id"], "show")
                trakt_id = (trakt_show or {}).get("trakt_id")
            except Exception as e:
                g.log(f"AniDB relations Trakt lookup failed (tmdb={row['themoviedb_id']}): {e}", "debug")
        return {
            "trakt_id": trakt_id,
            "imdb_id": row["imdb_id"],
            "themoviedb_id": row["themoviedb_id"],
        }
    except Exception as e:
        g.log(f"AniDB relations ID resolve failed (anidb_id={anidb_id}): {e}", "debug")
        return {}


def _get_cached(anidb_id):
    try:
        from resources.lib.database.animeCache import AnimeCache
        return AnimeCache().get_anime_relations(anidb_id)
    except Exception:
        return None


def _set_cached(anidb_id, relations):
    try:
        from resources.lib.database.animeCache import AnimeCache
        AnimeCache().set_anime_relations(anidb_id, relations)
    except Exception:
        pass
