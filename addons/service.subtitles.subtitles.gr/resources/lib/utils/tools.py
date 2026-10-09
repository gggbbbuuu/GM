# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
from random import choice
from os.path import split as os_split
from tulip import cleantitle
from tulip import kodi as control
from tulip.kodi import i18n as lang
from pickled import FunctionCache


cache_method = FunctionCache(control.join(control.dataPath, 'cache')).cache_method

# Static browser User-Agents. Deliberately NOT delegated to
# netclient.useragents.get_ua(): that helper answers through script.common's
# StorageServer over a bare TCP socket whose recv() has no timeout, so a
# lookup abandoned mid-transaction (a worker thread dying at SEARCH_TIMEOUT,
# an invocation ending) leaves the server thread blocked forever and Kodi
# cannot quit afterwards (service join with timeout=None). A User-Agent string
# is not worth a cross-process round trip; the static list is equivalent.
_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


def randomagent():

    return choice(_USER_AGENTS)


def clean_title(title):

    '''
    Normalises a title for cross-site matching.

    tulip's cleantitle only strips a leading article in upper case, so
    "The Matrix" and "Matrix" would not otherwise compare equal.
    '''

    title = re.sub(r'^(THE|A)\s+', '', str(title).strip().upper())

    return cleantitle.get(title)


class Cancelled(Exception):

    '''Raised when the user dismisses a multi subtitle picker.'''


def pick(filenames, allow_random=False):

    '''
    Returns the subtitle file the user chose.

    Raises Cancelled when the picker was dismissed, so callers can tell an
    intentional abort apart from a genuine failure instead of tripping over
    a None filename.
    '''

    if not filenames:
        raise Cancelled

    if len(filenames) == 1:
        return filenames[0]

    chosen = multichoice(filenames, allow_random=allow_random)

    if chosen is None:
        raise Cancelled

    return chosen


def multichoice(filenames, allow_random=False):

    if filenames is None or len(filenames) == 0:

        return

    elif len(filenames) >= 1:

        if allow_random:
            length = len(filenames) + 1
        else:
            length = len(filenames)

        if len(filenames) == 1:
            return filenames[0]

        choices = [os_split(i)[1] for i in filenames]

        if allow_random:
            choices.insert(0, lang(30215))

        _choice = control.selectDialog(heading=lang(30214), list=choices)

        if _choice == 0:
            if allow_random:
                filename = choice(filenames)
            else:
                filename = filenames[0]
        elif _choice != -1 and _choice <= length:
            if allow_random:
                filename = filenames[_choice - 1]
            else:
                filename = filenames[_choice]
        else:
            if allow_random:
                filename = choice(filenames)
            else:
                return

        return filename

    else:

        return


def cache_duration(duration):

    if control.setting('cache') == 'true':
        return duration
    else:
        return 0
