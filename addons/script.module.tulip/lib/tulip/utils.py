# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import codecs, os
from tulip import control, cleantitle
from tulip.log import log_debug
from tulip.compat import range, urlencode, parse_qsl, is_py3, py2_uni


def read_file(file_, line_by_line=False, reverse=False, encoding='utf-8'):

    if is_py3:
        f = open(file_, 'r', encoding=encoding)
    else:
        f = codecs.open(file_, 'r', encoding=encoding)

    if line_by_line:
        text = [i.rstrip('\n') for i in f.readlines()]
        if reverse:
            text = text[::-1]
    else:
        text = f.read()

    f.close()

    return text


def trim_content(file_, use_setting=False, setting_id='history_size', encoding='utf-8'):

    """
    Keeps a file with records line by line to certain limit.
    Adds a new line to the bottom and has new items on top
    :param file_: A file to be used
    :param use_setting: if you want to use a setting for other than 10 as integer of records
    :param setting_id: The setting id your addon is going to use
    :param encoding: The encoding you want to use, defaults to utf-8
    :return: Doesn't return anything it only keeps the file tidy
    """

    if use_setting:
        history_size = int(control.setting(setting_id))
    else:
        history_size = 10

    if is_py3:
        f = open(file_, 'r', encoding=encoding)
    else:
        f = codecs.open(file_, 'r', encoding=encoding)

    text = [i.rstrip('\n') for i in f.readlines()][::-1]

    f.close()

    if len(text) > history_size:

        if is_py3:
            f = open(file_, 'w', encoding='utf-8')
        else:
            f = codecs.open(file_, 'w', encoding='utf-8')

        dif = history_size - len(text)
        result = text[:dif][::-1]
        f.write('\n'.join(result) + '\n')
        f.close()


def add_to_file(file_, text, trim_file=True, encoding='utf-8'):

    """
    Adds a record as a new line to a file
    :param file_: file to be edited
    :param text: the text you want to add
    :param trim_file: will trim the file instead of keeping infinite record
    :param encoding: The encoding you want to use, defaults to utf-8
    :return: Doesn't return anything, it only processes the file
    """

    if not text:
        return

    try:

        if is_py3:
            f = open(file_, 'r', encoding=encoding)
            if text + '\n' in f.readlines():
                return
            else:
                pass
        else:
            f = codecs.open(file_, 'r', encoding=encoding)
            if py2_uni(text) + '\n' in f.readlines():
                return
        f.close()

    except IOError:
        try:
            log_debug('File {0} does not exist, creating new...'.format(os.path.basename(file_)))
        except Exception:
            print('File {0} does not exist, creating new...'.format(os.path.basename(file_)))

    if is_py3:
        f = open(file_, 'a', encoding='utf-8')
    else:
        f = codecs.open(file_, 'a', encoding='utf-8')

    f.writelines(text + '\n')
    f.close()

    if trim_file:
        trim_content(file_=file_)


def process_file(file_, text, mode='remove', cleanse=True, refresh_container=True, encoding='utf-8'):

    """
    This function can change a record to a file of records in a line by line (for instance a csv file)
    :param file_: File to be edited
    :param text: The text you want to remove or edit
    :param mode: change is going to change the text you want with an input dialog
    :param cleanse: This removes accents from the text
    :param refresh_container: refreshes the container in Kodi
    :return: Doesn't return anything, it only processes the file
    """

    if is_py3:
        f = open(file_, 'r', encoding='utf-8')
    else:
        f = codecs.open(file_, 'r', encoding='utf-8')

    lines = f.readlines()
    f.close()

    if py2_uni(text) + '\n' in lines:
        if mode == 'change':
            idx = lines.index(py2_uni(text) + '\n')
            search_type, _, search_term = py2_uni(lines[idx].strip('\n').partition(','))
            str_input = control.inputDialog(heading=control.lang(30445), default=search_term)
            str_input = py2_uni(str_input)
            if cleanse:
                str_input = cleantitle.strip_accents(str_input)
            lines[idx] = ','.join([search_type, str_input]) + '\n'
        else:
            lines.remove(py2_uni(text) + '\n')
    else:
        return

    if is_py3:
        f = open(file_, 'w', encoding='utf-8')
    else:
        f = codecs.open(file_, 'w', encoding='utf-8')

    f.write(''.join(lines))
    f.close()

    if refresh_container:
        control.refresh()


def single_picker(items, lang_integer=None):

    """
    Selects an item from a list of items with select dialog
    :param items: list of items, each item is a two item tuple, or single string
    :param lang_integer: an integer from the po file
    :return: A string (or unicode)
    """

    if lang_integer:
        heading = control.lang(lang_integer)
    else:
        heading = 'Choose an item'

    if isinstance(items[0], tuple):
        items = [item[0] for item in items]

    choice = control.selectDialog(heading=heading, list=items)

    if choice <= len(items) and not choice == -1:
        popped = items[choice]
        if isinstance(popped, tuple):
            popped = popped[1]
            return popped
        else:
            return popped


def duration_converter(duration):

    """
    Converts duration in string (minutes:seconds) to integer in seconds
    """

    result = duration.split(':')

    result = int(result[0]) * 60 + int(result[1])

    return result


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


def merge_dicts(d1, d2):

    d = d1.copy()
    d.update(d2)

    return d


def form_data_conversion(form_data):

    if isinstance(form_data, dict):
        return urlencode(form_data)
    elif isinstance(form_data, str):
        return dict(parse_qsl(form_data))
    else:
        pass  # won't do any conversion on other types
