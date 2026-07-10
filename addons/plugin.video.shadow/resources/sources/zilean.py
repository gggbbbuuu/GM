# -*- coding: utf-8 -*-
import re
from resources.modules import log
global global_var, stop_all
global_var = []
stop_all = 0
from resources.modules.client import get_html
from resources.modules.general import clean_name, check_link, server_data, replaceHTMLCodes, domain_s, similar, all_colors, base_header, detect_quality_from_name, parse_size_to_gb, check_episode_match, check_season_pack
from resources.modules import cache
try:
    from resources.modules.general import Addon, get_imdb
except:
    import Addon

type = ['tv', 'movie', 'torrent']

import urllib
try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus


def get_links(tv_movie, original_title, season_n, episode_n, season, episode, show_original_year, id):
    global global_var, stop_all

    try:
        zilean_url_setting = Addon.getSetting('zilean.url')
        if zilean_url_setting == '1':
            base_link = 'https://zileanfortheweebs.midnightignite.me'
        else:
            base_link = 'https://zilean.stremio.ru'

        max_size = int(Addon.getSetting('size_limit'))

        imdb = cache.get(get_imdb, 999, tv_movie, id, table='pages')
        if not imdb or imdb == ' ':
            return global_var

        if tv_movie == 'tv':
            url = '%s/dmm/filtered?ImdbId=%s&Season=%s&Episode=%s' % (base_link, imdb, season, episode)
        else:
            url = '%s/dmm/filtered?ImdbId=%s' % (base_link, imdb)
        log.warning(url)

        try:
            files = get_html(url, headers=base_header, timeout=10).json()
            if not files or not isinstance(files, list):
                return global_var
        except Exception as e:
            log.warning('ZILEAN request error: %s' % str(e))
            return global_var

        for file in files:
            try:
                if stop_all == 1:
                    break

                hash_value = file.get('info_hash', '')
                if not hash_value:
                    continue

                name = file.get('raw_title', '')
                if not name:
                    continue

                if tv_movie == 'tv':
                    if not check_episode_match(name, season_n, episode_n, season, episode):
                        if not check_season_pack(name, season_n, season):
                            continue

                quality = detect_quality_from_name(name)

                try:
                    size_bytes = float(file.get('size', 0))
                    size_gb = size_bytes / 1073741824 if size_bytes > 0 else 0
                    if size_gb > max_size:
                        continue
                    size_str = '%.2f' % size_gb
                except:
                    size_str = '0'

                lk = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash_value, quote_plus(name))
                global_var.append((name, lk, size_str, quality))

            except Exception as e:
                log.warning('ZILEAN file parse error: %s' % str(e))
                continue

    except Exception as e:
        log.warning('ZILEAN general error: %s' % str(e))

    return global_var
