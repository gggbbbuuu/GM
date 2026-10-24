import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.modules.globals import g


def browse_cast(action_args):
    item_information = tools.get_item_information(action_args)
    mediatype = action_args.get("mediatype")
    is_tv = mediatype in ("tvshow", "season", "episode")
    if mediatype in ("season", "episode"):
        tmdb_id = tools.safe_dict_get(item_information, "info", "tmdb_show_id")
    else:
        tmdb_id = tools.safe_dict_get(item_information, "info", "tmdb_id")
    if not tmdb_id:
        return

    from resources.lib.indexers.tmdb import TMDBAPI

    tmdb_api = TMDBAPI()
    endpoint = f"tv/{tmdb_id}/credits" if is_tv else f"movie/{tmdb_id}/credits"
    response = tmdb_api.get(endpoint)
    if response is None:
        return
    cast = [c for c in (response.json().get("cast") or []) if c.get("name") and c.get("id")]
    if not cast:
        return

    names = [c["name"] for c in cast]
    choice = xbmcgui.Dialog().select(g.get_language_string(31199), names)
    if choice == -1:
        return

    person = cast[choice]

    from resources.lib.indexers.trakt import TraktAPI

    trakt_person = TraktAPI().search_by_tmdb_id(person["id"], "person")
    slug = tools.safe_dict_get(trakt_person, "ids", "slug")

    action = "showsByActor" if is_tv else "movieByActor"
    url = g.create_url(g.BASE_URL, {"action": action, "action_args": slug or person["name"]})
    xbmc.executebuiltin(f'Container.Update("{url}")')
