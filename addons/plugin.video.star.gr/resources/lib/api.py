# -*- coding: utf-8 -*-

'''
    Star Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import quote, unquote

from . import constants as c

try:
    from netclient import Net

    _net = Net()
except ImportError:  # pragma: no cover - only when run outside Kodi
    _net = None


USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')

TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------

def fetch(url, timeout=30, retries=2):
    """
    The site rate limits bursts with a 429, which happens when a user pages
    through a long archive quickly. Back off and try again rather than
    surfacing an empty listing.
    """

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'el-GR,el;q=0.9,en;q=0.8',
    }

    for attempt in range(retries + 1):

        try:
            if _net is not None:
                response = _net.http_GET(url, headers=headers, timeout=timeout)
                # netclient falls back to ascii when a response carries no
                # charset, which mangles the Greek titles, so always decode
                # the raw bytes.
                return response.nodecode(True).content.decode('utf-8', 'replace')

            import urllib.request

            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode('utf-8', 'replace')

        except Exception as error:
            if not _throttled(error) or attempt == retries:
                raise

            time.sleep(3 * (attempt + 1))


def _throttled(error):
    """True for the HTTP 429 the site answers bursts with."""

    return getattr(error, 'code', None) == 429 or '429' in str(error)


def _clean(value):
    """Unescapes entities and flattens the whitespace of a scraped string."""

    if not value:
        return ''

    return WS_RE.sub(' ', unescape(value)).strip()


def _abs(url):
    """Makes a site-relative path absolute."""

    if not url:
        return ''

    url = unescape(url)

    if url.startswith('//'):
        return 'https:' + url

    if url.startswith('/'):
        # Unquote first: site paths mix raw UTF-8 and pre-encoded entities,
        # and quoting twice corrupts the latter.
        return c.BASE + quote(unquote(url))

    return url


def _humanize(slug):
    """Turns a url slug into a readable title when no better one exists."""

    return _clean(slug.replace('-', ' ')).capitalize()


# ---------------------------------------------------------------------------
# TV catalogue (/tv/ sections and shows)
#
# The section pages render the current line-up as swiper cards:
#   <a href="/tv/<section>/<show>" class="swiper-slide__link"></a>
#   <div class="item"> ... poster ... hoveredSliderInfo__title>SHOW</...>
# ---------------------------------------------------------------------------

def _swiper_cards(html, prefix, segments=1, deep=False):
    """
    Parses the theme's swiper cards, shared by section pages (shows) and show
    pages (episodes/clips):
        <div class="swiper-slide ...">
          <a href="PREFIX..."> <div class="item"> poster ...
          hoveredSliderInfo__title>TITLE</...>
    ``segments`` counts the path parts after the prefix; deep=True matches
    multi-segment links (episodes) of any depth instead.
    """

    cards = []
    seen = set()

    if deep:
        tail = r'[a-z0-9-/]+'
    else:
        tail = '/[a-z0-9-]+' * segments

    pattern = r'href="((?:https://www\.star\.gr)?{0}{1}/?)"'.format(re.escape(prefix), tail)

    for chunk in re.split(r'<div class="swiper-slide', html)[1:]:
        link = re.search(pattern, chunk[:800])

        if not link:
            continue

        url = _abs(link.group(1).rstrip('/'))

        if url in seen:
            continue

        seen.add(url)

        window = chunk[:8000]

        title = re.search(r'hoveredSliderInfo__title">\s*(.*?)\s*</', window, re.S) or \
            re.search(r'horizontalSlider__info">.*?<p>\s*(.*?)\s*</p>', window, re.S)
        image = re.search(r'data-srcset="([^" ]+)"', window) or \
            re.search(r'data-src="([^"]+)"', window)

        slug = url.rstrip('/').rsplit('/', 1)[-1]

        cards.append({
            'title': _clean(TAG_RE.sub('', title.group(1))) if title else _humanize(slug),
            'url': url,
            'image': _abs(image.group(1)) if image else '',
        })

    return cards


def _endless_config(html):
    """
    Reads the infinite-scroll button (data-plugin-endlessscroll) carrying the
    next page url, or None when the listing is complete.
    """

    match = re.search(r'''data-plugin-endlessscroll=(?:'|\")(\{.*?\})(?:'|\")''', html)

    if not match:
        return None

    try:
        return json.loads(unescape(match.group(1)))
    except Exception:
        return None


def tv_shows(section):
    """
    Returns [{'title', 'url', 'image'}] for one /tv/ section, following the
    "load more" pages until the button stops coming back.
    """

    prefix = '/tv/' + section
    html = fetch('{0}/{1}/'.format(c.BASE_TV, section))

    shows = _swiper_cards(html, prefix)
    seen = set(show['url'] for show in shows)

    config = _endless_config(html)
    pages = 0

    while config and config.get('Url') and config.get('Page') and pages < 20:
        pages += 1
        page_html = fetch('{0}{1}?pg={2}&endless=true'.format(
            c.BASE, config['Url'], config['Page']))

        for card in _swiper_cards(page_html, prefix):
            if card['url'] not in seen:
                seen.add(card['url'])
                shows.append(card)

        config = _endless_config(page_html)

    # Off-season shows keep a page but lose their card; the footer menu still
    # links them, so union those in with their og: artwork.
    for match in re.finditer(
            r'<a href="https://www\.star\.gr(/tv/{0}/[a-z0-9-]+/?)" target="_blank">\s*<span[^>]*></span>\s*(.*?)\s*</a>'.format(
                re.escape(section)), html):
        url = _abs(match.group(1).rstrip('/'))

        if url in seen:
            continue

        seen.add(url)
        meta = _video_meta(url) or {}
        shows.append({
            'title': _clean(TAG_RE.sub('', match.group(2))) or meta.get('title', ''),
            'url': url,
            'image': meta.get('image', ''),
        })

    return shows


# ---------------------------------------------------------------------------
# Show episodes (/tv/<section>/<show>/ pages)
#
# A show page lists its full episodes as dated links plus clip links:
#   <a href="/tv/<section>/<show>/12102026-<show>" class="swiper-slide__link">
# The episode pages resolve through PluginsGR (contentUrl m3u8).
# ---------------------------------------------------------------------------

def show_episodes(show_url):
    """Returns [{'title', 'url', 'image'}] for one show page, in page order."""

    base = show_url.rstrip('/')
    html = fetch(base if base.startswith('http') else c.BASE + base)

    prefix = base.replace(c.BASE, '')
    cards = _swiper_cards(html, prefix)

    episodes = []

    for card in cards:
        if card['url'].rstrip('/') == base:
            continue

        slug = card['url'].rstrip('/').rsplit('/', 1)[-1]
        # Dated slugs (DMMYYYY/DDMMYYYY-show, zero-padded or not) are full
        # episodes, named slugs clips.
        card['dated'] = bool(re.match(r'\d{6,8}-', slug))
        episodes.append(card)

    return episodes


def episode_details(url):
    """
    Reads one /tv/ episode page into an enriched dict. Entries with no
    playable marker (character profiles and other editorial pages share the
    same card markup) report playable False so listings can drop them.
    """

    try:
        html = fetch(url)
    except Exception:
        return None

    playable = bool(
        re.search(r'https://deliver2\.siliconweb\.com/kwik/star\.m3u8\?key=', html)
        or re.search(r'contentUrl": ".+?\.m3u8', html)
        or re.search(r'<iframe[^>]*src="[^"]*(?:youtube|youtu\.be|vimeo|dailymotion)', html, re.I)
        or re.search(r'data-video="([\w-]{11})"', html)
    )

    meta = _video_meta_from_html(html, url)
    meta['playable'] = playable

    return meta


def _video_meta_from_html(html, url):
    """
    Builds a listing dict from already-fetched page html. /video/ pages carry
    og: metatags while /tv/ episode pages use JSON-LD plus twitter metatags.
    """

    title = re.search(r'<meta property="og:title" content="([^"]+)"', html) or \
        re.search(r'"name": "([^"]+)"', html)
    image = re.search(r'<meta property="og:image"\s*content="([^"]+)"', html) or \
        re.search(r'<meta content="([^"]+)" name="twitter:image"', html) or \
        re.search(r'"thumbnailUrl": "([^"]+)"', html)
    plot = re.search(r'<meta property="og:description" content="([^"]+)"', html) or \
        re.search(r'"description": "([^"]+)"', html)

    slug = url.rstrip('/').rsplit('/', 1)[-1]

    if title:
        title = _clean(title.group(1))
        # Strip only the site suffix, pipes inside real titles are kept.
        title = re.sub(r'\s*(-\s*Video)?\s*\|\s*Star(\.gr| TV)\s*$', '', title).strip()
        if title.lower() in ('star tv', 'star.gr'):
            title = ''
    else:
        title = ''

    return {
        'title': title or _humanize(slug),
        'url': url,
        'image': _abs(image.group(1)) if image else '',
        'plot': _clean(plot.group(1)) if plot else '',
    }


# ---------------------------------------------------------------------------
# Video catalogue (/video/ hubs, backed by the video sitemaps)
#
# The sitemap index lists every playable video (loc + lastmod only, ~37k
# entries), grouped by hub category: /video/<hub>/[<sub>/]<id>/<slug>.
# Entries are sorted newest-first and paged; each page is enriched with the
# video page's own og: metatags, like the Alpha add-on's movie deep scrape.
# ---------------------------------------------------------------------------

def _sitemap_urls():
    """Returns the locs of the video sitemap parts from the sitemap index."""

    xml = fetch(c.VIDEO_SITEMAP_INDEX)

    return re.findall(r'<loc>([^<]+)</loc>', xml)


def _sitemap_entries():
    """Returns [{'url', 'lastmod'}] for every video in the sitemaps."""

    entries = []

    for part in _sitemap_urls():
        try:
            xml = fetch(part)
        except Exception:
            continue

        for block in re.findall(r'<url>(.*?)</url>', xml, re.S):
            loc = re.search(r'<loc>([^<]+)</loc>', block)
            lastmod = re.search(r'<lastmod>([^<]+)</lastmod>', block)

            if not loc:
                continue

            url = loc.group(1).strip()

            if '/video/' not in url:
                continue

            entries.append({
                'url': url,
                'lastmod': lastmod.group(1) if lastmod else '',
            })

    entries.sort(key=lambda entry: entry['lastmod'], reverse=True)

    return entries


def category_counts():
    """Returns {category: count} for every hub category in one pass."""

    from collections import Counter

    counts = Counter()

    for entry in _sitemap_entries():
        match = re.match(r'https://www\.star\.gr/video/([a-z0-9-]+)', entry['url'])

        if match:
            counts[match.group(1)] += 1

    return dict(counts)


def _video_meta(url):
    """Reads a video page's og: metatags into a listing dict."""

    try:
        html = fetch(url)
    except Exception:
        return None

    return _video_meta_from_html(html, url)


def category_videos(category, page=1):
    """Returns (items, total_pages) for one hub category page, newest first."""

    prefix = 'https://www.star.gr/video/{0}/'.format(category)
    matches = [entry['url'] for entry in _sitemap_entries() if entry['url'].startswith(prefix)]

    total_pages = max(1, (len(matches) + c.PAGE_SIZE - 1) // c.PAGE_SIZE)
    page = min(max(1, page), total_pages)

    urls = matches[(page - 1) * c.PAGE_SIZE:page * c.PAGE_SIZE]

    items = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_video_meta, url): url for url in urls}

        for future in as_completed(futures):
            try:
                meta = future.result()
            except Exception:
                continue

            if meta and meta['title']:
                items.append(meta)

    # The concurrent fetch scrambles the order, so restore newest-first.
    order = {url: index for index, url in enumerate(urls)}
    items.sort(key=lambda item: order.get(item['url'], 0))

    return items, total_pages


def search(query):
    """
    Searches the site's autocomplete endpoint. Returns (shows, episodes):
    show folders plus directly playable episode/clip pages.
    """

    html = fetch(c.SEARCH_URL.format(quote(query)))

    shows = _swiper_cards(html, '/tv', segments=2)
    show_urls = set(show['url'].rstrip('/') for show in shows)

    episodes = [card for card in _swiper_cards(html, '/tv', deep=True)
                if card['url'].rstrip('/') not in show_urls]

    return shows, episodes


# ---------------------------------------------------------------------------
# Programme (/tv/programma/)
#
# The date slider carries every day as <a data-role="date-tag"
# data-date="<iso>">; other days load through GET
# /tv/$component/ProgramProgramRows?dateRequest=<iso>, whose rows look like:
#   <div class="row row--vCenter row--noWrap"> ... <div class="time">HH:MM
#   [<div class="now">ΤΩΡΑ</div>] ... <div class="image">thumb</div> ...
#   <div class="content"><h2><a href="/tv/...">TITLE</a>
# ---------------------------------------------------------------------------

def programma_dates():
    """Returns [{'label', 'date', 'today'}] for every day in the slider."""

    html = fetch(c.PROGRAMMA_PAGE)

    dates = []

    for match in re.finditer(
            r'<a([^>]*data-role="date-tag"[^>]*)>(.*?)</a>', html, re.S):
        opening, body = match.group(1), match.group(2)
        iso = re.search(r'data-date="([^"]+)"', opening)
        label = _clean(TAG_RE.sub(' ', body))

        if iso and label:
            dates.append({
                'label': label,
                'date': iso.group(1),
                'today': 'today' in opening,
            })

    return dates


def programma_rows(date=None):
    """Returns [{'time', 'now', 'title', 'url', 'image'}] for one day."""

    url = c.PROGRAMMA_ROWS

    if date:
        url = '{0}?dateRequest={1}'.format(url, quote(date, safe=''))

    html = fetch(url)

    rows = []

    for chunk in re.split(r'<div class="row row--vCenter row--noWrap', html)[1:]:
        opening, _, rest = chunk.partition('>')
        time = re.search(r'<div class="time">\s*([\d:]+)', chunk)
        link = re.search(r'<h2>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S)
        content = re.search(r'<div class="content">.*?</h2>\s*<p>(.*?)</p>', chunk, re.S)
        # The row carries several images (rating icon, lazy placeholder); the
        # show thumbnail is the first real one.
        candidates = re.findall(r'data-src="([^"]+)"', chunk)
        candidates += re.findall(r'<img[^>]+src="([^"]+)"', chunk)
        image = next(
            (url for url in candidates
             if 'simanseis' not in url and 'default.svg' not in url), '')

        if not time or not link:
            continue

        rows.append({
            'time': time.group(1),
            'now': 'row--live' in opening or 'ΤΩΡΑ' in rest[:2000],
            'title': _clean(TAG_RE.sub('', link.group(2))),
            'plot': _clean(TAG_RE.sub('', content.group(1))) if content else '',
            'url': _abs(link.group(1)),
            'image': _abs(image) if image else '',
        })

    return [row for row in rows if row['title']]
