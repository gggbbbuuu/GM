"""Presentation logic for the Calendar and TV Shows Calendar windows (show_calendar_window.py).

Pure functions over the normalized episode rows calendar_data.py and tv_schedule_data.py
already return - nothing here fetches from Trakt, Simkl or MDBList, so the grouping, the
status badges and the local-time handling can be unit-tested with fixture rows. Nothing in
this module touches a database.

Air dates: Seren stores an episode's air date as a naive UTC string ("2026-10-18T02:00:00",
g.datetime_to_string() strips the offset). A US evening episode therefore carries the NEXT
day's UTC date, and showing the stored clock time shows UTC rather than the viewer's time.
local_datetime() applies the zone rules of the air date itself (so a date after a daylight-
saving change converts correctly, not with today's offset); every day / time / status shown
by the two TV windows goes through it. A date-only value (no time part) has no clock time to
convert and is used as it is.
"""
import datetime

MIN_YEAR = 1900  # a stored "unknown" date can parse as year 1 / 1601; nothing real airs before this

# status ids (state, language string id) - see en_gb strings.po 31587-31591
STATE_WATCHED = "watched"
STATE_AIRED = "aired"
STATE_TODAY = "today"
STATE_UNAIRED = "unaired"
STRING_WATCHED = 31587
STRING_AIRED = 31588
STRING_TODAY = 31582
STRING_TOMORROW = 31589
STRING_IN_DAYS = 31590  # "In %d days"
STRING_NO_AIR_DATE = 31591

BADGE_NEW_SHOW = 31592
BADGE_PREMIERE = 31593


def _has_time(aired):
    return bool(aired) and len(aired) > 10


def local_datetime(aired):
    """Naive local datetime for a stored UTC air date, or None when there is no clock time
    to convert (empty, date-only, unparsable)."""
    if not _has_time(aired):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(aired.rstrip("Z")).replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone().replace(tzinfo=None)
    except (ValueError, OverflowError, OSError):
        return None


def local_date(aired):
    """The local calendar day an episode airs on (datetime.date), or None when unknown."""
    converted = local_datetime(aired)
    if converted is not None:
        day = converted.date()
    else:
        try:
            day = datetime.date.fromisoformat(aired[:10]) if aired else None
        except ValueError:
            day = None
    return day if day is not None and day.year >= MIN_YEAR else None


def format_air_time(aired, time_format):
    """Local air time in the user's Kodi time format, seconds dropped ("" when the date has no clock time)."""
    converted = local_datetime(aired)
    if converted is None:
        return ""
    return converted.strftime((time_format or "%H:%M").replace(":%S", ""))


def get_air_date(episode):
    """Same fallback chain calendar_data.get_air_date() / tv_schedule_data.get_air_date() use
    (kept here too so this module has no import dependency on either)."""
    info = episode.get("info") or {}
    return episode.get("air_date") or info.get("aired") or info.get("premiered")


def is_watched(episode):
    info = episode.get("info") or {}
    return bool(episode.get("play_count") or info.get("playcount"))


def rating_text(episode):
    """The Simkl/MDBList union score when the row carries one, else Trakt's rating - the same
    precedence the old windows used. "" when there is none."""
    value = episode.get("_calendar_rating_override")
    if value is None:
        value = episode.get("_schedule_rating_override")
    if value is None:
        value = (episode.get("info") or {}).get("rating")
    return f"{value:.1f}" if isinstance(value, (int, float)) and value else ""


def episode_code(info):
    season, number = info.get("season"), info.get("episode")
    if isinstance(season, int) and isinstance(number, int):
        return f"{season}x{number:02d}"
    return ""


def status(air_day, today, watched):
    """(state, string id, count) for an episode row's right-hand status. count only matters
    for STRING_IN_DAYS."""
    if watched:
        return STATE_WATCHED, STRING_WATCHED, 0
    if air_day is None:
        return STATE_UNAIRED, STRING_NO_AIR_DATE, 0
    days = (air_day - today).days
    if days < 0:
        return STATE_AIRED, STRING_AIRED, 0
    if days == 0:
        return STATE_TODAY, STRING_TODAY, 0
    if days == 1:
        return STATE_UNAIRED, STRING_TOMORROW, 0
    return STATE_UNAIRED, STRING_IN_DAYS, days


def badge_id(info):
    """Language string id of the badge for an episode, or None. Seren's episode data does not carry Trakt's
    episode_type, so only what the episode number proves is badged: episode 1 is a Premiere (New show in season 1).
    There is deliberately no Finale badge: Trakt's season episode_count only says how many episodes are listed so
    far, so "the last listed episode" would be flagged as a finale every week of an ongoing season."""
    season, number = info.get("season"), info.get("episode")
    if isinstance(season, int) and isinstance(number, int) and season >= 1 and number == 1:
        return BADGE_NEW_SHOW if season == 1 else BADGE_PREMIERE
    return None


def _show_key(info):
    return info.get("trakt_show_id") or info.get("tvshowtitle") or info.get("title") or ""


def _sort_key(episode):
    air = get_air_date(episode)
    converted = local_datetime(air)
    info = episode.get("info") or {}
    return (converted or datetime.datetime.combine(local_date(air) or datetime.date.max, datetime.time.min),
            info.get("season") or 0, info.get("episode") or 0)


def episode_row(episode, today):
    """One episode entry of the overview (also used on its own by the Unwatched view)."""
    info = episode.get("info") or {}
    air = get_air_date(episode)
    day = local_date(air)
    state, string_id, count = status(day, today, is_watched(episode))
    return {
        "type": "episode",
        "episode": episode,
        "day": day,
        "air": air,
        "code": episode_code(info),
        "title": info.get("title") or "",
        "state": state,
        "status_id": string_id,
        "status_count": count,
        "badge_id": badge_id(info),
    }


def episode_rows(episodes, today):
    """Episode entries, oldest first (a flat list, no show headers)."""
    return [episode_row(e, today) for e in sorted(episodes, key=_sort_key)]


def build_overview(episodes, today):
    """Group calendar episodes by show: [{"type": "show", ...}, {"type": "episode", ...}, ...].

    Shows sorted by name, a show's episodes oldest first. Episode entries carry the raw row
    ("episode"), its local day ("day") and the status / badge ids; the show entry carries what
    the Unwatched view needs (the show's Trakt id, and the Trakt season id + season number of
    its latest season in this calendar)."""
    shows = {}
    for episode in episodes:
        shows.setdefault(_show_key(episode.get("info") or {}), []).append(episode)

    def title_of(items):
        info = items[0].get("info") or {}
        return info.get("tvshowtitle") or info.get("title") or ""

    rows = []
    for key, items in sorted(shows.items(), key=lambda kv: title_of(kv[1]).lower()):
        episodes_of_show = episode_rows(items, today)
        latest_info = max(items, key=lambda e: (e.get("info") or {}).get("season") or 0).get("info") or {}
        rows.append({
            "type": "show",
            "title": title_of(items),
            "trakt_show_id": (items[0].get("info") or {}).get("trakt_show_id"),
            "season": latest_info.get("season"),
            "trakt_season_id": latest_info.get("trakt_season_id"),
            "poster_source": items[0],
            "total": len(episodes_of_show),
            "unaired": sum(1 for r in episodes_of_show if r["state"] == STATE_UNAIRED),
            "to_watch": sum(1 for r in episodes_of_show if r["state"] in (STATE_AIRED, STATE_TODAY)),
        })
        rows.extend(episodes_of_show)
    return rows


def utc_dates_of_local_day(day):
    """(first, last) UTC calendar dates a local day spans: the stored UTC air dates of every episode airing on that
    local day fall between them. Works for any zone, daylight saving and half-hour offsets included; when the local
    zone cannot be resolved it falls back to the day itself."""
    try:
        first = datetime.datetime.combine(day, datetime.time.min).astimezone(datetime.timezone.utc).date()
        last = datetime.datetime.combine(day, datetime.time.max).astimezone(datetime.timezone.utc).date()
    except (ValueError, OverflowError, OSError):
        return day, day
    return first, last


def episodes_on_local_day(rows, day):
    """Rows whose LOCAL air day is `day` (a stored UTC day can be the day before or after)."""
    return [r for r in rows if local_date(get_air_date(r)) == day]
