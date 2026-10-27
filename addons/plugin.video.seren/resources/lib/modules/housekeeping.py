"""Background housekeeping the service used to start as one RunPlugin interpreter per step.

Every RunPlugin is a fresh Kodi plugin interpreter (4.6-8.5 s of start-up overhead on the Shield at
Kodi start, about 1 s once quiet, 9-60 ms when the interpreter is reused under reuselanguageinvoker), so
steps that never needed to run side by side are grouped here: run_startup() replaces the torrentCacheCleanup / undesirablesStartup / updateAnimeMappings trio the
service launched 15 s apart at start-up, run_cycle() replaces the cleanOrphanedMetadata /
updateLocalTimezone pair at the end of each 13-17 minute service cycle. The individual router
actions are unchanged (torrentCacheCleanup is still fired on wake-up by SerenMonitor).
"""
import os
import time

from resources.lib.modules.globals import g

# The orphan sweep deletes rows that no show/movie/season/episode references any more, which only
# accumulates when something is removed from the library - it does not need to run every cycle.
_ORPHAN_CLEAN_INTERVAL = 24 * 60 * 60
_ORPHAN_CLEAN_STAMP = "cleanOrphanedMetadata.stamp"


def run_startup():
    for step in (_torrent_cache_cleanup, _undesirables_startup, _anime_mappings):
        if g.abort_requested():
            return
        try:
            step()
        except Exception as e:
            g.log(f"startupHousekeeping: {step.__name__} failed: {e}", "error")


def run_cycle():
    try:
        _clean_orphaned_metadata_daily()
    except Exception as e:
        g.log(f"cycleHousekeeping: orphaned metadata cleanup failed: {e}", "error")
    if g.abort_requested():
        return
    try:
        g.init_local_timezone()
    except Exception as e:
        g.log(f"cycleHousekeeping: local timezone update failed: {e}", "error")


def _torrent_cache_cleanup():
    from resources.lib.database import torrentCache

    torrentCache.TorrentCache().do_cleanup()


def _undesirables_startup():
    try:
        from resources.lib.database.undesirables import UndesirableCache

        uc = UndesirableCache()
        uc.add_new_defaults()
        g.log("Undesirables database initialized", "debug")
    except Exception as e:
        g.log(f"Undesirables startup error: {e}", "warning")


def _anime_mappings():
    try:
        from resources.lib.modules.anime.anilist_mapping import update_mapping_db

        update_mapping_db()
    except Exception as e:
        g.log(f"Anime mappings update error: {e}", "warning")
    try:
        from resources.lib.modules.anime.dub_data import update_mal_dub_json

        update_mal_dub_json()
    except Exception as e:
        g.log(f"MAL-Dubs update error: {e}", "warning")
    try:
        from resources.lib.modules.anime.anidb_titles import download_titles_dump

        download_titles_dump()
    except Exception as e:
        g.log(f"AniDB titles dump update error: {e}", "warning")


def _orphan_stamp_path():
    return os.path.join(g.ADDON_USERDATA_PATH, _ORPHAN_CLEAN_STAMP)


def _orphan_clean_due(now):
    """True when the stamp file is missing, unreadable, from the future (clock moved back) or older
    than the interval. A stamp file rather than a runtime property: the property is lost at every
    Kodi start, which is exactly when this would otherwise run again."""
    try:
        with open(_orphan_stamp_path(), "r", encoding="utf-8") as stamp:
            last = float(stamp.read().strip())
    except (OSError, ValueError):
        return True
    age = now - last
    return age < 0 or age >= _ORPHAN_CLEAN_INTERVAL


def _clean_orphaned_metadata_daily():
    now = time.time()
    if not _orphan_clean_due(now):
        g.log("cycleHousekeeping: orphaned metadata cleaned within the last 24 h - skipping", "debug")
        return
    from resources.lib.database.trakt_sync import TraktSyncDatabase

    TraktSyncDatabase().clean_orphaned_metadata()
    try:
        with open(_orphan_stamp_path(), "w", encoding="utf-8") as stamp:
            stamp.write(str(now))
    except OSError as e:
        g.log(f"cycleHousekeeping: could not save the orphan cleanup stamp: {e}", "warning")
