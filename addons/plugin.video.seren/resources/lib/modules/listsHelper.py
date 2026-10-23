from resources.lib.common import tools
from resources.lib.database.trakt_sync import lists
from resources.lib.modules.globals import g
from resources.lib.modules.list_builder import ListBuilder
from resources.lib.modules.metadataHandler import MetadataHandler


class ListsHelper:
    def __init__(self):
        self.title_appends = g.get_setting('general.appendListTitles')
        self.lists_database = lists.TraktSyncDatabase()
        self.builder = ListBuilder()
        self.no_paging = not g.get_bool_setting('general.paginatetraktlists')

    def get_list_items(self):
        arguments = g.REQUEST_PARAMS['action_args']
        media_type = g.REQUEST_PARAMS.get('media_type', arguments.get('type'))
        ignore_cache = True
        if g.FROM_WIDGET:
            widget_loaded_setting = f"widget_loaded.{media_type}.{arguments}"
            if not g.get_bool_runtime_setting(widget_loaded_setting):
                ignore_cache = False
                g.set_runtime_setting(widget_loaded_setting, True)
        list_items = self.lists_database.get_list_content(
            arguments['username'],
            arguments['trakt_id'],
            self._backwards_compatibility(media_type),
            ignore_cache=ignore_cache,
            page=g.PAGE,
            no_paging=self.no_paging,
        )

        if not list_items:
            # a list with no items of this media type (eg. a movies-only list browsed under shows)
            # is a valid empty menu, not a failure
            g.log(f"No {media_type} items returned for list {arguments['trakt_id']}", "debug")
            g.close_directory(g.CONTENT_SHOW if media_type in ("tvshow", "shows") else g.CONTENT_MOVIE)
            return

        if media_type in ['tvshow', 'shows']:
            self.builder.show_list_builder(list_items, no_paging=self.no_paging)
        elif media_type in ['movie', 'movies']:
            self.builder.movie_menu_builder(list_items, no_paging=self.no_paging)

    def my_trakt_lists(self, media_type):
        self._create_list_menu(
            self._get_list_menu('users/me/lists', media_type),
            media_type=media_type,
        )

    def my_liked_lists(self, media_type):
        self._create_list_menu(
            self._get_list_menu('users/me/likes/lists', media_type),
            media_type=media_type,
        )

    def trending_lists(self, media_type):
        self._create_list_menu(
            self.lists_database.extract_trakt_page('lists/trending', media_type, page=g.PAGE), media_type=media_type
        )

    def popular_lists(self, media_type):
        self._create_list_menu(
            self.lists_database.extract_trakt_page('lists/popular', media_type, page=g.PAGE), media_type=media_type
        )

    def _create_list_menu(self, trakt_lists, **params):
        trakt_object = MetadataHandler.trakt_object
        get = MetadataHandler.get_trakt_info
        trakt_lists = self._normalize_list_menu(trakt_lists)
        if not trakt_lists:
            g.close_directory(g.CONTENT_MENU)
            return

        self.builder.lists_menu_builder(
            [
                tools.smart_merge_dictionary(
                    trakt_object(trakt_list),
                    {'args': {'trakt_id': get(trakt_list, 'trakt_id'), 'username': get(trakt_list, 'username')}},
                )
                for trakt_list in trakt_lists
            ],
            **params,
        )

    def _get_list_menu(self, endpoint, media_type):
        trakt_lists = self.lists_database.extract_trakt_page(
            endpoint,
            media_type,
            page=g.PAGE,
            no_paging=self.no_paging,
            pull_all=True,
            ignore_cache=True,
        )
        if trakt_lists:
            return trakt_lists

        # extract_trakt_page only returns lists containing items of media_type; when the user has
        # none of those, fall back to showing their lists unfiltered rather than an empty menu
        g.log(f"No {media_type} list contents found for {endpoint}; falling back to unfiltered list menu", "debug")
        return self._get_unfiltered_lists(endpoint)

    def _get_unfiltered_lists(self, endpoint):
        page_limit = self.lists_database.page_limit
        results = self.lists_database.trakt_api.get_all_pages_flat(endpoint, limit=page_limit)
        if self.no_paging:
            return results

        offset = page_limit * (g.PAGE - 1)
        return results[offset : offset + page_limit]

    def _normalize_list_menu(self, trakt_lists):
        normalized_lists = []
        for trakt_list in trakt_lists or []:
            if not isinstance(trakt_list, dict):
                continue

            # info is a live reference into trakt_list, so these defaults persist for the menu builder
            info = MetadataHandler.info(MetadataHandler.trakt_object(trakt_list))
            if not info:
                continue

            info["mediatype"] = "list"
            if not info.get("username"):
                info["username"] = self.lists_database.trakt_api.username or "me"
            normalized_lists.append(trakt_list)

        return normalized_lists

    @staticmethod
    def _backwards_compatibility(media_type):
        if media_type == 'movie':
            return 'movies'
        return 'shows' if media_type in ['tvshow', 'show'] else media_type
