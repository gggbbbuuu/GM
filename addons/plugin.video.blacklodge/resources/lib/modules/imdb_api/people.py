# -*- coding: utf-8 -*-

import requests

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


def get_people(first, after, params):
    query = """
        query GetPopularPeople($first: Int!, $after: String) {
          advancedNameSearch(first: $first, after: $after, sort: { sortBy: POPULARITY, sortOrder: ASC }) {
            edges {
              node {
                name {
                  id
                  nameText {
                    text
                  }
                  primaryImage {
                    url
                  }
                  primaryProfessions {
                    category {
                      text
                    }
                  }
                  bio {
                    text {
                      plainText
                    }
                  }
                  knownForV2 {
                    credits {
                      title {
                        titleText {
                          text
                        }
                      }
                    }
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
    """

    request = {'query': query, 'variables': {'first': first, 'after': after}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['advancedNameSearch']


def search_people(first, after, params):
    query = """
        query SearchByName($searchTerm: String!) {
          mainSearch(first: 20, options: { searchTerm: $searchTerm, type: NAME, includeAdult: false }) {
            edges {
              node {
                entity {
                  ... on Name {
                    id
                    nameText {
                      text
                    }
                    primaryImage {
                      url
                    }
                    primaryProfessions {
                      category {
                        text
                      }
                    }
                    bio {
                      text {
                        plainText
                      }
                    }
                    knownForV2 {
                      credits {
                        title {
                          titleText {
                            text
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    request = {'query': query, 'variables': {'searchTerm': params['searchTerm']}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['mainSearch']


def get_person_details(nameId):
    query = """
        query GetPersonDetails($nameId: ID!) {
          name(id: $nameId) {
            nameText {
              text
            }
            birthDate {
              date
            }
            deathStatus
            deathDate {
              date
            }
            bio {
              text {
                plainText
              }
            }
          }
        }
    """

    request = {'query': query, 'variables': {'nameId': nameId}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()['data']['name']

