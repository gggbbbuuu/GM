# -*- coding: utf-8 -*-
import re
import concurrent.futures
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

_LINKS_RE = re.compile(r'<a\s*href\s*=\s*["\'](.+?torrent\.html)["\']', re.I)
BASE = 'https://torrentproject2.com'

def _get_source(link, max_size, all_links):
    try:
        url = '%s%s' % (BASE, link)
        r = get_html(url, headers=base_header, timeout=8)
        result = r.content()
        if not result:
            return

        hash_m = re.search(r'<a\s*title\s*=\s*["\']hash:(.+?)\s*torrent', result, re.I)
        name_m = re.search(r'<title>(.+?)</title>', result, re.I)
        if not hash_m or not name_m:
            return

        hash_val = hash_m.group(1).strip()
        nam = name_m.group(1).strip()

        try:
            size_m = re.search(r'<div id\s*=\s*["\']torrent-size["\']>(.+?)<', result, re.I)
            size = parse_size_to_gb(size_m.group(1)) if size_m else 0
        except:
            size = 0

        lk = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash_val, que(nam))
        res = detect_quality_from_name(nam)

        if size < max_size:
            all_links.append((nam, lk, str(round(size, 2)), res))
    except:
        pass

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
    url = '%s/?t=%s&orderby=seeders' % (BASE, qup(query))
    log.warning(url)

    try:
        r = get_html(url, headers=base_header, timeout=8)
        results = r.content()
        if not results:
            return global_var
        links = _LINKS_RE.findall(results)
    except:
        return global_var

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for link in links:
            if stop_all == 1:
                break
            executor.submit(_get_source, link, max_size, all_links)

    global_var = all_links
    return global_var
