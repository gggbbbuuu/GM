# -*- coding: utf-8 -*-

import requests
import datetime

now = datetime.datetime.now()

session = requests.Session()

_GRAPHQL_IMDB_API_URL = 'https://graphql.imdb.com'
_GRAPHQL_IMDB_API_URL2 = 'https://graphql.prod.api.imdb.a2z.com/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'https://www.imdb.com/',
    'Origin': 'https://www.imdb.com',
    'Content-Type': 'application/json'
}
session.headers.update(headers)


def get_most_popular_tv(first, after):
    query = """
        query GetMostPopularTv($first: Int!, $after: String, $endDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] }, titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              releaseDateConstraint: { releaseDateRange: { end: $endDate }}
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) {
            edges {
              node {
                title {
                  id
                  originalTitleText { text }
                  releaseYear { year }
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
        }
    """

    endDate = '%s-%s-%s' % (now.year, str(now.month).zfill(2), str(now.day).zfill(2))

    request = {'query': query, 'variables': {'first': first, 'after': after, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_most_voted_tv(first, after):
    query = """
        query GetMostVotedTv($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] }, titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] }
            }
            sort: { sortBy: USER_RATING_COUNT, sortOrder: DESC }
          ) {
            edges {
              node {
                title {
                  id
                  originalTitleText { text }
                  releaseYear { year }
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
        }
    """

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_top_rated_tv(first, after):
    query = """
        query GetTopRatedTv($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] }, titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              userRatingsConstraint: { ratingsCountRange: { min: 10000 } }
            }
            sort: { sortBy: USER_RATING, sortOrder: DESC }
          ) {
            edges {
              node {
                title {
                  id
                  originalTitleText { text }
                  releaseYear { year }
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
        }
    """

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_premier_tv(first, after):
    query = """
        query GetPremierTv($first: Int!, $after: String, $endDate: Date!, $startDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Reality-TV", "Game-Show"] },
              titleTypeConstraint: { anyTitleTypeIds: ["tvSeries", "tvMiniSeries"], excludeTitleTypeIds: [] },
              languageConstraint: { allLanguages: ["en"] },
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate }},
              userRatingsConstraint: { ratingsCountRange: { min: 50 } }
            }
            sort: { sortBy: RELEASE_DATE, sortOrder: DESC }
          ) {
            edges {
              node {
                title {
                  id
                  originalTitleText { text }
                  releaseYear { year }
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
        }
    """

    startDate = now - datetime.timedelta(days=60)
    startDate = '%s-%s-%s' % (startDate.year, str(startDate.month).zfill(2), str(startDate.day).zfill(2))
    endDate = '%s-%s-%s' % (now.year, str(now.month).zfill(2), str(now.day).zfill(2))

    request = {'query': query, 'variables': {'first': first, 'after': after, 'startDate': startDate, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


