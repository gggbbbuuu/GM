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


def get_oscar_winners(first, after):
    query = """
        query GetOscarWinners($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              awardConstraint: { allEventNominations: [{ eventId: "ev0000003", searchAwardCategoryId: "bestPicture", winnerFilter: WINNER_ONLY }] },
              titleTypeConstraint: { anyTitleTypeIds: ["movie"] }
            }
            sort: { sortBy: YEAR, sortOrder: DESC }
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
                  runtime { seconds }
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


def get_top_rated(first, after):
    query = """
        query GetTopRatedMovies($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] }, titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] },
              userRatingsConstraint: { ratingsCountRange: { min: 100000 } }
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
                  runtime { seconds }
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


def get_most_voted(first, after):
    query = """
        query GetMostVotedMovies($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] }, titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] }
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
                  runtime { seconds }
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


def get_most_popular(first, after):
    query = """
        query GetMostPopularMovies($first: Int!, $after: String, $endDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] }, titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] },
              rankedTitleListConstraint: { allRankedTitleLists: [{ rankRange: { max: 1000 }, rankedTitleListType: TOP_RATED_MOVIES }], excludeRankedTitleLists: [] },
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
                  runtime { seconds }
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


def get_featured(first, after):
    query = """
        query GetFeaturedMovies($first: Int!, $after: String, $endDate: Date!, $startDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] },
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] },
              languageConstraint: { allLanguages: ["en"] },
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate }}
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
                  runtime { seconds }
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

    startDate = now - datetime.timedelta(days=365)
    startDate = '%s-%s-%s' % (startDate.year, str(startDate.month).zfill(2), str(startDate.day).zfill(2))
    endDate = '%s-%s-%s' % (now.year, str(now.month).zfill(2), str(now.day).zfill(2))

    request = {'query': query, 'variables': {'first': first, 'after': after, 'startDate': startDate, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_added(first, after):
    query = """
        query GetAdded($first: Int!, $after: String, $endDate: Date!, $startDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] },
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] },
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate }},
              userRatingsConstraint: { ratingsCountRange: { min: 100 } }
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
                  runtime { seconds }
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

    startDate = now - datetime.timedelta(days=365)
    startDate = '%s-%s-%s' % (startDate.year, str(startDate.month).zfill(2), str(startDate.day).zfill(2))
    endDate = '%s-%s-%s' % (now.year, str(now.month).zfill(2), str(now.day).zfill(2))

    request = {'query': query, 'variables': {'first': first, 'after': after, 'startDate': startDate, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_boxoffice(first, after):
    query = """
        query GetBoxOffice($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] }
            }
            sort: { sortBy: BOX_OFFICE_GROSS_DOMESTIC, sortOrder: DESC }
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
                  runtime { seconds }
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


