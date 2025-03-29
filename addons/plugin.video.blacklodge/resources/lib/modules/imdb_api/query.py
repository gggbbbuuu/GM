# -*- coding: utf-8 -*-


def get_imdb_trailers(imdb_id):
    _GRAPHQL_TRAILERS_QUERY = '''query (
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

    variables = {'id': imdb_id}
    return {'query': _GRAPHQL_TRAILERS_QUERY, 'variables': variables}

