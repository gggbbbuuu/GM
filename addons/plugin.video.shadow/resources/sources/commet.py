# -*- coding: utf-8 -*-
import re
import time
import base64
from json import dumps as jsdumps
global global_var,stop_all#global
global_var=[]
stop_all=0
from  resources.modules.client import get_html
 
from resources.modules.general import clean_name,check_link,server_data,replaceHTMLCodes,domain_s,similar,all_colors,base_header,detect_quality_from_name,parse_size_to_gb
from  resources.modules import cache
try:
    from resources.modules.general import Addon,get_imdb
except:
  import Addon
type=['movie','tv','torrent']

import urllib,logging,base64,json

from resources.modules import log

try:
    que=urllib.quote_plus
except:
    que=urllib.parse.quote_plus
color=all_colors[112]

_INFO_RE = re.compile(r'💾.*')
_SIZE_RE = re.compile(r'((?:\d+,\d+\.\d+|\d+\.\d+|\d+,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))')

def build_debrid_services():
    """Build list of enabled debrid services for Comet params."""
    services = []
    if Addon.getSetting('debrid_use_rd') == 'true':
        token = Addon.getSetting('rd.auth')
        if token:
            services.append({'service': 'realdebrid', 'apiKey': token})
    if Addon.getSetting('debrid_use_pm') == 'true':
        token = Addon.getSetting('premiumize.token')
        if token:
            services.append({'service': 'premiumize', 'apiKey': token})
    if Addon.getSetting('debrid_use_ad') == 'true':
        token = Addon.getSetting('alldebrid.token')
        if token:
            services.append({'service': 'alldebrid', 'apiKey': token})
    if Addon.getSetting('debrid_use_tr') == 'true':
        token = Addon.getSetting('tb.token')
        if token:
            services.append({'service': 'torbox', 'apiKey': token})
    return services

def build_url(tv_movie, imdb, season, episode):
    base_link = 'https://comet.elfhosted.com'
    movieSearch_link = '/%s/stream/movie/%s.json'
    tvSearch_link = '/%s/stream/series/%s:%s:%s.json'

    debrid_services = build_debrid_services()
    if not debrid_services:
        return None

    params = {
        "maxResultsPerResolution": 0, "maxSize": 0, "cachedOnly": True,
        "sortCachedUncachedTogether": False, "removeTrash": True,
        "resultFormat": ["all"], "debridServices": debrid_services,
        "enableTorrent": False, "deduplicateStreams": False,
        "scrapeDebridAccountTorrents": False, "debridStreamProxyPassword": "",
        "languages": {"required": [], "allowed": [], "exclude": [], "preferred": []},
        "resolutions": {},
        "options": {"remove_ranks_under": -10000000000, "allow_english_in_languages": False, "remove_unknown_languages": False}
    }
    params = base64.b64encode(jsdumps(params, separators=(',', ':')).encode('utf-8')).decode('utf-8')
    if tv_movie == 'movie':
        url = '%s%s' % (base_link, movieSearch_link % (params, imdb))
    else:
        url = '%s%s' % (base_link, tvSearch_link % (params, imdb, season, episode))
    return url

def get_links(tv_movie, original_title, season_n, episode_n, season, episode, show_original_year, id):
    global global_var, stop_all
    all_links = []

    max_size = int(Addon.getSetting("size_limit"))

    imdb_id = cache.get(get_imdb, 999, tv_movie, id, table='pages')

    url = build_url(tv_movie, imdb_id, season_n, episode_n)
    if not url:
        return global_var
    log.warning(url)

    x = get_html(url, headers=base_header).json()

    if 'streams' not in x:
        return global_var

    for file in x['streams']:
        if stop_all == 1:
            break
        try:
            # Hash — use infoHash directly (top-level field per Comet API)
            hash_val = file.get('infoHash') or file.get('behaviorHints', {}).get('bingeGroup', '')
            if not hash_val:
                continue
            # Strip any service prefix if bingeGroup was used as fallback
            hash_val = re.sub(r'^comet\|[^|]+\|', '', hash_val)

            # Name — first line of description (same as pov reference)
            desc_lines = file.get('description', '').split('\n')
            nam = desc_lines[0].replace('📄','').strip() if desc_lines else original_title

            # Size — parse from 💾 line in description
            size = 0
            try:
                info_line = [x for x in desc_lines if _INFO_RE.search(x)][0]
                size_match = _SIZE_RE.search(info_line)
                if size_match:
                    size_str = size_match.group(0)
                    size_num = float(re.sub(r'[^\d.]', '', size_str.split()[0].replace(',', '')))
                    if 'MB' in size_str or 'MiB' in size_str or 'Mb' in size_str:
                        size = size_num / 1024
                    else:
                        size = size_num
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