import os
import json
import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon(id="script.module.jetextractors")
_ADDON_DATA_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
_CONFIG_FILE = os.path.join(_ADDON_DATA_DIR, 'settings.json')

_config = None

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
