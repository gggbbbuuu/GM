"""MyDramaList title aliases for Asian dramas and films, through the unofficial Kuryana API.

TMDb is missing romanized, English and native variants that release names use. MyDramaList lists them as
"also known as" titles. Kuryana (https://github.com/tbdsux/kuryana) scrapes MyDramaList on request and has no TMDb id
lookup, so a title is searched, the hits are filtered by year and country, and the detail page of a hit is only
accepted when one of the TMDb titles is among its titles. Anything that does not match gives no aliases.

The service is a free single-maintainer host: every failure is a normal miss, a failed or slow call pauses all calls
for a few minutes, and results (also misses) are kept in Seren's cache database.
"""

import datetime
import re
import time
import unicodedata
from urllib.parse import quote

import requests

from resources.lib.modules.globals import g

KURYANA_URL = "https://kuryana.tbdh.app"
REQUEST_TIMEOUT = (3, 5)  # connect, read - the service scrapes live and a play waits for this
MAX_CALLS = 3  # per lookup: a search and up to two detail pages (or a second search)
MAX_DETAIL_PAGES = 2
MAX_SECONDS = 10  # per lookup
MAX_LATIN_ALIASES = 6
MAX_NATIVE_ALIASES = 2
MAX_WORDS = 6  # longer titles are descriptive subtitles, not names a release would use

FOUND_CACHE_DAYS = 30
RECENT_CACHE_DAYS = 7  # a drama from the last two years is still getting alternative titles
MISSING_CACHE_HOURS = 24
BREAKER_MINUTES = 10
BREAKER_KEY = "kuryana.down"

# Country code -> first word of the MyDramaList type ("Korean Drama", "Hong Kong TV Show", "Thai Movie").
# Countries MyDramaList barely covers (India, ...) are left out, so a play there costs no call.
_COUNTRY_WORDS = {
    "KR": "korean",
    "CN": "chinese",
    "TW": "taiwanese",
    "HK": "hong kong",
    "TH": "thai",
    "JP": "japanese",
    "PH": "filipino",
}
_SHOW_KINDS = ("drama", "tv show")
_MOVIE_KINDS = ("movie",)

# Seasons, parts and specials are separate MyDramaList entries; their names would match the wrong releases.
_JUNK_RE = re.compile(r"\b(?:season|part|special|episode)\b|\bs\d{1,2}\b", re.IGNORECASE)

_memory = {}  # {cache key: [aliases]} - every plugin call is a fresh interpreter, g.CACHE is the real cache


class _Unavailable(Exception):
    """The service timed out, refused us or failed (not a normal 'no such drama')."""


def get_aliases(media_type, tmdb_id, title, original_title, year, country):
    """Alternative titles of a drama (media_type 'tv') or film ('movie') from MyDramaList.

    Args:
        media_type: 'tv' or 'movie'
        tmdb_id: TMDb id of the show / movie (the cache key)
        title: title TMDb gives (not a user substitute)
        original_title: TMDb's native-language title
        year: first air year / release year, str or int
        country: TMDb origin country code, e.g. 'KR'

    Returns:
        list of title strings (empty when MyDramaList has no match or the service cannot be reached)
    """
    try:
        return _get_aliases(media_type, tmdb_id, title, original_title, year, country)
    except Exception as e:  # nothing here may break a scrape
        g.log(f"MyDramaList aliases failed for '{title}': {e}", "warning")
        return []


def _get_aliases(media_type, tmdb_id, title, original_title, year, country):
    word = _COUNTRY_WORDS.get((country or "").upper())
    year = _to_year(year)
    if not word or not title or not year or media_type not in ("tv", "movie"):
        return []

    key = _cache_key(media_type, tmdb_id, title, year)
    cached = _lookup(key)
    if cached is not None:
        return cached

    if _service_down():
        return []

    try:
        aliases = _search(media_type, word, title, original_title, year)
    except _Unavailable as e:
        g.log(f"MyDramaList (Kuryana) unavailable, pausing for {BREAKER_MINUTES} minutes: {e}", "info")
        _store(BREAKER_KEY, True, datetime.timedelta(minutes=BREAKER_MINUTES))
        return []

    if aliases:
        days = RECENT_CACHE_DAYS if year >= datetime.date.today().year - 1 else FOUND_CACHE_DAYS
        _store(key, aliases, datetime.timedelta(days=days))
    else:
        _store(key, [], datetime.timedelta(hours=MISSING_CACHE_HOURS))
    return aliases


def _to_year(value):
    match = re.match(r"\s*(\d{4})", str(value or ""))
    return int(match.group(1)) if match else 0


def _cache_key(media_type, tmdb_id, title, year):
    # TMDb show and movie ids overlap, so the kind is part of the key
    if tmdb_id:
        return f"kuryana.{media_type}.{tmdb_id}"
    return f"kuryana.{media_type}.t.{_norm(title)}.{year}"


def _lookup(key):
    """The cached aliases (memory, then the cache database), or None if not cached."""
    if key in _memory:
        return _memory[key]
    from resources.lib.database.cache import CacheBase

    try:
        cached = g.CACHE.get(key)
    except Exception as e:  # a cache problem must never break a scrape
        g.log(f"MyDramaList aliases: cache read failed: {e}", "debug")
        return None
    if cached == CacheBase.NOT_CACHED or not isinstance(cached, list):
        return None
    _memory[key] = cached
    return cached


def _store(key, value, expiration):
    if isinstance(value, list):
        _memory[key] = value
    try:
        g.CACHE.set(key, value, expiration=expiration)
    except Exception as e:
        g.log(f"MyDramaList aliases: cache write failed: {e}", "debug")


def _service_down():
    from resources.lib.database.cache import CacheBase

    try:
        return g.CACHE.get(BREAKER_KEY) != CacheBase.NOT_CACHED
    except Exception:
        return False


def _norm(text):
    """Case, accent, punctuation and space blind form used to compare titles (CJK letters are kept)."""
    text = unicodedata.normalize("NFKC", text or "").casefold()
    return "".join(c for c in text if c.isalnum())


def _is_latin(text):
    return not any(ord(c) > 0x24F for c in text)


def _request(path, state, **params):
    """GET a Kuryana v2 route; returns its 'data', None for 'no such page' (or out of calls); raises _Unavailable."""
    if state["calls"] >= MAX_CALLS:
        return None
    remaining = MAX_SECONDS - (time.monotonic() - state["start"])
    if remaining <= 0:
        raise _Unavailable("lookup took too long")
    state["calls"] += 1
    # the read timeout shrinks with the time left, so the last call cannot run far past MAX_SECONDS
    timeout = (REQUEST_TIMEOUT[0], max(1, min(REQUEST_TIMEOUT[1], remaining)))
    try:
        response = requests.get(KURYANA_URL + path, params=params or None, timeout=timeout, headers={"User-Agent": "Seren"})
    except requests.RequestException as e:
        raise _Unavailable(str(e))
    if response.status_code == 429 or response.status_code >= 500:
        raise _Unavailable(f"HTTP {response.status_code}")
    if not response.ok:
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict) or not body.get("success"):
        return None
    return body.get("data")


def _search(media_type, word, title, original_title, year):
    state = {"calls": 0, "start": time.monotonic()}
    names = [n for n in (_norm(title), _norm(original_title)) if len(n) >= 2]
    queries = [title]
    if original_title and original_title != title and _is_latin(original_title):
        queries.append(original_title)

    tried = set()
    for query in queries:
        data = _request("/v2/search", state, q=query)
        for slug in _candidates(data, media_type, word, year):
            if slug in tried:
                continue
            if len(tried) >= MAX_DETAIL_PAGES:
                break
            tried.add(slug)
            detail = _request(f"/v2/dramas/{quote(slug, safe='')}", state)
            if _matches(detail, names, _norm(original_title), year):
                aliases = _pick_aliases(detail, set(names))
                g.log(f"MyDramaList: {len(aliases)} aliases for '{title}' ({slug}): {aliases}", "info")
                return aliases
    return []


def _candidates(data, media_type, word, year):
    """Slugs of the search hits that have the right country, kind and (within a year) release year."""
    kinds = _MOVIE_KINDS if media_type == "movie" else _SHOW_KINDS
    for item in (data or {}).get("dramas") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type") or "").lower()
        hit_year = item.get("year")
        if not kind.startswith(word + " ") or kind[len(word) + 1 :] not in kinds:
            continue
        if not isinstance(hit_year, int) or abs(hit_year - year) > 1 or not item.get("slug"):
            continue
        yield item["slug"]


def _matches(detail, names, original_norm, year):
    """True when the detail page is the same work: a TMDb title is one of its titles (or inside its native title)."""
    if not isinstance(detail, dict):
        return False
    detail_year = detail.get("year")
    if isinstance(detail_year, int) and abs(detail_year - year) > 1:
        return False
    listed = [detail.get("title"), detail.get("native_title")] + list(detail.get("also_known_as") or [])
    listed = {_norm(t) for t in listed if isinstance(t, str)}
    if any(n in listed for n in names):
        return True
    # TMDb keeps only the short native title ("Dokkaebi"), MyDramaList the long one with the subtitle
    native = _norm(detail.get("native_title") if isinstance(detail.get("native_title"), str) else "")
    return len(original_norm) >= 3 and original_norm in native


def _pick_aliases(detail, known):
    """Short, name-like titles from a detail page: Latin ones first (shortest first), then native ones."""
    listed = [detail.get("title"), detail.get("native_title")] + list(detail.get("also_known_as") or [])
    seen = set(known)
    latin = []
    native = []
    for alias in listed:
        if not isinstance(alias, str):
            continue
        alias = alias.strip()
        norm = _norm(alias)
        if not alias or norm in seen or _JUNK_RE.search(alias):
            continue
        if _is_latin(alias):
            if len(norm) < 4 or len(alias.split()) > MAX_WORDS:
                continue
            seen.add(norm)
            latin.append(alias)
        else:
            if len(norm) < 2:
                continue
            seen.add(norm)
            native.append(alias)
    latin.sort(key=lambda a: len(a.split()))  # stable: MyDramaList's own order breaks ties
    return latin[:MAX_LATIN_ALIASES] + native[:MAX_NATIVE_ALIASES]
