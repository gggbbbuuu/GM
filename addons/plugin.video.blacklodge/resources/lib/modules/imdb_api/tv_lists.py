# -*- coding: utf-8 -*-

import requests
import datetime

now = datetime.datetime.now()

_GRAPHQL_IMDB_API_URL = 'https://graphql.imdb.com'
_GRAPHQL_IMDB_API_URL2 = 'https://graphql.prod.api.imdb.a2z.com/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'https://www.imdb.com/',
    'Origin': 'https://www.imdb.com',
    'Content-Type': 'application/json',
    'Accept-Language': 'en-US'
}
session = requests.Session()
session.headers.update(headers)


edges = """{
            edges {
              node {
                title {
                  id
                  titleText { text }
                  releaseYear { year }
                  releaseDate {
                    year
                    month
                    day
                  }
                  ratingsSummary {
                    aggregateRating
                    voteCount
                  }
                  plot { plotText { plainText } }
                  primaryImage { url }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
    """


def get_keyword_tv(first, after, params):
    query = """
        query GetKeywordTv($first: Int!, $after: String, $endDate: Date!, $keyword: String!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              releaseDateConstraint: { releaseDateRange: { end: $endDate }},
              keywordConstraint: { anyKeywords: [$keyword], excludeKeywords: [] }
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) %s
        }
    """ % edges

    endDate = now.strftime('%Y-%m-%d')

    request = {'query': query, 'variables': {'first': first, 'after': after, 'endDate': endDate, 'keyword': params}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_genre_tv(first, after, params):
    query = """
        query GetGenreTv($first: Int!, $after: String, $endDate: Date!, $genre: String!, $exclude: String!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              releaseDateConstraint: { releaseDateRange: { end: $endDate }},
              genreConstraint: { allGenreIds: [$genre], excludeGenreIds: [$exclude] }
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) %s
        }
    """ % edges

    endDate = now.strftime('%Y-%m-%d')
    exclude = 'Documentary' if not params == 'Documentary' else ''

    request = {'query': query, 'variables': {'first': first, 'after': after, 'endDate': endDate, 'genre': params, 'exclude': exclude}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_language_tv(first, after, params):
    query = """
        query GetLanguageTv($first: Int!, $after: String, $endDate: Date!, $lang: String!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              releaseDateConstraint: { releaseDateRange: { end: $endDate }},
              languageConstraint: { anyPrimaryLanguages: [$lang] }
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) %s
        }
    """ % edges

    endDate = now.strftime('%Y-%m-%d')

    request = {'query': query, 'variables': {'first': first, 'after': after, 'endDate': endDate, 'lang': params}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_year_tv(first, after, params):
    query = """
        query GetYearTv($first: Int!, $after: String, $endDate: Date!, $startDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] },
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate }}
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) %s
        }
    """ % edges

    years = params.split(',')
    startDate = '%s-01-01' % years[0]
    endDate = '%s-12-31' % years[1]

    request = {'query': query, 'variables': {'first': first, 'after': after, 'startDate': startDate, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_certification_tv(first, after, params):
    query = """
        query GetCertificationTv($first: Int!, $after: String, $endDate: Date!, $cert: String!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              releaseDateConstraint: { releaseDateRange: { end: $endDate }},
              certificateConstraint: { anyRegionCertificateRatings: [{ rating: $cert, region: "US" }], excludeRegionCertificateRatings: [] }
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) %s
        }
    """ % edges

    endDate = now.strftime('%Y-%m-%d')

    request = {'query': query, 'variables': {'first': first, 'after': after, 'endDate': endDate, 'cert': params}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()



