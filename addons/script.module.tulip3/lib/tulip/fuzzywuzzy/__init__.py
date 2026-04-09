# -*- coding: utf-8 -*-
__version__ = '0.17.0'

try:
    from tulip import control
except Exception:
    control = None
from tulip.fuzzywuzzy import process

def wrapper(_list_, limit=5, score=70):

    results = []

    if not _list_:
        return

    if control:
        term = control.inputDialog()
    else:
        term = input('Please enter search term: ')

    if not term:
        return

    try:
        term = term.decode('utf-8')
    except AttributeError:
        pass

    if control:
        control.busy()

    titles = [i['title'].encode('unicode-escape') for i in _list_]

    matches = [
        titles.index(l) for l, s in process.extract(
            term.encode('unicode-escape'), titles, limit=limit
        ) if s >= score
    ]

    for m in matches:
        results.append(_list_[m])

    if control:
        control.idle()

    return results
