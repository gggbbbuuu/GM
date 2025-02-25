# -*- coding: utf-8 -*-

import requests
from .query import prepare_search_request, get_node_by_id, get_offers_by_id
#from resources.lib.modules import log_utils


_GRAPHQL_API_URL = 'https://apis.justwatch.com/graphql'
headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Referer': 'https://www.justwatch.com/',
        'Origin': 'https://www.justwatch.com',
        'Content-Type': 'application/json'
}


def search(title, object_types=[], years={}, country='US', count=10):
    """Search JustWatch for given title.

    Args:
        title: title to search
        object_types: list of media types to include in search, eg MOVIE, SHOW
        years: release years range in form {'min': int, 'max': int}
        country: country to search for offers, "US" by default
        count: how many entries should be returned

    Returns:
        JustWatch json response
    """
    request = prepare_search_request(title, object_types, years, country, count)
    response = requests.post(_GRAPHQL_API_URL, headers=headers, json=request)
    #log_utils.log('Search: ' + repr(response.json()))
    response.raise_for_status()
    return response.json()


def node_by_id(id, country='US'):
    request = get_node_by_id(id, country)
    response = requests.post(_GRAPHQL_API_URL, headers=headers, json=request)
    #log_utils.log('Ep_node: ' + repr(response.json()))
    response.raise_for_status()
    return response.json()


def offers_by_id(id, country='US'):
    request = get_offers_by_id(id, country)
    response = requests.post(_GRAPHQL_API_URL, headers=headers, json=request)
    #log_utils.log('Offers: ' + repr(response.json()))
    response.raise_for_status()
    return response.json()
