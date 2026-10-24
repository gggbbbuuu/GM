import xbmcgui

from resources.lib.modules.globals import g
from resources.lib.third_party import pytz


def choose_region():
    current = g.get_setting("calendar.region")
    countries = sorted(
        ((code.lower(), name) for code, name in pytz.country_names.items()),
        key=lambda pair: pair[1],
    )
    codes = [code for code, _name in countries]
    labels = [name for _code, name in countries]
    try:
        preselect = codes.index(current) if current else -1
    except ValueError:
        preselect = -1
    index = xbmcgui.Dialog().select(g.get_language_string(31531), labels, preselect=preselect)
    if index != -1 and codes[index] != current:
        g.set_setting("calendar.region", codes[index])
        _invalidate_calendar_caches()


def choose_language():
    from resources.lib.modules.locale_playback import _stream_language_pairs

    current = g.get_setting("calendar.language")
    pairs = _stream_language_pairs()
    codes = [code for code, _name in pairs]
    labels = [name for _code, name in pairs]
    try:
        preselect = codes.index(current) if current else -1
    except ValueError:
        preselect = -1
    index = xbmcgui.Dialog().select(g.get_language_string(31535), labels, preselect=preselect)
    if index != -1 and codes[index] != current:
        g.set_setting("calendar.language", codes[index])
        _invalidate_calendar_caches()


def _invalidate_calendar_caches():
    """A changed region/language filter means any already-fetched TV Schedule
    week's or Movie Calendar month's item set was fetched under the old filter -
    drop all of it so the next view re-fetches under the new one. Both
    bookkeeping tables only track fetched trakt_ids per period; the actual
    content stays in the shared trakt_sync tables, untouched by this clear."""
    from resources.lib.database.tvSchedule import TvScheduleDatabase
    from resources.lib.database.movieCalendar import MovieCalendarDatabase

    TvScheduleDatabase().clear_all()
    MovieCalendarDatabase().clear_all()
