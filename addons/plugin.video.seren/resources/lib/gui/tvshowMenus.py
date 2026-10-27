import datetime
from functools import cached_property
from urllib import parse

import xbmcgui
import xbmcplugin

from resources.lib.common import tools
from resources.lib.indexers import trakt_auth_guard
from resources.lib.modules.globals import g
from resources.lib.modules.metadataHandler import MetadataHandler

_PERIOD_ENDPOINTS = frozenset({"played", "watched", "collected", "favorited"})


class Menus:
    def __init__(self):
        self.page_limit = g.get_int_setting("item.limit")
        self.page_start = (g.PAGE - 1) * self.page_limit
        self.page_end = g.PAGE * self.page_limit

    # Cached properties to lazy load imports

    @cached_property
    def shows_database(self):
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

        return TraktSyncDatabase()

    @cached_property
    def search_history(self):
        from resources.lib.database.searchHistory import SearchHistory

        return SearchHistory()

    @cached_property
    def hidden_database(self):
        from resources.lib.database.trakt_sync.hidden import TraktSyncDatabase as HiddenDatabase

        return HiddenDatabase()

    @cached_property
    def bookmark_database(self):
        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase as BookmarkDatabase

        return BookmarkDatabase()

    @cached_property
    def trakt_api(self):
        from resources.lib.indexers.trakt import TraktAPI

        return TraktAPI()

    @cached_property
    def list_builder(self):
        from resources.lib.modules.list_builder import ListBuilder

        return ListBuilder()

    ######################################################
    # MENUS
    ######################################################

    @trakt_auth_guard
    def on_deck_shows(self):
        hidden_shows = self.hidden_database.get_hidden_items("progress_watched", "tvshow")
        bookmarked_items = [
            i
            for i in self.bookmark_database.get_all_bookmark_items("episode")
            if i["trakt_show_id"] not in hidden_shows
        ][self.page_start : self.page_end]
        self.list_builder.mixed_episode_builder(bookmarked_items, hide_watched=False)

    @staticmethod
    def discover_shows():

        g.add_directory_item(
            g.get_language_string(30004),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="popular",
            description=g.get_language_string(30416),
            menu_item=g.create_icon_dict("shows_popular", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30345),
            action="showsPopularRecent",
            description=g.get_language_string(30417),
            menu_item=g.create_icon_dict("shows_recent", g.ICONS_PATH),
        )
        if g.get_setting("trakt.auth") and g.get_bool_setting("trakt.enabled", False):
            g.add_directory_item(
                g.get_language_string(30005),
                action="showsRecommended",
                description=g.get_language_string(30418),
                menu_item=g.create_icon_dict("shows_recommended", g.ICONS_PATH),
            )
        g.add_directory_item(
            g.get_language_string(30006),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="trending",
            description=g.get_language_string(30419),
            menu_item=g.create_icon_dict("shows_trending", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30346),
            action="showsTrendingRecent",
            description=g.get_language_string(30420),
            menu_item=g.create_icon_dict("shows_recent", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30046),
            action="showsNew",
            description=g.get_language_string(30421),
            menu_item=g.create_icon_dict("shows_new", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30007),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="played",
            description=g.get_language_string(30422),
            menu_item=g.create_icon_dict("shows_played", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30008),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="watched",
            description=g.get_language_string(30423),
            menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30009),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="collected",
            description=g.get_language_string(30424),
            menu_item=g.create_icon_dict("shows_collected", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30983),
            action="genericEndpoint",
            mediatype="shows",
            endpoint="favorited",
            description=g.get_language_string(30985),
            menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30352),
            action="TrendingLists",
            mediatype="shows",
            description=g.get_language_string(30425),
            menu_item=g.create_icon_dict("list_trending", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30354),
            action="PopularLists",
            mediatype="shows",
            description=g.get_language_string(30426),
            menu_item=g.create_icon_dict("list_popular", g.ICONS_PATH),
        )
        if not g.get_bool_setting("general.hideUnAired"):
            g.add_directory_item(
                g.get_language_string(30010),
                action="genericEndpoint",
                mediatype="shows",
                endpoint="anticipated",
                description=g.get_language_string(30427),
                menu_item=g.create_icon_dict("shows_anticipated", g.ICONS_PATH),
            )

        g.add_directory_item(
            g.get_language_string(30011),
            action="showsUpdated",
            description=g.get_language_string(30428),
            menu_item=g.create_icon_dict("shows_recent", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30169),
            action="showsNetworks",
            description=g.get_language_string(30429),
            menu_item=g.create_icon_dict("shows_networks", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30171),
            action="showYears",
            description=g.get_language_string(30430),
            menu_item=g.create_icon_dict("shows_calendar", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30042),
            action="tvGenres",
            description=g.get_language_string(30431),
            menu_item=g.create_icon_dict("shows_genres", g.ICONS_PATH),
        )
        g.add_directory_item(
            g.get_language_string(30190),
            action="showsByActor",
            description=g.get_language_string(30432),
            menu_item=g.create_icon_dict("shows_actor", g.ICONS_PATH),
        )
        if not g.get_bool_setting("searchHistory"):
            g.add_directory_item(
                g.get_language_string(30013),
                action="showsSearch",
                description=g.get_language_string(30372),
                menu_item=g.create_icon_dict("shows_search", g.ICONS_PATH),
            )
        else:
            g.add_directory_item(
                g.get_language_string(30013),
                action="showsSearchHistory",
                description=g.get_language_string(30374),
                menu_item=g.create_icon_dict("shows_search", g.ICONS_PATH),
            )
        g.close_directory(g.CONTENT_MENU)

    @staticmethod
    def my_shows():
        trakt_active = g.trakt_active()
        mdblist_active = g.mdblist_active()
        simkl_active = g.simkl_active()
        if (trakt_active or mdblist_active or simkl_active) and g.get_bool_setting('watchlistcalendar.enabled', False):
            g.add_directory_item(
                g.get_language_string(31472),
                action="calendarBrowse",
                description=g.get_language_string(31475),
                menu_item=g.create_icon_dict("shows_update", g.ICONS_PATH),
                is_folder=False,
            )
        if (trakt_active or mdblist_active or simkl_active) and g.get_bool_setting('tvschedule.enabled', False):
            g.add_directory_item(
                g.get_language_string(31539),
                action="tvScheduleBrowse",
                description=g.get_language_string(31542),
                menu_item=g.create_icon_dict("shows_update", g.ICONS_PATH),
                is_folder=False,
            )
        if sum((trakt_active, mdblist_active, simkl_active)) >= 2 and g.get_bool_setting('mergeshows.enabled', False):
            g.add_directory_item(
                g.get_language_string(30977),
                action="mergeInProgressShows",
                description=g.get_language_string(30978),
                menu_item=g.create_icon_dict("shows_progress", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31516),
                action="mergeInProgressTVShows",
                description=g.get_language_string(31517),
                menu_item=g.create_icon_dict("shows_progress", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30979),
                action="mergeWatchedShows",
                description=g.get_language_string(30980),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
        if g.get_setting('trakt.auth') and g.get_bool_setting('trakt.enabled', False):
            g.add_directory_item(
                g.get_language_string(30043),
                action="onDeckShows",
                description=g.get_language_string(30433),
                menu_item=g.create_icon_dict("shows_progress", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30210),
                action="showsNextUp",
                description=g.get_language_string(30436),
                menu_item=g.create_icon_dict("shows_nextup", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30015),
                action="showsMyWatchlist",
                description=g.get_language_string(30435),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30014),
                action="showsMyCollection",
                description=g.get_language_string(30434),
                menu_item=g.create_icon_dict("shows_collected", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30986),
                action="showsMyFavorites",
                description=g.get_language_string(30988),
                menu_item=g.create_icon_dict("list_liked", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31478),
                action="traktDroppedShows",
                description=g.get_language_string(31479),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30972),
                action="showsRecentlyWatched",
                description=g.get_language_string(30479),
                menu_item=g.create_icon_dict("shows_recent", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30213),
                action="showsMyRecentEpisodes",
                description=g.get_language_string(30439),
                menu_item=g.create_icon_dict("shows_recent", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30211),
                action="myUpcomingEpisodes",
                description=g.get_language_string(30437),
                menu_item=g.create_icon_dict("shows_update", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30212),
                action="showsMyProgress",
                description=g.get_language_string(30438),
                menu_item=g.create_icon_dict("shows_progress", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30214),
                action="myTraktLists",
                mediatype="shows",
                description=g.get_language_string(30440),
                menu_item=g.create_icon_dict("list_trakt", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30350),
                action="myLikedLists",
                mediatype="shows",
                description=g.get_language_string(30441),
                menu_item=g.create_icon_dict("list_liked", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31489),
                action="searchTraktShowLists",
                description=g.get_language_string(31490),
                menu_item=g.create_icon_dict("list_trakt", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30325),
                action="myWatchedEpisodes",
                description=g.get_language_string(30442),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
        if g.get_setting('mdblist.enabled') == "true" and (g.get_setting('mdblist.auth') or g.get_setting('mdblist.apikey')):
            g.add_directory_item(
                g.get_language_string(30970),
                action="mdblistInProgressEpisodes",
                description=g.get_language_string(30971),
                menu_item=g.create_icon_dict("shows_progress", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31603),
                action="mdblistInProgressShows",
                description=g.get_language_string(31604),
                menu_item=g.create_icon_dict("shows_progress", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31476),
                action="mdblistNextUp",
                description=g.get_language_string(31477),
                menu_item=g.create_icon_dict("shows_nextup", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31503),
                action="mdblistWatchlistShows",
                description=g.get_language_string(31504),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31159),
                action="mdblistCollectionShows",
                description=g.get_language_string(31160),
                menu_item=g.create_icon_dict("shows_collected", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31161),
                action="mdblistDroppedShows",
                description=g.get_language_string(31162),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30966),
                action="mdblistRecentShows",
                description=g.get_language_string(30967),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(30996),
                action="mdblistMyLists",
                mediatype="shows",
                description=g.get_language_string(30997),
                menu_item=g.create_icon_dict("list_trakt", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31507),
                action="mdblistLikedLists",
                mediatype="shows",
                description=g.get_language_string(31508),
                menu_item=g.create_icon_dict("list_liked", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31486),
                action="mdblistDiscover",
                mediatype="shows",
                description=g.get_language_string(31064),
                menu_item=g.create_icon_dict("list_trakt", g.ICONS_PATH),
            )
        if g.get_setting('simkl.auth') and g.get_bool_setting('simkl.enabled'):
            g.add_directory_item(
                g.get_language_string(31111),
                action="simklInProgressEpisodes",
                description=g.get_language_string(31112),
                menu_item=g.create_icon_dict("shows_progress", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31601),
                action="simklNextUp",
                description=g.get_language_string(31602),
                menu_item=g.create_icon_dict("shows_nextup", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31147),
                action="simklWatchingShows",
                description=g.get_language_string(31148),
                menu_item=g.create_icon_dict("shows_progress", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31149),
                action="simklPlanToWatchShows",
                description=g.get_language_string(31150),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31151),
                action="simklHoldShows",
                description=g.get_language_string(31152),
                menu_item=g.create_icon_dict("shows_collected", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31153),
                action="simklCompletedShows",
                description=g.get_language_string(31154),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31155),
                action="simklDroppedShows",
                description=g.get_language_string(31156),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
            g.add_directory_item(
                g.get_language_string(31107),
                action="simklRecentShows",
                description=g.get_language_string(31108),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
        g.close_directory(g.CONTENT_MENU)

    def generic_endpoint(self, endpoint):
        trakt_endpoint = f"shows/{endpoint}"
        if endpoint in _PERIOD_ENDPOINTS:
            trakt_endpoint += "/weekly"
        # "anticipated" shows have future air_dates by definition — bypass the
        # hide_unaired filter so they are not silently filtered out entirely.
        hide_unaired = endpoint != "anticipated"
        trakt_list = self.shows_database.extract_trakt_page(
            trakt_endpoint, page=g.PAGE, extended="full", hide_unaired=hide_unaired, hide_watched=False
        )
        self.list_builder.show_list_builder(trakt_list, hide_unaired=hide_unaired, hide_watched=False)

    def shows_popular_recent(self):
        year_range = f"{datetime.datetime.now().year - 1}-{datetime.datetime.now().year}"
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/popular", years=year_range, page=g.PAGE, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    def shows_trending_recent(self):
        year_range = f"{datetime.datetime.now().year - 1}-{datetime.datetime.now().year}"
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/trending", years=year_range, page=g.PAGE, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    @trakt_auth_guard
    def my_shows_collection(self):
        no_paging = not g.get_bool_setting("general.paginatecollection")
        sort = "title" if g.get_int_setting("general.sortcollection") == 1 else False
        trakt_list = self.shows_database.get_collected_shows(g.PAGE)
        if sort == "title" and not no_paging:
            trakt_list = sorted(
                trakt_list, key=lambda k: tools.SORT_TOKEN_REGEX.sub("", k["trakt_object"]["info"].get('title').lower())
            )
            offset = (g.PAGE - 1) * self.page_limit
            trakt_list = trakt_list[offset : offset + self.page_limit]
        self.list_builder.show_list_builder(
            trakt_list, no_paging=no_paging, sort=sort, hide_watched=False
        )

    @trakt_auth_guard
    def my_shows_watchlist(self):
        paginate = not g.get_bool_setting("general.paginatetraktlists")
        trakt_list = self.shows_database.extract_trakt_page(
            "users/me/watchlist/shows",
            extended="full",
            page=g.PAGE,
            ignore_cache=True,
            no_paging=paginate,
            hide_unaired=False,
            hide_watched=False,
        )
        if g.PAGE == 1:
            g.add_directory_item(
                g.get_language_string(31521),
                action="traktWatchlistBulkDrop",
                description=g.get_language_string(31522),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
        self.list_builder.show_list_builder(
            trakt_list,
            no_paging=paginate,
            hide_unaired=False,
            hide_watched=False,
        )

    @trakt_auth_guard
    def watchlist_bulk_drop(self):
        # Bulk-hide counterpart to dropped_shows_bulk_restore() below - same live-fetch,
        # multiselect, then POST shape, mirrored in the opposite direction: POST
        # users/hidden/dropped (add) instead of .../remove, and add_hidden_item() instead
        # of remove_item() for the local hidden-table cache.
        trakt_list = self.shows_database.extract_trakt_page(
            "users/me/watchlist/shows",
            extended="full",
            ignore_cache=True,
            no_paging=True,
            hide_unaired=False,
            hide_watched=False,
        )
        if not trakt_list:
            g.notification(g.ADDON_NAME, g.get_language_string(31525))
            self.my_shows_watchlist()
            return

        list_items = [
            item.get("title") or MetadataHandler.get_trakt_info(item, "title") or ""
            for item in trakt_list
        ]
        selected = xbmcgui.Dialog().multiselect(
            f"{g.ADDON_NAME}: {g.get_language_string(31523)}", list_items
        )

        if not selected:
            self.my_shows_watchlist()
            return

        show_ids = [trakt_list[i].get("trakt_id") for i in selected]
        show_ids = [i for i in show_ids if i is not None]

        self.trakt_api.post_json(
            "users/hidden/dropped", {"shows": [{"ids": {"trakt": i}} for i in show_ids]}
        )
        for trakt_id in show_ids:
            self.hidden_database.add_hidden_item(trakt_id, "tvshow", "dropped")

        g.notification(g.ADDON_NAME, g.get_language_string(31524).format(len(show_ids)))
        self.my_shows_watchlist()

    @trakt_auth_guard
    def dropped_shows(self):
        paginate = not g.get_bool_setting("general.paginatetraktlists")
        hide_watched = g.get_bool_setting("trakt.dropped.hideWatched")
        trakt_list = self.shows_database.extract_trakt_page(
            "users/hidden/dropped",
            type="show",
            extended="full",
            page=g.PAGE,
            ignore_cache=True,
            no_paging=paginate,
            hide_unaired=False,
            hide_watched=hide_watched,
        )
        if not trakt_list:
            # hide_watched can empty an otherwise non-empty Dropped Shows list (all dropped
            # shows fully watched). Surface the Restore action instead of dead-ending the
            # screen, since restoring is exactly what a user in that state needs to reach.
            if hide_watched and g.PAGE == 1:
                g.notification(g.ADDON_NAME, g.get_language_string(31528))
                g.add_directory_item(
                    g.get_language_string(31480),
                    action="traktDroppedShowsRestore",
                    description=g.get_language_string(31481),
                    menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
                )
            g.cancel_directory()
            return
        if g.PAGE == 1:
            g.add_directory_item(
                g.get_language_string(31480),
                action="traktDroppedShowsRestore",
                description=g.get_language_string(31481),
                menu_item=g.create_icon_dict("shows_watched", g.ICONS_PATH),
            )
        self.list_builder.show_list_builder(
            trakt_list,
            no_paging=paginate,
            hide_unaired=False,
            hide_watched=hide_watched,
        )

    @trakt_auth_guard
    def dropped_shows_bulk_restore(self):
        # Live-fetch only, same as dropped_shows() above - the hidden DB table is a local
        # filter cache for other screens (calendar/recommendations), not a mirror of Trakt's
        # dropped state, so it is never read here. It is still cleared per-show on restore to
        # keep it consistent with _hide_item()'s own write when a show is dropped.
        trakt_list = self.shows_database.extract_trakt_page(
            "users/hidden/dropped",
            type="show",
            extended="full",
            ignore_cache=True,
            no_paging=True,
            hide_unaired=False,
            hide_watched=False,
        )
        if not trakt_list:
            g.notification(g.ADDON_NAME, g.get_language_string(31485))
            self.dropped_shows()
            return

        list_items = [
            item.get("title") or MetadataHandler.get_trakt_info(item, "title") or ""
            for item in trakt_list
        ]
        selected = xbmcgui.Dialog().multiselect(
            f"{g.ADDON_NAME}: {g.get_language_string(31482)}", list_items
        )

        if not selected:
            self.dropped_shows()
            return

        show_ids = [trakt_list[i].get("trakt_id") for i in selected]
        show_ids = [i for i in show_ids if i is not None]

        self.trakt_api.post_json(
            "users/hidden/dropped/remove", {"shows": [{"ids": {"trakt": i}} for i in show_ids]}
        )
        for trakt_id in show_ids:
            self.hidden_database.remove_item("dropped", trakt_id)

        g.notification(g.ADDON_NAME, g.get_language_string(31484).format(len(show_ids)))
        self.dropped_shows()

    @trakt_auth_guard
    def my_shows_favorites(self):
        paginate = not g.get_bool_setting("general.paginatetraktlists")
        trakt_list = self.shows_database.extract_trakt_page(
            "sync/favorites/shows/rank/asc",
            extended="full",
            page=g.PAGE,
            ignore_cache=True,
            no_paging=paginate,
            pull_all=True,
            hide_unaired=False,
            hide_watched=False,
        )
        self.list_builder.show_list_builder(
            trakt_list,
            no_paging=paginate,
            hide_unaired=False,
            hide_watched=False,
        )

    @trakt_auth_guard
    def my_show_progress(self):
        no_paging = not g.get_bool_setting("general.paginatecollection")
        sort = "title" if g.get_int_setting("general.sortcollection") == 1 else False
        trakt_list = self.shows_database.get_unfinished_collected_shows(g.PAGE)
        if sort == "title" and not no_paging:
            trakt_list = sorted(
                trakt_list, key=lambda k: tools.SORT_TOKEN_REGEX.sub("", k["trakt_object"]["info"].get('title').lower())
            )
            offset = (g.PAGE - 1) * self.page_limit
            trakt_list = trakt_list[offset : offset + self.page_limit]
        self.list_builder.show_list_builder(trakt_list, no_paging=no_paging, sort=sort)

    @trakt_auth_guard
    def shows_recommended(self):
        trakt_list = self.shows_database.extract_trakt_page(
            "recommendations/shows", ignore_collected=True, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)

    def shows_new(self):
        hidden_items = self.hidden_database.get_hidden_items("recommendations", "tvshow")
        date_string = datetime.datetime.now() - datetime.timedelta(days=29)
        trakt_list = self.shows_database.extract_trakt_page(
            f"calendars/all/shows/new/{date_string.strftime('%Y-%m-%d')}/30",
            languages=','.join({'en', g.get_language_code()}),
            extended="full",
            pull_all=True,
            no_paging=True,
            ignore_cache=True,
            hide_watched=False,
            hide_unaired=False,
        )
        trakt_list = [i for i in trakt_list if i["trakt_id"] not in hidden_items][: self.page_limit]
        self.list_builder.show_list_builder(trakt_list, no_paging=True)

    def shows_recently_watched(self):
        self.list_builder.show_list_builder(
            self.shows_database.get_recently_watched_shows(),
            no_paging=True,
            hide_watched=False,
        )

    def my_next_up(self):
        episodes = self.shows_database.get_nextup_episodes(g.get_int_setting("nextup.sort") == 1)
        self.list_builder.mixed_episode_builder(episodes, no_paging=True)

    @trakt_auth_guard
    def my_recent_episodes(self):
        hidden_shows = self.hidden_database.get_hidden_items("calendar", "tvshow")
        date_string = datetime.datetime.now() - datetime.timedelta(days=13)
        trakt_list = self.trakt_api.get_json(
            f"calendars/my/shows/{date_string.strftime('%Y-%m-%d')}/14", extended="full", pull_all=True
        )
        if trakt_list is None:
            trakt_list = []
        trakt_list = sorted(
            [i for i in trakt_list if i.get("trakt_show_id") not in hidden_shows],
            key=lambda t: (t.get("first_aired") or ""),
            reverse=True,
        )

        self.list_builder.mixed_episode_builder(trakt_list, hide_watched=False)

    @trakt_auth_guard
    def my_upcoming_episodes(self):
        tomorrow = g.datetime_to_string(datetime.date.today() + datetime.timedelta(days=1))
        upcoming_episodes = self.trakt_api.get_json(
            f"calendars/my/shows/{tomorrow}/30", extended="full", pull_all=True
        )
        if upcoming_episodes is None:
            upcoming_episodes = []
        start = (g.PAGE - 1) * self.page_limit
        page_slice = upcoming_episodes[start : start + self.page_limit]
        self.list_builder.mixed_episode_builder(
            page_slice,
            prepend_date=True,
            hide_unaired=False,
            force_next_page=len(upcoming_episodes) > start + self.page_limit,
        )

    def shows_networks(self):
        trakt_list = self.trakt_api.get_json_cached("networks")
        list_items = [
            g.add_directory_item(
                i["name"],
                action="showsNetworkShows",
                action_args=i["name"],
                bulk_add=True,
            )
            for i in trakt_list
        ]

        xbmcplugin.addDirectoryItems(g.PLUGIN_HANDLE, list_items, len(list_items))
        g.close_directory(g.CONTENT_MENU)

    def shows_networks_results(self, network):
        trakt_list = self.shows_database.extract_trakt_page(
            "shows/popular", networks=network, page=g.PAGE, extended="full"
        )
        self.list_builder.show_list_builder(trakt_list)
        g.close_directory(g.CONTENT_SHOW)

    def shows_updated(self):
        date = datetime.date.today() - datetime.timedelta(days=21)
        date = g.datetime_to_string(date)
        trakt_list = self.shows_database.extract_trakt_page(
            f"shows/updates/{date}", extended="full", ignore_cache=True, hide_watched=False, hide_unaired=False
        )
        self.list_builder.show_list_builder(trakt_list, no_paging=True)

    def shows_search_history(self):
        history = self.search_history.get_search_history("tvshow")
        g.add_directory_item(
            g.get_language_string(30182),
            action="showsSearch",
            description=g.get_language_string(30372),
        )
        g.add_directory_item(
            g.get_language_string(30180),
            action="clearSearchHistory",
            mediatype="tvshow",
            is_folder=False,
            description=g.get_language_string(30180),
        )
        for i in history:
            remove_path = g.create_url(
                g.BASE_URL,
                {"action": "removeSearchHistory", "mediatype": "tvshow", "endpoint": i},
            )
            g.add_directory_item(
                i,
                action="showsSearchResults",
                action_args=tools.construct_action_args(i),
                cm=[(g.get_language_string(30565), f"RunPlugin({remove_path})")],
            )
        g.close_directory(g.CONTENT_MENU)

    def search_trakt_show_lists(self, query=None):
        if not query:
            query = g.get_keyboard_input(g.get_language_string(30013))
        if not query:
            g.cancel_directory(silent=True)
            return

        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().search_lists("shows", query)

    def shows_search(self, query=None):
        if not query:
            query = g.get_keyboard_input(g.get_language_string(30013))
        if not query:
            g.cancel_directory(silent=True)
            return

        if g.get_bool_setting("searchHistory"):
            self.search_history.add_search_history("tvshow", query)
        self.shows_search_results(query)

    def shows_search_results(self, query):
        trakt_list = self.shows_database.extract_trakt_page(
            "search/show",
            query=query,
            fields="title,aliases",
            page=g.PAGE,
            extended="full",
            field="title",
            hide_unaired=False,
            hide_watched=False,
        )

        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(
            [show for show in trakt_list if float(show["trakt_object"]["info"]["score"]) > 0],
            hide_unaired=False,
            hide_watched=False,
        )

    def shows_by_actor(self, query):
        if not query:
            query = g.get_keyboard_input(g.get_language_string(30013))
        if not query:
            g.cancel_directory(silent=True)
            return

        if g.get_bool_setting("searchHistory"):
            self.search_history.add_search_history("showActor", query)

        query = g.transliterate_string(query)
        # Try to deal with transliterated chinese actor names as some character -> word transliterations can be joined
        # I have no idea of the rules and it could well be arbitrary
        # This approach will only work if only one pair of adjoining transliterated chars are joined
        name_parts = query.split()
        for i in range(len(name_parts), 0, -1):
            query = "-".join(name_parts[:i]) + "-".join(name_parts[i : i + 1])
            query = parse.quote_plus(query)

            trakt_list = self.shows_database.extract_trakt_page(
                f"people/{query}/shows",
                extended="full",
                page=g.PAGE,
                hide_watched=False,
                hide_unaired=False,
            )
            if not trakt_list:
                continue
            else:
                break

        try:
            if not trakt_list or 'trakt_id' not in trakt_list[0]:
                raise KeyError
        except KeyError:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(trakt_list, hide_watched=False, hide_unaired=False)

    def show_seasons(self, args):
        self.list_builder.season_list_builder(args["trakt_id"], no_paging=True, hide_watched=False)

    def season_episodes(self, args):
        self.list_builder.episode_list_builder(args["trakt_show_id"], args["trakt_id"], no_paging=True, hide_watched=False)

    def flat_episode_list(self, args):
        self.list_builder.episode_list_builder(args["trakt_id"], no_paging=True, hide_watched=False)

    def shows_genres(self):
        g.add_directory_item(
            g.get_language_string(30045),
            action="showGenresGet",
            description=g.get_language_string(31581),
            menu_item=g.create_icon_dict("list", g.ICONS_PATH),
        )
        genres = self.trakt_api.get_json_cached("genres/shows", extended="full")

        if genres is None:
            g.cancel_directory()
            return

        for i in genres:
            g.add_directory_item(
                i["name"],
                action="showGenresGet",
                action_args=i["slug"],
                menu_item=g.create_icon_dict(i['slug'], g.GENRES_PATH),
            )
        g.close_directory(g.CONTENT_GENRES)

    def shows_genre_list(self, args):
        if args is None:
            genre_display_list = []
            genres = self.trakt_api.get_json_cached("genres/shows")

            for genre in genres:
                gi = xbmcgui.ListItem(genre["name"])
                gi.setArt({"thumb": f"{g.GENRES_PATH}{genre['slug']}.png"})
                genre_display_list.append(gi)
            genre_multiselect = xbmcgui.Dialog().multiselect(
                f"{g.ADDON_NAME}: {g.get_language_string(30303)}", genre_display_list, useDetails=True
            )

            if genre_multiselect is None:
                return
            genre_string = "".join(f", {genres[selection]['slug']}" for selection in genre_multiselect)

            genre_string = genre_string[2:]
        else:
            genre_string = parse.unquote(args)

        trakt_list = self.shows_database.extract_trakt_page(
            f"shows/{'trending' if g.get_int_setting('general.genres.endpoint.tv') == 0 else 'popular'}",
            genres=genre_string,
            page=g.PAGE,
            extended="full",
        )

        if trakt_list is None:
            g.cancel_directory()
            return

        self.list_builder.show_list_builder(trakt_list, next_args=genre_string)

    def shows_related(self, args):
        trakt_list = self.shows_database.extract_trakt_page(f"shows/{args}/related", extended="full")
        self.list_builder.show_list_builder(trakt_list)

    def shows_years(self, year=None):
        if year is None:
            current_year = datetime.datetime.now().year
            for year in range(current_year, 1899, -1):
                g.add_directory_item(str(year), action="showYears", action_args=year)
            g.close_directory(g.CONTENT_MENU)
        else:
            trakt_list = self.shows_database.extract_trakt_page(
                "shows/popular", years=year, page=g.PAGE, extended="full", hide_watched=False
            )
            self.list_builder.show_list_builder(trakt_list)

    @trakt_auth_guard
    def my_watched_episode(self):
        watched_episodes = self.shows_database.get_watched_episodes(g.PAGE)
        self.list_builder.mixed_episode_builder(watched_episodes, hide_watched=False)

    def anime_related_shows(self, anidb_id):
        """Display related anime (sequels/prequels/side stories) for a given AniDB ID.

        Resolves related AniDB IDs to Trakt IDs via Otaku-Mappings DB and
        builds a standard show list. Items without Trakt IDs are shown as
        unplayable directory items.
        """
        from resources.lib.modules.anime.anidb_relations import get_related_anime
        relations = get_related_anime(anidb_id)
        if not relations:
            g.cancel_directory()
            return

        # Split into those with Trakt IDs (playable) and those without
        trakt_shows = []
        for rel in relations:
            if rel.get("trakt_id"):
                trakt_shows.append(rel)

        if trakt_shows:
            # Build using existing trakt show infrastructure
            trakt_ids = [{"trakt_id": r["trakt_id"]} for r in trakt_shows]
            trakt_list = self.shows_database.get_show_list(trakt_ids)
            if trakt_list:
                self.list_builder.show_list_builder(trakt_list)
                return

        # Fallback: plain directory items with relation info
        for rel in relations:
            label = f"[{rel['relation_type']}] {rel['title'] or 'Unknown'}"
            if rel.get("trakt_id"):
                g.add_directory_item(
                    label,
                    action="showSeasons",
                    action_args=rel["trakt_id"],
                )
            else:
                g.add_directory_item(label, is_folder=False)
        g.close_directory(g.CONTENT_SHOW)
