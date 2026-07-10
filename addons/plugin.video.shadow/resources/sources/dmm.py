# -*- coding: utf-8 -*-
import re
import time
import ctypes
import math
import random
import requests
from resources.modules.client import get_html

global global_var, stop_all  # global
global_var = []
stop_all = 0

from resources.modules.general import clean_name, check_link, server_data, replaceHTMLCodes, domain_s, similar, all_colors, base_header, detect_quality_from_name, parse_size_to_gb
from resources.modules import cache
try:
    from resources.modules.general import Addon, get_imdb
except:
    import Addon
from resources.modules import log

type = ['movie', 'tv', 'torrent']

import urllib
import logging
import base64
import json

try:
    que = urllib.quote_plus
except:
    que = urllib.parse.quote_plus


def calc_value_alg(t, n, const):
    temp = t ^ n
    t = ctypes.c_long((temp * const)).value
    t4 = ctypes.c_long(t << 5).value
    x32 = t & 0xFFFFFFFF  # convert to 32-bit unsigned value
    t5 = ctypes.c_long(x32 >> 27).value
    t6 = t4 | t5
    return t6


def slice_str(e, t):
    a = math.floor(len(e) / 2)
    s = e[0:a]
    n = e[a:]
    i = t[0:a]
    o = t[a:]

    l = ""
    for e in range(0, a):
        l += s[e] + i[e]

    temp = l + (o[::-1] + n[::-1])
    return temp


def generateHash(e):
    t = int(3735928559) ^ int(len(e))
    t = ctypes.c_long(t).value
    a = 1103547991 ^ len(e)

    for s in range(len(e)):
        n = ord(e[s])
        t = calc_value_alg(t, n, 2654435761)
        a = calc_value_alg(a, n, 1597334677)

    t_o = t
    t = ctypes.c_long(t + ctypes.c_long(a * 1566083941).value | 0).value
    a = ctypes.c_long(a + ctypes.c_long(t * 2024237689).value | 0).value

    return (ctypes.c_long(t ^ a).value & 0xFFFFFFFF) >> 0


def get_secret():
    ran = random.randrange(10 ** 80)
    myhex = "%064x" % ran

    # limit string to 64 characters
    e = myhex[:8]
    t = int(time.time())
    a = str(e) + '-' + str(t)

    s = generateHash(a)
    s = hex(s).replace('0x', '')

    n = generateHash("debridmediamanager.com%%fe7#td00rA3vHz%VmI-" + e)
    n = hex(n).replace('0x', '')

    i = slice_str(s, n)
    dmmProblemKey = a
    solution = i
    return dmmProblemKey, solution


def get_links(tv_movie, original_title, season_n, episode_n, season, episode, show_original_year, id):
    global global_var, stop_all

    all_links = []

    # ====== PERFORMANCE: Cache settings before loops ======
    max_size = int(Addon.getSetting("size_limit"))

    try:
        dmmProblemKey, solution = get_secret()
        params = {'dmmProblemKey': dmmProblemKey, 'solution': solution}
        base_link = "https://debridmediamanager.com"

        if tv_movie == 'movie':
            search_title = clean_name(original_title, 1).replace(' ', '').replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
            imdb_id = cache.get(get_imdb, 999, tv_movie, id, table='pages')
            if not imdb_id:
                return global_var
            movieSearch_link = '/api/torrents/movie?imdbId=%s' % imdb_id
            url = '%s%s&page=0' % (base_link, movieSearch_link)

            try:
                results = requests.get(url, params=params, timeout=10, verify=False).json()
                files = results.get('results', [])
            except:
                log.warning('DMM API Error for movie')
                return global_var

            for file in files:
                if stop_all == 1:
                    break
                try:
                    hash_val = file['hash']
                    title = file['title']
                    name = clean_name(title, 1)

                    url_magnet = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash_val, que(name))

                    size = float(file.get('fileSize', 0)) / (1024 * 1024 * 1024)
                    res = detect_quality_from_name(name)

                    if size < max_size:
                        all_links.append((name, url_magnet, str(round(size, 2)), res))
                        global_var = all_links
                except Exception as e:
                    log.warning('DMM Error processing file: ' + str(e))

        elif tv_movie == 'tv':
            search_title = clean_name(original_title, 1).replace(' ', '').replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
            imdb_id = cache.get(get_imdb, 999, tv_movie, id, table='pages')
            if not imdb_id:
                return global_var
            tvSearch_link = '/api/torrents/tv?imdbId=%s&seasonNum=%s' % (imdb_id, season_n)
            url = '%s%s&page=0' % (base_link, tvSearch_link)

            try:
                results = requests.get(url, params=params, timeout=10, verify=False).json()
                files = results.get('results', [])
            except:
                log.warning('DMM API Error for tv')
                return global_var

            for file in files:
                if stop_all == 1:
                    break
                try:
                    hash_val = file['hash']
                    title = file['title']
                    name = clean_name(title, 1)

                    url_magnet = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash_val, que(name))

                    size = float(file.get('fileSize', 0)) / (1024 * 1024 * 1024)
                    res = detect_quality_from_name(name)

                    if size < max_size:
                        all_links.append((name, url_magnet, str(round(size, 2)), res))
                        global_var = all_links
                except Exception as e:
                    log.warning('DMM Error processing file: ' + str(e))

    except Exception as e:
        log.warning('DMM Main Error: ' + str(e))

    return global_var
