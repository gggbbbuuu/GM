# -*- coding: utf-8 -*-
__version__ = '0.18.0'

from fuzzywuzzy import process

def wrapper(items_list, search_term, limit=5, score=70):

    results = []

    if not items_list or not search_term:
        return None

    try:
        search_term = search_term.decode('utf-8')
    except AttributeError:
        pass

    titles = [i['title'].encode('unicode-escape') for i in items_list]

    matches = [
        titles.index(l) for l, s in process.extract(
            search_term.encode('unicode-escape'), titles, limit=limit
        ) if s >= score
    ]

    for m in matches:
        results.append(items_list[m])

    return results
