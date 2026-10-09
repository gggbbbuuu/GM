# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Captures the Subs4Series session cookie the user obtained in their browser.

    Accepts the messiest possible input so nobody has to hand-pick a value:
      - a raw cookie string            PHPSESSID=abc
      - a copied Cookie header         Cookie: PHPSESSID=abc
      - a full "Copy as cURL" command  curl 'https://...' -H 'Cookie: ...'
    then stores the cleaned string in the 's4f.session' setting.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import re

import xbmcaddon
import xbmcgui

ADDON_ID = 'service.subtitles.subtitles.gr'
SETTING = 's4f.session'


def addon():

    # RunScript(path) carries no addon id, so it must be passed explicitly
    return xbmcaddon.Addon(ADDON_ID)


def lang(string_id):

    return addon().getLocalizedString(string_id)


def extract_cookies(blob):

    '''Pulls every name=value pair out of whatever the user pasted.'''

    blob = blob.replace('\\n', ' ').replace('\\t', ' ').replace('\\"', '"')

    pairs = []
    seen = set()

    def add(name, value):

        name, value = name.strip(), value.strip()

        if not name or not value or '=' in value:
            return

        item = '{0}={1}'.format(name, value)

        if item in seen:
            return

        seen.add(item)
        pairs.append(item)

    # prefer explicit cookie header/argument when present
    headers = re.findall(
        r'(?:-H|--header)\s+["\']?\s*cookie:\s*([^"\']+)["\']?', blob, flags=re.I
    )
    headers += re.findall(r'cookie:\s*([^"\';]+(?:;[^"\'\n]+)*)', blob, flags=re.I)

    for chunk in headers:
        for part in chunk.split(';'):
            if '=' in part:
                name, value = part.split('=', 1)
                add(name, value)

    # fall back to any bare name=value tokens
    if not pairs:
        for name, value in re.findall(r'\b([A-Za-z0-9_\-]{3,})=([A-Za-z0-9_\-\.]{3,})', blob):
            add(name, value)

    return '; '.join(pairs)


def prompt():

    dialog = xbmcgui.Dialog()

    current = addon().getSetting(SETTING)
    default = current if current else ''

    try:
        value = dialog.input(
            heading='Subtitles.gr', default=default, type=xbmcgui.INPUT_ALPHANUM
        )
    except TypeError:
        # older Kodi names this argument defaultt
        value = dialog.input(
            heading='Subtitles.gr', defaultt=default, type=xbmcgui.INPUT_ALPHANUM
        )

    return value


if __name__ == '__main__':

    dialog = xbmcgui.Dialog()

    if not dialog.yesno('Subtitles.gr', lang(30260)):
        raise SystemExit

    pasted = prompt()

    if not pasted:
        raise SystemExit

    cookies = extract_cookies(pasted)

    if not cookies:
        dialog.ok('Subtitles.gr', lang(30261))
        raise SystemExit

    addon().setSetting(SETTING, cookies)

    dialog.notification('Subtitles.gr', lang(30262), time=3000, sound=False)