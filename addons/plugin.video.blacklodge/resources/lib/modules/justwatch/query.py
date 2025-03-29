# -*- coding: utf-8 -*-

_GRAPHQL_SEARCH_QUERY = """
    query GetSearchTitles(
        $searchTitlesFilter: TitleFilter!,
        $country: Country!,
        $platform: Platform! = WEB
        $first: Int!,
        $filter: OfferFilter!,
    ) {
        popularTitles(
            country: $country
            filter: $searchTitlesFilter
            first: $first
            sortBy: POPULAR
            sortRandomSeed: 0
        ) {
        edges {
            ...SearchTitleGraphql
            }
        }
    }

    fragment SearchTitleGraphql on PopularTitlesEdge {
        __typename
        node {
            __typename
            id
            objectType
            content(country: $country, language: "en") {
                title
                originalReleaseYear
                fullPath
                externalIds {
                    imdbId
                    tmdbId
                }
            }
            offers(country: $country, platform: $platform, filter: $filter) {
                monetizationType
                presentationType
                standardWebURL
                deeplinkRoku: deeplinkURL(platform: ROKU_OS)
                deeplinkAndroid: deeplinkURL(platform: ANDROID_TV)
                package {
                    packageId
                    clearName
                    shortName
                }
            }
        }
    }
"""

def prepare_search_request(title, object_types, years, country, count):
    return {
        "operationName": "GetSearchTitles",
        "variables": {
            "first": count,
            "country": country.upper(),
            "searchTitlesFilter": {"searchQuery": title, "objectTypes": object_types, "releaseYear": years},
            "filter": {"bestOnly": False, "monetizationTypes": ["FLATRATE", "FREE", "ADS"]},
        },
        "query": _GRAPHQL_SEARCH_QUERY,
    }

##########################################################################################################################################

_GRAPHQL_NODEID_QUERY = """
    query GetNodeById(
        $nodeId: ID!,
        $country: Country!,
        $platform: Platform! = WEB,
        $filter: OfferFilter!) {
            node(id: $nodeId) {
                ...Node
            }
        }

    fragment Episode on Episode {
        __typename
        id
        content(country: $country, language: "en") {
            seasonNumber
            episodeNumber
        }
        offers(country: $country, platform: $platform, filter: $filter) {
            monetizationType
            presentationType
            standardWebURL
            deeplinkRoku: deeplinkURL(platform: ROKU_OS)
            deeplinkAndroid: deeplinkURL(platform: ANDROID_TV)
            package {
                packageId
                clearName
                shortName
            }
        }
    }

    fragment Season on Season {
        __typename
        id
        content(country: $country, language: "en") {
            seasonNumber
        }
        episodes {
            ...Episode
        }
    }

    fragment Show on Show {
        __typename
        id
        seasons {
            ...Season
        }
    }

    fragment Movie on Movie {
        __typename
        id
        offers(country: $country, platform: $platform, filter: $filter) {
            monetizationType
            presentationType
            standardWebURL
            deeplinkRoku: deeplinkURL(platform: ROKU_OS)
            deeplinkAndroid: deeplinkURL(platform: ANDROID_TV)
            package {
                packageId
                clearName
                shortName
            }
        }
    }

    fragment Node on Node {
        __typename
        id
        ...Episode
        ...Season
        ...Show
        ...Movie
    }
"""

def get_node_by_id(id, country):
    return {
        "operationName": "GetNodeById",
        "variables": {"nodeId": id, "country": country.upper(), "filter": {"bestOnly": False, "monetizationTypes": ["FLATRATE", "FREE", "ADS"]}},
        "query": _GRAPHQL_NODEID_QUERY,
    }

##########################################################################################################################################

_GRAPHQL_OFFERS_QUERY = """
    query GetTitleOffers(
        $nodeId: ID!,
        $country: Country!,
        $filterFlatrate: OfferFilter!,
        $platform: Platform! = WEB
    ) {
        node(id: $nodeId) {
            __typename
            id
            ... on MovieOrShowOrSeasonOrEpisode {
                flatrate: offers(
                    country: $country,
                    platform: $platform,
                    filter: $filterFlatrate
                ) {
                    ...TitleOffer
                  }
                }
            }
        }

    fragment TitleOffer on Offer {
        presentationType
        monetizationType
        package {
            packageId
            clearName
            shortName
        }
        standardWebURL
        deeplinkRoku: deeplinkURL(platform: ROKU_OS)
        deeplinkAndroid: deeplinkURL(platform: ANDROID_TV)
    }
"""

def get_offers_by_id(id, country):
    return {
        "operationName": "GetTitleOffers",
        "variables": {"nodeId": id, "country": country, "filterFlatrate": {"monetizationTypes": ["FLATRATE", "ADS", "FREE"], "bestOnly": False}},
        "query": _GRAPHQL_OFFERS_QUERY,
    }

