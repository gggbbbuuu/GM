import calendar
import datetime
import threading

import xbmc

from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g

PREV_BUTTON_ID = 3001
NEXT_BUTTON_ID = 3002
GRID_ID = 1000
CLOSE_BUTTON_ID = 2999

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2

_PREFETCH_FORWARD_DELAY = 3.0   # land on a month, fetch the next one after this
_PREFETCH_BACKWARD_DELAY = 8.0  # ...then the previous one 5s after that (3s + 5s)


def _prefetch_month(year, month):
    """threading.Timer callback - module-level and takes only plain values,
    never a bound window method or `self`. A Timer holding the window instance
    would keep it alive past open_movie_calendar()'s `del window`, and a stray
    callback firing after close() would risk touching torn-down controls."""
    if g.abort_requested():
        return
    try:
        from resources.lib.modules.movie_calendar_data import get_movie_calendar_month

        get_movie_calendar_month(year, month, prefetch=True)
        g.log(f"movie_calendar_window: prefetched {year}-{month:02d}", "debug")
    except Exception as e:
        g.log(f"movie_calendar_window: prefetch of {year}-{month:02d} failed: {e}", "warning")


class MovieCalendarWindow(BaseWindow):
    def __init__(self, xml_file, location, item_information=None):
        super().__init__(xml_file, location, item_information=item_information)
        self.grid_control = None
        self.movies = []
        today = datetime.date.today()
        self.year, self.month = today.year, today.month
        self._prefetch_timers = []

    def onInit(self):
        self.grid_control = self.getControlList(GRID_ID)
        try:
            self._populate_grid()
            # an empty grid cannot take focus: land on Next, so an empty month can be paged straight away
            self.set_default_focus(self.grid_control, NEXT_BUTTON_ID, control_list_reset=True)
        finally:
            # closes any busy dialog - must run even if population raises, matching ShowCalendarWindow
            super().onInit()

        self._schedule_prefetch()

    def _schedule_prefetch(self):
        """Rolling background prefetch: land on a month, warm the adjacent
        months' MovieCalendarDatabase bookkeeping so paging there is a cache
        hit instead of a live Trakt call. Re-triggered on every navigation -
        _cancel_prefetch() drops any still-pending timers for the position
        just left, so rapid paging only ever prefetches around the month the
        user actually lands on."""
        from resources.lib.modules.movie_calendar_data import shift_month

        self._cancel_prefetch()

        fwd_year, fwd_month = shift_month(self.year, self.month, 1)
        back_year, back_month = shift_month(self.year, self.month, -1)

        fwd_timer = threading.Timer(_PREFETCH_FORWARD_DELAY, _prefetch_month, args=(fwd_year, fwd_month))
        back_timer = threading.Timer(_PREFETCH_BACKWARD_DELAY, _prefetch_month, args=(back_year, back_month))
        fwd_timer.daemon = True
        back_timer.daemon = True
        self._prefetch_timers = [fwd_timer, back_timer]
        fwd_timer.start()
        back_timer.start()

    def _cancel_prefetch(self):
        for timer in self._prefetch_timers:
            timer.cancel()
        self._prefetch_timers = []

    def close(self):
        self._cancel_prefetch()
        super().close()

    def _populate_grid(self):
        from resources.lib.modules.movie_calendar_data import get_movie_calendar_month

        self.grid_control.reset()
        self.setProperty("month_year_label", f"{calendar.month_name[self.month]} {self.year}")
        self.movies = get_movie_calendar_month(self.year, self.month)
        for movie in self.movies:
            self.grid_control.addItem(self._build_tile_item(movie))
        if self.movies:
            self.clearProperty("empty_text")
        else:
            # Region and language filters compose as AND on Trakt's side (confirmed live:
            # countries=jp&languages=en alone returns 0 over a 30-day window) - a mismatched
            # pair reads as a broken calendar without this distinct message.
            if g.get_setting("calendar.region") and g.get_setting("calendar.language"):
                self.setProperty("empty_text", g.get_language_string(31538))
            else:
                self.setProperty("empty_text", g.get_language_string(31518))

    @staticmethod
    def _build_tile_item(movie):
        info = movie.get("info") or {}
        list_item = BaseWindow.get_list_item_with_properties(movie, label=info.get("title") or "")
        list_item.setProperty("movie_title", info.get("title") or "")
        list_item.setProperty("release_date_label", movie.get("_calendar_date_label") or "")
        list_item.setProperty("release_countdown", movie.get("_calendar_countdown") or "")
        list_item.setProperty("rating_display", movie.get("_calendar_rating_display") or "")
        list_item.setProperty("release_status", movie.get("_calendar_status") or "upcoming")
        return list_item

    def _navigate_month(self, delta):
        from resources.lib.modules.movie_calendar_data import shift_month

        g.show_busy_dialog()
        try:
            self.year, self.month = shift_month(self.year, self.month, delta)
            self._populate_grid()
            self.set_default_focus(self.grid_control, NEXT_BUTTON_ID, control_list_reset=True)
        finally:
            g.close_busy_dialog()
        # After the busy dialog closes, not before - the 3s/8s clock should start
        # when the user is actually looking at the new month.
        self._schedule_prefetch()

    def handle_action(self, action_id, control_id=None):
        # movie_calendar.xml redirects the grid's onleft/onright to these same button ids
        # at a genuine row boundary (see its comment) - Left/Right paging here is what
        # actually happens, matching ShowCalendarWindow's own Left/Right-pages-day precedent.
        # An empty month has no grid to focus, so there Left/Right page the month from whichever
        # control has the focus.
        if not self.movies and action_id in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT):
            self._navigate_month(-1 if action_id == ACTION_MOVE_LEFT else 1)
            return
        if action_id == ACTION_MOVE_LEFT and control_id == PREV_BUTTON_ID:
            self._navigate_month(-1)
            return
        if action_id == ACTION_MOVE_RIGHT and control_id == NEXT_BUTTON_ID:
            self._navigate_month(1)
            return

        if action_id != 7:
            return
        if control_id == CLOSE_BUTTON_ID:
            self.close()
        elif control_id == PREV_BUTTON_ID:
            self._navigate_month(-1)
        elif control_id == NEXT_BUTTON_ID:
            self._navigate_month(1)
        elif control_id == GRID_ID:
            self._play_selected()

    def _play_selected(self):
        position = self.grid_control.getSelectedPosition()
        if position < 0:
            return
        args = self.movies[position].get("args")
        if not args:
            return
        self.close()
        url = g.create_url(g.BASE_URL, {"action": "getSources", "action_args": args})
        xbmc.executebuiltin(f'RunPlugin("{url}")')


def open_movie_calendar():
    from resources.lib.database.skinManager import SkinManager

    g.show_busy_dialog()
    window = MovieCalendarWindow(*SkinManager().confirm_skin_path("movie_calendar.xml"))
    try:
        window.doModal()
    finally:
        g.close_busy_dialog()
        del window
