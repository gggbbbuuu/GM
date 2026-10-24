import datetime
import threading

import xbmc
import xbmcgui

from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules import calendar_view as view
from resources.lib.modules.globals import g

""" The My Watch List Calendar and the TV Shows Calendar, one window class for both.

Both are one scrollable page: a header row per show with that show's episodes under it (air time, date, aired / today /
in N days / watched, a Premiere badge, a tick on watched episodes). Select on a show lists that show's unwatched
episodes (the Back button or the back key returns to the page); Select on an episode plays it.

MODE_WATCHLIST: your episodes from 13 days back to 30 days ahead (calendar_data.get_calendar_episodes()).
MODE_DAY: every show airing on ONE day (tv_schedule_data.get_schedule_week(), cached per week for as long as the window
is open); Left / Right or the < > buttons change the day, Today jumps back. Days are LOCAL days: stored air dates are UTC,
so a day can need rows from the neighbouring UTC week (see calendar_view.py).
"""

LIST_ID = 1000
CLOSE_BUTTON_ID = 2999
PREV_BUTTON_ID = 3001
NEXT_BUTTON_ID = 3002
BACK_BUTTON_ID = 3003
TODAY_BUTTON_ID = 3004

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_SELECT = 7

MODE_WATCHLIST = "watchlist"
MODE_DAY = "day"
VIEW_SHOWS = "shows"
VIEW_UNWATCHED = "unwatched"

WATCHLIST_DAYS_BACK = 13   # calendar_data.get_calendar_episodes()'s window: 13 days back through 30 days ahead
WATCHLIST_DAYS_AHEAD = 30

_PREFETCH_FORWARD_DELAY = 3.0   # land on a week, fetch the next one after this
_PREFETCH_BACKWARD_DELAY = 8.0  # ...then the previous one 5s after that (3s + 5s)


def _prefetch_week(week_start):
    """threading.Timer callback - module-level and takes only a plain datetime.date, never a bound window method
    or `self`: a Timer holding the window instance would keep it alive past the opener's `del window`, and a stray
    callback firing after close() would risk touching torn-down controls."""
    if g.abort_requested():
        return
    try:
        from resources.lib.modules.tv_schedule_data import prefetch_schedule_week

        prefetch_schedule_week(week_start)
        g.log(f"show_calendar_window: prefetched week of {week_start}", "debug")
    except Exception as e:
        g.log(f"show_calendar_window: prefetch of week {week_start} failed: {e}", "warning")


def _weekday_name(day):
    # Kodi core localized-string ids: 11 = Monday .. 17 = Sunday (xbmc.getLocalizedString, not this addon's strings)
    return xbmc.getLocalizedString(11 + day.weekday())


class ShowCalendarWindow(BaseWindow):
    def __init__(self, xml_file, location, mode, item_information=None):
        super().__init__(xml_file, location, item_information=item_information)
        self.mode = mode
        self.today = datetime.date.today()
        self.day = self.today
        self.list_control = None
        self._view = VIEW_SHOWS
        self._rows = []             # the row entries behind the list control's items, same order
        self._saved_position = 0
        self._watchlist_episodes = None
        self._weeks = {}            # week_start -> get_schedule_week() rows, fetched once per window
        self._prefetch_timers = []
        self._prefetch_week_start = None
        self._time_format = xbmc.getRegion("time")
        self._date_format = xbmc.getRegion("dateshort")

    # region window life-cycle

    def onInit(self):
        self.list_control = self.getControlList(LIST_ID)
        self.setProperty("window_title", g.get_language_string(31539 if self.mode == MODE_DAY else 31472))
        if self.mode == MODE_DAY:
            self.setProperty("day_mode", "True")
        try:
            self._show_overview()
        finally:
            # closes any busy dialog - must run even if population raises
            super().onInit()
        self._schedule_prefetch()

    def close(self):
        self._cancel_prefetch()
        super().close()

    def _schedule_prefetch(self):
        """Rolling background prefetch (day mode): land on a week, warm the adjacent weeks' TvScheduleDatabase
        bookkeeping so paging there is a cache hit instead of a live Trakt call. Only re-armed when the day moves
        into another week - _cancel_prefetch() drops any still-pending timers for the week just left."""
        if self.mode != MODE_DAY:
            return
        from resources.lib.modules.tv_schedule_data import shift_week, week_start_for

        week_start = week_start_for(self.day)
        if week_start == self._prefetch_week_start:
            return
        self._cancel_prefetch()
        self._prefetch_week_start = week_start
        fwd_timer = threading.Timer(_PREFETCH_FORWARD_DELAY, _prefetch_week, args=(shift_week(week_start, 1),))
        back_timer = threading.Timer(_PREFETCH_BACKWARD_DELAY, _prefetch_week, args=(shift_week(week_start, -1),))
        fwd_timer.daemon = True
        back_timer.daemon = True
        self._prefetch_timers = [fwd_timer, back_timer]
        fwd_timer.start()
        back_timer.start()

    def _cancel_prefetch(self):
        for timer in self._prefetch_timers:
            timer.cancel()
        self._prefetch_timers = []

    # endregion

    # region data

    def _load_episodes(self):
        if self.mode == MODE_DAY:
            return self._day_episodes()
        if self._watchlist_episodes is None:
            from resources.lib.modules.calendar_data import get_calendar_episodes

            self._watchlist_episodes = get_calendar_episodes()
        return self._watchlist_episodes

    def _day_episodes(self):
        """Episodes airing on self.day LOCAL time. Stored air dates are UTC, so the local day can hold rows from the
        UTC day before or after: load the weeks that the local day's UTC dates fall in (once per window - the watchlist layer of
        get_schedule_week() is never cached and costs live lookups) and keep the rows whose local day matches."""
        from resources.lib.modules.tv_schedule_data import get_schedule_week, week_start_for

        starts = sorted({week_start_for(d) for d in view.utc_dates_of_local_day(self.day)})
        rows = []
        for start in starts:
            if start not in self._weeks:
                self._weeks[start] = get_schedule_week(start)
            rows.extend(self._weeks[start])
        return view.episodes_on_local_day(rows, self.day)

    @staticmethod
    def _unwatched_episodes(show_row):
        """Unwatched episodes of the show's latest season in the calendar (the season it is airing)."""
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase

        show_id = show_row.get("trakt_show_id")
        if not show_id:
            return []
        season_id = show_row.get("trakt_season_id")
        db = ShowsDatabase()
        if season_id:
            episodes = db.get_episode_list(show_id, trakt_season_id=season_id, hide_unaired=False, hide_watched=True)
        else:
            episodes = db.get_episode_list(show_id, hide_unaired=False, hide_watched=True)
            episodes = [e for e in episodes or [] if (e.get("info") or {}).get("season") == show_row.get("season")]
        return [e for e in episodes or [] if e and ((e.get("info") or {}).get("season") or 0) > 0 and not view.is_watched(e)]

    # endregion

    # region views

    def _show_overview(self, position=0):
        self._view = VIEW_SHOWS
        self.clearProperty("view_unwatched")
        if self.mode == MODE_DAY:
            if self.day != self.today:  # the Today button shows only when another day than today is open
                self.setProperty("not_today", "True")
            else:
                self.clearProperty("not_today")
            label = f"{_weekday_name(self.day)} {self.day.strftime(self._date_format)}"
            if self.day == self.today:
                label = f"{label} {g.get_language_string(31599)}"
            self.setProperty("center_label", label)
            empty_text = g.get_language_string(31543 if g.get_setting("calendar.region") and g.get_setting("calendar.language") else 31584)
        else:
            start = self.today - datetime.timedelta(days=WATCHLIST_DAYS_BACK)
            end = self.today + datetime.timedelta(days=WATCHLIST_DAYS_AHEAD)
            self.setProperty("center_label", f"{start.strftime(self._date_format)} - {end.strftime(self._date_format)}")
            empty_text = g.get_language_string(31474)

        try:
            episodes = [e for e in self._load_episodes() or [] if e]
            rows = view.build_overview(episodes, self.today)
        except Exception as exc:  # a failed load must not leave the window dead
            g.log(f"show_calendar_window: could not load the calendar: {exc}", "error")
            rows = []
        self._set_rows(rows, empty_text, position)

    def _show_unwatched(self, show_row, position):
        self._saved_position = position
        self._view = VIEW_UNWATCHED
        self.setProperty("view_unwatched", "True")
        self.setProperty("center_label", f"{show_row['title']} - {g.get_language_string(31586)}")
        try:
            episodes = self._unwatched_episodes(show_row)
            rows = view.episode_rows(episodes, self.today)
        except Exception as exc:
            g.log(f"show_calendar_window: could not load the unwatched episodes of {show_row.get('trakt_show_id')}: {exc}", "error")
            rows = []
        self._set_rows(rows, g.get_language_string(31585))

    def _set_rows(self, rows, empty_text, position=0):
        self._rows = rows
        self.list_control.reset()
        self.list_control.addItems([self._build_item(r) for r in rows])
        if rows:
            self.clearProperty("empty_text")
            self.setFocusId(LIST_ID)
            if 0 < position < len(rows):
                self.list_control.selectItem(position)
        else:
            self.setProperty("empty_text", empty_text)
            # an empty list cannot take focus: land on the day buttons (an empty day is common), else on Close
            self.setFocusId(NEXT_BUTTON_ID if self.mode == MODE_DAY and self._view == VIEW_SHOWS else CLOSE_BUTTON_ID)

    def _navigate_day(self, delta):
        self._go_to_day(self.day + datetime.timedelta(days=delta))

    def _go_to_day(self, day):
        g.show_busy_dialog()
        try:
            self.day = day
            self._show_overview()
        finally:
            g.close_busy_dialog()
        self._schedule_prefetch()

    # endregion

    # region list items

    def _build_item(self, row):
        return self._build_show_item(row) if row["type"] == "show" else self._build_episode_item(row)

    @staticmethod
    def _first_art(episode, *keys):
        art = episode.get("art") or {}
        for key in keys:
            if art.get(key):
                return art[key]
        return ""

    def _build_show_item(self, row):
        parts = [g.get_language_string(31595 if row["total"] == 1 else 31596) % row["total"]]
        if row["unaired"]:
            parts.append(g.get_language_string(31597) % row["unaired"])
        if row["to_watch"]:
            parts.append(g.get_language_string(31598) % row["to_watch"])

        item = xbmcgui.ListItem(label=row["title"], offscreen=True)
        item.setProperty("row_type", "show")
        item.setProperty("show_summary", "  -  ".join(parts))
        source = row["poster_source"]
        art = {
            "poster": self._first_art(source, "tvshow.poster", "poster"),
            "fanart": self._first_art(source, "tvshow.fanart", "fanart"),
        }
        item.setArt({k: v for k, v in art.items() if v})
        return item

    def _build_episode_item(self, row):
        label = f"{row['code']}. {row['title']}" if row["title"] else row["code"]
        item = BaseWindow.get_list_item_with_properties(row["episode"], label=label)
        item.setProperty("row_type", "episode")
        item.setProperty("air_state", row["state"])
        text = g.get_language_string(row["status_id"])
        item.setProperty("air_status", text % row["status_count"] if row["status_count"] else text)
        item.setProperty("row_date", row["day"].strftime(self._date_format) if row["day"] else "")
        item.setProperty("air_time", view.format_air_time(row["air"], self._time_format))
        item.setProperty("rating_display", view.rating_text(row["episode"]))
        if row["badge_id"]:
            item.setProperty("row_badge", g.get_language_string(row["badge_id"]))
        return item

    # endregion

    # region input

    def onAction(self, action):
        action_id = action.getId()
        if action_id in self.action_exitkeys_id:
            self._go_back()
            return
        # Day mode: Left / Right on the list is the previous / next day (the list's own left / right point back at it).
        # An empty day has no list to focus, so there Left / Right change the day from whichever button has the focus.
        if (
            self.mode == MODE_DAY
            and self._view == VIEW_SHOWS
            and action_id in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT)
            and (self.getFocusId() == LIST_ID or not self._rows)
        ):
            self._navigate_day(-1 if action_id == ACTION_MOVE_LEFT else 1)
            return
        super().onAction(action)

    def handle_action(self, action_id, control_id=None):
        if action_id != ACTION_SELECT:
            return
        if control_id == CLOSE_BUTTON_ID:
            self.close()
        elif control_id == BACK_BUTTON_ID:
            self._go_back()
        elif control_id == PREV_BUTTON_ID:
            self._navigate_day(-1)
        elif control_id == NEXT_BUTTON_ID:
            self._navigate_day(1)
        elif control_id == TODAY_BUTTON_ID:
            self._go_to_day(self.today)
        elif control_id == LIST_ID:
            self._select()

    def _go_back(self):
        if self._view == VIEW_UNWATCHED:
            self._show_overview(self._saved_position)
        else:
            self.close()

    def _select(self):
        position = self.list_control.getSelectedPosition()
        if position < 0 or position >= len(self._rows):
            return
        row = self._rows[position]
        if row["type"] == "show":
            self._show_unwatched(row, position)
            return
        args = row["episode"].get("args")
        if not args:
            return
        self.close()
        url = g.create_url(g.BASE_URL, {"action": "getSources", "action_args": args})
        xbmc.executebuiltin(f'RunPlugin("{url}")')

    # endregion


def _open(mode):
    from resources.lib.database.skinManager import SkinManager

    g.show_busy_dialog()
    window = ShowCalendarWindow(*SkinManager().confirm_skin_path("show_calendar.xml"), mode=mode)
    try:
        window.doModal()
    finally:
        g.close_busy_dialog()
        del window


def open_watchlist_calendar():
    _open(MODE_WATCHLIST)


def open_tv_schedule():
    _open(MODE_DAY)
