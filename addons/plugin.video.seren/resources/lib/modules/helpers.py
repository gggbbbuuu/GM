import datetime
import time

import xbmcgui

from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.database.providerCache import ProviderCache
from resources.lib.database.skinManager import SkinManager
from resources.lib.gui.windows.resolver_window import ResolverWindow
from resources.lib.modules.getSources import Sources
from resources.lib.modules.globals import g
from resources.lib.modules.resolver import Resolver
from resources.lib.modules.source_sorter import SourceSorter


class Resolverhelper:
    """
    Helper object to stream line resolving items
    """

    window = None

    @use_cache(1)
    def resolve_silent_or_visible(self, sources, item_information, pack_select=False, overwrite_cache=False):
        """
        Method to handle automatic background or foreground resolving
        :param sources: list of sources to handle
        :param item_information: information on item to play
        :param pack_select: True if you want to perform a manual file selection
        :param overwrite_cache: Set to true if you wish to overwrite the current cached return value
        :return: None if unsuccessful otherwise a playable object
        """
        stream_link = None
        release_title = None

        # Bubble last-played release title to position 0 — applies to both
        # silent and visible resolution paths (Otaku reorder_sources pattern).
        if not pack_select:
            episode_number = item_information.get('info', {}).get('episode', 1)
            Resolver.reorder_sources(sources, episode_number)

        if g.get_bool_runtime_setting('tempSilent') or g.get_bool_setting("general.resolverHide", False):
            stream_link, release_title = Resolver().resolve_multiple_until_valid_link(
                sources, item_information, pack_select, True
            )
        else:
            self.window = ResolverWindow(
                *SkinManager().confirm_skin_path('resolver.xml'),
                item_information=item_information,
                close_callback=self.close_window,
            )
            tools.run_threaded(self.window.doModal, sources, pack_select)
            try:
                while not g.wait_for_abort(0.30):
                    # Capture reference once to avoid TOCTOU race with close_window()
                    # which sets self.window = None on the background thread.
                    window = self.window
                    if window is None or window.canceled:
                        break
                    stream_link, release_title = window.get_return_data()
                    if stream_link:
                        break
            finally:
                # Kodi's Python invoker waits for every thread of the script to end. If the resolver
                # window stays open, its doModal thread keeps running after the script is done and the
                # interpreter never shuts down, blocking every later Python script in Kodi.
                self.close_window()

        if item_information['info']['mediatype'] == g.MEDIA_EPISODE and release_title:
            g.set_runtime_setting(
                f"last_resolved_release_title.{item_information['info']['trakt_show_id']}", release_title
            )
        return stream_link

    def close_window(self):
        if self.window:
            window = self.window
            self.window = None
            window.close()
            del window


class SourcesHelper:
    """
    Helper object to stream line scraping of items
    """

    @use_cache(1)
    def get_sources(self, action_args, overwrite_cache=False):
        """
        Method to handle automatic background or foreground scraping
        :param action_args: action arguments from request uri
        :param overwrite_cache: Set to true if you wish to overwrite the current cached return value
        :return:
        """
        item_information = self._get_item_information_for_play(action_args)
        if not ProviderCache().get_provider_packages():
            yesno = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30443))
            if not yesno:
                return
        self._negative_hit_message = None
        track_empty = not overwrite_cache and g.REQUEST_PARAMS.get("action") != "preScrape"
        if track_empty:
            remembered = self._remembered_empty_result(item_information)
            if remembered:
                self._negative_hit_message = remembered
                return [], [], item_information
        sources = Sources(item_information)
        result = sources.get_sources(overwrite_torrent_cache=overwrite_cache)
        if track_empty:
            blockers = sources.empty_scrape_blockers()
            if not result or not result[1]:
                if blockers:
                    g.log(f"Negative cache: this empty scrape does not count ({', '.join(blockers)})", "info")
            self._note_scrape_outcome(item_information, bool(result and result[1]), not blockers)
        return result

    # ── Negative result cache ──
    # A scrape that ran to completion and found nothing at all (no sources, no uncached torrents) is remembered
    # after it happens twice, so replaying the same dead item does not repeat a full scrape each time.
    # Any scrape that is incomplete (timeout, cancel, provider error) or has uncached torrents to act on never counts,
    # and a manual rescrape always searches again.
    NEGATIVE_STRIKES_NEEDED = 2
    NEGATIVE_TTL_MINUTES = 30
    NEGATIVE_TTL_AIRING_MINUTES = 10

    @staticmethod
    def _negative_cache_key(item_information):
        return f"seren.nosources.{item_information['info']['mediatype']}.{item_information.get('trakt_id')}"

    @staticmethod
    def _negative_cache_checksum():
        # A different scraping setup can find different things; those settings changing forgets the remembered result
        keys = [f"scraping.tier{n}" for n in range(1, 8)] + ["scraping.allTierSweep", "general.timeout"]
        return "|".join(str(g.get_setting(k)) for k in keys)

    def _remembered_empty_result(self, item_information):
        """The message to show when this item's empty result is still remembered, else None."""
        try:
            state = g.CACHE.get(
                self._negative_cache_key(item_information), checksum=self._negative_cache_checksum()
            )
            if not isinstance(state, dict) or state.get("until", 0) <= time.time():
                return None
            ago = max(1, int((time.time() - state.get("last", time.time())) / 60))
            until = datetime.datetime.fromtimestamp(state["until"]).strftime("%H:%M")
            g.log(f"Negative cache hit: {self._negative_cache_key(item_information)} (no sources {ago} min ago)", "info")
            return f"Nothing was found {ago} min ago - not searching again until {until}. Rescrape to search now."
        except Exception as e:
            g.log(f"Negative cache lookup failed: {e}", "warning")
            return None

    def _note_scrape_outcome(self, item_information, found_sources, found_nothing):
        """Count a completed empty scrape as a strike (remembering the item at the second one); any other outcome
        for an item that had strikes forgets them."""
        try:
            key = self._negative_cache_key(item_information)
            checksum = self._negative_cache_checksum()
            state = g.CACHE.get(key, checksum=checksum)
            state = state if isinstance(state, dict) else None
            if found_nothing:
                airing = item_information["info"]["mediatype"] == g.MEDIA_EPISODE and item_information.get("is_airing")
                ttl = self.NEGATIVE_TTL_AIRING_MINUTES if airing else self.NEGATIVE_TTL_MINUTES
                strikes = (state.get("strikes", 0) if state else 0) + 1
                now = time.time()
                until = now + ttl * 60 if strikes >= self.NEGATIVE_STRIKES_NEEDED else 0
                g.CACHE.set(
                    key,
                    {"strikes": strikes, "until": until, "last": now},
                    checksum=checksum,
                    expiration=datetime.timedelta(minutes=max(ttl, self.NEGATIVE_TTL_MINUTES)),
                )
                g.log(
                    f"Negative cache: nothing found (strike {strikes}/{self.NEGATIVE_STRIKES_NEEDED})"
                    + (f", remembered for {ttl} min" if until else ""),
                    "info",
                )
            elif state and found_sources:
                # Sources turned up: forget the strikes (1 s tombstone: the cache has no delete)
                g.CACHE.set(key, {}, checksum=checksum, expiration=datetime.timedelta(seconds=1))
        except Exception as e:
            g.log(f"Negative cache update failed: {e}", "warning")

    @staticmethod
    def _get_item_information_for_play(action_args):
        """Item metadata for an interactive play.

        Reading an episode makes the sync database mill the show, and that waits for any background Trakt/MDBList
        sync that is milling the same show (it once held a play for 23 s with no window). When the requested episode
        is already stored locally, that wait is capped so playback goes ahead with the stored data.
        """
        if (
            isinstance(action_args, dict)
            and action_args.get("mediatype") == "episode"
            and action_args.get("trakt_id")
            and g.REQUEST_PARAMS.get("action") != "preScrape"
        ):
            try:
                from resources.lib.database.trakt_sync import shows
                from resources.lib.modules.sync_lock import SYNC_WAIT_CAP_SECONDS, BoundedSyncWait

                stored = shows.TraktSyncDatabase().fetchone(
                    f"SELECT 1 FROM episodes WHERE trakt_id = {int(action_args['trakt_id'])}"
                )
                if stored:
                    with BoundedSyncWait(SYNC_WAIT_CAP_SECONDS):
                        return tools.get_item_information(action_args)
            except Exception as e:
                g.log(f"Bounded sync wait unavailable, reading item information normally: {e}", "warning")
        return tools.get_item_information(action_args)

    def sort_sources(self, item_information, sources_list):
        """
        Method to handle source filtering, sorting and notifications
        :param item_information: The item information
        :type item_information: dict
        :param sources_list: the list of sources to be sorted
        :type sources_list list
        :return: Filtered and Sorted sources
        :rtype: list
        """
        sources = SourceSorter(item_information).sort_sources(sources_list)
        if sources is None or len(sources) < 1:
            g.cancel_playback()
            remembered = getattr(self, "_negative_hit_message", None)
            if remembered:
                g.notification(g.ADDON_NAME, remembered, time=6000)
            else:
                g.notification(g.ADDON_NAME, g.get_language_string(30032), time=5000)
            return

        return sources


def show_persistent_window_if_required(item_information):
    """
    Displays a constant window in the background, used to fill in gaps between windows dropping and opening
    :param item_information:
    :return: WindowDialog
    """
    if g.get_int_setting('general.scrapedisplay') != 0 or g.get_runtime_setting('tempSilent'):
        return None
    from resources.lib.database.skinManager import SkinManager
    from resources.lib.gui.windows.persistent_background import PersistentBackground

    background = PersistentBackground(
        *SkinManager().confirm_skin_path('persistent_background.xml'), item_information=item_information
    )
    background.set_text(g.get_language_string(30030))
    background.show()
    return background
