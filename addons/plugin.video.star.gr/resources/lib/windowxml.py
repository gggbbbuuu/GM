# -*- coding: utf-8 -*-

'''
    Star Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

from datetime import datetime, timedelta

import xbmc
import xbmcgui

from tulip import kodi
from tulip.init import sysaddon

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 2 fallback, unconverted times
    ZoneInfo = None

# The schedule is published in station-local time.
STATION_TZ = 'Europe/Athens'


DATES_LIST = 100
ROWS_LIST = 101
TITLE_LABEL = 1
DATE_LABEL = 2
HINT_LABEL = 3
CLOSE_BUTTON = 200


def _label(number):
    try:
        return kodi.i18n(number)
    except Exception:
        return str(number)


class ProgrammaDialog(xbmcgui.WindowXMLDialog):
    """
    Replicates the look of https://www.star.gr/tv/programma/: a day strip on
    top and the day's schedule (time, title, ΤΩΡΑ badge) below it.

    Activating a schedule row plays the live stream when the entry is airing
    now, resolves a directly playable video page, or opens the linked show's
    episode listing otherwise.
    """

    def __init__(self, *args, **kwargs):
        self.dates = kwargs.pop('dates', [])
        self.rows = []
        self._index = 0

    def onInit(self):

        self._fill_dates()

        if self.dates:
            initial = self._today_index()
            try:
                self.getControl(DATES_LIST).selectItem(initial)
            except Exception:
                pass
            self.setFocus(self.getControl(DATES_LIST))
            self._load_rows(initial)

        try:
            self.getControl(TITLE_LABEL).setLabel(_label(30071))
            self.getControl(HINT_LABEL).setLabel(_label(30082))
        except Exception:
            pass

    # -- dates ------------------------------------------------------------

    def _fill_dates(self):

        control = self.getControl(DATES_LIST)
        control.reset()

        for day in self.dates:
            item = xbmcgui.ListItem(label=day['label'])
            item.setProperty('date', day['date'])
            item.setProperty('today', '1' if day.get('today') else '')
            control.addItem(item)

    def _today_index(self):
        """Keeps past days on the left but opens on today."""

        for index, day in enumerate(self.dates):
            if day.get('today'):
                return index

        try:
            today = datetime.now(ZoneInfo(STATION_TZ)).date().isoformat() \
                if ZoneInfo is not None else datetime.now().date().isoformat()
        except Exception:
            return 0

        for index, day in enumerate(self.dates):
            try:
                if datetime.fromisoformat(day['date']).date().isoformat() == today:
                    return index
            except Exception:
                continue

        return 0

    def _load_rows(self, index):

        self._index = index
        date = self.dates[index]['date']

        try:
            self.getControl(DATE_LABEL).setLabel(self.dates[index]['label'])
        except Exception:
            pass

        control = self.getControl(ROWS_LIST)
        control.reset()
        self.rows = []

        try:
            from .navigator import _prog_rows
            rows = _prog_rows(date)
        except Exception:
            rows = []

        rows = _localize_rows(rows, date)
        now_position = None

        for position, row in enumerate(rows):
            self.rows.append(row)
            label = '{0}  {1}'.format(row['time'], row['title'])
            item = xbmcgui.ListItem(label=label)
            item.setProperty('time', row['time'])
            item.setProperty('title', row['title'])
            item.setProperty('plot', row.get('plot', ''))
            item.setProperty('now_text', _label(30081) if row['now'] else '')
            if row.get('image'):
                item.setArt({'thumb': row['image'], 'icon': row['image']})
            control.addItem(item)

            if row['now'] and now_position is None:
                now_position = position

        if now_position is not None:
            try:
                control.selectItem(now_position)
            except Exception:
                pass

    # -- actions ----------------------------------------------------------

    def onClick(self, control_id):

        if control_id == CLOSE_BUTTON:
            self.close()
        elif control_id == DATES_LIST:
            control = self.getControl(DATES_LIST)
            self._load_rows(control.getSelectedPosition())
        elif control_id == ROWS_LIST:
            control = self.getControl(ROWS_LIST)
            position = control.getSelectedPosition()
            if 0 <= position < len(self.rows):
                self._activate(self.rows[position])

    def onAction(self, action):

        action_id = action.getId()

        if action_id in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK,
                         xbmcgui.ACTION_STOP):
            self.close()

    # -- row activation ---------------------------------------------------

    def _activate(self, row):

        url = row.get('url', '')

        if row.get('now'):
            self.close()
            xbmc.executebuiltin('PlayMedia({0}?action=live)'.format(sysaddon))
            return

        if '/video/' in url:
            self.close()
            from urllib.parse import quote_plus
            xbmc.executebuiltin('PlayMedia({0}?action=play&url={1})'.format(
                sysaddon, quote_plus(url)))
            return

        show_url = self._show_url(url)

        if show_url:
            self.close()
            from urllib.parse import quote_plus
            import json
            ref = quote_plus(json.dumps({'kind': 'episodes', 'base': show_url,
                                         'title': row.get('title', '')},
                                        separators=(',', ':')))
            xbmc.executebuiltin('Container.Update({0}?action=listing&url={1})'.format(
                sysaddon, ref))
            return

        kodi.infoDialog(_label(30014))

    @staticmethod
    def _show_url(url):
        """Trims a schedule link down to its /tv/<section>/<show> page."""

        import re

        match = re.match(r'(https://www\.star\.gr/tv/[a-z]+/[a-z0-9-]+)', url or '')

        return match.group(1) if match else ''


def _localize_rows(rows, date):
    """
    Converts the station-local schedule to the user's timezone and recomputes
    the now-airing row, so the ΤΩΡΑ highlight matches the user's clock even
    outside Greece. Overnight entries past midnight count toward the next day.
    Falls back to the raw site values when timezones are unavailable.
    """

    try:
        day = datetime.fromisoformat(date).date()
    except Exception:
        return rows

    localized = []
    starts = []

    for row in rows:
        try:
            hour, minute = [int(part) for part in row['time'].split(':')]
        except Exception:
            continue

        if starts and (hour, minute) < (starts[-1][1], starts[-1][2]):
            day += timedelta(days=1)

        starts.append((day, hour, minute, len(localized)))
        localized.append(dict(row))

    if ZoneInfo is None:
        return localized

    try:
        station = ZoneInfo(STATION_TZ)
        moments = [datetime(d.year, d.month, d.day, h, m, tzinfo=station)
                   for d, h, m, _ in starts]
        now = datetime.now(station)
    except Exception:
        return localized

    for (_, _, _, position), moment in zip(starts, moments):
        localized[position]['time'] = moment.astimezone().strftime('%H:%M')

    # The computed window follows the user's clock and wins over the site's
    # badge, which goes stale as the page ages. The badge is only kept when
    # timezones are unavailable and no computation ran at all.
    for row in localized:
        row['now'] = False

    for index, moment in enumerate(moments):
        end = moments[index + 1] if index + 1 < len(moments) \
            else moment + timedelta(hours=4)

        if moment <= now < end:
            localized[index]['now'] = True

    return localized
