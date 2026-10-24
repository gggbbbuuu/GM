"""Anime Filler Episode Detection — scrapes animefillerlist.com for filler data.

Returns per-episode filler/canon/mixed status based on show title.
Uses stdlib html.parser (no BeautifulSoup dependency).
Results cached in module-level dict per show slug.
"""

import re
from html.parser import HTMLParser

import requests

from resources.lib.modules.globals import g

FILLER_LIST_URL = "https://www.animefillerlist.com/shows"

# Process-level cache: {slug: [list of episode type strings]}. Every plugin call is a fresh interpreter, so the lists
# are also kept in Seren's cache database (a list of 7 anime episodes used to cost 7 sequential HTTP requests each time).
_filler_cache = {}

FOUND_CACHE_HOURS = 24  # a list for a show on the site (new episodes are added as they air)
MISSING_CACHE_HOURS = 24  # the site answered "no such show" (404)
ERROR_CACHE_MINUTES = 10  # timeout / 5xx / 429: try again soon, but not on every list open


class _EpisodeListParser(HTMLParser):
    """Minimal parser to extract episode types from animefillerlist.com HTML.

    Matches Otaku's BeautifulSoup pattern: for each <tr> in the EpisodeList table,
    captures the text of the first <span> (the type indicator like "Filler", "Canon").
    """

    def __init__(self):
        super().__init__()
        self.results = []
        self._in_episode_table = False
        self._in_row = False
        self._in_span = False
        self._got_span_this_row = False
        self._current_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table" and "EpisodeList" in attrs_dict.get("class", ""):
            self._in_episode_table = True
        if self._in_episode_table and tag == "tr":
            self._in_row = True
            self._got_span_this_row = False
        if self._in_row and tag == "span" and not self._got_span_this_row:
            self._in_span = True
            self._current_text = ""

    def handle_data(self, data):
        if self._in_span:
            self._current_text += data.strip()

    def handle_endtag(self, tag):
        if tag == "span" and self._in_span:
            self._in_span = False
            self._got_span_this_row = True
            if self._current_text:
                self.results.append(self._current_text)
        if tag == "tr" and self._in_row:
            self._in_row = False
        if tag == "table" and self._in_episode_table:
            self._in_episode_table = False


def _title_to_slug(title):
    """Convert a show title to animefillerlist.com URL slug.

    Examples:
        "Naruto Shippuden" → "naruto-shippuden"
        "One Piece" → "one-piece"
        "Attack on Titan" → "attack-on-titan"
    """
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def _cache_key(slug):
    return f"animefillerlist.{slug}"


def _lookup(slug):
    """The cached list for this slug (memory, then the cache database), or None if it is not cached."""
    if slug in _filler_cache:
        return _filler_cache[slug]
    from resources.lib.database.cache import CacheBase

    try:
        cached = g.CACHE.get(_cache_key(slug))
    except Exception as e:  # a cache problem must never break a list
        g.log(f"Filler list: cache read failed: {e}", "debug")
        return None
    if cached == CacheBase.NOT_CACHED or not isinstance(cached, list):
        return None
    _filler_cache[slug] = cached
    return cached


def _store(slug, results, expiration):
    _filler_cache[slug] = results
    try:
        g.CACHE.set(_cache_key(slug), results, expiration=expiration)
    except Exception as e:
        g.log(f"Filler list: cache write failed: {e}", "debug")


def prefetch(show_titles):
    """Fetch the lists that are not cached yet in parallel, before a list of episodes is built one episode at a time."""
    missing = {}
    for title in show_titles:
        slug = _title_to_slug(title) if title else ""
        if slug and slug not in missing and _lookup(slug) is None:
            missing[slug] = title
    if not missing:
        return
    if len(missing) == 1:
        get_filler_list(next(iter(missing.values())))
        return
    from resources.lib.common.thread_pool import ThreadPool

    pool = ThreadPool()
    try:
        for title in missing.values():
            pool.put(get_filler_list, title)
        pool.wait_completion()
    except Exception as e:
        g.log(f"Filler list: prefetch failed: {e}", "debug")
    finally:
        pool.close()


def get_filler_list(show_title):
    """Get filler episode list for a show by title.

    Args:
        show_title: English show title (e.g. "Naruto Shippuden")

    Returns:
        list of episode type strings in order, e.g.:
        ["Manga Canon", "Manga Canon", "Filler", "Mixed Canon/Filler", ...]
        Empty list if show not found or on error.
        Index 0 = episode 1, index 1 = episode 2, etc.
    """
    if not show_title:
        return []

    slug = _title_to_slug(show_title)

    # Check cache
    cached = _lookup(slug)
    if cached is not None:
        return cached

    import datetime

    try:
        url = f"{FILLER_LIST_URL}/{slug}"
        response = requests.get(url, timeout=5, headers={"User-Agent": "Seren"})

        if not response.ok:
            g.log(f"Filler list: no data for '{show_title}' (slug={slug}, status={response.status_code})", "debug")
            if response.status_code == 404:
                _store(slug, [], datetime.timedelta(hours=MISSING_CACHE_HOURS))
            else:
                _store(slug, [], datetime.timedelta(minutes=ERROR_CACHE_MINUTES))
            return []

        parser = _EpisodeListParser()
        parser.feed(response.text)

        _store(slug, parser.results, datetime.timedelta(hours=FOUND_CACHE_HOURS))
        if parser.results:
            filler_count = sum(1 for ep in parser.results if "filler" in ep.lower() and "canon" not in ep.lower())
            g.log(
                f"Filler list: '{show_title}' — {len(parser.results)} episodes, {filler_count} filler",
                "debug",
            )
        return parser.results

    except requests.RequestException as e:
        g.log(f"Filler list error for '{show_title}': {e}", "warning")
        _store(slug, [], datetime.timedelta(minutes=ERROR_CACHE_MINUTES))
        return []


def is_filler(show_title, episode_number):
    """Check if a specific episode is filler.

    Args:
        show_title: English show title
        episode_number: Episode number (1-indexed)

    Returns:
        True if the episode is filler (not canon), False otherwise.
        Returns False if data is unavailable.
    """
    filler_list = get_filler_list(show_title)
    if not filler_list or episode_number < 1 or episode_number > len(filler_list):
        return False

    ep_type = filler_list[episode_number - 1].lower()
    return "filler" in ep_type and "canon" not in ep_type


def get_episode_type(show_title, episode_number):
    """Get the episode type string for a specific episode.

    Args:
        show_title: English show title
        episode_number: Episode number (1-indexed)

    Returns:
        Episode type string (e.g. "Filler", "Manga Canon", "Mixed Canon/Filler")
        or None if data unavailable.
    """
    filler_list = get_filler_list(show_title)
    if not filler_list or episode_number < 1 or episode_number > len(filler_list):
        return None

    return filler_list[episode_number - 1]


def invalidate_cache():
    """Clear the process-level filler cache (the cache database copies expire on their own)."""
    global _filler_cache
    _filler_cache = {}
