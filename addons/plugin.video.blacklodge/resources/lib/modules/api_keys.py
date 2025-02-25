# -*- coding: utf-8 -*-

import base64
from six import ensure_text


tmdb_key = ensure_text(base64.b64decode(b'ZTJlYTlmM2M2NDQ2YTNjZDcxZGU2MGRlNDE2NjcwYTA='))[::-1]
tvdb_key = ensure_text(base64.b64decode(b'TkdDNjdYWElIUUw4T0NNSgo='))[::-1]
omdb_key = ''
fanarttv_key = ensure_text(base64.b64decode(b'MTcyZDMwYmNiY2ZmZTFkNWZiOWEzMzEzNzNmYjdiYjA='))[::-1]
yt_key = ''
trakt_client_id = ensure_text(base64.b64decode(b'YTY1MGIyNjBjZWYyZjcwZDUyM2ZmNWQyMWE1Mzc4Mzc3MmNkZmQ4ZjA1MWY4MjU3ZjA2MWIwZDExYjQzNDIxMw=='))[::-1]
trakt_secret = ensure_text(base64.b64decode(b'ZTk4YTkxZGVjMDM3NWQ4NTFiM2U1OGQ5ZjgzODIyYWUwYzQzYzcwMTNkOTUyZGZjMDQ2YWFkMWUwZDJiZTYzMQ=='))[::-1]
opensubtitles_key = ensure_text(base64.b64decode(b'OEcwRjRFejJmaWV4eXYzOXZFWnIwZWVOWXhwZzhBTlA='))[::-1]
pin = ensure_text(base64.b64decode(b'NTQwMjQwMjQ='))[::-1]
