from resources.lib.common import tools
from resources.lib.modules.globals import g

CATALOGS = ("movie", "tv", "anime")

ANIME_PLAYBACK_PRESETS = {
    "sub": {"use_kodi": False, "audio": "Japanese", "subtitle": "English"},
    "dub": {"use_kodi": False, "audio": "English", "subtitle": "English"},
}


def normalize_catalog(catalog):
    if catalog in CATALOGS:
        return catalog
    return "movie"


def resolve_catalog_from_item_information(item_information):
    """Resolve movie / tv / anime for playback locale profiles."""
    if not item_information:
        return "movie"

    info = item_information.get("info") or {}
    mediatype = info.get("mediatype")

    if mediatype == g.MEDIA_MOVIE:
        catalog = "movie"
    elif mediatype in (g.MEDIA_SHOW, g.MEDIA_SEASON, g.MEDIA_EPISODE):
        catalog = "tv"
    else:
        return "movie"

    if tools.is_anime_by_genre(item_information):
        return "anime"
    return catalog


def apply_anime_playback_preset(preset):
    """Apply the sub/dub playback locale preset for the anime catalog. Returns True if applied."""
    key = str(preset or "").strip().lower()
    profile = ANIME_PLAYBACK_PRESETS.get(key)
    if profile is None:
        return False

    from resources.lib.modules.locale_playback import (
        set_catalog_audio,
        set_catalog_subtitle,
        set_use_kodi_defaults,
    )

    set_use_kodi_defaults("anime", profile["use_kodi"])
    set_catalog_audio("anime", profile["audio"])
    set_catalog_subtitle("anime", profile["subtitle"])
    return True
