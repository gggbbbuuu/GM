# -*- coding: utf-8 -*-

import requests
import datetime

now = datetime.datetime.now()

_GRAPHQL_IMDB_API_URL_ = 'https://graphql.imdb.com'
_GRAPHQL_IMDB_API_URL2 = 'https://graphql.prod.api.imdb.a2z.com/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
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

    votes = params.get('votes', '')
    if votes:
        votes = """\n              userRatingsConstraint: { ratingsCountRange: { min: %d } }""" % int(votes)

    keyword = params.get('kw', '')
    if keyword:
        keyword = ['"'+k+'"' for k in keyword.split(',')]
        keyword = """\n              keywordConstraint: { anyKeywords: [%s] }""" % ', '.join(keyword)

    genre = params.get('genre', '')
    if genre: genre = ['"'+g+'"' for g in genre.split(',')]
    excGenre = params.get('excGenre', '')
    if excGenre: excGenre = ['"'+g+'"' for g in excGenre.split(',')]
    if genre or excGenre:
        genre = """\n              genreConstraint: { allGenreIds: [%s], excludeGenreIds: [%s] }""" % (', '.join(genre), ', '.join(excGenre))

    cert = params.get('cert', '')
    if cert: cert = ', '.join(["""{ rating: "%s", region: "US" }""" % c for c in cert.split(',')])
    excCert = params.get('excCert', '')
    if excCert: excCert = ', '.join(["""{ rating: "%s", region: "US" }""" % c for c in excCert.split(',')])
    if cert or excCert:
        cert = """\n              certificateConstraint: { anyRegionCertificateRatings: [%s], excludeRegionCertificateRatings: [%s] }""" % (cert, excCert)

    lang = params.get('lang', '')
    if lang:
        lang = ['"'+l+'"' for l in lang.split(',')]
        lang = """\n              languageConstraint: { anyPrimaryLanguages: [%s] }""" % ', '.join(lang)

    awards = params.get('awards', '')
    if awards:
        awards = awards.split(',')
        event = awards[0]
        category = """, searchAwardCategoryId: "%s" """ % awards[1] if awards[1] else ''
        winner = """, winnerFilter: %s """ % awards[2] if awards[2] else ''
        awards = """\n              awardConstraint: { allEventNominations: [{ eventId: "%s"%s%s}] }""" % (event, category, winner)

    groups = params.get('groups', '')
    if groups:
        groups = """\n              rankedTitleListConstraint: { allRankedTitleLists: [{ rankRange: { max: %s }, rankedTitleListType: TOP_RATED_MOVIES }] }""" % int(groups)

    searchTerm = params.get('search', '')
    if searchTerm:
        searchTerm = """\n              titleTextConstraint: { searchTerm: "%s" }""" % searchTerm

    with_name = params.get('nameId', '')
    if with_name:
        with_name = """\n              titleCreditsConstraint: { allCredits: [{ nameId: "%s" }] }""" % with_name

    query = """
        query AdvancedSearch($first: Int!, $after: String, $titleType: [String!], $startDate: Date, $endDate: Date, $sort: AdvancedTitleSearchSort) {
          advancedTitleSearch(
            first: $first
            after: $after
            constraints: {
              titleTypeConstraint: { anyTitleTypeIds: $titleType }
              releaseDateConstraint: { releaseDateRange: { start: $startDate, end: $endDate } }%s%s%s%s%s%s%s%s%s
            }
            sort: $sort
          ) {
            edges {
              node {
                title {
                  id
                  titleText {
                    text
                  }
                  releaseYear {
                    year
                  }
                  releaseDate {
                    year
                    month
                    day
                  }
                  ratingsSummary {
                    aggregateRating
                    voteCount
                  }
                  plot {
                    plotText {
                      plainText
                    }
                  }
                  primaryImage {
                    url
                  }
                  certificate {
                    rating
                  }
                  runtime {
                    seconds
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
    """ % (votes, keyword, genre, cert, lang, awards, groups, searchTerm, with_name)

    variables = {
        'first': first,
        'after': after,
        'startDate': startDate,
        'endDate': endDate,
        'titleType': params['titleType'].split(','),
        'sort': {'sortBy': params['sort'].split(',')[0], 'sortOrder': params['sort'].split(',')[1]}
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
                  titleText {
                    text
                  }
                  releaseYear {
                    year
                  }
                  releaseDate {
                    year
                    month
                    day
                  }
                  ratingsSummary {
                    aggregateRating
                    voteCount
                  }
                  plot {
                    plotText {
                      plainText
                    }
                  }
                  primaryImage {
                    url
                  }
                  certificate {
                    rating
                  }
                  runtime {
                    seconds
                  }
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
                  titleText {
                    text
                  }
                  releaseYear {
                    year
                  }
                  releaseDate {
                    year
                    month
                    day
                  }
                  ratingsSummary {
                    aggregateRating
                    voteCount
                  }
                  plot {
                    plotText {
                      plainText
                    }
                  }
                  primaryImage {
                    url
                  }
                  certificate {
                    rating
                  }
                  runtime {
                    seconds
                  }
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

    variables = {
        'first': first,
        'after': after,
        'listId': params['list'],
        'titleType': params['titleType'].split(','),
        'sort': {'by': params['sort'].split(',')[0], 'order': params['sort'].split(',')[1]}
    }

    request = {'query': query, 'variables': variables}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['list']['titleListItemSearch']


