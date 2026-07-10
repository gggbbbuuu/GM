# -*- coding: utf-8 -*-
import re
global global_var, stop_all
global_var = []
stop_all = 0
from resources.modules.client import get_html
from resources.modules.general import clean_name, check_link, server_data, replaceHTMLCodes, domain_s, similar, all_colors, base_header, detect_quality_from_name, parse_size_to_gb
from resources.modules import cache
from resources.modules import log
try:
    from resources.modules.general import Addon, get_imdb
except:
    import Addon

type = ['movie', 'tv', 'torrent']

import urllib
try:
    que = urllib.quote_plus
    qup = urllib.quote_plus
except:
    que = urllib.parse.quote_plus
    qup = urllib.parse.quote_plus

SERVER_ERROR = ('something went wrong', 'Connection timed out', '521: Web server is down', '503 Service Unavailable')

def get_links(tv_movie, original_title, season_n, episode_n, season, episode, show_original_year, id):
    global global_var, stop_all
    all_links = []

    max_size = int(Addon.getSetting("size_limit"))

    title = original_title.replace('&', 'and').replace('/', ' ')
    if tv_movie == 'tv':
        hdlr = 'S%sE%s' % (season_n, episode_n)
    else:
        hdlr = show_original_year

    query = '%s %s' % (re.sub(r'[^A-Za-z0-9\s\.-]+', '', title), hdlr)
    url = 'https://torrentz2.nz/search?q=%s' % qup(query)
    log.warning(url)

    try:
        r = get_html(url, headers=base_header, timeout=10)
        results = r.content()
        if not results or any(e in results for e in SERVER_ERROR):
            return global_var
    except:
        return global_var

    rows = re.findall(r'<dl>(.*?)</dl>', results, re.DOTALL)
    for row in rows:
        if stop_all == 1:
            break
        try:
            if 'magnet:' not in row:
                continue
            columns = re.findall(r'<span.*?>(.+?)</span>', row, re.DOTALL)

            lk = columns[0].replace('&amp;', '&')
            lk = re.sub(r'(&tr=.+)&dn=', '&dn=', lk)
            lk = re.search(r'(magnet:.+?)">', lk, re.I)
            if not lk:
                continue
            lk = lk.group(1).replace(' ', '.')

            hash_val = re.search(r'btih:(.*?)&', lk, re.I)
            if not hash_val:
                continue
            hash_val = hash_val.group(1)
            nam = lk.split('&dn=')[1] if '&dn=' in lk else original_title
            nam = re.sub(r'&tr=.*', '', nam).strip()

            try:
                size = parse_size_to_gb(columns[2])
            except:
                size = 0

            res = detect_quality_from_name(nam)

            if size < max_size:
                all_links.append((nam, lk, str(round(size, 2)), res))
                global_var = all_links
        except:
            pass

    return global_var
