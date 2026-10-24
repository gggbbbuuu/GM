import sqlite3
import sys
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

    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=torrentCacheCleanup")')
    if not g.wait_for_abort(15):  # Stagger the startup RunPlugins onto separate ticks so their plugin
        xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=undesirablesStartup")')
    if not g.wait_for_abort(15):  # interpreters are never created all at once (deadlock risk under RLI)
        xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=updateAnimeMappings")')

    g.wait_for_abort(15)  # Let widget loads settle. Trimmed from 30s - the two staggered ticks above now cover the rest.

    # Restore any enabled flags Account Manager re-enabled against the user's intent.
    # AM's startup sync runs within the first 30s; this fires after it has finished.
    protect_enabled_flags()

    while not monitor.abortRequested():
        xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=runMaintenance")')
        if not g.wait_for_abort(15):  # Sleep to make sure tokens refreshed during maintenance
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncTraktActivities")')
        if not g.wait_for_abort(15):  # Stagger the provider syncs onto separate ticks so their plugin
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncMDBListActivities")')
        if not g.wait_for_abort(15):  # interpreters are never created all at once (deadlock risk under RLI)
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncSimklActivities")')
        if not g.wait_for_abort(15):  # Sleep to let the provider syncs above actually complete first
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=bridgeSync")')
        if not g.wait_for_abort(15):  # Sleep to make sure we don't possibly clobber settings
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=cleanOrphanedMetadata")')
        if not g.wait_for_abort(15):  # Sleep to make sure we don't possibly clobber settings
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=updateLocalTimezone")')
        if g.wait_for_abort(60 * randint(13, 17)):
            break
finally:
    xbmcgui.Window(10000).clearProperty('seren.service.ready')
    del monitor
    g.deinit()
