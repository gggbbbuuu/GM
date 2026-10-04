# -*- coding: utf-8 -*-

from .imdb_client import imdb_request


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
    response = imdb_request(request)
    return response['data']['advancedNameSearch']


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
    response = imdb_request(request)
    return response['data']['mainSearch']


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
    response = imdb_request(request)
    return response['data']['name']

