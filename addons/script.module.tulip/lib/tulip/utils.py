# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from tulip.compat import range


def percent(count, total):

    return min(int(round(count * 100 / total)), 100)


def enum(**enums):

    try:
        return type(b'Enum', (), enums)
    except TypeError:
        return type('Enum', (), enums)


def list_divider(list_, chunks):

    """
    This function can split a list into smaller parts.
    Can help creating pages
    :param list_: A list, can be a list of dictionaries
    :param chunks: How many items are required on each item of the final list
    :return: List of lists
    """

    return [list_[i:i + chunks] for i in range(0, len(list_), chunks)]
