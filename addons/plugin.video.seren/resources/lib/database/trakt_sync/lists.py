from resources.lib.database import trakt_sync
from resources.lib.modules.metadataHandler import MetadataHandler


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    def extract_trakt_page(self, url, media_type, **params):
        params = dict(params)
        result = []
        page_number = params.pop("page", 1)
        no_paging = params.get("no_paging", False)
        pull_all = params.pop("pull_all", False)
        params["limit"] = self.page_limit
        get = MetadataHandler.get_trakt_info
        for page in self.trakt_api.get_all_pages_json(url, **params):
            if results := self.task_queue.map_results(
                self._indexed_list_contents,
                ((get(i, "username"), get(i, "trakt_id"), media_type) for i in page),
                kwargs_iterable=(dict(params) for _ in page),
            ):
                result.extend(
                    i for i in page if results.get(i.get("trakt_id")) and len(results.get(i.get("trakt_id"))) != 0
                )
                if not pull_all and len(result) >= (self.page_limit * page_number):
                    return result[self.page_limit * (page_number - 1) : self.page_limit * page_number]

        if pull_all and no_paging:
            return result
        else:
            return result[self.page_limit * (page_number - 1) : self.page_limit * page_number]

    def _indexed_list_contents(self, username, trakt_id, media_type, **params):
        params = dict(params)
        params["page"] = 1
        return {trakt_id: self.get_list_content(username, trakt_id, media_type, **params)}

    def get_list_content(self, username, trakt_id, media_type, **params):
        params = dict(params)
        trakt_media_type = {"movies": "movie", "shows": "show"}.get(media_type, media_type)
        list_item_url = f"users/{username}/lists/{trakt_id}/items/{trakt_media_type}"
        params["pull_all"] = True
        return self._extract_trakt_page(list_item_url, media_type, extended="full", **params)
