import sys


def _stdlib_first():
    # Kodi puts every add-on library folder ahead of the standard library. On Android those folders are on slow
    # external storage and a fresh interpreter lists each one on its first import, so look in the standard library
    # and Seren's own folders first. Same reorder TMDb Helper 7.0.6 ships; harmless when run again under
    # reuselanguageinvoker (already in order). Seren's Shield gain is unmeasured.
    try:
        import os

        std = os.path.normcase(os.path.normpath(os.path.dirname(os.__file__)))
        zipdir = os.path.dirname(std)

        def in_std(p):
            n = os.path.normcase(os.path.normpath(p))
            if "packages" in os.path.basename(n):
                return False  # site-packages / dist-packages hold third-party code that add-on libraries must override
            return n == std or n.startswith(std + os.sep) or (n.endswith(".zip") and os.path.dirname(n) == zipdir)

        own = ("plugin.video.seren", "script.module.requests", "script.module.beautifulsoup4", "script.module.unidecode",
               "script.module.myconnpy", "script.module.curl_cffi")
        front = [p for p in sys.path if in_std(p)]
        need = [p for p in sys.path if p not in front and any(name in p for name in own)]
        sys.path[:] = front + need + [p for p in sys.path if p not in front and p not in need]
    except Exception:
        pass


_stdlib_first()
del _stdlib_first

import sqlite3
from random import randint

import xbmc
import xbmcgui

from resources.lib.common import tools

if tools.is_stub():
    # noinspection PyUnresolvedReferences
    from mock_kodi import MOCK

from resources.lib.modules.globals import g

from resources.lib.modules.seren_version import do_version_change
from resources.lib.modules.serenMonitor import SerenMonitor
from resources.lib.modules.update_news import do_update_news
from resources.lib.modules.manual_timezone import validate_timezone_detected
from resources.lib.modules.locale_playback import recover_orphaned_locale_override
from resources.lib.modules.accountmgr_sync import sync_accountmgr_credentials, snapshot_enabled_flags, protect_enabled_flags

g.init_globals(sys.argv)
do_version_change()

# Snapshot user's intended enabled/disabled state BEFORE Account Manager runs its own
# startup sync, which re-enables services the user has intentionally disabled in Seren.
snapshot_enabled_flags()

# Sync credentials from Account Manager / sibling addons before pre-warming settings
# so all subsequent reads see the correct tokens without requiring manual re-auth.
sync_accountmgr_credentials()

# Pre-warm all settings into memory cache so plugin calls never hit the settings lock
_prewarm_count = g.SETTINGS_CACHE.pre_warm_settings(g.SETTINGS_PATH)

# Store immutable state in window properties so plugin calls skip full re-init
g._store_service_state()

# Pre-warm studio icons into window property so first list render doesn't block on listdir
_ = g.studio_icons

g.log("##################  STARTING SERVICE  ######################")
g.log(f"### {g.ADDON_ID} {g.VERSION}")
g.log(f"### Platform: {g.PLATFORM}")
g.log(f"### Python: {sys.version.split(' ', 1)[0]}")
g.log(f"### SQLite: {sqlite3.sqlite_version}")  # pylint: disable=no-member
g.log(f"### Detected Kodi Version: {g.KODI_VERSION}")
g.log(f"### Detected timezone: {repr(g.LOCAL_TIMEZONE.zone)}")
g.log(f"### Settings pre-warmed: {_prewarm_count}")
g.log("#############  SERVICE ENTERED KEEP ALIVE  #################")


def _sync_configured():
    """(trakt, mdblist, simkl): whether each service is enabled and signed in, the same checks the sync actions make
    before doing anything. A RunPlugin for a service that is not set up only starts and tears down an interpreter to
    do nothing, and the more interpreters start and stop, the more often Kodi's Python can deadlock on that."""
    try:
        trakt = bool(g.get_setting("trakt.auth")) and g.get_bool_setting("trakt.enabled", False)
        mdblist = g.get_bool_setting("mdblist.enabled") and bool(
            g.get_setting("mdblist.auth") or g.get_setting("mdblist.apikey")
        )
        simkl = g.get_bool_setting("simkl.enabled") and bool(g.get_setting("simkl.auth"))
    except Exception:
        return True, True, True  # cannot tell: keep running them all
    return trakt, mdblist, simkl

monitor = SerenMonitor()
try:
    # Signal to Account Manager (and any other addon) that Seren's service is ready.
    # Inside try so clearProperty() in finally is always paired with this setProperty.
    xbmcgui.Window(10000).setProperty('seren.service.ready', g.VERSION)
    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=longLifeServiceManager")')

    do_update_news()
    validate_timezone_detected()
    recover_orphaned_locale_override()
    try:
        g.clear_kodi_bookmarks()
    except TypeError:
        g.log(
            "Unable to clear bookmarks on service init. This is not a problem if it occurs immediately after install.",
            "warning",
        )

    # One interpreter runs the torrent cache cleanup, undesirables and anime mapping steps in turn
    # (three RunPlugins 15 s apart before 3.9.55 - each paid the 4.6-8.5 s interpreter start-up on the Shield).
    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=startupHousekeeping")')

    g.wait_for_abort(45)  # Let widget loads settle; same 45 s the three staggered ticks used to take before the first maintenance run

    # Restore any enabled flags Account Manager re-enabled against the user's intent.
    # AM's startup sync runs within the first 30s; this fires after it has finished.
    protect_enabled_flags()

    while not monitor.abortRequested():
        xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=runMaintenance")')
        trakt = mdblist = simkl = False
        if not g.wait_for_abort(15):  # Sleep to make sure tokens refreshed during maintenance
            trakt, mdblist, simkl = _sync_configured()
            if trakt:
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncTraktActivities")')
        if not g.wait_for_abort(15):  # Stagger the provider syncs onto separate ticks so their plugin
            if mdblist:
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncMDBListActivities")')
        if not g.wait_for_abort(15):  # interpreters are never created all at once (deadlock risk under RLI)
            if simkl:
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncSimklActivities")')
        if not g.wait_for_abort(15):  # Sleep to let the provider syncs above actually complete first
            if trakt + mdblist + simkl >= 2:  # the bridge needs at least two configured services
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=bridgeSync")')
        if not g.wait_for_abort(30):  # Sleep to make sure we don't possibly clobber settings (the timezone check writes one)
            # Orphaned-metadata cleanup (at most once a day) then the local timezone check, in one interpreter.
            # 30 s = the gap the timezone check had after bridgeSync when it was its own RunPlugin.
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=cycleHousekeeping")')
        if g.wait_for_abort(60 * randint(13, 17)):
            break
finally:
    xbmcgui.Window(10000).clearProperty('seren.service.ready')
    del monitor
    g.deinit()
