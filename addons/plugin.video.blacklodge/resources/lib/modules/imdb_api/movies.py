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
                  runtime { seconds }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
    """


def get_oscar_winners(first, after, params):
    query = """
        query GetOscarWinners($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["movie"] },
              awardConstraint: { allEventNominations: [{ eventId: "ev0000003", searchAwardCategoryId: "bestPicture", winnerFilter: WINNER_ONLY }] }
            }
            sort: { sortBy: YEAR, sortOrder: DESC }
          ) %s
        }
    """ % edges

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_top_rated(first, after, params):
    query = """
        query GetTopRatedMovies($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] },
              userRatingsConstraint: { ratingsCountRange: { min: 100000 } }
            }
            sort: { sortBy: USER_RATING, sortOrder: DESC }
          ) %s
        }
    """ % edges

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_most_voted(first, after, params):
    query = """
        query GetMostVotedMovies($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] }
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] }
            }
            sort: { sortBy: USER_RATING_COUNT, sortOrder: DESC }
          ) %s
        }
    """ % edges

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_most_popular(first, after, params):
    query = """
        query GetMostPopularMovies($first: Int!, $after: String, $endDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] },
              rankedTitleListConstraint: { allRankedTitleLists: [{ rankRange: { max: 1000 }, rankedTitleListType: TOP_RATED_MOVIES }], excludeRankedTitleLists: [] },
              releaseDateConstraint: { releaseDateRange: { end: $endDate }}
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) %s
        }
    """ % edges

    endDate = now.strftime('%Y-%m-%d')

    request = {'query': query, 'variables': {'first': first, 'after': after, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_featured(first, after, params):
    query = """
        query GetFeaturedMovies($first: Int!, $after: String, $endDate: Date!, $startDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] },
              languageConstraint: { allLanguages: ["en"] },
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate }}
            }
            sort: { sortBy: POPULARITY, sortOrder: ASC }
          ) %s
        }
    """ % edges

    startDate = (now - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    endDate = now.strftime('%Y-%m-%d')

    request = {'query': query, 'variables': {'first': first, 'after': after, 'startDate': startDate, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_added(first, after, params):
    query = """
        query GetAdded($first: Int!, $after: String, $endDate: Date!, $startDate: Date!) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] },
              genreConstraint: { allGenreIds: [], excludeGenreIds: ["Documentary"] },
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate }},
              userRatingsConstraint: { ratingsCountRange: { min: 100 } }
            }
            sort: { sortBy: RELEASE_DATE, sortOrder: DESC }
          ) %s
        }
    """ % edges

    startDate = (now - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    endDate = now.strftime('%Y-%m-%d')

    request = {'query': query, 'variables': {'first': first, 'after': after, 'startDate': startDate, 'endDate': endDate}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_boxoffice(first, after, params):
    query = """
        query GetBoxOffice($first: Int!, $after: String) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: ["movie", "tvMovie"], excludeTitleTypeIds: [] }
            }
            sort: { sortBy: BOX_OFFICE_GROSS_DOMESTIC, sortOrder: DESC }
          ) %s
        }
    """ % edges

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()



