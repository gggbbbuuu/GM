# -*- coding: utf-8 -*-

'''
    Blacklodge Add-on

    A Trakt list with its movies and shows on one screen (used by the Trakt
    public lists). One Trakt call per page (/lists/{id}/items/movie,show/...),
    the rows are split by type and go through the existing movies/tvshows code
    (trakt_list, worker, movieDirectory/tvshowDirectory with ret=True), then
    the items are put back in the list's own order.
'''

import sys

from six.moves import urllib_parse

from resources.lib.modules import cache
from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import views
from resources.lib.modules import log_utils


def _order_map(rows, kind):
    # Position of each row in the Trakt page, by tmdb and by imdb id.
    out = {}
    for pos, row in rows:
        ids = (row.get(kind) or {}).get('ids') or {}
        if ids.get('tmdb'): out['tmdb:%s' % ids['tmdb']] = pos
        if ids.get('imdb'): out['imdb:%s' % ids['imdb']] = pos
    return out


def _set_order(items, order):
    for n, i in enumerate(items):
        pos = order.get('tmdb:%s' % i.get('tmdb'))
        if pos is None: pos = order.get('imdb:%s' % i.get('imdb'))
        i['mixed_order'] = pos if pos is not None else 100000 + n


def mixed_list(url):
    from resources.lib.indexers import movies, tvshows

    sysaddon, syshandle = sys.argv[0], int(sys.argv[1])

    try:
        q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
        fq = dict(q, extended='full')
        # Smart lists can follow the user's own data (watchlist, library):
        # 1 hour. Public lists: 24 hours.
        hours = 1 if '/smart-lists/' in url else 24
        result = cache.get(trakt.getTrakt, hours, url.split('?')[0] + '?' + urllib_parse.urlencode(fq)) or []
    except:
        log_utils.log('trakt_mixed_get', 1)
        q, result = {}, []

    rows = list(enumerate(result if isinstance(result, list) else []))
    mrows = [(p, r) for p, r in rows if r.get('type') == 'movie' and r.get('movie')]
    srows = [(p, r) for p, r in rows if r.get('type') == 'show' and r.get('show')]

    m_items, s_items = [], []
    try:
        if mrows:
            m = movies.movies()
            m.trakt_list(url, [r for p, r in mrows])
            _set_order(m.list, _order_map(mrows, 'movie'))
            m.worker()
            if m.list: m_items = m.movieDirectory(m.list, ret=True) or []
    except:
        log_utils.log('trakt_mixed_movies', 1)
    try:
        if srows:
            s = tvshows.tvshows()
            s.trakt_list(url, [r for p, r in srows])
            _set_order(s.list, _order_map(srows, 'show'))
            s.worker()
            if s.list: s_items = s.tvshowDirectory(s.list, ret=True) or []
    except:
        log_utils.log('trakt_mixed_tvshows', 1)

    list_items = [x[1] for x in sorted(m_items + s_items, key=lambda x: x[0])]

    if not list_items:
        control.idle()
        control.infoDialog('No content')

    try:
        limit = int(q.get('limit', '0'))
        if list_items and limit and len(rows) >= limit:
            page = int(q.get('page', '1'))
            nq = dict(q, page=str(page + 1))
            nxt = url.split('?')[0] + '?' + urllib_parse.urlencode(nq)
            label = control.lang(32053) + '[I] (%s)[/I]' % (page + 1)
            icon = control.addonNext()
            try: item = control.item(label=label, offscreen=True)
            except: item = control.item(label=label)
            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon, 'fanart': control.addonFanart()})
            item.setProperty('SpecialSort', 'bottom')
            list_items.append(('%s?action=traktMixedList&url=%s' % (sysaddon, urllib_parse.quote_plus(nxt)), item, True))
    except:
        pass

    # The screen is declared as the type with more items, so the skin keeps
    # its usual movies or tv shows view.
    content = 'tvshows' if len(s_items) > len(m_items) else 'movies'
    control.addItems(handle=syshandle, items=list_items, totalItems=len(list_items))
    control.content(syshandle, content)
    control.directory(syshandle, cacheToDisc=True)
    control.sleep(1000)
    views.setView(content, {'skin.estuary': 55, 'skin.confluence': 500})
