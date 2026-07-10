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
except:
    que = urllib.parse.quote_plus

_INFO_RE = re.compile(r'💾.*')
_SIZE_RE = re.compile(r'((?:\d+,\d+\.\d+|\d+\.\d+|\d+,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))')

def get_links(tv_movie, original_title, season_n, episode_n, season, episode, show_original_year, id):
    global global_var, stop_all
    all_links = []

    max_size = int(Addon.getSetting("size_limit"))
    imdb_id = cache.get(get_imdb, 999, tv_movie, id, table='pages')
    if not imdb_id:
        return global_var

    base = 'https://torrentsdb.com'
    if tv_movie == 'movie':
        url = '%s/stream/movie/%s.json' % (base, imdb_id)
    else:
        url = '%s/stream/series/%s:%s:%s.json' % (base, imdb_id, season_n.lstrip('0') or '1', episode_n.lstrip('0') or '1')
    log.warning(url)

    try:
        x = get_html(url, headers=base_header, timeout=10).json()
        files = x.get('streams', [])
    except:
        return global_var

    for file in files:
        if stop_all == 1:
            break
        try:
            hash_val = file['infoHash']
            file_title = file.get('title', '').split('\n')
            nam = file_title[0].strip() if file_title else original_title

            size = 0
            try:
                info_line = [l for l in file_title if _INFO_RE.search(l)][0]
                m = _SIZE_RE.search(info_line)
                if m:
                    size = parse_size_to_gb(m.group(0))
            except:
                pass

            lk = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash_val, que(nam))
            res = detect_quality_from_name(nam)

            if size < max_size:
                all_links.append((nam, lk, str(round(size, 2)), res))
                global_var = all_links
        except:
            pass

    return global_var
