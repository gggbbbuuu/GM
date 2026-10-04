# -*- coding: utf-8 -*-

import requests

_GRAPHQL_IMDB_API_URL_ = 'https://graphql.imdb.com'
_GRAPHQL_IMDB_API_URL2 = 'https://graphql.prod.api.imdb.a2z.com/'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'Referer': 'https://www.imdb.com/',
    'Origin': 'https://www.imdb.com',
    'Content-Type': 'application/json',
    'Accept-Language': 'en-US',
    'x-imdb-client-name': 'imdb-web-next',
    'x-imdb-user-language': 'en-US'
}

_session = requests.Session()
_session.headers.update(HEADERS)

def imdb_request(payload):
    try:
        response = _session.post(_GRAPHQL_IMDB_API_URL2, json=payload)
        response.raise_for_status()
        return response.json()
    except:
        from resources.lib.modules import log_utils
        log_utils.log('imdb_request_fail', 1)
        return {}