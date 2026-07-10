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

# MediaFusion elfhosted public instance token
_TOKEN = (
    'D-h5mpsX35oygOGFiHutl66dLAPiXzjQTODPXKQuKBaQOLjwNBbVkSPi7TJPr0gdykpCFREq8JOh'
    'DHZcvoS_UNZsWpsbjscCAwzgqc9VvP0S3Wt9lz5blcPT8lU6fcHdAHYctp_yde6nWKtSQ1O9Tjeh'
    'GNwajH9TjGZwn6rOybPFmoMpccXfTkB3Xwe9xRhT9O-bKzoYnGnlG8fCDxlNGdzrnlythePc3C7O'
    'phF8b5GyhuSnvBhxD7dTfkI77Dbay8_k_wqS-me9euZQ-oyOJBNTOIsO8HiWQhLGCC8m9rYsqJT6'
    'QF1Xhn-2bNzlukfbSYh_X1kOFdi6Y-YkBeEYokDlQHzzU45qmrj2b1Nz-GALcJHjNDJEMF3h9Eyx'
    '7UcmGWT1qvTpv_tcXjAX37ceqrWH-e_EqwVkvQDjNnmpjOhBWhuUW2R-0KbvxKUn1s5d2jZjLBxC'
    'bMotHIC-G2SrVCLgC_KV0OUainevUHKOKTe0CQmWz1HKV1ju52CFZFZYAWkOAX5cw55qzNnWl_nQ'
    'RnLyngrW_P6aYqghbYyyrAvQ6hCrIbSnVj4GsMFIelcMETvGW4jIXdwZGZA1L8gCzmyCbI9vAqPv'
    'dZxRWb7roc2EnB7gaSYdFtTP9gGoFKKkQ-9aircUEiPXjkP4QWO7lVI4GZri7KKCKjBM7-hWf4nm'
    'ttY7lJS_4Te_H80BeR_qpqeYQ6V0gpVwihARA6cIsZFbWmQXtoYNO16jt1ZqeVztwR6L1IQQnAsH'
    'ANyR5kF7ovGCOnhWlDDxO3nk8fhm3s0k7XewrMisZHy1zNsivTjvJW6KoVwghLn8-QCTf9PEPoPj'
    's6tW5KjciaRvbMg5-mbhpAhYOmPisB4ZyW63vWY6TeU1OBJV0T_fkHtgbvgiTEX5RFoRVDLnhaof'
    '-xHVw2oCc2AdXmBDVROmFjY8x9KEyZ91QfNjHnrTFmGetelcHE'
)

def get_links(tv_movie, original_title, season_n, episode_n, season, episode, show_original_year, id):
    global global_var, stop_all
    all_links = []

    max_size = int(Addon.getSetting("size_limit"))
    imdb_id = cache.get(get_imdb, 999, tv_movie, id, table='pages')
    if not imdb_id:
        return global_var

    base = 'https://mediafusionfortheweebs.midnightignite.me'
    if tv_movie == 'movie':
        url = '%s/%s/stream/movie/%s.json' % (base, _TOKEN, imdb_id)
    else:
        url = '%s/%s/stream/series/%s:%s:%s.json' % (base, _TOKEN, imdb_id, season_n.lstrip('0') or '1', episode_n.lstrip('0') or '1')
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
            file_title = file.get('description', '').split('\n')
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
