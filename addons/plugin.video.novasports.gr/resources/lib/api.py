# -*- coding: utf-8 -*-

'''
    Novasports.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json
import re
from urllib.parse import urlencode

from .constants import (
    BASE_LINK, VIDEO_REST_LINK, MATCHCENTER_LINK, TAX_EVENT, TAX_SHOW, VIDEO_FIELDS
)

try:
    from tulip import kodi
except ImportError:
    kodi = None

try:
    from netclient import Net

    _net = Net()
except ImportError:
    _net = None


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------

def _fetch(url, headers=None, timeout=30):

    headers = dict(headers or {})
    headers.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                    '(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')
    headers.setdefault('Accept', '*/*')

    if _net is not None:
        response = _net.http_GET(url, headers=headers, timeout=timeout)
        # netclient falls back to ascii when a response carries no charset,
        # which mangles the Greek titles, so always decode the raw bytes.
        return response.nodecode(True).content, response.get_headers(as_dict=True)

    import urllib.request

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), dict(response.headers)


def _get_json(url, headers=None, timeout=30):

    body, response_headers = _fetch(url, headers=headers, timeout=timeout)
    return json.loads(body.decode('utf-8')), response_headers


# ---------------------------------------------------------------------------
# Listing / taxonomy
# ---------------------------------------------------------------------------

def per_page():

    try:
        return max(1, min(100, int(kodi.setting('per_page'))))
    except Exception:
        return 40


def videos(page=1, taxonomy=None, term=None, search=None, date=None):

    """Returns (items, total_pages)."""

    params = {
        'per_page': per_page(),
        'page': max(1, int(page or 1)),
        '_fields': VIDEO_FIELDS,
        'orderby': 'date',
        'order': 'desc',
    }

    if taxonomy and term:
        params[taxonomy] = term

    if search:
        params['search'] = search

    if date:
        params['after'] = '{}T00:00:00'.format(date)
        params['before'] = '{}T23:59:59'.format(date)

    data, response_headers = _get_json('{}?{}'.format(VIDEO_REST_LINK, urlencode(params)))

    return [_listing_item(item) for item in data], _total_pages(response_headers, per_page())


def _listing_item(item):

    return {
        'title': _clean(item.get('title', {}).get('rendered', '')),
        'url': item.get('link'),
        'image': item.get('featured_media_url') or '',
        'plot': _clean(item.get('acf', {}).get('video_short_desc', '') or ''),
        'date': item.get('date', ''),
        'studio': _studios(item),
    }


def _studios(item):
    """Competition / show names, used as the listing's studio field."""

    taxonomies = item.get('taxonomies') or {}

    names = []

    for key in (TAX_EVENT, TAX_SHOW):
        for entry in (taxonomies.get(key) or [])[:1]:
            if isinstance(entry, dict) and entry.get('name'):
                names.append(_clean(entry['name']))

    seen, out = set(), []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)

    return ', '.join(out[:2])


def terms(taxonomy, page=1):

    params = {
        'per_page': 100,
        'page': max(1, int(page or 1)),
        'hide_empty': 'true',
        'orderby': 'count',
        'order': 'desc',
        '_fields': 'id,name,slug,count',
    }

    data, response_headers = _get_json(
        '{}/wp/v2/{}?{}'.format(BASE_LINK + '/wp-json', taxonomy, urlencode(params))
    )

    return [
        {'id': item['id'], 'title': _clean(item.get('name', '')), 'count': item.get('count', 0)}
        for item in data
    ], _total_pages(response_headers, 100)


def match_center(date):

    data, _ = _get_json('{}?{}'.format(MATCHCENTER_LINK, urlencode({'dt': date})))
    return data


def _total_pages(headers, per_page):

    for key in ('X-Wp-Totalpages', 'x-wp-totalpages'):
        if key in headers:
            try:
                return int(headers[key])
            except (TypeError, ValueError):
                return 1

    return 1


# ---------------------------------------------------------------------------

def _clean(text):

    try:
        from html import unescape

        return unescape(re.sub(r'<[^>]+>', '', text or '')).strip()
    except Exception:
        return text or ''