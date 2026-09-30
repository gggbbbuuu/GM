import os
import json
import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon(id="script.module.jetextractors")
_ADDON_DATA_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
_CONFIG_FILE = os.path.join(_ADDON_DATA_DIR, 'settings.json')

_config = None
_EXTRACTOR_EXCLUDE_NAMES = {"TelegramXtream", "HomeIPTV", "MyIPTV"}

def _save_config():
    global _config
    try:
        if not os.path.exists(_ADDON_DATA_DIR):
            os.makedirs(_ADDON_DATA_DIR, exist_ok=True)
        with open(_CONFIG_FILE, 'w') as f:
            json.dump(_config, f, indent=2)
    except Exception:
        pass

def _load_config(force_reload=False):
    global _config
    if _config is not None and not force_reload:
        return _config
    _config = {
        "debug_logging": False,
        "telegramxtream_enabled": False,
        "homeiptv_enabled": False,
        "myiptv_enabled": False,
        "disabled_extractors": [],
    }
    try:
        if not os.path.exists(_ADDON_DATA_DIR):
            os.makedirs(_ADDON_DATA_DIR, exist_ok=True)
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _config.update(data)
        else:
            _save_config()
    except Exception:
        pass
    return _config

def reload_config():
    """Force reload config from disk."""
    global _config
    _config = None
    return _load_config(force_reload=True)

def is_debug_enabled():
    return _load_config(force_reload=True).get("debug_logging", False)

def set_debug_logging(enabled):
    _load_config()
    _config["debug_logging"] = bool(enabled)
    _save_config()

def is_telegramxtream_enabled():
    return _load_config(force_reload=True).get("telegramxtream_enabled", False)

def set_telegramxtream_enabled(enabled):
    _load_config()
    _config["telegramxtream_enabled"] = bool(enabled)
    _save_config()

def is_homeiptv_enabled():
    return _load_config(force_reload=True).get("homeiptv_enabled", False)

def set_homeiptv_enabled(enabled):
    _load_config()
    _config["homeiptv_enabled"] = bool(enabled)
    _save_config()

def is_myiptv_enabled():
    return _load_config(force_reload=True).get("myiptv_enabled", False)

def set_myiptv_enabled(enabled):
    _load_config()
    _config["myiptv_enabled"] = bool(enabled)
    _save_config()


def get_extractor_names():
    """Return a sorted list of all extractor names (excluding TelegramXtream, HomeIPTV, MyIPTV which have dedicated toggles)."""
    from .extractor import get_extractors
    names = []
    for ext in get_extractors():
        name = getattr(ext, "name", None) or ext.__class__.__name__
        if name in _EXTRACTOR_EXCLUDE_NAMES:
            continue
        names.append(name)
    return sorted(names)


def is_extractor_enabled(name):
    """Check if an extractor is enabled (not in the disabled_extractors list)."""
    _load_config()
    disabled_list = _config.get("disabled_extractors", [])
    import xbmc
    xbmc.log(f"[JetExtractors] is_extractor_enabled({name}): disabled_list={disabled_list}, enabled={name not in disabled_list}", xbmc.LOGDEBUG)
    return name not in disabled_list


def is_extractor_disabled(name):
    """Check if an extractor is disabled."""
    return not is_extractor_enabled(name)


def set_extractor_disabled(name, disabled):
    """Toggle an extractor's disabled state in the config file."""
    import xbmc
    _load_config()
    xbmc.log(f"[JetExtractors] set_extractor_disabled({name}, {disabled}): before disabled_extractors={_config.get('disabled_extractors', [])}", xbmc.LOGDEBUG)
    disabled_list = list(_config.get("disabled_extractors", []))
    if disabled and name not in disabled_list:
        disabled_list.append(name)
    elif not disabled and name in disabled_list:
        disabled_list.remove(name)
    _config["disabled_extractors"] = disabled_list
    xbmc.log(f"[JetExtractors] set_extractor_disabled({name}, {disabled}): after disabled_extractors={disabled_list}", xbmc.LOGDEBUG)
    _save_config()
    try:
        from .extractor import clear_extractor_cache
        clear_extractor_cache()
    except Exception:
        pass


def debug_log(msg, level=xbmc.LOGINFO):
    """Debug logging function - only logs when debug_logging is enabled."""
    try:
        if is_debug_enabled():
            xbmc.log(f"[JetExtractors] {msg}", level)
    except Exception:
        pass


def revalidate_telegramxtream():
    """Trigger a background revalidation of Telegram Xtream channels."""
    import threading
    from .extractors.telegram_xtream import scrape_telegram_sources

    def _run():
        try:
            count = scrape_telegram_sources()
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,TelegramXtream revalidation complete: %s channels,3000)' % count
            )
        except Exception as e:
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,Revalidation failed: %s,3000)' % str(e)
            )

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def revalidate_homeiptv():
    """Trigger a background revalidation of HomeIPTV channels."""
    import threading
    from .extractors.homeiptv import scrape_homeiptv_sources

    def _run():
        try:
            count = scrape_homeiptv_sources()
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,HomeIPTV revalidation complete: %s channels,3000)' % count
            )
        except Exception as e:
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,Revalidation failed: %s,3000)' % str(e)
            )

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def revalidate_myiptv():
    """Trigger a background revalidation of MyIPTV channels."""
    import threading
    from .extractors.myiptv import scrape_myiptv_sources

    def _run():
        try:
            count = scrape_myiptv_sources()
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,MyIPTV revalidation complete: %s channels,3000)' % count
            )
        except Exception as e:
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,Revalidation failed: %s,3000)' % str(e)
            )

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _refresh_sportsx():
    from .extractors.sportsx import _background_scrape
    _background_scrape()


def _refresh_foxxy():
    from .extractors.foxxy import _background_scrape
    _background_scrape()


def _refresh_homeiptv():
    from .extractors.homeiptv import _background_scrape
    _background_scrape()


def _refresh_myiptv():
    from .extractors.myiptv import _background_scrape
    _background_scrape()


def _refresh_telegramxtream():
    from .extractors.telegram_xtream import _background_scrape
    _background_scrape()


def _refresh_backdoor1():
    from .extractors.backdoor import Backdoor1
    extractor = Backdoor1()
    extractor._ensure_domains()
    extractor._fetch_channels()


def _refresh_backdoor2():
    from .extractors.backdoor2 import BckDr2
    extractor = BckDr2()
    extractor._fetch_events()


def _refresh_xyz():
    from .extractors.XYZ import XYZ
    extractor = XYZ()
    extractor._fetch_homepage_data()


def _refresh_timstreams():
    from .extractors.timstreams import TimStreams
    extractor = TimStreams()
    extractor.get_items()


def _refresh_cdnlivetv():
    from .extractors.cdnlivetv import _background_scrape
    _background_scrape()


def _build_store_registry():
    """Build registry of stores with staleness checks and refresh callbacks.

    Returns a list of dicts with keys:
        name: display name for logging
        store: the store module (has is_stale() and REFRESH_INTERVAL)
        enabled: callable() -> bool
        refresh: callable() -> None (does lazy imports internally)
    """
    from .util import (
        sportsx_store, foxxy_store, backdoor1_store, backdoor2_store,
        sling_store, timstreams_store, homeiptv_store, myiptv_store,
        cdnlivetv_store,
    )
    from .util import TelegramStore

    return [
        {
            "name": "SportsX",
            "store": sportsx_store,
            "enabled": lambda: is_extractor_enabled("SportsX"),
            "refresh": _refresh_sportsx,
        },
        {
            "name": "Foxxy",
            "store": foxxy_store,
            "enabled": lambda: is_extractor_enabled("Foxxy"),
            "refresh": _refresh_foxxy,
        },
        {
            "name": "Backdoor1",
            "store": backdoor1_store,
            "enabled": lambda: is_extractor_enabled("Backdoor1"),
            "refresh": _refresh_backdoor1,
        },
        {
            "name": "BckDr2",
            "store": backdoor2_store,
            "enabled": lambda: is_extractor_enabled("BckDr2"),
            "refresh": _refresh_backdoor2,
        },
        {
            "name": "XYZ",
            "store": sling_store,
            "enabled": lambda: is_extractor_enabled("XYZ"),
            "refresh": _refresh_xyz,
        },
        {
            "name": "TimStreams",
            "store": timstreams_store,
            "enabled": lambda: is_extractor_enabled("TimStreams"),
            "refresh": _refresh_timstreams,
        },
        {
            "name": "HomeIPTV",
            "store": homeiptv_store,
            "enabled": is_homeiptv_enabled,
            "refresh": _refresh_homeiptv,
        },
        {
            "name": "MyIPTV",
            "store": myiptv_store,
            "enabled": is_myiptv_enabled,
            "refresh": _refresh_myiptv,
        },
        {
            "name": "TelegramXtream",
            "store": TelegramStore,
            "enabled": is_telegramxtream_enabled,
            "refresh": _refresh_telegramxtream,
        },
        {
            "name": "CDNLiveTV",
            "store": cdnlivetv_store,
            "enabled": lambda: is_extractor_enabled("CDNLiveTV"),
            "refresh": _refresh_cdnlivetv,
        },
    ]


def _safe_refresh(store_name, refresh_func):
    """Run a refresh function in a try/except, logging errors."""
    try:
        refresh_func()
    except Exception as e:
        import xbmc
        debug_log(f"[BackgroundRefresh] {store_name} refresh failed: {e}", xbmc.LOGWARNING)


def refresh_stale_stores():
    """Check all streaming stores for staleness and refresh stale ones in background threads.

    Called periodically by the Kodi service to keep stores fresh without user interaction.
    """
    import threading
    registry = _build_store_registry()
    refreshed = []
    for entry in registry:
        if not entry["enabled"]():
            continue
        try:
            if entry["store"].is_stale():
                t = threading.Thread(
                    target=_safe_refresh,
                    args=(entry["name"], entry["refresh"]),
                    daemon=True,
                )
                t.start()
                refreshed.append(entry["name"])
        except Exception as e:
            debug_log(f"[BackgroundRefresh] Error checking {entry['name']}: {e}")
    if refreshed:
        debug_log(f"[BackgroundRefresh] Refreshed: {', '.join(refreshed)}")

def revalidate_homeiptv():
    """Trigger a background revalidation of HomeIPTV channels."""
    import threading
    from .extractors.homeiptv import scrape_homeiptv_sources

    def _run():
        try:
            count = scrape_homeiptv_sources()
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,HomeIPTV revalidation complete: %s channels,3000)' % count
            )
        except Exception as e:
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,Revalidation failed: %s,3000)' % str(e)
            )

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def revalidate_myiptv():
    """Trigger a background revalidation of MyIPTV channels."""
    import threading
    from .extractors.myiptv import scrape_myiptv_sources

    def _run():
        try:
            count = scrape_myiptv_sources()
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,MyIPTV revalidation complete: %s channels,3000)' % count
            )
        except Exception as e:
            import xbmc
            xbmc.executebuiltin(
                'Notification(JetExtractors,Revalidation failed: %s,3000)' % str(e)
            )

    t = threading.Thread(target=_run, daemon=True)
    t.start()
