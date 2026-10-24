from resources.lib.database import trakt_sync
from resources.lib.database.trakt_sync import _list_cache_key, list_cache_get, list_cache_set
from resources.lib.modules.globals import g
from resources.lib.modules.guard_decorators import guard_against_none
from resources.lib.modules.guard_decorators import guard_against_none_or_empty
from resources.lib.modules.metadataHandler import MetadataHandler


class TraktSyncDatabase(trakt_sync.TraktSyncDatabase):
    def extract_trakt_page(self, url, **params):
        return super()._extract_trakt_page(url, "movies", **params)

    @guard_against_none(list)
    def get_movie_list(self, trakt_list, **params):
        # L1 cache check — returns cached result if available (reuselanguageinvoker)
        cache_key = _list_cache_key("movies", [i.get('trakt_id') for i in trakt_list if i.get('trakt_id')], **params)
        cached = list_cache_get(cache_key)
        if cached is not None:
            return cached

        self._update_movies(trakt_list)
        query = f"""
            SELECT m.trakt_id,
                   m.info,
                   m.art,
                   m.cast,
                   m.args,
                   b.resume_time,
                   b.percent_played,
                   m.watched AS play_count,
                   m.user_rating
            FROM movies AS m
                     LEFT JOIN bookmarks AS b
                               ON m.trakt_id = b.trakt_id
            WHERE m.trakt_id IN ({','.join(str(i.get('trakt_id')) for i in trakt_list)})
            """

        if params.get("hide_unaired", self.hide_unaired):
            query += f" AND (air_date IS NULL OR Datetime(air_date) < Datetime('{self._get_datetime_now()}'))"
        if params.get("hide_watched", self.hide_watched):
            query += " AND watched = 0"

        result = MetadataHandler.sort_list_items(self.fetchall(query), trakt_list)
        list_cache_set(cache_key, result)
        return result

    @guard_against_none(list)
    def get_collected_movies(self, page):
        paginate = g.get_bool_setting("general.paginatecollection")

        query = """
            SELECT m.trakt_id, meta.value AS trakt_object
            FROM movies AS m
                     LEFT JOIN movies_meta AS meta
                               ON m.trakt_id = meta.id
            WHERE collected = TRUE
            """

        if paginate:
            query += f"ORDER BY collected_at desc LIMIT {self.page_limit} OFFSET {self.page_limit * (page - 1)}"

        return self.fetchall(query)

    @guard_against_none(list)
    def get_watched_movies(self, page, force_all=False):
        query = """
            SELECT m.trakt_id, m.tmdb_id, meta.value AS trakt_object, m.last_watched_at
            FROM movies AS m
                     LEFT JOIN movies_meta AS meta
                               ON m.trakt_id = meta.id
            WHERE watched = 1
            ORDER BY last_watched_at DESC
            """
        if not force_all:
            query += f" LIMIT {self.page_limit} OFFSET {self.page_limit * (page - 1)}"
        return self.fetchall(query)

    def get_all_collected_movies(self):
        return self.fetchall(
            """
            SELECT m.trakt_id, meta.value AS trakt_object
            FROM movies AS m
                     LEFT JOIN movies_meta AS meta
                         ON m.trakt_id = meta.id
            WHERE collected = TRUE
            """
        )

    def get_all_watched_movie_tmdb_ids(self):
        """bridgeSync's read-side for the Watched domain - bare tmdb_ids only,
        no metadata join. watched > 0, not =1: the column is a play-count, not
        a boolean (see mark_movie_watched below)."""
        return self.fetchall("SELECT tmdb_id FROM movies WHERE watched > 0 AND tmdb_id IS NOT NULL")

    def get_all_collected_movie_tmdb_ids(self):
        """bridgeSync's read-side for the Collection domain."""
        return self.fetchall("SELECT tmdb_id FROM movies WHERE collected = TRUE AND tmdb_id IS NOT NULL")

    @guard_against_none()
    def mark_movie_watched(self, trakt_id):
        play_count = self.fetchone("SELECT watched FROM movies WHERE trakt_id=?", (trakt_id,))["watched"]
        self._mark_movie_record("watched", play_count + 1, trakt_id)

    @guard_against_none()
    def mark_movie_unwatched(self, trakt_id):
        self._mark_movie_record("watched", 0, trakt_id)

    @guard_against_none()
    def mark_movie_collected(self, trakt_id):
        self._mark_movie_record("collected", 1, trakt_id)

    @guard_against_none()
    def mark_movie_uncollected(self, trakt_id):
        self._mark_movie_record("collected", 0, trakt_id)

    def is_movie_watchlisted(self, trakt_id):
        row = self.fetchone("SELECT watchlisted FROM movies WHERE trakt_id=?", (trakt_id,))
        return bool(row and row["watchlisted"])

    def is_movie_favorited(self, trakt_id):
        row = self.fetchone("SELECT favorited FROM movies WHERE trakt_id=?", (trakt_id,))
        return bool(row and row["favorited"])

    @guard_against_none()
    def mark_movie_watchlisted(self, trakt_id, watchlisted):
        self.execute_sql("UPDATE movies SET watchlisted=? WHERE trakt_id=?", (1 if watchlisted else 0, trakt_id))

    @guard_against_none()
    def mark_movie_favorited(self, trakt_id, favorited):
        self.execute_sql("UPDATE movies SET favorited=? WHERE trakt_id=?", (1 if favorited else 0, trakt_id))

    @guard_against_none()
    def _mark_movie_record(self, column, value, trakt_id):
        if column == "watched":
            datetime_column = "last_watched_at"
        elif column == "collected":
            datetime_column = "collected_at"
        else:
            datetime_column = None
        if datetime_column is None:
            # Just in case we forgot any methods that call this
            raise TypeError("NoneType Error: Date Time Column")
        self.execute_sql(
            f"UPDATE movies SET {column}=?, {datetime_column}=? WHERE trakt_id=?",
            (value, self._get_datetime_now() if value > 0 else None, trakt_id),
        )

    def _fetch_movie_summary(self, trakt_id):
        return self.trakt_api.get_json_cached(f"movies/{trakt_id}", extended=True)

    @guard_against_none(list)
    def get_movie(self, trakt_id):
        return self.get_movie_list([self._get_single_movie_meta(trakt_id)], hide_unaired=False, hide_watched=False)[0]

    @guard_against_none()
    def _get_single_movie_meta(self, trakt_id):
        return self._get_single_meta(f"/movies/{trakt_id}", trakt_id, "movies")

    def missing_trakt_meta_ids(self, trakt_ids):
        """Subset of trakt_ids with no persisted raw Trakt object in movies_meta.
        Used by movie_calendar_data.py's cache-hit branch to self-heal bookkeeping
        (movieCalendar.db) that has outlived traktSync.db being cleared out of band
        (e.g. Rebuild Database) - without this, a wiped row crashes
        metadataHandler.format_db_object() on every future open of that month,
        forever, since the cache-hit branch normally never re-inserts (see the
        insert_trakt_movies() call in movie_calendar_data.py)."""
        ids = {int(t) for t in trakt_ids if t is not None}
        if not ids:
            return []
        id_list = ",".join(str(i) for i in ids)
        present = {
            r["id"] for r in self.fetchall(f"SELECT id FROM movies_meta WHERE type='trakt' AND id IN ({id_list})")
        }
        return sorted(ids - present)

    @guard_against_none_or_empty()
    def _update_movies(self, list_to_update):
        get = MetadataHandler.get_trakt_info

        sql_statement = f"""
            WITH requested(trakt_id, last_updated) AS (VALUES
                    {','.join(f"({i.get('trakt_id')},'{get(i, 'dateadded')}')" for i in list_to_update)})
            SELECT r.trakt_id,
                   trakt.value      AS trakt_object,
                   trakt.meta_hash  AS trakt_meta_hash,
                   tmdb_id,
                   tmdb.value       AS tmdb_object,
                   tmdb.meta_hash   AS tmdb_meta_hash,
                   fanart.value     AS fanart_object,
                   fanart.meta_hash AS fanart_meta_hash,
                   m.imdb_id,
                   omdb.value       AS omdb_object,
                   omdb.meta_hash   AS omdb_meta_hash,
                   m.needs_update
            FROM requested as r
                     LEFT JOIN movies AS m
                               ON r.trakt_id = m.trakt_id
                     LEFT JOIN movies_meta AS trakt
                               ON trakt.id = m.trakt_id AND trakt.type = 'trakt'
                     LEFT JOIN movies_meta AS tmdb
                               ON tmdb.id = m.tmdb_id AND tmdb.type = 'tmdb'
                     LEFT JOIN movies_meta AS omdb
                               ON omdb.id = m.imdb_id AND omdb.type = 'omdb'
                     LEFT JOIN movies_meta AS fanart
                               ON fanart.id = m.tmdb_id AND fanart.type = 'fanart'
            """

        db_list_to_update = self.fetchall(sql_statement)

        for movie in db_list_to_update:
            self.task_queue.put(self.metadataHandler.update, movie)
        updated_items = self.task_queue.wait_completion()

        if not updated_items:
            self.task_queue.close()
            return

        self.task_queue.put(
            self.save_to_meta_table,
            (i for i in updated_items if "tmdb_object" in i),
            "movies",
            "tmdb",
            "tmdb_id",
        )
        self.task_queue.put(
            self.save_to_meta_table,
            (i for i in updated_items if "fanart_object" in i),
            "movies",
            "fanart",
            "tmdb_id",
        )
        self.task_queue.put(
            self.save_to_meta_table,
            (i for i in updated_items if "omdb_object" in i),
            "movies",
            "omdb",
            "imdb_id",
        )
        self.task_queue.wait_completion()
        self.task_queue.close()

        formatted_items = self.metadataHandler.format_db_object(updated_items)

        self.execute_sql(
            self.upsert_movie_query,
            [
                (
                    i["info"]["trakt_id"],
                    i["info"],
                    i.get("art"),
                    i.get("cast"),
                    None,
                    None,
                    i["info"].get("aired"),
                    i["info"].get("dateadded"),
                    i["info"].get("tmdb_id"),
                    i["info"].get("imdb_id"),
                    self.metadataHandler.meta_hash,
                    self._create_args(i),
                    None,
                    None,
                    None,
                )
                for i in formatted_items
            ],
        )
