# -*- coding: utf-8 -*-

import requests

session = requests.Session()

_GRAPHQL_IMDB_API_URL = 'https://graphql.imdb.com'
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
session.headers.update(headers)


def get_imdb_trailers(imdb_id):
    query = '''
        query (
            $id: ID!
        ) {
            title(
                id: $id
            ) {
                titleText {
                    text
                }
                primaryVideos(first: 100) {
                    edges {
                        node {
                            id
                            name {
                                value
                            }
                            contentType {
                                displayName {
                                    value
                                }
                            }
                            description {
                                value
                            }
                            thumbnail {
                                url
                            }
                            primaryTitle {
                                id
                            }
                        }
                    }
                }
            }
        }
    '''

    request = {'query': query, 'variables': {'id': imdb_id}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


def get_playback_url(video_id):
    query = '''
        query VideoPlayback(
            $viconst: ID!
        ) {
            video(id: $viconst) {
                ...SharedVideoAllPlaybackUrls
            }
        }

        fragment SharedVideoAllPlaybackUrls on Video {
            playbackURLs {
                displayName {
                    value
                }
                videoMimeType
                url
            }
        }
    '''

    request = {'operationName': 'VideoPlayback', 'query': query, 'variables': {'viconst': video_id}}
    response = session.post(_GRAPHQL_IMDB_API_URL2, json=request)
    response.raise_for_status()
    return response.json()


