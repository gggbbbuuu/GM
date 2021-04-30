# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from random import choice
from os.path import split as os_split
from tulip import control, cache

cache_method = cache.FunctionCache().cache_method


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
            choices.insert(0, control.lang(30215))

        _choice = control.selectDialog(heading=control.lang(30214), list=choices)

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
