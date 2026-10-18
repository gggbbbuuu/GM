# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Cookie-string parsing for the Subs4Series hand-over. The served page takes
    the browser's cookie (or its Copy as cURL text) in its manual box, and this
    pulls the name=value pairs out of whatever arrived.

    Accepts the messiest possible input:
      - a raw cookie string            PHPSESSID=abc
      - a copied Cookie header         Cookie: PHPSESSID=abc
      - a full "Copy as cURL" command  curl 'https://...' -H 'Cookie: ...'

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import re


def extract_cookies(blob):

    '''Pulls every name=value pair out of whatever the user pasted.'''

    blob = blob.replace('\\n', ' ').replace('\\t', ' ').replace('\\"', '"')

    pairs = []
    seen = set()

    def add(name, value):

        name, value = name.strip(), value.strip()

        if not name or not value:
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

    # fall back to a raw name=value string split on its own delimiters, so a
    # name keeps a dot (techaro.lol-anubis-auth) and a value keeps padding or
    # punctuation (cf_clearance) instead of being truncated by a safe-class match
    if not pairs:
        for part in blob.split(';'):
            if '=' in part:
                name, value = part.split('=', 1)
                add(name, value)

    return '; '.join(pairs)