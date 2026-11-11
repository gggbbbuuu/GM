"""When Seren's cross-service sync (modules/bridgeSync.py) runs, besides its fixed interval (crosssync.intervalMinutes,
the slow safety net). Port of TMDb Helper 7.0.42's monitor/bridge_trigger.py.

Setting crosssync.dynamic (default on, only meaningful while crosssync.enabled is on) adds two triggers, checked every
few seconds by a small thread in the service:

  - after a change made in Seren: a mark (watched / unwatched, lists) reaches g.trigger_widget_refresh(), a playback
    ends in the player: both call request_run() (a Home window property, so any interpreter can set it). The bridge
    runs once the requests have been quiet for _DEBOUNCE seconds, so marking five episodes gives one run.
  - when a service reports new activity: every _POLL_SECONDS one plugin interpreter (action bridgeTriggerPoll) reads
    Trakt's, MDBList's and Simkl's cheap last-activity stamps FRESH (never the copies the activity syncs keep) and
    compares them with the stamps saved in the bridge meta by the previous poll or run. A change made on the website
    or in an app starts a run in that same interpreter. The first poll only sets the baseline.

A run that leaves removals waiting for their second check (BridgeSync._removals) is followed by another after
_FOLLOWUP_DELAY seconds, up to _MAX_FOLLOWUPS times; a removal also has to have been missing for
bridgeSync._REMOVE_CONFIRM_SECONDS, so two reads made seconds apart can never confirm each other.

The service thread does no network work and holds no token: the reads and the run happen in RunPlugin interpreters, like
every other heavy job in Seren. It never starts one while a video plays (the request stays and is served afterwards).
"""
import threading
import time

import xbmc

from resources.lib.modules.globals import g

REQUEST_KEY = "bridge.requested"  # runtime setting (Home window property): time of the newest request
FINISHED_KEY = "bridge.finished"  # time the last triggered run / poll ended (written by bridgeSync, even when it did nothing)
PENDING_KEY = "bridge.pending"  # True when a run that really happened left removals waiting for their second check

_TICK = 5  # seconds between looks at the request
_DEBOUNCE = 20  # seconds the requests must have been quiet
_MIN_GAP = 30  # seconds between two started runs
POLL_SECONDS = 300  # one interpreter per poll: on the Shield each one costs 5-8 s to start, so not faster than this
_FOLLOWUP_DELAY = 190  # a little after bridgeSync._REMOVE_CONFIRM_SECONDS
_MAX_FOLLOWUPS = 3
_START_WAIT = 90  # seconds to wait for a started interpreter to show its running flag or its end marker
_RUN_WAIT_MAX = 30 * 60  # a Simkl-paced run can take long; give up waiting for its end marker after this
_RUNNING_KEY = "seren.bridgeSync.running"


def request_run():
    """Ask the service to run the bridge soon. Safe to call from any interpreter."""
    try:
        g.set_runtime_setting(REQUEST_KEY, time.time())
    except Exception:
        pass


def publish_finished(pending):
    try:
        g.set_runtime_setting(PENDING_KEY, bool(pending))
        g.set_runtime_setting(FINISHED_KEY, time.time())
    except Exception:
        pass


def dynamic_enabled():
    return bool(g.get_bool_setting("crosssync.enabled", False) and g.get_bool_setting("crosssync.dynamic", True))


class BridgeTrigger(threading.Thread):
    def __init__(self):
        super().__init__(name="seren-bridge-trigger", daemon=True)
        self._stop_event = threading.Event()
        self._last_poll = time.time()  # the first poll is one interval after the service starts
        self._last_start = 0.0
        self._started_at = 0.0  # when the interpreter we are waiting for was started; 0 = not waiting
        self._followup_at = 0.0
        self._followups = 0

    def stop(self):
        self._stop_event.set()

    def run(self):
        monitor = xbmc.Monitor()
        while not self._stop_event.is_set() and not monitor.abortRequested():
            if monitor.waitForAbort(_TICK):
                break
            try:
                self._tick()
            except Exception as e:
                g.log(f"BridgeTrigger error: {e}", "warning")

    def _start(self, action, reason):
        now = time.time()
        g.log(f"BridgeTrigger: starting {action} - {reason}", "debug" if action == "bridgeTriggerPoll" else "info")
        xbmc.executebuiltin(f'RunPlugin("plugin://plugin.video.seren/?action={action}")')
        self._last_start = now
        self._started_at = now

    def _tick(self):
        if not dynamic_enabled():
            return
        now = time.time()
        if self._started_at:
            finished = g.get_float_runtime_setting(FINISHED_KEY, 0.0)
            # a run that never started (dropped RunPlugin, crashed interpreter) shows neither its running flag nor an end marker
            lost = now > self._started_at + _START_WAIT and not g.get_runtime_setting(_RUNNING_KEY) and finished < self._started_at
            if finished >= self._started_at or lost or now > self._started_at + _RUN_WAIT_MAX:
                self._started_at = 0.0
                if g.get_bool_runtime_setting(PENDING_KEY, False) and self._followups < _MAX_FOLLOWUPS:
                    self._followups += 1
                    self._followup_at = time.time() + _FOLLOWUP_DELAY
                else:
                    self._followups = 0
                    self._followup_at = 0.0
            else:
                return
        if g.get_runtime_setting(_RUNNING_KEY):
            return  # a run (the service's own interval run, or a long one of ours) is going
        requested = g.get_float_runtime_setting(REQUEST_KEY, 0.0)
        action = reason = None
        if requested and now - requested >= _DEBOUNCE:
            action, reason = "bridgeSyncNow", "a change made in Seren"
        elif self._followup_at and now >= self._followup_at:
            action, reason = "bridgeSyncNow", "removals waiting for their second check"
        elif now - self._last_poll >= POLL_SECONDS:
            action, reason = "bridgeTriggerPoll", "checking the services' activity stamps"
        if not action:
            return
        if now - self._last_start < _MIN_GAP:
            return
        if xbmc.Player().isPlaying():
            return
        if action == "bridgeTriggerPoll":
            self._last_poll = now
        else:
            if requested and g.get_float_runtime_setting(REQUEST_KEY, 0.0) == requested:
                g.clear_runtime_setting(REQUEST_KEY)  # a request made while the run is going starts another
            self._followup_at = 0.0
        self._start(action, reason)
