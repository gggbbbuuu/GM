import xbmcgui

from resources.lib.modules.globals import g


def configured_providers():
    providers = []
    if g.get_setting('trakt.auth') and g.get_bool_setting('trakt.enabled', False):
        providers.append('trakt')
    if g.get_setting('mdblist.enabled') == "true" and (g.get_setting('mdblist.auth') or g.get_setting('mdblist.apikey')):
        providers.append('mdblist')
    if g.get_setting('simkl.auth') and g.get_bool_setting('simkl.enabled'):
        providers.append('simkl')
    return providers


def clear_all_sync():
    """Clear-button gateway: resets each configured provider's sync cursor via its
    existing bare primitive, not clear_last_sync() - that already notifies per-provider,
    and firing 2-3 near-identical "Seren" toasts back to back (no submenu context left to
    tell them apart) would read as a duplicate-fire bug. One combined notification instead."""
    providers = configured_providers()
    cleared = []

    if 'trakt' in providers:
        from resources.lib.database.trakt_sync import TraktSyncDatabase

        TraktSyncDatabase().flush_activities()
        cleared.append("Trakt")

    if 'mdblist' in providers:
        from resources.lib.database.mdblist_sync import MDBListSyncDatabase

        MDBListSyncDatabase().set_base_activities()
        cleared.append("MDBList")

    if 'simkl' in providers:
        from resources.lib.database.simkl_sync import SimklSyncDatabase

        SimklSyncDatabase().set_base_activities()
        cleared.append("Simkl")

    if cleared:
        g.notification(g.ADDON_NAME, g.get_language_string(31127).format(", ".join(cleared)))


def force_all_sync():
    """Force-button gateway: calls each configured provider's existing, unchanged
    force-sync entry point and lets its own notification fire naturally - each is
    already content-differentiated by item count, so unlike Clear there's no
    identical-toast ambiguity to solve here."""
    providers = configured_providers()

    if 'trakt' in providers:
        from resources.lib.database.trakt_sync.activities import TraktSyncDatabase

        trakt_db = TraktSyncDatabase()
        trakt_db.flush_activities()
        trakt_db.sync_activities()

    if 'mdblist' in providers:
        from resources.lib.database.mdblist_sync.activities import MDBListSyncDatabase

        MDBListSyncDatabase().force_sync()

    if 'simkl' in providers:
        from resources.lib.database.simkl_sync.activities import SimklSyncDatabase

        SimklSyncDatabase().force_sync()

    if len(providers) >= 2:
        from resources.lib.modules.bridgeSync import run as run_bridge_sync

        run_bridge_sync(force=True)


def rebuild_all_sync():
    """Rebuild-button gateway: physically drops and recreates each configured provider's
    database tables (a heavier reset than Force/Clear's cursor-only reset - see each
    provider's re_build_database()), then resyncs. One confirm dialog up front covers
    every provider about to be wiped, since this is destructive; each provider then runs
    silently and lets its own resync notification fire naturally, same reasoning as
    force_all_sync() above."""
    providers = configured_providers()
    if not providers:
        return

    if not xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30179)):
        return

    if 'trakt' in providers:
        from resources.lib.database.trakt_sync import TraktSyncDatabase

        TraktSyncDatabase().re_build_database(silent=True)

    if 'mdblist' in providers:
        from resources.lib.database.mdblist_sync import MDBListSyncDatabase

        MDBListSyncDatabase().re_build_database(silent=True)

    if 'simkl' in providers:
        from resources.lib.database.simkl_sync import SimklSyncDatabase

        SimklSyncDatabase().re_build_database(silent=True)

    if len(providers) >= 2:
        from resources.lib.modules.bridgeSync import run as run_bridge_sync

        run_bridge_sync(force=True)
