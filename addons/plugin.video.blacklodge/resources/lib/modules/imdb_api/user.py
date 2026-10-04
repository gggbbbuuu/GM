# -*- coding: utf-8 -*-

from .imdb_client import imdb_request


def get_userlists(uid):
    #$listElementType applicable values: TITLES, PEOPLE, VIDEOS, IMAGES, GALLERIES

    query = """
        query UserLists($userId: ID!) {
          lists(
            first: 1000
            listOwnerUserId: $userId
            filter:{
              classTypes: LIST
              listElementType: TITLES
            } 
          ) {
            edges{
              node{
                id
                author {
                  userId
                  nickName
                }
                name {
                  originalText
                }
              }
            }
          }
        }
    """

    request = {'query': query, 'variables': {'userId': uid}}
    response = imdb_request(request)
    return response['data']['lists']


def get_watchlist_id(uid):
    #$listClass applicable values: SEEN, NOT_INTERESTED, FAVORITE_THEATRES, FAVORITE_ACTORS, CHECK_INS, WATCH_LIST

    query = """
        query UserWatchList($userId: ID!) {
          predefinedList(
            classType: WATCH_LIST
            userId: $userId
          ){
            id
            name {
              originalText
            }
            author {
              userId
              nickName
            }
          }
        }
    """

    request = {'query': query, 'variables': {'userId': uid}}
    response = imdb_request(request)
    return response['data']['predefinedList']['id']


