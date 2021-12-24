# -*- coding: utf-8 -*-

'''
    Ant1 Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from base64 import b64decode

LIVE_LINK = 'https://antennaamdnoenc.akamaized.net/ant1_akamai/abr/playlist.m3u8'
VIDEOS_BASE = 'https://www.ant1news.gr'
VIDEOS_LINK = '/'.join([VIDEOS_BASE, 'videos'])
PLAYER_LINK = ''.join([VIDEOS_BASE, '/templates/data/player?cid={0}'])
RADIO_BASE = 'https://soundis.gr'
LIVE_RADIO = '/'.join([RADIO_BASE, 'stations/'])
YT_KEY = b64decode('JV3cLhnT3llSid3cFlUW4UEah92Xlx0Z0dXSk5mV4E3Q5NVY6lUQ'[::-1])
YT_ID = 'UC0smvAbfczoN75dP0Hw4Pzw'
SCRAMBLE = (
    'eJwVzN0KgjAYANBXiV2XbP6l3YVIWaaFEHkVUz/UlU7dnP3Qu4cPcM4X1QXaLBDBumnbLiZk7eBVj3GvV+xh0MFubPZ0dcqgUqNQzMqsQmq064RWcl'
    '4+YRQw5LyV0Eot5w1aLhDt6vsD3vO7DT40eXu9c22LYJJlCHdOK99JA19M2SGdotdRjMGsBOQDyBntYi8531buvkrUGVQThUxciJFiZX5OhfDimqPf'
    'H9WzPRs='
)
