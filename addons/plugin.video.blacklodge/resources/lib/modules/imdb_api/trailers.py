# -*- coding: utf-8 -*-

from .imdb_client import imdb_request


def get_imdb_trailers(imdb_id):
    query = '''
        query GetVideos($id: ID!) {
            title(id: $id) {
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
    response = imdb_request(request)
    return response


def get_playback_url(video_id):
    query = '''
        query VideoPlayback($viconst: ID!) {
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

    request = {'query': query, 'variables': {'viconst': video_id}}
    response = imdb_request(request)
    return response


