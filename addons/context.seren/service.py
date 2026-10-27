import time

import xbmc
import xbmcaddon

SEREN_ADDON_ID = "plugin.video.seren"

properties = [
    "context.seren.quickResume",
    "context.seren.shuffle",
    "context.seren.playFromRandomPoint",
    "context.seren.rescrape",
    "context.seren.rescrape_ss",
    "context.seren.sourceSelect",
    "context.seren.findSimilar",
    "context.seren.browseShow",
    "context.seren.browseSeason",
]

# properties gated on both this addon's own toggle AND the matching Seren watch-service
# actually being enabled/authorized, keyed by the Seren setting id used to check that
service_aware_properties = {
    "context.seren.traktManager": "trakt.auth",
    "context.seren.mdblistManager": "mdblist.enabled",
    "context.seren.simklManager": "simkl.auth",
}


# seconds between checks of Seren's own settings (see the loop at the bottom)
POLL_INTERVAL = 30
# every property is re-sent at least this often even if nothing changed, in case something else cleared one
FULL_REFRESH_INTERVAL = 600


class PropertiesUpdater(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        # property -> hidden (True = disabled/hidden) as last applied to the home window; empty so the
        # first pass applies everything
        self._applied = {}
        self._last_full = 0.0
        self._update_window_properties(force=True)

    def onSettingsChanged(self):
        self._update_window_properties(force=True)

    @staticmethod
    def _is_service_enabled(seren, seren_setting):
        if seren_setting == "trakt.auth":
            return bool(seren.getSetting("trakt.auth")) and seren.getSetting("trakt.enabled") != "false"
        if seren_setting == "mdblist.enabled":
            return seren.getSetting("mdblist.enabled") == "true" and bool(seren.getSetting("mdblist.apikey"))
        if seren_setting == "simkl.auth":
            return bool(seren.getSetting("simkl.auth")) and seren.getSetting("simkl.enabled") != "false"
        return False

    def _update_window_properties(self, force=False):
        # a fresh Addon() is constructed on every call rather than cached on self, since a
        # long-lived Addon object can snapshot settings at construction time and never see
        # later changes — this function now runs on a timer, not just on this addon's own
        # onSettingsChanged callback, so a stale cached handle is a real risk here
        addon = xbmcaddon.Addon()
        seren_addon = xbmcaddon.Addon(SEREN_ADDON_ID)

        if time.monotonic() - self._last_full >= FULL_REFRESH_INTERVAL:
            force = True
        if force:
            self._last_full = time.monotonic()

        desired = {}
        for prop in properties:
            desired[prop] = addon.getSetting(prop) == "false"

        for prop, seren_setting in service_aware_properties.items():
            manual_setting = addon.getSetting(prop)
            enabled = manual_setting != "false" and self._is_service_enabled(seren_addon, seren_setting)
            desired[prop] = not enabled

        # the property is only touched (and logged) when its state changed since the last pass, or on a
        # forced pass (this addon's own settings changed) — the 5 s poll used to re-send all 12 properties
        # and write 12 log lines every time even though nothing had changed
        for prop, hidden in desired.items():
            if not force and self._applied.get(prop) == hidden:
                continue
            if hidden:
                xbmc.executebuiltin(f"SetProperty({prop},false,home)")
            else:
                xbmc.executebuiltin(f"ClearProperty({prop},home)")
            xbmc.log(f'Context menu item {"disabled" if hidden else "enabled"}: {prop}')
            self._applied[prop] = hidden


xbmc.log("context.seren service: starting", xbmc.LOGINFO)

try:
    # start monitoring settings changes events
    properties_monitor = PropertiesUpdater()

    # onSettingsChanged only fires for this addon's own settings, not Seren's — poll
    # every POLL_INTERVAL s so the service-aware properties pick up Seren-side auth/enable changes
    while not properties_monitor.waitForAbort(POLL_INTERVAL):
        properties_monitor._update_window_properties()
except Exception as e:
    xbmc.log(f"context.seren service: error - {e}", xbmc.LOGERROR)
finally:
    del properties_monitor

xbmc.log("context.seren service: stopped", xbmc.LOGINFO)
