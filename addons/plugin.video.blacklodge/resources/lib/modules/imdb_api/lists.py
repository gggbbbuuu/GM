# -*- coding: utf-8 -*-

import requests
import datetime

now = datetime.datetime.now()

_GRAPHQL_IMDB_API_URL_ = 'https://graphql.imdb.com'
_GRAPHQL_IMDB_API_URL2 = 'https://graphql.prod.api.imdb.a2z.com/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'https://www.imdb.com/',
    'Origin': 'https://www.imdb.com',
    'Content-Type': 'application/json',
    'Accept-Language': 'en-US',
    'x-imdb-client-name': 'imdb-web-next',
    'x-imdb-user-language': 'en-US'
}
session = requests.Session()
session.headers.update(headers)


def advanced_search(first, after, params):
    startDate = params.get('startDate', '')
    if startDate.isdigit() and len(startDate) == 4: startDate = '%s-01-01' % startDate
    elif startDate.isdigit() and len(startDate) < 4: startDate = (now - datetime.timedelta(days=int(startDate))).strftime('%Y-%m-%d')
    else: startDate = '1888-01-01'

    endDate = params.get('endDate', '')
    if endDate.isdigit() and len(endDate) == 4: endDate = '%s-12-31' % endDate
    elif endDate.isdigit() and len(endDate) < 4: endDate = (now - datetime.timedelta(days=int(endDate))).strftime('%Y-%m-%d')
    else: endDate = now.strftime('%Y-%m-%d')

    sort = params['sort'].split(',')
    sortBy = sort[0].upper().replace('ALPHA', 'TITLE_REGIONAL')
    sortOrder = sort[1].upper()

    votes = params.get('votes', '')
    if votes:
        votes = """userRatingsConstraint: { ratingsCountRange: { min: %d } }""" % int(votes)

    keyword = params.get('kw', '')
    if keyword:
        keyword = """keywordConstraint: { anyKeywords: ["%s"] }""" % keyword

    genre = params.get('genre', '')
    if genre: genre = ['"'+g+'"' for g in genre.split(',')]
    excGenre = params.get('excGenre', '')
    if excGenre: excGenre = ['"'+g+'"' for g in excGenre.split(',')]
    if genre or excGenre:
        genre = """genreConstraint: { allGenreIds: [%s], excludeGenreIds: [%s] }""" % (', '.join(genre), ', '.join(excGenre))

    cert = params.get('cert', '')
    if cert: cert = ', '.join(["""{ rating: "%s", region: "US" }""" % c for c in cert.split(',')])
    excCert = params.get('excCert', '')
    if excCert: excCert = ', '.join(["""{ rating: "%s", region: "US" }""" % c for c in excCert.split(',')])
    if cert or excCert:
        cert = """certificateConstraint: { anyRegionCertificateRatings: [%s], excludeRegionCertificateRatings: [%s] }""" % (cert, excCert)

    lang = params.get('lang', '')
    if lang:
        lang = """languageConstraint: { anyPrimaryLanguages: ["%s"] }""" % lang

    awards = params.get('awards', '')
    if awards:
        awards = """awardConstraint: { allEventNominations: [{eventId: "%s", searchAwardCategoryId: "%s", winnerFilter: %s}] }""" % (awards.split(',')[0], awards.split(',')[1], awards.split(',')[2])

    groups = params.get('groups', '')
    if groups:
        groups = """rankedTitleListConstraint: { allRankedTitleLists: [{ rankRange: { max: %s }, rankedTitleListType: TOP_RATED_MOVIES }] }"""% int(groups)

    query = """
        query AdvancedSearch($first: Int!, $after: String, $titleType: [String!], $startDate: Date, $endDate: Date, $sort: AdvancedTitleSearchSort) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: $titleType }
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate }}
              %s
              %s
              %s
              %s
              %s
              %s
              %s
            }
            sort: $sort
          ) {
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
                  certificate { rating }
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
    """ % (votes, keyword, genre, cert, lang, awards, groups)

    variables = {
        'first': first,
        'after': after,
        'startDate': startDate,
        'endDate': endDate,
        'titleType': params['titleType'].split(','),
        'sort': {'sortBy': sortBy, 'sortOrder': sortOrder}
    }

    request = {'query': query, 'variables': variables}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['advancedTitleSearch']


def more_like_this(first, after, params):
    query = """
        query similar(
          $imdb: ID!
          $first: Int!
          %s
        ) {
          title(id: $imdb) {
            moreLikeThisTitles(
              first: $first
              %s
            ) {
              edges {
                node {
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
                  certificate { rating }
                  runtime { seconds }
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
    """ % ('$after: ID' if after else '', 'after: $after' if after else '')

    request = {'query': query, 'variables': {'imdb': params['imdb'], 'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['title']['moreLikeThisTitles']


def get_customlist(first, after, params):
    query = """
        query GetListDetails($listId: ID!, $first: Int!, $after: String, $titleType: [String!], $sort: TitleListSearchSort) {
          list(id: $listId) {
            titleListItemSearch(
              first: $first
              after: $after
              filter: { titleTypeConstraint: { anyTitleTypeIds: $titleType } }
              sort: $sort
            ) {
              edges {
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
                  certificate { rating }
                  runtime { seconds }
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
    """

    sort = params['sort'].split(',')
    sortBy = sort[0].upper().replace('ALPHA', 'TITLE_REGIONAL')
    sortOrder = sort[1].upper()

    variables = {
        'first': first,
        'after': after,
        'listId': params['list'],
        'titleType': params['titleType'].split(','),
        'sort': {'by': sortBy, 'order': sortOrder}
    }

    request = {'query': query, 'variables': variables}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['list']['titleListItemSearch']


